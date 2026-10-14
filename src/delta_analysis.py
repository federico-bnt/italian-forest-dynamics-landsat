import ee

from src.indices import add_all_indices

STUDY_REGIONS = ("gallura", "basilicata", "alpi_apuane", "trento")


def build_delta_composites(
    composites: dict[str, ee.Image],
) -> dict[str, ee.Image]:
    """Build T3-minus-T1 NDVI and NBR images for each study region."""
    delta_composites = {}

    for region in STUDY_REGIONS:
        image_t1 = add_all_indices(
            composites[f"{region}_T1"],
            sensor_type="L5_L7",
        )
        image_t3 = add_all_indices(
            composites[f"{region}_T3"],
            sensor_type="L8_L9",
        )

        delta_ndvi = (
            image_t3.select("NDVI")
            .subtract(image_t1.select("NDVI"))
            .rename("delta_NDVI")
        )
        delta_nbr = (
            image_t3.select("NBR")
            .subtract(image_t1.select("NBR"))
            .rename("delta_NBR")
        )
        delta_composites[f"{region}_delta"] = ee.Image([delta_ndvi, delta_nbr])
        print(f"Completed delta analysis for {region}.")

    return delta_composites


def get_expansion_mask(
    delta_image: ee.Image,
    band_name: str = "delta_NDVI",
    threshold: float = 0.15,
) -> ee.Image:
    """Return a binary mask for pixels where the selected delta exceeds threshold."""
    return delta_image.select(band_name).gt(threshold).rename("vegetation_expansion")
