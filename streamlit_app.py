import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date, timedelta
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V11.42 - Anti-Block & Premier Fix", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
TARGET_FINALE = 5000.0

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A",
    "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_england_premier_league": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League",
    "soccer_spain_la_liga": "🇪🇸 La Liga",
    "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_uefa_champions_league": "🇪🇺 Champions",
    "soccer_uefa_europa_league": "🇪🇺 Europa League",
    "soccer_france_ligue_1": "🇫🇷 Ligue 1"
}

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "888sport"]

# --- MOTORE DATABASE CON CACHE (RISOLVE ERRORE 429) ---
@st.cache_data(ttl=10)
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
        df = df.dropna(subset=["Match"])
        df['dt_obj'] = pd.to_datetime(df['Data Match'] + f"/{date.today().year}", format="%d/%m %H:%M/%Y", errors='coerce')
        return df
    except Exception as e:
        st.warning("⚠️ Limite Google raggiunto. Attendi 10 secondi...")
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    if 'dt_obj' in df.columns: df = df.drop(columns=['dt_obj'])
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear() # Svuota la cache dopo il salvataggio
    st.toast("✅ Cloud Sincronizzato!")

# --- AGGIORNAMENTO AUTOMATICO RISULTATI ---
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
st.title("🎯 AI SNIPER V11.42")
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
        with st.spinner(f"Ricerca in {sel_name}..."):
            res = requests.get(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_name]}/odds/', params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
            if res.status_code == 200:
                st.session_state['api_data'] = res.json()
                if not st.session_state['api_data']: st.warning("Nessun match trovato per i parametri scelti.")
            else: st.error("Errore API. Controlla la tua quota o connessione.")

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
                        if gia_presente:
                            col_txt.write(f"📅 {date_m} | {sel_name} | **{nome_match}** \n✅ **GIÀ IN PORTAFOGLIO**")
                            col_btn.button("OK", key=f"btn_{nome_match}", disabled=True)
                        else:
                            col_txt.write(f"📅 {date_m} | {sel_name} | **{nome_match}**")
                            if col_btn.button(f"ADD {best['T']} @{best['Q']}", key=f"add_{nome_match}"):
                                val_k = (best['P'] * best['Q']) - 1
                                stake = round(max(2.0, min(budget_cassa * (val_k/(best['Q']-1)) * rischio, budget_cassa*0.15)), 2)
                                n = {"Data Match": date_m, "Match": nome_match, "Scelta": best['T'], "Quota": best['Q'], "Stake": stake, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": leagues[sel_name], "Risultato": "-"}
                                salva_db(pd.concat([carica_db(), pd.DataFrame([n])], ignore_index=True))
                                st.rerun()
                        st.divider()
            except: continue

with t2:
    st.subheader("💼 Portafoglio")
    df_p = carica_db()
    pend = df_p[df_p['Esito'] == "Pendente"]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Esposto", f"{round(pend['Stake'].sum(), 2)} €")
    c2.metric("Rientro Lordo", f"{round((pend['Stake'] * pend['Quota']).sum(), 2)} €")
    c3.metric("Possibile Vincita", f"{round((pend['Stake'] * pend['Quota']).sum() - pend['Stake'].sum(), 2)} €")
    
    st.button("🔄 AGGIORNA RISULTATI", on_click=check_results, use_container_width=True)
    st.divider()
    
    for i, r in pend.iterrows():
        col_main, col_btn = st.columns([10, 1])
        camp = LEAGUE_NAMES.get(r['Sport_Key'], "Vari")
        vincita_r = round(r['Stake'] * r['Quota'], 2)
        riga = f"🗓️ {r['Data Match']} | {camp} | **{r['Match']}** | <span style='font-size:1.1rem;'>**{r['Scelta']} @{r['Quota']}**</span> | 💰 {r['Stake']}€ | 💸 **{vincita_r}€** | 🏦 {r['Bookmaker']}"
        col_main.markdown(riga, unsafe_allow_html=True)
        if col_btn.button("🗑️", key=f"del_{i}"):
            salva_db(df_p.drop(i)); st.rerun()
        st.divider()

with t3:
    st.subheader("📊 Analisi Fiscale")
    df_f = carica_db()
    if not df_f.empty:
        # Calcoli Goal Tracker
        tot_speso = round(df_f['Stake'].sum(), 2)
        tot_vinto = round(df_f[df_f['Esito'] == "VINTO"]['Profitto'].sum() + df_f[df_f['Esito'] == "VINTO"]['Stake'].sum(), 2)
        netto = round(tot_vinto - tot_speso, 2)
        
        st.info(f"🏆 **Goal: {TARGET_FINALE}€** | Attuale: **{netto}€** | Mancano: **{round(TARGET_FINALE - netto, 2)}€**")
        st.progress(min(1.0, max(0.0, netto / TARGET_FINALE)))
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Speso", f"{tot_speso} €")
        m2.metric("Vinto", f"{tot_vinto} €")
        m3.metric("Netto", f"{netto} €", delta=f"{netto}€")
        
        csv = df_f.to_csv(index=False).encode('utf-8')
        st.download_button("📥 BACKUP CSV", data=csv, file_name="sniper_backup.csv", mime='text/csv')
        st.divider()

        df_valid = df_f.dropna(subset=['dt_obj'])
        s_range = st.date_input("Periodo:", [df_valid['dt_obj'].min().date() if not df_valid.empty else date.today(), date.today()])
        if len(s_range) == 2:
            df_fil = df_f[(df_f['dt_obj'].dt.date >= s_range[0]) & (df_f['dt_obj'].dt.date <= s_range[1])].sort_index(ascending=False)
            for i, row in df_fil.iterrows():
                camp = LEAGUE_NAMES.get(row['Sport_Key'], "Vari")
                v_pot = round(row['Stake'] * row['Quota'], 2)
                dati = f"{row['Data Match']} | {camp} | **{row['Match']}** | **{row['Scelta']} @{row['Quota']}**"
                if row['Esito'] == "VINTO": st.success(f"🟢 VINTO | {dati} | Score: {row['Risultato']} | +{row['Profitto']}€")
                elif row['Esito'] == "PERSO": st.error(f"🔴 PERSO | {dati} | Score: {row['Risultato']} | {row['Profitto']}€")
                else: st.warning(f"🟡 PENDENTE | {dati} | 💰 Rientro: **{v_pot}€**")
