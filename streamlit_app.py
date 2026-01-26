import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date, timedelta
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="AI SNIPER V11.43", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
TARGET_FINALE = 5000.0

# DIZIONARIO AGGIORNATO: Nota 'soccer_epl' per la Premier
LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A",
    "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", 
    "soccer_spain_la_liga": "🇪🇸 La Liga",
    "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_uefa_champions_league": "🇪🇺 Champions",
    "soccer_france_ligue_1": "🇫🇷 Ligue 1"
}

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin"]

# --- FUNZIONI DATABASE (CON CACHE ANTI-BLOCCO) ---
@st.cache_data(ttl=20) # Aumentato a 20 secondi per sicurezza
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
        df = df.dropna(subset=["Match"])
        df['dt_obj'] = pd.to_datetime(df['Data Match'] + f"/{date.today().year}", format="%d/%m %H:%M/%Y", errors='coerce')
        return df
    except:
        st.error("🚨 Google Sheets è temporaneamente bloccato (Errore 429). Attendi 30 secondi senza cliccare nulla.")
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    if 'dt_obj' in df.columns: df = df.drop(columns=['dt_obj'])
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()
    st.toast("✅ Salvataggio Cloud completato!")

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11.43")
if 'api_data' not in st.session_state: st.session_state['api_data'] = []

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    df_tot = carica_db()
    match_pendenti = df_tot[df_tot['Esito'] == "Pendente"]['Match'].tolist() if not df_tot.empty else []

    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    sel_name = st.selectbox("Seleziona Campionato:", list(leagues.keys()))
    
    col_btn, col_val = st.columns([1, 2])
    scansiona = col_btn.button("🚀 AVVIA SCANNER")
    soglia = col_val.slider("Valore Minimo %", 0, 15, 2) / 100

    if scansiona:
        with st.spinner(f"Chiamata API per {sel_name}..."):
            url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_name]}/odds/'
            res = requests.get(url, params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
            
            if res.status_code == 200:
                st.session_state['api_data'] = res.json()
                if not st.session_state['api_data']:
                    st.info(f"Nessun match quotato trovato per {sel_name}. Riprova tra qualche ora.")
            elif res.status_code == 429:
                st.error("Hai esaurito i crediti mensili di The-Odds-API!")
            else:
                st.error(f"Errore API: {res.status_code}")

    if st.session_state['api_data']:
        for m in st.session_state['api_data']:
            try:
                nome_match = f"{m['home_team']}-{m['away_team']}"
                if nome_match in match_pendenti: continue
                
                date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
                opts = []
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_EURO_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == 'totals'), None)
                        if mk:
                            q_ov = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), None)
                            q_un = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), None)
                            if q_ov and q_un:
                                margin = (1/q_ov) + (1/q_un)
                                opts.append({"T": "OVER 2.5", "Q": q_ov, "P": ((1/q_ov)/margin)+0.05, "BK": b['title']})
                                opts.append({"T": "UNDER 2.5", "Q": q_un, "P": ((1/q_un)/margin)+0.05, "BK": b['title']})
                
                if opts:
                    best = max(opts, key=lambda x: (x['P'] * x['Q']) - 1)
                    valore = (best['P'] * best['Q']) - 1
                    if valore >= soglia:
                        c_info, c_add = st.columns([3, 1])
                        c_info.write(f"📅 {date_m} | **{nome_match}** | Valore: {round(valore*100,1)}%")
                        if c_add.button(f"ADD {best['T']} @{best['Q']}", key=f"a_{nome_match}"):
                            # Calcolo Stake Kelly semplificato
                            stake = round(max(2.0, min(100 * (valore/best['Q']), 25.0)), 2)
                            nuova_g = {"Data Match": date_m, "Match": nome_match, "Scelta": best['T'], "Quota": best['Q'], "Stake": stake, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": leagues[sel_name], "Risultato": "-"}
                            salva_db(pd.concat([carica_db(), pd.DataFrame([nuova_g])], ignore_index=True))
                            st.rerun()
                        st.divider()
            except: continue

# --- TAB 2 & 3 (PORTAFOGLIO E FISCALE) ---
# [Mantieni il codice della V11.42 per brevità, sono compatibili]
