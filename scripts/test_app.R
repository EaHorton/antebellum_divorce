library(shiny)
library(testthat)
library(sf)

source("shiny_app/app.R")  # Load the app code

# Test the get_state_boundaries function
test_that("get_state_boundaries works correctly", {
  # Test for each decade
  years <- c(1800, 1810, 1820, 1830, 1840, 1850, 1860)
  
  for (year in years) {
    print(paste("Testing year:", year))
    
    # Get boundaries for the year
    states <- get_state_boundaries(year)
    
    # Check that we got an sf object
    expect_true(inherits(states, "sf"))
    
    # Check that we have geometries
    expect_true("geometry" %in% names(states))
    
    # Check that we have some rows
    expect_true(nrow(states) > 0)
    
    print(paste("✓ Boundaries for", year, "loaded correctly"))
  }
})

# Test intermediate years (should get closest previous decade)
test_that("get_state_boundaries handles intermediate years", {
  test_cases <- list(
    list(input = 1805, expected = 1800),
    list(input = 1812, expected = 1810),
    list(input = 1825, expected = 1820),
    list(input = 1838, expected = 1830),
    list(input = 1845, expected = 1840),
    list(input = 1858, expected = 1850)
  )
  
  for (test in test_cases) {
    print(paste("Testing intermediate year:", test$input))
    
    # Get the actual file path that would be used
    actual_path <- basename(dirname(dirname(attr(get_state_boundaries(test$input), "path"))))
    expected_path <- sprintf("US_state_%d", test$expected)
    
    # Check that we got the right file
    expect_true(grepl(expected_path, actual_path))
    
    print(paste("✓ Year", test$input, "correctly mapped to", test$expected))
  }
})

print("All tests complete!")