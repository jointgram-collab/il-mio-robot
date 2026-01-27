import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="AI SNIPER V11.48", layout="wide")

API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
TARGET_FINALE = 5000.0

LEAGUE_MAP = {
    "🇮🇹 Serie A": "soccer_italy_serie_a",
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League": "soccer_epl",
    "🇪🇸 La Liga": "soccer_spain_la_liga",
    "🇩🇪 Bundesliga": "soccer_germany_bundesliga",
    "🇫🇷 Ligue 1": "soccer_france_ligue_1",
    "🇪🇺 Champions League": "soccer_uefa_champions_league"
}

BK_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "888sport"]

# --- 2. MOTORE DATABASE (CON CACHE ANTI-BLOCCO) ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=20)
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
        # Gestione data
        df['dt_obj'] = pd.to_datetime(df['Data Match'] + f"/{date.today().year}", format="%d/%m %H:%M/%Y", errors='coerce')
        return df.dropna(subset=["Match"])
    except Exception as e:
        st.error(f"Errore connessione Google: {e}")
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    if 'dt_obj' in df.columns: df = df.drop(columns=['dt_obj'])
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()
    st.toast("✅ Cloud Sincronizzato!")

# --- 3. AUTO-CHECK RISULTATI ---
def check_results():
    df = carica_db()
    pendenti = df[df['Esito'] == "Pendente"]
    if pendenti.empty: return
    cambiamenti = False
    with st.spinner("🔄 Recupero Score..."):
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

# --- 4. INTERFACCIA PRINCIPALE ---
st.title("🎯 AI SNIPER V11.48")
df_tot = carica_db()

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER CON DEEP DEBUG ---
with t1:
    col_l, col_v = st.columns([1, 2])
    sel_name = col_l.selectbox("Campionato:", list(LEAGUE_MAP.keys()))
    soglia_v = col_v.slider("Soglia Valore %", 0, 15, 2) / 100
    
    if st.button("🚀 AVVIA SCANSIONE", use_container_width=True):
        st.session_state['api_data'] = None
        with st.status("📡 Connessione API...", expanded=True) as status:
            try:
                url = f'https://api.the-odds-api.com/v4/sports/{LEAGUE_MAP[sel_name]}/odds/'
                params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals', 'oddsFormat': 'decimal'}
                
                st.write("Cercando dati sui server...")
                res = requests.get(url, params=params, timeout=12)
                
                if res.status_code == 200:
                    st.session_state['api_data'] = res.json()
                    rem = res.headers.get('x-requests-remaining', 'N/D')
                    st.sidebar.metric("Crediti API", rem)
                    status.update(label="✅ Dati ricevuti!", state="complete", expanded=False)
                else:
                    st.error(f"Errore API {res.status_code}: {res.text}")
                    status.update(label="❌ Errore API", state="error")
            except Exception as e:
                st.error(f"Connessione fallita: {e}")
                status.update(label="❌ Timeout", state="error")

    if 'api_data' in st.session_state and st.session_state['api_data']:
        match_pendenti = df_tot[df_tot['Esito'] == "Pendente"]['Match'].tolist()
        for m in st.session_state['api_data']:
            try:
                nome_m = f"{m['home_team']}-{m['away_team']}"
                date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
                
                opts = []
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == 'totals'), None)
                        if mk:
                            q_o = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), 0)
                            q_u = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), 0)
                            if q_o > 1 and q_u > 1:
                                margin = (1/q_o) + (1/q_u)
                                prob_o = ((1/q_o)/margin) + 0.05
                                opts.append({"T": "OVER 2.5", "Q": q_o, "V": (prob_o * q_o) - 1, "BK": b['title']})
                
                if opts:
                    best = max(opts, key=lambda x: x['V'])
                    if best['V'] >= soglia_v:
                        c_info, c_add = st.columns([4, 1])
                        if nome_m in match_pendenti:
                            c_info.write(f"📅 {date_m} | {nome_m} | ✅ **IN LISTA**")
                        else:
                            c_info.write(f"📅 {date_m} | **{nome_m}** | Valore: **{round(best['V']*100,1)}%**")
                            if c_add.button(f"ADD {best['Q']}", key=f"btn_{nome_m}"):
                                stake = round(max(2.0, min(250 * (best['V']/(best['Q']-1)) * 0.15, 30.0)), 2)
                                n = {"Data Match": date_m, "Match": nome_m, "Scelta": best['T'], "Quota": best['Q'], "Stake": stake, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": LEAGUE_MAP[sel_name], "Risultato": "-"}
                                salva_db(pd.concat([carica_db(), pd.DataFrame([n])], ignore_index=True))
                                st.rerun()
                        st.divider()
            except: continue

# --- TAB 2: PORTAFOGLIO ---
with t2:
    st.subheader("💼 Portafoglio")
    pend = df_tot[df_tot['Esito'] == "Pendente"]
    if not pend.empty:
        st.button("🔄 AGGIORNA RISULTATI", on_click=check_results, use_container_width=True)
        for i, r in pend.iterrows():
            cm, cb = st.columns([10, 1])
            cm.markdown(f"🗓️ {r['Data Match']} | **{r['Match']}** | <span style='font-size:1.1rem;'>**{r['Scelta']} @{r['Quota']}**</span> | 💰 {r['Stake']}€", unsafe_allow_html=True)
            if cb.button("🗑️", key=f"del_{i}"):
                salva_db(df_tot.drop(i)); st.rerun()
            st.divider()
    else: st.info("Nessuna giocata attiva.")

# --- TAB 3: FISCALE ---
with t3:
    st.subheader("📊 Analisi Fiscale")
    if not df_tot.empty:
        netto = round(df_tot['Profitto'].sum(), 2)
        mancante = round(TARGET_FINALE - netto, 2)
        st.info(f"🏆 Goal: {TARGET_FINALE}€ | Attuale: {netto}€ | Mancano: {mancante}€")
        st.progress(min(1.0, max(0.0, netto / TARGET_FINALE)))
        st.dataframe(df_tot[["Data Match", "Match", "Scelta", "Quota", "Esito", "Profitto", "Risultato"]].sort_index(ascending=False), use_container_width=True)
