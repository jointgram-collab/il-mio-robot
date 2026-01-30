import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V14.4 - DEBUG MODE", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

BUDGET_DISPONIBILE = 500.0
OBIETTIVO_TARGET = 5000.0

# Inizializzazione Session State
if 'api_usage' not in st.session_state:
    st.session_state['api_usage'] = {'remaining': "N/D", 'used': "N/D"}
if 'api_data' not in st.session_state:
    st.session_state['api_data'] = []

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "William Hill", "888sport"]

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie",
    "soccer_spain_la_liga": "🇪🇸 La Liga", "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_france_ligue_1": "🇫🇷 Ligue 1", "soccer_uefa_europa_league": "🇪🇺 Europa League",
    "soccer_uefa_champions_league": "🏆 Champions"
}

# --- FUNZIONI CORE ---
def aggiorna_api_stats(headers):
    rem = headers.get('x-requests-remaining')
    used = headers.get('x-requests-used')
    if rem is not None: st.session_state['api_usage']['remaining'] = rem
    if used is not None: st.session_state['api_usage']['used'] = used

def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        return df.dropna(subset=["Match"]) if df is not None else pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
    except Exception as e:
        st.error(f"Errore caricamento DB: {e}")
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

def chiudi_manualmente(idx, esito, risultato_score="-"):
    df = carica_db()
    if idx in df.index:
        q, s = float(df.at[idx, 'Quota']), float(df.at[idx, 'Stake'])
        df.at[idx, 'Esito'] = esito
        df.at[idx, 'Risultato'] = risultato_score
        df.at[idx, 'Profitto'] = round((s * q) - s, 2) if esito == "VINTO" else -s
        salva_db(df)
        st.rerun()

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V14.4")
df_attuale = carica_db()

with st.sidebar:
    st.header("📊 Stato API")
    c1, c2 = st.columns(2)
    c1.metric("Residui", st.session_state['api_usage']['remaining'])
    c2.metric("Usati", st.session_state['api_usage']['used'])
    st.divider()
    budget_cassa = st.number_input("Cassa Operativa (€)", value=BUDGET_DISPONIBILE)
    rischio = st.slider("Aggressività (Kelly)", 0.05, 0.50, 0.15)
    soglia_val = st.slider("Filtro Valore Min %", 0, 15, 3) / 100
    debug_mode = st.checkbox("🐞 Attiva Debug Mode")

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER ---
with t1:
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    c_sel, c_all, c_sing, c_ore = st.columns([1.5, 1, 1, 1])
    sel_name = c_sel.selectbox("Campionato:", list(leagues.keys()))
    ore_limite = c_ore.selectbox("Window Ore:", [24, 48, 72, 96, 120, 168], index=2)
    
    if c_all.button("🚀 SCAN TOTALE", use_container_width=True):
        all_found = []
        pbar = st.progress(0)
        for idx, k in enumerate(LEAGUE_NAMES.keys()):
            r = requests.get(f'https://api.the-odds-api.com/v4/sports/{k}/odds/', params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
            if r.status_code == 200:
                aggiorna_api_stats(r.headers)
                all_found.extend(r.json())
            elif debug_mode: st.warning(f"Errore su {k}: {r.status_code}")
            time.sleep(0.3)
            pbar.progress((idx + 1) / len(LEAGUE_NAMES))
        st.session_state['api_data'] = all_found
        st.rerun()

    if c_sing.button("🔍 SCAN SINGOLO", use_container_width=True):
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_name]}/odds/', params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
        if res.status_code == 200:
            aggiorna_api_stats(res.headers)
            st.session_state['api_data'] = res.json()
            if not res.json() and debug_mode: st.info("L'API ha risposto correttamente ma non ci sono match disponibili.")
        else:
            st.error(f"Errore API {res.status_code}: {res.text}")
        st.rerun()

    if st.session_state['api_data']:
        pend_list = df_attuale[df_attuale['Esito'] == "Pendente"]['Match'].tolist()
        matches_visualizzati = 0
        
        for i, m in enumerate(st.session_state['api_data']):
            try:
                nome_m = f"{m['home_team']}-{m['away_team']}"
                dt_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
                
                # Check Window Ore
                dt_obj = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
                if dt_obj > datetime.utcnow() + timedelta(hours=ore_limite): continue

                opts = []
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_EURO_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == 'totals'), None)
                        if mk:
                            for o in mk['outcomes']:
                                if o.get('point') == 2.5:
                                    q = o['price']
                                    val = ((1/q + 0.06) * q) - 1
                                    opts.append({"T": f"{o['name'].upper()} 2.5", "Q": q, "V": val, "BK": b['title']})
                
                if opts:
                    best = max(opts, key=lambda x: x['V'])
                    if best['V'] >= soglia_val:
                        matches_visualizzati += 1
                        stk = round(max(2.0, min(budget_cassa * (best['V']/(best['Q']-1)) * rischio, budget_cassa*0.15)), 2)
                        c_a, c_b = st.columns([3, 1])
                        c_a.markdown(f"📅 {dt_m} | **{nome_m}**<br>🎯 **{best['T']}** @{best['Q']} (Val: {round(best['V']*100,1)}%) | 🏦 {best['BK']}", unsafe_allow_html=True)
                        if nome_m in pend_list:
                            c_b.button("✅", key=f"add_{i}", disabled=True, use_container_width=True)
                        elif c_b.button("ADD", key=f"add_{i}", use_container_width=True):
                            nuova = pd.DataFrame([{"Data Match": dt_m, "Match": nome_m, "Scelta": best['T'], "Quota": best['Q'], "Stake": stk, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": m['sport_key'], "Risultato": "-"}])
                            salva_db(pd.concat([df_attuale, nuova], ignore_index=True)); st.rerun()
                        st.divider()
            except Exception as e:
                if debug_mode: st.error(f"Errore parsing match {i}: {e}")

        if matches_visualizzati == 0:
            st.warning("Nessun match trovato con i filtri attuali. Prova a ridurre 'Filtro Valore Min %' o aumentare la 'Window Ore'.")

# --- TAB 2: PORTAFOGLIO ---
with t2:
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"]
    
    if st.button("🤖 AUTO-CHECK RISULTATI", use_container_width=True, type="primary"):
        with st.spinner("Controllando esiti..."):
            for idx, row in df_p.iterrows():
                res = requests.get(f"https://api.the-odds-api.com/v4/sports/{row['Sport_Key']}/scores/", params={'api_key': API_KEY, 'daysFrom': 3})
                if res.status_code == 200:
                    aggiorna_api_stats(res.headers)
                    match_data = next((s for s in res.json() if s['home_team'] in row['Match'] and s['completed']), None)
                    if match_data:
                        h = int(match_data['scores'][0]['score'])
                        a = int(match_data['scores'][1]['score'])
                        vinto = (row['Scelta'] == "OVER 2.5" and (h+a) > 2.5) or (row['Scelta'] == "UNDER 2.5" and (h+a) < 2.5)
                        chiudi_manualmente(idx, "VINTO" if vinto else "PERSO", f"{h}-{a}")
        st.rerun()

    for i, r in df_p.iterrows():
        with st.expander(f"{r['Match']} | @{r['Quota']} | {r['Stake']}€"):
            b1, b2, b3 = st.columns(3)
            if b1.button("VINTO ✅", key=f"w_{i}", use_container_width=True): chiudi_manualmente(i, "VINTO", "MAN")
            if b2.button("PERSO ❌", key=f"l_{i}", use_container_width=True): chiudi_manualmente(i, "PERSO", "MAN")
            if b3.button("ELIMINA 🗑️", key=f"d_{i}", use_container_width=True): salva_db(df_attuale.drop(i)); st.rerun()

# --- TAB 3: FISCALE ---
with t3:
    if not df_attuale.empty:
        prof = round(df_attuale['Profitto'].sum(), 2)
        st.metric("📈 Profitto Netto", f"{prof} €")
        st.progress(min(1.0, max(0.0, prof / OBIETTIVO_TARGET)) if prof > 0 else 0.0)
        st.dataframe(df_attuale.sort_index(ascending=False), use_container_width=True)
