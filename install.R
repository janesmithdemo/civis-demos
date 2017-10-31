install.packages(c('devtools', 
                   'shiny', 
                   'shinydashboard',
                   'RColorBrewer', 
                   'ggplot2', 
                   'gsheet'), 
                 repos='https://cran.rstudio.com/')

library(devtools)
devtools::install_github("jcheng5/bubbles")
