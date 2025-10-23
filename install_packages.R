packages <- c("shiny", "DBI", "RSQLite", "DT", "sf", "leaflet", "leaflet.extras", "viridis", "bslib")

installed_packages <- rownames(installed.packages())
packages_to_install <- packages[!packages %in% installed_packages]

if (length(packages_to_install) > 0) {
  cat("Installing missing packages:", paste(packages_to_install, collapse=", "), "\n")
  install.packages(packages_to_install)
} else {
  cat("All required packages are already installed.\n")
}