import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V11.29 - Ultimate Visual", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

BK_EURO_AUTH = {
    "Bet365": "https://www.bet365.it", "Snai": "https://www.snai.it",
    "Better": "https://www.lottomatica.it/scommesse", "Planetwin365": "https://www.planetwin365.it",
    "Eurobet": "https://www.eurobet.it", "Goldbet": "https://www.goldbet.it", 
    "Sisal": "https://www.sisal.it", "Bwin": "https://www.bwin.it",
    "William Hill": "https://www.williamhill.it", "888sport": "https://www.888sport.it"
}

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A",
    "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_england_league_1": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League",
    "soccer_spain_la_liga": "🇪🇸 La Liga",
    "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_uefa_champions_league": "🇪🇺 Champions",
    "soccer_uefa_europa_league": "🇪🇺 Europa League",
    "soccer_france_ligue_1": "🇫🇷 Ligue 1"
}

# --- MOTORE DATABASE ---
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
        df = df.dropna(subset=["Match"])
        df['dt_obj'] = pd.to_datetime(df['Data Match'] + f"/{date.today().year}", format="%d/%m %H:%M/%Y", errors='coerce')
        return df
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    if 'dt_obj' in df.columns: df = df.drop(columns=['dt_obj'])
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

# --- LOGICA CALCOLI ---
def get_totals_value(q_over, q_under):
    margin = (1/q_over) + (1/q_under)
    return (1/q_over) / margin, (1/q_under) / margin

def calc_stake(prob, quota, budget, frazione):
    valore = (prob * quota) - 1
    if valore <= 0: return 2.0
    importo = budget * (valore / (quota - 1)) * frazione
    return round(max(2.0, min(importo, budget * 0.15)), 2)

# --- AUTO-CHECK ---
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
                    if m_res and m_res.get('scores'):
                        s = m_res['scores']
                        score_str = f"{s[0]['score']}-{s[1]['score']}"
                        goals = sum(int(x['score']) for x in s)
                        vinto = (r['Scelta'] == "OVER 2.5" and goals > 2.5) or (r['Scelta'] == "UNDER 2.5" and goals < 2.5)
                        df.at[i, 'Esito'] = "VINTO" if vinto else "PERSO"
                        df.at[i, 'Risultato'] = score_str
                        df.at[i, 'Profitto'] = round((r['Stake']*r['Quota'])-r['Stake'], 2) if vinto else -r['Stake']
                        cambiamenti = True
    if cambiamenti: salva_db(df); st.rerun()

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11.29")
if 'api_data' not in st.session_state: st.session_state['api_data'] = []

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    with st.sidebar:
        st.header("⚙️ Parametri Cassa")
        budget_cassa = st.number_input("Budget (€)", value=250.0)
        rischio = st.slider("Kelly", 0.05, 0.50, 0.20)
        soglia_val = st.slider("Valore Min %", 0, 15, 5) / 100
    
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    sel_name = st.selectbox("Campionato:", list(leagues.keys()))
    sel_key = leagues[sel_name]
    
    if st.button("🚀 SCANSIONA"):
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{sel_key}/odds/', params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
        if res.status_code == 200: st.session_state['api_data'] = res.json()

    if st.session_state['api_data']:
        for m in st.session_state['api_data']:
            try:
                date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
                opts = []
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_EURO_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == 'totals'), None)
                        if mk:
                            q_ov = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), None)
                            q_un = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), None)
                            if q_ov and q_un:
                                p_ov, p_un = get_totals_value(q_ov, q_un)
                                opts.append({"T": "OVER 2.5", "Q": q_ov, "P": p_ov+0.06, "BK": b['title']})
                                opts.append({"T": "UNDER 2.5", "Q": q_un, "P": p_un+0.06, "BK": b['title']})
                if opts:
                    best = max(opts, key=lambda x: (x['P'] * x['Q']) - 1)
                    val = round(((best['P'] * best['Q']) - 1) * 100, 2)
                    if val/100 > soglia_val:
                        st.write(f"📅 {date_m} | {sel_name} | **{m['home_team']}-{m['away_team']}**")
                        if st.button(f"ADD {best['T']} @{best['Q']} (+{val}%)", key=f"add_{m['home_team']}_{best['BK']}"):
                            n = {"Data Match": date_m, "Match": f"{m['home_team']}-{m['away_team']}", "Scelta": best['T'], "Quota": best['Q'], "Stake": calc_stake(best['P'], best['Q'], budget_cassa, rischio), "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": sel_key, "Risultato": "-"}
                            salva_db(pd.concat([carica_db(), pd.DataFrame([n])], ignore_index=True))
                            st.toast("Aggiunto!")
            except: continue

with t2:
    st.subheader("💼 Portafoglio Pendente")
    if st.button("🔄 AGGIORNA RISULTATI"): check_results()
    df_p = carica_db()
    pend = df_p[df_p['Esito'] == "Pendente"]
    st.metric("Capitale Esposto", f"{round(pend['Stake'].sum(), 2)} €")
    st.divider()
    for i, r in pend.iterrows():
        c_info, c_del = st.columns([5, 1])
        campionato = LEAGUE_NAMES.get(r['Sport_Key'], "Sport Vari")
        c_info.write(f"📅 **{r['Data Match']}** | {campionato}")
        c_info.write(f"🏟️ **{r['Match']}** | 🎯 {r['Scelta']} @{r['Quota']} | 💰 Stake: **{r['Stake']}€**")
        if c_del.button("🗑️", key=f"del_{i}"): salva_db(df_p.drop(i)); st.rerun()
        st.divider()

with t3:
    st.subheader("📊 Analisi Fiscale")
    df_f = carica_db()
    if not df_f.empty and 'dt_obj' in df_f.columns:
        df_valid = df_f.dropna(subset=['dt_obj'])
        start_date = df_valid['dt_obj'].min().date() if not df_valid.empty else date.today()
        s_range = st.date_input("Range Temporale:", [start_date, date.today()])
        
        if len(s_range) == 2:
            mask = (df_f['dt_obj'].dt.date >= s_range[0]) & (df_f['dt_obj'].dt.date <= s_range[1])
            df_fil = df_f[mask]
            conc = df_fil[df_fil['Esito'] != "Pendente"]
            scomm = round(conc['Stake'].sum(), 2)
            vinto = round(conc[conc['Esito']=="VINTO"]['Profitto'].sum() + conc[conc['Esito']=="VINTO"]['Stake'].sum(), 2)
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Volume Scommesso", f"{scomm} €")
            m2.metric("Rientro Lordo", f"{vinto} €")
            m3.metric("Profitto Netto", f"{round(vinto-scomm, 2)} €", delta=f"{round(vinto-scomm, 2)} €")
            
            st.write("### 📜 Dettaglio Esiti (Timeline)")
            for i, row in df_fil.sort_index(ascending=False).iterrows():
                if row['Esito'] == "VINTO":
                    st.success(f"🟢 **VINTO** | {row['Data Match']} | **{row['Match']}** | Esito: {row['Risultato']} | Profitto: +{row['Profitto']}€")
                elif row['Esito'] == "PERSO":
                    st.error(f"🔴 **PERSO** | {row['Data Match']} | **{row['Match']}** | Esito: {row['Risultato']} | Perdita: {row['Profitto']}€")
                else:
                    st.warning(f"🟡 **PENDENTE** | {row['Data Match']} | **{row['Match']}** | {row['Scelta']} @{row['Quota']}")
            
            st.divider()
            st.write("### 🗃️ Tabella Dati")
            st.dataframe(df_fil.drop(columns=['dt_obj']).sort_index(ascending=False), use_container_width=True)
