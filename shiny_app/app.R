library(shiny)
library(DBI)
library(RSQLite)
library(DT)
library(sf)
library(leaflet)
library(leaflet.extras)
library(viridis)
library(bslib)

# Path to the SQLite DB and boundary data (relative to repo root)
db_path <- file.path('..', 'dv_petitions.db')
states_geojson <- file.path('..', 'data', 'boundaries', 'states_1860.geojson')

# UI
ui <- fluidPage(
  theme = bs_theme(version = 5, bootswatch = "yeti"),
  tags$head(
    tags$link(
      href = "https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&display=swap",
      rel = "stylesheet"
    ),
    tags$style("
      body {
        background-color: #f5f5f0;
      }
      .container-fluid {
        background-color: #f5f5f0;
      }
      .title-panel {
        font-family: 'Playfair Display', serif;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 1.5rem;
        color: #2c3e50;
      }
      .well {
        background-color: #ffffff;
        border: 1px solid #e3e3e3;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
      }
      .tab-content {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 4px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
      }
      .results-panel {
        margin-top: 20px;
        padding: 15px;
        border-radius: 4px;
        background-color: #ffffff;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
      }
      #download_filtered_csv {
        margin-top: 10px;
      }
    ")
  ),
  tags$div(class = "title-panel", "Antebellum Divorce Petitions"),
  
  sidebarLayout(
    sidebarPanel(
      # Filter controls
      checkboxGroupInput('active_filters', 'Select Filters to Apply:',
                        choices = c(
                          'Reasoning' = 'reasoning',
                          'Party Accused' = 'party',
                          'Petition Result' = 'results'
                        )),
      
      conditionalPanel(
        condition = "input.active_filters.includes('reasoning')",
        selectInput('reasoning_type', 'Reasoning Category',
                   choices = c('All' = 'all'))  # Will be populated dynamically
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
        condition = "input.active_filters.includes('results')",
        selectInput('result_type', 'Petition Result',
                   choices = c(
                     'Granted' = 'granted',
                     'Rejected' = 'rejected'
                   ))
      ),
      
      hr(),
      
      # Time range slider
      sliderInput("year_range", "Year Range:",
                 min = 1800, max = 1860,
                 value = c(1800, 1860),
                 step = 1,
                 sep = "",
                 animate = TRUE),
      
      hr(),
      
      # Original table controls
      textInput('filter_col', 'Filter table column (optional)', value=''),
      textInput('filter_val', 'Filter value (optional)', value=''),
      numericInput('nrows', 'Table rows per page', value = 50, min = 1, max = 1000),
      actionButton('refresh', 'Refresh')
    ),
    
    mainPanel(
      tabsetPanel(
        tabPanel("Map", 
                leafletOutput("map", height = "600px"),
                hr(),
                DTOutput("county_stats"),
                
                # Conditional panel for filtered results
                conditionalPanel(
                  condition = "input.active_filters && input.active_filters.length > 0",
                  div(class = "results-panel",
                    h3("Filtered Results", class = "title-panel", style = "font-size: 1.5rem; margin-top: 0;"),
                    DTOutput("filtered_results_table"),
                    downloadButton('download_filtered_csv', 'Download Filtered Results')
                  )
                )),
        tabPanel("All Petitions", 
                DTOutput("petitions_table"),
                downloadButton('download_csv', 'Download All Petitions'))
      )
    )
  )
)

# Server
server <- function(input, output, session) {
  conn <- dbConnect(RSQLite::SQLite(), db_path)
  onSessionEnded(function() dbDisconnect(conn))
  
  # Load states boundary data
  states <- st_read(states_geojson, quiet = TRUE)
  
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
  
  # Function to get map data based on active filters
  get_map_data <- function() {
    if (is.null(input$year_range)) return(NULL)
    
    # Base query with year filter
    base_sql <- sprintf('
      SELECT g.*, COUNT(DISTINCT p.petition_id) as value
      FROM Geolocations g
      LEFT JOIN Petitions p ON g.county = p.county AND g.state = p.state
      LEFT JOIN Petition_Reasoning_Lookup prl ON p.petition_id = prl.petition_id
      LEFT JOIN Reasoning r ON prl.reasoning_id = r.reasoning_id
      WHERE p.petition_id IS NOT NULL 
      AND CAST(COALESCE(p.year, "0") AS INTEGER) BETWEEN %d AND %d
    ', input$year_range[1], input$year_range[2])
    
    # Build WHERE clause based on active filters
    where_clauses <- c()
    
    if ('reasoning' %in% input$active_filters && input$reasoning_type != 'all') {
      where_clauses <- c(where_clauses, sprintf("r.reasoning = '%s'", input$reasoning_type))
    }
    
    if ('party' %in% input$active_filters) {
      where_clauses <- c(where_clauses, sprintf("r.party_accused = '%s'", input$party_type))
    }
    
    if ('results' %in% input$active_filters) {
      where_clauses <- c(where_clauses, sprintf("LOWER(p.result) LIKE '%%%s%%'", input$result_type))
    }
    
    # Combine all conditions
    where_clause <- if (length(where_clauses) > 0) {
      paste("AND", paste(where_clauses, collapse = " AND "))
    } else {
      ""
    }
    
    # Complete query
    sql <- paste0(base_sql, where_clause, " GROUP BY g.county, g.state")
    
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
    if (is.null(data) || nrow(data) == 0) {
      return(leaflet() %>%
             addProviderTiles(providers$CartoDB.Positron) %>%
             setView(lng = -85, lat = 34, zoom = 6) %>%
             addPolygons(data = states,
                        fillColor = "white",
                        weight = 2,
                        opacity = 1,
                        color = "#008cba",
                        fillOpacity = 0.1))
    }
    
    # Create color palette based on values
    pal <- colorNumeric(
      palette = viridis(10),
      domain = data$value
    )
    
    # Create the map
    leaflet() %>%
      addProviderTiles(providers$CartoDB.Positron) %>%
      setView(lng = -85, lat = 34, zoom = 6) %>%
      addPolygons(data = states,
                 fillColor = "white",
                 weight = 2,
                 opacity = 1,
                 color = "#008cba",
                 fillOpacity = 0.1) %>%
      addCircleMarkers(
        data = data,
        lng = ~longitude,
        lat = ~latitude,
        radius = ~sqrt(value) * 3,
        fillColor = ~pal(value),
        color = "black",
        weight = 1,
        opacity = 1,
        fillOpacity = 0.7,
        popup = ~paste0(
          "<b>", county, ", ", state, "</b><br>",
          "Count: ", value
        )
      ) %>%
      addLegend("bottomright",
                pal = pal,
                values = data$value,
                title = "Count",
                opacity = 1)
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
    stats <- data[c("county", "state", "value")]
    stats <- stats[order(-stats$value),]
    stats <- stats[stats$value > 0,]  # Only show counties with data
    
    # Build title based on active filters
    title_parts <- c()
    if ('reasoning' %in% input$active_filters && input$reasoning_type != 'all') {
      title_parts <- c(title_parts, sprintf("Reasoning: %s", input$reasoning_type))
    }
    if ('party' %in% input$active_filters) {
      title_parts <- c(title_parts, sprintf("Party: %s", input$party_type))
    }
    if ('results' %in% input$active_filters) {
      title_parts <- c(title_parts, sprintf("Result: %s", input$result_type))
    }
    
    filter_text <- if (length(title_parts) > 0) {
      paste0(" (", paste(title_parts, collapse = ", "), ")")
    } else {
      ""
    }
    
    colnames(stats) <- c("County", "State", sprintf("Count %d-%d%s", 
                                                   input$year_range[1], 
                                                   input$year_range[2],
                                                   filter_text))
    
    datatable(stats,
              options = list(
                pageLength = 10,
                order = list(list(2, 'desc')),
                dom = 'Bfrtip'
              ),
              class = 'cell-border stripe',
              style = 'bootstrap')
  })

  observeEvent(input$refresh, {
    # build query with optional filter - include reasoning via LEFT JOIN
    filter_col <- input$filter_col
    filter_val <- input$filter_val
    sql <- 'SELECT p.*, GROUP_CONCAT(r.reasoning, ", ") as reasoning
            FROM Petitions p
            LEFT JOIN Petition_Reasoning_Lookup prl ON p.petition_id = prl.petition_id
            LEFT JOIN Reasoning r ON prl.reasoning_id = r.reasoning_id'
    has_filter <- FALSE
    if (nzchar(filter_col) && nzchar(filter_val)) {
      # basic validation: allow only alphanum + underscore
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

  output$petitions_table <- renderDT({
    df <- query_data()
    if (is.null(df)) return(NULL)
    datatable(df, options = list(pageLength = input$nrows, scrollX = TRUE))
  })

  output$download_csv <- downloadHandler(
    filename = function() paste0('petitions_', Sys.Date(), '.csv'),
    content = function(file) {
      write.csv(query_data(), file, row.names = FALSE)
    }
  )

  # Function to get filtered results data
  get_filtered_results <- function() {
    if (is.null(input$year_range)) return(NULL)
    
    # Base query with year filter
    base_sql <- sprintf('
      SELECT DISTINCT
        p.petition_id,
        p.year,
        p.county,
        p.state,
        GROUP_CONCAT(DISTINCT r.reasoning) as reasoning_list,
        GROUP_CONCAT(DISTINCT r.party_accused) as party_accused,
        p.result
      FROM Petitions p
      LEFT JOIN Petition_Reasoning_Lookup prl ON p.petition_id = prl.petition_id
      LEFT JOIN Reasoning r ON prl.reasoning_id = r.reasoning_id
      WHERE p.petition_id IS NOT NULL 
      AND CAST(COALESCE(p.year, "0") AS INTEGER) BETWEEN %d AND %d
    ', input$year_range[1], input$year_range[2])
    
    # Build WHERE clause based on active filters
    where_clauses <- c()
    
    if ('reasoning' %in% input$active_filters && input$reasoning_type != 'all') {
      where_clauses <- c(where_clauses, sprintf("r.reasoning = '%s'", input$reasoning_type))
    }
    
    if ('party' %in% input$active_filters) {
      where_clauses <- c(where_clauses, sprintf("r.party_accused = '%s'", input$party_type))
    }
    
    if ('results' %in% input$active_filters) {
      where_clauses <- c(where_clauses, sprintf("LOWER(p.result) LIKE '%%%s%%'", input$result_type))
    }
    
    # Combine all conditions
    where_clause <- if (length(where_clauses) > 0) {
      paste("AND", paste(where_clauses, collapse = " AND "))
    } else {
      ""
    }
    
    # Complete query
    sql <- paste0(base_sql, where_clause, " GROUP BY p.petition_id ORDER BY p.year, p.state, p.county")
    
    dbGetQuery(conn, sql)
  }
  
  # Render filtered results table
  output$filtered_results_table <- renderDT({
    data <- get_filtered_results()
    if (is.null(data)) return(NULL)
    
    # Rename columns for display
    colnames(data) <- c("Petition ID", "Year", "County", "State", "Reasoning", "Party Accused", "Result")
    
    datatable(data,
              options = list(
                pageLength = 25,
                scrollX = TRUE,
                dom = 'Bfrtip'
              ),
              class = 'cell-border stripe',
              style = 'bootstrap')
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

  # Auto-load data on startup
  observeEvent(TRUE, {
    # build query with optional filter - include reasoning via LEFT JOIN
    filter_col <- input$filter_col
    filter_val <- input$filter_val
    sql <- 'SELECT p.*, GROUP_CONCAT(r.reasoning, ", ") as reasoning
            FROM Petitions p
            LEFT JOIN Petition_Reasoning_Lookup prl ON p.petition_id = prl.petition_id
            LEFT JOIN Reasoning r ON prl.reasoning_id = r.reasoning_id'
    has_filter <- FALSE
    if (nzchar(filter_col) && nzchar(filter_val)) {
      # basic validation: allow only alphanum + underscore
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
  }, once = TRUE, ignoreNULL = FALSE)
}

shinyApp(ui, server)
