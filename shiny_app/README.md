Shiny app for DV petitions

How to run

1. Install R (3.6+ recommended) and the packages used by the app:

```r
install.packages(c('shiny','DBI','RSQLite','DT'))
```

2. From the project folder, run the app with R or RStudio:

```bash
# from repo root
R -e "shiny::runApp('shiny_app', host='127.0.0.1', port=3838)"
```

3. Open http://127.0.0.1:3838 in your browser.

Notes

- The app reads the database at `../dv_petitions.db` (relative to `shiny_app/`).
- The UI provides optional filter column/value (basic validation) and a CSV download of the current view.
