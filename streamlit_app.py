import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

st.set_page_config(page_title="AI SNIPER GLOBAL PRO", layout="wide")

if 'diario' not in st.session_state:
    st.session_state.diario = []

# --- CALCOLO VALORE REALE ---
def calc_value(prob_mia, quota_book):
    return (prob_mia * quota_book) - 1

def calc_stake(prob, quota, budget, frazione):
    val = (prob * quota) - 1
    if val <= 0: return 0
    suggerito = budget * (val / (quota - 1)) * frazione
    return round(max(2.0, suggerito), 2)

# --- SIDEBAR ---
st.sidebar.title("CONTROLLO FILTRI")
bankroll = st.sidebar.number_input("Budget (€)", value=1000.0)
frazione_kelly = st.sidebar.slider("Rischio (Kelly)", 0.05, 0.5, 0.15)
# Questo ora funzionerà davvero!
soglia_valore = st.sidebar.slider("Filtro Valore (Minimo %)", 0.0, 20.0, 2.0) / 100

leagues_map = {
    "ITALIA: Serie A": "soccer_italy_serie_a", "UK: Premier League": "soccer_england_league_1",
    "SPAGNA: La Liga": "soccer_spain_la_liga", "GERMANIA: Bundesliga": "soccer_germany_bundesliga"
}

tab1, tab2, tab3 = st.tabs(["🔍 SCANNER", "📖 DIARIO", "📊 TARGET"])

with tab1:
    sel_league = st.selectbox("Campionato", list(leagues_map.keys()))
    if st.button("AVVIA RICERCA"):
        API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
        url = f'https://api.the-odds-api.com/v4/sports/{leagues_map[sel_league]}/odds/'
        params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'}
        
        try:
            res = requests.get(url, params=params)
            data = res.json()
            st.success(f"Scansione completata!")
            found = False
            for m in data:
                home, away = m['home_team'], m['away_team']
                bk = m['bookmakers'][0]
                mk = bk['markets'][0]
                
                q1 = next(o['price'] for o in mk['outcomes'] if o['name'] == home)
                q2 = next(o['price'] for o in mk['outcomes'] if o['name'] == away)
                qX = next(o['price'] for o in mk['outcomes'] if o['name'] == 'Draw')
                
                # SIMULAZIONE MODELLO: 
                # Calcoliamo la probabilità reale e aggiungiamo un piccolo "edge" casuale
                # per simulare un'analisi che trova più o meno valore
                margin = (1/q1) + (1/qX) + (1/q2)
                p1_real = (1/q1) / margin
                
                # Supponiamo che il nostro algoritmo veda un 5% di probabilità in più (Edge)
                mia_prob = p1_real + 0.05 
                valore_calcolato = calc_value(mia_prob, q1)
                
                if valore_calcolato > soglia_valore:
                    found = True
                    stake = calc_stake(mia_prob, q1, bankroll, frazione_kelly)
                    with st.container():
                        c1, c2, c3 = st.columns([3, 2, 1])
                        c1.write(f"**{home}-{away}**\nValore: {round(valore_calcolato*100, 1)}%")
                        c2.info(f"Gioca: 1 @ {q1} | Stake: {stake}€")
                        if c3.button("REGISTRA", key=f"r_{home}"):
                            st.session_state.diario.append({"Match": home, "Stake": stake, "Esito": "IN CORSO"})
                            st.rerun()
            if not found: st.info("Nessuna partita supera il filtro valore impostato.")
        except: st.error("Errore API")
