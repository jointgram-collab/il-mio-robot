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
    
    # Usiamo un tasto che resetta lo stato per evitare loop
    if st.button("AVVIA RICERCA"):
        API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
        url = f'https://api.the-odds-api.com/v4/sports/{leagues_map[sel_league]}/odds/'
        params = {
            'api_key': API_KEY,
            'regions': 'eu',
            'markets': 'h2h', # Inizia solo con 1x2 per risparmiare crediti
            'oddsFormat': 'decimal'
        }
        
        try:
            response = requests.get(url, params=params)
            # Vediamo cosa dice il server prima di elaborare
            if response.status_code == 401:
                st.error("ERRORE 401: Chiave API non valida. Controlla se è copiata bene.")
            elif response.status_code == 429:
                st.error("ERRORE 429: Crediti Esauriti! Hai superato i 500 limiti mensili.")
            elif response.status_code != 200:
                st.error(f"Errore Server: {response.status_code}")
            else:
                data = response.json()
                # ... resto del codice per mostrare i risultati ...
                if not data:
                    st.warning("Nessuna partita trovata per questo campionato al momento.")
                else:
                    st.success(f"Dati ricevuti con successo! Crediti residui stimati: {response.headers.get('x-requests-remaining', 'N/D')}")
                    # Mostra qui i tuoi risultati verdi
        except Exception as e:
            st.error(f"Errore di connessione: {e}")
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
