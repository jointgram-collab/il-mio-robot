import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date, timedelta
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V11.40 - Credit Monitor", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
TARGET_FINALE = 5000.0

# Inizializza contatore crediti nella sessione
if 'api_usage' not in st.session_state:
    st.session_state['api_usage'] = {'remaining': "N/D", 'used': "N/D"}

BK_EURO_AUTH = {
    "Bet365": "https://www.bet365.it", "Snai": "https://www.snai.it",
    "Better": "https://www.lottomatica.it/scommesse", "Planetwin365": "https://www.planetwin365.it",
    "Eurobet": "https://www.eurobet.it", "Goldbet": "https://www.goldbet.it", 
    "Sisal": "https://www.sisal.it", "Bwin": "https://www.bwin.it",
    "William Hill": "https://www.williamhill.it", "888sport": "https://www.888sport.it"
}

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", 
    "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", 
    "soccer_england_efl_championship": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Championship",
    "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie",
    "soccer_spain_la_liga": "🇪🇸 La Liga",
    "soccer_germany_bundesliga": "🇩🇪 Bundesliga", 
    "soccer_uefa_champions_league": "🇪🇺 Champions",
    "soccer_uefa_europa_league": "🇪🇺 Europa League", 
    "soccer_france_ligue_1": "🇫🇷 Ligue 1"
}

# --- FUNZIONI API ---
def update_api_usage(headers):
    """Estrae i crediti residui dagli headers della risposta API"""
    remaining = headers.get('x-requests-remaining')
    used = headers.get('x-requests-used')
    if remaining:
        st.session_state['api_usage'] = {'remaining': remaining, 'used': used}

# --- MOTORE DATABASE ---
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
        df = df.dropna(subset=["Match"])
        df['dt_obj'] = pd.to_datetime(df['Data Match'] + f"/{date.today().year}", format="%d/%m %H:%M/%Y", errors='coerce')
        return df
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    if 'dt_obj' in df.columns: df = df.drop(columns=['dt_obj'])
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11.40")

with st.sidebar:
    st.header("📊 Stato API")
    c1, c2 = st.columns(2)
    c1.metric("Residui", st.session_state['api_usage']['remaining'])
    c2.metric("Usati", st.session_state['api_usage']['used'])
    st.caption("Il credito si aggiorna dopo ogni scansione.")
    st.divider()
    
    st.header("⚙️ Parametri Cassa")
    budget_cassa = st.number_input("Budget (€)", value=250.0)
    rischio = st.slider("Kelly", 0.05, 0.50, 0.20)
    soglia_val = st.slider("Valore Min %", 0, 15, 5) / 100
    st.divider()
    
    # Sezione Backup (Tuo ripristino 11.40)
    st.header("💾 Backup dati")
    df_f = carica_db()
    csv_data = df_f.to_csv(index=False).encode('utf-8')
    st.download_button("SCARICA CSV", data=csv_data, file_name=f"backup_{date.today()}.csv", use_container_width=True)

# --- SCANNER (Tab principale) ---
t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    sel_name = st.selectbox("Campionato:", list(leagues.keys()))
    
    if st.button("🚀 SCANSIONA", use_container_width=True):
        res = requests.get(
            f'https://api.the-odds-api.com/v4/sports/{leagues[sel_name]}/odds/', 
            params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'}
        )
        if res.status_code == 200: 
            update_api_usage(res.headers) # AGGIORNA CREDITI
            st.session_state['api_data'] = res.json()
            st.rerun()
        else:
            st.error(f"Errore API: {res.status_code}")

    # Resto della logica di visualizzazione (identica alla tua 11.40)...
    if 'api_data' in st.session_state and st.session_state['api_data']:
        st.write("### Risultati Scansione")
        # [Logica visualizzazione match...]
