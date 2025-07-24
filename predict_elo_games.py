import requests
import pandas as pd
from datetime import datetime

HOME_ADVANTAGE = 65
ELO_FILE = "nfl_team_elo_final.csv"

def predict_win_prob(home_elo, away_elo):
    home_elo += HOME_ADVANTAGE
    return 1 / (1 + 10 ** ((away_elo - home_elo) / 400))

def find_next_upcoming_week_and_year():
    # Check weeks 1 to 18 for upcoming games on ESPN, starting from this year, and next year if needed
    current_year = datetime.now().year
    years_to_check = [current_year, current_year + 1]

    for year in years_to_check:
        for week in range(1, 19):
            url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week={week}&year={year}&seasontype=2"
            resp = requests.get(url)
            if resp.status_code != 200:
                continue
            data = resp.json()
            events = data.get("events", [])
            # If there are any games scheduled and any of them are in pre-game state, this is the next upcoming week
            if events:
                for event in events:
                    status = event.get("status", {}).get("type", {}).get("state", "")
                    if status in ("pre", "in"):
                        return week, year
    return None, None

def get_week_schedule(week, year):
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week={week}&year={year}&seasontype=2"
    resp = requests.get(url)
    if resp.status_code != 200:
        return pd.DataFrame()
    data = resp.json()
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
    week, year = find_next_upcoming_week_and_year()
    if not week or not year:
        print("Could not detect the next upcoming NFL week and year.")
        return
    print(f"Next upcoming NFL week is Week {week} of {year}.")

    schedule_df = get_week_schedule(week, year)
    if schedule_df.empty:
        print(f"No games scheduled for Week {week} of {year}.")
        return

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
