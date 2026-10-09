# Google Earth Engine Setup

## Prerequisites

- Python environment with the required packages:

  ```bash
  python -m pip install earthengine-api geemap
  ```

- A Google account with **Earth Engine User** and **Resource Viewer** access to the shared GCP project.

## One-Time Authentication

Authenticate from a terminal using the Google account that has access to the shared project:

```bash
earthengine authenticate
```

Complete the browser authorization prompt. Authentication is saved locally for later Python sessions.

## Initialize Earth Engine in Python

```python
import ee

PROJECT_ID = "bd-506013"

try:
    ee.Initialize(project=PROJECT_ID)
    print("GEE initialized successfully.")
except Exception:
    ee.Authenticate()
    ee.Initialize(project=PROJECT_ID)
```

## Troubleshooting Permissions

If initialization reports a permission error, confirm that:

- The active Google account is the one granted access to the shared project. Re-run `earthengine authenticate` if needed.
- The account has **Earth Engine User** and **Resource Viewer** roles on project `bd-506013`.
- `PROJECT_ID` matches the shared GCP project ID exactly.
