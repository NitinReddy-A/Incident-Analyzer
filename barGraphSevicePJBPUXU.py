import dash
from dash import dcc, html
import plotly.graph_objs as go
import requests

# Authenticate with PagerDuty API
API_TOKEN = 'u+Dt9tsyzfBYDCPrTxjQ'

# Fetch incidents data for a specific service
def fetch_incidents_data(service_id):
    headers = {
        'Authorization': f'Token token={API_TOKEN}',
        'Content-Type': 'application/json',
    }
    # Fetch incidents data
    incidents_response = requests.get(f'https://api.pagerduty.com/incidents?service_ids[]={service_id}&limit=100', headers=headers)
    incidents_data = incidents_response.json()

    return incidents_data

# Process incidents data to get counts for triggered and solved incidents
def process_data(incidents_data):
    # Initialize lists to store dates and counts
    triggered_dates = []
    solved_dates = []

    # Process incidents data
    for incident in incidents_data['incidents']:
        if incident['status'] == 'triggered':
            triggered_dates.append(incident['created_at'][:10])  # Extract date from created_at
        elif incident['status'] == 'resolved':
            solved_dates.append(incident['resolved_at'][:10])  # Extract date from resolved_at

    # Count occurrences of each date
    triggered_counts = {date: triggered_dates.count(date) for date in sorted(set(triggered_dates))}
    solved_counts = {date: solved_dates.count(date) for date in sorted(set(solved_dates))}

    return triggered_counts, solved_counts

# Specify the ID of the service for which you want to plot incidents
service_id = 'PJBPUXU'

# Fetch incidents data for the specified service
incidents_data = fetch_incidents_data(service_id)

# Process data for the specified service
triggered_counts, solved_counts = process_data(incidents_data)

# Create Dash application
app = dash.Dash(__name__)

# Define layout
app.layout = html.Div(children=[
    html.H1('PagerDuty Data Visualization'),
    dcc.Graph(
        id='service-incidents-status-bar-chart',
        figure={
            'data': [
                go.Bar(
                    x=list(triggered_counts.keys()),
                    y=list(triggered_counts.values()),
                    name='Triggered',
                    marker=dict(color='blue')  # Custom color for triggered bars
                ),
                go.Bar(
                    x=list(solved_counts.keys()),
                    y=list(solved_counts.values()),
                    name='Solved',
                    marker=dict(color='red')  # Custom color for solved bars
                )
            ],
            'layout': go.Layout(
                title='Incidents by Date',
                xaxis={'title': 'Date'},
                yaxis={'title': 'Number of Incidents'}
            )
        }
    )
])

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
