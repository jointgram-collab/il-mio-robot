import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI & CSS ---
st.set_page_config(page_title="AI SNIPER V13.8 - FULL DESIGN", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    
    /* Card Scanner */
    .match-card {
        background-color: #161b22;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 12px;
        border: 1px solid #30363d;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* KPI Metrics Fiscale */
    .metric-container {
        display: flex;
        gap: 10px;
        margin-bottom: 20px;
    }
    .metric-box {
        flex: 1;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        font-weight: bold;
    }
    .bg-blue { background-color: rgba(33, 150, 243, 0.2); border: 1px solid #2196f3; }
    .bg-green { background-color: rgba(76, 175, 80, 0.2); border: 1px solid #4caf50; }
    .bg-red { background-color: rgba(244, 67, 54, 0.2); border: 1px solid #f44336; }
    .bg-orange { background-color: rgba(255, 152, 0, 0.2); border: 1px solid #ff9800; }
    
    /* Header & Sidebar */
    .main-header { font-size: 28px; font-weight: 800; letter-spacing: -1px; margin-bottom: 25px; }
    section[data-testid="stSidebar"] { background-color: #0d1117; }
    </style>
""", unsafe_allow_html=True)

# --- (LOGICA CORE IDENTICA ALLA V13.6 - OMESSA PER FOCUS GRAFICO) ---
# [Qui inserisci le funzioni carica_db, salva_db, check_results e i parametri API]

# ... (Riprendiamo dall'interfaccia) ...

st.markdown('<div class="main-header">🎯 AI SNIPER <span style="font-size:14px; color:#58a6ff;">V13.8 STABILE</span></div>', unsafe_allow_html=True)
df_attuale = carica_db()

with st.sidebar:
    st.markdown("### 📊 Status Crediti")
    # Qui usiamo un piccolo hack CSS per i colori della sidebar
    res = st.session_state['api_usage']['remaining']
    color = "#39d353" if (isinstance(res, int) and res > 100) else "#f44336"
    st.markdown(f"<h2 style='color:{color}; text-align:center;'>{res}</h2>", unsafe_allow_html=True)
    st.divider()
    budget_cassa = st.number_input("Budget (€)", value=500.0)
    rischio = st.slider("Kelly Criterion", 0.05, 0.50, 0.20)

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER ---
with t1:
    # ... (Selettori campionati e pulsanti scansione) ...
    # Esempio di rendering Card
    st.markdown("""
        <div class="match-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:1.1em; font-weight:600;">Inter - Milan</span>
                <span style="background:#238636; padding:2px 8px; border-radius:12px; font-size:11px;">LIVE SOON</span>
            </div>
            <div style="margin: 10px 0; color:#58a6ff; font-size:20px; font-weight:700;">OVER 2.5 @ 1.85</div>
            <div style="color:#8b949e; font-size:13px;">
                Stake: <b style="color:#e3b341;">15.00€</b> | Valore: <b style="color:#39d353;">+4.2%</b> | 🏛️ Bet365
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- TAB 3: FISCALE (DESIGN KPI) ---
with t3:
    if not df_attuale.empty:
        tot_giocato = round(df_attuale['Stake'].sum(), 2)
        tot_vinto = round(df_attuale[df_attuale['Esito'] == "VINTO"]['Profitto'].sum() + df_attuale[df_attuale['Esito'] == "VINTO"]['Stake'].sum(), 2)
        tot_perso = round(df_attuale[df_attuale['Esito'] == "PERSO"]['Stake'].sum(), 2)
        prof_netto = round(df_attuale['Profitto'].sum(), 2)
        
        # Ecco i quadratini colorati come nella grafica
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-box bg-blue">💰 GIOCATO<br><span style="font-size:20px;">{tot_giocato}€</span></div>
                <div class="metric-box bg-green">✅ VINTO<br><span style="font-size:20px;">{tot_vinto}€</span></div>
                <div class="metric-box bg-red">❌ PERSO<br><span style="font-size:20px;">{tot_perso}€</span></div>
                <div class="metric-box bg-orange">📈 NETTO<br><span style="font-size:20px;">{prof_netto}€</span></div>
            </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        # Tabella pulita
        st.dataframe(df_attuale[["Data Match", "Match", "Scelta", "Quota", "Stake", "Esito", "Profitto"]].sort_index(ascending=False), use_container_width=True)
