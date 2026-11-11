import json
import sys
from pathlib import Path

import ee
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch

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
from src.qualitative_analysis import _fetch_pixels

OUTPUT_DIR = PROJECT_ROOT / "results" / "figures" / "quantitative_expansion"
MAX_SIDE_PX = 1_000
NODATA = -9999
RGB_VIS_MAX = 0.3
FOREST_NDVI_THRESHOLD = 0.6
LOSS_NDVI_DELTA = -0.1
EXPANSION_COLOR = "#00FF00"
LOSS_COLOR = "#FF0000"
MASK_ALPHA = 0.7


def build_expansion_image(t1_composite, t3_composite):
    ndvi_t1 = add_all_indices(t1_composite, "L5_L7").select("NDVI")
    ndvi_t3 = add_all_indices(t3_composite, "L8_L9").select("NDVI")
    expansion = ndvi_t3.gte(FOREST_NDVI_THRESHOLD).And(ndvi_t1.lt(FOREST_NDVI_THRESHOLD))
    return expansion.unmask(0).rename("expanded")


def build_loss_image(t1_composite, t3_composite):
    ndvi_t1 = add_all_indices(t1_composite, "L5_L7").select("NDVI")
    ndvi_t3 = add_all_indices(t3_composite, "L8_L9").select("NDVI")
    loss = ndvi_t3.subtract(ndvi_t1).lt(LOSS_NDVI_DELTA)
    return loss.unmask(0).rename("loss")


def build_rgb_image(t3_composite):
    return t3_composite.select(["SR_B4", "SR_B3", "SR_B2"]).rename(["red", "green", "blue"])


def fetch_region_arrays(t1_composite, t3_composite, bbox):
    image = ee.Image.cat(
        [
            build_rgb_image(t3_composite),
            build_expansion_image(t1_composite, t3_composite),
            build_loss_image(t1_composite, t3_composite),
        ]
    )
    pixels = _fetch_pixels(
        image,
        bbox,
        ["red", "green", "blue", "expanded", "loss"],
        max_side=MAX_SIDE_PX,
        nodata=NODATA,
    )
    rgb = np.dstack([pixels[band] for band in ("red", "green", "blue")])
    rgb = np.clip(np.nan_to_num(rgb, nan=0.0) / RGB_VIS_MAX, 0.0, 1.0)
    expanded = np.nan_to_num(pixels["expanded"]) == 1
    loss = np.nan_to_num(pixels["loss"]) == 1
    return rgb, expanded, loss


def render_region(region_name, bbox, period_label, rgb, expanded, loss):
    xmin, ymin, xmax, ymax = bbox
    extent = (xmin, xmax, ymin, ymax)

    overlay = np.zeros((*expanded.shape, 4))
    overlay[expanded] = (*to_rgb(EXPANSION_COLOR), 1.0)
    overlay[loss] = (*to_rgb(LOSS_COLOR), 1.0)

    fig, ax = plt.subplots(figsize=(9, 7), constrained_layout=True)
    ax.set_aspect(1 / np.cos(np.deg2rad((ymin + ymax) / 2)))
    ax.set_xticks([])
    ax.set_yticks([])

    ax.imshow(rgb, extent=extent)
    ax.imshow(overlay, extent=extent, alpha=MASK_ALPHA)
    ax.set_title("FOREST EXPANSION AND LOSS")
    ax.legend(
        handles=[
            Patch(
                facecolor=EXPANSION_COLOR,
                edgecolor="none",
                label="NDVI T3 ≥ 0.6 and NDVI T1 < 0.6",
            ),
            Patch(
                facecolor=LOSS_COLOR,
                edgecolor="none",
                label="ΔNDVI (T3 − T1) < −0.1",
            ),
        ],
        loc="lower left",
        frameon=True,
        framealpha=0.9,
        fontsize=9,
    )

    fig.suptitle(f"{region_name} ({period_label})", fontsize=13, fontweight="bold")
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
    period_label = f"{t3['start_year']}–{t3['end_year']} vs {t1['start_year']}–{t1['end_year']}"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for region in AREA_KEYS:
        bbox = area_info[region]["bbox"]
        print(f"Rendering {region}...")
        t1_composite = get_median_composite(areas[region], t1, config)
        t3_composite = get_median_composite(areas[region], t3, config)
        rgb, expanded, loss = fetch_region_arrays(t1_composite, t3_composite, bbox)

        fig = render_region(area_info[region]["name"], bbox, period_label, rgb, expanded, loss)
        output_path = OUTPUT_DIR / f"{region}_quantitative_expansion.png"
        fig.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved {output_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
