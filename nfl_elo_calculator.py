import pandas as pd
import math
from collections import defaultdict
import requests

BASE_ELO = 1500
K = 20
HOME_ADVANTAGE = 65
REVERSION_FACTOR = 0.75
CURRENT_SEASON = 2025
SEASON_WINDOW = [2022, 2023, 2024]

def expected_score(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

def update_elo(winner_elo, loser_elo, margin):
    expected_win = expected_score(winner_elo, loser_elo)
    multiplier = math.log(abs(margin) + 1) * (2.2 / ((winner_elo - loser_elo) * 0.001 + 2.2))
    return K * multiplier * (1 - expected_win)

def regress_elos(elos):
    for team in elos:
        elos[team] = REVERSION_FACTOR * elos[team] + (1 - REVERSION_FACTOR) * BASE_ELO

def fetch_espn_games(season):
    all_games = []
    for week in range(1, 19):
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?year={season}&week={week}&seasontype=2"
        resp = requests.get(url)
        if resp.status_code != 200:
            continue
        data = resp.json()
        for event in data.get("events", []):
            competition = event["competitions"][0]
            teams = competition["competitors"]
            home = [t for t in teams if t["homeAway"] == "home"][0]
            away = [t for t in teams if t["homeAway"] == "away"][0]
            home_score = int(home.get("score", 0)) if home.get("score") else None
            away_score = int(away.get("score", 0)) if away.get("score") else None
            status = event["status"]["type"]["state"]
            if status == "post" and home_score is not None and away_score is not None:
                all_games.append({
                    "season": season,
                    "week": week,
                    "date": event["date"],
                    "home_team": home["team"]["displayName"],
                    "away_team": away["team"]["displayName"],
                    "home_score": home_score,
                    "away_score": away_score
                })
    return pd.DataFrame(all_games)

def calculate_team_elos(games_df):
    elos = defaultdict(lambda: BASE_ELO)
    elo_history = []
    current_season = None

    for _, game in games_df.iterrows():
        season = game['season']
        week = game['week']

        if week == 1 and season != current_season:
            regress_elos(elos)
            current_season = season

        home = game['home_team']
        away = game['away_team']
        home_score = game['home_score']
        away_score = game['away_score']

        if pd.isna(home_score) or pd.isna(away_score):
            continue

        home_elo = elos[home] + HOME_ADVANTAGE
        away_elo = elos[away]
        margin = abs(home_score - away_score)

        if home_score > away_score:
            change = update_elo(home_elo, away_elo, margin)
            elos[home] += change
            elos[away] -= change
        else:
            change = update_elo(away_elo, home_elo, margin)
            elos[away] += change
            elos[home] -= change

        elo_history.append({
            'season': season,
            'week': week,
            'date': game['date'],
            'home_team': home,
            'away_team': away,
            'home_score': home_score,
            'away_score': away_score,
            'home_elo': elos[home],
            'away_elo': elos[away]
        })

    return pd.DataFrame(elo_history), elos

# Load past 3 years from local CSV
past_df = pd.read_csv("nfl_game_results.csv").sort_values(by=['season', 'week'])
past_df = past_df[past_df['season'].isin(SEASON_WINDOW)]

# Fetch completed games from current season (live from ESPN)
current_df = fetch_espn_games(CURRENT_SEASON)

# Combine and calculate
all_games = pd.concat([past_df, current_df]).sort_values(by=['season', 'week'])
elo_history_df, final_elos = calculate_team_elos(all_games)

# Save outputs
elo_history_df.to_csv("nfl_elo_history.csv", index=False)
pd.DataFrame.from_dict(final_elos, orient='index', columns=['elo']).sort_values(by='elo', ascending=False).to_csv("nfl_team_elo_final.csv")

print("✅ ELO ratings (2022–2024 + live 2025) calculated and saved.")
