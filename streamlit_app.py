import streamlit as st
import pandas as pd
import requests
import io
import time
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V15.1.13 - FULL", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. COSTANTI E STATO ---
API_KEYS = ['01f1c8f2a314814b17de03eeb6c53623', '55f08c25f38fa1006dd9e66282170e1a']
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

MARKET_MAP = {
    "Under/Over 2.5": "totals",
    "Esito Finale (1X2)": "h2h",
    "Goal/No Goal": "both_teams_to_score"
}

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "William Hill", "888sport"]

# --- 3. FUNZIONI CORE ---
def chiamata_sicura_api(endpoint, params_extra={}):
    idx = st.session_state['api_usage'].get('active_index', 0)
    for _ in range(len(API_KEYS)):
        current_key = API_KEYS[idx]
        params = {'api_key': current_key}
        params.update(params_extra)
        try:
            r = requests.get(endpoint, params=params)
            if r.status_code == 200:
                st.session_state['api_usage']['remaining'] = r.headers.get('x-requests-remaining', "0")
                return r.json()
            idx = (idx + 1) % len(API_KEYS)
            st.session_state['api_usage']['active_index'] = idx
        except:
            idx = (idx + 1) % len(API_KEYS)
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

def check_risultati_automatico():
    df = carica_db()
    pendenti = df[df['Esito'] == "Pendente"]
    if pendenti.empty:
        st.toast("Nessun match pendente.")
        return
    keys_da_controllare = pendenti['Sport_Key'].unique()
    aggiornati = False
    for skey in keys_da_controllare:
        res = chiamata_sicura_api(f'https://api.the-odds-api.com/v4/sports/{skey}/scores/', {'daysFrom': 3})
        if res:
            for m_api in res:
                if not m_api['completed']: continue
                nome_api = f"{m_api['home_team']}-{m_api['away_team']}"
                for idx, r_db in pendenti[pendenti['Match'] == nome_api].iterrows():
                    score = m_api['scores']
                    if score:
                        # Logica semplificata esito (va rifinita per 1X2 e GG/NG se necessario)
                        df.at[idx, 'Risultato'] = f"{score[0]['score']}-{score[1]['score']}"
                        aggiornati = True
    if aggiornati:
        salva_db(df); st.success("Risultati scaricati. Chiudi manualmente per sicurezza."); st.rerun()

def chiudi_gara(idx, esito, risultato_score="-"):
    df = carica_db()
    if idx in df.index:
        q, s = float(df.at[idx, 'Quota']), float(df.at[idx, 'Stake'])
        df.at[idx, 'Esito'], df.at[idx, 'Risultato'] = esito, risultato_score
        df.at[idx, 'Profitto'] = round((s * q) - s, 2) if esito == "VINTO" else -s
        salva_db(df); st.rerun()

# --- 4. INTERFACCIA ---
st.title("🎯 AI SNIPER V15.1.13")
df_attuale = carica_db()

with st.sidebar:
    st.header("📊 Parametri")
    budget_cassa = st.number_input("Budget Attuale (€)", value=BUDGET_DISPONIBILE)
    rischio_kelly = st.slider("Aggressività Kelly", 0.05, 0.50, 0.15)
    soglia_valore = st.slider("Min Value %", 0, 15, 3) / 100
    st.info(f"API Residue: {st.session_state['api_usage']['remaining']}")

tab1, tab2, tab3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE & BACKUP"])

# --- TAB 1: SCANNER MULTI-MERCATO ---
# --- TAB 1: SCANNER MULTI-MERCATO (SOSTITUISCI DA QUI) ---
with tab1:
    c_a, c_b, c_m, c_o = st.columns([1.5, 1, 1.5, 0.8])
    leagues_map = {v: k for k, v in LEAGUE_NAMES.items()}
    sel_league = c_a.selectbox("Campionato:", ["TUTTI"] + list(leagues_map.keys()))
    sel_market = c_m.selectbox("Mercato:", list(MARKET_MAP.keys()))
    ore_max = c_o.selectbox("Ore:", [24, 48, 72, 96, 120], index=1)
    
    if c_b.button("🎯 AVVIA SCAN", use_container_width=True, type="primary"):
        results = []
        m_key = MARKET_MAP[sel_market]
        if sel_league == "TUTTI":
            bar = st.progress(0)
            leagues_list = list(leagues_map.values())
            for i, l_key in enumerate(leagues_list):
                data = chiamata_sicura_api(f'https://api.the-odds-api.com/v4/sports/{l_key}/odds/', {'regions': 'eu', 'markets': m_key})
                if data: results.extend(data)
                bar.progress((i + 1) / len(leagues_list))
        else:
            data = chiamata_sicura_api(f'https://api.the-odds-api.com/v4/sports/{leagues_map[sel_league]}/odds/', {'regions': 'eu', 'markets': m_key})
            if data: results = data
        st.session_state['api_data'] = results
        st.rerun()

    if st.session_state['api_data']:
        st.divider()
        pend_list = df_attuale[df_attuale['Esito'] == "Pendente"]['Match'].tolist()
        m_key = MARKET_MAP[sel_market]
        
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
                                
                                # LOGICA MARGINE E TRADUZIONE ETICHETTE
                                if m_key == "both_teams_to_score":
                                    margin = 0.05
                                    label = "GOAL (GG)" if o['name'].lower() in ["yes", "both"] else "NO GOAL (NG)"
                                elif m_key == "h2h":
                                    margin = 0.07
                                    label = o['name']
                                else:
                                    margin = 0.06
                                    label = f"{o['name'].upper()} 2.5"
                                
                                val = ((1/q + margin) * q) - 1
                                if val >= soglia_valore:
                                    opts.append({"T": label, "Q": q, "V": val, "BK": b['title']})
                if opts:
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
                        nuova = pd.DataFrame([{"Data Match": dt_m.strftime('%d/%m %H:%M'), "Match": nome_m, "Scelta": best['T'], "Quota": best['Q'], "Stake": stk, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": m['sport_key'], "Risultato": "-"}])
                        salva_db(pd.concat([df_attuale, nuova], ignore_index=True)); st.rerun()
                    st.divider()
            except: continue
# --- FINE TAB 1 (IL CODICE PROSEGUE CON WITH TAB2) ---

# --- TAB 2: PORTAFOGLIO ---
with tab2:
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"].copy()
    m1, m2, m3 = st.columns(3)
    if not df_p.empty:
        df_p['Stake'] = pd.to_numeric(df_p['Stake'], errors='coerce').fillna(0)
        df_p['Quota'] = pd.to_numeric(df_p['Quota'], errors='coerce').fillna(0)
        m1.metric("Stake Impegnato", f"{round(df_p['Stake'].sum(), 2)} €")
        m2.metric("Vincita Potenziale", f"{round((df_p['Stake'] * df_p['Quota']).sum(), 2)} €")
    if m3.button("🔄 AGGIORNA RISULTATI API", use_container_width=True, type="primary"): check_risultati_automatico()
    st.divider()
    for i, r in df_p.iterrows():
        with st.expander(f"📅 {r['Data Match']} | {r['Match']} | 🏦 {r['Bookmaker']} | {r['Stake']}€"):
            st.write(f"🎯 Scelta: **{r['Scelta']}** @{r['Quota']}")
            b1, b2, b3 = st.columns(3)
            if b1.button("VINTO ✅", key=f"w_{i}"): chiudi_gara(i, "VINTO")
            if b2.button("PERSO ❌", key=f"l_{i}"): chiudi_gara(i, "PERSO")
            if b3.button("ELIMINA 🗑️", key=f"d_{i}"): salva_db(df_attuale.drop(i)); st.rerun()

# --- TAB 3: FISCALE & BACKUP ---
with tab3:
    df_chiuse = df_attuale[df_attuale['Esito'].isin(["VINTO", "PERSO"])].copy()
    if not df_chiuse.empty:
        df_chiuse[['Profitto', 'Stake']] = df_chiuse[['Profitto', 'Stake']].apply(pd.to_numeric)
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Profitto Netto", f"{round(df_chiuse['Profitto'].sum(), 2)} €")
        f2.metric("Volume Scommesso", f"{round(df_chiuse['Stake'].sum(), 2)} €")
        f3.metric("Goal Target", f"{OBIETTIVO_TARGET} €")
        f4.metric("Incasso Lordo", f"{round(df_chiuse[df_chiuse['Esito']=='VINTO']['Profitto'].sum() + df_chiuse[df_chiuse['Esito']=='VINTO']['Stake'].sum(), 2)} €")
        
        st.subheader("📜 Storico Giocate")
        for i, r in df_chiuse[::-1].iterrows():
            c, b = ("#d4edda", "#155724") if r['Esito'] == "VINTO" else ("#f8d7da", "#721c24")
            st.markdown(f'<div style="background-color:{c}; border-radius:10px; padding:15px; margin-bottom:10px; border: 1px solid {b}; color:{b};"><b>{r["Esito"]}</b> | {r["Data Match"]} | {r["Match"]} | {r["Scelta"]} @{r["Quota"]} | Profitto: {r["Profitto"]}€ | Ris: {r["Risultato"]}</div>', unsafe_allow_html=True)
    
    st.divider()
    st.subheader("⚙️ Gestione Backup")
    b_col1, b_col2 = st.columns(2)
    b_col1.download_button("📥 SCARICA BACKUP CSV", data=df_attuale.to_csv(index=False).encode('utf-8'), file_name="backup.csv", use_container_width=True)
    up = st.file_uploader("📤 RIPRISTINA DA CSV", type="csv")
    if up and st.button("CONFERMA RIPRISTINO"): salva_db(pd.read_csv(up)); st.rerun()
