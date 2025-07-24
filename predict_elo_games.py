import requests
import pandas as pd
from datetime import datetime

HOME_ADVANTAGE = 65
ELO_FILE = "nfl_team_elo_final.csv"

def predict_win_prob(home_elo, away_elo):
    home_elo += HOME_ADVANTAGE
    return 1 / (1 + 10 ** ((away_elo - home_elo) / 400))

def get_upcoming_week():
    for week in range(1, 19):
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week={week}&seasontype=2"
        data = requests.get(url).json()
        games = data.get("events", [])
        if any("status" in e and e["status"]["type"]["state"] == "pre" for e in games):
            return week
    return None

def get_week_schedule(week, year):
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week={week}&year={year}&seasontype=2"
    data = requests.get(url).json()
    schedule = []
    for event in data.get("events", []):
        competition = event['competitions'][0]
        teams = competition['competitors']
        home = [t for t in teams if t['homeAway'] == 'home'][0]
        away = [t for t in teams if t['homeAway'] == 'away'][0]
        schedule.append({
            'home_team': home['team']['displayName'],
            'away_team': away['team']['displayName'],
            'date': event['date']
        })
    return pd.DataFrame(schedule)

def predict_upcoming_games():
    elos = pd.read_csv(ELO_FILE).set_index('Unnamed: 0')['elo'].to_dict()
    year = datetime.now().year
    if datetime.now().month < 3:
        year -= 1
    week = get_upcoming_week()
    if not week:
        print("No upcoming games found.")
        return
    schedule_df = get_week_schedule(week, year)
    predictions = []
    for _, row in schedule_df.iterrows():
        home = row['home_team']
        away = row['away_team']
        home_elo = elos.get(home, 1500)
        away_elo = elos.get(away, 1500)
        home_win_prob = predict_win_prob(home_elo, away_elo)
        predictions.append({
            'week': week,
            'date': row['date'],
            'home_team': home,
            'away_team': away,
            'home_elo': home_elo,
            'away_elo': away_elo,
            'home_win_prob': round(home_win_prob, 3),
            'away_win_prob': round(1 - home_win_prob, 3),
            'predicted_winner': home if home_win_prob > 0.5 else away
        })
    pred_df = pd.DataFrame(predictions)
    pred_df.to_csv(f"nfl_elo_predictions_week{week}.csv", index=False)
    print(pred_df[['home_team', 'away_team', 'home_win_prob', 'away_win_prob', 'predicted_winner']])

if __name__ == "__main__":
    predict_upcoming_games()