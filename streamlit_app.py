import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="AI SNIPER V15.1.18", layout="wide")

API_KEYS = ['01f1c8f2a314814b17de03eeb6c53623', '55f08c25f38fa1006dd9e66282170e1a']
LEAGUE_KEYS = [
    "soccer_italy_serie_a", "soccer_italy_serie_b", "soccer_epl", 
    "soccer_spain_la_liga", "soccer_germany_bundesliga", "soccer_france_ligue_1"
]

if 'data_raw' not in st.session_state: st.session_state['data_raw'] = []
if 'status' not in st.session_state: st.session_state['status'] = "Pronto"

# --- LOGICA API ---
def scarica_dati(market):
    results = []
    for key in API_KEYS:
        for league in LEAGUE_KEYS:
            url = f"https://api.the-odds-api.com/v4/sports/{league}/odds/"
            params = {'api_key': key, 'regions': 'eu', 'markets': market, 'oddsFormat': 'decimal'}
            try:
                r = requests.get(url, params=params, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    results.extend(data)
                    st.session_state['status'] = f"OK - Residue: {r.headers.get('x-requests-remaining')}"
            except: continue
        if results: break 
    return results

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V15.1.18 - DEBUG MODE")

with st.sidebar:
    st.write(f"**Stato API:** {st.session_state['status']}")
    ore_limite = st.slider("Fino a ore:", 12, 168, 72)
    min_val = st.slider("Min Value %", 0, 10, 0)

m_scelto = st.selectbox("Seleziona Mercato per Test:", ["both_teams_to_score", "h2h", "totals"])

if st.button("🔥 FORZA SCANSIONE TOTALE", type="primary", use_container_width=True):
    with st.spinner("Estrazione dati in corso..."):
        st.session_state['data_raw'] = scarica_dati(m_scelto)
    st.rerun()

# --- DISPLAY ---
if st.session_state['data_raw']:
    st.write(f"Trovati {len(st.session_state['data_raw'])} match grezzi. Analisi quote...")
    for m in st.session_state['data_raw']:
        try:
            match_name = f"{m['home_team']} vs {m['away_team']}"
            for bk in m['bookmakers']:
                for mkt in bk['markets']:
                    if mkt['key'] == m_scelto:
                        for o in mkt['outcomes']:
                            # Traduzione rapida per visualizzazione
                            scelta = o['name']
                            if m_scelto == "both_teams_to_score":
                                scelta = "GOAL (GG)" if o['name'].lower() in ["yes", "both"] else "NO GOAL (NG)"
                            
                            col1, col2, col3 = st.columns([3, 1, 1])
                            col1.write(f"🏟️ {match_name}")
                            col2.write(f"🎯 **{scelta}**")
                            col3.write(f"🏦 {bk['title']} @**{o['price']}**")
            st.divider()
        except: continue
else:
    st.warning("Nessun dato presente. Clicca sul tasto rosso sopra.")
    
