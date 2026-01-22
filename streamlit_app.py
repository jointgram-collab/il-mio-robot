import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="AI SNIPER PRO - Real Time Control", layout="wide")

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
st.sidebar.title("TARGET 5000 EUR")
bankroll = st.sidebar.number_input("Budget Attuale", value=1000)
frazione_kelly = st.sidebar.slider("Rischio (Kelly)", 0.05, 0.5, 0.2)

# --- APP TABS ---
tab1, tab2, tab3 = st.tabs(["🔍 SCANNER LIVE", "📖 DIARIO E LIVE CONTROL", "📊 ANALISI TARGET"])

with tab1:
    st.header("Ricerca Occasioni e Invio Rapido")
    leagues = {"Serie A": "soccer_italy_serie_a", "Serie B": "soccer_italy_serie_b", "Champions": "soccer_uefa_champs_league", "Premier": "soccer_england_league_1"}
    sel_league = st.selectbox("Campionato", list(leagues.keys()))
    
    if st.button("TROVA VALUE BET"):
        API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
        url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/'
        params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'h2h,totals,btts', 'oddsFormat': 'decimal'}
        
        data = requests.get(url, params=params).json()
        for m in data:
            home, away = m['home_team'], m['away_team']
            if m.get('bookmakers'):
                bk = m['bookmakers'][0]
                q1 = next((o['price'] for market in bk['markets'] if market['key'] == 'h2h' for o in market['outcomes'] if o['name'] == home), 1.0)
                p1, pX, p2, pO, pGG = get_poisson_probs(1.7, 1.2)
                valore = (p1 * q1) - 1
                
                if valore > 0.06:
                    stake = calc_stake(p1, q1, bankroll, frazione_kelly)
                    with st.container():
                        c1, c2, c3 = st.columns([3, 2, 1])
                        c1.success(f"**{home} - {away}** | {bk['title'].upper()}")
                        c2.write(f"Giocata: SEGNO 1 @ {q1} | Puntata: {stake}€")
                        if c3.button("REGISTRA", key=f"btn_{home}"):
                            st.session_state.diario.append({
                                "Match": f"{home}-{away}", "Giocata": "1", "Quota": q1, "Puntata": stake,
                                "Esito": "IN CORSO", "Score": "0-0", "Ritorno": 0
                            })
                            st.toast("Scommessa aggiunta al Diario!")

with tab2:
    st.header("Controllo Scommesse Attive")
    if st.session_state.diario:
        for i, bet in enumerate(st.session_state.diario):
            with st.expander(f"{bet['Match']} - {bet['Score']}"):
                col1, col2, col3 = st.columns(3)
                nuovo_score = col1.text_input("Aggiorna Risultato (es. 1-0)", value=bet['Score'], key=f"score_{i}")
                nuovo_esito = col2.selectbox("Stato", ["IN CORSO", "VINTO", "PERSO"], key=f"status_{i}")
                
                # Logica Colore Live (Esempio per Segno 1)
                h_goals = int(nuovo_score.split('-')[0])
                a_goals = int(nuovo_score.split('-')[1])
                is_winning = h_goals > a_goals if bet['Giocata'] == "1" else False # Semplificato per Segno 1
                
                if nuovo_esito == "IN CORSO":
                    color = "green" if is_winning else "red"
                    st.markdown(f"<div style='background-color:{color}; padding:10px; border-radius:5px; color:white'>Live Status: {nuovo_score}</div>", unsafe_allow_html=True)
                
                if st.button("AGGIORNA DEFINITIVO", key=f"upd_{i}"):
                    st.session_state.diario[i]['Score'] = nuovo_score
                    st.session_state.diario[i]['Esito'] = nuovo_esito
                    st.session_state.diario[i]['Ritorno'] = bet['Puntata'] * bet['Quota'] if nuovo_esito == "VINTO" else 0
                    st.rerun()
    else:
        st.info("Nessuna scommessa registrata.")

with tab3:
    st.header("Statistiche Obiettivo 5000€")
    if st.session_state.diario:
        df = pd.DataFrame(st.session_state.diario)
        investito = df['Puntata'].sum()
        vinto = df['Ritorno'].sum()
        bilancio = vinto - investito
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Totale Giocato", f"{investito:.2f}€")
        c2.metric("Totale Vinto", f"{vinto:.2f}€")
        c3.metric("Profitto Netto", f"{bilancio:.2f}€", delta=f"{bilancio:.2f}€")
        
        st.progress(min(max((bilancio + bankroll)/5000, 0.0), 1.0), text="Progresso verso i 5000€")
        st.dataframe(df)
