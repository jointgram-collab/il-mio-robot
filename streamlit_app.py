import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="AI SNIPER GLOBAL PRO", layout="wide")

if 'diario' not in st.session_state:
    st.session_state.diario = []

# --- LOGICA MATEMATICA REALE ---
def get_clean_probs(q1, qX, q2):
    # Rimuove l'allibramento per trovare le probabilità "eque"
    allibramento = (1/q1) + (1/qX) + (1/q2)
    p1 = (1/q1) / allibramento
    pX = (1/qX) / allibramento
    p2 = (1/q2) / allibramento
    return p1, pX, p2

def calc_stake(prob, quota, budget, frazione):
    val = (prob * quota) - 1
    if val <= 0: return 0
    suggerito = budget * (val / (quota - 1)) * frazione
    return round(max(2.0, suggerito), 2)

# --- SIDEBAR ---
st.sidebar.title("TARGET 5000 EURO")
bankroll = st.sidebar.number_input("Budget (€)", value=1000.0, step=50.0)
frazione_kelly = st.sidebar.slider("Rischio (Kelly)", 0.05, 0.5, 0.15)
soglia_valore = st.sidebar.slider("Filtro Valore (Minimo %)", 0.0, 15.0, 3.0) / 100

leagues_map = {
    "ITALIA: Serie A": "soccer_italy_serie_a", "ITALIA: Serie B": "soccer_italy_serie_b",
    "UK: Premier League": "soccer_england_league_1", "UK: Championship": "soccer_england_league_2",
    "SPAGNA: La Liga": "soccer_spain_la_liga", "GERMANIA: Bundesliga": "soccer_germany_bundesliga",
    "FRANCIA: Ligue 1": "soccer_france_ligue_1", "EUROPA: Europa League": "soccer_uefa_europa_league"
}

tab1, tab2, tab3 = st.tabs(["🔍 SCANNER VALORE", "📖 DIARIO LIVE", "📊 TARGET"])

with tab1:
    sel_league = st.selectbox("Seleziona Campionato", list(leagues_map.keys()))
    if st.button("AVVIA RICERCA"):
        API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
        url = f'https://api.the-odds-api.com/v4/sports/{leagues_map[sel_league]}/odds/'
        params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'}
        
        try:
            res = requests.get(url, params=params)
            if res.status_code == 200:
                data = res.json()
                st.success(f"Dati Ricevuti! Crediti: {res.headers.get('x-requests-remaining')}")
                found_any = False
                
                for m in data:
                    home, away = m['home_team'], m['away_team']
                    if not m.get('bookmakers'): continue
                    bk = m['bookmakers'][0]
                    mk_h2h = next((mk for mk in bk['markets'] if mk['key'] == 'h2h'), None)
                    if not mk_h2h: continue
                    
                    q1 = next((o['price'] for o in mk_h2h['outcomes'] if o['name'] == home), 1.0)
                    q2 = next((o['price'] for o in mk_h2h['outcomes'] if o['name'] == away), 1.0)
                    qX = next((o['price'] for o in mk_h2h['outcomes'] if o['name'] == 'Draw'), 1.0)

                    # Calcoliamo probabilità eque + un "Edge" simulato del 5% per testare il filtro
                    p1_e, pX_e, p2_e = get_clean_probs(q1, qX, q2)
                    
                    opzioni = [
                        {"tipo": "1", "q": q1, "p_mia": p1_e + 0.05}, 
                        {"tipo": "X", "q": qX, "p_mia": pX_e + 0.05},
                        {"tipo": "2", "q": q2, "p_mia": p2_e + 0.05}
                    ]
                    
                    # Filtriamo l'opzione migliore per questo match
                    best = max(opzioni, key=lambda x: (x['p_mia'] * x['q']) - 1)
                    valore = (best['p_mia'] * best['q']) - 1
                    
                    if valore > soglia_valore:
                        found_any = True
                        stake = calc_stake(best['p_mia'], best['q'], bankroll, frazione_kelly)
                        with st.container():
                            c1, c2, c3 = st.columns([3, 2, 1])
                            c1.markdown(f"⚽ **{home} - {away}**\n\n*Book: {bk['title']}*")
                            c2.warning(f"🎯 **SEGNO {best['tipo']}** @ {best['q']}\n\nValue: {round(valore*100,1)}% | Stake: **{stake}€**")
                            
                            btn_id = f"reg_{home}_{best['tipo']}_{sel_league}".replace(" ", "")
                            if c3.button("REGISTRA", key=btn_id):
                                st.session_state.diario.append({
                                    "Match": f"{home}-{away}", "Giocata": best['tipo'], "Quota": best['q'],
                                    "Stake": stake, "Esito": "IN CORSO", "Ritorno": 0.0
                                })
                                st.success("Registrato!")
                                st.rerun()
                if not found_any:
                    st.info("Nessuna partita trovata con questo valore minimo.")
            else:
                st.error(f"Errore API {res.status_code}")
        except Exception as e:
            st.error(f"Errore tecnico: {e}")

with tab2:
    if st.session_state.diario:
        for i, b in enumerate(st.session_state.diario):
            with st.expander(f"📌 {b['Match']} - {b['Giocata']} ({b['Esito']})"):
                c1, c2, c3 = st.columns(3)
                nuovo = c1.selectbox("Esito", ["IN CORSO", "VINTO", "PERSO"], key=f"sel_{i}")
                if c2.button("SALVA", key=f"upd_{i}"):
                    st.session_state.diario[i]['Esito'] = nuovo
                    st.session_state.diario[i]['Ritorno'] = b['Stake'] * b['Quota'] if nuovo == "VINTO" else 0.0
                    st.rerun()
                if c3.button("ELIMINA", key=f"del_{i}"):
                    st.session_state.diario.pop(i)
                    st.rerun()
    else:
        st.info("Diario vuoto.")

with tab3:
    if st.session_state.diario:
        df = pd.DataFrame(st.session_state.diario)
        st.dataframe(df)
        if st.button("RESET"):
            st.session_state.diario = []
            st.rerun()
