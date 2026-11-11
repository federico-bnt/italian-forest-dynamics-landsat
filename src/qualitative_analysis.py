from pathlib import Path
from typing import Mapping

import ee
import matplotlib.pyplot as plt
import numpy as np

from src.indices import add_all_indices

CORINE_CLASS_LABELS = ("agriculture", "grassland", "shrubland", "bare_ground", "other")
NDMI_BANDS = {"L5_L7": ("SR_B4", "SR_B5"), "L8_L9": ("SR_B5", "SR_B6")}
CORINE_EPOCH_ASSETS = {
    "T1": "COPERNICUS/CORINE/V20/100m/1990",
    "T2": "COPERNICUS/CORINE/V20/100m/2006",
    "T3": "COPERNICUS/CORINE/V20/100m/2018",  # 2018 ends 4+ years before T3 starts
}


def _get_region_delta(deltas: Mapping[str, ee.Image], region: str) -> ee.Image:
    for key in (f"{region}_delta", region):
        if key in deltas:
            return deltas[key]
    raise KeyError(
        f"No delta image found for {region!r}; expected key "
        f"{region!r} or {region + '_delta'!r}."
    )


def _percent(part: float, total: float):
    return 100 * part / total if total else None


def _corine_group(code: int) -> str:
    if code // 100 == 2:
        return "agriculture"
    if code == 321:
        return "grassland"
    if code in (322, 323, 324):
        return "shrubland"
    if code // 10 == 33:
        return "bare_ground"
    return "other"


def _corine_class_areas(
    corine_landcover: ee.Image,
    valid: ee.Image,
    aoi: ee.Geometry,
    scale: int,
) -> dict[str, float]:
    image = (
        ee.Image.pixelArea()
        .divide(1_000_000)
        .addBands(corine_landcover)
        .updateMask(valid)
    )
    result = image.reduceRegion(
        reducer=ee.Reducer.sum().group(groupField=1, groupName="code"),
        geometry=aoi,
        scale=scale,
        maxPixels=1e13,
        tileScale=4,
    ).getInfo()
    class_km2: dict[str, float] = {}
    for group in next(iter(result.values())):
        label = _corine_group(int(group["code"]))
        class_km2[label] = class_km2.get(label, 0.0) + float(group["sum"])
    return class_km2


def calculate_expanded_forest_profile(
    areas: Mapping[str, ee.Geometry],
    deltas: Mapping[str, ee.Image],
    period_composites: Mapping[str, Mapping[str, ee.Image]],
    sensor_types: Mapping[str, str],
    area_info: Mapping[str, Mapping[str, object]],
    land_mask: ee.Image,
    scale: int = 30,
    corine_scale: int = 100,
    forest_ndvi_threshold: float = 0.6,
) -> list[dict[str, object]]:
    """Per region and period: NDMI, NBR inside the expanded-forest mask, NDVI forest cover and CORINE land cover."""
    stats_reducer = ee.Reducer.mean()
    stats_reducer = stats_reducer.combine(ee.Reducer.median(), "", True)
    stats_reducer = stats_reducer.combine(ee.Reducer.stdDev(), "", True)
    stats_reducer = stats_reducer.combine(ee.Reducer.sum(), "", True)

    rows = []
    for region, aoi in areas.items():
        expanded = (
            _get_region_delta(deltas, region).select("expanded_forest").eq(1).And(land_mask)
        )
        expanded_mask = expanded.selfMask()
        region_name = str(area_info[region]["name"])

        for period_key, corine_asset in CORINE_EPOCH_ASSETS.items():
            composite = period_composites[region][period_key]
            sensor_type = sensor_types[period_key]
            nir_band, swir1_band = NDMI_BANDS[sensor_type]
            ndmi = composite.normalizedDifference([nir_band, swir1_band]).rename("NDMI")
            indices = add_all_indices(composite, sensor_type)
            nbr = indices.select("NBR")
            forest_cover = (
                indices.select("NDVI").gte(forest_ndvi_threshold).rename("forest_cover")
            )

            metrics = (
                ee.Image(
                    [
                        ndmi.updateMask(expanded_mask),
                        nbr.updateMask(expanded_mask),
                        forest_cover.updateMask(land_mask),
                        ee.Image.pixelArea()
                        .divide(1_000_000)
                        .updateMask(expanded_mask)
                        .rename("expanded_area_km2"),
                    ]
                )
                .reduceRegion(
                    reducer=stats_reducer,
                    geometry=aoi,
                    scale=scale,
                    maxPixels=1e13,
                    tileScale=4,
                )
                .getInfo()
            )

            corine_landcover = ee.Image(corine_asset).select("landcover")
            class_km2 = _corine_class_areas(
                corine_landcover,
                corine_landcover.gt(0).And(expanded),
                aoi,
                corine_scale,
            )
            corine_total_km2 = sum(class_km2.values())

            forest_cover_mean = metrics.get("forest_cover_mean")
            forest_cover_pct = None if forest_cover_mean is None else 100 * forest_cover_mean

            row = {
                "Region": region_name,
                "Period": period_key,
                "CORINE year": corine_asset.split("/")[-1],
                "Expanded Forest (km²)": float(metrics.get("expanded_area_km2_sum") or 0.0),
                "Forest cover (%)": forest_cover_pct,
                "Mean NDMI": metrics.get("NDMI_mean"),
                "Median NDMI": metrics.get("NDMI_median"),
                "Std NDMI": metrics.get("NDMI_stdDev"),
                "Mean NBR": metrics.get("NBR_mean"),
                "Median NBR": metrics.get("NBR_median"),
                "Std NBR": metrics.get("NBR_stdDev"),
                "CORINE mapped expansion (km²)": corine_total_km2,
            }
            for label in CORINE_CLASS_LABELS:
                label_km2 = class_km2.get(label, 0.0)
                row[f"CORINE {label} (km²)"] = label_km2
                row[f"CORINE {label} (%)"] = _percent(label_km2, corine_total_km2)
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
