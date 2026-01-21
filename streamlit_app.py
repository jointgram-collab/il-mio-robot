import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests

# --- CONFIGURAZIONE ---
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
st.set_page_config(page_title="AI Betting Scanner PRO", layout="wide")

st.title("🤖 AI Value Bet Auto-Scanner")
st.sidebar.header("Impostazioni Bankroll")
bankroll = st.sidebar.number_input("Budget Totale (€)", value=3000)

# Mappatura Campionati per API e per Dati Storici
leagues_map = {
    "Serie A": {"api": "soccer_italy_serie_a", "csv": "I1"},
    "Serie B": {"api": "soccer_italy_serie_b", "csv": "I2"},
    "Premier League": {"api": "soccer_uefa_champs_league", "csv": "E0"}, # Esempio Champions per test
    "Champions League": {"api": "soccer_uefa_champs_league", "csv": "CL"}
}

selected_league = st.selectbox("Seleziona Campionato da Scansionare", list(leagues_map.keys()))

# --- 1. CARICAMENTO DATI STORICI (Per il Modello AI) ---
@st.cache_data
def get_historical_data(code):
    try:
        url = f"https://www.football-data.co.uk/mmz4281/2526/{code}.csv"
        df = pd.read_csv(url)
        return df[['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']].dropna()
    except:
        st.error("Dati storici non disponibili per questo campionato.")
        return None

# --- 2. MOTORE DI CALCOLO POISSON ---
def calculate_poisson_probs(h_team, a_team, df):
    # Protezione: se df è vuoto o None, usa medie standard
    if df is None or df.empty:
        exp_h = 1.5  # Media gol casa standard
        exp_a = 1.2  # Media gol trasferta standard
    else:
        try:
            avg_h = df['FTHG'].mean()
            avg_a = df['FTAG'].mean()
            
            att_h = df.groupby('HomeTeam')['FTHG'].mean().get(h_team, 1.0) / avg_h
            def_h = df.groupby('HomeTeam')['FTAG'].mean().get(h_team, 1.0) / avg_a
            att_a = df.groupby('AwayTeam')['FTAG'].mean().get(a_team, 1.0) / avg_a
            def_a = df.groupby('AwayTeam')['FTHG'].mean().get(a_team, 1.0) / avg_h
            
            exp_h = att_h * def_a * avg_h
            exp_a = att_a * def_h * avg_a
        except:
            exp_h, exp_a = 1.5, 1.2

    m = np.outer(poisson.pmf(range(6), exp_h), poisson.pmf(range(6), exp_a))
    return np.sum(np.tril(m, -1)), np.sum(np.diag(m)), np.sum(np.triu(m, 1))
    
    # Calcolo forza squadre (gestione errori se squadra nuova)
    try:
        att_h = df.groupby('HomeTeam')['FTHG'].mean()[h_team] / avg_h
        def_h = df.groupby('HomeTeam')['FTAG'].mean()[h_team] / avg_a
        att_a = df.groupby('AwayTeam')['FTAG'].mean()[a_team] / avg_a
        def_a = df.groupby('AwayTeam')['FTHG'].mean()[a_team] / avg_h
        
        exp_h = att_h * def_a * avg_h
        exp_a = att_a * def_h * avg_a
        
        m = np.outer(poisson.pmf(range(6), exp_h), poisson.pmf(range(6), exp_a))
        return np.sum(np.tril(m, -1)), np.sum(np.diag(m)), np.sum(np.triu(m, 1))
    except:
        return 0.33, 0.33, 0.33 # Default se mancano dati

# --- 3. SCANSIONE QUOTE REALI (Via API) ---
def fetch_real_odds(sport_key):
    url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds/'
    params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'h2h'}
    res = requests.get(url, params=params)
    return res.json()

# --- 4. ESECUZIONE SCANNER ---
hist_df = get_historical_data(leagues_map[selected_league]['csv'])

if st.button("Avvia Scansione Mercati Live"):
    with st.spinner("L'AI sta analizzando i bookmaker..."):
        odds_data = fetch_real_odds(leagues_map[selected_league]['api'])
        
        results = []
        for match in odds_data:
            h_team = match['home_team']
            a_team = match['away_team']
            
            # Calcolo Probabilità AI
            p1, pX, p2 = calculate_poisson_probs(h_team, a_team, hist_df)
            
            # Prendi la quota migliore tra i bookmaker
            all_odds = match['bookmakers'][0]['markets'][0]['outcomes']
            q1 = next(o['price'] for o in all_odds if o['name'] == h_team)
            q2 = next(o['price'] for o in all_odds if o['name'] == a_team)
            qX = next(o['price'] for o in all_odds if o['name'] == 'Draw')
            
            # Trova Valore
            v1 = (p1 * q1) - 1
            vX = (pX * qX) - 1
            v2 = (p2 * q2) - 1
            
            results.append({
                "Partita": f"{h_team} vs {a_team}",
                "1": q1, "X": qX, "2": q2,
                "Value Max": max(v1, vX, v2),
                "Segno Consigliato": ["1", "X", "2"][np.argmax([v1, vX, v2])]
            })
            
        if results:
            res_df = pd.DataFrame(results)
            st.write("### Opportunità Rilevate")
            
            def highlight_value(s):
                return ['background-color: #90ee90' if v > 0.05 else '' for v in s]
            
            st.table(res_df.style.apply(highlight_value, subset=['Value Max']))
            
            # Suggerimento Kelly per la migliore
            best_bet = res_df.loc[res_df['Value Max'].idxmax()]
            if best_bet['Value Max'] > 0:
                quota = best_bet[best_bet['Segno Consigliato']]
                prob = best_bet['Value Max'] + 1 / quota # Ricavo prob dal value
                stake = ((best_bet['Value Max']) / (quota - 1)) * 0.25 * bankroll
                st.success(f"🔥 MIGLIOR GIOCATA: {best_bet['Partita']} - Segno {best_bet['Segno Consigliato']} - Punta {stake:.2f}€")
        else:
            st.warning("Nessuna partita trovata al momento per questo campionato.")
