library(shiny)

ui <- fluidPage(
  titlePanel("Test App"),
  mainPanel(
    h1("Hello World")
  )
)

server <- function(input, output, session) {
}

shinyApp(ui = ui, server = server)