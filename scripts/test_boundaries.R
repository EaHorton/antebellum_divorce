library(sf)
library(testthat)

# Test file
test_that("Boundary files can be read correctly", {
  years <- c(1800, 1810, 1820, 1830, 1840, 1850, 1860)
  
  for (year in years) {
    filename <- file.path("/Users/eahorton/antebellum_divorce_clone/antebellum_divorce/data/boundaries", sprintf("US_state_%d.geojson", year))
    print(paste("Testing", filename))
    
    # Try to read the file
    states <- st_read(filename, quiet = TRUE)
    
    # Basic checks
    expect_true(inherits(states, "sf"))
    expect_true(nrow(states) > 0)
    expect_true("geometry" %in% names(states))
    
    # Check if geometries are valid
    expect_true(all(st_is_valid(states)))
    
    print(paste("✓ File for year", year, "passed all checks"))
  }
})

# Run the test
test_results <- test_file("scripts/test_boundaries.R", reporter = "progress")