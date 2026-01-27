import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V11.85 - Total European Radar", layout="wide")

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
    "soccer_uefa_champions_league": "🇪🇺 Champions League",
    "soccer_uefa_europa_league": "🇪🇺 Europa League",
    "soccer_uefa_europa_conference_league": "🇪🇺 Conference League"
}

# --- MOTORE DATABASE ---
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
    if pendenti.empty: return
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
st.title("🎯 AI SNIPER V11.85")
df_attuale = carica_db()

with st.sidebar:
    st.header("📊 Stato API")
    c1, c2 = st.columns(2)
    c1.metric("Residui", st.session_state['api_usage']['remaining'])
    c2.metric("Usati", st.session_state['api_usage']['used'])
    st.divider()
    budget_cassa = st.number_input("Budget (€)", value=500.0)
    rischio = st.slider("Kelly", 0.05, 0.50, 0.20)
    soglia_val = st.slider("Valore Min %", 0, 15, 5) / 100

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER ---
with t1:
    c_sel, c_btn_all, c_slider = st.columns([1, 1, 1])
    
    leagues_map = {v: k for k, v in LEAGUE_NAMES.items()}
    sel_name = c_sel.selectbox("Campionato Singolo:", list(leagues_map.keys()))
    ore_ricerca = c_slider.select_slider("Finestra (ore):", options=[24, 48, 72, 96, 120], value=120)
    
    if c_btn_all.button("🚀 SCANSIONE TOTALE (EU)", use_container_width=True):
        all_found = []
        progress = st.progress(0)
        status = st.empty()
        
        for idx, (l_key, l_name) in enumerate(LEAGUE_NAMES.items()):
            status.text(f"Scansione: {l_name}...")
            try:
                r = requests.get(f'https://api.the-odds-api.com/v4/sports/{l_key}/odds/', 
                               params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'}, timeout=15)
                if r.status_code == 200:
                    all_found.extend(r.json())
                    st.session_state['api_usage']['remaining'] = r.headers.get('x-requests-remaining')
                time.sleep(0.5) 
            except:
                st.error(f"Errore su {l_name}")
            progress.progress((idx + 1) / len(LEAGUE_NAMES))
        
        st.session_state['api_data'] = all_found
        status.success(f"Analisi completata: {len(all_found)} match in memoria.")
        st.rerun()

    if c_sel.button("🔍 Scansiona Singolo", use_container_width=True):
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{leagues_map[sel_name]}/odds/', 
                           params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
        if res.status_code == 200:
            st.session_state['api_data'] = res.json()
            st.rerun()

    st.divider()

    if st.session_state['api_data']:
        now = datetime.utcnow()
        limit = now + timedelta(hours=ore_ricerca)
        pend_list = df_attuale[df_attuale['Esito'] == "Pendente"]['Match'].tolist()
        found_valore = False
        
        for i, m in enumerate(st.session_state['api_data']):
            try:
                m_time = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
                if not (now <= m_time <= limit): continue
                
                nome_m = f"{m['home_team']}-{m['away_team']}"
                dt_m = m_time.strftime("%d/%m %H:%M")
                sport_key = m['sport_key']
                
                opts = []
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_EURO_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == 'totals'), None)
                        if mk:
                            q_ov = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), None)
                            q_un = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), None)
                            if q_ov and q_un:
                                margin = (1/q_ov) + (1/q_un)
                                opts.append({"T": "OVER 2.5", "Q": q_ov, "P": ((1/q_ov)/margin)+0.06, "BK": b['title']})
                
                if opts:
                    best = max(opts, key=lambda x: (x['P'] * x['Q']) - 1)
                    val = (best['P'] * best['Q']) - 1
                    
                    if val >= soglia_val:
                        found_valore = True
                        stk_c = round(max(2.0, min(budget_cassa * (val/(best['Q']-1)) * rischio, budget_cassa*0.15)), 2)
                        c_info, c_add = st.columns([3, 1])
                        
                        camp_label = LEAGUE_NAMES.get(sport_key, "🏆 Cup/Other")
                        is_p = " ✅" if nome_m in pend_list else ""
                        
                        c_info.markdown(f"📅 {dt_m} | **{nome_m}** <br>🏆 <small>{camp_label}</small> | **{best['BK']}** | Val: **{round(val*100,1)}%**{is_p}", unsafe_allow_html=True)
                        if c_add.button(f"ADD @{best['Q']}", key=f"add_{nome_m}_{i}", disabled=(nome_m in pend_list)):
                            nuova = pd.DataFrame([{"Data Match": dt_m, "Match": nome_m, "Scelta": best['T'], "Quota": best['Q'], "Stake": stk_c, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": sport_key, "Risultato": "-"}])
                            salva_db(pd.concat([carica_db(), nuova], ignore_index=True))
                            st.rerun()
                        st.divider()
            except: continue
        
        if not found_valore: st.warning("Nessun match di valore trovato con questi filtri.")

# --- TAB 2: PORTAFOGLIO ---
with t2:
    st.button("🔄 AGGIORNA RISULTATI", on_click=check_results, key="btn_check_port")
    st.divider()
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"]
    if not df_p.empty:
        for i, r in df_p.iterrows():
            vinc_p = round(r['Stake'] * r['Quota'], 2)
            camp = LEAGUE_NAMES.get(r['Sport_Key'], r['Sport_Key'])
            c_p1, c_p2 = st.columns([15, 1])
            with c_p1:
                st.markdown(f"🟡 **{r['Match']}** <small>({camp})</small> | {r['Scelta']} @**{r['Quota']}** | Stake: **{r['Stake']}€** | Vincita: **{vinc_p}€**", unsafe_allow_html=True)
            with c_p2:
                if st.button("🗑️", key=f"del_p_{i}"):
                    salva_db(df_attuale.drop(i))
                    st.rerun()
            st.markdown("<hr style='margin:2px 0px; border:0.1px solid #f0f2f6'>", unsafe_allow_html=True)
    else: st.info("Nessuna giocata pendente.")

# --- TAB 3: FISCALE ---
with t3:
    st.subheader("🏁 Resoconto Finanziario")
    if not df_attuale.empty:
        tot_giocato = round(df_attuale['Stake'].sum(), 2)
        prof_netto = round(df_attuale['Profitto'].sum(), 2)
        
        m1, m2 = st.columns(2)
        m1.metric("💰 Volume Totale", f"{tot_giocato} €")
        m2.metric("📈 Profitto Netto", f"{prof_netto} €", delta=f"{prof_netto} €")
        
        st.divider()
        st.write("### Storico Operazioni")
        def color_row(row):
            if row['Esito'] == "VINTO": return ['background-color: rgba(0, 255, 0, 0.1)'] * len(row)
            if row['Esito'] == "PERSO": return ['background-color: rgba(255, 0, 0, 0.1)'] * len(row)
            return [''] * len(row)
            
        st.dataframe(df_attuale.style.apply(color_row, axis=1), use_container_width=True)
