import random
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd

# Load the CSV data
try:
    data = pd.read_csv('data/categorized_incidents.csv')
except pd.errors.ParserError:
    # Handle parsing errors
    print("Parsing error occurred. Please check the CSV file for formatting issues.")

# Read the transition probabilities data
transition_df = pd.read_csv('data/transition_probabilities_within_service.csv')

# Get unique services
services = transition_df['Service Name'].unique()


data['created_at'] = pd.to_datetime(data['created_at'])

# Calculate the total number of services
total_services = len(data['service'].unique())

# Calculate the total number of triggered incidents
total_triggered = (data['status'] == 'triggered').sum()

# Calculate the total number of acknowledged incidents
total_acknowledged = (data['status'] == 'acknowledged').sum()

# Calculate the total number of resolved incidents
total_resolved = (data['status'] == 'resolved').sum()

# Calculate the number of incidents for each service and status
incidents_by_service_status = data.groupby(['service', 'status']).size().unstack(fill_value=0)

# Filter triggered incidents
triggered_incidents = data[data['status'] == 'triggered']

# Calculate probability of occurrence for each incident category
incident_probabilities = triggered_incidents['category'].value_counts(normalize=True)


app = dash.Dash(__name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}])

app.layout = html.Div([
     html.Div([
        html.Div([
            html.P('Select Service:', className='fix_label'),
            dcc.Dropdown(id='service_dropdown',
                         multi=False,
                         clearable=True,
                         value='Payment Processing System',
                         placeholder='Select Service',
                         options=[{'label': c, 'value': c} for c in data['service'].unique()],
                         className='dcc_compon'),
            html.Div([
                html.H4("Service Specific Analysis")
            ],style={"margin-bottom": "25px",'textAlign': 'center', 'color': 'navy', 'fontSize': 30}),
            html.Div(children=[
            html.H1(children='Transition Probabilities for Incident Occurence:'),
            dcc.Graph(id='sankey-diagram')])
        ], className="create_container three columns", id="cross-filter-options"),
        
    ], className="row")])


# Define callback to update the Sankey diagram based on dropdown selection
@app.callback(
    Output('sankey-diagram', 'figure'),
    [Input('service_dropdown', 'value')]
)
def update_sankey_diagram(selected_service):
    # Filter the data for the selected service
    filtered_data = transition_df[transition_df['Service Name'] == selected_service]
    
    # Create a Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color='black', width=0.5),
            label=filtered_data['Incident Name (From)'].tolist() + filtered_data['Incident Name (To)'].tolist(),
            color="rgba(31, 119, 180, 0.8)"  # Change color to a visually pleasing one
        ),
        link=dict(
            source=filtered_data['Incident Name (From)'].apply(lambda x: filtered_data['Incident Name (From)'].tolist().index(x)).tolist(),
            target=filtered_data['Incident Name (To)'].apply(lambda x: len(filtered_data['Incident Name (From)'].tolist()) + filtered_data['Incident Name (To)'].tolist().index(x)).tolist(),
            value=filtered_data['Probability'].tolist(),
            color="rgba(31, 119, 180, 0.4)"  # Change color to a visually pleasing one
        )
    )])
    
    # Update layout
    fig.update_layout(title_text=f"Transition Probabilities for {selected_service}",
                      font_size=10)
    
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
