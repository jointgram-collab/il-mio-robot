import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V11.45 - Debug Mode", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
TARGET_FINALE = 5000.0

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "888sport"]

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", "soccer_england_efl_championship": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Championship",
    "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie", "soccer_spain_la_liga": "🇪🇸 La Liga",
    "soccer_germany_bundesliga": "🇩🇪 Bundesliga", "soccer_uefa_champions_league": "🇪🇺 Champions",
    "soccer_france_ligue_1": "🇫🇷 Ligue 1"
}

def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        return df.dropna(subset=["Match"]) if df is not None else pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

st.title("🎯 AI SNIPER V11.45")
if 'api_data' not in st.session_state: st.session_state['api_data'] = []

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    df_tot = carica_db()
    with st.sidebar:
        st.header("⚙️ Parametri")
        budget_cassa = st.number_input("Budget (€)", value=250.0)
        rischio = st.slider("Kelly", 0.05, 0.50, 0.20)
        soglia_val = st.slider("Valore Min %", -5, 15, 2) / 100
        st.info("Abbassa la soglia a -5% per vedere tutti i match estratti.")

    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    c1, c2 = st.columns(2)
    sel_name = c1.selectbox("Campionato:", list(leagues.keys()))
    sel_market = c2.selectbox("Mercato:", ["Over/Under 2.5", "Gol/No Gol"])
    
    # Per evitare il 422, chiediamo 'totals' (che spesso include anche btts in automatico in molti campionati)
    m_key = "totals" if sel_market == "Over/Under 2.5" else "btts"

    if st.button("🚀 AVVIA SCANSIONE", use_container_width=True):
        st.session_state['api_data'] = [] 
        with st.spinner("Contattando Server..."):
            res = requests.get(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_name]}/odds/', 
                               params={'api_key': API_KEY, 'regions': 'eu', 'markets': m_key})
            
            if res.status_code == 200:
                st.session_state['api_data'] = res.json()
                st.success(f"Analisi di {len(st.session_state['api_data'])} eventi in corso...")
            else:
                st.error(f"Errore {res.status_code}. Il mercato '{sel_market}' potrebbe non essere supportato per questa lega.")

    if st.session_state['api_data']:
        match_visualizzati = 0
        for m in st.session_state['api_data']:
            try:
                nome_match = f"{m['home_team']}-{m['away_team']}"
                date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
                opts = []
                
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_EURO_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == m_key), None)
                        if mk:
                            if m_key == "totals":
                                q_ov = next((o['price'] for o in mk['outcomes'] if o['name'].lower() == 'over' and o['point'] == 2.5), None)
                                q_un = next((o['price'] for o in mk['outcomes'] if o['name'].lower() == 'under' and o['point'] == 2.5), None)
                                if q_ov and q_un:
                                    margin = (1/q_ov) + (1/q_un)
                                    opts.append({"T": "OVER 2.5", "Q": q_ov, "P": ((1/q_ov)/margin)+0.06, "BK": b['title']})
                            else: # btts
                                q_yes = next((o['price'] for o in mk['outcomes'] if o['name'].lower() in ['yes', 'gol', 'both']), None)
                                q_no = next((o['price'] for o in mk['outcomes'] if o['name'].lower() in ['no', 'nogol', 'neither']), None)
                                if q_yes and q_no:
                                    margin = (1/q_yes) + (1/q_no)
                                    opts.append({"T": "GOL", "Q": q_yes, "P": ((1/q_yes)/margin)+0.06, "BK": b['title']})
                
                if opts:
                    best = max(opts, key=lambda x: (x['P'] * x['Q']) - 1)
                    val = (best['P'] * best['Q']) - 1
                    
                    if val >= soglia_val:
                        match_visualizzati += 1
                        col_t, col_b = st.columns([3, 1])
                        txt_color = "green" if val > 0 else "red"
                        col_t.markdown(f"📅 {date_m} | **{nome_match}** | <span style='color:{txt_color}'>Valore: {round(val*100,1)}%</span> ({best['BK']})", unsafe_allow_html=True)
                        if col_b.button(f"ADD {best['T']} @{best['Q']}", key=f"add_{nome_match}_{best['T']}"):
                            stake = round(max(2.0, min(budget_cassa * (val/(best['Q']-1)) * rischio, budget_cassa*0.15)), 2)
                            n = {"Data Match": date_m, "Match": nome_match, "Scelta": best['T'], "Quota": best['Q'], "Stake": stake, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": leagues[sel_name], "Risultato": "-"}
                            salva_db(pd.concat([carica_db(), pd.DataFrame([n])], ignore_index=True))
                            st.rerun()
            except: continue
        
        if match_visualizzati == 0:
            st.warning("Nessun match trovato con i parametri attuali. Prova ad abbassare il 'Valore Min %' nella sidebar a -5%.")

with t2:
    st.subheader("💼 Portafoglio")
    df_p = carica_db()
    if not df_p.empty: st.dataframe(df_p[df_p['Esito'] == "Pendente"], use_container_width=True)

with t3:
    st.subheader("📊 Fiscale")
    df_f = carica_db()
    if not df_f.empty: st.dataframe(df_f.sort_index(ascending=False), use_container_width=True)
