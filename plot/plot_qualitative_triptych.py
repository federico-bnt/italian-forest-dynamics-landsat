import json
import sys
from pathlib import Path

import ee
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colormaps
from matplotlib.colors import Normalize

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.indices import add_all_indices
from src.landsat_composites import (
    AREA_KEYS,
    CONFIG_DIR,
    get_median_composite,
    load_areas,
    load_project_id,
    load_time_periods,
)
from src.qualitative_analysis import NDMI_BANDS, _fetch_pixels

OUTPUT_DIR = PROJECT_ROOT / "results" / "figures" / "qualitative_triptych"
MAX_SIDE_PX = 1_000
NODATA = -9999
RGB_VIS_MAX = 0.3
FOREST_NDVI_THRESHOLD = 0.6
OVERLAY_ALPHA = 0.85
INDEX_PANELS = (
    ("NDVI", "RdYlGn", "NDVI"),
    ("NDMI", "BrBG", "NDMI (canopy moisture)"),
    ("NBR", "PiYG", "NBR (burn / structure)"),
)


def build_expansion_image(t1_composite, t3_composite):
    ndvi_t1 = add_all_indices(t1_composite, "L5_L7").select("NDVI")
    ndvi_t3 = add_all_indices(t3_composite, "L8_L9").select("NDVI")
    expansion = ndvi_t3.gte(FOREST_NDVI_THRESHOLD).And(ndvi_t1.lt(FOREST_NDVI_THRESHOLD))
    return expansion.unmask(0).rename("expanded")


def build_rgb_image(t3_composite):
    return t3_composite.select(["SR_B4", "SR_B3", "SR_B2"]).rename(["red", "green", "blue"])


def build_index_image(t3_composite):
    indices = add_all_indices(t3_composite, "L8_L9").select(["NDVI", "NBR"])
    ndmi = t3_composite.normalizedDifference(NDMI_BANDS["L8_L9"]).rename("NDMI")
    return indices.addBands(ndmi)


def fetch_region_arrays(t1_composite, t3_composite, bbox):
    image = ee.Image.cat(
        [
            build_rgb_image(t3_composite),
            build_index_image(t3_composite),
            build_expansion_image(t1_composite, t3_composite),
        ]
    )
    pixels = _fetch_pixels(
        image,
        bbox,
        ["red", "green", "blue", "NDVI", "NDMI", "NBR", "expanded"],
        max_side=MAX_SIDE_PX,
        nodata=NODATA,
    )
    rgb = np.dstack([pixels[band] for band in ("red", "green", "blue")])
    rgb = np.clip(np.nan_to_num(rgb, nan=0.0) / RGB_VIS_MAX, 0.0, 1.0)
    expanded = np.nan_to_num(pixels["expanded"]) == 1
    indices = {
        name: np.where(expanded, pixels[name], np.nan) for name in ("NDVI", "NDMI", "NBR")
    }
    return rgb, indices


def render_region(region_name, bbox, period_label, rgb, indices):
    xmin, ymin, xmax, ymax = bbox
    extent = (xmin, xmax, ymin, ymax)

    fig, axes = plt.subplots(1, 3, figsize=(18, 6.5), constrained_layout=True)
    for ax in axes:
        ax.set_aspect(1 / np.cos(np.deg2rad((ymin + ymax) / 2)))
        ax.set_xticks([])
        ax.set_yticks([])

    for ax, (index_name, cmap_name, title) in zip(axes, INDEX_PANELS):
        values = indices[index_name]
        vmin, vmax = np.nanpercentile(values, [2, 98])
        ax.imshow(rgb, extent=extent)
        overlay = ax.imshow(
            np.ma.masked_invalid(values),
            extent=extent,
            cmap=colormaps[cmap_name],
            norm=Normalize(vmin=vmin, vmax=vmax),
            alpha=OVERLAY_ALPHA,
        )
        ax.set_title(title)
        fig.colorbar(overlay, ax=ax, label=index_name, shrink=0.75)

    fig.suptitle(f"{region_name}: newly expanded forest ({period_label})", fontsize=13, fontweight="bold")
    return fig


def main():
    project_id = load_project_id()
    try:
        ee.Initialize(project=project_id)
    except ee.EEException:
        ee.Authenticate()
        ee.Initialize(project=project_id)

    config = load_time_periods()
    areas = load_areas()
    area_info = json.loads((CONFIG_DIR / "areas.json").read_text(encoding="utf-8"))
    t1 = config["periods"]["T1"]
    t3 = config["periods"]["T3"]
    period_label = f"T3 {t3['start_year']}–{t3['end_year']} vs T1 {t1['start_year']}–{t1['end_year']}"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for region in AREA_KEYS:
        bbox = area_info[region]["bbox"]
        print(f"Rendering {region}...")
        t1_composite = get_median_composite(areas[region], t1, config)
        t3_composite = get_median_composite(areas[region], t3, config)
        rgb, indices = fetch_region_arrays(t1_composite, t3_composite, bbox)

        if np.isnan(indices["NDVI"]).all():
            print(f"Skipped {region}: no expanded-forest pixels.")
            continue

        fig = render_region(area_info[region]["name"], bbox, period_label, rgb, indices)
        output_path = OUTPUT_DIR / f"{region}_qualitative_tritych.png"
        fig.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved {output_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
