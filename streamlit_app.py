import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime

# --- CONFIGURAZIONE ---
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
st.set_page_config(page_title="AI Sniper Global - Obiettivo 5000€", layout="wide")

st.title("🎯 AI Sniper Global Scanner")
bankroll = st.sidebar.number_input("Capitale Operativo (€)", value=1000)
frazione_kelly = st.sidebar.slider("Livello Rischio (Kelly)", 0.05, 0.5, 0.2)

# --- MAPPA CAMPIONATI ESTESA ---
leagues_map = {
    "🇮🇹 Serie A": "soccer_italy_serie_a",
    "🇮🇹 Serie B": "soccer_italy_serie_b",
    "🇪🇺 Champions League": "soccer_uefa_champs_league",
    "🇪🇺 Europa League": "soccer_uefa_europa_league",
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League": "soccer_england_league_1",
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Championship (UK 2)": "soccer_england_league_2",
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 League One (UK 3)": "soccer_england_league_3",
    "🇫🇷 Ligue 1": "soccer_france_ligue_1",
    "🇫🇷 Ligue 2": "soccer_france_ligue_2",
    "🇩🇪 Bundesliga": "soccer_germany_bundesliga",
    "🇩🇪 Bundesliga 2": "soccer_germany_bundesliga_2",
    "🇪🇸 La Liga": "soccer_spain_la_liga",
    "🇪🇸 La Liga 2": "soccer_spain_segunda_division",
    "🇳🇱 Eredivisie": "soccer_netherlands_eredivisie"
}

selected_label = st.selectbox("Seleziona Competizione", list(leagues_map.keys()))
league_id = leagues_map[selected_label]

# --- MOTORE DI CALCOLO ---
def get_poisson_probs(h_exp, a_exp):
    m = np.outer(poisson.pmf(range(7), h_exp), poisson.pmf(range(7), a_exp))
    p1 = np.sum(np.tril(m, -1))
    pX = np.sum(np.diag(m))
    p2 = np.sum(np.triu(m, 1))
    p_over = 1 - (m[0,0] + m[0,1] + m[0,2] + m[1,0] + m[1,1] + m[2,0])
    p_gg = (1 - poisson.pmf(0, h_exp)) * (1 - poisson.pmf(0, a_exp))
    return p1, pX, p2, p_over, p_gg

def calc_stake(prob, quota, budget, frazione):
    if quota <= 1.05: return 0
    value = (prob * quota) - 1
    if value <= 0: return 0
    kelly = value / (quota - 1)
    return round(budget * kelly * frazione, 2)

# --- SCANSIONE ---
if st.button("🔍 AVVIA SCANSIONE INTERNAZIONALE"):
    url = f'https://api.the-odds-api.com/v4/sports/{league_id}/odds/'
    params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'h2h,totals,btts', 'oddsFormat': 'decimal'}
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if not data or 'error' in str(data):
            st.warning("Dati non disponibili o limite API raggiunto.")
        else:
            formatted_results = []
            for match in data:
                home, away = match['home_team'], match['away_team']
                q1, qX, q2, qO, qGG = 1.0, 1.0, 1.0, 1.0, 1.0
                
                if match.get('bookmakers'):
                    for m in match['bookmakers'][0]['markets']:
                        if m['key'] == 'h2h':
                            q1 = next((o['price'] for o in m['outcomes'] if o['name'] == home), 1.0)
                            q2 = next((o['price'] for o in m['outcomes'] if o['name'] == away), 1.0)
                            qX = next((o['price'] for o in m['outcomes'] if o['name'] == 'Draw'), 1.0)
                        elif m['key'] == 'totals':
                            qO = next((o['price'] for o in m['outcomes'] if o['name'] == 'Over'), 1.0)
                        elif m['key'] == 'btts':
                            qGG = next((o['price'] for o in m['outcomes'] if o['name'] == 'Yes'), 1.0)

                # Probabilità basate su medie generali (Poisson)
                p1, pX, p2, pO, pGG = get_poisson_probs(1.6, 1.2)
                
                valori = [
                    {"tipo": "1", "q": q1, "v": (p1*q1)-1, "p": p1},
                    {"tipo": "2", "q": q2, "v": (p2*q2)-1, "p": p2},
                    {"tipo": "OVER 2.5", "q": qO, "v": (pO*qO)-1, "p": pO},
                    {"tipo": "GG", "q": qGG, "v": (pGG*qGG)-1, "p": pGG}
                ]
                
                best = max(valori, key=lambda x: x['v'])
                
                if best['v'] > 0.05:
                    stake = calc_stake(best['p'], best['q'], bankroll, frazione_kelly)
                    formatted_results.append({
                        "PARTITA": f"{home} - {away}",
                        "GIOCATA": f"🎯 {best['tipo']} ({best['q']}) - Punta €{stake}",
                        "VALUE": f"+{best['v']*100:.1f}%"
                    })

            if formatted_results:
                df = pd.DataFrame(formatted_results)
                st.table(df.style.set_properties(**{
                    'background-color': '#28a745',
                    'color': 'white',
                    'font-weight': 'bold',
                    'border-color': 'white'
                }))
            else:
                st.info("Nessun errore di quota trovato con valore > 5%.")
    except Exception as e:
        st.error(f"Errore tecnico: {e}")
