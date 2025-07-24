import requests
import pandas as pd
import os
from datetime import datetime

CSV_FILENAME = "nfl_game_results.csv"

def get_espn_nfl_scores(year: int, week: int):
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week={week}&year={year}&seasontype=2"
    resp = requests.get(url)
    if resp.status_code != 200:
        return []
    data = resp.json()
    games = []
    for event in data.get('events', []):
        competition = event['competitions'][0]
        teams = competition['competitors']
        home = [t for t in teams if t['homeAway'] == 'home'][0]
        away = [t for t in teams if t['homeAway'] == 'away'][0]
        games.append({
            'season': year,
            'week': week,
            'date': event['date'],
            'home_team': home['team']['displayName'],
            'home_score': int(home.get('score', 0)),
            'away_team': away['team']['displayName'],
            'away_score': int(away.get('score', 0)),
            'winner': home['team']['displayName'] if home.get('winner') else away['team']['displayName']
        })
    return games

def find_latest_week(year: int):
    for week in range(1, 19):
        games = get_espn_nfl_scores(year, week)
        if not games:
            return week - 1
    return 18

def load_existing_data():
    if os.path.exists(CSV_FILENAME):
        return pd.read_csv(CSV_FILENAME)
    else:
        return pd.DataFrame(columns=[
            'season', 'week', 'date', 'home_team', 'home_score',
            'away_team', 'away_score', 'winner'
        ])

def game_exists(existing_df, new_game):
    return ((existing_df['season'] == new_game['season']) &
            (existing_df['week'] == new_game['week']) &
            (existing_df['home_team'] == new_game['home_team']) &
            (existing_df['away_team'] == new_game['away_team'])).any()

def update_nfl_game_data():
    existing_df = load_existing_data()
    new_games = []

    current_year = datetime.now().year
    if datetime.now().month < 3:
        current_year -= 1

    start_year = current_year - 3
    end_year = current_year

    print(f"Fetching NFL game data from {start_year} to {end_year}...")

    for year in range(start_year, end_year + 1):
        latest_week = find_latest_week(year) if year == end_year else 18
        for week in range(1, latest_week + 1):
            weekly_games = get_espn_nfl_scores(year, week)
            for game in weekly_games:
                if not game_exists(existing_df, game):
                    new_games.append(game)

    if new_games:
        print(f"Found {len(new_games)} new games. Adding to dataset...")
        updated_df = pd.concat([existing_df, pd.DataFrame(new_games)], ignore_index=True)
        updated_df.sort_values(by=['season', 'week'], inplace=True)
        updated_df.to_csv(CSV_FILENAME, index=False)
        print(f"Saved updated dataset with {len(updated_df)} total games to {CSV_FILENAME}")
    else:
        print("No new games found. Dataset is already up to date.")

if __name__ == "__main__":
    update_nfl_game_data()