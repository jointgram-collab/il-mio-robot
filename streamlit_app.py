import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V15.1.17", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. COSTANTI ---
API_KEYS = ['01f1c8f2a314814b17de03eeb6c53623', '55f08c25f38fa1006dd9e66282170e1a']
# Lista base (che verrà ignorata se non si trovano risultati GG/NG)
BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "William Hill", "888sport", "Unibet", "Betfair"]

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie",
    "soccer_spain_la_liga": "🇪🇸 La Liga", "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_france_ligue_1": "🇫🇷 Ligue 1", "soccer_uefa_europa_league": "🇪🇺 Europa League",
    "soccer_uefa_champions_league": "🏆 Champions"
}

MARKET_MAP = {
    "Goal/No Goal": "both_teams_to_score",
    "Under/Over 2.5": "totals",
    "Esito Finale (1X2)": "h2h"
}

if 'api_data' not in st.session_state: st.session_state['api_data'] = []
if 'res' not in st.session_state: st.session_state['res'] = "Verifica..."

# --- 3. FUNZIONE CHIAMATA ---
def fetch_api(endpoint, p_extra={}):
    for k in API_KEYS:
        p = {'api_key': k, 'regions': 'eu', 'oddsFormat': 'decimal'}
        p.update(p_extra)
        try:
            r = requests.get(endpoint, params=p, timeout=12)
            if r.status_code == 200:
                st.session_state['res'] = r.headers.get('x-requests-remaining', "N/D")
                return r.json()
        except: continue
    return None

# --- 4. INTERFACCIA ---
st.title("🎯 AI SNIPER V15.1.17")

with st.sidebar:
    st.header("📊 Parametri")
    soglia = st.slider("Min Value %", 0, 15, 0) / 100
    st.info(f"API Residue: {st.session_state['res']}")

tab1, tab2 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO"])

with tab1:
    c1, c2, c3, c4 = st.columns([1.5, 1, 1.5, 0.8])
    sel_league = c1.selectbox("Campionato:", ["TUTTI"] + list(LEAGUE_NAMES.values()))
    sel_market = c2.selectbox("Mercato:", list(MARKET_MAP.keys()))
    ore = c4.selectbox("Fino a (Ore):", [24, 48, 72, 96, 120, 168], index=3) # Aggiunta una settimana intera
    
    if c3.button("🚀 AVVIA SCANNER", use_container_width=True, type="primary"):
        m_key = MARKET_MAP[sel_market]
        l_keys = [k for k, v in LEAGUE_NAMES.items() if v == sel_league or sel_league == "TUTTI"]
        
        all_matches = []
        bar = st.progress(0)
        for i, lk in enumerate(l_keys):
            data = fetch_api(f'https://api.the-odds-api.com/v4/sports/{lk}/odds/', {'markets': m_key})
            if data: all_matches.extend(data)
            bar.progress((i+1)/len(l_keys))
        st.session_state['api_data'] = all_matches
        st.rerun()

    if st.session_state['api_data']:
        m_key = MARKET_MAP[sel_market]
        found = 0
        
        st.write(f"Analizzando **{len(st.session_state['api_data'])}** eventi totali...")
        
        for m in st.session_state['api_data']:
            try:
                nome = f"{m['home_team']}-{m['away_team']}"
                dt = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
                if dt > datetime.utcnow() + timedelta(hours=ore): continue
                
                options = []
                for bk in m.get('bookmakers', []):
                    # FORZATURA: Se è GG/NG e non troviamo nulla coi soliti, apriamo a tutti i bookmaker
                    mkt = next((x for x in bk['markets'] if x['key'] == m_key), None)
                    if mkt:
                        for o in mkt['outcomes']:
                            if m_key == "totals" and o.get('point') != 2.5: continue
                            q = o['price']
                            val = ((1/q + 0.02) * q) - 1 # Margine ridottissimo per test
                            
                            if val >= soglia:
                                lbl = o['name']
                                if m_key == "both_teams_to_score":
                                    lbl = "GOAL (GG)" if o['name'].lower() in ["yes", "both"] else "NO GOAL (NG)"
                                options.append({"T": lbl, "Q": q, "V": val, "BK": bk['title']})
                
                if options:
                    found += 1
                    best = max(options, key=lambda x: x['V'])
                    col1, col2, col3, col4 = st.columns([3, 1.5, 1.5, 1])
                    col1.write(f"📅 {dt.strftime('%d/%m %H:%M')} | **{nome}**")
                    col2.write(f"🎯 {best['T']} @**{best['Q']}**")
                    col3.write(f"🏦 {best['BK']} ({round(best['V']*100,1)}%)")
                    col4.button("ADD", key=f"add_{nome}_{found}")
                    st.divider()
            except: continue
        
        if found == 0:
            st.warning("⚠️ Nessuna quota trovata nemmeno tra i bookmaker internazionali. È probabile che i dati non siano ancora disponibili nell'API per le date selezionate.")
