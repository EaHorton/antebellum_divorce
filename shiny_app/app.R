library(shiny)
library(DBI)
library(RSQLite)
library(DT)
library(sf)
library(leaflet)
library(leaflet.extras)
library(viridis)

# Path to the SQLite DB and boundary data (relative to repo root)
db_path <- file.path('..', 'dv_petitions.db')
states_geojson <- file.path('..', 'data', 'boundaries', 'states_1860.geojson')

# UI
ui <- fluidPage(
  titlePanel('Antebellum Divorce Petitions'),
  
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
    sql <- switch(input$viz_type,
      "count" = '
        SELECT g.*, COUNT(p.petition_id) as value
        FROM Geolocations g
        LEFT JOIN Petitions p ON g.county = p.county AND g.state = p.state
        GROUP BY g.county, g.state
      ',
      "reasoning" = sprintf('
        SELECT g.*, COUNT(p.petition_id) as value
        FROM Geolocations g
        LEFT JOIN Petitions p ON g.county = p.county AND g.state = p.state
        LEFT JOIN Petition_Reasoning_Lookup prl ON p.petition_id = prl.petition_id
        LEFT JOIN Reasoning r ON prl.reasoning_id = r.reasoning_id
        WHERE %s
        GROUP BY g.county, g.state
      ', if(input$reasoning_type == 'all') '1=1' else sprintf("r.reasoning = '%s'", input$reasoning_type)),
      "party" = sprintf('
        SELECT g.*, COUNT(p.petition_id) as value
        FROM Geolocations g
        LEFT JOIN Petitions p ON g.county = p.county AND g.state = p.state
        LEFT JOIN Petition_Reasoning_Lookup prl ON p.petition_id = prl.petition_id
        LEFT JOIN Reasoning r ON prl.reasoning_id = r.reasoning_id
        WHERE r.party_accused = "%s"
        GROUP BY g.county, g.state
      ', input$party_type),
      "results" = sprintf('
        SELECT g.*, COUNT(p.petition_id) as value
        FROM Geolocations g
        LEFT JOIN Petitions p ON g.county = p.county AND g.state = p.state
        WHERE LOWER(p.result) LIKE "%%%s%%"
        GROUP BY g.county, g.state
      ', input$result_type)
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
    if (is.null(data)) return(NULL)
    
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
                 color = "black",
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
    if (is.null(data)) return(NULL)
    
    # Format data for display
    stats <- data[c("county", "state", "value")]
    stats <- stats[order(-stats$value),]
    colnames(stats) <- c("County", "State", "Count")
    
    datatable(stats,
              options = list(pageLength = 10,
                           order = list(list(2, 'desc'))))
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
