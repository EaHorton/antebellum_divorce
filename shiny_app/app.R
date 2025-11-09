library(shiny)
library(DBI)
library(RSQLite)
library(DT)
library(sf)
library(leaflet)
library(leaflet.extras)
library(viridis)
library(bslib)

# Path to the SQLite DB and boundary data (absolute paths)
app_dir <- getwd()
base_dir <- dirname(app_dir)
db_path <- file.path(base_dir, 'dv_petitions.db')
boundary_dir <- file.path(base_dir, 'data', 'boundaries')

print(paste("Base directory:", base_dir))
print(paste("Boundary directory:", boundary_dir))
print("Available boundary files:")
print(list.files(boundary_dir, pattern = "*.geojson"))

# Function to get state boundaries for a specific year
get_state_boundaries <- function(year) {
  # Round down to nearest decade
  decade <- floor(year/10) * 10
  # Get the closest available year that's not greater than the target year
  available_years <- c(1800, 1810, 1820, 1830, 1840, 1850, 1860)
  map_year <- max(available_years[available_years <= decade])
  file_path <- file.path(boundary_dir, sprintf("US_state_%d.geojson", map_year))
  print(paste("Loading boundary file:", file_path))
  print(paste("File exists:", file.exists(file_path)))
  if (!file.exists(file_path)) {
    print(paste("Error: File does not exist:", file_path))
    return(NULL)
  }
  # Read and transform to WGS84 (what Leaflet expects)
  states <- sf::st_read(file_path, quiet = TRUE)
  states <- sf::st_transform(states, 4326)  # 4326 is the EPSG code for WGS84
  print(paste("Loaded", nrow(states), "state boundaries"))
  print(paste("CRS after transformation:", sf::st_crs(states)$input))
  return(states)
}

# Custom theme settings
custom_theme <- bs_theme(
  version = 5,
  bootswatch = "lumen",
  primary = "#2c3e50",
  secondary = "#95a5a6",
  success = "#18bc9c",
  info = "#3498db",
  warning = "#f39c12",
  danger = "#e74c3c",
  base_font = "Source Sans Pro",
  heading_font = "Playfair Display",
  font_scale = 1.0
)

# UI
ui <- fluidPage(
  theme = custom_theme,
  # Initialize map_year input
  tags$script("$(document).ready(function() { Shiny.setInputValue('map_year', 1860); });"),
  tags$head(
    tags$link(
      href = "https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Source+Sans+Pro:wght@400;600&display=swap",
      rel = "stylesheet"
    ),
    tags$style("
      body {
        background-color: #f8f9fa;
        color: #2c3e50;
      }
      .container-fluid {
        max-width: 1400px;
        margin: 0 auto;
        padding: 2rem;
      }
      .title-panel {
        font-family: 'Playfair Display', serif;
        font-size: 3rem;
        font-weight: 700;
        text-align: center;
        margin: 2rem 0 3rem;
        color: #2c3e50;
        border-bottom: 3px solid #18bc9c;
        padding-bottom: 1rem;
      }
      .well, .card {
        background-color: #ffffff;
        border: none;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        padding: 1.5rem;
        margin-bottom: 1.5rem;
      }
      .tab-content {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      }
      .nav-tabs {
        border-bottom: 2px solid #e9ecef;
        margin-bottom: 1rem;
      }
      .nav-tabs .nav-link {
        color: #6c757d;
        border: none;
        padding: 1rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
      }
      .nav-tabs .nav-link.active {
        color: #18bc9c;
        border-bottom: 3px solid #18bc9c;
        background: none;
      }
      .nav-tabs .nav-link:hover {
        color: #18bc9c;
        border-bottom: 3px solid #18bc9c;
        background: none;
      }
      .form-group {
        margin-bottom: 1.5rem;
      }
      .form-label {
        font-weight: 600;
        color: #2c3e50;
        margin-bottom: 0.5rem;
      }
      .form-control {
        border-radius: 6px;
        border: 1px solid #e9ecef;
        padding: 0.5rem 1rem;
      }
      .btn {
        border-radius: 6px;
        padding: 0.5rem 1.25rem;
        font-weight: 600;
        transition: all 0.3s ease;
      }
      .btn-primary {
        background-color: #18bc9c;
        border-color: #18bc9c;
      }
      .btn-primary:hover {
        background-color: #159a80;
        border-color: #159a80;
      }
      .results-panel {
        margin-top: 2rem;
        padding: 1.5rem;
        border-radius: 8px;
        background-color: #ffffff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      }
      .results-panel h3 {
        color: #2c3e50;
        margin-bottom: 1.5rem;
      }
      #download_filtered_csv {
        margin-top: 1rem;
      }
      /* Leaflet custom styles */
      .leaflet-container {
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      }
      .leaflet-popup-content {
        font-family: 'Source Sans Pro', sans-serif;
        font-size: 14px;
        line-height: 1.6;
      }
      .leaflet-popup-content b {
        color: #2c3e50;
      }
      /* DataTable custom styles */
      .dataTables_wrapper {
        padding: 1rem;
        border-radius: 8px;
        background-color: #ffffff;
      }
      .dataTables_info, .dataTables_length, .dataTables_filter {
        font-size: 0.9rem;
        color: #6c757d;
      }
      table.dataTable thead th {
        background-color: #f8f9fa;
        color: #2c3e50;
        font-weight: 600;
        border-bottom: 2px solid #e9ecef;
      }
      table.dataTable tbody td {
        padding: 0.75rem;
        vertical-align: middle;
      }
      /* Custom slider styles */
      .irs--shiny .irs-bar {
        background: #18bc9c;
      }
      .irs--shiny .irs-from, .irs--shiny .irs-to, .irs--shiny .irs-single {
        background-color: #18bc9c;
      }
      .irs--shiny .irs-handle {
        border-color: #18bc9c;
      }
    ")
  ),
  
  tags$div(class = "title-panel", "Antebellum Divorce Petitions Database"),
  
  sidebarLayout(
    sidebarPanel(
      div(class = "card",
          h4("Filter Options", class = "mb-4", style = "color: #2c3e50; border-bottom: 2px solid #18bc9c; padding-bottom: 0.5rem;"),
          # Filter controls
          checkboxGroupInput('active_filters', 'Select Filters to Apply:',
                          choices = c(
                            'Reasoning' = 'reasoning',
                            'Party Accused' = 'party',
                            'Court Type' = 'court',
                            'Result' = 'result'
                          )),
          
          conditionalPanel(
            condition = "input.active_filters.includes('reasoning')",
            selectizeInput('reasoning_type', 'Reasoning Category',
                       choices = c('All' = 'all'),
                       multiple = TRUE,
                       options = list(
                         placeholder = 'Select reasons',
                         plugins = list('remove_button')
                       ))
          ),
          
          conditionalPanel(
            condition = "input.active_filters.includes('party')",
            selectInput('party_type', 'Party Accused',
                       choices = c(
                         'Husband Accused' = 'husband_accused',
                         'Wife Accused' = 'wife_accused'
                       ))
          ),
          
          conditionalPanel(
            condition = "input.active_filters.includes('court')",
            selectizeInput('court_type', 'Court Type',
                       choices = c('All' = 'all'),
                       multiple = TRUE,
                       options = list(
                         placeholder = 'Select courts',
                         plugins = list('remove_button')
                       ))
          ),
          
          conditionalPanel(
            condition = "input.active_filters.includes('result')",
            selectizeInput('result_type', 'Petition Result',
                       choices = c('All' = 'all'),
                       multiple = TRUE,
                       options = list(
                         placeholder = 'Select results',
                         plugins = list('remove_button')
                       ))
          )
      ),
      
      div(class = "card mt-4",
          h4("Time Period", class = "mb-4", style = "color: #2c3e50; border-bottom: 2px solid #18bc9c; padding-bottom: 0.5rem;"),
          # Time range slider
          sliderInput("year_range", "Year Range:",
                     min = 1800, max = 1860,
                     value = c(1800, 1860),
                     step = 10,  # Changed to 10-year steps to match boundary data
                     sep = "",
                     animate = list(interval = 2000),  # 2 second delay between animations
                     width = "100%")
      ),
      
      div(class = "card mt-4",
          h4("Table Controls", class = "mb-4", style = "color: #2c3e50; border-bottom: 2px solid #18bc9c; padding-bottom: 0.5rem;"),
          # Original table controls
          textInput('filter_col', 'Filter Column', value='', placeholder = 'Enter column name'),
          textInput('filter_val', 'Filter Value', value='', placeholder = 'Enter filter value'),
          numericInput('nrows', 'Rows per Page', value = 50, min = 1, max = 1000),
          actionButton('refresh', 'Refresh Data', class = "btn-primary w-100 mt-3"))
    ),
    
    mainPanel(
      tabsetPanel(
        tabPanel("Interactive Map", 
                div(class = "card",
                    leafletOutput("map", height = "600px")),
                div(class = "card mt-4",
                    h4("County Statistics", class = "mb-4", style = "color: #2c3e50; border-bottom: 2px solid #18bc9c; padding-bottom: 0.5rem;"),
                    DTOutput("county_stats")),
                
                # Conditional panel for filtered results
                conditionalPanel(
                  condition = "input.active_filters && input.active_filters.length > 0",
                  div(class = "results-panel",
                      h4("Filtered Results", class = "mb-4", style = "color: #2c3e50; border-bottom: 2px solid #18bc9c; padding-bottom: 0.5rem;"),
                      DTOutput("filtered_results_table"),
                      downloadButton('download_filtered_csv', 'Download Filtered Results', class = "btn-primary mt-3")))),
        tabPanel("Complete Database", 
                div(class = "card",
                    h4("All Petitions", class = "mb-4", style = "color: #2c3e50; border-bottom: 2px solid #18bc9c; padding-bottom: 0.5rem;"),
                    DTOutput("petitions_table"),
                    downloadButton('download_csv', 'Download All Petitions', class = "btn-primary mt-3")))
      )
    )
  )
)

# Server
server <- function(input, output, session) {
  conn <- dbConnect(RSQLite::SQLite(), db_path)
  onSessionEnded(function() dbDisconnect(conn))
  
  # Reactive states boundary data
  states_data <- reactive({
    # Use the end year of the range for the map boundaries
    year <- as.numeric(input$year_range[2])
    print(paste("Selected year for boundaries:", year))
    boundaries <- get_state_boundaries(year)
    if (is.null(boundaries)) {
      print("Warning: No boundary data loaded")
    }
    boundaries
  })
  
  # Observer to track when boundaries change and update the map
  observe({
    boundaries <- states_data()
    if (!is.null(boundaries)) {
      print(paste("Boundaries updated. Number of states:", nrow(boundaries)))
      # Update the map with new boundaries
      leafletProxy("map") %>%
        clearShapes() %>%
        addPolygons(
          data = boundaries,
          fillColor = NA,
          weight = 2,
          opacity = 1,
          color = "#000000",
          dashArray = NULL,
          fillOpacity = 0,
          layerId = ~paste("state", row.names(boundaries)),
          options = pathOptions(pane = "polygons", interactive = TRUE),
          highlightOptions = highlightOptions(
            weight = 3,
            color = "#333333",
            fillOpacity = 0.1,
            bringToFront = TRUE
          ),
          label = ~paste("State boundary from year", input$year_range[2])
        )
    }
  })
  
  # Initialize year range based on data
  observe({
    years <- dbGetQuery(conn, "SELECT MAX(CAST(year AS INTEGER)) as max_year FROM Petitions")
    updateSliderInput(session, "year_range",
                     min = 1800,
                     max = max(years$max_year, 1860),
                     value = c(1800, max(years$max_year, 1860)))
  })
  
  # Initialize reactive values
  query_data <- reactiveVal(NULL)
  map_data <- reactiveVal(NULL)
  
  # Populate reasoning choices dynamically
  observe({
    reasons <- dbGetQuery(conn, "SELECT DISTINCT reasoning FROM Reasoning ORDER BY reasoning")
    updateSelectInput(session, "reasoning_type",
                     choices = c('All' = 'all', setNames(reasons$reasoning, reasons$reasoning)))
  })
  
  # Populate court choices dynamically
  observe({
    courts <- dbGetQuery(conn, "SELECT DISTINCT court FROM Petitions WHERE court IS NOT NULL ORDER BY court")
    updateSelectInput(session, "court_type",
                     choices = c('All' = 'all', setNames(courts$court, courts$court)))
  })
  
  # Populate result choices dynamically
  observe({
    results <- dbGetQuery(conn, "SELECT DISTINCT result FROM Result ORDER BY result")
    updateSelectInput(session, "result_type",
                     choices = c('All' = 'all', setNames(results$result, results$result)))
  })
  
  # Function to get map data based on active filters
  get_map_data <- function() {
    if (is.null(input$year_range)) return(NULL)
    
    # Build WHERE clause for filters
    where_clauses <- c()
    
    # Check if we're filtering by multiple specific reasoning types
    multi_reasoning <- 'reasoning' %in% input$active_filters && 
                       length(input$reasoning_type) > 1 && 
                       !('all' %in% input$reasoning_type)
    
    if ('reasoning' %in% input$active_filters && length(input$reasoning_type) > 0 && !('all' %in% input$reasoning_type)) {
      reasoning_conditions <- paste(sprintf("r.reasoning = '%s'", input$reasoning_type), collapse = " OR ")
      where_clauses <- c(where_clauses, paste0("(", reasoning_conditions, ")"))
    }
    
    if ('party' %in% input$active_filters) {
      where_clauses <- c(where_clauses, sprintf("r.party_accused = '%s'", input$party_type))
    }
    
    if ('court' %in% input$active_filters && length(input$court_type) > 0 && !('all' %in% input$court_type)) {
      court_conditions <- paste(sprintf("p.court = '%s'", input$court_type), collapse = " OR ")
      where_clauses <- c(where_clauses, paste0("(", court_conditions, ")"))
    }
    
    if ('result' %in% input$active_filters && length(input$result_type) > 0 && !('all' %in% input$result_type)) {
      result_conditions <- paste(sprintf("res.result = '%s'", input$result_type), collapse = " OR ")
      where_clauses <- c(where_clauses, paste0("(", result_conditions, ")"))
    }
    
    filter_sql <- if (length(where_clauses) > 0) {
      paste("AND", paste(where_clauses, collapse = " AND "))
    } else {
      ""
    }
    
    # If multiple reasoning types selected, return data with reasoning categories
    if (multi_reasoning) {
      # Create a list of selected reasoning types for the query
      selected_reasons <- paste(sprintf("'%s'", input$reasoning_type), collapse = ", ")
      
      sql <- sprintf('
        WITH petition_reasoning_counts AS (
          SELECT 
            p.petition_id,
            p.county,
            p.state,
            p.court,
            p.year,
            COUNT(DISTINCT CASE WHEN r.reasoning IN (%s) THEN r.reasoning END) as matching_reasons_count,
            GROUP_CONCAT(DISTINCT CASE WHEN r.reasoning IN (%s) THEN r.reasoning END) as reasoning_list
          FROM Petitions p
          LEFT JOIN Petition_Reasoning_Lookup prl ON p.petition_id = prl.petition_id
          LEFT JOIN Reasoning r ON prl.reasoning_id = r.reasoning_id
          LEFT JOIN Result res ON p.petition_id = res.petition_id
          WHERE 1=1 
          AND CAST(COALESCE(p.year, "0") AS INTEGER) BETWEEN %d AND %d
          GROUP BY p.petition_id, p.county, p.state, p.court, p.year
          HAVING matching_reasons_count > 0
        )
        SELECT 
          g.*,
          CASE 
            WHEN prc.matching_reasons_count > 1 THEN "Multiple Selected Reasonings"
            ELSE prc.reasoning_list
          END as reasoning_type,
          COUNT(DISTINCT prc.petition_id) as value,
          GROUP_CONCAT(DISTINCT prc.court) as courts,
          GROUP_CONCAT(DISTINCT res.result) as results,
          GROUP_CONCAT(DISTINCT prc.year) as years,
          prc.reasoning_list as all_reasons
        FROM Geolocations g
        INNER JOIN petition_reasoning_counts prc ON g.county = prc.county AND g.state = prc.state
        LEFT JOIN Result res ON prc.petition_id = res.petition_id
        GROUP BY g.state, g.county, g.latitude, g.longitude, reasoning_type
      ', selected_reasons, selected_reasons, input$year_range[1], input$year_range[2])
    } else {
      # Original query for single or no reasoning filter
      sql <- sprintf('
        SELECT 
          g.*,
          COUNT(DISTINCT p.petition_id) as value,
          p.court as courts,
          GROUP_CONCAT(DISTINCT res.result) as results,
          GROUP_CONCAT(DISTINCT p.year) as years,
          GROUP_CONCAT(DISTINCT r.reasoning) as reasons
        FROM Geolocations g
        INNER JOIN Petitions p ON g.county = p.county AND g.state = p.state
        LEFT JOIN Petition_Reasoning_Lookup prl ON p.petition_id = prl.petition_id
        LEFT JOIN Reasoning r ON prl.reasoning_id = r.reasoning_id
        LEFT JOIN Result res ON p.petition_id = res.petition_id
        WHERE 1=1 
        AND CAST(COALESCE(p.year, "0") AS INTEGER) BETWEEN %d AND %d
        %s
        GROUP BY g.state, g.county, g.latitude, g.longitude
      ', input$year_range[1], input$year_range[2], filter_sql)
    }
    
    dbGetQuery(conn, sql)
  }
  
  # Update map when inputs change
  observe({
    data <- get_map_data()
    map_data(data)
  })
  
  # Render the map
  output$map <- renderLeaflet({
    data <- map_data()
    current_states <- states_data()
    
    if (is.null(data) || nrow(data) == 0) {
      map <- leaflet() %>%
             addProviderTiles(providers$CartoDB.Positron) %>%
             setView(lng = -85, lat = 34, zoom = 6)
      
      if (!is.null(current_states)) {
        map <- map %>%
          addMapPane("polygons", zIndex = 420) %>%
          addPolygons(data = current_states,
                     fillColor = NA,  # No fill color
                     weight = 2,      # Thinner lines
                     opacity = 1,
                     color = "#000000",   # Pure black
                     dashArray = NULL,
                     fillOpacity = 0,
                     options = pathOptions(pane = "polygons", interactive = TRUE))
      }
      return(map)
    }
    
    # Check if we have multiple reasoning types (indicated by reasoning_type column)
    has_reasoning_types <- "reasoning_type" %in% names(data)
    
    # Create base map
    map <- leaflet() %>%
      addProviderTiles(providers$CartoDB.Positron) %>%
      setView(lng = -85, lat = 34, zoom = 6) %>%
      addMapPane("polygons", zIndex = 420)
    
    # Add state boundaries if available
    if (!is.null(current_states)) {
      map <- map %>%
        addPolygons(
          data = current_states,
          fillColor = NA,        # No fill color
          weight = 2,            # Thinner lines
          opacity = 1,
          color = "#000000",     # Pure black
          dashArray = NULL,
          fillOpacity = 0,
          layerId = ~paste("state", row.names(current_states)),
          options = pathOptions(pane = "polygons", interactive = TRUE),
          highlightOptions = highlightOptions(
            weight = 3,          # Slightly thicker on hover
            color = "#333333",   # Darker gray on hover
            fillOpacity = 0.1,
            bringToFront = TRUE
          ),
          label = ~paste("State boundary from year", input$map_year)
        )
    } else {
      print("Warning: No state boundaries to display")
    }
    
    map  # Return the map object
    
    if (has_reasoning_types) {
      # Color by reasoning type, size by count
      unique_reasons <- unique(data$reasoning_type)
      
      # Check if we have "Multiple Selected Reasonings" category
      has_multiple <- "Multiple Selected Reasonings" %in% unique_reasons
      single_reasons <- unique_reasons[unique_reasons != "Multiple Selected Reasonings"]
      
      # Assign colors - use a distinct color for "Multiple"
      if (has_multiple) {
        # Use viridis colors for individual reasons, and a distinct color for multiple
        colors <- c(viridis(length(single_reasons)), "#FF6B6B")  # Red/coral for multiple
        names_order <- c(single_reasons, "Multiple Selected Reasonings")
        color_map <- setNames(colors, names_order)
      } else {
        colors <- viridis(length(unique_reasons))
        color_map <- setNames(colors, unique_reasons)
      }
      
      # Add color column to data based on reasoning type
      data$marker_color <- color_map[data$reasoning_type]
      
      # Add all markers at once with colors from the data
      map <- map %>%
        addCircleMarkers(
          data = data,
          lng = ~longitude,
          lat = ~latitude,
          radius = ~sqrt(value) * 3,
          fillColor = ~marker_color,
          color = "#2c3e50",
          weight = 1,
          opacity = 1,
          fillOpacity = 0.8,
          popup = ~paste0(
            "<div style='font-family: Source Sans Pro, sans-serif;'>",
            "<h6 style='margin: 0 0 8px; color: #2c3e50; border-bottom: 2px solid #18bc9c; padding-bottom: 4px;'>",
            county, ", ", state,
            "</h6>",
            "<strong>Reasoning:</strong> ", reasoning_type, "<br>",
            ifelse(!is.na(all_reasons) & reasoning_type == "Multiple Selected Reasonings", 
                   paste0("<em>(Contains: ", all_reasons, ")</em><br>"), ""),
            "<strong>Petitions:</strong> ", value, "<br>",
            "<strong>Years:</strong> ", years, "<br>",
            "<strong>Courts:</strong> ", courts, "<br>",
            "<strong>Results:</strong> ", results, "<br>",
            "<div style='margin-top: 8px; padding-top: 8px; border-top: 1px solid #e9ecef;'>",
            "<em>Click for more details below</em>",
            "</div>",
            "</div>"
          )
        )
      
      # Add custom legend for reasoning types with proper ordering
      legend_labels <- if (has_multiple) names_order else unique_reasons
      legend_colors <- if (has_multiple) colors else colors
      
      map <- map %>%
        addLegend("bottomright",
                  colors = legend_colors,
                  labels = legend_labels,
                  title = "Reasoning Type",
                  opacity = 1)
      
    } else {
      # Original behavior: color by count
      pal <- colorNumeric(
        palette = viridis(10),
        domain = data$value
      )
      
      map <- map %>%
        addCircleMarkers(
          data = data,
          lng = ~longitude,
          lat = ~latitude,
          radius = ~sqrt(value) * 3,
          fillColor = ~pal(value),
          color = "#2c3e50",
          weight = 1,
          opacity = 1,
          fillOpacity = 0.8,
          popup = ~paste0(
            "<div style='font-family: Source Sans Pro, sans-serif;'>",
            "<h6 style='margin: 0 0 8px; color: #2c3e50; border-bottom: 2px solid #18bc9c; padding-bottom: 4px;'>",
            county, ", ", state,
            "</h6>",
            "<strong>Total Petitions:</strong> ", value, "<br>",
            "<strong>Years:</strong> ", years, "<br>",
            "<strong>Courts:</strong> ", courts, "<br>",
            "<strong>Reasons:</strong> ", reasons, "<br>",
            "<strong>Results:</strong> ", results, "<br>",
            "<div style='margin-top: 8px; padding-top: 8px; border-top: 1px solid #e9ecef;'>",
            "<em>Click for more details below</em>",
            "</div>",
            "</div>"
          )
        ) %>%
        addLegend("bottomright",
                  pal = pal,
                  values = data$value,
                  title = "Count",
                  opacity = 1)
    }
    
    map
  })
  
  # Render county statistics table
  output$county_stats <- renderDT({
    data <- map_data()
    if (is.null(data) || nrow(data) == 0) {
      return(datatable(data.frame(
        County = character(0),
        State = character(0),
        Count = integer(0)
      )))
    }
    
    # Format data for display
    stats <- data[c("county", "state", "value", "courts", "reasons")]
    stats <- stats[order(-stats$value),]
    stats <- stats[stats$value > 0,]  # Only show counties with data
    
    # Build title based on active filters
    title_parts <- c()
    if ('reasoning' %in% input$active_filters && length(input$reasoning_type) > 0 && !('all' %in% input$reasoning_type)) {
      title_parts <- c(title_parts, sprintf("Reasoning: %s", paste(input$reasoning_type, collapse = ", ")))
    }
    if ('party' %in% input$active_filters) {
      title_parts <- c(title_parts, sprintf("Party: %s", input$party_type))
    }
    if ('court' %in% input$active_filters && length(input$court_type) > 0 && !('all' %in% input$court_type)) {
      title_parts <- c(title_parts, sprintf("Court: %s", paste(input$court_type, collapse = ", ")))
    }
    
    filter_text <- if (length(title_parts) > 0) {
      paste0(" (", paste(title_parts, collapse = ", "), ")")
    } else {
      ""
    }
    
    colnames(stats) <- c(
      "County",
      "State",
      sprintf("Petitions %d-%d%s", input$year_range[1], input$year_range[2], filter_text),
      "Courts",
      "Reasons"
    )
    
    datatable(stats,
              options = list(
                pageLength = 10,
                order = list(list(2, 'desc')),
                dom = 'Bfrtip',
                scrollX = TRUE,
                className = 'cell-border stripe hover'
              ),
              style = 'bootstrap4')
  })
  
  # Auto-load data on startup
  observeEvent(input$refresh, {
    filter_col <- input$filter_col
    filter_val <- input$filter_val
    sql <- 'SELECT p.*, GROUP_CONCAT(r.reasoning, ", ") as reasoning
            FROM Petitions p
            LEFT JOIN Petition_Reasoning_Lookup prl ON p.petition_id = prl.petition_id
            LEFT JOIN Reasoning r ON prl.reasoning_id = r.reasoning_id
            LEFT JOIN Court c ON p.court_id = c.court_id'
    
    has_filter <- FALSE
    if (nzchar(filter_col) && nzchar(filter_val)) {
      if (!grepl('^[A-Za-z0-9_]+$', filter_col)) {
        showNotification('Invalid filter column name', type='error')
        return()
      }
      sql <- paste0(sql, ' WHERE p.', filter_col, ' = ?')
      has_filter <- TRUE
    }
    
    sql <- paste0(sql, ' GROUP BY p.petition_id LIMIT ', as.integer(input$nrows))
    
    res <- tryCatch({
      if (has_filter) {
        dbGetQuery(conn, sql, params = list(filter_val))
      } else {
        dbGetQuery(conn, sql)
      }
    }, error = function(e) {
      showNotification(paste('Query error:', e$message), type='error')
      return(NULL)
    })
    
    query_data(res)
  })
  
  # Render petitions table
  output$petitions_table <- renderDT({
    df <- query_data()
    if (is.null(df)) return(NULL)
    datatable(df, 
             options = list(
               pageLength = input$nrows,
               scrollX = TRUE,
               dom = 'Bfrtip',
               className = 'cell-border stripe hover'
             ),
             style = 'bootstrap4')
  })
  
  # Download handler for complete dataset
  output$download_csv <- downloadHandler(
    filename = function() paste0('petitions_', Sys.Date(), '.csv'),
    content = function(file) {
      write.csv(query_data(), file, row.names = FALSE)
    }
  )
  
  # Function to get filtered results data
  get_filtered_results <- function() {
    if (is.null(input$year_range)) return(NULL)
    
    # Build WHERE clause for filters
    where_clauses <- c()
    
    if ('reasoning' %in% input$active_filters && length(input$reasoning_type) > 0 && !('all' %in% input$reasoning_type)) {
      reasoning_conditions <- paste(sprintf("r.reasoning = '%s'", input$reasoning_type), collapse = " OR ")
      where_clauses <- c(where_clauses, paste0("(", reasoning_conditions, ")"))
    }
    
    if ('party' %in% input$active_filters) {
      where_clauses <- c(where_clauses, sprintf("r.party_accused = '%s'", input$party_type))
    }
    
    if ('court' %in% input$active_filters && length(input$court_type) > 0 && !('all' %in% input$court_type)) {
      court_conditions <- paste(sprintf("p.court = '%s'", input$court_type), collapse = " OR ")
      where_clauses <- c(where_clauses, paste0("(", court_conditions, ")"))
    }
    
    if ('result' %in% input$active_filters && length(input$result_type) > 0 && !('all' %in% input$result_type)) {
      result_conditions <- paste(sprintf("res.result = '%s'", input$result_type), collapse = " OR ")
      where_clauses <- c(where_clauses, paste0("(", result_conditions, ")"))
    }
    
    filter_sql <- if (length(where_clauses) > 0) {
      paste("AND", paste(where_clauses, collapse = " AND "))
    } else {
      ""
    }
    
    # Base query with year filter
    sql <- sprintf('
      SELECT DISTINCT
        p.petition_id,
        p.year,
        p.county,
        p.state,
        GROUP_CONCAT(DISTINCT r.reasoning) as reasoning_list,
        GROUP_CONCAT(DISTINCT r.party_accused) as party_accused,
        p.court as court_name,
        GROUP_CONCAT(DISTINCT res.result) as result
      FROM Petitions p
      LEFT JOIN Petition_Reasoning_Lookup prl ON p.petition_id = prl.petition_id
      LEFT JOIN Reasoning r ON prl.reasoning_id = r.reasoning_id
      LEFT JOIN Result res ON p.petition_id = res.petition_id
      WHERE 1=1 
      AND CAST(COALESCE(p.year, "0") AS INTEGER) BETWEEN %d AND %d
      %s
      GROUP BY p.petition_id 
      ORDER BY p.year, p.state, p.county
    ', input$year_range[1], input$year_range[2], filter_sql)
    
    dbGetQuery(conn, sql)
  }
  
  # Render filtered results table
  output$filtered_results_table <- renderDT({
    data <- get_filtered_results()
    if (is.null(data)) return(NULL)
    
    # Rename columns for display
    colnames(data) <- c("Petition ID", "Year", "County", "State", "Reasoning", "Party Accused", "Court", "Result")
    
    datatable(data,
              options = list(
                pageLength = 25,
                scrollX = TRUE,
                dom = 'Bfrtip',
                className = 'cell-border stripe hover'
              ),
              style = 'bootstrap4')
  })
  
  # Download handler for filtered results
  output$download_filtered_csv <- downloadHandler(
    filename = function() {
      filter_text <- paste0(input$active_filters, collapse = "_")
      paste0('petitions_filtered_', filter_text, '_', Sys.Date(), '.csv')
    },
    content = function(file) {
      write.csv(get_filtered_results(), file, row.names = FALSE)
    }
  )
}

shinyApp(ui, server)