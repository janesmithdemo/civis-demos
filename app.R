library(shiny)
library(shinydashboard)
library(tidyr)
library(dplyr)
library(ggplot2)
library(RColorBrewer)
library(gsheet)
library(bubbles)

# 1 = beginner, 2 = intermediate, 3 = advanced, 4 = expert
df <- gsheet2tbl("https://docs.google.com/spreadsheets/d/1grp7lbnPc1SWTxPTAt8BMK8XYsTkEnt3KZ5Z1Qmhb0s/edit?usp=sharing")
df_t <- df %>%
  gather(key = User, value = Proficiency, 2:ncol(.))

df_learn <- gsheet2tbl("https://docs.google.com/spreadsheets/d/1DttBDc9n8XN9nW89RWbeU-H0197FkcL5MuDfsoyDeWo/edit?usp=sharing")
df_learn_t <- df_learn %>%
  gather(key = User, value = Flag, 2:ncol(.))
  
for (i in c(1:nrow(df_t))) {
  if (df_t$Proficiency[i] > 1) {
    df_t <- df_t %>%
      union_all(tibble(
        Skill = rep(df_t$Skill[i],df_t$Proficiency[i] - 1),
        User = rep(df_t$User[i],df_t$Proficiency[i] - 1),
        Proficiency = c(1:(df_t$Proficiency[i] - 1))
      ))
  }
}

ui <- dashboardPage(
  dashboardHeader(title = 'Civis Hive Mind',
                  titleWidth = 250
  ),
  dashboardSidebar(
    width = 250,
    sidebarMenu(
      menuItem("Profile", tabName = "profile", icon = icon("user")),
      menuItem("Civis (teach)", tabName = "civis_teach", icon = icon("group")),
      menuItem("Civis (learn)", tabName = "civis_learn", icon = icon("group")),
      menuItem("Learn", tabName = "learn", icon = icon("mortar-board"))
    )
  ),
  dashboardBody(
    style = "background-color: #ffffff;",
    tabItems(
      tabItem(tabName = "profile",
              fluidRow(
                column(
                  width = 4,
                  wellPanel(
                    selectInput(inputId = 'user', 
                                label = 'Select User:', 
                                choices = colnames(df)[2:length(colnames(df))], 
                                selected = NULL, multiple = FALSE,
                                selectize = FALSE, width = NULL, size = NULL)
                    
                  )
                )
              ),
              fluidRow(
                plotOutput("radar", 
                           width = "100%",
                           height = "600px") 
              )
      ),
      
      tabItem(tabName = "civis_teach",
              bubblesOutput("civis_teach", 
                           width = "100%",
                           height = "600px"
              ) 
      ),
      
      tabItem(tabName = "civis_learn",
              bubblesOutput("civis_learn", 
                            width = "100%",
                            height = "600px"
              ) 
      ),
      
      tabItem(tabName = "learn",
              fluidRow(
                column(
                  width = 4,
                  wellPanel(
                    selectInput(inputId = 'skill', 
                                label = 'Select Skill:', 
                                choices = df$Skill, 
                                selected = NULL, multiple = FALSE,
                                selectize = FALSE, width = NULL, size = NULL)
                    
                  )
                )
              ),
              fluidRow(
                column(
                  width = 3,
                  align = "center",
                  h2("Beginner"),
                  bubblesOutput("bubble_beginner",
                                width = "100%")
                ),
                column(
                  width = 3,
                  align = "center",
                  h2("Intermediate"),
                  bubblesOutput("bubble_intermediate",
                                width = "100%")
                ),
                column(
                  width = 3,
                  align = "center",
                  h2("Advanced"),
                  bubblesOutput("bubble_advanced",
                                width = "100%")
                ),column(
                  width = 3,
                  align = "center",
                  h2("Expert"),
                  bubblesOutput("bubble_expert",
                                width = "100%")
                )
              )
      )
    )
  )
)

server <- function(input, output) {
  output$radar <- renderPlot({

    df_draw <- df_t %>%
      filter(User == input$user & Proficiency >= 1)
    
    ggplot(data=df_draw,aes(x=Skill,y=Proficiency,fill=Proficiency))+
      geom_tile(colour="white",size=0.3)+
      scale_fill_gradientn(colours=c("#86CFE8","#006082"))+
      coord_polar()+xlab("")+ylab("") + 
      theme(panel.background = element_rect(
        fill = "white", colour = "white", size = 0.5, 
        linetype = "solid"),
        panel.grid = element_blank(), 
        panel.grid.minor = element_line(
          size = 0.25, linetype = 'solid', colour = "white"),
        legend.position = "none",
        axis.text.y = element_blank(),
        axis.ticks.y = element_blank(),
        axis.text.x = element_text(size=10,
                                   family="Lato",
                                   face="bold"))
  })
  
  output$civis_teach <- renderBubbles({
    df_civis_teach <- df_t %>%
      filter(Proficiency >= 1) %>%
      group_by(Skill) %>%
      summarize(Value = n())
      
    bubbles(value = df_civis_teach$Value,
            label = df_civis_teach$Skill,
            color = rainbow(nrow(df_civis_teach), alpha=NULL)[sample(nrow(df_civis_teach))])
  })
  
  output$civis_learn <- renderBubbles({
    df_civis_learn <- df_learn_t %>%
      filter(Flag == 1) %>%
      group_by(Skill) %>%
      summarize(Value = n())
    
    bubbles(value = df_civis_learn$Value,
            label = df_civis_learn$Skill,
            color = rainbow(nrow(df_civis_learn), alpha=NULL)[sample(nrow(df_civis_learn))])
  })
  
  output$bubble_beginner <- renderBubbles({
    df_beginners <- df_t %>%
      filter(Skill == input$skill & Proficiency == 1) %>%
      mutate(Value = 1)
    
    if (nrow(df_beginners) > 0) {
      bubbles(value = df_beginners$Value,
            label = df_beginners$User,
            color = "#86CFE8")
    }
  })
  output$bubble_intermediate <- renderBubbles({
    df_intermediates <- df_t %>%
      filter(Skill == input$skill & Proficiency == 2) %>%
      mutate(Value = 1)
    
    if (nrow(df_intermediates) > 0) {
      bubbles(value = df_intermediates$Value,
            label = df_intermediates$User,
            color = "#4DC0E8")
    }
  })
  output$bubble_advanced <- renderBubbles({
    df_advanceds <- df_t %>%
      filter(Skill == input$skill & Proficiency == 3) %>%
      mutate(Value = 1)
    
    if (nrow(df_advanceds) > 0) {
      bubbles(value = df_advanceds$Value,
            label = df_advanceds$User,
            color = "#0194D3")
    }
  })
  output$bubble_expert <- renderBubbles({
    df_experts <- df_t %>%
      filter(Skill == input$skill & Proficiency == 4) %>%
      mutate(Value = 1)
    
    if (nrow(df_experts) > 0) {
      bubbles(value = df_experts$Value,
            label = df_experts$User,
            color = "#006082")
    }
  })
}

shinyApp(ui = ui, server = server)
