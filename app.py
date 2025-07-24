import streamlit as st
import pandas as pd
from datetime import datetime

ELO_FILE = "nfl_team_elo_final.csv"

@st.cache_data
def load_elo_data():
    df = pd.read_csv(ELO_FILE)
    df = df.rename(columns={'Unnamed: 0': 'team'}) if 'Unnamed: 0' in df.columns else df
    df = df.sort_values(by='elo', ascending=False)
    return df

@st.cache_data
def load_predictions():
    import glob
    import os
    files = glob.glob("nfl_elo_predictions.xlsx")
    if not files:
        return pd.DataFrame()
    latest_file = max(files, key=os.path.getctime)
    return pd.read_csv(latest_file)

st.sidebar.title("NFL ELO Dashboard")
st.sidebar.markdown("Powered by your custom ELO model.")

st.title("🏈 NFL Team ELO Ratings & Predictions")

elos = load_elo_data()
st.subheader("Current Team ELO Ratings")
st.dataframe(elos.reset_index(drop=True))

pred_df = load_predictions()
if pred_df.empty:
    st.warning("No upcoming game predictions found. Run `predict_elo_games.py` first.")
else:
    st.subheader(f"Upcoming Games & ELO Predictions (Week {pred_df['week'].iloc[0]})")
    pred_df['home_win_prob_pct'] = (pred_df['home_win_prob'] * 100).round(1)
    pred_df['away_win_prob_pct'] = (pred_df['away_win_prob'] * 100).round(1)

    def format_pred(row):
        winner = row['predicted_winner']
        home = row['home_team']
        away = row['away_team']
        return (
            f"{away} @ {home} — "
            f"{home} win: {row['home_win_prob_pct']}%, "
            f"{away} win: {row['away_win_prob_pct']}%, "
            f"Predicted winner: **{winner}**"
        )

    st.markdown("\n".join(pred_df.apply(format_pred, axis=1).tolist()))

st.markdown("---")
st.markdown("Built with ❤️ using Streamlit")
