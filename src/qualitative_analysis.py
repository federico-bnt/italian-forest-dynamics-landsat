from pathlib import Path
from typing import Mapping

import ee
import matplotlib.pyplot as plt
import numpy as np

from src.indices import add_all_indices

CORINE_1990_ASSET = "COPERNICUS/CORINE/V20/100m/1990"
CORINE_ORIGIN_GROUPS = {
    "agriculture": [211, 212, 213, 221, 222, 223, 241, 242, 243, 244],
    "grassland": [231, 321],
    "shrubland": [322, 323, 324],
    "bare_ground": [331, 332, 333, 334, 335],
}


def _get_region_delta(deltas: Mapping[str, ee.Image], region: str) -> ee.Image:
    for key in (f"{region}_delta", region):
        if key in deltas:
            return deltas[key]
    raise KeyError(
        f"No delta image found for {region!r}; expected key "
        f"{region!r} or {region + '_delta'!r}."
    )


def _reduce_expansion_origin(
    landcover: ee.Image,
    expanded_mask: ee.Image,
    aoi: ee.Geometry,
    scale: int,
) -> dict[str, float]:
    all_codes = [code for group in CORINE_ORIGIN_GROUPS.values() for code in group]
    classified = landcover.remap(all_codes, [1] * len(all_codes), 0).eq(1)
    valid_expansion = expanded_mask.And(landcover.gt(0))
    pixel_area_km2 = ee.Image.pixelArea().divide(1_000_000)

    area_bands = []
    for group_name, class_codes in CORINE_ORIGIN_GROUPS.items():
        class_mask = landcover.remap(class_codes, [1] * len(class_codes), 0).eq(1)
        area_bands.append(
            pixel_area_km2.updateMask(valid_expansion.And(class_mask)).rename(group_name)
        )

    other_mask = valid_expansion.And(classified.Not())
    area_bands.extend(
        [
            pixel_area_km2.updateMask(other_mask).rename("other"),
            pixel_area_km2.updateMask(valid_expansion).rename("mapped_total"),
        ]
    )
    totals = (
        ee.Image(area_bands)
        .reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=aoi,
            scale=scale,
            maxPixels=1e13,
            tileScale=4,
        )
        .getInfo()
    )

    mapped_total = float(totals.get("mapped_total") or 0.0)
    result = {"CORINE mapped expansion (km²)": mapped_total}
    for group_name in CORINE_ORIGIN_GROUPS:
        area_km2 = float(totals.get(group_name) or 0.0)
        result[f"CORINE {group_name} (km²)"] = area_km2
        result[f"CORINE {group_name} (%)"] = (
            100 * area_km2 / mapped_total if mapped_total else None
        )

    other_km2 = float(totals.get("other") or 0.0)
    result["CORINE other (km²)"] = other_km2
    result["CORINE other (%)"] = 100 * other_km2 / mapped_total if mapped_total else None
    return result


def calculate_expanded_forest_quality(
    areas: Mapping[str, ee.Geometry],
    deltas: Mapping[str, ee.Image],
    t3_composites: Mapping[str, ee.Image],
    area_info: Mapping[str, Mapping[str, object]],
    land_mask: ee.Image,
    scale: int = 30,
    corine_scale: int = 100,
) -> list[dict[str, object]]:
    """Summarize T3 moisture/structure and CORINE 1990 origin within new-forest pixels."""
    corine_landcover = ee.Image(CORINE_1990_ASSET).select("landcover")
    stats_reducer = ee.Reducer.mean()
    stats_reducer = stats_reducer.combine(ee.Reducer.median(), "", True)
    stats_reducer = stats_reducer.combine(ee.Reducer.stdDev(), "", True)
    stats_reducer = stats_reducer.combine(ee.Reducer.sum(), "", True)

    rows = []
    for region, aoi in areas.items():
        expanded_mask = _get_region_delta(deltas, region).select("expanded_forest").eq(1)
        expanded_mask = expanded_mask.updateMask(land_mask)

        t3_image = t3_composites[region]
        t3_indices = add_all_indices(t3_image, sensor_type="L8_L9")
        ndmi = t3_image.expression(
            "(nir - swir1) / (nir + swir1)",
            {
                "nir": t3_image.select("SR_B5"),
                "swir1": t3_image.select("SR_B6"),
            },
        ).rename("NDMI")
        nbr = t3_indices.select("NBR")

        expanded_metrics = ee.Image(
            [
                ndmi.updateMask(expanded_mask),
                nbr.updateMask(expanded_mask),
                ee.Image.pixelArea()
                .divide(1_000_000)
                .updateMask(expanded_mask)
                .rename("expanded_area_km2"),
            ]
        )
        metrics = expanded_metrics.reduceRegion(
            reducer=stats_reducer,
            geometry=aoi,
            scale=scale,
            maxPixels=1e13,
            tileScale=4,
        ).getInfo()

        expanded_area = float(metrics.get("expanded_area_km2_sum") or 0.0)
        row = {
            "Region": str(area_info[region]["name"]),
            "Expanded Forest (km²)": expanded_area,
            "Mean T3 NDMI": metrics.get("NDMI_mean"),
            "Median T3 NDMI": metrics.get("NDMI_median"),
            "Std T3 NDMI": metrics.get("NDMI_stdDev"),
            "Mean T3 NBR": metrics.get("NBR_mean"),
            "Median T3 NBR": metrics.get("NBR_median"),
            "Std T3 NBR": metrics.get("NBR_stdDev"),
        }
        row.update(
            _reduce_expansion_origin(
                corine_landcover,
                expanded_mask,
                aoi,
                corine_scale,
            )
        )
        rows.append(row)

    return rows


def _fetch_pixels(
    image: ee.Image,
    bbox: list[float],
    bands: list[str],
    max_side: int,
    nodata: float,
) -> dict[str, np.ndarray]:
    xmin, ymin, xmax, ymax = bbox
    pixel_degrees = max(xmax - xmin, ymax - ymin) / max_side
    request = {
        "expression": image.select(bands).unmask(nodata),
        "fileFormat": "NUMPY_NDARRAY",
        "grid": {
            "dimensions": {
                "width": max(1, round((xmax - xmin) / pixel_degrees)),
                "height": max(1, round((ymax - ymin) / pixel_degrees)),
            },
            "affineTransform": {
                "scaleX": pixel_degrees,
                "shearX": 0,
                "translateX": xmin,
                "shearY": 0,
                "scaleY": -pixel_degrees,
                "translateY": ymax,
            },
            "crsCode": "EPSG:4326",
        },
    }
    pixels = ee.data.computePixels(request)
    return {
        band: np.where(pixels[band] == nodata, np.nan, pixels[band])
        for band in bands
    }


def _add_scale_bar(ax, bbox: list[float], length_km: float = 5.0) -> None:
    xmin, ymin, xmax, ymax = bbox
    center_latitude = (ymin + ymax) / 2
    longitude_length = length_km / (111.32 * np.cos(np.deg2rad(center_latitude)))
    x_start = xmin + 0.05 * (xmax - xmin)
    y_position = ymin + 0.07 * (ymax - ymin)
    ax.plot(
        [x_start, x_start + longitude_length],
        [y_position, y_position],
        color="black",
        linewidth=3,
        solid_capstyle="butt",
    )
    ax.text(
        x_start,
        y_position + 0.025 * (ymax - ymin),
        f"{length_km:g} km",
        fontsize=8,
        color="black",
        bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none", "pad": 1},
    )


def _format_map_axis(ax, bbox: list[float], title: str) -> None:
    xmin, ymin, xmax, ymax = bbox
    ax.set_title(title)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    ax.set_aspect(1 / np.cos(np.deg2rad((ymin + ymax) / 2)))
    _add_scale_bar(ax, bbox)


def render_t3_qualitative_figures(
    areas: Mapping[str, ee.Geometry],
    t3_composites: Mapping[str, ee.Image],
    deltas: Mapping[str, ee.Image],
    area_info: Mapping[str, Mapping[str, object]],
    land_mask: ee.Image,
    output_dir: Path,
    max_side: int = 1_000,
    nodata: float = -9999,
) -> list[Path]:
    """Save matched-extent T3 RGB/NDVI/NBR and RGB/NDVI/expanded-NDMI figures."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = []
    rgb_vis_max = 0.3

    for region, aoi in areas.items():
        t3_image = t3_composites[region]
        t3_indices = add_all_indices(t3_image, sensor_type="L8_L9")
        ndmi = t3_image.expression(
            "(nir - swir1) / (nir + swir1)",
            {
                "nir": t3_image.select("SR_B5"),
                "swir1": t3_image.select("SR_B6"),
            },
        ).rename("NDMI")
        rgb = t3_image.select(["SR_B4", "SR_B3", "SR_B2"]).rename(
            ["red", "green", "blue"]
        )
        ndvi = t3_indices.select("NDVI").updateMask(land_mask)
        nbr = t3_indices.select("NBR").updateMask(land_mask)
        ndmi = ndmi.updateMask(land_mask)
        expanded_mask = _get_region_delta(deltas, region).select("expanded_forest").eq(1)
        ndmi_expanded = ndmi.updateMask(expanded_mask).rename("NDMI_expanded")

        map_image = ee.Image(
            [
                rgb.updateMask(land_mask),
                ndvi,
                nbr,
                ndmi,
                ndmi_expanded,
            ]
        ).clip(aoi)
        bbox = list(area_info[region]["bbox"])
        arrays = _fetch_pixels(
            map_image,
            bbox,
            ["red", "green", "blue", "NDVI", "NBR", "NDMI", "NDMI_expanded"],
            max_side,
            nodata,
        )
        rgb_array = np.stack(
            [arrays[band] for band in ("red", "green", "blue")], axis=-1
        )
        rgb_array = np.clip(np.nan_to_num(rgb_array) / rgb_vis_max, 0.0, 1.0)
        region_name = str(area_info[region]["name"])

        figure_a, axes_a = plt.subplots(1, 3, figsize=(16, 6), constrained_layout=True)
        axes_a[0].imshow(rgb_array, extent=(bbox[0], bbox[2], bbox[1], bbox[3]))
        _format_map_axis(axes_a[0], bbox, f"T3 True Color\n{region_name}")

        ndvi_plot = axes_a[1].imshow(
            np.ma.masked_invalid(arrays["NDVI"]),
            cmap="YlGn",
            vmin=0.0,
            vmax=0.8,
            extent=(bbox[0], bbox[2], bbox[1], bbox[3]),
        )
        figure_a.colorbar(ndvi_plot, ax=axes_a[1], label="NDVI", shrink=0.8)
        _format_map_axis(axes_a[1], bbox, f"T3 NDVI\n{region_name}")

        nbr_plot = axes_a[2].imshow(
            np.ma.masked_invalid(arrays["NBR"]),
            cmap="RdYlGn",
            vmin=-1.0,
            vmax=1.0,
            extent=(bbox[0], bbox[2], bbox[1], bbox[3]),
        )
        figure_a.colorbar(nbr_plot, ax=axes_a[2], label="NBR", shrink=0.8)
        _format_map_axis(axes_a[2], bbox, f"T3 NBR\n{region_name}")

        path_a = output_dir / f"T3_NDVI_NBR_comparison_{region}.png"
        figure_a.savefig(path_a, dpi=220, bbox_inches="tight")
        plt.close(figure_a)
        output_paths.append(path_a)

        figure_b, axes_b = plt.subplots(1, 3, figsize=(16, 6), constrained_layout=True)
        axes_b[0].imshow(rgb_array, extent=(bbox[0], bbox[2], bbox[1], bbox[3]))
        _format_map_axis(axes_b[0], bbox, f"T3 True Color\n{region_name}")

        ndvi_plot = axes_b[1].imshow(
            np.ma.masked_invalid(arrays["NDVI"]),
            cmap="YlGn",
            vmin=0.0,
            vmax=0.8,
            extent=(bbox[0], bbox[2], bbox[1], bbox[3]),
        )
        figure_b.colorbar(ndvi_plot, ax=axes_b[1], label="NDVI", shrink=0.8)
        _format_map_axis(axes_b[1], bbox, f"T3 NDVI\n{region_name}")

        ndmi_plot = axes_b[2].imshow(
            np.ma.masked_invalid(arrays["NDMI_expanded"]),
            cmap="YlGnBu",
            vmin=-0.5,
            vmax=0.5,
            extent=(bbox[0], bbox[2], bbox[1], bbox[3]),
        )
        figure_b.colorbar(ndmi_plot, ax=axes_b[2], label="NDMI in expanded forest", shrink=0.8)
        _format_map_axis(axes_b[2], bbox, f"T3 NDMI in Expanded Forest\n{region_name}")

        path_b = output_dir / f"T3_NDVI_NDMI_comparison_{region}.png"
        figure_b.savefig(path_b, dpi=220, bbox_inches="tight")
        plt.close(figure_b)
        output_paths.append(path_b)

    return output_paths
