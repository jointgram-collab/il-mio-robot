import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V12.5 - Full Power", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

if 'api_data' not in st.session_state: st.session_state['api_data'] = []
if 'api_usage' not in st.session_state: st.session_state['api_usage'] = {'remaining': "N/D", 'used': "N/D"}

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "William Hill", "888sport"]

LEAGUE_MAP = {
    "🇮🇹 Serie A": "soccer_italy_serie_a",
    "🇮🇹 Serie B": "soccer_italy_serie_b",
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League": "soccer_epl",
    "🇪🇸 La Liga": "soccer_spain_la_liga",
    "🇩🇪 Bundesliga": "soccer_germany_bundesliga",
    "🇫🇷 Ligue 1": "soccer_france_ligue_1",
    "🇳🇱 Eredivisie": "soccer_netherlands_eredivisie",
    "🇪🇺 Europa League": "soccer_uefa_europa_league",
    "🇪🇺 Conference League": "soccer_uefa_europa_conference_league"
}

# --- FUNZIONI CORE DATABASE ---
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

def get_champions_key():
    try:
        r = requests.get(f'https://api.the-odds-api.com/v4/sports/?api_key={API_KEY}')
        if r.status_code == 200:
            for s in r.json():
                if "Champions League" in s.get('title', ''): return s.get('key')
        return "soccer_uefa_champions_league"
    except: return "soccer_uefa_champions_league"

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V12.5")
df_attuale = carica_db()

with st.sidebar:
    st.header("📊 Stato API")
    c1, c2 = st.columns(2)
    c1.metric("Residui", st.session_state['api_usage']['remaining'])
    c2.metric("Usati", st.session_state['api_usage']['used'])
    st.divider()
    budget_cassa = st.number_input("Budget (€)", value=500.0)
    rischio = st.slider("Kelly Criterion", 0.05, 0.50, 0.20)
    soglia_val = st.slider("Valore Min %", 0, 15, 3) / 100

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER ---
with t1:
    col_sel, col_btn, col_ore = st.columns([1, 1, 1])
    sel_name = col_sel.selectbox("Campionato Singolo:", list(LEAGUE_MAP.keys()) + ["🏆 Champions League"])
    ore_ricerca = col_ore.select_slider("Finestra (ore):", options=[24, 48, 72, 96, 120], value=120)
    
    if col_btn.button("🚀 SCANSIONE TOTALE", use_container_width=True):
        all_data = []
        keys = list(LEAGUE_MAP.values())
        keys.append(get_champions_key())
        pbar = st.progress(0)
        for idx, k in enumerate(set(keys)):
            res = requests.get(f'https://api.the-odds-api.com/v4/sports/{k}/odds/', params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
            if res.status_code == 200:
                all_data.extend(res.json())
                st.session_state['api_usage']['remaining'] = res.headers.get('x-requests-remaining')
            time.sleep(0.5)
            pbar.progress((idx + 1) / len(set(keys)))
        st.session_state['api_data'] = all_data
        st.rerun()

    st.divider()

    if st.session_state['api_data']:
        now = datetime.utcnow()
        limit = now + timedelta(hours=ore_ricerca)
        pend_list = df_attuale[df_attuale['Esito'] == "Pendente"]['Match'].tolist()
        
        for i, m in enumerate(st.session_state['api_data']):
            try:
                m_time = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
                if not (now <= m_time <= limit): continue
                
                nome_m = f"{m['home_team']}-{m['away_team']}"
                opts = []
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_EURO_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == 'totals'), None)
                        if mk:
                            q_ov = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and float(o.get('point',0)) == 2.5), None)
                            q_un = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and float(o.get('point',0)) == 2.5), None)
                            if q_ov and q_un:
                                margin = (1/q_ov) + (1/q_un)
                                opts.append({"T": "OVER 2.5", "Q": q_ov, "P": ((1/q_ov)/margin)+0.06, "BK": b['title']})
                
                if opts:
                    best = max(opts, key=lambda x: (x['P'] * x['Q']) - 1)
                    val = (best['P'] * best['Q']) - 1
                    if val >= soglia_val:
                        stk_c = round(max(2.0, min(budget_cassa * (val/(best['Q']-1)) * rischio, budget_cassa*0.15)), 2)
                        c_a, c_b = st.columns([3, 1])
                        c_a.markdown(f"📅 {m_time.strftime('%d/%m %H:%M')} | **{nome_m}** <br>🏆 {m['sport_title']} | **{best['BK']}** | Valore: **{round(val*100,1)}%**", unsafe_allow_html=True)
                        if c_b.button(f"ADD @{best['Q']}", key=f"add_{i}", disabled=(nome_m in pend_list)):
                            nuova = pd.DataFrame([{"Data Match": m_time.strftime('%d/%m %H:%M'), "Match": nome_m, "Scelta": best['T'], "Quota": best['Q'], "Stake": stk_c, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": m['sport_key'], "Risultato": "-"}])
                            salva_db(pd.concat([carica_db(), nuova], ignore_index=True))
                            st.rerun()
                        st.divider()
            except: continue

# --- TAB 2: PORTAFOGLIO ---
with t2:
    st.button("🔄 AGGIORNA RISULTATI", on_click=check_results, use_container_width=True)
    st.divider()
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"]
    if not df_p.empty:
        for i, r in df_p.iterrows():
            c1, c2 = st.columns([15, 1])
            c1.markdown(f"🟡 **{r['Match']}** | {r['Scelta']} @**{r['Quota']}** | Stake: **{r['Stake']}€**", unsafe_allow_html=True)
            if c2.button("🗑️", key=f"del_{i}"):
                salva_db(df_attuale.drop(i))
                st.rerun()
            st.markdown("<hr style='margin:2px 0px; border:0.1px solid #f0f2f6'>", unsafe_allow_html=True)

# --- TAB 3: FISCALE ---
with t3:
    if not df_attuale.empty:
        tot_giocato = round(df_attuale['Stake'].sum(), 2)
        prof_netto = round(df_attuale['Profitto'].sum(), 2)
        m1, m2 = st.columns(2)
        m1.metric("💰 Volume Totale", f"{tot_giocato} €")
        m2.metric("📈 Profitto Netto", f"{prof_netto} €", delta=f"{prof_netto} €")
        
        st.divider()
        def color_row(row):
            if row['Esito'] == "VINTO": return ['background-color: rgba(0, 255, 0, 0.1)'] * len(row)
            if row['Esito'] == "PERSO": return ['background-color: rgba(255, 0, 0, 0.1)'] * len(row)
            return [''] * len(row)
        st.dataframe(df_attuale.style.apply(color_row, axis=1), use_container_width=True)
        
        csv = df_attuale.to_csv(index=False).encode('utf-8')
        st.download_button("📥 BACKUP CSV", data=csv, file_name=f"sniper_backup_{date.today()}.csv")
