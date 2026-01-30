import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="AI SNIPER V13.6 - STABLE", layout="wide")

# --- 2. CSS SIDEBAR & UI (HIGH-CONTRAST) ---
st.markdown("""
    <style>
    /* Sfondo Generale */
    .stApp { background-color: #0b0e14; color: #ffffff; }

    /* Sidebar Professionale */
    [data-testid="stSidebar"] {
        background-color: #11141a;
        border-right: 1px solid #30363d;
    }

    .sb-title {
        color: #ffffff !important;
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .label-text { color: #8b949e; font-size: 14px; font-weight: 500; }
    .value-text { color: #ffffff; font-weight: 700; }

    /* Slider Neon Style */
    div[data-testid="stSlider"] [data-baseweb="slider"] [aria-valuenow] {
        background-color: #ffffff !important;
        border: 2px solid #39d353 !important;
    }

    /* Box API Metric */
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

    /* Fix scritte etichette */
    [data-testid="stWidgetLabel"] p { color: #ffffff !important; font-size: 15px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONNESSIONI E COSTANTI ---
conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

if 'api_usage' not in st.session_state:
    st.session_state['api_usage'] = {'remaining': "440", 'used': "60"} # Valori default basati su tue immagini
if 'api_data' not in st.session_state:
    st.session_state['api_data'] = []

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", 
    "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", 
    "soccer_uefa_europa_league": "🇪🇺 Europa League",
    "soccer_uefa_champions_league": "🏆 Champions"
}

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "William Hill", "888sport"]

# --- 4. FUNZIONI CORE ---
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        return df.dropna(subset=["Match"]) if df is not None else pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

def check_results():
    df = carica_db()
    pendenti = df[df['Esito'] == "Pendente"]
    if pendenti.empty:
        st.info("Nessuna scommessa pendente.")
        return
    
    cambiamenti = False
    with st.spinner("🔄 Verifica risultati..."):
        for skey in pendenti['Sport_Key'].unique():
            res = requests.get(f'https://api.the-odds-api.com/v4/sports/{skey}/scores/', params={'api_key': API_KEY, 'daysFrom': 3})
            if res.status_code == 200:
                scores = res.json()
                for i, r in pendenti[pendenti['Sport_Key'] == skey].iterrows():
                    m_parts = r['Match'].split('-')
                    if len(m_parts) != 2: continue
                    t1, t2 = m_parts[0].strip(), m_parts[1].strip()
                    
                    # MATCHING FLESSIBILE (Indipendente dall'ordine Home-Away)
                    m_res = next((m for m in scores if (t1 in [m['home_team'], m['away_team']] and t2 in [m['home_team'], m['away_team']])), None)
                    
                    if m_res and m_res.get('completed') and m_res.get('scores'):
                        s_list = m_res['scores']
                        try:
                            # Associa i gol alle squadre corrette
                            s1 = int(next(x['score'] for x in s_list if x['name'] == m_res['home_team']))
                            s2 = int(next(x['score'] for x in s_list if x['name'] == m_res['away_team']))
                            tot_gol = s1 + s2
                            vinto = tot_gol > 2.5 if r['Scelta'] == "OVER 2.5" else tot_gol < 2.5
                            
                            df.at[i, 'Esito'] = "VINTO" if vinto else "PERSO"
                            df.at[i, 'Risultato'] = f"{s1}-{s2}"
                            df.at[i, 'Profitto'] = round((r['Stake'] * r['Quota']) - r['Stake'], 2) if vinto else -float(r['Stake'])
                            cambiamenti = True
                        except: continue
    if cambiamenti:
        salva_db(df)
        st.success("Risultati aggiornati!")
        st.rerun()

# --- 5. SIDEBAR ---
with st.sidebar:
    st.markdown('<div class="sb-title">🔥 API Status</div>', unsafe_allow_html=True)
    rem = st.session_state['api_usage']['remaining']
    # Calcolo percentuale per la barra verde (basato su 500 crediti)
    try: perc = int(((500 - int(rem)) / 500) * 100)
    except: perc = 12

    st.markdown(f"""
        <div class="api-container">
            <div class="api-row"><span class="label-text">Residui:</span><span class="value-text">{rem}</span></div>
            <div style="margin-top:10px; display:flex; justify-content:space-between;"><span class="label-text">Utilizzo</span><span style="color:#39d353; font-weight:bold;">{perc}%</span></div>
            <div class="api-bar-bg"><div class="api-bar-fill" style="width: {perc}%;"></div></div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="sb-title">📊 Parametri Strategia</div>', unsafe_allow_html=True)
    budget_cassa = st.number_input("Budget (€)", value=500.0)
    rischio = st.slider("Kelly Criterion %", 0.05, 0.50, 0.20)
    soglia_val = st.slider("Valore Minimo %", 0, 15, 3) / 100

# --- 6. MAIN CONTENT ---
st.title("🎯 AI SNIPER V13.6")
df_attuale = carica_db()

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    # Logica Scanner (Serie A di default come in immagine)
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    sel_name = st.selectbox("Seleziona Campionato:", list(leagues.keys()))
    if st.button("🚀 AVVIA SCAN"):
        target_key = leagues[sel_name]
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{target_key}/odds/', params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
        if res.status_code == 200:
            st.session_state['api_data'] = res.json()
            st.session_state['api_usage']['remaining'] = res.headers.get('x-requests-remaining')
            st.rerun()
    
    if st.session_state['api_data']:
        st.write("Risultati trovati. Logica card attiva.")
        # Qui si possono inserire le card grafiche viste nelle immagini

with t2:
    st.button("🔄 AGGIORNA RISULTATI", on_click=check_results, use_container_width=True)
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"]
    if not df_p.empty:
        st.dataframe(df_p, use_container_width=True)
    else:
        st.info("Nessuna giocata pendente.")

with t3:
    st.subheader("🏁 Storico Giocate")
    st.dataframe(df_attuale, use_container_width=True)
