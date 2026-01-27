import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V12.9 - Ultra Compact", layout="wide")

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

def get_champions_key():
    try:
        r = requests.get(f'https://api.the-odds-api.com/v4/sports/?api_key={API_KEY}')
        if r.status_code == 200:
            for s in r.json():
                if "Champions League" in s.get('title', ''): return s.get('key')
        return "soccer_uefa_champions_league"
    except: return "soccer_uefa_champions_league"

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
st.title("🎯 AI SNIPER V12.9")
df_attuale = carica_db()

with st.sidebar:
    st.header("📊 Stato API")
    c1, c2 = st.columns(2)
    c1.metric("Residui", st.session_state['api_usage']['remaining'])
    c2.metric("Usati", st.session_state['api_usage']['used'])
    st.divider()
    budget_cassa = st.number_input("Budget (€)", value=500.0)
    rischio = st.slider("Kelly", 0.05, 0.50, 0.20)
    soglia_val = st.slider("Valore Min %", 0, 15, 3) / 100

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER ---
with t1:
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    c_sel, c_all = st.columns([2, 1])
    sel_name = c_sel.selectbox("Campionato Singolo:", list(leagues.keys()))
    
    if c_all.button("🚀 SCANSIONE TOTALE", use_container_width=True):
        all_found = []
        keys_to_scan = list(LEAGUE_NAMES.keys())
        keys_to_scan.append(get_champions_key())
        pbar = st.progress(0)
        for idx, k in enumerate(set(keys_to_scan)):
            r = requests.get(f'https://api.the-odds-api.com/v4/sports/{k}/odds/', params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
            if r.status_code == 200:
                all_found.extend(r.json())
                st.session_state['api_usage']['remaining'] = r.headers.get('x-requests-remaining')
            time.sleep(0.4)
            pbar.progress((idx + 1) / len(set(keys_to_scan)))
        st.session_state['api_data'] = all_found
        st.rerun()

    if st.button("🔍 AVVIA SCANSIONE SINGOLA", use_container_width=True):
        target_key = get_champions_key() if "Champions" in sel_name else leagues[sel_name]
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{target_key}/odds/', params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
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
                            if q_ov and q_un:
                                margin = (1/q_ov) + (1/q_un)
                                opts.append({"T": "OVER 2.5", "Q": q_ov, "P": ((1/q_ov)/margin)+0.06, "BK": b['title']})
                if opts:
                    best = max(opts, key=lambda x: (x['P'] * x['Q']) - 1)
                    val = (best['P'] * best['Q']) - 1
                    if val >= soglia_val:
                        stk_c = round(max(2.0, min(budget_cassa * (val/(best['Q']-1)) * rischio, budget_cassa*0.15)), 2)
                        c_a, c_b = st.columns([3, 1])
                        c_a.write(f"📅 {dt_m} | **{nome_m}** | {m['sport_title']} | Val: **{round(val*100,1)}%**")
                        if c_b.button(f"ADD @{best['Q']}", key=f"add_{i}", disabled=(nome_m in pend_list)):
                            nuova = pd.DataFrame([{"Data Match": dt_m, "Match": nome_m, "Scelta": best['T'], "Quota": best['Q'], "Stake": stk_c, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": m['sport_key'], "Risultato": "-"}])
                            salva_db(pd.concat([carica_db(), nuova], ignore_index=True))
                            st.rerun()
                        st.divider()
            except: continue

# --- TAB 2: PORTAFOGLIO (SINGLE LINE COMPACT) ---
with t2:
    st.button("🔄 AGGIORNA RISULTATI", on_click=check_results, use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"]
    
    if not df_p.empty:
        for i, r in df_p.iterrows():
            vinc_p = round(r['Stake'] * r['Quota'], 2)
            league_name = LEAGUE_NAMES.get(r['Sport_Key'], r['Sport_Key'].split("_")[-1].upper())
            
            c1, c2 = st.columns([18, 1])
            # Layout su una singola riga con evento in grassetto
            c1.markdown(f"""
                <div style='background-color: rgba(255, 193, 7, 0.1); padding: 5px 10px; border-radius: 5px; margin-bottom: 2px; border-left: 4px solid #ffc107;'>
                    <b>{r['Match']}</b> ({league_name}) | <b>{r['Scelta']}</b> @{r['Quota']} | Stake: {r['Stake']}€ | Vincita: {vinc_p}€ | 🏦 {r['Bookmaker']}
                </div>
                """, unsafe_allow_html=True)
            if c2.button("🗑️", key=f"del_{i}"):
                salva_db(df_attuale.drop(i))
                st.rerun()
    else: 
        st.info("Nessuna giocata pendente.")

# --- TAB 3: FISCALE (STILE CLASSICO) ---
with t3:
    st.subheader("🏁 Cruscotto Finanziario")
    if not df_attuale.empty:
        tot_giocato = round(df_attuale['Stake'].sum(), 2)
        tot_vinto = round(df_attuale[df_attuale['Esito'] == "VINTO"]['Profitto'].sum() + df_attuale[df_attuale['Esito'] == "VINTO"]['Stake'].sum(), 2)
        tot_perso = round(df_attuale[df_attuale['Esito'] == "PERSO"]['Stake'].sum(), 2)
        prof_netto = round(df_attuale['Profitto'].sum(), 2)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💰 Giocato", f"{tot_giocato} €")
        m2.metric("✅ Vinto", f"{tot_vinto} €")
        m3.metric("❌ Perso", f"{tot_perso} €")
        m4.metric("📈 Netto", f"{prof_netto} €")
        
        st.divider()
        csv_data = df_attuale.to_csv(index=False).encode('utf-8')
        st.download_button("📥 ESPORTA CSV", data=csv_data, file_name=f"sniper_backup_{date.today()}.csv", use_container_width=True)

        st.divider()
        def color_row(row):
            if row['Esito'] == "VINTO": return ['background-color: rgba(0, 255, 0, 0.15)'] * len(row)
            if row['Esito'] == "PERSO": return ['background-color: rgba(255, 0, 0, 0.15)'] * len(row)
            if row['Esito'] == "Pendente": return ['background-color: rgba(255, 255, 0, 0.15)'] * len(row)
            return [''] * len(row)

        st.write("### Storico Operazioni")
        view_df = df_attuale[["Data Match", "Match", "Scelta", "Quota", "Stake", "Esito", "Profitto", "Risultato", "Bookmaker"]]
        st.dataframe(view_df.sort_index(ascending=False).style.apply(color_row, axis=1), use_container_width=True)
    else:
        st.info("Database vuoto.")
