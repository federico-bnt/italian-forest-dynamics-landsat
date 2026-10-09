import json
from pathlib import Path

import ee

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"
AREA_KEYS = ("gallura", "basilicata", "alpi_apuane", "trento")


def load_areas(path=CONFIG_DIR / "areas.json"):
    with Path(path).open(encoding="utf-8") as areas_file:
        area_data = json.load(areas_file)

    return {
        key: ee.Geometry.BBox(*area_data[key]["bbox"])
        for key in AREA_KEYS
    }


def load_time_periods(path=CONFIG_DIR / "time_period.json"):
    with Path(path).open(encoding="utf-8") as periods_file:
        config = json.load(periods_file)

    required_periods = {"T1", "T2", "T3"}
    missing_periods = required_periods.difference(config["periods"])
    if missing_periods:
        missing = ", ".join(sorted(missing_periods))
        raise ValueError(f"Missing time period configuration: {missing}")

    return config


def mask_and_scale_landsat_sr(image):
    qa_pixel = image.select("QA_PIXEL")
    clear_mask = (
        qa_pixel.bitwiseAnd(1 << 3).eq(0)
        .And(qa_pixel.bitwiseAnd(1 << 4).eq(0))
    )
    scaled_sr = image.select("SR_B.*").multiply(0.0000275).add(-0.2)
    return image.addBands(scaled_sr, overwrite=True).updateMask(clear_mask)


def get_median_composite(aoi, period, config):
    collection_ids = period["collection_ids"]
    collection = ee.ImageCollection(collection_ids[0])
    for collection_id in collection_ids[1:]:
        collection = collection.merge(ee.ImageCollection(collection_id))

    start_year = period["start_year"]
    end_year = period["end_year"]
    summer = config["summer"]
    summer_collection = (
        collection.filterBounds(aoi)
        .filterDate(f"{start_year}-01-01", f"{end_year + 1}-01-01")
        .filter(
            ee.Filter.calendarRange(
                summer["start_day_of_year"],
                summer["end_day_of_year"],
                "day_of_year",
            )
        )
        .filter(ee.Filter.lt("CLOUD_COVER", config["max_cloud_cover_percent"]))
    )

    return summer_collection.map(mask_and_scale_landsat_sr).median().clip(aoi)


def build_composites(areas, config):
    composites = {}
    for region_name, aoi in areas.items():
        for period_name, period in config["periods"].items():
            composite_key = f"{region_name}_{period_name}"
            print(f"Generating {composite_key}...")
            composites[composite_key] = get_median_composite(aoi, period, config)

    return composites
