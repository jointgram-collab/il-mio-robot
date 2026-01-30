import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="AI SNIPER V13.6 - FULL", layout="wide")

# --- 2. CSS SIDEBAR HIGH-CONTRAST & UI ---
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #11141a; border-right: 1px solid #30363d; }
    .sb-title { color: #ffffff !important; font-size: 18px; font-weight: 700; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
    .label-text { color: #8b949e; font-size: 14px; font-weight: 500; }
    .value-text { color: #ffffff; font-weight: 700; }
    div[data-testid="stSlider"] [data-baseweb="slider"] [aria-valuenow] { background-color: #ffffff !important; border: 2px solid #39d353 !important; }
    .api-container { background-color: #1c2128; padding: 15px; border-radius: 8px; border: 1px solid #444c56; margin-bottom: 20px; }
    .api-bar-bg { background: #30363d; height: 8px; border-radius: 4px; overflow: hidden; margin-top: 10px; }
    .api-bar-fill { background: #39d353; height: 100%; border-radius: 4px; box-shadow: 0 0 8px #39d353; }
    [data-testid="stWidgetLabel"] p { color: #ffffff !important; font-size: 15px !important; }
    
    /* Stile Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #1c2128; border-radius: 5px; padding: 10px; color: #8b949e; }
    .stTabs [aria-selected="true"] { background-color: #39d353 !important; color: #000 !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONNESSIONI E STATO ---
conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

if 'api_usage' not in st.session_state:
    st.session_state['api_usage'] = {'remaining': "440"}
if 'api_data' not in st.session_state:
    st.session_state['api_data'] = []

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", "soccer_uefa_europa_league": "🇪🇺 Europa League",
    "soccer_uefa_champions_league": "🏆 Champions", "soccer_spain_la_liga": "🇪🇸 La Liga",
    "soccer_germany_bundesliga": "🇩🇪 Bundesliga"
}

# --- 4. MOTORE DATABASE & RISULTATI ---
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
    with st.spinner("🔄 Verifica risultati in corso..."):
        for skey in pendenti['Sport_Key'].unique():
            res = requests.get(f'https://api.the-odds-api.com/v4/sports/{skey}/scores/', params={'api_key': API_KEY, 'daysFrom': 3})
            if res.status_code == 200:
                scores = res.json()
                for i, r in pendenti[pendenti['Sport_Key'] == skey].iterrows():
                    m_parts = r['Match'].split('-')
                    if len(m_parts) != 2: continue
                    t1, t2 = m_parts[0].strip(), m_parts[1].strip()
                    
                    # MATCHING FLESSIBILE: Cerca il match ignorando l'ordine
                    m_res = next((m for m in scores if (t1 in [m['home_team'], m['away_team']] and t2 in [m['home_team'], m['away_team']])), None)
                    
                    if m_res and m_res.get('scores'): # Se c'è un punteggio, procediamo
                        try:
                            s_list = m_res['scores']
                            s1 = int(next(x['score'] for x in s_list if x['name'] == m_res['home_team']))
                            s2 = int(next(x['score'] for x in s_list if x['name'] == m_res['away_team']))
                            tot_gol = s1 + s2
                            vinto = tot_gol > 2.5 if r['Scelta'] == "OVER 2.5" else tot_gol < 2.5
                            
                            # Aggiornamento riga
                            df.at[i, 'Esito'] = "VINTO" if vinto else "PERSO"
                            df.at[i, 'Risultato'] = f"{s1}-{s2}"
                            df.at[i, 'Profitto'] = round((float(r['Stake']) * float(r['Quota'])) - float(r['Stake']), 2) if vinto else -float(r['Stake'])
                            cambiamenti = True
                        except: continue

    if cambiamenti:
        salva_db(df)
        st.success("Risultati aggiornati!")
        st.rerun()
    else:
        st.warning("Nessun nuovo risultato definitivo trovato dall'API.")

# --- 5. SIDEBAR ---
df_attuale = carica_db()
with st.sidebar:
    st.markdown('<div class="sb-title">🔥 API Status</div>', unsafe_allow_html=True)
    rem = st.session_state['api_usage']['remaining']
    st.markdown(f"""
        <div class="api-container">
            <div class="api-row"><span class="label-text">Residui:</span><span class="value-text">{rem}</span></div>
            <div class="api-bar-bg"><div class="api-bar-fill" style="width: 25%;"></div></div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="sb-title">📊 Parametri</div>', unsafe_allow_html=True)
    budget_cassa = st.number_input("Budget (€)", value=500.0)
    rischio = st.slider("Kelly Criterion", 0.05, 0.50, 0.20)
    soglia_val = st.slider("Valore Min %", 0, 15, 3) / 100

# --- 6. MAIN ---
st.title("🎯 AI SNIPER V13.6")

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    c1, c2 = st.columns([3, 1])
    sel_name = c1.selectbox("Campionato:", list(leagues.keys()))
    if c2.button("🚀 SCAN", use_container_width=True):
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_name]}/odds/', params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
        if res.status_code == 200:
            st.session_state['api_data'] = res.json()
            st.session_state['api_usage']['remaining'] = res.headers.get('x-requests-remaining')
            st.rerun()
    
    # Qui visualizzazione card... (Logica già esistente nel tuo codice precedente)

with t2:
    st.header("💼 Gestione Portafoglio")
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"]
    
    if not df_p.empty:
        # --- CRUSCOTTO STATISTICHE ---
        tot_imp = round(df_p['Stake'].astype(float).sum(), 2)
        rit_pot = round((df_p['Stake'].astype(float) * df_p['Quota'].astype(float)).sum(), 2)
        
        c1, c2 = st.columns(2)
        c1.metric("TOTALE IMPEGNATO", f"{tot_imp} €")
        c2.metric("RITORNO POTENZIALE", f"{rit_pot} €", delta_color="normal")
        
        st.button("🔄 AGGIORNA RISULTATI", on_click=check_results, use_container_width=True)
        st.divider()
        st.dataframe(df_p, use_container_width=True)
    else:
        st.info("Nessun match in attesa.")

with t3:
    st.header("📊 Cruscotto Fiscale")
    if not df_attuale.empty:
        # Statistiche globali
        vinto = df_attuale[df_attuale['Esito'] == "VINTO"]['Profitto'].sum()
        perso = df_attuale[df_attuale['Esito'] == "PERSO"]['Stake'].sum()
        netto = vinto - perso
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Vinto Netto", f"{round(vinto,2)} €")
        m2.metric("Perso", f"{round(perso,2)} €")
        m3.metric("Profitto Totale", f"{round(netto,2)} €", delta=f"{round(netto,2)} €")
        
        st.divider()
        # Funzioni Backup
        c_down, c_up = st.columns(2)
        csv = df_attuale.to_csv(index=False).encode('utf-8')
        c_down.download_button("📥 SCARICA BACKUP CSV", csv, "sniper_backup.csv", "text/csv", use_container_width=True)
        
        up_file = c_up.file_uploader("Ripristina da CSV", type="csv")
        if up_file:
            if st.button("🔄 CARICA BACKUP"):
                salva_db(pd.read_csv(up_file))
                st.rerun()
        
        st.dataframe(df_attuale.sort_index(ascending=False), use_container_width=True)
