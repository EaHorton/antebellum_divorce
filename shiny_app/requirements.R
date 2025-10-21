# Helper to install required packages for the Shiny app
packages <- c('shiny','DBI','RSQLite','DT','ggplot2')
installed <- rownames(installed.packages())
for (p in packages) {
  if (!p %in% installed) install.packages(p)
}
