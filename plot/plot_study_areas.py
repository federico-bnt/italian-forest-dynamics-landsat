from pathlib import Path

import cartopy.crs as ccrs
import cartopy.io.img_tiles as cimgt
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
from matplotlib.patches import Rectangle

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "results" / "figures" / "study_areas" / "italy_study_areas.png"
MAP_EXTENT = (6.5, 19.0, 36.4, 47.2)  # lon_min, lon_max, lat_min, lat_max
SATELLITE_ZOOM = 8

# name, bbox [lon_min, lat_min, lon_max, lat_max], colour, label position (lon, lat)
STUDY_AREAS = [
    ("Gallura (Sardinia)", [9.05, 40.78, 9.65, 41.08], "#d62728", (11.0, 42.2)),
    ("Lucanian Apennines (Val d'Agri)", [15.65, 40.25, 16.25, 40.65], "#1f77b4", (13.4, 39.6)),
    ("Apuan Alps (Tuscany)", [10.12, 44.02, 10.45, 44.28], "#2ca02c", (8.6, 43.2)),
    ("Fiemme Valley (Trentino)", [11.45, 46.20, 11.85, 46.38], "#9467bd", (13.2, 45.7)),
]


class EsriWorldImagery(cimgt.GoogleTiles):
    def _image_url(self, tile):
        x, y, z = tile
        return f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"


def draw_base_map(ax):
    ax.set_extent(MAP_EXTENT, crs=ccrs.PlateCarree())
    ax.add_image(EsriWorldImagery(), SATELLITE_ZOOM)


def draw_study_area(ax, name, bbox, color, label_xy):
    lon_min, lat_min, lon_max, lat_max = bbox
    width = lon_max - lon_min
    height = lat_max - lat_min

    ax.add_patch(
        Rectangle(
            (lon_min, lat_min),
            width,
            height,
            transform=ccrs.PlateCarree(),
            facecolor=to_rgba(color, 0.35),
            edgecolor=color,
            linewidth=1.5,
            zorder=3,
        )
    )

    center = (lon_min + width / 2, lat_min + height / 2)
    ax.annotate(
        name,
        xy=center,
        xytext=label_xy,
        xycoords="data",
        textcoords="data",
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
        color=color,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=color, alpha=0.9),
        arrowprops=dict(arrowstyle="-|>", color=color, linewidth=1.5, shrinkA=4, shrinkB=2),
        annotation_clip=False,
        zorder=5,
    )


def main():
    fig = plt.figure(figsize=(9, 10))
    ax = plt.axes(projection=ccrs.PlateCarree())

    draw_base_map(ax)
    for name, bbox, color, label_xy in STUDY_AREAS:
        draw_study_area(ax, name, bbox, color, label_xy)

    ax.set_axis_off()
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=300, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    print(f"Saved {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
