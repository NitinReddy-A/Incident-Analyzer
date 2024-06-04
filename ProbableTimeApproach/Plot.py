import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import pandas as pd

# Load the transition probabilities data
transition_df = pd.read_csv('data/transition_probabilities_within_service.csv')

# Get unique services
services = transition_df['Service Name'].unique()

app = dash.Dash(__name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}])

app.layout = html.Div([
    html.Div([
        html.Div([
            html.P('Select Service:', className='fix_label'),
            dcc.Dropdown(id='service_dropdown',
                         multi=False,
                         clearable=True,
                         value=services[0],
                         placeholder='Select Service',
                         options=[{'label': c, 'value': c} for c in services],
                         className='dcc_compon'),
            html.Div([
                html.H4("Service Specific Analysis")
            ], style={"margin-bottom": "25px", 'textAlign': 'center', 'color': 'navy', 'fontSize': 30}),
            html.Div(children=[
                dcc.Graph(id='sankey-diagram')
            ])
        ], className="create_container three columns", id="cross-filter-options"),
    ], className="row")
])

@app.callback(
    Output('sankey-diagram', 'figure'),
    [Input('service_dropdown', 'value')]
)
def update_sankey_diagram(selected_service):
    # Filter the data for the selected service
    filtered_data = transition_df[transition_df['Service Name'] == selected_service]

    # Create a list of unique nodes
    unique_nodes = list(set(filtered_data['Incident Name (From)'].tolist() + filtered_data['Incident Name (To)'].tolist()))

    # Create a mapping from node name to index
    node_map = {name: idx for idx, name in enumerate(unique_nodes)}

    # Create a Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color='black', width=0.5),
            label=unique_nodes,
            color="rgba(31, 119, 180, 0.8)"
        ),
        link=dict(
            source=[node_map[name] for name in filtered_data['Incident Name (From)']],
            target=[node_map[name] for name in filtered_data['Incident Name (To)']],
            value=filtered_data['Probability'].tolist(),
            color="rgba(31, 119, 180, 0.4)"
        )
    )])

    # Update layout
    fig.update_layout(title_text=f"Probablity of incident occurance for {selected_service} based on proabable time.",
                      font_size=10)

    return fig

if __name__ == '__main__':
    app.run_server(debug=True,port=8000)
