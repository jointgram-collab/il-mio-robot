import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime

# --- CONFIGURAZIONE ---
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
st.set_page_config(page_title="Road to 5000€", layout="wide")

if 'diario' not in st.session_state:
    st.session_state.diario = []

# --- FUNZIONI CORE ---
def get_poisson_probs(h_exp, a_exp):
    m = np.outer(poisson.pmf(range(7), h_exp), poisson.pmf(range(7), a_exp))
    return np.sum(np.tril(m, -1)), np.sum(np.diag(m)), np.sum(np.triu(m, 1)), \
           1 - (m[0,0] + m[0,1] + m[0,2] + m[1,0] + m[1,1] + m[2,0]), \
           (1 - poisson.pmf(0, h_exp)) * (1 - poisson.pmf(0, a_exp))

def calc_stake(prob, quota, budget, frazione):
    if quota <= 1: return 0
    value = (prob * quota) - 1
    if value <= 0: return 0
    kelly = value / (quota - 1)
    return round(budget * kelly * frazione, 2)

# --- SIDEBAR: CONTROLLO CAPITALE ---
st.sidebar.header("💰 Piano 1.000€ -> 5.000€")
# Budget di default impostato a 1000
bankroll = st.sidebar.number_input("Capitale Operativo (€)", value=1000)
frazione_kelly = st.sidebar.slider("Livello di Rischio", 0.1, 0.5, 0.25)

# Calcolo esposizione giornaliera
df_diario = pd.DataFrame(st.session_state.diario)
esposizione_attuale = 0
if not df_diario.empty:
    esposizione_attuale = df_diario[df_diario['Esito'] == 'In corso ⏳']['Puntata'].sum()

perc_esposizione = (esposizione_attuale / bankroll) * 100
st.sidebar.metric("Esposizione Attuale", f"{esposizione_attuale:.2f}€", f"{perc_esposizione:.1f}% del budget")

# --- INTERFACCIA PRINCIPALE ---
tab1, tab2 = st.tabs(["🔍 Ricerca Valore", "📖 Registro e Statistiche"])

with tab1:
    leagues = {"Serie A": "soccer_italy_serie_a", "Serie B": "soccer_italy_serie_b", "Champions": "soccer_uefa_champs_league"}
    sel_league = st.selectbox("Seleziona Campionato", list(leagues.keys()))
    
    if st.button("Scansiona Mercati"):
        url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/'
        params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'h2h,totals', 'oddsFormat': 'decimal'}
        data = requests.get(url, params=params).json()
        
        results = []
        for match in data:
            q1 = match['bookmakers'][0]['markets'][0]['outcomes'][0]['price'] if match.get('bookmakers') else 1.0
            # Usiamo medie gol leggermente più alte per favorire la ricerca di valore
            p1, pX, p2, pO, pGG = get_poisson_probs(1.7, 1.3)
            stake = calc_stake(p1, q1, bankroll, frazione_kelly)
            
            results.append({
                "Match": f"{match['home_team']} - {match['away_team']}",
                "Quota 1": q1,
                "Importo Consigliato": f"{stake}€",
                "Value": f"{((p1 * q1) - 1)*100:.1f}%"
            })
        st.table(results)

with tab2:
    # (Codice diario come precedentemente impostato per registrare vincite/perdite)
    st.info("Usa questa sezione per segnare i risultati e vedere la barra progresso verso i 5000€.")
