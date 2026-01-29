import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="AI SNIPER V13.6", layout="wide")

# --- 2. CSS SIDEBAR OTTIMIZZATA (ALTO CONTRASTO) ---
st.markdown("""
    <style>
    /* Sfondo Generale App */
    .stApp { background-color: #0b0e14; color: #ffffff; }

    /* Personalizzazione Sidebar */
    [data-testid="stSidebar"] {
        background-color: #11141a;
        border-right: 1px solid #30363d;
    }

    /* Titoli e Testi Sidebar */
    .sb-title {
        color: #ffffff !important;
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .label-text {
        color: #8b949e;
        font-size: 14px;
        font-weight: 500;
    }

    .value-text {
        color: #ffffff;
        font-weight: 700;
    }

    /* Styling degli Slider (Verde Neon e Bianco) */
    div[data-testid="stSlider"] [data-baseweb="slider"] [aria-valuenow] {
        background-color: #ffffff !important;
        border: 2px solid #39d353 !important;
    }
    
    /* Forza etichette bianche per gli slider */
    [data-testid="stWidgetLabel"] p {
        color: #ffffff !important;
        font-size: 15px !important;
        font-weight: 600;
    }

    /* Box Crediti API */
    .api-container {
        background-color: #1c2128;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #444c56;
        margin-bottom: 20px;
    }
    
    .api-row { display: flex; justify-content: space-between; margin-bottom: 5px; }
    
    .api-bar-bg { background: #30363d; height: 8px; border-radius: 4px; overflow: hidden; margin-top: 10px; }
    .api-bar-fill { background: #39d353; height: 100%; border-radius: 4px; box-shadow: 0 0 8px #39d353; }

    /* Pulizia Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1c2128;
        border-radius: 4px 4px 0 0;
        padding: 8px 16px;
        color: #8b949e;
    }
    .stTabs [aria-selected="true"] { background-color: #39d353 !important; color: #000 !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 3. LOGICA DATABASE & API ---
conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        return df.dropna(subset=["Match"]) if df is not None else pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

df_attuale = carica_db()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown('<div class="sb-title">🔥 API Status</div>', unsafe_allow_html=True)
    
    # Gestione crediti API
    rem = st.session_state.get('api_rem', "N/D")
    try:
        # Calcolo percentuale basato su un ipotetico piano da 500 crediti
        perc_util = int(((500 - int(rem)) / 500) * 100) if rem != "N/D" else 0
    except:
        perc_util = 0
        
    st.markdown(f"""
        <div class="api-container">
            <div class="api-row">
                <span class="label-text">Residui:</span>
                <span class="value-text">{rem}</span>
            </div>
            <div style="margin-top:12px; display:flex; justify-content:space-between;">
                <span class="label-text">Utilizzo</span>
                <span style="color:#39d353; font-weight:bold;">{perc_util}%</span>
            </div>
            <div class="api-bar-bg"><div class="api-bar-fill" style="width: {perc_util}%;"></div></div>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    st.markdown('<div class="sb-title">📊 Parametri</div>', unsafe_allow_html=True)
    budget = st.slider("Budget (€)", 0, 2000, 500)
    kelly = st.slider("Kelly Criterion", 0.05, 0.50, 0.20)
    valore_min = st.slider("Valore Minimo %", 0, 20, 3) / 100

    st.divider()
    st.markdown('<div class="sb-title">⚙️ Impostazioni</div>', unsafe_allow_html=True)
    if st.button("Reset Cache"):
        st.cache_data.clear()
        st.rerun()

# --- 5. MAIN CONTENT ---
st.markdown("<h1 style='text-align: center; color: white;'>🎯 AI SNIPER V13.6</h1>", unsafe_allow_html=True)

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    c1, c2 = st.columns([3, 1])
    sport = c1.selectbox("Campionato", ["soccer_italy_serie_a", "soccer_epl", "soccer_spain_la_liga"])
    
    if c2.button("🚀 AVVIA SCAN", use_container_width=True):
        with st.spinner("Analisi in corso..."):
            url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"
            params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals', 'oddsFormat': 'decimal'}
            r = requests.get(url, params=params)
            if r.status_code == 200:
                st.session_state['data'] = r.json()
                st.session_state['api_rem'] = r.headers.get('x-requests-remaining')
                st.rerun()
            else:
                st.error("Errore API")

    if 'data' in st.session_state:
        st.dataframe(pd.DataFrame(st.session_state['data']), use_container_width=True)

with t2:
    st.write("### Giocate Pendenti")
    pendenti = df_attuale[df_attuale['Esito'] == "Pendente"]
    st.dataframe(pendenti, use_container_width=True)

with t3:
    st.write("### Report Fiscale")
    st.dataframe(df_attuale, use_container_width=True)
