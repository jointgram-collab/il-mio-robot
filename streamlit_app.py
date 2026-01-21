import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson

# Configurazione Grafica
st.set_page_config(page_title="AI Profit Engine 2026", layout="wide")
st.title("💰 AI Value Betting System")
st.markdown("---")

# 1. SELEZIONE CAMPIONATO
leagues = {
    "Serie A (Italia)": "I1",
    "Premier League (Inghilterra)": "E0",
    "La Liga (Spagna)": "SP1",
    "Bundesliga (Germania)": "D1",
    "Ligue 1 (Francia)": "F1"
    }

with st.sidebar:
    st.header("Impostazioni")
    league_name = st.selectbox("Scegli Campionato", list(leagues.keys()))
    bankroll = st.number_input("Budget Totale (€)", value=3000)
    st.info("Regola: Punta solo quando il Valore è positivo.")

# 2. CARICAMENTO DATI AUTOMATICO
@st.cache_data
def load_data(code):
    url = f"https://www.football-data.co.uk/mmz4281/2526/{code}.csv"
    df = pd.read_csv(url)
    return df[['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']].dropna()

try:
    data = load_data(leagues[league_name])
    teams = sorted(data['HomeTeam'].unique())
    
    col1, col2 = st.columns(2)
    with col1:
        h_team = st.selectbox("Casa", teams)
    with col2:
        a_team = st.selectbox("Trasferta", teams, index=1)

    # 3. MOTORE STATISTICO
    def get_probs(h, a, df):
        avg_h = df['FTHG'].mean()
        avg_a = df['FTAG'].mean()
        
        att_h = df.groupby('HomeTeam')['FTHG'].mean()[h] / avg_h
        def_h = df.groupby('HomeTeam')['FTAG'].mean()[h] / avg_a
        att_a = df.groupby('AwayTeam')['FTAG'].mean()[a] / avg_a
        def_a = df.groupby('AwayTeam')['FTHG'].mean()[a] / avg_h
        
        exp_h = att_h * def_a * avg_h
        exp_a = att_a * def_h * avg_a
        
        m = np.outer(poisson.pmf(range(7), exp_h), poisson.pmf(range(7), exp_a))
        
        p1, pX, p2 = np.sum(np.tril(m, -1)), np.sum(np.diag(m)), np.sum(np.triu(m, 1))
        p_under = m[0,0]+m[0,1]+m[0,2]+m[1,0]+m[1,1]+m[2,0]
        return p1, pX, p2, 1-p_under, p_under

    p1, pX, p2, p_over, p_under = get_probs(h_team, a_team, data)

    # 4. INPUT QUOTE E CALCOLO VALORE
    st.subheader("Inserisci Quote Bookmaker")
    c1, c2, c3, c4, c5 = st.columns(5)
    q1 = c1.number_input("Quota 1", 1.01, 50.0, 2.0)
    qX = c2.number_input("Quota X", 1.01, 50.0, 3.0)
    q2 = c3.number_input("Quota 2", 1.01, 50.0, 3.5)
    qo = c4.number_input("Quota Over 2.5", 1.01, 10.0, 1.8)
    qu = c5.number_input("Quota Under 2.5", 1.01, 10.0, 1.9)

    # 5. RISULTATI FINALI
    st.markdown("### Risultati Analisi")
    res = pd.DataFrame({
        "Esito": ["1", "X", "2", "Over 2.5", "Under 2.5"],
        "Probabilità AI": [p1, pX, p2, p_over, p_under],
        "Quota Bookie": [q1, qX, q2, qo, qu]
    })
    res["Value %"] = (res["Probabilità AI"] * res["Quota Bookie"] - 1) * 100
    
    def color_val(val):
        return 'background-color: #d4edda' if val > 0 else ''

    st.table(res.style.applymap(color_val, subset=['Value %']))

    for i, r in res.iterrows():
        if r["Value %"] > 0:
            k = ((r["Probabilità AI"] * r["Quota Bookie"] - 1) / (r["Quota Bookie"] - 1)) * 0.25
            st.success(f"🎯 VALORE TROVATO su {r['Esito']}! Punta: {max(0, bankroll*k):.2f}€")

except Exception as e:
    st.error(f"Seleziona squadre valide o attendi aggiornamento dati. Errore: {e}")
