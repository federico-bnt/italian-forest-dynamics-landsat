# Landsat Collection 2 Level-2 Band Guide

## Band Mapping

| Channel | Landsat 5 TM | Landsat 7 ETM+ | Landsat 8 OLI | Landsat 9 OLI-2 |
|---|---|---|---|---|
| Blue | `SR_B1` | `SR_B1` | `SR_B2` | `SR_B2` |
| Red | `SR_B3` | `SR_B3` | `SR_B4` | `SR_B4` |
| Near-Infrared (NIR) | `SR_B4` | `SR_B4` | `SR_B5` | `SR_B5` |
| Short-Wave Infrared 2 (SWIR2) | `SR_B7` | `SR_B7` | `SR_B7` | `SR_B7` |
| Quality Assessment | `QA_PIXEL` | `QA_PIXEL` | `QA_PIXEL` | `QA_PIXEL` |

## Spectral Index Formulas

Apply the Collection 2 surface reflectance scale and offset (`value * 0.0000275 - 0.2`) before calculating indices.

| Index | Landsat 5/7 | Landsat 8/9 |
|---|---|---|
| NDVI | `(SR_B4 - SR_B3) / (SR_B4 + SR_B3)` | `(SR_B5 - SR_B4) / (SR_B5 + SR_B4)` |
| EVI | `2.5 * (SR_B4 - SR_B3) / (SR_B4 + 6 * SR_B3 - 7.5 * SR_B1 + 1)` | `2.5 * (SR_B5 - SR_B4) / (SR_B5 + 6 * SR_B4 - 7.5 * SR_B2 + 1)` |
| NBR | `(SR_B4 - SR_B7) / (SR_B4 + SR_B7)` | `(SR_B5 - SR_B7) / (SR_B5 + SR_B7)` |

## Python/GEE Reference

```python
LANDSAT_BANDS = {
    "L5_L7": {
        "blue": "SR_B1",
        "red": "SR_B3",
        "nir": "SR_B4",
        "swir2": "SR_B7",
        "qa": "QA_PIXEL",
    },
    "L8_L9": {
        "blue": "SR_B2",
        "red": "SR_B4",
        "nir": "SR_B5",
        "swir2": "SR_B7",
        "qa": "QA_PIXEL",
    },
}
```
