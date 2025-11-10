import os
import civis
import pandas as pd

# Get database credentials from environment variables
DATABASE_CRED = os.environ['DATABASE_CRED_NAME']
TABLE = os.environ['TABLE']

# SQL query
query = f"""
SELECT
    avg(petallength) petallength,
    avg(sepalwidth) sepalwidth,
    species
FROM
    {TABLE}
GROUP BY
    species
"""

# Execute query and store results
result = civis.io.read_civis_sql(
    sql=query,
    database=DATABASE_CRED,
    use_pandas=True
)

# Store the result as a Civis Platform file output
civis.io.dataframe_to_civis(
    df=result,
    table='{TABLE}_civis_studio_demo',
    database=DATABASE_CRED,
    existing_table_rows='drop'
)