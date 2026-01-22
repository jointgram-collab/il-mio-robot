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

# --- MOTORE CALCOLO PROBABILITÀ ---
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
    "ITALIA: Serie B": "soccer_italy_serie_b",
    "EUROPA: Champions": "soccer_uefa_champs_league", 
    "EUROPA: Europa League": "soccer_uefa_europa_league",
    "UK: Premier League": "soccer_england_league_1", 
    "UK: Championship": "soccer_england_league_2",
    "GERMANIA: Bundesliga": "soccer_germany_bundesliga",
    "SPAGNA: La Liga": "soccer_spain_la_liga", 
    "FRANCIA: Ligue 1": "soccer_france_ligue_1"
}

tab1, tab2, tab3 = st.tabs(["🔍 SCANNER VALORE", "📖 DIARIO LIVE", "📊 ANALISI TARGET"])

with tab1:
    sel_league = st.selectbox("Campionato", list(leagues_map.keys()))
    if st.button("AVVIA RICERCA OPPORTUNITÀ"):
        API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
        url = f'https://api.the-odds-api.com/v4/sports/{leagues_map[sel_league]}/odds/'
        params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'h2h,totals,btts', 'oddsFormat': 'decimal'}
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            if response.status_code == 200 and data:
                st.success(f"Scansione completata! Crediti rimasti: {response.headers.get('x-requests-remaining')}")
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
                        with st.container():
                            c1, c2, c3 = st.columns([3, 2, 1])
                            c1.markdown(f"⚽ **{home} - {away}**")
                            c1.caption(f"Bookmaker: {bk['title']}")
                            c2.markdown(f"🎯 `{best['tipo']}` @ **{best['q']}**")
                            c2.caption(f"Value: +{round(best['v']*100, 1)}% | Stake: {stake}€")
                            if c3.button("REGISTRA", key=f"add_{home}_{best['tipo']}"):
                                st.session_state.diario.append({
                                    "Data": datetime.now().strftime("%d/%m"), 
                                    "Match": f"{home}-{away}",
                                    "Giocata": best['tipo'], 
                                    "Quota": best['q'], 
                                    "Puntata": stake,
                                    "Esito": "IN CORSO", 
                                    "Ritorno": 0
                                })
                                st.rerun()
                if not found: st.info("Nessuna scommessa trovata con la soglia attuale.")
            else: st.error("Errore dati API.")
        except Exception as e: st.error(f"Errore: {e}")

with tab2:
    if st.session_state.diario:
        for i, bet in enumerate(st.session_state.diario):
            with st.expander(f"{bet['Match']} - {bet['Giocata']} ({bet['Esito']})"):
                c1, c2, c3 = st.columns(3)
                nuovo = c1.selectbox("Esito", ["IN CORSO", "VINTO", "PERSO"], key=f"e_{i}")
                if c2.button("SALVA", key=f"s_{i}"):
                    st.session_state.diario[i]['Esito'] = nuovo
                    st.session_state.diario[i]['Ritorno'] = bet['Puntata'] * bet['Quota'] if nuovo == "VINTO" else 0
                    st.rerun()
                if c3.button("ELIMINA", key=f"d_{i}"):
                    st.session_state.diario.pop(i)
                    st.rerun()
    else: st.info("Diario vuoto.")

with tab3:
    if st.session_state.diario:
        df = pd.DataFrame(st.session_state.diario)
        investito = df['Puntata'].sum()
        ritorno = df['Ritorno'].sum()
        netto = ritorno - investito
        c1, c2, c3 = st.columns(3)
        c1.metric("Giocato Totale", f"{investito:.2f}€")
        c2.metric("Vinto Totale", f"{ritorno:.2f}€")
        c3.metric("P/L NETTO", f"{netto:.2f}€", delta=f"{netto:.2f}€")
        if st.button("RESET TOTALE DIARIO"):
            st.session_state.diario = []
            st.rerun()
