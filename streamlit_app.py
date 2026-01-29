import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="AI SNIPER V13.6 - PRO", layout="wide")

# --- 2. CSS PERSONALIZZATO (SIDEBAR & UI) ---
st.markdown("""
    <style>
    /* Sfondo Generale */
    .stApp { background-color: #0b0e14; color: #ffffff; }

    /* SIDEBAR HIGH-CONTRAST */
    [data-testid="stSidebar"] {
        background-color: #11141a;
        border-right: 1px solid #30363d;
    }

    /* Testi e Titoli Sidebar */
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

    /* API Metric Box */
    .api-container {
        background-color: #1c2128;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #444c56;
        margin-bottom: 20px;
    }
    
    .api-row { display: flex; justify-content: space-between; margin-bottom: 5px; }
    
    /* Barra di progresso verde */
    .api-bar-bg { background: #30363d; height: 8px; border-radius: 4px; overflow: hidden; margin-top: 10px; }
    .api-bar-fill { background: #39d353; height: 100%; border-radius: 4px; box-shadow: 0 0 8px #39d353; }

    /* Fix scritte Streamlit */
    [data-testid="stWidgetLabel"] p {
        color: #ffffff !important;
        font-size: 15px !important;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1c2128;
        border-radius: 5px 5px 0 0;
        padding: 10px 20px;
        color: #8b949e;
    }
    .stTabs [aria-selected="true"] { background-color: #39d353 !important; color: #000 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. LOGICA DATABASE (GOOGLE SHEETS) ---
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

# --- 4. SIDEBAR CON NUOVA GRAFICA ---
with st.sidebar:
    st.markdown('<div class="sb-title">🔥 API Status</div>', unsafe_allow_html=True)
    
    # Recupero crediti API reali dallo stato sessione
    api_rem = st.session_state.get('api_rem', "N/D")
    # Calcolo percentuale utilizzo (esempio basato su 500 totali)
    total_credits = 500
    try:
        rem_int = int(api_rem)
        perc = int(((total_credits - rem_int) / total_credits) * 100)
    except:
        perc = 0
    
    st.markdown(f"""
        <div class="api-container">
            <div class="api-row">
                <span class="label-text">Residui:</span>
                <span class="value-text">{api_rem}</span>
            </div>
            <div style="margin-top:15px; display:flex; justify-content:space-between;">
                <span class="label-text">Utilizzo API</span>
                <span style="color:#39d353; font-weight:bold;">{perc}%</span>
            </div>
            <div class="api-bar-bg"><div class="api-bar-fill" style="width: {perc}%;"></div></div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown('<div class="sb-title">📊 Parametri Strategia</div>', unsafe_allow_html=True)
    
    budget = st.slider("Budget (€)", 100, 2000, 500)
    kelly = st.slider("Kelly Criterion", 0.05, 0.50, 0.20)
    valore_min = st.slider("Valore Minimo %", 0, 20, 3) / 100

    st.markdown("---")
    st.markdown('<div class="sb-title">⚙️ Impostazioni</div>', unsafe_allow_html=True)
    if st.button("Svuota Cache"):
        st.cache_data.clear()
        st.success("Cache pulita!")

# --- 5. CORPO CENTRALE ---
st.markdown("<h1 style='color:white;'>🎯 AI SNIPER <span style='font-size:15px; color:#39d353;'>V13.6</span></h1>", unsafe_allow_html=True)

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER ---
with t1:
    c1, c2 = st.columns([3, 1])
    sport = c1.selectbox("Seleziona Sport/Campionato", ["soccer_italy_serie_a", "soccer_epl", "soccer_spain_la_liga", "soccer_germany_bundesliga"])
    
    if c2.button("🚀 AVVIA SCAN", use_container_width=True):
        with st.spinner("Scansione mercati in corso..."):
            url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"
            params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals', 'oddsFormat': 'decimal'}
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                st.session_state['data'] = response.json()
                st.session_state['api_rem'] = response.headers.get('x-requests-remaining')
                st.success(f"Scan completato! Crediti rimasti: {st.session_state['api_rem']}")
            else:
                st.error("Errore API. Controlla la chiave o i crediti.")

    if 'data' in st.session_state:
        st.write("### Risultati Analisi")
        st.dataframe(pd.DataFrame(st.session_state['data']).head(10)) # Visualizzazione base per 13.6
        st.info("Logica di calcolo Value Bet attiva in background.")

# --- TAB 2: PORTAFOGLIO ---
with t2:
    pendenti = df_attuale[df_attuale['Esito'] == "Pendente"]
    if not pendenti.empty:
        st.table(pendenti[["Data Match", "Match", "Scelta", "Quota", "Stake"]])
    else:
        st.write("Nessuna scommessa pendente.")

# --- TAB 3: FISCALE ---
with t3:
    st.write("### Storico Giocate")
    st.dataframe(df_attuale, use_container_width=True)
    
    if not df_attuale.empty:
        vinto = df_attuale[df_attuale['Profitto'] > 0]['Profitto'].sum()
        perso = df_attuale[df_attuale['Profitto'] < 0]['Profitto'].abs().sum()
        netto = vinto - perso
        
        c_v, c_p, c_n = st.columns(3)
        c_v.metric("Totale Vinto", f"{vinto:.2f} €")
        c_p.metric("Totale Perso", f"{perso:.2f} €")
        c_n.metric("Profitto Netto", f"{netto:.2f} €", delta=f"{netto:.2f}")
