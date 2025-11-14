Shiny app for DV petitions

How to run

1. Install R (3.6+ recommended) and the packages used by the app:

````markdown
Shiny app for DV petitions (historical boundaries)

Overview
--------
This Shiny app visualizes petitions and overlays historical state boundaries (decade snapshots from 1800–1860).

Summary of recent changes
-------------------------
- Added a Python script to convert zipped shapefiles to GeoJSON: `scripts/convert_shapefiles.py`.
- GeoJSON boundary files are stored in `data/boundaries/` (files named `US_state_1800.geojson`, ..., `US_state_1860.geojson`).
- The app dynamically loads boundaries based on the selected time range (uses the end year of the slider).
- If the slider selects a year beyond 1860, the app falls back to the 1860 boundaries.
- All boundary layers are transformed to WGS84 (EPSG:4326) so Leaflet renders them correctly.
- Styling updates: boundary lines are black and subtly transparent (fainter); hover popups and persistent highlights have been removed.
- Added defensive checks to avoid DataTable initialization errors when inputs are not yet ready.
- Test scripts to validate the GeoJSON files were added: `scripts/test_boundaries.R` and `scripts/test_app.R`.

Requirements
------------
- R (>= 4.0 suggested) with the packages used in `app.R` (examples below).
- Python (if you want to run the shapefile conversion) with `geopandas` installed.

Installing R packages
---------------------
Open R and run:

```r
install.packages(c(
	'shiny', 'DBI', 'RSQLite', 'DT', 'sf', 'leaflet', 'leaflet.extras',
	'viridis', 'bslib', 'testthat'
), repos = 'https://cloud.r-project.org')
```

Installing Python packages
--------------------------
If you plan to run the shapefile conversion script, install geopandas. In a terminal / virtualenv:

```bash
pip install geopandas
# If you use a project venv, activate it first; this repository may include a .venv in the project root
```

File locations
--------------
- App: `shiny_app/app.R`
- Database: `dv_petitions.db` (app expects it at the repo root; `shiny_app` reads `../dv_petitions.db`).
- Boundary data: `data/boundaries/US_state_*.geojson` (created by the conversion script)
- Shapefile conversion script: `scripts/convert_shapefiles.py`
- Tests (R): `scripts/test_boundaries.R`, `scripts/test_app.R`

Converting zipped shapefiles to GeoJSON
---------------------------------------
Place your shapefile ZIPs in the repo `Shapefiles/` directory (one ZIP per decade). Then run:

```bash
# from repo root
python scripts/convert_shapefiles.py
# or, if you have a project venv, run the venv's python: ./.venv/bin/python scripts/convert_shapefiles.py
```

The script will extract each ZIP, run a geometry-fix (buffer(0) to resolve common topology issues), and write GeoJSON files to `data/boundaries/`.

Running the R tests
-------------------
There are small test scripts to validate the GeoJSON files load and are valid:

```bash
# from repo root
Rscript scripts/test_boundaries.R
Rscript scripts/test_app.R
```

Starting the Shiny app
----------------------
From the repository root run (default port used in development is 3839):

```bash
# run from repo root
R -e "shiny::runApp('shiny_app', port = 3839)"
```

Then open the app at: http://127.0.0.1:3839

Notes about the map behavior
----------------------------
- The time slider controls both the data filter and the boundary snapshot shown on the map; the app uses the end-of-range year for boundaries.
- Boundary files exist for decades 1800, 1810, 1820, 1830, 1840, 1850, and 1860. If the slider selects a year that does not exactly match those decades, the app picks the closest previous decade (e.g., 1814 -> 1810).
- For years beyond 1860 the app uses the 1860 boundary file as a fallback.
- Boundary geometries are transformed to WGS84 before being added to the Leaflet map.

Troubleshooting
---------------
- If you see projection warnings in the R console, ensure the GeoJSONs were transformed to EPSG:4326. The app now performs the transform on load.
- If boundary lines are missing or very faint, ensure `data/boundaries/` contains the expected `US_state_*.geojson` files and that they load without errors in R. Use `scripts/test_boundaries.R` to validate.
- If the map or tables show initialization errors on startup, restart the app (inputs are protected now, but an old state may persist).

What changed in the code (quick list)
------------------------------------
- `scripts/convert_shapefiles.py`: converts zipped shapefiles in `Shapefiles/` -> `data/boundaries/*.geojson` (fixes invalid geometry via buffer(0)).
- `shiny_app/app.R`:
	- loads boundary files dynamically from `data/boundaries/` and transforms to EPSG:4326
	- time slider drives boundary selection (uses end year of range)
	- boundary styling: subtle black lines (no hover popups, no persistent highlight)
	- defensive checks to avoid DataTable errors during initialization
	- uses 1860 as fallback for years > 1860

If you want, I can also:
- Add a `requirements.txt` for the Python side and a small R script to install R dependencies automatically.
- Add a Git pre-commit that verifies `data/boundaries/*.geojson` load successfully.

````
