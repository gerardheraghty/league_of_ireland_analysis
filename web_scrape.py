import requests
from bs4 import BeautifulSoup 
import random
import pandas as pd
from datetime import datetime
import time
import base64
import os

#importing visualisation libraries
import seaborn as sns
import matplotlib.pyplot as plt 

import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc


#importing necessary packages for selenium as attendances are 
#populated using javascript therefore regular scraping will not suffice
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

## Defining functions
def check_premier(url):
    response = requests.get(url)

    if response.status_code == 200:
        page_content = response.text
    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")

    soup = BeautifulSoup(page_content, 'html.parser')

    # Find the meta tag with name="description"
    meta_tag = soup.find("meta", attrs={"name": "description"})
    # Extract the content
    meta_content = meta_tag["content"] if meta_tag else ""

    # Find the part that starts with "Premier"
    cont = False
    for word in meta_content.split(","):
        if "Premier" in word:
            cont = True
    return cont


def scrape_loi_webpage(url):
    #opening the webdriver
    print(f'Running for {url}')
    driver = webdriver.Chrome() 
    driver.get(url)
    
    time.sleep(.5)
    # Handle alert if it appears
    try:
        alert = WebDriverWait(driver, 2).until(EC.alert_is_present())  # Wait for alert
        alert.accept()  # Accept the alert (you can use alert.dismiss() to close it)
    except:
        pass  # If no alert, just continue

    try:
        # Wait for the attendance element to be populated
        game_centre_info_element = WebDriverWait(driver, 5).until(
                                   EC.presence_of_element_located((By.CLASS_NAME, "game-centre__header--info"))
                                    )
        score_element = WebDriverWait(driver, 5).until(
                               EC.presence_of_element_located((By.CLASS_NAME, "game-centre__header--score"))
                                )
        kick_off_element = WebDriverWait(driver, 5).until(
                               EC.presence_of_element_located((By.CLASS_NAME, "game-centre__header--kickoff"))
                                )

        #getting the score and game centre info
        game_score = score_element.text.strip()
        game_centre_info = game_centre_info_element.text.strip()
        kick_off_time = kick_off_element.text.strip()

        if game_score == 'v':
            home_goals = 'postponed'
            away_goals = 'postponed'
        else:
            home_goals_element = WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.CLASS_NAME, "home-goals"))
                                    )
            away_goals_element = WebDriverWait(driver, 5).until(
                                   EC.presence_of_element_located((By.CLASS_NAME, "away-goals"))
                                    )
            home_goals = home_goals_element.text.strip()
            away_goals = away_goals_element.text.strip()

    except Exception as e:
        print("Error:", e)

    finally:
        driver.quit()
        
    #----------checking match date------------#
    exit_loop = False
    # Parse the date part (first line of the string)
    game_date = game_centre_info.split('\n')[0]
    # Convert the date string to a datetime object
    game_date = datetime.strptime(game_date, "%a %d %b %Y")
     # Get today's date (set time to midnight for accurate date comparison)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    # Check if the match date is today or in the future
    if game_date >= today:
        exit_loop = True
    
    #------------------------------#
            
    #using regular html request to get teams
    response = requests.get(url)

    if response.status_code == 200:
        page_content = response.text
    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")

    soup = BeautifulSoup(page_content, 'html.parser')

    teams = soup.find_all('span', class_='d-none d-lg-block')
    # Extracting the text from each span
    team_names = [team.get_text(strip=True) for team in teams]
    home_team = team_names[0]
    away_team = team_names[1]
    
    game_centre_info = game_centre_info.split("\n")
    
    #creating dataframe
    return home_team, away_team, game_score, kick_off_time, home_goals, away_goals, game_centre_info, exit_loop



def format_dataframe(data):
    df = pd.DataFrame([data], columns=["home_team", "away_team", "score","kick_off_time"
                                   ,"home_goals","away_goals", "game_centre_info"])
    # Extract the time using regex
    df['kick_off_time'] = df['kick_off_time'].str.extract(r'KO Time: (\d{2}:\d{2})')
    
    # Convert match_info to string to avoid errors
    df['game_centre_info'] = df['game_centre_info'].astype(str)

    # Remove brackets and split the string by ", "
    df[['date', 'referee', 'stadium', 'attendance']] = (
        df['game_centre_info']
        .str.strip('[]')  # Remove brackets
        .str.split(', ', expand=True)  # Split by comma and space
    )
    
    #formatting the date column
    df['date'] = pd.to_datetime(df['date'].str[4:-1].str.strip(), format='%d %b %Y').dt.strftime('%d.%m.%Y')

    # Extract numeric attendance (removing "Att: " and commas)
    df['attendance'] = (df['attendance'].str.extract(r'(\d[\d,]*)')[0]
                                                   .str.replace(',', '')
                                                   .fillna(0).astype(int))
    #dropping game_centre_info
    df = df.drop(columns=['game_centre_info'])
    
    #converting date column for proper sorting
    df['date'] = pd.to_datetime(df['date'], format='%d.%m.%Y')
    
    #adding season column
    df['season'] = df['date'].dt.year
    
    return df



##---------------------------------##
#loading in historical data
loi_df = pd.read_csv('data/loi_df.csv', index_col=0)
loi_df['date'] = pd.to_datetime(loi_df['date'])

#loading in the broaken url df
broken_url = pd.read_csv('data/broken_url.csv', index_col=0)

#getting last link that scrape was run for
last_link = loi_df['last_link'].unique()[0]


#---------------Looping through links-----------------#
#creating code for looping through links
for i in range (last_link + 1, last_link + 30):
    url = f"https://www.leagueofireland.ie/game_centre/{i}/"
    #run function to determine whether or not premier division game
    is_prem = check_premier(url)
    
    #if it is premier division game, continue with processing
    if is_prem: 
        res = scrape_loi_webpage(url)
        #breaking loop if date is not before today
        if res[-1]:
            print("Match date is in the future. Breaking loop.")
            break #exiting the loop
            
        #not merging if attendance missing
        if (len(res[6]) != 4) and (res[4] != 'postponed'):
            broken_url = pd.concat([broken_url, pd.DataFrame({'url': [url]})], ignore_index=True)
        elif (res[4] != 'postponed'): 
            df = format_dataframe(res[0:7])
            loi_df =  pd.concat([loi_df, df], ignore_index=True)
            loi_df['last_link'] = int(i)

#sorting by date
loi_df = loi_df.sort_values(by='date').reset_index(drop=True)

##-------------Saving new data-----------------##
# Directory where the file is located
data_dir = "data"

# Original file path
original_file = os.path.join(data_dir, "loi_df.csv")

# Check if the original file exists
if os.path.exists(original_file):
    # Get the current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create the new filename with timestamp
    backup_file = os.path.join(data_dir, f"loi_df_{timestamp}.csv")
    
    # Rename the existing file
    os.rename(original_file, backup_file)
    print(f"Backed up existing file to {backup_file}")

# Save the new dataframe
loi_df.to_csv(original_file)
broken_url.to_csv('data/broken_url.csv')
print(f"Saved new data to {original_file}")
