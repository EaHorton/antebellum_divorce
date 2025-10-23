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
    ")
  ),
  tags$div(class = "title-panel", "Antebellum Divorce Petitions"),
  
  sidebarLayout(
    sidebarPanel(
      selectInput('viz_type', 'Visualization Type', 
                 choices = c(
                   'Petition Count' = 'count',
                   'Reasoning Analysis' = 'reasoning',
                   'Party Accused' = 'party',
                   'Results' = 'results'
                 )),
      
      conditionalPanel(
        condition = "input.viz_type == 'reasoning'",
        selectInput('reasoning_type', 'Reasoning Category',
                   choices = c('All' = 'all'))  # Will be populated dynamically
      ),
      
      conditionalPanel(
        condition = "input.viz_type == 'party'",
        selectInput('party_type', 'Party Accused',
                   choices = c(
                     'Husband Accused' = 'husband_accused',
                     'Wife Accused' = 'wife_accused'
                   ))
      ),
      
      conditionalPanel(
        condition = "input.viz_type == 'results'",
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
                DTOutput("county_stats")),
        tabPanel("Data Table", 
                DTOutput("petitions_table"),
                downloadButton('download_csv', 'Download CSV'))
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
  
  # Function to get map data based on visualization type
  get_map_data <- function() {
    if (is.null(input$year_range)) return(NULL)
    year_filter <- sprintf("AND CAST(COALESCE(p.year, '0') AS INTEGER) BETWEEN %d AND %d", input$year_range[1], input$year_range[2])
    
    sql <- switch(input$viz_type,
      "count" = sprintf('
        SELECT g.*, COUNT(p.petition_id) as value
        FROM Geolocations g
        LEFT JOIN Petitions p ON g.county = p.county AND g.state = p.state
        WHERE p.petition_id IS NOT NULL %s
        GROUP BY g.county, g.state
      ', year_filter),
      "reasoning" = sprintf('
        SELECT g.*, COUNT(p.petition_id) as value
        FROM Geolocations g
        LEFT JOIN Petitions p ON g.county = p.county AND g.state = p.state
        LEFT JOIN Petition_Reasoning_Lookup prl ON p.petition_id = prl.petition_id
        LEFT JOIN Reasoning r ON prl.reasoning_id = r.reasoning_id
        WHERE p.petition_id IS NOT NULL %s AND %s
        GROUP BY g.county, g.state
      ', year_filter, if(input$reasoning_type == 'all') '1=1' else sprintf("r.reasoning = '%s'", input$reasoning_type)),
      "party" = sprintf('
        SELECT g.*, COUNT(p.petition_id) as value
        FROM Geolocations g
        LEFT JOIN Petitions p ON g.county = p.county AND g.state = p.state
        LEFT JOIN Petition_Reasoning_Lookup prl ON p.petition_id = prl.petition_id
        LEFT JOIN Reasoning r ON prl.reasoning_id = r.reasoning_id
        WHERE p.petition_id IS NOT NULL %s AND r.party_accused = "%s"
        GROUP BY g.county, g.state
      ', year_filter, input$party_type),
      "results" = sprintf('
        SELECT g.*, COUNT(p.petition_id) as value
        FROM Geolocations g
        LEFT JOIN Petitions p ON g.county = p.county AND g.state = p.state
        WHERE p.petition_id IS NOT NULL %s AND LOWER(p.result) LIKE "%%%s%%"
        GROUP BY g.county, g.state
      ', year_filter, input$result_type)
    )
    
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
    colnames(stats) <- c("County", "State", sprintf("Count (%d-%d)", input$year_range[1], input$year_range[2]))
    
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
