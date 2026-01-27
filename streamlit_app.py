import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V12.0 - God Mode", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

if 'api_usage' not in st.session_state:
    st.session_state['api_usage'] = {'remaining': "N/D", 'used': "N/D"}
if 'api_data' not in st.session_state:
    st.session_state['api_data'] = []

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "William Hill", "888sport"]

# MAPPING AGGRESSIVO: Più chiavi per la stessa competizione per non fallire mai
LEAGUE_KEYS = {
    "🇮🇹 Serie A": ["soccer_italy_serie_a"],
    "🇮🇹 Serie B": ["soccer_italy_serie_b"],
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League": ["soccer_epl"],
    "🇪🇸 La Liga": ["soccer_spain_la_liga"],
    "🏆 Champions League": ["soccer_uefa_champions_league", "soccer_champions_league"], # Doppia chiave!
    "🇪🇺 Europa League": ["soccer_uefa_europa_league", "soccer_europa_league"],
    "🇩🇪 Bundesliga": ["soccer_germany_bundesliga"],
    "🇫🇷 Ligue 1": ["soccer_france_ligue_1"]
}

def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        return df.dropna(subset=["Match"]) if df is not None else pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V12.0")
df_attuale = carica_db()

with st.sidebar:
    st.header("📊 Stato API")
    c1, c2 = st.columns(2)
    c1.metric("Residui", st.session_state['api_usage']['remaining'])
    c2.metric("Usati", st.session_state['api_usage']['used'])
    st.divider()
    budget_cassa = st.number_input("Budget (€)", value=500.0)
    rischio = st.slider("Kelly Criterion", 0.05, 0.50, 0.20)
    soglia_val = st.slider("Valore Min %", 0, 15, 2) / 100 # Abbassata a 2% per test

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    c_sel, c_btn_all, c_slider = st.columns([1, 1, 1])
    sel_name = c_sel.selectbox("Campionato Singolo:", list(LEAGUE_KEYS.keys()))
    ore_ricerca = c_slider.select_slider("Finestra (ore):", options=[24, 48, 72, 96, 120, 168], value=120)
    
    if c_btn_all.button("🚀 SCANSIONE TOTALE", use_container_width=True):
        all_found = []
        progress = st.progress(0)
        status_msg = st.empty()
        
        # Iteriamo su tutte le chiavi nel dizionario
        total_steps = sum(len(keys) for keys in LEAGUE_KEYS.values())
        current_step = 0
        
        for name, keys in LEAGUE_KEYS.items():
            for k in keys:
                status_msg.text(f"Scansione: {name} ({k})...")
                try:
                    r = requests.get(f'https://api.the-odds-api.com/v4/sports/{k}/odds/', 
                                   params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'}, timeout=10)
                    if r.status_code == 200:
                        data = r.json()
                        if data: all_found.extend(data)
                        st.session_state['api_usage']['remaining'] = r.headers.get('x-requests-remaining')
                    time.sleep(0.4)
                except: pass
                current_step += 1
                progress.progress(current_step / total_steps)
        
        st.session_state['api_data'] = all_found
        status_msg.success(f"Analisi completata! {len(all_found)} match in memoria.")
        st.rerun()

    if c_sel.button("🔍 Scansiona Singolo", use_container_width=True):
        single_data = []
        for k in LEAGUE_KEYS[sel_name]:
            res = requests.get(f'https://api.the-odds-api.com/v4/sports/{k}/odds/', 
                               params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
            if res.status_code == 200:
                d = res.json()
                if d: single_data.extend(d)
        st.session_state['api_data'] = single_data
        st.rerun()

    st.divider()

    if st.session_state['api_data']:
        now = datetime.utcnow()
        limit = now + timedelta(hours=ore_ricerca)
        found_valore = False
        
        for i, m in enumerate(st.session_state['api_data']):
            try:
                m_time = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
                if not (now <= m_time <= limit): continue
                
                nome_m = f"{m['home_team']}-{m['away_team']}"
                dt_m = m_time.strftime("%d/%m %H:%M")
                
                opts = []
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_EURO_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == 'totals'), None)
                        if mk:
                            # Cerchiamo Over 2.5 con gestione decimale flessibile
                            q_ov = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and float(o.get('point',0)) == 2.5), None)
                            q_un = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and float(o.get('point',0)) == 2.5), None)
                            if q_ov and q_un:
                                margin = (1/q_ov) + (1/q_un)
                                opts.append({"T": "OVER 2.5", "Q": q_ov, "P": ((1/q_ov)/margin)+0.06, "BK": b['title']})
                
                if opts:
                    best = max(opts, key=lambda x: (x['P'] * x['Q']) - 1)
                    val = (best['P'] * best['Q']) - 1
                    
                    if val >= soglia_val:
                        found_valore = True
                        stk_c = round(max(2.0, min(budget_cassa * (val/(best['Q']-1)) * rischio, budget_cassa*0.15)), 2)
                        c_info, c_add = st.columns([3, 1])
                        c_info.markdown(f"📅 {dt_m} | **{nome_m}** <br>🏆 {m['sport_title']} | **{best['BK']}** | Val: **{round(val*100,1)}%**", unsafe_allow_html=True)
                        if c_add.button(f"ADD @{best['Q']}", key=f"add_{nome_m}_{i}"):
                            nuova = pd.DataFrame([{"Data Match": dt_m, "Match": nome_m, "Scelta": best['T'], "Quota": best['Q'], "Stake": stk_c, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": m['sport_key'], "Risultato": "-"}])
                            salva_db(pd.concat([carica_db(), nuova], ignore_index=True))
                            st.rerun()
                        st.divider()
            except: continue

# --- TAB 2 & 3 rimangono invariati ---
