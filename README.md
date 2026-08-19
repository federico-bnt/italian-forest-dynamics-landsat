# Multi-Temporal Landsat Analysis of Italian Forest Dynamics (1985–2025)

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Google Earth Engine](https://img.shields.io/badge/Google%20Earth%20Engine-API-green.svg)](https://earthengine.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Context & Literature Baseline
This repository contains the final project for the **Big Data Analytics** course (M.Sc. Data Science) at the **University of Potsdam**.

Rather than simply replicating existing literature, this project uses the scientific findings of two landmark national studies as its baseline:

1. **Agnoletti et al. (2022)** — *Cultural values and forest dynamics: The Italian forests in the last 150 years* (Forest Ecology and Management).
   > Highlights that Italy's forest area has nearly tripled (from 4.2M ha in 1888 to ~11.8M ha today), with over 5.2M ha consisting of secondary forests naturally established on abandoned agricultural land and pastures.
2. **D'Agata, Marchetti, Salvati, & Corona (2025)** — *Long-term forestation-deforestation dynamics in a socioeconomic perspective: The case of Italy, 1936–2018* (Forest Policy and Economics).
   > Confirms the long-term trend through the lens of Forest Transition Theory, linking forest expansion in remote/mountain municipalities to rural depopulation, while urbanized flatlands experienced localized deforestation.

---

## Research Question & Objective
> *How can multi-temporal Landsat imagery be used to validate the reported expansion of Italian forests (1985–2025) and characterize the condition and disturbance history of newly established forested areas?*

The key idea is to move beyond measuring **how much** forest cover has expanded and instead investigate **what has actually grown**. We aim to determine whether the reported expansion corresponds to healthy forest ecosystems or whether some of the newly classified forest areas include degraded, low-density, or fire-disturbed vegetation.

---

## Case Studies & Regional Dynamics
We analyze four distinct geographic regions in Italy, each representing specific socioeconomic drivers or ecological disturbances:

1. **Gallura (Sardinia):** Agro-pastoral abandonment, cork oak canopy shifts, and wildfire disturbance recovery (**NBR** focus).
2. **Basilicata:** Inland Apennine depopulation and secondary succession over former agricultural land (**NDVI** focus).
3. **Alpi Apuane (Tuscany):** High-altitude pasture abandonment, canopy closure, and biomass saturation (**EVI** focus).
4. **Autonomous Province of Trento:** Abrupt forest loss and natural regeneration post-Storm Vaia (2018) (**NBR / Disturbance** focus).

---

## Temporal Windows
To capture long-term trends across 40 years of Earth Observation data, we analyze three multi-year summer compositing periods (June–September):

* **Period 1 (1985–1991):** Historical baseline — *Landsat 5 TM*
* **Period 2 (2006–2010):** Intermediate transition — *Landsat 5 TM*
* **Period 3 (2022–2025):** Recent state — *Landsat 8 OLI & Landsat 9 OLI-2*

---

## Proposed Workflow & Methodology
To overcome local I/O bottlenecks and avoid storing hundreds of gigabytes of raw satellite tiles locally, the project adopts a **cloud-native geospatial Big Data pipeline** ("Bring code to data"):

---

## 👥 Contributors & Authors
* **Federico Bonato** ([federico.bonato@uni-potsdam.de](mailto:federico.bonato@uni-potsdam.de))
* **Rishikesh Bharti** ([rishikesh.bharti@uni-potsdam.de](mailto:rishikesh.bharti@uni-potsdam.de))

*M.Sc. Data Science — University of Potsdam*

---