required_packages <- c("shiny", "DBI", "RSQLite", "DT", "sf", "leaflet", "leaflet.extras", "viridis", "bslib")

# Get currently installed packages
installed_packages <- rownames(installed.packages())

# Find which packages need to be installed
packages_to_install <- required_packages[!required_packages %in% installed_packages]

if (length(packages_to_install) > 0) {
    cat("Installing missing packages:", paste(packages_to_install, collapse=", "), "\n")
    install.packages(packages_to_install)
} else {
    cat("All required packages are already installed.\n")
}