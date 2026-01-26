import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date, timedelta
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V11.36 - High Visibility", layout="wide")

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
    "soccer_italy_serie_a": "🇮🇹 Serie A", "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_england_league_1": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", "soccer_spain_la_liga": "🇪🇸 La Liga",
    "soccer_germany_bundesliga": "🇩🇪 Bundesliga", "soccer_uefa_champions_league": "🇪🇺 Champions",
    "soccer_uefa_europa_league": "🇪🇺 Europa League", "soccer_france_ligue_1": "🇫🇷 Ligue 1"
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

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11.36")
if 'api_data' not in st.session_state: st.session_state['api_data'] = []

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    df_tot = carica_db()
    match_pendenti = df_tot[df_tot['Esito'] == "Pendente"]['Match'].tolist() if not df_tot.empty else []

    with st.sidebar:
        st.header("⚙️ Parametri Cassa")
        budget_cassa = st.number_input("Budget (€)", value=250.0)
        rischio = st.slider("Kelly", 0.05, 0.50, 0.20)
        soglia_val = st.slider("Valore Min %", 0, 15, 5) / 100
        st.divider()
        st.header("📈 Obiettivo Settimanale")
        target_sett = st.number_input("Match Target", value=10)
        today = date.today()
        start_week = today - timedelta(days=today.weekday())
        partite_sett = df_tot[df_tot['dt_obj'].dt.date >= start_week].shape[0] if not df_tot.empty else 0
        st.progress(min(1.0, partite_sett / target_sett))
        st.write(f"Giocate: **{partite_sett}** | Mancanti: **{max(0, target_sett - partite_sett)}**")

    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    sel_name = st.selectbox("Campionato:", list(leagues.keys()))
    
    if st.button("🚀 SCANSIONA"):
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_name]}/odds/', params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
        if res.status_code == 200: st.session_state['api_data'] = res.json()

    if st.session_state['api_data']:
        for m in st.session_state['api_data']:
            try:
                nome_match = f"{m['home_team']}-{m['away_team']}"
                gia_presente = nome_match in match_pendenti
                date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
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
                                opts.append({"T": "UNDER 2.5", "Q": q_un, "P": ((1/q_un)/margin)+0.06, "BK": b['title']})
                
                if opts:
                    best = max(opts, key=lambda x: (x['P'] * x['Q']) - 1)
                    val = round(((best['P'] * best['Q']) - 1) * 100, 2)
                    if val/100 > soglia_val:
                        col_txt, col_btn = st.columns([3, 1])
                        info_txt = f"📅 {date_m} | {sel_name} | **{nome_match}**"
                        if gia_presente:
                            col_txt.write(f"{info_txt}  \n✅ **GIÀ IN PORTAFOGLIO**")
                            col_btn.button("OK", key=f"btn_{nome_match}", disabled=True)
                        else:
                            col_txt.write(info_txt)
                            if col_btn.button(f"ADD {best['T']} @{best['Q']}", key=f"add_{nome_match}"):
                                val_k = (best['P'] * best['Q']) - 1
                                stake = round(max(2.0, min(budget_cassa * (val_k/(best['Q']-1)) * rischio, budget_cassa*0.15)), 2)
                                n = {"Data Match": date_m, "Match": nome_match, "Scelta": best['T'], "Quota": best['Q'], "Stake": stake, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": leagues[sel_name], "Risultato": "-"}
                                salva_db(pd.concat([carica_db(), pd.DataFrame([n])], ignore_index=True))
                                st.rerun()
                        st.divider()
            except: continue

with t2:
    st.subheader("💼 Gestione Portafoglio")
    df_p = carica_db()
    pend = df_p[df_p['Esito'] == "Pendente"]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Capitale Esposto", f"{round(pend['Stake'].sum(), 2)} €")
    c2.metric("Rientro Lordo", f"{round((pend['Stake'] * pend['Quota']).sum(), 2)} €")
    c3.metric("Possibile Vincita", f"{round((pend['Stake'] * pend['Quota']).sum() - pend['Stake'].sum(), 2)} €")
    
    st.divider()
    if pend.empty:
        st.info("Nessuna scommessa pendente.")
    else:
        for i, r in pend.iterrows():
            col_main, col_btn = st.columns([6, 1])
            camp = LEAGUE_NAMES.get(r['Sport_Key'], "Vari")
            vincita_r = round(r['Stake'] * r['Quota'], 2)
            
            # Riga 1: Dati Match
            col_main.write(f"📅 {r['Data Match']} | {camp} | **{r['Match']}**")
            
            # Riga 2: EVIDENZA SCELTA (Grande e Grassetto)
            # Usiamo Markdown con tag HTML per aumentare la dimensione del carattere
            scelta_testo = r['Scelta']
            col_main.markdown(f"### 🎯 **{scelta_testo}** @{r['Quota']}")
            
            # Riga 3: Dettagli economici
            col_main.write(f"💰 Puntata: **{r['Stake']}€** | 💸 Rientro: **{vincita_r}€** | 🏦 {r['Bookmaker']}")
            
            if col_btn.button("🗑️", key=f"del_{i}"):
                salva_db(df_p.drop(i))
                st.rerun()
            st.divider()

with t3:
    st.subheader("📊 Analisi Fiscale")
    df_f = carica_db()
    if not df_f.empty:
        df_valid = df_f.dropna(subset=['dt_obj'])
        s_range = st.date_input("Periodo:", [df_valid['dt_obj'].min().date() if not df_valid.empty else date.today(), date.today()])
        if len(s_range) == 2:
            df_fil = df_f[(df_f['dt_obj'].dt.date >= s_range[0]) & (df_f['dt_obj'].dt.date <= s_range[1])]
            for i, row in df_fil.sort_index(ascending=False).iterrows():
                camp = LEAGUE_NAMES.get(row['Sport_Key'], "Vari")
                msg = f"{row['Data Match']} | {camp} | **{row['Match']}** | {row['Risultato']} | {row['Profitto']}€"
                if row['Esito'] == "VINTO": st.success(f"🟢 VINTO | {msg}")
                elif row['Esito'] == "PERSO": st.error(f"🔴 PERSO | {msg}")
                else: st.warning(f"🟡 PENDENTE | {row['Data Match']} | {camp} | {row['Match']} | @{row['Quota']}")
