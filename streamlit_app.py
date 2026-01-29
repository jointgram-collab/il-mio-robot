import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE UI & CSS RADICALE ---
st.set_page_config(page_title="AI SNIPER V15.0", layout="wide")

st.markdown("""
    <style>
    /* Global & Background */
    .stApp { background-color: #0b0e14; color: #ffffff; }
    .block-container { max-width: 900px !important; padding-top: 2rem; }
    
    /* SIDEBAR HIGH-CONTRAST */
    [data-testid="stSidebar"] { background-color: #11141a; border-right: 1px solid #30363d; }
    .sb-title { color: #ffffff !important; font-size: 18px; font-weight: 700; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
    .label-text { color: #8b949e; font-size: 14px; font-weight: 500; }
    .value-text { color: #ffffff; font-weight: 700; }
    
    /* SLIDERS NEON */
    div[data-testid="stSlider"] [data-baseweb="slider"] [aria-valuenow] { background-color: #ffffff !important; border: 2px solid #39d353 !important; }
    [data-testid="stWidgetLabel"] p { color: #ffffff !important; font-size: 15px !important; }

    /* API METRIC BOX */
    .api-container { background-color: #1c2128; padding: 15px; border-radius: 8px; border: 1px solid #444c56; margin-bottom: 20px; }
    .api-row { display: flex; justify-content: space-between; margin-bottom: 5px; }
    .api-bar-bg { background: #30363d; height: 8px; border-radius: 4px; overflow: hidden; margin-top: 10px; }
    .api-bar-fill { background: #39d353; height: 100%; border-radius: 4px; box-shadow: 0 0 8px #39d353; }

    /* ULTRA COMPACT ROW (SCANNER) */
    .ultra-compact-row {
        background-color: #0d1117;
        border: 1px solid #30363d;
        border-radius: 4px;
        padding: 6px 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .left-side { display: flex; align-items: center; gap: 12px; overflow: hidden; }
    .match-title { font-size: 13px; font-weight: 700; color: #ffffff; white-space: nowrap; }
    .bet-info { font-size: 13px; font-weight: 800; color: #58a6ff; white-space: nowrap; }
    .stk { color: #f1c40f; font-weight: 700; font-size: 11px; }
    .val { color: #39d353; font-weight: 700; font-size: 11px; }

    /* BOTTONE ICONA */
    .stButton > button {
        width: 30px !important; height: 30px !important; min-width: 30px !important;
        background-color: #21262d !important; border: 1px solid #30363d !important;
        color: white !important; border-radius: 4px !important; padding: 0 !important;
    }
    .stButton > button[disabled] { border-color: #39d353 !important; color: #39d353 !important; background: transparent !important; opacity: 1 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGICA DATABASE (STABILE) ---
conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        return df.dropna(subset=["Match"]) if df is not None else pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

df_attuale = carica_db()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.markdown('<div class="sb-title">🔥 API Status</div>', unsafe_allow_html=True)
    
    # Valori API dinamici
    rem = st.session_state.get('api_rem', 440)
    perc = (60 / (440 + 60)) * 100 # Esempio statico, si aggiorna con chiamate
    
    st.markdown(f"""
        <div class="api-container">
            <div class="api-row"><span class="label-text">Residui:</span><span class="value-text">{rem}</span></div>
            <div class="api-row"><span class="label-text">Utilizzo:</span><span style="color:#39d353;">{int(perc)}%</span></div>
            <div class="api-bar-bg"><div class="api-bar-fill" style="width: {perc}%;"></div></div>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    st.markdown('<div class="sb-title">📊 Parametri</div>', unsafe_allow_html=True)
    budget = st.slider("Budget (€)", 100, 2000, 500)
    kelly = st.slider("Kelly Criterion", 0.05, 0.50, 0.20)
    val_min = st.slider("Valore Minimo %", 0, 15, 3) / 100

# --- 4. CORPO CENTRALE ---
t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    # Selezione Lega e Scan
    col_l, col_b = st.columns([3, 1])
    lega = col_l.selectbox("Campionato", ["soccer_italy_serie_a", "soccer_epl", "soccer_spain_la_liga"])
    
    if col_b.button("🚀 SCAN", use_container_width=True):
        with st.spinner("Analisi mercati..."):
            res = requests.get(f'https://api.the-odds-api.com/v4/sports/{lega}/odds/', params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
            if res.status_code == 200:
                st.session_state['api_data'] = res.json()
                st.session_state['api_rem'] = res.headers.get('x-requests-remaining')
                st.rerun()

    # Visualizzazione Card con Logica Reale
    if 'api_data' in st.session_state:
        pend_list = df_attuale[df_attuale['Esito'] == "Pendente"]['Match'].tolist()
        for i, m in enumerate(st.session_state['api_data']):
            nome_m = f"{m['home_team']}-{m['away_team']}"
            # Logica calcolo valore semplificata per l'esempio
            quota, val_calc, stk_calc = 1.95, 5.2, 15.4 
            
            c_info, c_btn = st.columns([0.9, 0.1])
            with c_info:
                st.markdown(f"""
                    <div class="ultra-compact-row">
                        <div class="left-side">
                            <span class="match-title">⚽ {nome_m}</span>
                            <span class="bet-info">OV 2.5 @{quota}</span>
                            <div style="font-size:11px;"><span class="stk">S:{stk_calc}€</span> <span style="color:#30363d">|</span> <span class="val">V:+{val_calc}%</span></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            with c_btn:
                if nome_m in pend_list:
                    st.button("✔", key=f"bt_{i}", disabled=True)
                else:
                    if st.button("＋", key=f"bt_{i}"):
                        nuova = pd.DataFrame([{"Data Match": "Oggi", "Match": nome_m, "Scelta": "OVER 2.5", "Quota": quota, "Stake": stk_calc, "Bookmaker": "Bet365", "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": m['sport_key'], "Risultato": "-"}])
                        salva_db(pd.concat([df_attuale, nuova], ignore_index=True))
                        st.rerun()

with t3:
    st.write("Visualizzazione Report Fiscale...")
    st.dataframe(df_attuale, use_container_width=True)
