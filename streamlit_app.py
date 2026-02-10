import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V15.1.25", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. COSTANTI ---
API_KEYS = ['01f1c8f2a314814b17de03eeb6c53623', '55f08c25f38fa1006dd9e66282170e1a']
BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "William Hill", "888sport", "Unibet", "Betfair"]
OBIETTIVO_TARGET = 5000.0

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
if 'api_usage' not in st.session_state: st.session_state['api_usage'] = {'remaining': "Verifica...", 'active_index': 0}

# --- 3. FUNZIONI CORE ---
def fetch_api(endpoint, p_extra={}):
    idx = st.session_state['api_usage']['active_index']
    for attempt in range(len(API_KEYS)):
        current_idx = (idx + attempt) % len(API_KEYS)
        current_key = API_KEYS[current_idx]
        p = {'api_key': current_key, 'regions': 'eu', 'oddsFormat': 'decimal'}
        p.update(p_extra)
        try:
            r = requests.get(endpoint, params=p, timeout=12)
            if r.status_code == 200:
                st.session_state['api_usage']['remaining'] = r.headers.get('x-requests-remaining', "N/D")
                st.session_state['api_usage']['active_index'] = current_idx
                return r.json()
        except: continue
    return None

def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        return df.dropna(subset=["Match"]) if df is not None else pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

def chiudi_gara(idx, esito, risultato_score="-"):
    df = carica_db()
    if idx in df.index:
        q, s = float(df.at[idx, 'Quota']), float(df.at[idx, 'Stake'])
        df.at[idx, 'Esito'], df.at[idx, 'Risultato'] = esito, risultato_score
        df.at[idx, 'Profitto'] = round((s * q) - s, 2) if esito == "VINTO" else -s
        salva_db(df); st.rerun()

# --- 4. INTERFACCIA ---
st.title("🎯 AI SNIPER V15.1.25")
df_attuale = carica_db()

with st.sidebar:
    st.header("📊 Parametri")
    budget_cassa = st.number_input("Budget Attuale (€)", value=500.0)
    rischio_kelly = st.slider("Aggressività Kelly", 0.05, 0.50, 0.15)
    soglia_valore = st.slider("Min Value %", 0, 15, 0) / 100
    st.divider()
    st.info(f"💳 API Residue: **{st.session_state['api_usage']['remaining']}**")
    st.success(f"🔌 API Attiva: **Slot {st.session_state['api_usage']['active_index'] + 1}**")

tab1, tab2, tab3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 DASHBOARD FISCALE"])

# --- TAB 1: SCANNER ---
with tab1:
    c1, c2, c3, c4 = st.columns([1.5, 1, 1.5, 0.8])
    sel_league = c1.selectbox("Campionato:", ["TUTTI"] + list(LEAGUE_NAMES.values()))
    sel_market = c2.selectbox("Mercato:", list(MARKET_MAP.keys()))
    ore = c4.selectbox("Fino a (Ore):", [24, 48, 72, 96, 120, 168], index=3)
    
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
        giocate_esistenti = set(zip(df_attuale['Match'], df_attuale['Scelta']))
        found = 0
        for m in st.session_state['api_data']:
            try:
                nome = f"{m['home_team']}-{m['away_team']}"
                dt = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
                if dt > datetime.utcnow() + timedelta(hours=ore): continue
                
                # Raccogliamo TUTTE le opzioni valide per questa partita
                match_options = []
                for bk in m.get('bookmakers', []):
                    if bk['title'] in BK_EURO_AUTH:
                        mkt = next((x for x in bk['markets'] if x['key'] == m_key), None)
                        if mkt:
                            for o in mkt['outcomes']:
                                if m_key == "totals" and o.get('point') != 2.5: continue
                                q, marg = o['price'], (0.03 if m_key == "both_teams_to_score" else 0.06)
                                val = ((1/q + marg) * q) - 1
                                if val >= soglia_valore:
                                    lbl = o['name']
                                    if m_key == "both_teams_to_score":
                                        lbl = "GOAL (GG)" if o['name'].lower() in ["yes", "both"] else "NO GOAL (NG)"
                                    elif m_key == "totals":
                                        lbl = f"{o['name'].upper()} 2.5"
                                    match_options.append({"T": lbl, "Q": q, "V": val, "BK": bk['title']})
                
                # --- LOGICA SINGLE SIGNAL ---
                if match_options:
                    # Selezioniamo SOLO la migliore opzione assoluta per questa partita
                    best_signal = max(match_options, key=lambda x: x['V'])
                    found += 1
                    
                    stk = round(max(2.0, min(budget_cassa * (best_signal['V']/(best_signal['Q']-1)) * rischio_kelly, budget_cassa*0.15)), 2)
                    
                    col1, col2, col3, col4 = st.columns([3, 1.5, 1.5, 1])
                    col1.write(f"📅 {dt.strftime('%d/%m %H:%M')} | **{nome}**")
                    col2.write(f"🎯 **{best_signal['T']}** @**{best_signal['Q']}**")
                    col3.write(f"🏛️ {best_signal['BK']} ({round(best_signal['V']*100,1)}%)")
                    
                    if (nome, best_signal['T']) in giocate_esistenti:
                        col4.button("✅", key=f"ok_{nome}_{found}", disabled=True)
                    elif col4.button("ADD", key=f"add_{nome}_{found}"):
                        nuova = pd.DataFrame([{
                            "Data Match": dt.strftime('%d/%m %H:%M'), "Match": nome, "Scelta": best_signal['T'], 
                            "Quota": best_signal['Q'], "Stake": stk, "Bookmaker": best_signal['BK'], 
                            "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": m['sport_key'], "Risultato": "-"
                        }])
                        salva_db(pd.concat([df_attuale, nuova], ignore_index=True)); st.rerun()
                    st.divider()
            except: continue
