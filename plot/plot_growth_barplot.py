import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = PROJECT_ROOT / "results" / "csv"
CONFIG_PATH = PROJECT_ROOT / "config" / "time_period.json"
OUTPUT_DIR = PROJECT_ROOT / "results" / "figures" / "growth_barplot"
REGION_KEYS = ("gallura", "basilicata", "alpi_apuane", "trento")
PERIODS = ("T1", "T2", "T3")
METRIC = "Forest cover (%)"
METRIC_LABEL = "Change in forest cover vs T1 (%)"
BASELINE_PERIOD = "T1"
BAR_COLOR = "#4C6A8A"
DPI = 300


def load_period_labels():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    labels = {}
    for period in PERIODS:
        info = config["periods"][period]
        labels[period] = f"{period}\n{info['start_year']}–{info['end_year']}"
    return labels


def plot_region(region_key, table, period_labels):
    region_name = table["Region"].iloc[0]
    cover = table.set_index("Period").loc[list(PERIODS), METRIC].to_numpy(dtype=float)
    baseline = cover[PERIODS.index(BASELINE_PERIOD)]
    if baseline == 0:
        raise ValueError(f"{region_key}: {BASELINE_PERIOD} forest cover is zero, cannot compute change.")
    values = (cover / baseline - 1) * 100

    fig, ax = plt.subplots(figsize=(7, 5), constrained_layout=True)
    bars = ax.bar(
        [period_labels[period] for period in PERIODS],
        values,
        width=0.55,
        color=BAR_COLOR,
        edgecolor="black",
        linewidth=0.6,
    )
    ax.bar_label(bars, labels=[f"{value:+.1f}%" for value in values], padding=3, fontsize=10)

    low = min(0.0, values.min())
    high = max(0.0, values.max())
    pad = (high - low) * 0.15 or 1.0
    ax.set_ylim(low - pad if low < 0 else 0, high + pad)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Time period")
    ax.set_ylabel(METRIC_LABEL)
    ax.set_title(f"{region_name}\nForest cover change relative to T1 (NDVI-based)", fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.yaxis.grid(True, linestyle=":", linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)

    fig.savefig(OUTPUT_DIR / f"{region_key}_growth_barplot.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def main():
    period_labels = load_period_labels()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for region_key in REGION_KEYS:
        table = pd.read_csv(CSV_DIR / f"expanded_forest_profile_{region_key}.csv")
        plot_region(region_key, table, period_labels)
        print(f"Saved {region_key}_growth_barplot.png")


if __name__ == "__main__":
    main()
