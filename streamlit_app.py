import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date, timedelta
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V11.33 - Objective Tracker", layout="wide")

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
st.title("🎯 AI SNIPER V11.33")
if 'api_data' not in st.session_state: st.session_state['api_data'] = []

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    df_tot = carica_db()
    
    with st.sidebar:
        st.header("⚙️ Parametri Cassa")
        budget_cassa = st.number_input("Budget (€)", value=250.0)
        rischio = st.slider("Kelly", 0.05, 0.50, 0.20)
        soglia_val = st.slider("Valore Min %", 0, 15, 5) / 100
        
        st.divider()
        st.header("📈 Obiettivo Settimanale")
        target_settimanale = st.number_input("Match Target", value=10)
        
        # Calcolo partite della settimana corrente (Lunedì-Domenica)
        today = date.today()
        start_week = today - timedelta(days=today.weekday())
        
        if not df_tot.empty:
            partite_settimana = df_tot[df_tot['dt_obj'].dt.date >= start_week].shape[0]
        else:
            partite_settimana = 0
            
        mancanti = max(0, target_settimanale - partite_settimana)
        progresso = min(1.0, partite_settimana / target_settimanale)
        
        st.progress(progresso)
        st.write(f"Giocate: **{partite_settimana}** | Mancanti: **{mancanti}**")
        
        if mancanti > 0:
            st.info(f"💡 Mancano {mancanti} match per completare il piano settimanale.")
        else:
            st.success("✅ Obiettivo raggiunto! Valuta se fermarti o selezionare solo match 'Top Value'.")

    # Logica Scanner (Serie A, Premier, ecc.)
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
                                margin = (1/q_ov) + (1/q_un)
                                p_ov, p_un = (1/q_ov)/margin, (1/q_un)/margin
                                opts.append({"T": "OVER 2.5", "Q": q_ov, "P": p_ov+0.06, "BK": b['title']})
                                opts.append({"T": "UNDER 2.5", "Q": q_un, "P": p_un+0.06, "BK": b['title']})
                if opts:
                    best = max(opts, key=lambda x: (x['P'] * x['Q']) - 1)
                    val = round(((best['P'] * best['Q']) - 1) * 100, 2)
                    if val/100 > soglia_val:
                        st.write(f"📅 {date_m} | {sel_name} | **{m['home_team']}-{m['away_team']}**")
                        if st.button(f"ADD {best['T']} @{best['Q']} (+{val}%)", key=f"add_{m['home_team']}_{best['BK']}"):
                            valore_k = (best['P'] * best['Q']) - 1
                            importo_k = budget_cassa * (valore_k / (best['Q'] - 1)) * rischio
                            final_stake = round(max(2.0, min(importo_k, budget_cassa * 0.15)), 2)
                            n = {"Data Match": date_m, "Match": f"{m['home_team']}-{m['away_team']}", "Scelta": best['T'], "Quota": best['Q'], "Stake": final_stake, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": sel_key, "Risultato": "-"}
                            salva_db(pd.concat([carica_db(), pd.DataFrame([n])], ignore_index=True))
                            st.rerun() # Refresh per aggiornare il contatore nella sidebar
            except: continue

with t2:
    st.subheader("💼 Gestione Portafoglio")
    df_p = carica_db()
    pend = df_p[df_p['Esito'] == "Pendente"]
    capitale_esposto = round(pend['Stake'].sum(), 2)
    rientro_potenziale = round((pend['Stake'] * pend['Quota']).sum(), 2)
    vincita_potenziale_netta = round(rientro_potenziale - capitale_esposto, 2)
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Capitale Esposto", f"{capitale_esposto} €")
    m2.metric("Rientro Potenziale (Lordo)", f"{rientro_potenziale} €")
    m3.metric("Possibile Vincita (Netta)", f"{vincita_potenziale_netta} €")
    
    st.divider()
    if pend.empty:
        st.info("Nessun match pendente.")
    else:
        for i, r in pend.iterrows():
            c_info, c_del = st.columns([5, 1])
            vincita_r = round(r['Stake'] * r['Quota'], 2)
            c_info.write(f"📅 **{r['Data Match']}** | {LEAGUE_NAMES.get(r['Sport_Key'], 'Altro')}")
            c_info.write(f"🏟️ **{r['Match']}** | 🎯 **{r['Scelta']}** @{r['Quota']} | 💰 Stake: {r['Stake']}€")
            if c_del.button("🗑️", key=f"del_{i}"):
                salva_db(df_p.drop(i))
                st.rerun()

with t3:
    st.subheader("📊 Analisi Fiscale")
    df_f = carica_db()
    if not df_f.empty:
        df_valid = df_f.dropna(subset=['dt_obj'])
        min_d = df_valid['dt_obj'].min().date() if not df_valid.empty else date.today()
        s_range = st.date_input("Filtra Periodo:", [min_d, date.today()])
        
        if len(s_range) == 2:
            mask = (df_f['dt_obj'].dt.date >= s_range[0]) & (df_f['dt_obj'].dt.date <= s_range[1])
            df_fil = df_f[mask]
            conc = df_fil[df_fil['Esito'] != "Pendente"]
            scomm = round(conc['Stake'].sum(), 2)
            vinto = round(conc[conc['Esito']=="VINTO"]['Profitto'].sum() + conc[conc['Esito']=="VINTO"]['Stake'].sum(), 2)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Volume Scommesso", f"{scomm} €")
            c2.metric("Rientro Lordo", f"{vinto} €")
            c3.metric("Profitto Netto", f"{round(vinto-scomm, 2)} €")
            
            for i, row in df_fil.sort_index(ascending=False).iterrows():
                camp_fmt = LEAGUE_NAMES.get(row['Sport_Key'], "Sport Vari")
                if row['Esito'] == "VINTO":
                    st.success(f"🟢 **VINTO** | {row['Data Match']} | {camp_fmt} | **{row['Match']}** | {row['Risultato']} | +{row['Profitto']}€")
                elif row['Esito'] == "PERSO":
                    st.error(f"🔴 **PERSO** | {row['Data Match']} | {camp_fmt} | **{row['Match']}** | {row['Risultato']} | {row['Profitto']}€")
                else:
                    st.warning(f"🟡 **PENDENTE** | {row['Data Match']} | {camp_fmt} | **{row['Match']}** | {row['Scelta']} @{row['Quota']}")
