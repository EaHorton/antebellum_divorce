#!/usr/bin/env bash
# Script to run the R Shiny app for DV petitions

set -e

# Configuration
HOST="${SHINY_HOST:-127.0.0.1}"
PORT="${SHINY_PORT:-3838}"
APP_DIR="shiny_app"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting DV Petitions Shiny App${NC}"
echo "Host: $HOST"
echo "Port: $PORT"
echo ""

# Check if R is installed
if ! command -v R &> /dev/null; then
    echo -e "${RED}Error: R is not installed or not in PATH${NC}"
    echo "Please install R from https://www.r-project.org/"
    exit 1
fi

echo -e "${GREEN}✓${NC} R found: $(R --version | head -n1)"

# Check if required packages are installed
echo "Checking R packages..."
R --quiet --no-save <<EOF
required_packages <- c('shiny', 'DBI', 'RSQLite', 'DT')
missing_packages <- required_packages[!sapply(required_packages, requireNamespace, quietly = TRUE)]

if (length(missing_packages) > 0) {
  cat("\033[0;31mError: Missing R packages:\033[0m", paste(missing_packages, collapse=", "), "\n")
  cat("\nInstall them with:\n")
  cat("  R -e \"install.packages(c('", paste(missing_packages, collapse="','"), "'))\"\n", sep="")
  quit(status = 1)
} else {
  cat("\033[0;32m✓\033[0m All required packages installed\n")
}
EOF

if [ $? -ne 0 ]; then
    exit 1
fi

# Check if DB exists
DB_PATH="dv_petitions.db"
if [ ! -f "$DB_PATH" ]; then
    echo -e "${YELLOW}Warning: Database file '$DB_PATH' not found${NC}"
    echo "Make sure dv_petitions.db exists in the repo root"
fi

# Run the Shiny app
echo ""
echo -e "${GREEN}Starting Shiny app...${NC}"
echo "Open http://$HOST:$PORT in your browser"
echo "Press Ctrl+C to stop"
echo ""

R -e "shiny::runApp('$APP_DIR', host='$HOST', port=$PORT, launch.browser=FALSE)"
