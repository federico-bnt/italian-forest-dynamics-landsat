import ee

STUDY_REGIONS = ("gallura", "basilicata", "alpi_apuane", "trento")


def calculate_expansion_area(
    delta_image: ee.Image,
    aoi: ee.Geometry,
    index_band: str = "delta_NDVI",
    threshold: float = 0.15,
) -> float:
    """Calculate the area above an index-delta threshold in square kilometers."""
    expansion_mask = delta_image.select(index_band).gt(threshold)
    area_km2 = (
        expansion_mask.multiply(ee.Image.pixelArea())
        .multiply(1e-6)
        .rename("area_km2")
    )
    area_sum = area_km2.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=30,
        maxPixels=1_000_000_000,
    )

    area_value = area_sum.get("area_km2").getInfo()
    return 0.0 if area_value is None else float(area_value)


def get_all_region_areas(
    delta_composites: dict[str, ee.Image],
    regions_dict: dict[str, ee.Geometry],
    threshold: float = 0.15,
    index_band: str = "delta_NDVI",
) -> dict[str, float]:
    """Calculate thresholded expansion area for each study region."""
    region_areas = {}
    for region in STUDY_REGIONS:
        area_km2 = calculate_expansion_area(
            delta_composites[f"{region}_delta"],
            regions_dict[region],
            index_band=index_band,
            threshold=threshold,
        )
        region_areas[region] = area_km2
        print(f"{region}: {area_km2:.3f} km^2")

    return region_areas
