import pandas as pd
import plotly.graph_objects as go
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output

# Read the transition probabilities data
transition_df = pd.read_csv('data/transition_probabilities_within_service.csv')

# Get unique services
services = transition_df['Service Name'].unique()

# Initialize the Dash app
app = dash.Dash(__name__)

# Define the layout of the Dash app
app.layout = html.Div(children=[
    html.H1(children='Transition Probabilities for Different Services'),
    dcc.Dropdown(
        id='service-dropdown',
        options=[{'label': service, 'value': service} for service in services],
        value=services[0]
    ),
    dcc.Graph(id='sankey-diagram')
])

# Define callback to update the Sankey diagram based on dropdown selection
@app.callback(
    Output('sankey-diagram', 'figure'),
    [Input('service-dropdown', 'value')]
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

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True,port=8000)
