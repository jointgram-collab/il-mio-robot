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

# --- FUNZIONI ---
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
    val = (prob * quota) - 1
    if val <= 0: return 0
    return round(budget * (val / (quota - 1)) * frazione, 2)

# --- SIDEBAR ---
st.sidebar.title("TARGET 5000 EURO")
bankroll = st.sidebar.number_input("Budget Attuale (€)", value=1000)
frazione_kelly = st.sidebar.slider("Rischio (Kelly)", 0.05, 0.5, 0.15)
soglia_valore = st.sidebar.slider("Filtro Valore (Minimo %)", 0.0, 10.0, 1.0) / 100

leagues_map = {
    "ITALIA: Serie A": "soccer_italy_serie_a", 
    "UK: Premier League": "soccer_england_league_1", 
    "SPAGNA: La Liga": "soccer_spain_la_liga",
    "GERMANIA: Bundesliga": "soccer_germany_bundesliga",
    "FRANCIA: Ligue 1": "soccer_france_ligue_1",
    "EUROPA: Champions": "soccer_uefa_champs_league"
}

tab1, tab2, tab3 = st.tabs(["🔍 SCANNER", "📖 DIARIO", "📊 TARGET"])

with tab1:
    sel_league = st.selectbox("Campionato", list(leagues_map.keys()))
    if st.button("AVVIA RICERCA"):
        API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
        url = f'https://api.the-odds-api.com/v4/sports/{leagues_map[sel_league]}/odds/'
        params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'h2h,totals,btts', 'oddsFormat': 'decimal'}
        
        try:
            res = requests.get(url, params=params)
            
            if res.status_code != 200:
                st.error(f"Errore API {res.status_code}: {res.text}")
            else:
                data = res.json()
                if not data:
                    st.warning("Nessuna partita trovata per questo campionato oggi.")
                else:
                    st.success(f"Dati Ricevuti! Crediti rimasti: {res.headers.get('x-requests-remaining')}")
                    found = False
                    for m in data:
                        home, away = m['home_team'], m['away_team']
                        if not m.get('bookmakers'): continue
                        bk = m['bookmakers'][0]
                        
                        q1, qX, q2, qO, qGG = 1.0, 1.0, 1.0, 1.0, 1.0
                        for mk in bk['markets']:
                            if mk['key'] == 'h2h':
                                q1 = next((o['price'] for o in mk['outcomes'] if o['name'] == home), 1.0)
                                q2 = next((o['price'] for o in mk['outcomes'] if o['name'] == away), 1.0)
                                qX = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Draw'), 1.0)
                            elif mk['key'] == 'totals':
                                qO = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over'), 1.0)
                            elif mk['key'] == 'btts':
                                qGG = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Yes'), 1.0)

                        p1, pX, p2, pO, pGG = get_poisson_probs(1.65, 1.25)
                        opzioni = [
                            {"tipo": "1", "q": q1, "v": (p1*q1)-1, "p": p1},
                            {"tipo": "X", "q": qX, "v": (pX*qX)-1, "p": pX},
                            {"tipo": "2", "q": q2, "v": (p2*q2)-1, "p": p2},
                            {"tipo": "OVER 2.5", "q": qO, "v": (pO*qO)-1, "p": pO},
                            {"tipo": "GOAL", "q": qGG, "v": (pGG*qGG)-1, "p": pGG}
                        ]
                        best = max(opzioni, key=lambda x: x['v'])
                        
                        if best['v'] > soglia_valore:
                            found = True
                            stake = calc_stake(best['p'], best['q'], bankroll, frazione_kelly)
                            col_a, col_b = st.columns([3, 1])
                            col_a.write(f"**{home}-{away}** | {best['tipo']} @ {best['q']} (Valore: {round(best['v']*100,1)}%)")
                            if col_b.button("REGISTRA", key=f"btn_{home}_{best['tipo']}"):
                                st.session_state.diario.append({"Match": f"{home}-{away}", "Giocata": best['tipo'], "Quota": best['q'], "Stake": stake, "Esito": "IN CORSO"})
                                st.rerun()
                    if not found: st.info("Nessuna opportunità con il filtro attuale.")
        except Exception as e:
            st.error(f"Errore di sistema: {e}")

with tab2:
    if st.session_state.diario:
        for i, b in enumerate(st.session_state.diario):
            st.write(f"{b['Match']} - {b['Giocata']} @ {b['Quota']} - {b['Esito']}")
            if st.button("ELIMINA", key=f"del_{i}"):
                st.session_state.diario.pop(i)
                st.rerun()
    else: st.info("Diario vuoto.")

with tab3:
    st.write("Analisi Target: In fase di implementazione dati...")
