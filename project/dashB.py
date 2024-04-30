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


# Define a custom color scale for shades of red with dark maroon, red, and an intermediary shade of red
colorscale_red = [
    [0, '#ff9999'], # light red
    [0.5, '#ff0000'], # red
    [1, '#8B0000'] # dark maroon red
]

app = dash.Dash(__name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}])

app.layout = html.Div([
    html.Div([
        html.Div([
            html.Div([
                html.H3("Incident Analyzer")
            ]),
            html.Div([
                html.H4("Overview of all Incidents")
            ])
        ], id="title"),

    ], id="header", style={"margin-bottom": "25px",'textAlign': 'center', 'color': 'navy', 'fontSize': 30}),

    html.Div([
        html.Div([
            html.H6(children='Total Services'),
            html.P(f"{total_services}")
        ], className="card_container three columns", style={'textAlign': 'center', 'color': 'navy', 'fontSize': 30}),

        html.Div([
            html.H6(children='Triggered Incidents'),
            html.P(f"{total_triggered}")
        ], className="card_container three columns", style={'textAlign': 'center', 'color': 'red', 'fontSize': 30}),

        html.Div([
            html.H6(children='Acknowledged Incidents'),
            html.P(f"{total_acknowledged}")
        ], className="card_container three columns", style={'textAlign': 'center', 'color': 'orange', 'fontSize': 30}),

        html.Div([
            html.H6(children='Resolved Incidents'),
            html.P(f"{total_resolved}")
        ], className="card_container three columns", style={'textAlign': 'center', 'color': 'green', 'fontSize': 30})


    ], className="row",style={'display':'flex', 'justify-content':'space-between'}),

    html.Div([
            dcc.Input(id='dummy-input', type='hidden', value='trigger'),
            dcc.Graph(id='line_chart', config={'displayModeBar': 'hover'})
        ], className="create_container four columns",style={'height': '450px', 'margin-top': '20px'}),

    html.Div([
            dcc.Input(id='dummy-input1', type='hidden', value='trigger'),
            dcc.Graph(id='heat_map', config={'displayModeBar': 'hover'})
        ], className="create_container four columns",style={'height': '450px', 'margin-top': '20px'}),

    html.Div([
            dcc.Graph(id='pie-chart3'),
        ],style={'height': '450px', 'margin-top': '20px'}),


    # Dropdown Section
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
            html.Div([
                html.Div([
                    html.H6(children='Triggered Incidents',
                            style={'textAlign': 'center','fontSize': 25}),
                    html.P(id='triggered_count', style={'textAlign': 'center', 'color': 'red', 'fontSize': 30})
                ], className="card_container three columns"),
                html.Div([
                    html.H6(children='Acknowledged Incidents',
                            style={'textAlign': 'center','fontSize': 25}),
                    html.P(id='acknowledged_count', style={'textAlign': 'center', 'color': 'orange', 'fontSize': 30})
                ], className="card_container three columns"),
                html.Div([
                    html.H6(children='Resolved Incidents',
                            style={'textAlign': 'center','fontSize': 25}),
                    html.P(id='resolved_count', style={'textAlign': 'center', 'color': 'green', 'fontSize': 30})
                ], className="card_container three columns")
            ], className="row flex-display",style={'display':'flex', 'justify-content':'space-between'}),
            html.Div([
            dcc.Graph(id='pie_chart', config={'displayModeBar': 'hover'})
            ], className="create_container four columns",style={'height': '400px', 'margin-top': '20px'}),

            html.Div([
            dcc.Graph(id='pie_chart_1', config={'displayModeBar': 'hover'})
            ], className="create_container four columns",style={'height': '500px', 'margin-top': '20px'}),

            html.Div(children=[
            html.H1(children='Transition Probabilities for Incident Occurence:'),
            dcc.Graph(id='sankey-diagram')])
        ], className="create_container three columns", id="cross-filter-options"),
        
    ], className="row")

], id="mainContainer")


# Define callback to update the line chart based on 1-hour time period
@app.callback(
    Output('line_chart', 'figure'),
    [Input('dummy-input', 'value')]
)
def update_chart(value):
    # Resample the data to a finer time interval for smoother graph
    resampled_data = data.resample('10min', on='created_at').size().reset_index(name='count')

    # Create line chart
    figure = {
        'data': [{
            'x': resampled_data['created_at'],
            'y': resampled_data['count'],
            'mode': 'lines',
            'line': {'color': 'blue'},
            'name': 'Incidents Created'
        }],
        'layout': {
            'title': 'Number of Incidents Triggered vs Time (1-hour intervals)',
            'xaxis': {'title': 'Time'},
            'yaxis': {'title': 'Number of Incidents'}
        }
    }

    return figure


# Define callback to update heatmap
@app.callback(
    Output('heat_map', 'figure'),
    [Input('dummy-input1', 'value')]
)
def update_heatmap(value):
    # Group the data by 'service' column and count the number of incidents for each service
    service_counts = data.groupby('service')['incident_id'].count().reset_index()

    # Create the heatmap with custom color scale
    heatmap = go.Heatmap(
        x=service_counts['service'],
        y=['Incident Count'],
        z=[service_counts['incident_id']],
        colorscale=colorscale_red
    )

    # Create layout with custom colorbar settings to add white border
    layout = go.Layout(
        title='Heatmap of Incident Count per Service',
        xaxis=dict(title='Service'),
        yaxis=dict(title='Incidents'),
        coloraxis=dict(colorbar=dict(
            tickvals=[0.5, 1.5],  # Set ticks in the middle of each color category
            ticktext=['', ''],  # Hide tick labels
            tickmode='array',
            tickcolor='white',
            tickwidth=1,
            lenmode='pixels',
            len=400  # Set colorbar length
        ))
    )

    # Create figure object
    fig = go.Figure(data=[heatmap], layout=layout)

    return fig


# Define callback to update the pie chart
@app.callback(
    Output('pie-chart3', 'figure'),
    Input('dummy-input', 'value') 
)
def update_pie_chart(dummy_input):
    
    fig = px.pie(incident_probabilities, values=incident_probabilities.values, names=incident_probabilities.index,
                 title='Total Probability of Occurrence by Incident Category')
    return fig

@app.callback(
    Output('triggered_count', 'children'),
    [Input('service_dropdown', 'value')])
def update_trigger_count(selected_service):
    triggered_count = incidents_by_service_status.loc[selected_service, 'triggered']
    return f"{triggered_count}"

@app.callback(
    Output('acknowledged_count', 'children'),
    [Input('service_dropdown', 'value')])
def update_acknowledged_count(selected_service):
    if selected_service is None or selected_service not in incidents_by_service_status.index:
        # Return an empty figure if no service is selected or the selected service is not in the data
        return ''

    # Check if the 'acknowledged' column exists in the DataFrame
    if 'acknowledged' not in incidents_by_service_status.columns:
        # If 'acknowledged' column does not exist, set count to 0
        acknowledged_count = 0
    else:
        # Retrieve counts for 'acknowledged' status
        acknowledged_count = incidents_by_service_status.loc[selected_service, 'acknowledged']

    return f"{acknowledged_count}"


@app.callback(
    Output('resolved_count', 'children'),
    [Input('service_dropdown', 'value')])
def update_resolved_count(selected_service):
    resolved_count = incidents_by_service_status.loc[selected_service, 'resolved']
    return f"{resolved_count}"

@app.callback(
    Output('pie_chart', 'figure'),
    [Input('service_dropdown', 'value')])
def update_pie_chart(selected_service):
    if selected_service:
        filtered_data = data[data['service'] == selected_service]
    else:
        filtered_data = data

    category_counts = filtered_data['category'].value_counts()
    category_colors = {category: f'#{random.randint(0, 0xFFFFFF):06x}' for category in category_counts.index}

    pie_chart = go.Figure(
        data=[go.Pie(
            labels=category_counts.index,
            values=category_counts.values,
            textinfo='none',  # Hide labels
            hole=0.7,
            marker=dict(colors=[category_colors[category] for category in category_counts.index]),
            direction='clockwise',  # Change direction to clockwise
            sort=False  # Disable sorting
        )
        ],
        layout=go.Layout(
            title='Overall Incidents Category Split:',
            margin=dict(t=50, b=50, l=50, r=50),
            legend=dict(orientation='v', x=1.1),  # Position legend to the right
            showlegend=True
        )
    )

    return pie_chart

@app.callback(
    Output('pie_chart_1', 'figure'),
    [Input('service_dropdown', 'value')])
def update_pie_chart(selected_service):
    if selected_service:
        filtered_data = data[data['service'] == selected_service]
    else:
        filtered_data = data

    # Get the top 3 majority categories
    top_categories = filtered_data['category'].value_counts().nlargest(3)

    # Calculate the total count of incidents
    total_incidents = filtered_data.shape[0]

    # Calculate percentages for each of the top categories
    percentages = [(category, count / total_incidents * 100) for category, count in top_categories.items()]

    category_labels, category_percentages = zip(*percentages)

    # Generate colors for the categories
    category_colors = {category: f'#{random.randint(0, 0xFFFFFF):06x}' for category in category_labels}

    pie_chart = go.Figure(
        data=[go.Pie(
            labels=category_labels,
            values=category_percentages,
            textinfo='label+percent',
            hole=0.7,
            marker=dict(colors=[category_colors[category] for category in category_labels]),
            direction='clockwise',  # Change direction to clockwise
            sort=False  # Disable sorting
        )
        ],
        layout=go.Layout(
            title='Majority Incidents Category Split:',
            margin=dict(t=50, b=50, l=50, r=50),
            legend=dict(orientation='v', x=1.1),  # Position legend to the right
            showlegend=True
        )
    )

    return pie_chart

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
