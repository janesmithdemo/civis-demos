import os
import civis
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Get database credentials
DATABASE_CRED = os.environ['DATABASE_CRED_NAME']
TABLE = os.environ['TABLE']

# Read the data from the previous job
df = civis.io.read_civis_sql(
    sql="SELECT * FROM {TABLE}_civis_studio_demo",
    database=DATABASE_CRED,
    use_pandas=True
)

# Set the style
plt.style.use('seaborn')
sns.set_palette("husl")

# Create the plot
plt.figure(figsize=(10, 6))

# Create grouped bar plot
ax = sns.barplot(data=df.melt(id_vars=['species']), 
                x='species',
                y='value',
                hue='variable')

# Customize the plot
plt.title('Average Petal Length and Sepal Width by Species', pad=20)
plt.xlabel('Species')
plt.ylabel('Measurement (cm)')

# Rotate x-axis labels for better readability
plt.xticks(rotation=45)

# Adjust layout
plt.tight_layout()

# Save the plot as a file in Civis Platform
plt.savefig('iris_plot.png')
file_id = civis.io.file_to_civis('iris_plot.png', 'Iris Measurements Plot')