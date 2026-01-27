import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date, timedelta
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V11.50 - Stability", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
TARGET_FINALE = 5000.0

# Usiamo esattamente le chiavi della 11.39 che sai che funzionano
LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A",
    "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_england_league_1": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", # Mantengo questa se per te funzionava
    "soccer_spain_la_liga": "🇪🇸 La Liga",
    "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_uefa_champions_league": "🇪🇺 Champions",
    "soccer_france_ligue_1": "🇫🇷 Ligue 1"
}

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "888sport"]

# --- MOTORE DATABASE (STILE 11.39) ---
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
        df = df.dropna(subset=["Match"])
        df['dt_obj'] = pd.to_datetime(df['Data Match'] + f"/{date.today().year}", format="%d/%m %H:%M/%Y", errors='coerce')
        return df
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    if 'dt_obj' in df.columns: df = df.drop(columns=['dt_obj'])
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

# --- LOGICA RISULTATI ---
def check_results():
    df = carica_db()
    pendenti = df[df['Esito'] == "Pendente"]
    if pendenti.empty: return
    cambiamenti = False
    with st.spinner("🔄 Verifica risultati..."):
        for skey in pendenti['Sport_Key'].unique():
            res = requests.get(f'https://api.the-odds-api.com/v4/sports/{skey}/scores/', params={'api_key': API_KEY, 'daysFrom': 3})
            if res.status_code == 200:
                scores = res.json()
                for i, r in pendenti[pendenti['Sport_Key'] == skey].iterrows():
                    m_res = next((m for m in scores if f"{m['home_team']}-{m['away_team']}" == r['Match'] and m.get('completed')), None)
                    if m_res and m_res.get('scores'):
                        s = m_res['scores']
                        score_str = f"{s[0]['score']}-{s[1]['score']}"
                        goals = sum(int(x['score']) for x in s)
                        vinto = (r['Scelta'] == "OVER 2.5" and goals > 2.5) or (r['Scelta'] == "UNDER 2.5" and goals < 2.5)
                        df.at[i, 'Esito'] = "VINTO" if vinto else "PERSO"
                        df.at[i, 'Risultato'] = score_str
                        df.at[i, 'Profitto'] = round((r['Stake']*r['Quota'])-r['Stake'], 2) if vinto else -r['Stake']
                        cambiamenti = True
    if cambiamenti: salva_db(df); st.rerun()

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11.50")
if 'api_data' not in st.session_state: st.session_state['api_data'] = []

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    df_tot = carica_db()
    match_pendenti = df_tot[df_tot['Esito'] == "Pendente"]['Match'].tolist() if not df_tot.empty else []
    
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    sel_name = st.selectbox("Campionato:", list(leagues.keys()))
    soglia_v = st.slider("Valore Min %", 0, 15, 5) / 100

    if st.button("🚀 SCANSIONA"):
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_name]}/odds/', params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
        if res.status_code == 200:
            st.session_state['api_data'] = res.json()
            st.sidebar.write(f"Crediti: {res.headers.get('x-requests-remaining')}")

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
                                opts.append({"T": "OVER 2.5", "Q": q_ov, "P": ((1/q_ov)/margin)+0.06, "BK": b['title']})
                if opts:
                    best = max(opts, key=lambda x: (x['P'] * x['Q']) - 1)
                    val = (best['P'] * best['Q']) - 1
                    if val >= soglia_v:
                        col_t, col_b = st.columns([4, 1])
                        col_t.write(f"📅 {date_m} | **{nome_match}** | Valore: {round(val*100,1)}%")
                        if col_b.button(f"ADD {best['Q']}", key=f"add_{nome_match}"):
                            n = {"Data Match": date_m, "Match": nome_match, "Scelta": best['T'], "Quota": best['Q'], "Stake": 25.0, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": leagues[sel_name], "Risultato": "-"}
                            salva_db(pd.concat([carica_db(), pd.DataFrame([n])], ignore_index=True))
                            st.rerun()
            except: continue

with t2:
    st.subheader("💼 Portafoglio")
    df_p = carica_db()
    pend = df_p[df_p['Esito'] == "Pendente"]
    st.button("🔄 AGGIORNA RISULTATI", on_click=check_results)
    st.dataframe(pend) # Visualizzazione semplice come 11.39

with t3:
    st.subheader("📊 Fiscale & Backup")
    df_f = carica_db()
    # --- IL TUO NUOVO BACKUP MANUALE ---
    if not df_f.empty:
        csv = df_f.to_csv(index=False).encode('utf-8')
        st.download_button("📥 SCARICA BACKUP DI SICUREZZA (CSV)", data=csv, file_name="sniper_backup.csv", mime='text/csv')
    st.dataframe(df_f)
