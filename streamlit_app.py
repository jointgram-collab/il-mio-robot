import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date, timedelta
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V11.43 - Robust Scan", layout="wide")

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

# --- MOTORE DATABASE ---
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
        df = df.dropna(subset=["Match"])
        return df
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11.43")
if 'api_data' not in st.session_state: st.session_state['api_data'] = []

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    df_tot = carica_db()
    with st.sidebar:
        budget_cassa = st.number_input("Budget (€)", value=250.0)
        rischio = st.slider("Kelly", 0.05, 0.50, 0.20)
        soglia_val = st.slider("Valore Min %", -2, 15, 2) / 100 # Abbassata per test
        st.divider()
        st.download_button("BACKUP CSV", data=df_tot.to_csv(index=False).encode('utf-8'), file_name="backup.csv")

    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    c1, c2 = st.columns(2)
    sel_name = c1.selectbox("Campionato:", list(leagues.keys()))
    sel_market = c2.selectbox("Mercato:", ["Over/Under 2.5", "Gol/No Gol"])
    
    # Per evitare l'errore 422, usiamo una richiesta multi-mercato più sicura
    if st.button("🚀 AVVIA SCANSIONE", use_container_width=True):
        st.session_state['api_data'] = [] # Reset
        with st.spinner("Interrogazione API..."):
            # Usiamo 'totals' per O/U e 'btts' per Gol/NoGol
            m_key = "totals" if sel_market == "Over/Under 2.5" else "btts"
            res = requests.get(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_name]}/odds/', 
                               params={'api_key': API_KEY, 'regions': 'eu', 'markets': m_key, 'oddsFormat': 'decimal'})
            
            if res.status_code == 200:
                st.session_state['api_data'] = res.json()
                st.success(f"Trovati {len(st.session_state['api_data'])} match grezzi.")
            else:
                st.error(f"Errore API {res.status_code}: Verificare se il mercato '{m_key}' è attivo per questa lega.")

    if st.session_state['api_data']:
        found_any = False
        for m in st.session_state['api_data']:
            nome_match = f"{m['home_team']}-{m['away_team']}"
            date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
            opts = []
            
            for b in m.get('bookmakers', []):
                if b['title'] in BK_EURO_AUTH:
                    m_key = "totals" if sel_market == "Over/Under 2.5" else "btts"
                    mk = next((x for x in b['markets'] if x['key'] == m_key), None)
                    if mk:
                        try:
                            if m_key == "totals":
                                q_ov = next(o['price'] for o in mk['outcomes'] if o['name'].lower() == 'over' and o['point'] == 2.5)
                                q_un = next(o['price'] for o in mk['outcomes'] if o['name'].lower() == 'under' and o['point'] == 2.5)
                                margin = (1/q_ov) + (1/q_un)
                                opts.append({"T": "OVER 2.5", "Q": q_ov, "P": ((1/q_ov)/margin)+0.06, "BK": b['title']})
                                opts.append({"T": "UNDER 2.5", "Q": q_un, "P": ((1/q_un)/margin)+0.06, "BK": b['title']})
                            else: # btts
                                q_yes = next(o['price'] for o in mk['outcomes'] if o['name'].lower() in ['yes', 'gol', 'both'])
                                q_no = next(o['price'] for o in mk['outcomes'] if o['name'].lower() in ['no', 'nogol', 'neither'])
                                margin = (1/q_yes) + (1/q_no)
                                opts.append({"T": "GOL", "Q": q_yes, "P": ((1/q_yes)/margin)+0.06, "BK": b['title']})
                                opts.append({"T": "NO GOL", "Q": q_no, "P": ((1/q_no)/margin)+0.06, "BK": b['title']})
                        except: continue
            
            if opts:
                best = max(opts, key=lambda x: (x['P'] * x['Q']) - 1)
                val = (best['P'] * best['Q']) - 1
                if val > soglia_val:
                    found_any = True
                    col_t, col_b = st.columns([3, 1])
                    col_t.write(f"📅 {date_m} | **{nome_match}** | Valore: {round(val*100,1)}% ({best['BK']})")
                    if col_b.button(f"ADD {best['T']} @{best['Q']}", key=f"add_{nome_match}_{best['T']}"):
                        stake = round(max(2.0, min(budget_cassa * (val/(best
