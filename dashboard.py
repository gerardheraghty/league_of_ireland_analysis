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
# Extract month from date
loi_df['month'] = loi_df['date'].dt.month

print(loi_df.tail())
##------------------------------Creating aggregated dataframes---------------------------------##
# 1. Average attendance per season
season_avg = loi_df.groupby('season')['attendance'].mean().reset_index()
season_avg.rename(columns={'attendance': 'avg_attendance_season'}, inplace=True)

# 2. Average attendance per month within each season
month_season_avg = loi_df.groupby(['season', 'month'])['attendance'].mean().reset_index()
month_season_avg.rename(columns={'attendance': 'avg_attendance_month'}, inplace=True)

# 3. Average attendance per team per season
team_season_avg = loi_df.groupby(['season', 'home_team'])['attendance'].mean().reset_index()
team_season_avg.rename(columns={'attendance': 'avg_attendance_team_season'}, inplace=True)

# 4. Average attendance per team per month per season
team_month_season_avg = loi_df.groupby(['season', 'month', 'home_team'])['attendance'].mean().reset_index()
team_month_season_avg.rename(columns={'attendance': 'avg_attendance_team_month'}, inplace=True)

# 5. Accumulated attendance for each season
season_total = loi_df.groupby('season')['attendance'].sum().reset_index()
season_total.rename(columns={'attendance': 'total_attendance_season'}, inplace=True)

# 6. Accumulated attendance for each team per season
team_season_total = loi_df.groupby(['season', 'home_team'])['attendance'].sum().reset_index()
team_season_total.rename(columns={'attendance': 'total_attendance_team_season'}, inplace=True)

# Create the final results
# For season-level stats (without team breakdown)
season_stats = pd.merge(season_avg, season_total, on='season')
season_month_stats = pd.merge(month_season_avg, season_stats, on='season')

# For team-level stats
team_stats = pd.merge(team_season_avg, team_season_total, on=['season', 'home_team'])
team_month_stats = pd.merge(team_month_season_avg, team_stats, on=['season', 'home_team'])

# Sort the results
season_month_stats = season_month_stats.sort_values(['season', 'month'])
team_month_stats = team_month_stats.sort_values(['season', 'home_team', 'month'])

# Add month names
month_names = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April', 
    5: 'May', 6: 'June', 7: 'July', 8: 'August',
    9: 'September', 10: 'October', 11: 'November', 12: 'December'
}

season_month_stats['month_name'] = season_month_stats['month'].map(month_names)
team_month_stats['month_name'] = team_month_stats['month'].map(month_names)

##--------------------------------------##

#extract unique teams and seasons for dropdown options
all_teams = sorted(list(set(loi_df['home_team'].unique()) | set(loi_df['away_team'].unique())))
all_seasons = sorted(loi_df['season'].unique())

##-----------------LOI Logo-----------------##
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

##--------------------------Dash App--------------------------##

# Initialize the Dash app with Bootstrap CSS
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# App layout using Bootstrap components for better styling
app.layout = dbc.Container([
    # Header row with logo and title - same for both tabs
        # Logo row - centered at the top of the screen
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Img(
                        src=encoded_logo,
                        style={'height': 'auto', 'width': 'auto', 'max-width': '200px'}
                    )
                ], className="d-flex justify-content-center")
            ], width=12, className="mb-3")
        ]),

        # Title row
        dbc.Row([
            dbc.Col([
                html.H1("League of Ireland Attendance Dashboard", className="text-center my-2 my-md-4"),
                html.P("Explore attendance data for League of Ireland clubs", className="text-center mb-2 mb-md-4")
            ], width=12)
        ], className="mb-4"),
    
    # Common club selection dropdown for both tabs
    dbc.Row([
        dbc.Col([
            html.Label("Select Club:"),
            dcc.Dropdown(
                id='common-club-dropdown',
                options=[{'label': team, 'value': team} for team in all_teams],
                value=default_team,
                clearable=False
            )
        ], width=12, className="mb-3"),
    ], className="mb-3"),
    
    # Tabs for different views
    dbc.Tabs([
        # Tab 1: Original detailed attendance view
        dbc.Tab(label="Match Attendance", children=[
            dbc.Row([
                # Season selection (multi-select) for Tab 1
                dbc.Col([
                    html.Label("Select Season(s):"),
                    dcc.Dropdown(
                        id='season-dropdown',
                        options=[{'label': str(season), 'value': season} for season in all_seasons],
                        value=[all_seasons[-1]],
                        multi=True
                    )
                ], width=12, className="mb-3")
            ]),
            
            dbc.Row([
                dbc.Col([
                    # Main attendance chart
                    dcc.Graph(id='attendance-chart')
                ], width=12, className="mb-4")
            ])
        ]),
        
        # Tab 2: Aggregated monthly and season data
        dbc.Tab(label="Aggregated Statistics", children=[
            dbc.Row([
                # Season selection (single season) for Tab 2
                dbc.Col([
                    html.Label("Select Season:"),
                    dcc.Dropdown(
                        id='agg-season-dropdown',
                        options=[{'label': str(season), 'value': season} for season in all_seasons],
                        value=all_seasons[-1],
                        clearable=False
                    )
                ], width=12, md=8, className="mb-3"),
                
                # League average toggle switch
                dbc.Col([
                    dbc.Checklist(
                        options=[
                            {"label": "Include League Average", "value": 1}
                        ],
                        value=[],
                        id="include-league-avg",
                        switch=True,  # Use toggle switch style
                    ),
                ], width=12, md=4, className="mb-3 d-flex align-items-center"),
            ]),
            
            dbc.Row([
                # Monthly average attendance bar chart
                dbc.Col([
                    dcc.Graph(id='monthly-avg-chart')
                ], width=12, md=8, className="mb-4"),
                
                # Season statistics card
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Season Statistics", className="text-center")),
                        dbc.CardBody([
                            html.Div(id='season-stats-content')
                        ])
                    ], className="h-100")
                ], width=12, md=4, className="mb-4")
            ])
        ])
    ]),
    
    # Footer - same for both tabs
    dbc.Row([
        dbc.Col([
            html.Div([
                html.P("Data source: leagueofireland.ie", className="text-muted text-center")
            ])
        ])
    ])
], fluid=True)

#Callback 1 - creating a chart for each home attendance for the selected club
@callback(
    Output('attendance-chart', 'figure'),
    [Input('common-club-dropdown', 'value'),
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
        season_data = club_data[club_data['season'] == int(season)].copy()
        
        # Skip if no data for this season
        if len(season_data) == 0:
            continue
            
        # Sort by date for proper line chart
        season_data = season_data.sort_values('date')
        
        # Create a standardized date by replacing the year with a constant year
        # This allows comparing months across different seasons
        season_data.loc[:, 'standard_date'] = season_data['date'].apply(
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
            ticktext=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            range=['2000-01-01', '2000-12-31'],  # Ensure the range is always Jan to Dec
            fixedrange=True  # Disable zoom on x-axis
        ),
        yaxis=dict(
            title='Attendance',
            rangemode='tozero',
            fixedrange=True  # Disable zoom on y-axis
        ),
        legend_title='Season',
        hovermode='closest',
        dragmode=False  # Disable drag mode
    )
    
    return fig

#Callback 2 - creating a bar chart for showing monthly attendance aggregation.
@callback(
    Output('monthly-avg-chart', 'figure'),
    [Input('common-club-dropdown', 'value'),
     Input('agg-season-dropdown', 'value'),
     Input('include-league-avg', 'value')]
)
def update_monthly_avg_chart(selected_club, selected_season, include_league_avg):
    if not selected_club or not selected_season:
        return go.Figure()
    
    # Convert season to integer
    season_int = int(selected_season)
    
    # Filter data for the selected club and season
    filtered_data = loi_df[(loi_df['home_team'] == selected_club) & 
                           (loi_df['season'] == season_int)].copy()
    
    # If no data, return empty figure
    if len(filtered_data) == 0:
        fig = go.Figure()
        fig.update_layout(
            title=f'No data available for {selected_club} in season {selected_season}',
            xaxis_title='Month',
            yaxis_title='Attendance'
        )
        return fig
    
    # Define month names dictionary
    month_names = {
        1: 'January', 2: 'February', 3: 'March', 4: 'April', 
        5: 'May', 6: 'June', 7: 'July', 8: 'August',
        9: 'September', 10: 'October', 11: 'November', 12: 'December'
    }
    
    # Create a complete dataset with all months (even those with no data)
    complete_months = pd.DataFrame({'month': range(2, 12)})
    complete_months['month_name'] = complete_months['month'].map(month_names)
    
    # Extract month from date and calculate monthly averages for the selected club
    filtered_data.loc[:, 'month'] = filtered_data['date'].dt.month
    club_monthly_avg = filtered_data.groupby('month')['attendance'].mean().reset_index()
    
    # Merge with complete months
    club_monthly_data = pd.merge(complete_months, club_monthly_avg, on='month', how='left')
    club_monthly_data['attendance'] = club_monthly_data['attendance'].fillna(0)
    
    # Create bar chart using go.Figure
    fig = go.Figure()
    
    # Add the selected club's attendance
    show_text = 1 not in include_league_avg  # Only show text annotations if league avg is not included
    
    fig.add_trace(go.Bar(
        x=club_monthly_data['month_name'],
        y=club_monthly_data['attendance'],
        name=selected_club,
        text=club_monthly_data['attendance'].apply(lambda x: f"{int(round(x)):,}" if x > 0 and show_text else ""),
        textposition='auto',
        marker_color='royalblue',
        hovertemplate='<b>%{y:.1f} spectators</b><br>' + 
                      '%{x}<br>' +
                      f'Club: {selected_club}<extra></extra>'
    ))
    
    # If league average should be included, add it as a second trace
    if 1 in include_league_avg:
        # Filter all data for the selected season
        league_data = loi_df[loi_df['season'] == season_int].copy()
        
        # Extract month from date and calculate monthly averages across all clubs
        league_data.loc[:, 'month'] = league_data['date'].dt.month
        league_monthly_avg = league_data.groupby(['month'])['attendance'].mean().reset_index()
        
        # Merge with complete months
        league_monthly_data = pd.merge(complete_months, league_monthly_avg, on='month', how='left')
        league_monthly_data['attendance'] = league_monthly_data['attendance'].fillna(0)
        
        # Add league average trace
        fig.add_trace(go.Bar(
            x=league_monthly_data['month_name'],
            y=league_monthly_data['attendance'],
            name='League Average',
            marker_color='red',
            hovertemplate='<b>%{y:.1f}  spectators</b><br>' + 
                          '%{x}<br>' +
                          'League Average<extra></extra>'
        ))
    
    # Update layout
    fig.update_layout(
        title=f'{selected_club} - Average Monthly Attendance ({selected_season})',
        xaxis_title='Month',
        yaxis_title='Average Attendance',
        yaxis=dict(rangemode='tozero', fixedrange=True),
        xaxis=dict(
            type='category',
            categoryorder='array',
            categoryarray=list(month_names.values()),
            fixedrange=True
        ),
        barmode='group',  # Group bars side by side
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        dragmode=False
    )
    
    return fig

#Callback 3 - updating monthly statistics 
@callback(
    Output('season-stats-content', 'children'),
    [Input('common-club-dropdown', 'value'),
     Input('agg-season-dropdown', 'value')]
)
def update_season_stats(selected_club, selected_season):
    if not selected_club or not selected_season:
        return html.P("No data selected")
    
    # Filter data for the selected club and season
    filtered_data = loi_df[(loi_df['home_team'] == selected_club) & 
                           (loi_df['season'] == int(selected_season))]
    
    # If no data, return message
    if len(filtered_data) == 0:
        return html.P(f"No data available for {selected_club} in season {selected_season}")
    
    # Calculate statistics
    season_avg = filtered_data['attendance'].mean()
    season_total = filtered_data['attendance'].sum()
    season_max = filtered_data['attendance'].max()
    max_attended_match = filtered_data.loc[filtered_data['attendance'].idxmax()]
    num_games = len(filtered_data)
    
    # Format opponent and date for max attended match
    max_opponent = max_attended_match['away_team']
    max_date = max_attended_match['date'].strftime('%d.%m.%Y')
    max_score = max_attended_match['score']
    
    # Create statistics display
    stats_content = [
        html.H5(f"{selected_club} - Season {selected_season}", className="text-center mb-3"),
        html.Div([
            html.H6("Season Average:", className="fw-bold"),
            html.P(f"{round(season_avg, 1):,} spectators per match")
        ], className="mb-3"),
        html.Div([
            html.H6("Total Season Attendance:", className="fw-bold"),
            html.P(f"{int(season_total):,} spectators")
        ], className="mb-3"),
        html.Div([
            html.H6("Highest Attendance:", className="fw-bold"),
            html.P(f"{int(season_max):,} spectators"),
            html.P(f"{selected_club} v {max_opponent} on {max_date}"),
            html.P(f"Score: {max_score}")
        ])
    ]
    
    return stats_content


#running the server
if __name__ == '__main__':
    app.run_server(debug=False, host='0.0.0.0')