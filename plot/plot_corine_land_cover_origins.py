from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = PROJECT_ROOT / "results" / "csv"
OUTPUT_DIR = PROJECT_ROOT / "results" / "figures" / "corine_land_cover_origins"
OUTPUT_PATH = OUTPUT_DIR / "corine_land_cover_origins.png"
REGION_KEYS = ("gallura", "basilicata", "alpi_apuane", "trento")
ORIGIN_PERIOD = "T1"
CLASSES = {
    "agriculture": "Agriculture",
    "grassland": "Grassland",
    "shrubland": "Shrubland",
    "bare_ground": "Bare ground",
    "other": "Other (includes forest)",
}
PALETTE = ["#4C72B0", "#55A868", "#C44E52", "#8172B2", "#B07D2B"]
LABEL_MIN_PERCENT = 3.0
DPI = 300


def load_origin_shares(region_key):
    table = pd.read_csv(CSV_DIR / f"expanded_forest_profile_{region_key}.csv")
    row = table.loc[table["Period"] == ORIGIN_PERIOD].iloc[0]
    shares = {label: float(row[f"CORINE {key} (%)"]) for key, label in CLASSES.items()}
    return row["Region"].replace(" (", "\n("), shares


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    regions = [load_origin_shares(key) for key in REGION_KEYS]
    shares = pd.DataFrame([share for _, share in regions], index=[name for name, _ in regions])

    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    bottom = [0.0] * len(shares)
    for color, label in zip(PALETTE, shares.columns):
        values = shares[label].to_numpy()
        bars = ax.bar(
            shares.index,
            values,
            bottom=bottom,
            width=0.6,
            color=color,
            edgecolor="white",
            linewidth=0.8,
            label=label,
        )
        labels = [f"{value:.1f}%" if value >= LABEL_MIN_PERCENT else "" for value in values]
        ax.bar_label(bars, labels=labels, label_type="center", color="white", fontsize=9, fontweight="bold")
        bottom = [base + value for base, value in zip(bottom, values)]

    ax.set_ylim(0, 100)
    ax.set_xlabel("Study area")
    ax.set_ylabel("Share of expanded forest (%)")
    ax.set_title("Land cover origin of expanded forest (CORINE 1990, T1)", fontweight="bold")
    ax.legend(title="CORINE class", bbox_to_anchor=(1.02, 1), loc="upper left", frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.yaxis.grid(True, linestyle=":", linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)

    fig.savefig(OUTPUT_PATH, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
