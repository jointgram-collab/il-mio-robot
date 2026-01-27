import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V11.50 - Full Radar", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
TARGET_FINALE = 5000.0

# Inizializzazione sessione
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
st.title("🎯 AI SNIPER V11.50")
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
    c_btn1, c_btn2 = st.columns([1, 1])
    
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    sel_name = c_btn1.selectbox("Campionato Singolo:", list(leagues.keys()))
    
    # PULSANTE SCANSIONE TOTALE 48H
    if c_btn2.button("🚀 SCANSIONE TOTALE (48H)", use_container_width=True, help="Scansiona tutti i campionati. Consuma circa 8 crediti."):
        all_data = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, (l_name, l_key) in enumerate(LEAGUE_NAMES.items()):
            status_text.text(f"Scansione {l_name}...")
            res = requests.get(f'https://api.the-odds-api.com/v4/sports/{l_key}/odds/', 
                               params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
            if res.status_code == 200:
                all_data.extend(res.json())
                st.session_state['api_usage']['remaining'] = res.headers.get('x-requests-remaining')
                st.session_state['api_usage']['used'] = res.headers.get('x-requests-used')
            progress_bar.progress((idx + 1) / len(LEAGUE_NAMES))
        
        status_text.text("Filtraggio partite prossime 48h...")
        # Filtro 48 ore
        now = datetime.utcnow()
        limit = now + timedelta(hours=48)
        
        filtered_data = []
        for match in all_data:
            m_time = datetime.strptime(match['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
            if now <= m_time <= limit:
                filtered_data.append(match)
        
        st.session_state['api_data'] = filtered_data
        st.rerun()

    if c_btn1.button("🔍 Scansiona Singolo", use_container_width=True):
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_name]}/odds/', 
                           params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
        if res.status_code == 200:
            st.session_state['api_data'] = res.json()
            st.rerun()

    st.divider()

    # Visualizzazione Risultati
    if st.session_state['api_data']:
        pend_list = df_attuale[df_attuale['Esito'] == "Pendente"]['Match'].tolist()
        found_any = False
        for m in st.session_state['api_data']:
            try:
                nome_m = f"{m['home_team']}-{m['away_team']}"
                dt_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
                sport_key = m['sport_key']
                camp_name = LEAGUE_NAMES.get(sport_key, "Altro")
                
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
                        found_any = True
                        stk_c = round(max(2.0, min(budget_cassa * (val/(best['Q']-1)) * rischio, budget_cassa*0.15)), 2)
                        c_a, c_b = st.columns([3, 1])
                        is_p = " ✅" if nome_m in pend_list else ""
                        c_a.write(f"📅 {dt_m} | **{nome_m}** ({camp_name}) | {best['BK']} | Val: **{round(val*100,1)}%** | Suggerito: **{stk_c}€**{is_p}")
                        if c_b.button(f"ADD @{best['Q']}", key=f"add_{nome_m}_{sport_key}", disabled=(nome_m in pend_list)):
                            nuova = pd.DataFrame([{"Data Match": dt_m, "Match": nome_m, "Scelta": best['T'], "Quota": best['Q'], "Stake": stk_c, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": sport_key, "Risultato": "-"}])
                            salva_db(pd.concat([carica_db(), nuova], ignore_index=True))
                            st.rerun()
                        st.divider()
            except: continue
        if not found_any: st.write("Nessuna scommessa di valore trovata nelle prossime 48h.")
