import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="AI SNIPER V15.1.19 - INQUISITOR", layout="wide")

API_KEYS = ['01f1c8f2a314814b17de03eeb6c53623', '55f08c25f38fa1006dd9e66282170e1a']
LEAGUES = ["soccer_italy_serie_a", "soccer_epl", "soccer_spain_la_liga"]

if 'results_gg' not in st.session_state: st.session_state['results_gg'] = []
if 'results_1x2' not in st.session_state: st.session_state['results_1x2'] = []

def check_data(market):
    data_found = []
    for k in API_KEYS:
        url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/" # Test su Premier League (più fornita)
        p = {'api_key': k, 'regions': 'eu', 'markets': market, 'oddsFormat': 'decimal'}
        try:
            r = requests.get(url, params=p, timeout=5)
            if r.status_code == 200: return r.json()
        except: continue
    return []

st.title("🕵️ AI SNIPER - TEST INCROCIATO")

if st.button("🔍 VERIFICA DISPONIBILITÀ DATI (1X2 vs GG/NG)", type="primary"):
    with st.spinner("Interrogazione API..."):
        st.session_state['results_1x2'] = check_data("h2h")
        st.session_state['results_gg'] = check_data("both_teams_to_score")
    st.rerun()

col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Mercato 1X2")
    if st.session_state['results_1x2']:
        st.success(f"✅ OK! Trovati {len(st.session_state['results_1x2'])} match con quote 1X2.")
        for m in st.session_state['results_1x2'][:3]: st.write(f"- {m['home_team']} vs {m['away_team']}")
    else: st.error("❌ Nessun dato 1X2 disponibile.")

with col2:
    st.subheader("⚽ Mercato Goal/No Goal")
    if st.session_state['results_gg']:
        st.success(f"✅ OK! Trovati {len(st.session_state['results_gg'])} match con quote GG/NG.")
        # Verifica se ci sono quote reali dentro
        has_odds = any(len(m.get('bookmakers', [])) > 0 for m in st.session_state['results_gg'])
        if not has_odds: st.warning("⚠️ Match trovati, ma i bookmaker hanno le quote GG/NG vuote.")
    else:
        st.error("❌ L'API non restituisce proprio il mercato GG/NG.")
        st.info("Questo conferma che i bookmaker non hanno ancora inviato i dati al server API.")
