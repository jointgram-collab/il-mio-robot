import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V15.1.14 - RECOVERY", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. COSTANTI E CHIAVI ---
# Assicurati che queste chiavi siano attive su the-odds-api.com
API_KEYS = ['01f1c8f2a314814b17de03eeb6c53623', '55f08c25f38fa1006dd9e66282170e1a']

if 'api_usage' not in st.session_state:
    st.session_state['api_usage'] = {'remaining': "Verifica in corso...", 'active_index': 0}
if 'api_data' not in st.session_state:
    st.session_state['api_data'] = []

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie",
    "soccer_spain_la_liga": "🇪🇸 La Liga", "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_france_ligue_1": "🇫🇷 Ligue 1", "soccer_uefa_europa_league": "🇪🇺 Europa League",
    "soccer_uefa_champions_league": "🏆 Champions"
}

MARKET_MAP = {
    "Under/Over 2.5": "totals",
    "Esito Finale (1X2)": "h2h",
    "Goal/No Goal": "both_teams_to_score"
}

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "William Hill", "888sport"]

# --- 3. FUNZIONI CORE (POTENZIATE) ---
def chiamata_sicura_api(endpoint, params_extra={}):
    for i in range(len(API_KEYS)):
        idx = (st.session_state['api_usage']['active_index'] + i) % len(API_KEYS)
        params = {'api_key': API_KEYS[idx], 'regions': 'eu', 'oddsFormat': 'decimal'}
        params.update(params_extra)
        try:
            r = requests.get(endpoint, params=params, timeout=15)
            if r.status_code == 200:
                st.session_state['api_usage']['active_index'] = idx
                st.session_state['api_usage']['remaining'] = r.headers.get('x-requests-remaining', "N/D")
                return r.json()
            elif r.status_code == 401:
                st.error(f"Chiave API {idx} non valida o scaduta (Errore 401).")
            elif r.status_code == 429:
                st.warning(f"Chiave API {idx} ha esaurito i crediti (Errore 429).")
        except Exception as e:
            st.error(f"Errore di connessione: {e}")
    return None

def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        return df.dropna(subset=["Match"]) if df is not None else pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

# --- 4. INTERFACCIA ---
st.title("🎯 AI SNIPER V15.1.14")
df_attuale = carica_db()

with st.sidebar:
    st.header("📊 Parametri")
    budget_cassa = st.number_input("Budget Attuale (€)", value=500.0)
    rischio_kelly = st.slider("Aggressività Kelly", 0.05, 0.50, 0.15)
    soglia_valore = st.slider("Min Value %", 0, 15, 0) / 100
    st.info(f"API Residue: {st.session_state['api_usage']['remaining']}")
    if st.button("🔄 Test Connessione"):
        chiamata_sicura_api('https://api.the-odds-api.com/v4/sports/')
        st.rerun()

tab1, tab2, tab3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE & BACKUP"])

with tab1:
    c_a, c_b, c_m, c_o = st.columns([1.5, 1, 1.5, 0.8])
    leagues_map = {v: k for k, v in LEAGUE_NAMES.items()}
    sel_league = c_a.selectbox("Campionato:", ["TUTTI"] + list(leagues_map.keys()))
    sel_market = c_m.selectbox("Mercato:", list(MARKET_MAP.keys()))
    ore_max = c_o.selectbox("Fino a (Ore):", [24, 48, 72, 96, 120], index=1)
    
    if c_b.button("🚀 AVVIA SCANNER", use_container_width=True, type="primary"):
        all_results = []
        m_key = MARKET_MAP[sel_market]
        target_leagues = list(leagues_map.values()) if sel_league == "TUTTI" else [leagues_map[sel_league]]
        
        progress_bar = st.progress(0)
        for i, l_key in enumerate(target_leagues):
            data = chiamata_sicura_api(f'https://api.the-odds-api.com/v4/sports/{l_key}/odds/', {'markets': m_key})
            if data:
                all_results.extend(data)
            progress_bar.progress((i + 1) / len(target_leagues))
        
        st.session_state['api_data'] = all_results
        if not all_results:
            st.warning("Nessun dato ricevuto. Controlla i messaggi di errore sopra o le chiavi API.")
        st.rerun()

    if st.session_state['api_data']:
        st.divider()
        pend_list = df_attuale[df_attuale['Esito'] == "Pendente"]['Match'].tolist()
        m_key = MARKET_MAP[sel_market]
        match_contatore = 0
        
        for i, m in enumerate(st.session_state['api_data']):
            try:
                nome_m = f"{m['home_team']}-{m['away_team']}"
                dt_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
                if dt_m > datetime.utcnow() + timedelta(hours=ore_max): continue
                
                opts = []
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_EURO_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == m_key), None)
                        if mk:
                            for o in mk['outcomes']:
                                if m_key == "totals" and o.get('point') != 2.5: continue
                                q = o['price']
                                
                                # VALORE AGGRESSIVO PER GG/NG
                                margin = 0.04 if m_key == "both_teams_to_score" else 0.06
                                val = ((1/q + margin) * q) - 1
                                
                                if val >= soglia_valore:
                                    if m_key == "both_teams_to_score":
                                        label = "GOAL (GG)" if o['name'].lower() in ["yes", "both"] else "NO GOAL (NG)"
                                    elif m_key == "totals":
                                        label = f"{o['name'].upper()} 2.5"
                                    else:
                                        label = o['name']
                                    opts.append({"T": label, "Q": q, "V": val, "BK": b['title']})
                
                if opts:
                    match_contatore += 1
                    best = max(opts, key=lambda x: x['V'])
                    stk = round(max(2.0, min(budget_cassa * (best['V']/(best['Q']-1)) * rischio_kelly, budget_cassa*0.15)), 2)
                    col1, col2, col3, col4, col5 = st.columns([3, 1.2, 1.5, 1, 0.8])
                    col1.write(f"📅 {dt_m.strftime('%d/%m %H:%M')} | **{nome_m}**")
                    col2.write(f"🎯 {best['T']} | **@{best['Q']}**")
                    col3.write(f"🏦 {best['BK']} | **{round(best['V']*100,1)}%**")
                    col4.write(f"💰 **{stk}€**")
                    if nome_m in pend_list:
                        col5.button("✅", key=f"ok_{i}", disabled=True)
                    elif col5.button("ADD", key=f"add_{i}"):
                        nuova = pd.DataFrame([{"Data Match": nome_m, "Scelta": best['T'], "Quota": best['Q'], "Stake": stk, "Bookmaker": best['BK'], "Esito": "Pendente", "Sport_Key": m['sport_key']}])
                        # Nota: salva_db va integrata qui per il tuo foglio
                        st.success("Aggiunto!")
                    st.divider()
            except: continue
        
        if match_contatore == 0:
            st.info("Scanner completato: nessun match trovato con i parametri attuali.")
