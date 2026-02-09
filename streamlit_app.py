import streamlit as st
import pandas as pd
import requests
import io
import time
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V15.1.13 - ULTIMATE", layout="wide")
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
with tab1:
    c_a, c_b, c_m, c_o = st.columns([1.5, 1, 1.5, 0.8])
    leagues_map = {v: k for k, v in LEAGUE_NAMES.items()}
    sel_league = c_a.selectbox("Campionato:", ["TUTTI"] + list(leagues_map.keys()))
    sel_market = c_m.selectbox("Mercato:", list(MARKET_MAP.keys()))
    ore_max = c_o.selectbox("Fino a (Ore):", [24, 48, 72, 96, 120], index=1)
    
    if c_b.button("🚀 AVVIA SCANNER", use_container_width=True, type="primary"):
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
                                
                                # LOGICA MARGINE E TRADUZIONE ETICHETTE (FIX GG/NG)
                                if m_key == "both_teams_to_score":
                                    margin = 0.05 # Più basso per GG/NG
                                    label = "GOAL (GG)" if o['name'].lower() in ["yes", "both"] else "NO GOAL (NG)"
                                elif m_key == "h2h":
                                    margin = 0.07
                                    label = o['name']
                                else: # totals
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

# --- TAB 2: PORTAFOGLIO ---
with tab2:
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"].copy()
    m1, m2, m3 = st.columns(3)
    if not df_p.empty:
        df_p['Stake'] = pd.to_numeric(df_p['Stake'], errors='coerce').fillna(0)
        df_p['Quota'] = pd.to_numeric(df_p['Quota'], errors='coerce').fillna(0)
        m1.metric("Stake Impegnato", f"{round(df_p['Stake'].sum(), 2)} €")
        m2.metric("Vincita Potenziale", f"{round((df_p['Stake'] * df_p['Quota']).sum(), 2)} €")
    if m3.button("🔄 CONTROLLA RISULTATI (API)", use_container_width=True):
        st.toast("Interrogazione risultati...")
        # Nota: La chiusura automatica richiede logica specifica per 1X2 e GG/NG
        # Per sicurezza, in questa versione usiamo la chiusura manuale.
    st.divider()
    for i, r in df_p.iterrows():
        with st.expander(f"📅 {r['Data Match']} | {r['Match']} | 🏦 {r['Bookmaker']} | {r['Stake']}€"):
            b1, b2, b3 = st.columns(3)
            if b1.button("VINTO ✅", key=f"w_{i}"): chiudi_gara(i, "VINTO")
            if b2.button("PERSO ❌", key=f"l_{i}"): chiudi_gara(i, "PERSO")
            if b3.button("ELIMINA 🗑️", key=f"d_{i}"): salva_db(df_attuale.drop(i)); st.rerun()

# --- TAB 3: FISCALE & BACKUP ---
with tab3:
    df_chiuse = df_attuale[df_attuale['Esito'].isin(["VINTO", "PERSO"])].copy()
    if not df_chiuse.empty:
        df_chiuse[['Profitto', 'Stake']] = df_chiuse[['Profitto', 'Stake']].apply(pd.to_numeric)
        f1, f2, f3 = st.columns(3)
        f1.metric("Profitto Netto", f"{round(df_chiuse['Profitto'].sum(), 2)} €")
        f2.metric("Volume Scommesso", f"{round(df_chiuse['Stake'].sum(), 2)} €")
        f3.metric("Goal Target", f"{OBIETTIVO_TARGET} €")
        for i, r in df_chiuse[::-1].iterrows():
            c, b = ("#d4edda", "#155724") if r['Esito'] == "VINTO" else ("#f8d7da", "#721c24")
            st.markdown(f'<div style="background-color:{c}; border-radius:10px; padding:15px; margin-bottom:10px; border: 1px solid {b}; color:{b};"><b>{r["Esito"]}</b> | {r["Match"]} | {r["Scelta"]} @{r["Quota"]} | {r["Profitto"]}€</div>', unsafe_allow_html=True)
    st.divider()
    st.download_button("📥 BACKUP CSV", data=df_attuale.to_csv(index=False).encode('utf-8'), file_name="backup.csv", use_container_width=True)
    up = st.file_uploader("📤 RIPRISTINA")
    if up and st.button("CONFERMA"): salva_db(pd.read_csv(up)); st.rerun()
