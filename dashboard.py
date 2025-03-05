#importing relevant libraries
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
from datetime import datetime
import base64

#loading the extracted data into the script
loi_df = pd.read_csv('data/loi_df.csv', index_col=0)
#converting date column for proper sorting
loi_df['date'] = pd.to_datetime(loi_df['date'])

#extract unique teams and seasons for dropdown options
all_teams = sorted(list(set(loi_df['home_team'].unique()) | set(loi_df['away_team'].unique())))
all_seasons = sorted(loi_df['season'].unique())

#---------------------------------DASH APP---------------------------------
#path to loi logo
logo_filename = 'images/League_Of_Ireland_logo_2023.png'

# Function to encode the image
def encode_image(image_path):
    with open(image_path, 'rb') as f:
        encoded = base64.b64encode(f.read()).decode('ascii')
        return f'data:image/png;base64,{encoded}'

# Encode logo
encoded_logo = encode_image(logo_filename)

default_team = "Sligo Rovers"

# Initialize the Dash app with Bootstrap CSS
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
# App layout using Bootstrap components for better styling
app.layout = dbc.Container([
    dbc.Row([
        # Logo column - full width on mobile, 2 columns on larger screens
        dbc.Col([
            html.Div([
                # Logo image
                html.Img(
                    src=encoded_logo,
                    style={'height': '80px', 'width': 'auto', 'max-width': '120px'}
                )
            ], className="d-flex justify-content-center justify-content-md-start")
        ], xs=12, md=2, className="d-flex align-items-center mb-3 mb-md-0"),
        
        # Title column - full width on mobile, 10 columns on larger screens
        dbc.Col([
            html.H1("League of Ireland Attendance Dashboard", className="text-center my-2 my-md-4"),
            html.P("Select club and seasons to view home attendance data", className="text-center mb-2 mb-md-4")
        ], xs=12, md=10)
    ], className="mb-4"),
    
    dbc.Row([
        # Club selection dropdown
        dbc.Col([
            html.Label("Select Club:"),
            dcc.Dropdown(
                id='club-dropdown',
                options=[{'label': team, 'value': team} for team in all_teams],
                value=default_team,  # Default to Sligo Rovers
                clearable=False
            )
        ], width=12, md=6, className="mb-3"),
        
        # Season selection (multi-select)
        dbc.Col([
            html.Label("Select Season(s):"),
            dcc.Dropdown(
                id='season-dropdown',
                options=[{'label': str(season), 'value': season} for season in all_seasons],
                value=[all_seasons[-1]],  # Default to most recent season
                multi=True
            )
        ], width=12, md=6, className="mb-3")
    ]),
    
    dbc.Row([
        dbc.Col([
            # Main attendance chart
            dcc.Graph(id='attendance-chart')
        ], width=12, className="mb-4")
    ]),
    
    # Footer with additional information
    dbc.Row([
        dbc.Col([
            html.Div([
                html.P("Data source: League of Ireland attendance records", className="text-muted text-center")
            ])
        ])
    ])
], fluid=True)

@callback(
    Output('attendance-chart', 'figure'),
    [Input('club-dropdown', 'value'),
     Input('season-dropdown', 'value')]
)
def update_chart(selected_club, selected_seasons):
    if not selected_club or not selected_seasons:
        return go.Figure()
    
    # Filter data for the selected club as home team only
    club_data = loi_df[loi_df['home_team'] == selected_club]
    
    # Create empty figure
    fig = go.Figure()
    
    # Add a trace for each selected season
    for season in selected_seasons:
        season_data = club_data[club_data['season'] == season]
        
        # Skip if no data for this season
        if len(season_data) == 0:
            continue
            
        # Sort by date for proper line chart
        season_data = season_data.sort_values('date')
        
        # Create a standardized date by replacing the year with a constant year
        # This allows comparing months across different seasons
        season_data['standard_date'] = season_data['date'].apply(
            lambda x: x.replace(year=2000)
        )
        
        # Prepare the customdata for hover information
        custom_data = []
        for _, row in season_data.iterrows():
            custom_data.append([
                row['date'].strftime('%d.%m.%Y'),
                row['away_team'],
                row['score']
            ])
        
        # Add line trace for this season
        fig.add_trace(go.Scatter(
            x=season_data['standard_date'],
            y=season_data['attendance'],
            mode='lines+markers',
            name=f'Season {season}',
            hovertemplate='<b>%{y} spectators</b><br>' + 
                          'Date: %{customdata[0]}<br>' + 
                          'Opponent: %{customdata[1]}<br>' + 
                          'Score: %{customdata[2]}<extra></extra>',
            customdata=custom_data
        ))
    
    # Update layout with custom x-axis tick format (months only)
    fig.update_layout(
        title=f'{selected_club} Home Attendance Figures',
        xaxis=dict(
            title='Month',
            tickformat='%b',  # Display only month abbreviation
            tickmode='array',
            tickvals=pd.date_range(start='2000-01-01', end='2000-12-31', freq='MS'),  # Month starts
            ticktext=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        ),
        yaxis=dict(
            title='Attendance',
            rangemode='tozero'
        ),
        legend_title='Season',
        hovermode='closest'
    )
    
    return fig

#running the server
if __name__ == '__main__':
    app.run_server(debug=False, host='0.0.0.0')