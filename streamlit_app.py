import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V15.1.12 - PORTAFOGLIO STAKE", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. COSTANTI GLOBALI ---
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
                st.session_state['api_usage']['used'] = r.headers.get('x-requests-used', "0")
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
        df.at[idx, 'Esito'] = esito
        df.at[idx, 'Risultato'] = risultato_score
        df.at[idx, 'Profitto'] = round((s * q) - s, 2) if esito == "VINTO" else -s
        salva_db(df)
        st.rerun()

# --- 4. INTERFACCIA ---
st.title("🎯 AI SNIPER V15.1.12")
df_attuale = carica_db()

with st.sidebar:
    st.header("📊 Parametri")
    budget_cassa = st.number_input("Budget Attuale (€)", value=BUDGET_DISPONIBILE)
    rischio_kelly = st.slider("Aggressività Kelly", 0.05, 0.50, 0.15)
    soglia_valore = st.slider("Min Value %", 0, 15, 3) / 100

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER ---
with t1:
    pend_list = df_attuale[df_attuale['Esito'] == "Pendente"]['Match'].tolist()
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    c_sel, c_btn, c_ore = st.columns([2, 1, 1])
    sel_name = c_sel.selectbox("Campionato:", list(leagues.keys()))
    ore_limite = c_ore.selectbox("Fino a (Ore):", [24, 48, 72, 96, 120], index=2)
    
    if c_btn.button("🎯 AVVIA SCANNER", use_container_width=True):
        sport_key = leagues[sel_name]
        data = chiamata_sicura_api(f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds/', {'regions': 'eu', 'markets': 'totals'})
        if data: st.session_state['api_data'] = data
        st.rerun()

    if st.session_state['api_data']:
        st.markdown("---")
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
                                    if val >= soglia_valore:
                                        opts.append({"T": o['name'].upper(), "Q": q, "V": val, "BK": b['title']})
                if opts:
                    best = max(opts, key=lambda x: x['V'])
                    stk = round(max(2.0, min(budget_cassa * (best['V']/(best['Q']-1)) * rischio_kelly, budget_cassa*0.15)), 2)
                    col1, col2, col3, col4, col5 = st.columns([3.5, 1.2, 1.5, 1.2, 0.6])
                    with col1: st.markdown(f"📅 {dt_m.strftime('%d/%m %H:%M')} | **{nome_m}**")
                    with col2: st.markdown(f"🎯 {best['T']} 2.5 | **@{best['Q']}**")
                    with col3: st.markdown(f"🏦 {best['BK']} | Val: **{round(best['V']*100,1)}%**")
                    with col4: st.markdown(f"💰 **STAKE: {stk}€**")
                    with col5:
                        if nome_m in pend_list: st.button("✅", key=f"add_{i}", disabled=True)
                        elif st.button("ADD", key=f"add_{i}"):
                            nuova = pd.DataFrame([{"Data Match": dt_m.strftime('%d/%m %H:%M'), "Match": nome_m, "Scelta": f"{best['T']} 2.5", "Quota": best['Q'], "Stake": stk, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": m['sport_key'], "Risultato": "-"}])
                            salva_db(pd.concat([df_attuale, nuova], ignore_index=True)); st.rerun()
                    st.divider()
            except: continue

# --- TAB 2: PORTAFOGLIO (STAKE VISIBILE) ---
with t2:
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"].copy()
    if not df_p.empty:
        for i, r in df_p.iterrows():
            # Recupero nome campionato
            camp = LEAGUE_NAMES.get(r['Sport_Key'], r['Sport_Key'])
            
            # MODIFICA: Titolo Expander con l'informazione dello STAKE proposto
            label_p = f"📅 {r['Data Match']} | {r['Match']} | {camp} | 🏦 {r['Bookmaker']} | 💰 STAKE: {r['Stake']}€"
            
            with st.expander(label_p):
                st.write(f"🎯 **Scommessa:** {r['Scelta']} @{r['Quota']} | **Vincita Potenziale:** {round(float(r['Stake']) * float(r['Quota']), 2)}€")
                b1, b2, b3 = st.columns(3)
                if b1.button("VINTO ✅", key=f"w_{i}"): chiudi_gara(i, "VINTO", "MAN")
                if b2.button("PERSO ❌", key=f"l_{i}"): chiudi_gara(i, "PERSO", "MAN")
                if b3.button("ELIMINA 🗑️", key=f"d_{i}"): salva_db(df_attuale.drop(i)); st.rerun()
    else:
        st.info("Nessuna giocata pendente nel portafoglio.")

# --- TAB 3: FISCALE ---
with t3:
    if not df_attuale.empty:
        df_stats = df_attuale.copy()
        df_stats[['Stake', 'Profitto']] = df_stats[['Stake', 'Profitto']].apply(pd.to_numeric, errors='coerce').fillna(0)
        df_chiuse = df_stats[df_stats['Esito'].isin(["VINTO", "PERSO"])]
        
        p_netto = round(df_chiuse['Profitto'].sum(), 2)
        v_scommesso = round(df_chiuse['Stake'].sum(), 2)
        v_vinte = df_chiuse[df_chiuse['Esito'] == "VINTO"]
        vinc_lorda = round(v_vinte['Stake'].sum() + v_vinte['Profitto'].sum(), 2)

        st.subheader("📊 Analisi Fiscale")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Profitto Netto", f"{p_netto} €")
        m2.metric("Volume Scommesso", f"{v_scommesso} €")
        m3.metric("Goal Target", f"{OBIETTIVO_TARGET} €") 
        m4.metric("Incasso Lordo", f"{vinc_lorda} €")
        
        st.divider()
        st.subheader("💾 Backup")
        st.download_button("📥 Scarica Backup CSV", data=df_attuale.to_csv(index=False).encode('utf-8'), file_name="backup_sniper.csv", use_container_width=True)
