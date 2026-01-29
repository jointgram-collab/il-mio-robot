import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI & CSS AVANZATO ---
st.set_page_config(page_title="AI SNIPER V14.0", layout="wide")

st.markdown("""
    <style>
    /* Reset e Sfondo */
    .stApp { background-color: #0e1117; color: #ffffff; font-family: 'Segoe UI', Roboto, sans-serif; }
    
    /* Card Scanner - Replicata dal Mockup */
    .match-card {
        background-color: #1a1d26;
        border: 1px solid #2d313d;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .card-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2d313d; padding-bottom: 8px; margin-bottom: 10px; }
    .card-title { font-size: 1.1em; font-weight: 700; color: #ffffff; }
    .card-bet { font-size: 1.3em; font-weight: 800; color: #58a6ff; margin: 8px 0; }
    .card-details { display: flex; justify-content: space-between; font-size: 0.9em; color: #8b949e; }
    .val-highlight { color: #39d353; font-weight: bold; }
    .stk-highlight { color: #ffc107; font-weight: bold; }

    /* KPI Fiscale (I quadratini colorati) */
    .kpi-container { display: flex; gap: 10px; margin-bottom: 25px; }
    .kpi-box { flex: 1; padding: 15px; border-radius: 8px; text-align: center; font-weight: 800; color: #ffffff; }
    .kpi-giocato { background-color: #7289da; }
    .kpi-vinto { background-color: #2eb872; }
    .kpi-perso { background-color: #e74c3c; }
    .kpi-netto { background-color: #f1c40f; color: #000; }

    /* Customizzazione Sidebar e Pulsanti */
    section[data-testid="stSidebar"] { background-color: #11141a; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: 700; transition: 0.3s; }
    
    /* Nascondi header Streamlit per pulizia */
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- MOTORE DATABASE ---
conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

# Caricamento dati (Logica stabile)
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        return df.dropna(subset=["Match"]) if df is not None else pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

df_attuale = carica_db()

# --- SIDEBAR (Stato API e Parametri) ---
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: white;'>🎯 AI SNIPER</h1>", unsafe_allow_html=True)
    st.markdown("---")
    st.metric("Crediti Residui", st.session_state.get('api_usage', {}).get('remaining', 'N/D'))
    budget_cassa = st.number_input("Budget (€)", value=500.0)
    rischio = st.slider("Kelly Criterion", 0.05, 0.50, 0.20)
    soglia_val = st.slider("Valore Minimo %", 0, 15, 3) / 100

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER (Il cuore della tua richiesta) ---
with t1:
    # Qui usiamo le colonne per i pulsanti di controllo
    c1, c2, c3 = st.columns([2, 1, 1])
    c1.selectbox("Seleziona Campionato:", ["Serie A", "Premier League", "La Liga", "Champions"])
    c2.button("🚀 SCAN TOTALE")
    c3.button("🔍 SCAN SINGOLO")

    # Simulazione Rendering a Card per farti vedere la differenza
    # In produzione questo ciclo userà i dati reali dell'API
    for i in range(2): 
        nome_m = "Juventus - Inter" if i == 0 else "Real Madrid - Barcelona"
        st.markdown(f"""
            <div class="match-card">
                <div class="card-header">
                    <span class="card-title">⚽ {nome_m}</span>
                    <span style="font-size:0.8em; color:#8b949e;">📅 29/01 20:45</span>
                </div>
                <div class="card-bet">OVER 2.5 @ 1.95</div>
                <div class="card-details">
                    <span>💰 Stake: <span class="stk-highlight">15.40€</span></span>
                    <span>📈 Valore: <span class="val-highlight">+5.2%</span></span>
                    <span>🏛️ Bet365</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Il pulsante di Streamlit deve stare fuori dal blocco HTML per funzionare
        if st.button(f"➕ AGGIUNGI AL PORTAFOGLIO", key=f"add_{i}"):
            st.success(f"{nome_m} aggiunto!")

# --- TAB 3: FISCALE (Con i box colorati del mockup) ---
with t3:
    st.markdown("""
        <div class="kpi-container">
            <div class="kpi-box kpi-giocato">💰 GIOCATO<br>185.0 €</div>
            <div class="kpi-box kpi-vinto">✅ VINTO<br>322.75 €</div>
            <div class="kpi-box kpi-perso">❌ PERSO<br>85.0 €</div>
            <div class="kpi-box kpi-netto">📈 NETTO<br>+237.75 €</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.dataframe(df_attuale, use_container_width=True)
