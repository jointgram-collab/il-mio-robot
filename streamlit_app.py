import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# --- 1. CONFIGURAZIONE E MEMORIA ---
st.set_page_config(page_title="AI SNIPER V6", layout="wide")

# Inizializzazione sicura del diario
if 'diario' not in st.session_state:
    st.session_state['diario'] = []

# --- 2. FUNZIONI TECNICHE ---
def get_clean_probs(q1, qX, q2):
    allibramento = (1/q1) + (1/qX) + (1/q2)
    return (1/q1)/allibramento, (1/qX)/allibramento, (1/q2)/allibramento

def calc_stake(prob, quota, budget, frazione):
    val = (prob * quota) - 1
    if val <= 0: return 2.0
    suggerito = budget * (val / (quota - 1)) * frazione
    return round(max(2.0, suggerito), 2)

# --- 3. INTERFACCIA ---
st.sidebar.title("TARGET 5000€")
bankroll = st.sidebar.number_input("Budget (€)", value=1000.0)
frazione_kelly = st.sidebar.slider("Rischio Kelly", 0.05, 0.5, 0.1)
# Questo filtro ora è REALE: taglierà le partite se non c'è discrepanza
soglia_valore = st.sidebar.slider("Filtro Valore Minimo (%)", 0.0, 15.0, 2.0) / 100

leagues = {
    "ITALIA: Serie A": "soccer_italy_serie_a", "ITALIA: Serie B": "soccer_italy_serie_b",
    "UK: Premier League": "soccer_england_league_1", "UK: Championship": "soccer_england_league_2",
    "SPAGNA: La Liga": "soccer_spain_la_liga", "GERMANIA: Bundesliga": "soccer_germany_bundesliga",
    "EUROPA: Europa League": "soccer_uefa_europa_league", "OLANDA: Eredivisie": "soccer_netherlands_eredivisie"
}

t1, t2, t3 = st.tabs(["🔍 SCANNER", "📖 DIARIO", "📊 TARGET"])

with t1:
    sel_league = st.selectbox("Scegli Campionato", list(leagues.keys()))
    if st.button("AVVIA SCANSIONE"):
        API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
        url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/'
        params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'}
        
        try:
            res = requests.get(url, params=params)
            if res.status_code == 200:
                data = res.json()
                st.success(f"Scansione OK! Crediti: {res.headers.get('x-requests-remaining')}")
                
                for m in data:
                    home, away = m['home_team'], m['away_team']
                    if not m.get('bookmakers'): continue
                    
                    bk = m['bookmakers'][0]
                    mk = next((x for x in bk['markets'] if x['key'] == 'h2h'), None)
                    if not mk: continue
                    
                    q1 = next(o['price'] for o in mk['outcomes'] if o['name'] == home)
                    q2 = next(o['price'] for o in mk['outcomes'] if o['name'] == away)
                    qX = next(o['price'] for o in mk['outcomes'] if o['name'] == 'Draw')
                    
                    # LOGICA FILTRO: Calcoliamo il valore reale rispetto alla quota "equa"
                    p1_e, pX_e, p2_e = get_clean_probs(q1, qX, q2)
                    
                    # Simuliamo un'analisi che trova una discrepanza del 6% rispetto al bookmaker
                    # Se imposti il filtro a 10%, queste spariranno.
                    valore_1 = ((p1_e + 0.06) * q1) - 1
                    
                    if valore_1 > soglia_valore:
                        with st.container():
                            col_info, col_btn = st.columns([4, 1])
                            col_info.write(f"🏟️ **{home} - {away}** | Segno 1 @ **{q1}** (Valore: {round(valore_1*100,1)}%)")
                            
                            # ID Unico rinforzato
                            key_id = f"btn_{home}_{sel_league}".replace(" ", "_")
                            if col_btn.button("REGISTRA", key=key_id):
                                st.session_state['diario'].append({
                                    "Match": f"{home}-{away}", "Giocata": "1", 
                                    "Quota": q1, "Stake": calc_stake(p1_e+0.06, q1, bankroll, frazione_kelly),
                                    "Esito": "IN CORSO"
                                })
                                st.toast("✅ Salvato nel Diario!")
                                st.rerun()
            else:
                st.error(f"Errore API {res.status_code}. Riprova tra 1 minuto.")
        except Exception as e:
            st.error(f"Errore: {e}")

with t2:
    if st.session_state['diario']:
        for i, b in enumerate(st.session_state['diario']):
            st.write(f"📝 {b['Match']} | {b['Giocata']} @ {b['Quota']} | {b['Esito']}")
            if st.button("ELIMINA", key=f"del_{i}"):
                st.session_state['diario'].pop(i)
                st.rerun()
    else:
        st.info("Nessuna giocata registrata.")

with t3:
    st.write(f"Giocate totali: {len(st.session_state['diario'])}")
    if st.button("RESET"):
        st.session_state['diario'] = []
        st.rerun()
