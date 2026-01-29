import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI & CSS ---
st.set_page_config(page_title="AI SNIPER V13.8 - FULL DESIGN", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    
    /* Card Scanner */
    .match-card {
        background-color: #161b22;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 12px;
        border: 1px solid #30363d;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* KPI Metrics Fiscale */
    .metric-container {
        display: flex;
        gap: 10px;
        margin-bottom: 20px;
    }
    .metric-box {
        flex: 1;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        font-weight: bold;
    }
    .bg-blue { background-color: rgba(33, 150, 243, 0.2); border: 1px solid #2196f3; }
    .bg-green { background-color: rgba(76, 175, 80, 0.2); border: 1px solid #4caf50; }
    .bg-red { background-color: rgba(244, 67, 54, 0.2); border: 1px solid #f44336; }
    .bg-orange { background-color: rgba(255, 152, 0, 0.2); border: 1px solid #ff9800; }
    
    /* Box Riepilogo Portafoglio */
    .summary-box {
        background-color: #161b22;
        padding: 20px;
        border-radius: 12px;
        border: 2px solid #30363d;
        text-align: center;
        margin-bottom: 25px;
    }
    
    .main-header { font-size: 28px; font-weight: 800; letter-spacing: -1px; margin-bottom: 25px; }
    section[data-testid="stSidebar"] { background-color: #0d1117; }
    </style>
""", unsafe_allow_html=True)

# --- MOTORE DATABASE ---
conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

if 'api_usage' not in st.session_state:
    st.session_state['api_usage'] = {'remaining': "N/D", 'used': "N/D"}
if 'api_data' not in st.session_state:
    st.session_state['api_data'] = []

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "William Hill", "888sport"]

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", 
    "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", 
    "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie",
    "soccer_spain_la_liga": "🇪🇸 La Liga", 
    "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_france_ligue_1": "🇫🇷 Ligue 1",
    "soccer_uefa_europa_league": "🇪🇺 Europa League",
    "soccer_uefa_champions_league": "🏆 Champions"
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

def check_results():
    df = carica_db()
    pendenti = df[df['Esito'] == "Pendente"]
    if pendenti.empty:
        st.info("Nessuna scommessa pendente.")
        return
    cambiamenti = False
    with st.spinner("🔄 Verifica risultati..."):
        for skey in pendenti['Sport_Key'].unique():
            res = requests.get(f'https://api.the-odds-api.com/v4/sports/{skey}/scores/', params={'api_key': API_KEY, 'daysFrom': 3})
            if res.status_code == 200:
                scores = res.json()
                for i, r in pendenti[pendenti['Sport_Key'] == skey].iterrows():
                    m_res = next((m for m in scores if f"{m['home_team']}-{m['away_team']}" == r['Match'] and m.get('completed')), None)
                    if m_res:
                        s = m_res['scores']
                        if s:
                            s1, s2 = int(s[0]['score']), int(s[1]['score'])
                            vinto = (s1 + s2) > 2.5 if r['Scelta'] == "OVER 2.5" else (s1 + s2) < 2.5
                            df.at[i, 'Esito'] = "VINTO" if vinto else "PERSO"
                            df.at[i, 'Risultato'] = f"{s1}-{s2}"
                            df.at[i, 'Profitto'] = round((r['Stake'] * r['Quota']) - r['Stake'], 2) if vinto else -r['Stake']
                            cambiamenti = True
    if cambiamenti:
        salva_db(df)
        st.rerun()

# --- INTERFACCIA ---
st.markdown('<div class="main-header">🎯 AI SNIPER <span style="font-size:14px; color:#58a6ff;">V13.8 DESIGN</span></div>', unsafe_allow_html=True)
df_attuale = carica_db()

with st.sidebar:
    st.markdown("### 📊 API Status")
    c1, c2 = st.columns(2)
    c1.metric("Residui", st.session_state['api_usage']['remaining'])
    c2.metric("Usati", st.session_state['api_usage']['used'])
    st.divider()
    budget_cassa = st.number_input("Budget (€)", value=500.0)
    rischio = st.slider("Kelly %", 0.05, 0.50, 0.20)
    soglia_val = st.slider("Valore Min %", 0, 15, 3) / 100

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER ---
with t1:
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    c_sel, c_btns, c_ore = st.columns([1.5, 1, 1])
    sel_name = c_sel.selectbox("Campionato Singolo:", list(leagues.keys()))
    ore_limite = c_ore.selectbox("Finestra Ore:", [24, 48, 72, 96, 120], index=2)
    
    col_t, col_s = c_btns.columns(2)
    if col_t.button("🚀 TOTALE", use_container_width=True):
        all_found = []
        keys_to_scan = list(LEAGUE_NAMES.keys())
        pbar = st.progress(0)
        limit_date = datetime.utcnow() + timedelta(hours=ore_limite)
        for idx, k in enumerate(set(keys_to_scan)):
            r = requests.get(f'https://api.the-odds-api.com/v4/sports/{k}/odds/', params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
            if r.status_code == 200:
                data = r.json()
                filtered = [m for m in data if datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ") <= limit_date]
                all_found.extend(filtered)
                st.session_state['api_usage']['remaining'] = r.headers.get('x-requests-remaining')
            time.sleep(0.4)
            pbar.progress((idx+1)/len(set(keys_to_scan)))
        st.session_state['api_data'] = all_found
        st.rerun()

    if col_s.button("🔍 SINGOLA", use_container_width=True):
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_name]}/odds/', params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
        if res.status_code == 200:
            st.session_state['api_data'] = res.json()
            st.session_state['api_usage']['remaining'] = res.headers.get('x-requests-remaining')
            st.rerun()

    if st.session_state['api_data']:
        pend_list = df_attuale[df_attuale['Esito'] == "Pendente"]['Match'].tolist()
        for i, m in enumerate(st.session_state['api_data']):
            try:
                nome_m = f"{m['home_team']}-{m['away_team']}"
                dt_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
                opts = []
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_EURO_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == 'totals'), None)
                        if mk:
                            q_ov = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and float(o.get('point',0)) == 2.5), None)
                            q_un = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and float(o.get('point',0)) == 2.5), None)
                            if q_ov: opts.append({"T": "OVER 2.5", "Q": q_ov, "P": (1/q_ov)+0.06, "BK": b['title']})
                            if q_un: opts.append({"T": "UNDER 2.5", "Q": q_un, "P": (1/q_un)+0.06, "BK": b['title']})
                
                if opts:
                    best = max(opts, key=lambda x: (x['P'] * x['Q']) - 1)
                    val = (best['P'] * best['Q']) - 1
                    if val >= soglia_val:
                        stk_c = round(max(2.0, min(budget_cassa * (val/(best['Q']-1)) * rischio, budget_cassa*0.15)), 2)
                        st.markdown(f"""
                            <div class="match-card">
                                <div style="display: flex; justify-content: space-between;">
                                    <span>📅 {dt_m} | <b>{nome_m}</b></span>
                                    <span style="color: #8b949e;">{m['sport_title']}</span>
                                </div>
                                <div style="margin-top: 10px; color: #58a6ff; font-size: 18px;">Giocata: <b>{best['T']}</b> @{best['Q']}</div>
                                <div style="font-size: 13px; color: #8b949e;">Stake: <span style="color: #ffc107;">{stk_c}€</span> | Valore: <span style="color: #39d353;">{round(val*100,1)}%</span> | 🏦 {best['BK']}</div>
                            </div>
                        """, unsafe_allow_html=True)
                        if nome_m in pend_list:
                            st.button("✅ IN PORTAFOGLIO", key=f"btn_{i}", disabled=True, use_container_width=True)
                        elif st.button(f"AGGIUNGI {nome_m}", key=f"btn_{i}", use_container_width=True):
                            nuova = pd.DataFrame([{"Data Match": dt_m, "Match": nome_m, "Scelta": best['T'], "Quota": best['Q'], "Stake": stk_c, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": m['sport_key'], "Risultato": "-"}])
                            salva_db(pd.concat([carica_db(), nuova], ignore_index=True))
                            st.rerun()
            except: continue

# --- TAB 2: PORTAFOGLIO ---
with t2:
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"]
    if not df_p.empty:
        tot_impegnato = round(df_p['Stake'].sum(), 2)
        ritorno_potenziale = round((df_p['Stake'] * df_p['Quota']).sum(), 2)
        st.markdown(f"""<div class="summary-box"><div style="display: flex; justify-content: space-around;">
            <div><div style="color: white; font-size: 14px; opacity: 0.8;">TOTALE IMPEGNATO</div><div style="color: #ffc107; font-size: 32px; font-weight: bold;">{tot_impegnato} €</div></div>
            <div><div style="color: white; font-size: 14px; opacity: 0.8;">RITORNO POTENZIALE</div><div style="color: #39d353; font-size: 32px; font-weight: bold;">{ritorno_potenziale} €</div></div>
        </div></div>""", unsafe_allow_html=True)
        st.button("🔄 AGGIORNA RISULTATI", on_click=check_results, key="upd_res", use_container_width=True)
        for i, r in df_p.iterrows():
            st.markdown(f"<div class='match-card'><b>{r['Match']}</b> | {r['Scelta']} @{r['Quota']} | Stake: {r['Stake']}€</div>", unsafe_allow_html=True)
            if st.button(f"Rimuovi {r['Match']}", key=f"del_{i}"):
                salva_db(df_attuale.drop(i))
                st.rerun()
    else: st.info("Nessuna giocata pendente.")

# --- TAB 3: FISCALE ---
with t3:
    if not df_attuale.empty:
        tot_giocato = round(df_attuale['Stake'].sum(), 2)
        tot_vinto = round(df_attuale[df_attuale['Esito'] == "VINTO"]['Profitto'].sum() + df_attuale[df_attuale['Esito'] == "VINTO"]['Stake'].sum(), 2)
        tot_perso = round(df_attuale[df_attuale['Esito'] == "PERSO"]['Stake'].sum(), 2)
        prof_netto = round(df_attuale['Profitto'].sum(), 2)
        st.markdown(f"""<div class="metric-container">
            <div class="metric-box bg-blue">💰 GIOCATO<br><span style="font-size:20px;">{tot_giocato}€</span></div>
            <div class="metric-box bg-green">✅ VINTO<br><span style="font-size:20px;">{tot_vinto}€</span></div>
            <div class="metric-box bg-red">❌ PERSO<br><span style="font-size:20px;">{tot_perso}€</span></div>
            <div class="metric-box bg-orange">📈 NETTO<br><span style="font-size:20px;">{prof_netto}€</span></div>
        </div>""", unsafe_allow_html=True)
        st.dataframe(df_attuale[["Data Match", "Match", "Scelta", "Quota", "Stake", "Esito", "Profitto"]].sort_index(ascending=False), use_container_width=True)
