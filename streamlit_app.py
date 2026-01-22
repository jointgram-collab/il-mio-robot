import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="AI SNIPER GLOBAL PRO", layout="wide")

if 'diario' not in st.session_state:
    st.session_state.diario = []

# --- MOTORE CALCOLO ---
def get_poisson_probs(h_exp, a_exp):
    m = np.outer(poisson.pmf(range(7), h_exp), poisson.pmf(range(7), a_exp))
    return np.sum(np.tril(m, -1)), np.sum(np.diag(m)), np.sum(np.triu(m, 1)), \
           1 - (m[0,0] + m[0,1] + m[0,2] + m[1,0] + m[1,1] + m[2,0]), \
           (1 - poisson.pmf(0, h_exp)) * (1 - poisson.pmf(0, a_exp))

def calc_stake(prob, quota, budget, frazione):
    if quota <= 1.05: return 0
    val = (prob * quota) - 1
    if val <= 0: return 0
    return round(budget * (val / (quota - 1)) * frazione, 2)

# --- SIDEBAR ---
st.sidebar.title("TARGET 5000 EURO")
bankroll = st.sidebar.number_input("Budget Attuale", value=1000)
frazione_kelly = st.sidebar.slider("Rischio (Kelly)", 0.05, 0.5, 0.15)

# --- MAPPA CAMPIONATI ---
leagues_map = {
    "ITALIA: Serie A": "soccer_italy_serie_a", "ITALIA: Serie B": "soccer_italy_serie_b",
    "EUROPA: Champions League": "soccer_uefa_champs_league", "EUROPA: Europa League": "soccer_uefa_europa_league",
    "UK: Premier League": "soccer_england_league_1", "UK: Championship": "soccer_england_league_2",
    "GERMANIA: Bundesliga": "soccer_germany_bundesliga", "SPAGNA: La Liga": "soccer_spain_la_liga",
    "FRANCIA: Ligue 1": "soccer_france_ligue_1", "OLANDA: Eredivisie": "soccer_netherlands_eredivisie"
}

tab1, tab2, tab3 = st.tabs(["🔍 SCANNER", "📖 DIARIO LIVE", "📊 ANALISI TARGET"])

with tab1:
    sel_league = st.selectbox("Seleziona Competizione", list(leagues_map.keys()))
    if st.button("AVVIA RICERCA"):
        API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
        url = f'https://api.the-odds-api.com/v4/sports/{leagues_map[sel_league]}/odds/'
        params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'h2h,totals,btts', 'oddsFormat': 'decimal'}
        try:
            data = requests.get(url, params=params).json()
            for m in data:
                home = m['home_team']
                if m.get('bookmakers'):
                    bk = m['bookmakers'][0]
                    q1 = next((o['price'] for market in bk['markets'] if market['key'] == 'h2h' for o in market['outcomes'] if o['name'] == home), 1.0)
                    p1, pX, p2, pO, pGG = get_poisson_probs(1.7, 1.2)
                    valore = (p1 * q1) - 1
                    if valore > 0.05:
                        stake = calc_stake(p1, q1, bankroll, frazione_kelly)
                        with st.container():
                            c1, c2, c3 = st.columns([3, 2, 1])
                            c1.info(f"**{m['home_team']} - {m['away_team']}**\n\n{bk['title'].upper()}")
                            c2.write(f"Giocata: 1 @ {q1}\n\nStake: {stake}€")
                            if c3.button("REGISTRA", key=f"add_{home}"):
                                st.session_state.diario.append({
                                    "Match": f"{m['home_team']}-{m['away_team']}", "Quota": q1, 
                                    "Puntata": stake, "Esito": "IN CORSO", "Ritorno": 0
                                })
                                st.rerun()
        except: st.error("Errore API")

with tab2:
    if st.session_state.diario:
        for i, bet in enumerate(st.session_state.diario):
            with st.expander(f"{bet['Match']} - {bet['Esito']}"):
                c1, c2, c3 = st.columns(3)
                nuovo_esito = c1.selectbox("Esito", ["IN CORSO", "VINTO", "PERSO"], key=f"es_{i}")
                if c2.button("AGGIORNA", key=f"up_{i}"):
                    st.session_state.diario[i]['Esito'] = nuovo_esito
                    st.session_state.diario[i]['Ritorno'] = bet['Puntata'] * bet['Quota'] if nuovo_esito == "VINTO" else 0
                    st.rerun()
                if c3.button("ELIMINA", key=f"del_{i}"):
                    st.session_state.diario.pop(i)
                    st.rerun()
    else: st.info("Diario vuoto.")

with tab3:
    if st.session_state.diario:
        df = pd.DataFrame(st.session_state.diario)
        netto = df['Ritorno'].sum() - df[df['Esito'] != 'IN CORSO']['Puntata'].sum()
        st.metric("Profitto Netto", f"{netto:.2f}€")
        if st.button("CANCELLA TUTTO IL DIARIO"):
            st.session_state.diario = []
            st.rerun()
