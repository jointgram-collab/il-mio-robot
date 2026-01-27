import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V11.65 - Ultra Stable", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

if 'api_usage' not in st.session_state:
    st.session_state['api_usage'] = {'remaining': "N/D", 'used': "N/D"}
if 'api_data' not in st.session_state:
    st.session_state['api_data'] = []

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "William Hill", "888sport"]

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie",
    "soccer_spain_la_liga": "🇪🇸 La Liga", "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_uefa_champions_league": "🇪🇺 Champions", "soccer_france_ligue_1": "🇫🇷 Ligue 1"
}

# --- MOTORE DATABASE ---
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
st.title("🎯 AI SNIPER V11.65")
df_attuale = carica_db()

with st.sidebar:
    st.header("📊 Stato API")
    c1, c2 = st.columns(2)
    c1.metric("Residui", st.session_state['api_usage']['remaining'])
    c2.metric("Usati", st.session_state['api_usage']['used'])
    st.divider()
    budget_cassa = st.number_input("Budget (€)", value=500.0)
    rischio = st.slider("Kelly", 0.05, 0.50, 0.20)
    soglia_val = st.slider("Valore Min %", 0, 15, 5) / 100

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER ---
with t1:
    c_sel, c_btn_tot, c_slider = st.columns([1, 1, 1])
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    sel_name = c_sel.selectbox("Campionato Singolo:", list(leagues.keys()))
    ore_ricerca = c_slider.select_slider("Finestra (ore):", options=[24, 48, 72, 96, 120], value=120)
    
    if c_btn_tot.button("🚀 SCANSIONE TOTALE", use_container_width=True):
        all_matches = []
        progress_bar = st.progress(0)
        status = st.empty()
        
        # Svuota i dati vecchi prima di iniziare
        st.session_state['api_data'] = []
        
        for idx, (l_name, l_key) in enumerate(LEAGUE_NAMES.items()):
            status.text(f"Scansione in corso: {l_name}...")
            try:
                # Chiamata API
                res = requests.get(
                    f'https://api.the-odds-api.com/v4/sports/{l_key}/odds/', 
                    params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'},
                    timeout=15
                )
                if res.status_code == 200:
                    data = res.json()
                    all_matches.extend(data)
                    st.session_state['api_usage']['remaining'] = res.headers.get('x-requests-remaining')
                    st.session_state['api_usage']['used'] = res.headers.get('x-requests-used')
                
                # PAUSA DI SICUREZZA PER EVITARE BLOCCHI
                time.sleep(0.6) 
                
            except Exception as e:
                st.warning(f"Salto {l_name} per timeout.")
            
            progress_bar.progress((idx + 1) / len(LEAGUE_NAMES))
        
        # Filtro temporale
        now = datetime.utcnow()
        limit = now + timedelta(hours=ore_ricerca)
        
        filtered = []
        for m in all_matches:
            try:
                m_time = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
                if now <= m_time <= limit:
                    filtered.append(m)
            except: continue
            
        st.session_state['api_data'] = filtered
        status.success(f"Analisi completata: trovati {len(filtered)} match.")
        st.rerun()

    # Visualizzazione Risultati (Logica identica alla singola che funziona)
    if st.session_state['api_data']:
        pend_list = df_attuale[df_attuale['Esito'] == "Pendente"]['Match'].tolist()
        found = False
        for m in st.session_state['api_data']:
            try:
                nome_m = f"{m['home_team']}-{m['away_team']}"
                dt_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
                sport_key = m['sport_key']
                
                opts = []
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_EURO_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == 'totals'), None)
                        if mk:
                            q_ov = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), None)
                            q_un = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), None)
                            if q_ov and q_un:
                                margin = (1/q_ov) + (1/q_un)
                                opts.append({"T": "OVER 2.5", "Q": q_ov, "P": ((1/q_ov)/margin)+0.06, "BK": b['title']})
                
                if opts:
                    best = max(opts, key=lambda x: (x['P'] * x['Q']) - 1)
                    val = (best['P'] * best['Q']) - 1
                    if val >= soglia_val:
                        found = True
                        stk_c = round(max(2.0, min(budget_cassa * (val/(best['Q']-1)) * rischio, budget_cassa*0.15)), 2)
                        c_a, c_b = st.columns([3, 1])
                        c_a.write(f"📅 {dt_m} | **{nome_m}** ({LEAGUE_NAMES.get(sport_key, 'Cup')}) | Val: **{round(val*100,1)}%** | {best['BK']}")
                        if c_b.button(f"ADD {best['Q']}", key=f"add_{nome_m}_{sport_key}"):
                            nuova = pd.DataFrame([{"Data Match": dt_m, "Match": nome_m, "Scelta": best['T'], "Quota": best['Q'], "Stake": stk_c, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": sport_key, "Risultato": "-"}])
                            salva_db(pd.concat([carica_db(), nuova], ignore_index=True))
                            st.rerun()
            except: continue
        if not found: st.info("Nessun match con valore trovato. Prova ad abbassare la soglia %.")
