# Antebellum Divorce — Shiny DB Explorer

A small R Shiny app to explore `dv_petitions.db`.

Requirements
- R (>= 4.0)
- R packages: shiny, DBI, RSQLite, DT, ggplot2

Install packages in R:

```r
install.packages(c('shiny','DBI','RSQLite','DT','ggplot2'))
```

Run the app

From the `shiny_app` directory:

```bash
Rscript -e "shiny::runApp('.')"
```

By default the app looks for `dv_petitions.db` one level up from the app directory. You can override the DB path by setting the `DV_DB_PATH` environment variable, e.g.:

```bash
export DV_DB_PATH=/full/path/to/dv_petitions.db
Rscript -e "shiny::runApp('.')"
```
