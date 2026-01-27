import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE E COSTANTI ---
st.set_page_config(page_title="AI SNIPER V11.46", layout="wide")

API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
TARGET_FINALE = 5000.0

# Mappatura aggiornata con chiavi multiple per sicurezza
LEAGUE_MAP = {
    "🇮🇹 Serie A": "soccer_italy_serie_a",
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League": "soccer_epl",
    "🇪🇸 La Liga": "soccer_spain_la_liga",
    "🇩🇪 Bundesliga": "soccer_germany_bundesliga",
    "🇫🇷 Ligue 1": "soccer_france_ligue_1",
    "🇪🇺 Champions League": "soccer_uefa_champions_league"
}

BK_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "888sport"]

# --- 2. GESTIONE DATABASE (CACHE 15s) ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=15)
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
        df['dt_obj'] = pd.to_datetime(df['Data Match'] + f"/{date.today().year}", format="%d/%m %H:%M/%Y", errors='coerce')
        return df.dropna(subset=["Match"])
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    if 'dt_obj' in df.columns: df = df.drop(columns=['dt_obj'])
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()
    st.toast("✅ Cloud Sincronizzato!")

# --- 3. INTERFACCIA ---
st.title("🎯 AI SNIPER V11.46")
df_tot = carica_db()

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    c1, c2 = st.columns([1, 2])
    sel_name = c1.selectbox("Campionato:", list(LEAGUE_MAP.keys()))
    soglia_v = c2.slider("Soglia Valore %", 0, 15, 2) / 100
    
    if st.button("🚀 SCANSIONA", use_container_width=True):
        with st.spinner("Interrogazione API..."):
            url = f'https://api.the-odds-api.com/v4/sports/{LEAGUE_MAP[sel_name]}/odds/'
            res = requests.get(url, params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
            
            if res.status_code == 200:
                st.session_state['api_data'] = res.json()
                # Visualizzazione crediti residui
                remaining = res.headers.get('x-requests-remaining', 'N/D')
                st.info(f"💳 Crediti API rimanenti: **{remaining}**")
                if not st.session_state['api_data']:
                    st.warning("Nessun match trovato per i parametri Totals 2.5 su questo campionato.")
            else:
                st.error(f"Errore API {res.status_code}: {res.text}")

    if 'api_data' in st.session_state and st.session_state['api_data']:
        match_pendenti = df_tot[df_tot['Esito'] == "Pendente"]['Match'].tolist()
        for m in st.session_state['api_data']:
            try:
                nome_m = f"{m['home_team']}-{m['away_team']}"
                date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
                
                # Cerca la quota migliore tra i bookmaker autorizzati
                best_opt = None
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == 'totals'), None)
                        if mk:
                            q_o = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), 0)
                            q_u = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), 0)
                            if q_o > 1 and q_u > 1:
                                margin = (1/q_o) + (1/q_u)
                                prob_o = ((1/q_o)/margin) + 0.05 # Aggio AI sniper
                                val = (prob_o * q_o) - 1
                                if not best_opt or val > best_opt['val']:
                                    best_opt = {"T": "OVER 2.5", "Q": q_o, "val": val, "BK": b['title']}
                
                if best_opt and best_opt['val'] >= soglia_v:
                    col_info, col_btn = st.columns([4, 1])
                    if nome_m in match_pendenti:
                        col_info.write(f"📅 {date_m} | {nome_m} | ✅ **GIÀ IN LISTA**")
                        col_btn.button("OK", key=f"ok_{nome_m}", disabled=True)
                    else:
                        col_info.write(f"📅 {date_m} | **{nome_m}** | Valore: **{round(best_opt['val']*100,1)}%**")
                        if col_btn.button(f"ADD {best_opt['Q']}", key=f"add_{nome_m}"):
                            stake = round(max(2.0, min(250 * (best_opt['val']/(best_opt['Q']-1)) * 0.15, 30.0)), 2)
                            n = {"Data Match": date_m, "Match": nome_m, "Scelta": best_opt['T'], "Quota": best_opt['Q'], "Stake": stake, "Bookmaker": best_opt['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": LEAGUE_MAP[sel_name], "Risultato": "-"}
                            salva_db(pd.concat([carica_db(), pd.DataFrame([n])], ignore_index=True))
                            st.rerun()
                    st.divider()
            except: continue

# --- TAB 2 & 3 (PORTAFOGLIO E FISCALE) ---
with t2:
    st.subheader("💼 Portafoglio Pendente")
    pend = df_tot[df_tot['Esito'] == "Pendente"]
    for i, r in pend.iterrows():
        cm, cb = st.columns([10, 1])
        riga = f"🗓️ {r['Data Match']} | **{r['Match']}** | <span style='font-size:1.1rem;'>**{r['Scelta']} @{r['Quota']}**</span> | 💰 {r['Stake']}€ | 🏦 {r['Bookmaker']}"
        cm.markdown(riga, unsafe_allow_html=True)
        if cb.button("🗑️", key=f"d_{i}"):
            salva_db(df_tot.drop(i)); st.rerun()
        st.divider()

with t3:
    st.subheader("📊 Analisi Fiscale")
    vinte = df_tot[df_tot['Esito'] == "VINTO"]
    netto = round(df_tot['Profitto'].sum(), 2)
    st.info(f"🏆 **Goal: {TARGET_FINALE}€** | Attuale: **{netto}€**")
    st.progress(min(1.0, max(0.0, netto / TARGET_FINALE)))
    st.dataframe(df_tot[["Data Match", "Match", "Scelta", "Quota", "Esito", "Profitto"]].sort_index(ascending=False), use_container_width=True)
