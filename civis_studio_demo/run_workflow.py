import civis
import os
from civis.futures import CivisFuture

# Initialize the client
client = civis.APIClient()

# Workflow ID from the URL
WORKFLOW_ID = 116976

# Define the input parameters, pulling both from environment variables
workflow_input = {
    "DATABASE_CRED_NAME": os.environ.get('DATABASE_CRED_NAME'),
    "TABLE": os.environ.get('TABLE')
}

# Start the workflow execution
execution = client.workflows.post_executions(WORKFLOW_ID, input=workflow_input)

# Create a future to track the execution
future = CivisFuture(
    client.workflows.get_executions,
    (WORKFLOW_ID, execution.id)
)

# Wait for the workflow to complete and get the result
result = future.result()
print(f"Workflow execution completed with status: {result.state}")