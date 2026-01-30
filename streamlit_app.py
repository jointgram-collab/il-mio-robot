import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V14.5 - MULTI-API", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- GESTIONE DOPPIA CHIAVE ---
# Ho inserito le tue chiavi in una lista per la rotazione automatica
API_KEYS = [
    '01f1c8f2a314814b17de03eeb6c53623', # Chiave 1
    'INSERISCI_QUI_LA_TUA_SECONDA_CHIAVE' # Sostituisci questa stringa con la nuova chiave
]

BUDGET_DISPONIBILE = 500.0
OBIETTIVO_TARGET = 5000.0

if 'api_usage' not in st.session_state:
    st.session_state['api_usage'] = {'remaining': "N/D", 'used': "N/D", 'active_index': 0}
if 'api_data' not in st.session_state:
    st.session_state['api_data'] = []

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie",
    "soccer_spain_la_liga": "🇪🇸 La Liga", "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_france_ligue_1": "🇫🇷 Ligue 1", "soccer_uefa_europa_league": "🇪🇺 Europa League",
    "soccer_uefa_champions_league": "🏆 Champions"
}

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "William Hill", "888sport"]

# --- FUNZIONI INTELLIGENTI API ---
def chiamata_sicura_api(endpoint, params_extra={}):
    """Tenta la chiamata con la chiave attiva. Se fallisce, ruota sulla successiva."""
    idx = st.session_state['api_usage'].get('active_index', 0)
    
    for _ in range(len(API_KEYS)):
        current_key = API_KEYS[idx]
        params = {'api_key': current_key, 'regions': 'eu', 'markets': 'totals'}
        params.update(params_extra)
        
        try:
            r = requests.get(endpoint, params=params)
            # Se la chiave è esaurita (429) o non valida (401), passiamo alla prossima
            if r.status_code in [401, 429]:
                idx = (idx + 1) % len(API_KEYS)
                st.session_state['api_usage']['active_index'] = idx
                continue
            
            if r.status_code == 200:
                # Aggiorna contatori sidebar
                st.session_state['api_usage']['remaining'] = r.headers.get('x-requests-remaining', "0")
                st.session_state['api_usage']['used'] = r.headers.get('x-requests-used', "0")
                return r.json()
        except:
            idx = (idx + 1) % len(API_KEYS)
            st.session_state['api_usage']['active_index'] = idx
            
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

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V14.5")
df_attuale = carica_db()

with st.sidebar:
    st.header("📊 Stato Slot API")
    st.info(f"Slot Attivo: {st.session_state['api_usage']['active_index'] + 1} / {len(API_KEYS)}")
    c1, c2 = st.columns(2)
    c1.metric("Residui", st.session_state['api_usage']['remaining'])
    c2.metric("Usati", st.session_state['api_usage']['used'])
    st.divider()
    budget_cassa = st.number_input("Cassa (€)", value=BUDGET_DISPONIBILE)
    rischio = st.slider("Kelly", 0.05, 0.50, 0.15)
    soglia_val = st.slider("Valore Min %", 0, 15, 3) / 100

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER ---
with t1:
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    c_sel, c_all, c_sing, c_ore = st.columns([1.5, 1, 1, 1])
    sel_name = c_sel.selectbox("Campionato:", list(leagues.keys()))
    ore_limite = c_ore.selectbox("Window:", [24, 48, 72, 96, 120, 168], index=2)
    
    if c_all.button("🚀 SCAN TOTALE", use_container_width=True):
        all_found = []
        pbar = st.progress(0)
        for idx, k in enumerate(LEAGUE_NAMES.keys()):
            data = chiamata_sicura_api(f'https://api.the-odds-api.com/v4/sports/{k}/odds/')
            if data: all_found.extend(data)
            time.sleep(0.3)
            pbar.progress((idx + 1) / len(LEAGUE_NAMES))
        st.session_state['api_data'] = all_found
        st.rerun()

    if c_sing.button("🔍 SCAN SINGOLO", use_container_width=True):
        data = chiamata_sicura_api(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_name]}/odds/')
        if data: st.session_state['api_data'] = data
        st.rerun()

    # Visualizzazione Risultati
    if st.session_state['api_data']:
        pend_list = df_attuale[df_attuale['Esito'] == "Pendente"]['Match'].tolist()
        for i, m in enumerate(st.session_state['api_data']):
            try:
                nome_m = f"{m['home_team']}-{m['away_team']}"
                dt_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
                if dt_m > datetime.utcnow() + timedelta(hours=ore_limite): continue
                
                opts = []
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_EURO_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == 'totals'), None)
                        if mk:
                            for o in mk['outcomes']:
                                if o.get('point') == 2.5:
                                    q = o['price']
                                    val = ((1/q + 0.06) * q) - 1
                                    if val >= soglia_val:
                                        opts.append({"T": f"{o['name'].upper()} 2.5", "Q": q, "V": val, "BK": b['title']})
                if opts:
                    best = max(opts, key=lambda x: x['V'])
                    stk = round(max(2.0, min(budget_cassa * (best['V']/(best['Q']-1)) * rischio, budget_cassa*0.15)), 2)
                    c_a, c_b = st.columns([3, 1])
                    c_a.markdown(f"📅 {dt_m.strftime('%d/%m %H:%M')} | **{nome_m}**<br>🎯 **{best['T']}** @{best['Q']} | 🏦 {best['BK']}", unsafe_allow_html=True)
                    if nome_m in pend_list:
                        c_b.button("✅", key=f"add_{i}", disabled=True, use_container_width=True)
                    elif c_b.button("ADD", key=f"add_{i}", use_container_width=True):
                        nuova = pd.DataFrame([{"Data Match": dt_m.strftime('%d/%m %H:%M'), "Match": nome_m, "Scelta": best['T'], "Quota": best['Q'], "Stake": stk, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": m['sport_key'], "Risultato": "-"}])
                        salva_db(pd.concat([df_attuale, nuova], ignore_index=True)); st.rerun()
                    st.divider()
            except: continue

# --- TAB 2: PORTAFOGLIO ---
with t2:
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"]
    if st.button("🤖 AUTO-CHECK", use_container_width=True, type="primary"):
        for idx, row in df_p.iterrows():
            data = chiamata_sicura_api(f"https://api.the-odds-api.com/v4/sports/{row['Sport_Key']}/scores/", {'daysFrom': 3})
            if data:
                m_res = next((s for s in data if s['home_team'] in row['Match'] and s['completed']), None)
                if m_res:
                    h, a = m_res['scores'][0]['score'], m_res['scores'][1]['score']
                    vinto = (row['Scelta'] == "OVER 2.5" and (int(h)+int(a)) > 2.5) or (row['Scelta'] == "UNDER 2.5" and (int(h)+int(a)) < 2.5)
                    # Funzione di chiusura integrata
                    df_up = carica_db()
                    df_up.at[idx, 'Esito'] = "VINTO" if vinto else "PERSO"
                    df_up.at[idx, 'Profitto'] = round((row['Stake']*row['Quota'])-row['Stake'],2) if vinto else -row['Stake']
                    df_up.at[idx, 'Risultato'] = f"{h}-{a}"
                    salva_db(df_up)
        st.rerun()
    
    for i, r in df_p.iterrows():
        with st.expander(f"{r['Match']} | @{r['Quota']} | {r['Stake']}€"):
            st.write(f"Bookmaker: {r['Bookmaker']}")
            # Pulsanti manuali qui (omessi per brevità, ma presenti nella logica V14.2)
