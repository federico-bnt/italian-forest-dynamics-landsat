import ee

LANDSAT_BANDS = {
    "L5_L7": {
        "blue": "SR_B1",
        "red": "SR_B3",
        "nir": "SR_B4",
        "swir2": "SR_B7",
    },
    "L8_L9": {
        "blue": "SR_B2",
        "red": "SR_B4",
        "nir": "SR_B5",
        "swir2": "SR_B7",
    },
}


def add_ndvi(
    image: ee.Image,
    nir_band: str = "SR_B5",
    red_band: str = "SR_B4",
) -> ee.Image:
    """Append NDVI calculated from near-infrared and red reflectance bands."""
    ndvi = image.normalizedDifference([nir_band, red_band]).rename("NDVI")
    return image.addBands(ndvi)


def add_evi(
    image: ee.Image,
    nir_band: str = "SR_B5",
    red_band: str = "SR_B4",
    blue_band: str = "SR_B2",
) -> ee.Image:
    """Append EVI calculated from near-infrared, red, and blue bands."""
    evi = image.expression(
        "2.5 * ((nir - red) / (nir + 6 * red - 7.5 * blue + 1))",
        {
            "nir": image.select(nir_band),
            "red": image.select(red_band),
            "blue": image.select(blue_band),
        },
    ).rename("EVI")
    return image.addBands(evi)


def add_nbr(
    image: ee.Image,
    nir_band: str = "SR_B5",
    swir2_band: str = "SR_B7",
) -> ee.Image:
    """Append NBR calculated from near-infrared and SWIR2 reflectance bands."""
    nbr = image.normalizedDifference([nir_band, swir2_band]).rename("NBR")
    return image.addBands(nbr)


def add_all_indices(image: ee.Image, sensor_type: str = "L8_L9") -> ee.Image:
    """Append NDVI, EVI, and NBR using the selected Landsat sensor mapping."""
    if sensor_type not in LANDSAT_BANDS:
        supported_sensors = ", ".join(LANDSAT_BANDS)
        raise ValueError(
            f"Unsupported sensor_type {sensor_type!r}. "
            f"Choose one of: {supported_sensors}."
        )

    bands = LANDSAT_BANDS[sensor_type]
    image = add_ndvi(image, bands["nir"], bands["red"])
    image = add_evi(image, bands["nir"], bands["red"], bands["blue"])
    return add_nbr(image, bands["nir"], bands["swir2"])
