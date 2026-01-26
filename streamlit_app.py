import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE E CONNESSIONE ---
st.set_page_config(page_title="AI SNIPER V11.44 - TOTAL RESET", layout="wide")

# Parametri Fissi
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
TARGET_FINALE = 5000.0

# Mappatura Campionati Aggiornata
LEAGUE_MAP = {
    "🇮🇹 Serie A": "soccer_italy_serie_a",
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League": "soccer_epl",
    "🇪🇸 La Liga": "soccer_spain_la_liga",
    "🇩🇪 Bundesliga": "soccer_germany_bundesliga",
    "🇫🇷 Ligue 1": "soccer_france_ligue_1",
    "🇪🇺 Champions League": "soccer_uefa_champions_league"
}

BK_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "888sport"]

# --- 2. GESTIONE DATABASE CON PROTEZIONE ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=30) # Cache alta per evitare blocchi 429
def get_data():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
        df['dt_obj'] = pd.to_datetime(df['Data Match'] + f"/{date.today().year}", format="%d/%m %H:%M/%Y", errors='coerce')
        return df.dropna(subset=["Match"])
    except:
        st.error("⚠️ Google Sheets non risponde. Non cliccare nulla per 30 secondi.")
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def save_data(df):
    if 'dt_obj' in df.columns: df = df.drop(columns=['dt_obj'])
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()
    st.toast("✅ Cloud Sincronizzato!")

# --- 3. INTERFACCIA ---
st.title("🎯 AI SNIPER V11.44")
df_db = get_data()

tabs = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER ---
with tabs[0]:
    c1, c2 = st.columns([1, 1])
    sel_league = c1.selectbox("Campionato", list(LEAGUE_MAP.keys()))
    soglia = c2.slider("Soglia Valore %", 0, 15, 3) / 100
    
    if st.button("🚀 AVVIA SCANSIONE"):
        with st.spinner("Recupero dati..."):
            url = f"https://api.the-odds-api.com/v4/sports/{LEAGUE_MAP[sel_league]}/odds/"
            res = requests.get(url, params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
            if res.status_code == 200:
                st.session_state['last_scan'] = res.json()
            else:
                st.error(f"Errore API: {res.status_code}")

    if 'last_scan' in st.session_state:
        pendenti = df_db[df_db['Esito'] == "Pendente"]['Match'].tolist()
        for m in st.session_state['last_scan']:
            nome = f"{m['home_team']}-{m['away_team']}"
            if nome in pendenti: continue # Salta se già giocata
            
            # Logica calcolo valore rapida
            for b in m.get('bookmakers', []):
                if b['title'] in BK_AUTH:
                    mk = next((x for x in b['markets'] if x['key'] == 'totals'), None)
                    if mk:
                        o_q = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), 1.0)
                        u_q = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), 1.0)
                        margin = (1/o_q) + (1/u_q)
                        prob_o = (1/o_q)/margin + 0.05
                        val = (prob_o * o_q) - 1
                        
                        if val >= soglia:
                            col_m, col_b = st.columns([4, 1])
                            col_m.write(f"📅 {nome} | **OVER 2.5** @{o_q} | Valore: **{round(val*100, 1)}%**")
                            if col_b.button("ADD", key=f"btn_{nome}"):
                                stake = round(250 * (val/(o_q-1)) * 0.1, 2) # Kelly 10%
                                new_row = {"Data Match": datetime.now().strftime("%d/%m %H:%M"), "Match": nome, "Scelta": "OVER 2.5", "Quota": o_q, "Stake": stake, "Bookmaker": b['title'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": LEAGUE_MAP[sel_league], "Risultato": "-"}
                                save_data(pd.concat([df_db, pd.DataFrame([new_row])], ignore_index=True))
                                st.rerun()

# --- TAB 2: PORTAFOGLIO ---
with tabs[1]:
    pend = df_db[df_db['Esito'] == "Pendente"]
    if not pend.empty:
        for i, r in pend.iterrows():
            col_x, col_y = st.columns([10, 1])
            col_x.markdown(f"🗓️ {r['Data Match']} | **{r['Match']}** | <span style='font-size:1.1rem;'>**{r['Scelta']} @{r['Quota']}**</span> | 💰 {r['Stake']}€", unsafe_allow_html=True)
            if col_y.button("🗑️", key=f"del_{i}"):
                save_data(df_db.drop(i))
                st.rerun()
    else:
        st.info("Nessuna scommessa pendente.")

# --- TAB 3: FISCALE ---
with tabs[2]:
    if not df_db.empty:
        vinte = df_db[df_db['Esito'] == "VINTO"]
        persone = df_db[df_db['Esito'] == "PERSO"]
        netto = round(vinte['Profitto'].sum() + persone['Profitto'].sum(), 2)
        
        st.metric("Profitto Netto Scalata", f"{netto} €", delta=f"{round(TARGET_FINALE - netto, 2)}€ mancanti")
        st.progress(min(1.0, max(0.0, netto / TARGET_FINALE)))
        
        st.dataframe(df_db[["Data Match", "Match", "Scelta", "Quota", "Esito", "Profitto"]].sort_index(ascending=False), use_container_width=True)
