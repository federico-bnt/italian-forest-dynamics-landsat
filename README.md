# Multi-Temporal Landsat Analysis of Italian Forest Dynamics (1985-2025)

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Google Earth Engine](https://img.shields.io/badge/Google%20Earth%20Engine-API-green.svg)](https://earthengine.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Project

This project uses Landsat Collection 2 Level-2 imagery in Google Earth Engine to compare forest conditions across four Italian study areas from 1985 to 2025. It examines where forest cover increased, how vegetation indices changed, and the moisture and land-cover characteristics of expanded forest.

The project was developed for the Big Data Analytics course in the M.Sc. Data Science program at the University of Potsdam.

## Study Areas

The AOIs are bounding boxes defined in `config/areas.json`; they are focused study areas, not complete administrative regions.

| Key | Study area | Focus |
|---|---|---|
| `gallura` | Gallura, Limbara and inland Sardinia | Agricultural abandonment and wildfire recovery |
| `basilicata` | Lucanian Apennines, Val d'Agri | Secondary succession |
| `alpi_apuane` | Apuan Alps mountain core | Pasture abandonment and canopy closure |
| `trento` | Fiemme Valley and Paneveggio | Storm Vaia disturbance and regeneration |

## Time Periods

All periods use summer imagery filtered to day-of-year 152-243 and scene cloud cover below 20%.

| Period | Years | Landsat collections |
|---|---|---|
| T1 | 1985-1991 | Landsat 5 TM |
| T2 | 2006-2010 | Landsat 5 TM and Landsat 7 ETM+ |
| T3 | 2022-2025 | Landsat 8 OLI and Landsat 9 OLI-2 |

Surface reflectance is scaled using the Collection 2 Level-2 scale and offset. Cloud and cloud-shadow pixels are masked with `QA_PIXEL`. Cross-sensor harmonization is not applied, so sensor differences may contribute to observed changes.

## Analysis

The notebooks create median composites and calculate NDVI, EVI, and NBR. The T3-minus-T1 analysis identifies expanded forest as pixels below the NDVI forest threshold in T1 and at or above it in T3. Water is excluded using ESA WorldCover 2021.

The qualitative analysis compares expanded pixels with CORINE 1990 land cover and summarizes T3 NDMI and NBR within the expansion mask. CORINE origin percentages use only expanded pixels with valid CORINE coverage; the 1990 product represents source coverage from 1989 to 1998.

## Setup and Notebooks

Install the Earth Engine Python API and geemap, authenticate with a Google account that has access to the shared GCP project, and run the notebooks from the repository root. See [GEE_SETUP.md](GEE_SETUP.md) for setup instructions.

- `landsat_summer_composite.ipynb` builds regional composites, calculates index changes, and provides interactive map inspection.
- `02_indices_analysis.ipynb` generates differential maps, summary statistics, NDVI comparison thumbnails, qualitative summaries, and T3 comparison figures. It also contains local GeoTIFF download code; generated rasters are saved under `results/TIFF/` when that cell completes successfully.

## Outputs

- `results/maps/`: differential NDVI and NBR maps.
- `results/ndvi_thumbnails/`: fixed-scale T1, T2, and T3 NDVI images and comparison grid.
- `results/qualitative_figures/`: T3 RGB/NDVI/NBR and RGB/NDVI/NDMI comparison figures.
- `results/summary_stats.csv`: area and change summary.
- `results/qualitative_summary_stats.csv`: CORINE origin and expanded-forest NDMI/NBR statistics.
- `results/TIFF/`: local GeoTIFF outputs when exports complete successfully.

## Project Structure

```text
.
├── 02_indices_analysis.ipynb
├── BAND_GUIDE.md
├── GEE_SETUP.md
├── LICENSE
├── README.md
├── landsat_summer_composite.ipynb
├── config/
│   ├── areas.json
│   ├── project_id.json
│   └── time_period.json
├── papers/
│   ├── Cultural Values and Forest Dynamics.pdf
│   └── Forestation Deforestation Dynamics Italy 1936-2018.pdf
└── src/
    ├── area_analysis.py
    ├── delta_analysis.py
    ├── indices.py
    ├── landsat_composites.py
    └── qualitative_analysis.py
```

## References

- Agnoletti et al. (2022), “Cultural values and forest dynamics: The Italian forests in the last 150 years,” *Forest Ecology and Management*.
- D'Agata, Marchetti, Salvati, and Corona (2025), “Long-term forestation-deforestation dynamics in a socioeconomic perspective: The case of Italy, 1936-2018,” *Forest Policy and Economics*.

## Authors

- Federico Bonato, [federico.bonato@uni-potsdam.de](mailto:federico.bonato@uni-potsdam.de)
- Rishikesh Bharti, [rishikesh.bharti@uni-potsdam.de](mailto:rishikesh.bharti@uni-potsdam.de)

M.Sc. Data Science, University of Potsdam.