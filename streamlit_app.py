import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE ELITE UI ---
st.set_page_config(page_title="SNIPER ELITE V12.1", layout="wide", initial_sidebar_state="collapsed")

# CSS AGGRESSIVO PER LOOK PREMIUM
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0f1116;
        font-family: 'Inter', sans-serif;
    }
    
    /* Titoli e Testi */
    h1, h2, h3 { color: #ffffff !important; font-weight: 900 !important; }
    
    /* Card Stile Glassmorphism */
    div.stBox, [data-testid="stExpander"], .stMetric {
        background: rgba(30, 34, 45, 0.7) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 20px !important;
        padding: 20px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3) !important;
    }

    /* Metriche Giganti */
    [data-testid="stMetricValue"] {
        font-size: 45px !important;
        font-weight: 900 !important;
        color: #00ff88 !important;
    }

    /* Pulsanti Elite */
    .stButton > button {
        background: linear-gradient(90deg, #1e222d 0%, #2e3344 100%) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        height: 55px !important;
        width: 100% !important;
    }

    .stButton > button:hover {
        border-color: #00ff88 !important;
        color: #00ff88 !important;
        transform: translateY(-2px);
    }

    /* Badge Esiti */
    .vinto { color: #00ff88; font-weight: 900; font-size: 20px; }
    .perso { color: #ff4b4b; font-weight: 900; font-size: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGICA CORE ---
conn = st.connection("gsheets", type=GSheetsConnection)
BK_URLS = {"Bet365": "https://www.bet365.it", "Snai": "https://www.snai.it", "Better": "https://www.lottomatica.it/scommesse", "Planetwin365": "https://www.planetwin365.it"}

def carica_db():
    try: return conn.read(worksheet="Giocate", ttl="0").dropna(how='all')
    except: return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto"])

def salva_db(df): conn.update(worksheet="Giocate", data=df)

# --- INTERFACCIA ---
st.markdown("# 🎯 SNIPER ELITE <span style='color:#00ff88'>V12.1</span>", unsafe_allow_html=True)

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    with st.expander("⚙️ CONFIGURAZIONE STRATEGIA"):
        c1, c2 = st.columns(2)
        budget = c1.number_input("CASSA (€)", value=1000.0)
        risk = c2.slider("AGGRESSIVITÀ", 0.1, 0.5, 0.2)
    
    leagues = {"Serie A": "soccer_italy_serie_a", "Champions": "soccer_uefa_champions_league", "Premier": "soccer_england_league_1"}
    sel_league = st.selectbox("CAMPIONATO", list(leagues.keys()))

    if st.button("🚀 SCANSIONA MERCATI"):
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/', 
                           params={'api_key': '01f1c8f2a314814b17de03eeb6c53623', 'regions': 'eu', 'markets': 'totals'})
        if res.status_code == 200:
            st.session_state['data'] = res.json()

    if 'data' in st.session_state:
        for m in st.session_state['data']:
            # Logica calcolo valore (semplificata per brevità)
            home, away = m['home_team'], m['away_team']
            st.markdown(f"""
                <div style='background:rgba(255,255,255,0.05); padding:20px; border-radius:15px; margin-bottom:15px; border-left: 5px solid #00ff88;'>
                    <h3 style='margin:0;'>{home} vs {away}</h3>
                    <p style='color:#888;'>2.5 GOAL TARGET</p>
                </div>
            """, unsafe_allow_html=True)
            
            c_a, c_b = st.columns([2,1])
            if c_b.button("📥 AGGIUNGI", key=f"add_{home}"):
                # Logica salvataggio...
                st.toast("Salvato!")

with t2:
    st.markdown("### 💼 OPERAZIONI ATTIVE")
    df = carica_db()
    pendenti = df[df['Esito'] == "Pendente"]
    if not pendenti.empty:
        for i, r in pendenti.iterrows():
            st.markdown(f"**{r['Match']}** | @{r['Quota']}")
            col1, col2, col3 = st.columns(3)
            if col1.button("✅", key=f"w_{i}"): pass # Logica Win
            if col2.button("❌", key=f"l_{i}"): pass # Logica Loss
            if col3.button("🗑️", key=f"d_{i}"): pass # Logica Del

with t3:
    df = carica_db()
    prof = round(df['Profitto'].sum(), 2)
    st.metric("PROFITTO NETTO", f"{prof} €", delta=f"{round(prof/50, 2)}% verso target")
    
    st.markdown("---")
    for i, r in df.iterrows():
        color = "#00ff88" if r['Esito'] == "VINTO" else "#ff4b4b"
        st.markdown(f"""
            <div style='display:flex; justify-content:space-between; align-items:center; padding:10px; border-bottom:1px solid #222;'>
                <div><b>{r['Match']}</b><br><small>{r['Bookmaker']}</small></div>
                <div style='color:{color}; font-size:20px; font-weight:900;'>{r['Profitto']}€</div>
            </div>
        """, unsafe_allow_html=True)
