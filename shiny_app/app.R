# Minimal R Shiny app for exploring dv_petitions.db
# Requirements: R with packages: shiny, DBI, RSQLite, DT, ggplot2

library(shiny)
library(DBI)
library(RSQLite)
library(DT)
library(ggplot2)

# DB path (default to repo root dv_petitions.db). You can override with env DV_DB_PATH
default_db <- normalizePath(file.path('..', 'dv_petitions.db'), winslash = '/', mustWork = FALSE)
DB_PATH <- Sys.getenv('DV_DB_PATH', default_db)

# Connect on app start
conn <- dbConnect(RSQLite::SQLite(), DB_PATH)

# Helper: get table names
tbls <- dbListTables(conn)

ui <- fluidPage(
  titlePanel('Antebellum Divorce — DB Explorer'),
  sidebarLayout(
    sidebarPanel(
      selectInput('table', 'Choose table', choices = tbls, selected = tbls[1]),
      numericInput('nrows', 'Rows to preview', value = 100, min = 1, max = 10000, step = 50),
      textInput('where', 'Filter (WHERE clause, without "WHERE")', value = ''),
      actionButton('refresh', 'Refresh preview'),
      hr(),
      downloadButton('download_csv', 'Download preview as CSV'),
      hr(),
      tags$small('DB path:'),
      tags$div(style='word-break:break-all', DB_PATH)
    ),

    mainPanel(
      tabsetPanel(
        tabPanel('Table preview', DTOutput('table_preview')),
        tabPanel('SQL console',
                 textAreaInput('sql', 'SQL query', rows = 6, value = paste0('SELECT * FROM ', tbls[1], ' LIMIT 100')),
                 actionButton('run_sql', 'Run SQL'),
                 verbatimTextOutput('sql_msg'),
                 DTOutput('sql_res')
        ),
        tabPanel('Visualization',
                 uiOutput('viz_ui'),
                 plotOutput('viz_plot')
        )
      )
    )
  )
)

server <- function(input, output, session) {
  # reactive to get column names for selected table
  table_cols <- reactive({
    req(input$table)
    dbListFields(conn, input$table)
  })

  preview_data <- eventReactive(input$refresh, {
    req(input$table)
    where_clause <- if (nzchar(trimws(input$where))) paste0(' WHERE ', input$where) else ''
    sql <- sprintf('SELECT * FROM %s %s LIMIT %d', DBI::dbQuoteIdentifier(conn, input$table), where_clause, input$nrows)
    tryCatch({
      dbGetQuery(conn, sql)
    }, error = function(e) {
      showNotification(paste('Preview query error:', e$message), type='error')
      NULL
    })
  }, ignoreNULL = FALSE)

  output$table_preview <- renderDT({
    df <- preview_data()
    datatable(df, options = list(pageLength = 10, scrollX = TRUE))
  })

  output$download_csv <- downloadHandler(
    filename = function() paste0(input$table, '_preview.csv'),
    content = function(file) {
      df <- preview_data()
      write.csv(df, file, row.names = FALSE)
    }
  )

  observeEvent(input$run_sql, {
    query <- input$sql
    if (!nzchar(trimws(query))) {
      output$sql_msg <- renderText('Empty query')
      output$sql_res <- renderDT(NULL)
      return()
    }
    res <- tryCatch({
      df <- dbGetQuery(conn, query)
      output$sql_msg <- renderText('Query OK')
      output$sql_res <- renderDT(datatable(df, options = list(pageLength = 10, scrollX = TRUE)))
      NULL
    }, error = function(e) {
      output$sql_msg <- renderText(paste('SQL error:', e$message))
      output$sql_res <- renderDT(NULL)
      NULL
    })
  })

  output$viz_ui <- renderUI({
    cols <- table_cols()
    if (is.null(cols) || length(cols) == 0) return(NULL)
    tagList(
      selectInput('viz_x', 'X column', choices = cols, selected = cols[1]),
      selectInput('viz_y', 'Aggregate (count/none)', choices = c('count', cols), selected = 'count')
    )
  })

  output$viz_plot <- renderPlot({
    req(input$table, input$viz_x)
    df <- dbGetQuery(conn, sprintf('SELECT %s FROM %s', DBI::dbQuoteIdentifier(conn, input$viz_x), DBI::dbQuoteIdentifier(conn, input$table)))
    if (nrow(df) == 0) return()
    if (input$viz_y == 'count') {
      gg <- ggplot(df, aes_string(x = input$viz_x)) + geom_bar() + theme_minimal() + coord_flip()
    } else {
      gg <- ggplot(df, aes_string(x = input$viz_x, y = input$viz_y)) + geom_col() + theme_minimal()
    }
    print(gg)
  })

  session$onSessionEnded(function() {
    dbDisconnect(conn)
  })
}

shinyApp(ui, server)
