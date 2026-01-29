import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE PAGINA E CSS "HARDCORE" ---
st.set_page_config(page_title="AI SNIPER V14.1", layout="wide")

st.markdown("""
    <style>
    /* Sfondo e font */
    .stApp { background-color: #0b0e14; color: #e1e1e1; }
    
    /* Riduciamo i margini eccessivi di Streamlit */
    .block-container { padding-top: 2rem; padding-bottom: 0rem; max-width: 95%; }
    
    /* HEADER STILE MOCKUP */
    .main-title { font-size: 30px; font-weight: 800; color: white; margin-bottom: 5px; }
    .sub-title { color: #58a6ff; font-size: 14px; margin-bottom: 20px; font-weight: 600; }

    /* CARD SCANNER (IL TUO DESIGN) */
    .card-scanner {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        display: flex;
        flex-direction: column;
    }
    .card-row-1 { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
    .match-name { font-size: 18px; font-weight: 700; color: #ffffff; }
    .league-tag { background: #21262d; padding: 3px 8px; border-radius: 5px; font-size: 11px; color: #8b949e; }
    
    .bet-info { font-size: 22px; font-weight: 800; color: #58a6ff; margin-bottom: 12px; }
    
    .details-row { display: flex; gap: 20px; font-size: 14px; color: #8b949e; border-top: 1px solid #30363d; padding-top: 10px; }
    .detail-item b { color: #ffffff; }
    .valore-verde { color: #39d353; font-weight: bold; }
    .stake-giallo { color: #f1c40f; font-weight: bold; }

    /* KPI BOXES (FISCALI) */
    .kpi-wrapper { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px; }
    .kpi-card { padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; }
    .blue-k { background: rgba(33, 150, 243, 0.2); border: 1px solid #2196f3; color: #2196f3; }
    .green-k { background: rgba(57, 211, 83, 0.2); border: 1px solid #39d353; color: #39d353; }
    .red-k { background: rgba(248, 81, 73, 0.2); border: 1px solid #f85149; color: #f85149; }
    .yellow-k { background: rgba(241, 196, 15, 0.2); border: 1px solid #f1c40f; color: #f1c40f; }

    /* PULSANTI */
    .stButton>button { border-radius: 6px; font-weight: 700; height: 3em; transition: 0.3s; }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #0d1117; }
    </style>
""", unsafe_allow_html=True)

# --- 2. MOTORE DATI (STABILE) ---
conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        return df.dropna(subset=["Match"]) if df is not None else pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

df_attuale = carica_db()

# --- 3. INTERFACCIA ---
st.markdown('<div class="main-title">🎯 AI SNIPER</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">V14.1 STABILE | PROFESSIONAL BETTING DASHBOARD</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 📊 API Status")
    st.metric("Crediti", st.session_state.get('api_usage', {}).get('remaining', 'N/D'))
    st.divider()
    budget = st.number_input("Cassa (€)", value=500.0)
    kelly = st.slider("Kelly %", 0.05, 0.50, 0.20)

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB SCANNER ---
with t1:
    c_head1, c_head2, c_head3 = st.columns([2,1,1])
    c_head1.selectbox("Campionato:", ["Serie A", "Serie B", "Premier League", "La Liga"])
    
    # Simuliamo un risultato per farti vedere la card
    match_finto = {"home": "Bari", "away": "Palermo", "quota": 2.05, "valore": 12.3, "stake": 11.71, "bk": "William Hill"}
    
    # LA CARD "MOCKUP STYLE"
    st.markdown(f"""
        <div class="card-scanner">
            <div class="card-row-1">
                <span class="match-name">⚽ {match_finto['home']} - {match_finto['away']}</span>
                <span class="league-tag">IT Serie B | 30/01 19:30</span>
            </div>
            <div class="bet-info">OVER 2.5 @ {match_finto['quota']}</div>
            <div class="details-row">
                <div class="detail-item">💰 Stake: <span class="stake-giallo">{match_finto['stake']}€</span></div>
                <div class="detail-item">🔥 Valore: <span class="valore-verde">+{match_finto['valore']}%</span></div>
                <div class="detail-item">🏛️ {match_finto['bk']}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Pulsante Streamlit (subito sotto la card)
    st.button("➕ AGGIUNGI AL PORTAFOGLIO", key="add_1", use_container_width=True)

# --- TAB FISCALE ---
with t3:
    st.markdown(f"""
        <div class="kpi-wrapper">
            <div class="kpi-card blue-k">💰 GIOCATO<br>185.00€</div>
            <div class="kpi-card green-k">✅ VINTO<br>322.75€</div>
            <div class="kpi-card red-k">❌ PERSO<br>85.00€</div>
            <div class="kpi-card yellow-k">📈 NETTO<br>+237.75€</div>
        </div>
    """, unsafe_allow_html=True)
    st.dataframe(df_attuale, use_container_width=True)
