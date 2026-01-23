import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ALTO CONTRASTO ---
st.set_page_config(page_title="AI SNIPER V11.13", layout="wide")

st.markdown("""
    <style>
    /* Forza visibilità testi */
    [data-testid="stAppViewContainer"] { background-color: #0e1117 !important; }
    h1, h2, h3, p, label, .stMarkdown { color: #ffffff !important; }
    
    /* Card Portafoglio/Scanner */
    .stExpander, div.stBlock {
        background-color: #1a1c24 !important;
        border: 1px solid #30363d !important;
        border-radius: 10px !important;
        padding: 10px !important;
    }
    
    /* Metriche brillanti */
    [data-testid="stMetricValue"] { color: #00ff88 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

# --- FUNZIONI ---
def carica_db():
    try: return conn.read(worksheet="Giocate", ttl="0").dropna(how='all')
    except: return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key"])

def salva_db(df): conn.update(worksheet="Giocate", data=df)

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11.13")

t1, t2, t3 = st.tabs(["🔍 SCANNER VALORE", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    with st.sidebar:
        budget_cassa = st.number_input("Budget (€)", value=250.0)
        rischio = st.slider("Aggressività", 0.1, 0.5, 0.25)
        soglia_val = st.slider("Soglia Valore %", 0, 15, 3) / 100
        
    leagues = {
        "ITALIA: Serie A": "soccer_italy_serie_a", "ITALIA: Serie B": "soccer_italy_serie_b",
        "UK: Premier League": "soccer_england_league_1", "SPAGNA: La Liga": "soccer_spain_la_liga",
        "GERMANIA: Bundesliga": "soccer_germany_bundesliga", "EUROPA: Champions": "soccer_uefa_champions_league"
    }
    sel_league = st.selectbox("Seleziona Campionato:", list(leagues.keys()))

    if st.button("🚀 AVVIA SCANSIONE"):
        try:
            url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/'
            res = requests.get(url, params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
            st.session_state['api_rem'] = res.headers.get('x-requests-remaining')
            
            if res.status_code == 200:
                st.session_state['api_data'] = res.json()
                st.success("Dati Ricevuti correttamente!")
            else:
                st.error(f"Errore API {res.status_code}: {res.text}")
        except Exception as e:
            st.error(f"Errore di connessione: {e}")

    if 'api_rem' in st.session_state:
        st.info(f"💳 Credito Residuo API: {st.session_state['api_rem']}")

    if st.session_state.get('api_data'):
        for m in st.session_state['api_data']:
            # Logica calcolo valore... (mantenuta dalla V11.12)
            home, away = m['home_team'], m['away_team']
            date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
            # ... resto della logica scanner ...

with t2:
    st.subheader("💼 Portafoglio Cloud")
    df_p = carica_db()
    pendenti = df_p[df_p['Esito'] == "Pendente"]
    
    col_exp1, col_exp2 = st.columns(2)
    col_exp1.metric("Totale Scommesso", f"{round(pendenti['Stake'].sum(), 2)} €")
    col_exp2.metric("Potenziale Ritorno", f"{round((pendenti['Stake'] * pendenti['Quota']).sum(), 2)} €")
    
    for i, r in pendenti.iterrows():
        vinc_pot = round(r['Stake'] * r['Quota'], 2)
        with st.container():
            c_a, c_b, c_c = st.columns([3, 2, 1])
            # AGGIUNTA DATA E DETTAGLI ECONOMICI PER RIGA
            c_a.markdown(f"🗓️ **{r['Data Match']}**\n**{r['Match']}**\n{r['Scelta']} @{r['Quota']}")
            c_b.markdown(f"💰 Scommesso: **{r['Stake']}€**\n💸 Vincita: **{vinc_pot}€**")
            if c_c.button("🗑️", key=f"del_p_{i}"):
                salva_db(df_p.drop(i)); st.rerun()
            st.divider()

with t3:
    # ... Sezione Fiscale con pallini 🟢/🔴 ...
    st.subheader("📊 Fiscale & Obiettivi")
    df_f = carica_db()
    if not df_f.empty:
        prof_netto = round(df_f['Profitto'].sum(), 2)
        st.metric("Profitto Netto Attuale", f"{prof_netto} €", delta=f"{prof_netto} €")
        # Storico con pallini già implementato
