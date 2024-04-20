import dash
from dash import dcc, html , Dash
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px

# Read the CSV file into a DataFrame
df = pd.read_csv('data/incidents_data.csv')

# Convert 'created_at' column to datetime format
df['updated_at'] = pd.to_datetime(df['updated_at'])

# Initialize Dash app
app = dash.Dash(__name__)

# Set up the app layout
service_dropdown = dcc.Dropdown(options=df['service'].unique(),
                            value='PulseGuard')

app.layout = html.Div(children=[
    html.H1(children='PagerDuty Incidents Graph'),
    service_dropdown,
    dcc.Graph(id='incidents-graph')
])


# Set up the callback function
@app.callback(
    Output(component_id='incidents-graph', component_property='figure'),
    Input(component_id=service_dropdown, component_property='value')
)
def update_graph(selected_service):
    filtered_incidents = df[df['service'] == selected_service]
    line_fig = px.scatter(filtered_incidents,
                       x='updated_at', y='incident_number',
                       color='status',
                       title=f'Incidents on {selected_service}')
    return line_fig


# Run local server
if __name__ == '__main__':
    app.run_server(debug=True)