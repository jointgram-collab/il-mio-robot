import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE UI E COSTANTI ---
st.set_page_config(page_title="AI SNIPER V11.45 - Definitive", layout="wide")

API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
TARGET_FINALE = 5000.0

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A",
    "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", 
    "soccer_spain_la_liga": "🇪🇸 La Liga",
    "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_uefa_champions_league": "🇪🇺 Champions",
    "soccer_france_ligue_1": "🇫🇷 Ligue 1"
}

BK_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "888sport"]

# --- 2. MOTORE DATABASE (CON PROTEZIONE 429) ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=15)
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
        df['dt_obj'] = pd.to_datetime(df['Data Match'] + f"/{date.today().year}", format="%d/%m %H:%M/%Y", errors='coerce')
        return df.dropna(subset=["Match"])
    except:
        st.warning("⚠️ Google Sheets saturo. Attendi qualche secondo...")
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    if 'dt_obj' in df.columns: df = df.drop(columns=['dt_obj'])
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()
    st.toast("✅ Database Aggiornato!")

# --- 3. AUTO-CHECK RISULTATI ---
def check_results():
    df = carica_db()
    pendenti = df[df['Esito'] == "Pendente"]
    if pendenti.empty: return
    cambiamenti = False
    with st.spinner("🔄 Recupero Score in corso..."):
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

# --- 4. INTERFACCIA ---
st.title("🎯 AI SNIPER V11.45")
df_tot = carica_db()
if 'api_data' not in st.session_state: st.session_state['api_data'] = []

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER ---
with t1:
    match_pendenti = df_tot[df_tot['Esito'] == "Pendente"]['Match'].tolist() if not df_tot.empty else []
    
    with st.sidebar:
        st.header("⚙️ Parametri")
        budget = st.number_input("Cassa (€)", value=250.0)
        kelly = st.slider("Kelly %", 0.05, 0.50, 0.15)
        st.divider()
        st.header("📈 Target Settimana")
        target_s = st.number_input("Goal Match", value=10)
        today = date.today()
        start_w = today - timedelta(days=today.weekday())
        fatte = df_tot[df_tot['dt_obj'].dt.date >= start_w].shape[0] if not df_tot.empty else 0
        st.progress(min(1.0, fatte / target_s))
        st.write(f"Giocate: **{fatte}** | Mancanti: **{max(0, target_s - fatte)}**")

    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    sel_name = st.selectbox("Campionato:", list(leagues.keys()))
    c_btn, c_val = st.columns([1, 3])
    scansiona = c_btn.button("🚀 SCANSIONA")
    soglia_v = c_val.slider("Soglia Valore %", 0, 15, 3) / 100

    if scansiona:
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_name]}/odds/', params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
        if res.status_code == 200: st.session_state['api_data'] = res.json()

    if st.session_state['api_data']:
        for m in st.session_state['api_data']:
            try:
                nome_m = f"{m['home_team']}-{m['away_team']}"
                gia_presente = nome_m in match_pendenti
                date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
                
                opts = []
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == 'totals'), None)
                        if mk:
                            q_o = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), None)
                            q_u = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), None)
                            if q_o and q_u:
                                margin = (1/q_o) + (1/q_u)
                                opts.append({"T": "OVER 2.5", "Q": q_o, "P": ((1/q_o)/margin)+0.05, "BK": b['title']})
                                opts.append({"T": "UNDER 2.5", "Q": q_u, "P": ((1/q_u)/margin)+0.05, "BK": b['title']})
                
                if opts:
                    best = max(opts, key=lambda x: (x['P'] * x['Q']) - 1)
                    val = (best['P'] * best['Q']) - 1
                    if val > soglia_v:
                        col_t, col_b = st.columns([4, 1])
                        if gia_presente:
                            col_t.write(f"📅 {date_m} | {nome_m} | ✅ **IN PORTAFOGLIO**")
                            col_b.button("OK", key=f"ok_{nome_m}", disabled=True)
                        else:
                            col_t.write(f"📅 {date_m} | **{nome_m}** | Valore: **{round(val*100,1)}%**")
                            if col_b.button(f"ADD {best['Q']}", key=f"add_{nome_m}"):
                                stake = round(max(2.0, min(budget * (val/(best['Q']-1)) * kelly, budget*0.1)), 2)
                                n = {"Data Match": date_m, "Match": nome_m, "Scelta": best['T'], "Quota": best['Q'], "Stake": stake, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": leagues[sel_name], "Risultato": "-"}
                                salva_db(pd.concat([carica_db(), pd.DataFrame([n])], ignore_index=True))
                                st.rerun()
                        st.divider()
            except: continue

# --- TAB 2: PORTAFOGLIO ---
with t2:
    st.subheader("💼 Portafoglio Corrente")
    df_p = carica_db()
    pend = df_p[df_p['Esito'] == "Pendente"]
    
    if not pend.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Esposto", f"{round(pend['Stake'].sum(), 2)} €")
        c2.metric("Rientro Lordo", f"{round((pend['Stake'] * pend['Quota']).sum(), 2)} €")
        c3.metric("Possibile Vincita", f"{round((pend['Stake'] * pend['Quota']).sum() - pend['Stake'].sum(), 2)} €")
        
        st.button("🔄 AGGIORNA RISULTATI", on_click=check_results, use_container_width=True)
        st.divider()
        
        for i, r in pend.iterrows():
            col_m, col_b = st.columns([10, 1])
            vinc = round(r['Stake'] * r['Quota'], 2)
            # RIGA UNICA CON SCELTA GRANDE
            riga = f"🗓️ {r['Data Match']} | **{r['Match']}** | <span style='font-size:1.2rem;'>**{r['Scelta']} @{r['Quota']}**</span> | 💰 {r['Stake']}€ | 💸 **{vinc}€** | 🏦 {r['Bookmaker']}"
            col_m.markdown(riga, unsafe_allow_html=True)
            if col_b.button("🗑️", key=f"del_{i}"):
                salva_db(df_p.drop(i)); st.rerun()
            st.divider()
    else:
        st.info("Nessuna scommessa pendente.")

# --- TAB 3: FISCALE ---
with t3:
    st.subheader("📊 Analisi Fiscale & Goal")
    df_f = carica_db()
    if not df_f.empty:
        vinte = df_f[df_f['Esito'] == "VINTO"]
        perso = df_f[df_f['Esito'] == "PERSO"]
        netto = round(vinte['Profitto'].sum() + perso['Profitto'].sum(), 2)
        mancante = round(TARGET_FINALE - netto, 2)
        
        st.info(f"🏆 **Obiettivo: {TARGET_FINALE}€** | Attuale: **{netto}€** | Mancano: **{mancante}€**")
        st.progress(min(1.0, max(0.0, netto / TARGET_FINALE)))
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Tot. Speso", f"{round(df_f['Stake'].sum(), 2)} €")
        m2.metric("Profitto Netto", f"{netto} €", delta=f"{netto}€")
        m3.metric("Win Rate", f"{round((len(vinte)/(len(vinte)+len(perso))*100),1) if (len(vinte)+len(perso))>0 else 0}%")
        
        csv = df_f.to_csv(index=False).encode('utf-8')
        st.download_button("📥 BACKUP DATABASE (CSV)", data=csv, file_name="sniper_stats.csv", mime='text/csv')
        st.divider()

        # STORICO COMPATTO
        for i, row in df_f.sort_index(ascending=False).iterrows():
            dati = f"{row['Data Match']} | **{row['Match']}** | **{row['Scelta']} @{row['Quota']}**"
            if row['Esito'] == "VINTO": st.success(f"🟢 VINTO | {dati} | Score: {row['Risultato']} | +{row['Profitto']}€")
            elif row['Esito'] == "PERSO": st.error(f"🔴 PERSO | {dati} | Score: {row['Risultato']} | {row['Profitto']}€")
            else: st.warning(f"🟡 PENDENTE | {dati} | 💰 Rientro: **{round(row['Stake']*row['Quota'],2)}€**")
