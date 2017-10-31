FROM civisanalytics/datascience-r:2.0.0

RUN apt-get update && apt-get install -y \
    git

RUN echo 'options(repos = c(CRAN = "https://cran.rstudio.com/"), download.file.method = "libcurl")' >> /etc/R/Rprofile.site
COPY ./requirements.txt /requirements.txt
RUN Rscript -e "packages <- readLines('/requirements.txt'); install.packages(packages)"

RUN Rscript -e "devtools::install_github('jcheng5/bubbles')"

# Copy the app into the image
COPY . /src/app

# Shiny will serve via port 3838
EXPOSE 3838

# Serve the App!
CMD ["R", "-e", "shiny::runApp(appDir='/src/app', port=3838, host='0.0.0.0')"]
