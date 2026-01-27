import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="AI SNIPER V12.1 - AutoDiscovery", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

if 'api_data' not in st.session_state: st.session_state['api_data'] = []
BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "William Hill", "888sport"]

# Campionati Standard
LEAGUE_MAP = {
    "🇮🇹 Serie A": "soccer_italy_serie_a",
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League": "soccer_epl",
    "🇪🇸 La Liga": "soccer_spain_la_liga",
    "🇩🇪 Bundesliga": "soccer_germany_bundesliga",
    "🇪🇺 Europa League": "soccer_uefa_europa_league"
}

def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        return df.dropna(subset=["Match"]) if df is not None else pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
    except: return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

# --- FUNZIONE AUTO-DISCOVERY CHAMPIONS ---
def get_champions_key():
    try:
        r = requests.get(f'https://api.the-odds-api.com/v4/sports/?api_key={API_KEY}')
        if r.status_code == 200:
            sports = r.json()
            # Cerca qualsiasi sport che contenga "Champions League" nel titolo
            for s in sports:
                if "Champions League" in s.get('title', ''):
                    return s.get('key')
        return "soccer_uefa_champions_league" # Fallback
    except: return "soccer_uefa_champions_league"

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V12.1")
df_attuale = carica_db()

with st.sidebar:
    st.header("⚙️ Impostazioni")
    budget_cassa = st.number_input("Budget (€)", value=500.0)
    rischio = st.slider("Kelly", 0.05, 0.50, 0.20)
    soglia_val = st.slider("Valore Min %", -1, 10, 2) / 100 # Abbassata per vedere TUTTO

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    c1, c2, c3 = st.columns(3)
    ore_ricerca = c3.select_slider("Ore:", options=[24, 48, 72, 96, 120], value=120)
    
    if c1.button("🚀 SCANSIONE TOTALE"):
        all_data = []
        keys_to_scan = list(LEAGUE_MAP.values())
        keys_to_scan.append(get_champions_key()) # Aggiunge la chiave dinamica
        
        for k in set(keys_to_scan):
            r = requests.get(f'https://api.the-odds-api.com/v4/sports/{k}/odds/', 
                             params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
            if r.status_code == 200: all_data.extend(r.json())
            time.sleep(0.5)
        st.session_state['api_data'] = all_data
        st.rerun()

    if c2.button("🏆 FORZA CHAMPIONS"):
        ckey = get_champions_key()
        st.info(f"Cerco match con chiave: {ckey}")
        r = requests.get(f'https://api.the-odds-api.com/v4/sports/{ckey}/odds/', 
                         params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
        if r.status_code == 200:
            data = r.json()
            if not data: st.error("L'API dice: Zero match con quote Over/Under 2.5 per la Champions.")
            else: st.session_state['api_data'] = data
        st.rerun()

    st.divider()

    # Visualizzazione
    if st.session_state['api_data']:
        now = datetime.utcnow()
        limit = now + timedelta(hours=ore_ricerca)
        for i, m in enumerate(st.session_state['api_data']):
            try:
                m_time = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
                if not (now <= m_time <= limit): continue
                
                nome_m = f"{m['home_team']}-{m['away_team']}"
                opts = []
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_EURO_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == 'totals'), None)
                        if mk:
                            q_ov = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and float(o.get('point',0)) == 2.5), None)
                            q_un = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and float(o.get('point',0)) == 2.5), None)
                            if q_ov and q_un:
                                margin = (1/q_ov) + (1/q_un)
                                opts.append({"T": "OVER 2.5", "Q": q_ov, "P": ((1/q_ov)/margin)+0.06, "BK": b['title']})
                
                if opts:
                    best = max(opts, key=lambda x: (x['P'] * x['Q']) - 1)
                    val = (best['P'] * best['Q']) - 1
                    if val >= soglia_val:
                        col_a, col_b = st.columns([3, 1])
                        col_a.write(f"📅 {m_time.strftime('%d/%m %H:%M')} | **{nome_m}** | {m['sport_title']}")
                        col_a.caption(f"Valore: {round(val*100,1)}% | {best['BK']}")
                        if col_b.button(f"ADD {best['Q']}", key=f"btn_{i}"):
                            # Logica salvataggio...
                            pass
            except: continue
