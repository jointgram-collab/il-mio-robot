import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V14.8 - PRO PORTFOLIO", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- GESTIONE DOPPIA CHIAVE ---
API_KEYS = [
    '01f1c8f2a314814b17de03eeb6c53623', 
    '55f08c25f38fa1006dd9e66282170e1a' 
]

# Parametri Utente (500€ Budget -> 5000€ Target)
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

# --- FUNZIONI CORE API ---
def chiamata_sicura_api(endpoint, params_extra={}):
    idx = st.session_state['api_usage'].get('active_index', 0)
    for _ in range(len(API_KEYS)):
        current_key = API_KEYS[idx]
        params = {'api_key': current_key, 'regions': 'eu', 'markets': 'totals'}
        params.update(params_extra)
        try:
            r = requests.get(endpoint, params=params)
            if r.status_code in [401, 429]:
                idx = (idx + 1) % len(API_KEYS)
                st.session_state['api_usage']['active_index'] = idx
                continue
            if r.status_code == 200:
                st.session_state['api_usage']['remaining'] = r.headers.get('x-requests-remaining', "0")
                st.session_state['api_usage']['used'] = r.headers.get('x-requests-used', "0")
                return r.json()
        except:
            idx = (idx + 1) % len(API_KEYS)
            st.session_state['api_usage']['active_index'] = idx
    return None

# --- FUNZIONI DATABASE ---
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

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V14.8")
df_attuale = carica_db()

with st.sidebar:
    st.header("📊 Stato API")
    st.info(f"Slot Attivo: {st.session_state['api_usage']['active_index'] + 1}")
    c1, c2 = st.columns(2)
    c1.metric("Residui", st.session_state['api_usage']['remaining'])
    c2.metric("Usati", st.session_state['api_usage']['used'])
    st.divider()
    budget_cassa = st.number_input("Cassa Operativa (€)", value=BUDGET_DISPONIBILE)
    rischio = st.slider("Kelly %", 0.05, 0.50, 0.15)
    soglia_val = st.slider("Valore Min %", 0, 15, 3) / 100

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
            except: continue

# --- TAB 2: PORTAFOGLIO (RIGA AGGIORNATA) ---
with t2:
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"]
    
    if st.button("🤖 AUTO-CHECK RISULTATI", use_container_width=True, type="primary"):
        with st.spinner("Sincronizzazione risultati..."):
            for idx, row in df_p.iterrows():
                data = chiamata_sicura_api(f"https://api.the-odds-api.com/v4/sports/{row['Sport_Key']}/scores/", {'daysFrom': 3})
                if data:
                    m_res = next((s for s in data if s['home_team'] in row['Match'] and s['completed']), None)
                    if m_res:
                        h, a = m_res['scores'][0]['score'], m_res['scores'][1]['score']
                        vinto = (row['Scelta'] == "OVER 2.5" and (int(h)+int(a)) > 2.5) or (row['Scelta'] == "UNDER 2.5" and (int(h)+int(a)) < 2.5)
                        chiudi_gara(idx, "VINTO" if vinto else "PERSO", f"{h}-{a}")
        st.rerun()
    
    if not df_p.empty:
        for i, r in df_p.iterrows():
            vincita_pot = round(float(r['Stake']) * float(r['Quota']), 2)
            camp_icon = LEAGUE_NAMES.get(r['Sport_Key'], "⚽")
            
            # --- RIGA PRINCIPALE OTTIMIZZATA ---
            label_main = f"{r['Data Match']} | {r['Match']} | {r['Scelta']} | 🏦 {r['Bookmaker']} | {camp_icon} | 💰 {vincita_pot}€"
            
            with st.expander(label_main):
                st.markdown(f"**Gestione Scommessa**")
                c_inf1, c_inf2 = st.columns(2)
                c_inf1.write(f"📈 Quota Giocata: **@{r['Quota']}**")
                c_inf1.write(f"💸 Stake Investito: **{r['Stake']}€**")
                c_inf2.write(f"📍 Campionato ID: `{r['Sport_Key']}`")
                
                st.divider()
                b1, b2, b3 = st.columns(3)
                if b1.button("VINTO ✅", key=f"w_{i}", use_container_width=True): chiudi_gara(i, "VINTO", "MAN")
                if b2.button("PERSO ❌", key=f"l_{i}", use_container_width=True): chiudi_gara(i, "PERSO", "MAN")
                if b3.button("ELIMINA 🗑️", key=f"d_{i}", use_container_width=True): salva_db(df_attuale.drop(i)); st.rerun()
    else:
        st.info("Nessuna scommessa pendente.")

# --- TAB 3: FISCALE ---
with t3:
    if not df_attuale.empty:
        df_vis = df_attuale.copy()
        profitto_netto = round(df_vis['Profitto'].sum(), 2)
        v_chiusi = len(df_vis[df_vis['Esito'] != "Pendente"])
        win_rate = round((len(df_vis[df_vis['Esito']=="VINTO"]) / v_chiusi * 100), 1) if v_chiusi > 0 else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("📈 Profitto Netto", f"{profitto_netto} €")
        m2.metric("🎯 Win Rate", f"{win_rate} %")
        m3.metric("🏁 Goal", f"{OBIETTIVO_TARGET} €")
        
        st.progress(min(1.0, max(0.0, profitto_netto / OBIETTIVO_TARGET)) if profitto_netto > 0 else 0.0)
        st.caption(f"Progresso Scalata: {int((profitto_netto/OBIETTIVO_TARGET)*100)}% verso il target di 5000€")
        
        st.divider()
        st.dataframe(df_vis.sort_index(ascending=False), use_container_width=True)
        
        st.download_button("📥 BACKUP CSV", data=df_attuale.to_csv(index=False).encode('utf-8'), file_name=f"sniper_v14_8_{date.today()}.csv", use_container_width=True)
