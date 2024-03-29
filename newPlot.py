import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go

# Read the CSV file into a DataFrame
df = pd.read_csv('data/incidents_data.csv')

# Convert 'created_at' column to datetime format
df['created_at'] = pd.to_datetime(df['created_at'])

# Initialize Dash app
app = dash.Dash(__name__)

# Define a custom color scale for shades of red with dark maroon, red, and an intermediary shade of red
colorscale_red = [
    [0, '#ff9999'], # light red
    [0.5, '#ff0000'], # red
    [1, '#8B0000'] # dark maroon red
]

# Define app layout
app.layout = html.Div([
    dcc.Graph(id='heatmap'),
    dcc.Input(id='dummy-input', type='hidden', value='trigger'),
    html.Div(id='line-graph')
])

# Define callback to update heatmap
@app.callback(
    Output('heatmap', 'figure'),
    [Input('dummy-input', 'value')]
)
def update_heatmap(value):
    # Group the data by 'service' column and count the number of incidents for each service
    service_counts = df.groupby('service')['incident_id'].count().reset_index()

    # Create the heatmap with custom color scale
    heatmap = go.Heatmap(
        x=service_counts['service'],
        y=['Incident Count'],
        z=[service_counts['incident_id']],
        colorscale=colorscale_red
    )

    # Create layout
    layout = go.Layout(
        title='Heatmap of Incident Count per Service',
        xaxis=dict(title='Service'),
        yaxis=dict(title='Incident Count')
    )

    # Create figure object
    fig = go.Figure(data=[heatmap], layout=layout)

    return fig

# Define callback to update line graph
@app.callback(
    Output('line-graph', 'children'),
    [Input('dummy-input', 'value')]
)
def update_line_graph(value):
    # Group the data by 'created_at' column and count the number of incidents for each minute
    incident_count_by_time = df.groupby(pd.Grouper(key='created_at', freq='Min'))['incident_id'].count().reset_index()

    # Plot the line graph
    line_graph = dcc.Graph(
        id='incident-line-graph',
        figure={
            'data': [
                {'x': incident_count_by_time['created_at'], 'y': incident_count_by_time['incident_id'], 'type': 'line', 'name': 'Incident Count'}
            ],
            'layout': {
                'title': 'Incident Count Over Time (Per Minute)',
                'xaxis': {'title': 'Time Stamp'},
                'yaxis': {'title': 'Number of Incidents'}
            }
        }
    )

    return line_graph

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
