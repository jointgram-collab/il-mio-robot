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

# --- TAB 1: SCANNER MULTI-CLICK (V11.70) ---
with t1:
    st.write("### 📡 Radar Campionati")
    st.info("Clicca sui campionati per caricarli nella lista. I risultati si accumuleranno qui sotto.")
    
    # Griglia di pulsanti per scansione rapida
    c1, c2, c3, c4 = st.columns(4)
    cols = [c1, c2, c3, c4]
    
    if 'accumulated_data' not in st.session_state:
        st.session_state['accumulated_data'] = []

    for i, (l_key, l_name) in enumerate(LEAGUE_NAMES.items()):
        with cols[i % 4]:
            if st.button(f"🔍 {l_name}", key=f"btn_{l_key}", use_container_width=True):
                res = requests.get(
                    f'https://api.the-odds-api.com/v4/sports/{l_key}/odds/', 
                    params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'}
                )
                if res.status_code == 200:
                    new_matches = res.json()
                    # Evitiamo duplicati
                    existing_ids = [m['id'] for m in st.session_state['accumulated_data']]
                    for nm in new_matches:
                        if nm['id'] not in existing_ids:
                            st.session_state['accumulated_data'].append(nm)
                    
                    st.session_state['api_usage']['remaining'] = res.headers.get('x-requests-remaining')
                    st.rerun()

    if st.button("🗑️ Svuota Radar", type="primary"):
        st.session_state['accumulated_data'] = []
        st.rerun()

    st.divider()

    # Visualizzazione dati accumulati
    if st.session_state['accumulated_data']:
        now = datetime.utcnow()
        limit = now + timedelta(hours=ore_ricerca)
        
        display_list = [m for m in st.session_state['accumulated_data'] 
                       if now <= datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ") <= limit]
        
        st.write(f"📊 Partite in lista: **{len(display_list)}**")
        
        pend_list = df_attuale[df_attuale['Esito'] == "Pendente"]['Match'].tolist()
        
        for m in display_list:
            try:
                nome_m = f"{m['home_team']}-{m['away_team']}"
                dt_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
                sport_key = m['sport_key']
                
                # ... STESSA LOGICA DI CALCOLO VALUE (IDENTICA ALLA SINGOLA) ...
                # (Inserisci qui la logica degli outcomes/best/val che già conosci)
            except: continue
