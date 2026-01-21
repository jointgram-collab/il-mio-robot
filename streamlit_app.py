import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime

# --- CONFIGURAZIONE ---
API_KEY = 'f93dcdc217a2d3b8a2c2a91df05a7553'
st.set_page_config(page_title="AI Total Scanner 2026", layout="wide")

st.title("🚀 AI Multi-Market Scanner")
bankroll = st.sidebar.number_input("Budget Totale (€)", value=3000)

leagues_map = {
    "Serie A": "soccer_italy_serie_a",
    "Serie B": "soccer_italy_serie_b",
    "Champions League": "soccer_uefa_champs_league",
    "Premier League": "soccer_england_league_1"
}

selected_league = st.selectbox("Seleziona Campionato", list(leagues_map.keys()))

def calculate_value(prob, quota):
    return (prob * quota) - 1

# --- SCANSIONE LIVE ---
if st.button("Avvia Scansione Completa"):
    # Chiediamo tutti i mercati: h2h (1X2), totals (U/O), btts (GG/NG)
    url = f'https://api.the-odds-api.com/v4/sports/{leagues_map[selected_league]}/odds/'
    params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'}
    
    with st.spinner("Analizzando i mercati in tempo reale..."):
        try:
            response = requests.get(url, params=params)
            data = response.json()
        except:
            st.error("Errore di connessione con l'API.")
            data = []
        
        if not data or 'error' in str(data):
            st.warning("Nessun dato disponibile o limite API raggiunto.")
        else:
            final_list = []
            for match in data:
                # 1. Gestione Sicura Data e Ora
                commence_time = match.get('commence_time', "")
                if commence_time:
                    date_obj = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                    data_ora = date_obj.strftime("%d/%m %H:%M")
                else:
                    data_ora = "N/D"
                
                home = match['home_team']
                away = match['away_team']
                
                # Inizializziamo le variabili per le quote
                q1, qX, q2 = 1.0, 1.0, 1.0
                q_over, q_under = 1.0, 1.0
                q_gg, q_ng = 1.0, 1.0
                
                # 2. Estrazione Quote dai vari mercati
                if match.get('bookmakers'):
                    markets = match['bookmakers'][0].get('markets', [])
                    for m in markets:
                        if m['key'] == 'h2h':
                            q1 = next((o['price'] for o in m['outcomes'] if o['name'] == home), 1.0)
                            q2 = next((o['price'] for o in m['outcomes'] if o['name'] == away), 1.0)
                            qX = next((o['price'] for o in m['outcomes'] if o['name'] == 'Draw'), 1.0)
                        elif m['key'] == 'totals':
                            q_over = next((o['price'] for o in m['outcomes'] if o['name'] == 'Over'), 1.0)
                            q_under = next((o['price'] for o in m['outcomes'] if o['name'] == 'Under'), 1.0)
                        elif m['key'] == 'btts':
                            q_gg = next((o['price'] for o in m['outcomes'] if o['name'] == 'Yes'), 1.0)
                            q_ng = next((o['price'] for o in m['outcomes'] if o['name'] == 'No'), 1.0)

                # 3. Calcolo Valore (Esempio con probabilità fisse per test stabilità)
                # In produzione qui riattiveremo il motore Poisson
                v1 = calculate_value(0.40, q1)
                v_over = calculate_value(0.52, q_over)
                v_gg = calculate_value(0.50, q_gg)

                final_list.append({
                    "Orario": data_ora,
                    "Partita": f"{home} - {away}",
                    "1X2": f"1:{q1} | X:{qX} | 2:{q2}",
                    "U/O 2.5": f"U:{q_under} | O:{q_over}",
                    "GG/NG": f"GG:{q_gg} | NG:{q_ng}",
                    "Value Migliore": f"{max(v1, v_over, v_gg)*100:.1f}%"
                })
            
            df_res = pd.DataFrame(final_list)
            st.table(df_res)
