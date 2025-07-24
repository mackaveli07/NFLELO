import requests
import pandas as pd

HOME_ADVANTAGE = 65
ELO_FILE = "nfl_team_elo_final.csv"
FORCED_YEAR = 2025  # Explicitly use 2025
SEASON_TYPE = 2     # 2 = regular season

def predict_win_prob(home_elo, away_elo):
    home_elo += HOME_ADVANTAGE
    return 1 / (1 + 10 ** ((away_elo - home_elo) / 400))

def find_first_valid_week(year):
    for week in range(1, 19):  # Regular season weeks 1-18
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week={week}&year={year}&seasontype={SEASON_TYPE}"
        resp = requests.get(url)
        if resp.status_code != 200:
            continue
        data = resp.json()
        events = data.get("events", [])
        if not events:
            continue
        for event in events:
            state = event.get("status", {}).get("type", {}).get("state", "")
            if state == "pre":  # Game hasn't started yet
                return week
    return None

def get_week_schedule(week, year):
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week={week}&year={year}&seasontype={SEASON_TYPE}"
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
    year = FORCED_YEAR
    week = find_first_valid_week(year)
    if not week:
        print(f"No upcoming *regular season* games found for {year}.")
        return

    print(f"📅 Predicting Week {week} of {year} regular season...")

    schedule_df = get_week_schedule(week, year)
    if schedule_df.empty:
        print("No games scheduled.")
        return

    predictions = []
    for _, row in schedule_df.iterrows():
        home = row['home_team']
        away = row['away_team']
        home_elo = elos.get(home, 1500)
        away_elo = elos.get(away, 1500)
        home_win_prob = predict_win_prob(home_elo, away_elo)
        predictions.append({
            'season': year,
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
    pred_df.to_excel("nfl_elo_predictions.xlsx", index=False)
    print("✅ Saved to nfl_elo_predictions.xlsx")
    print(pred_df[['home_team', 'away_team', 'home_win_prob', 'away_win_prob', 'predicted_winner']])

if __name__ == "__main__":
    predict_upcoming_games()
