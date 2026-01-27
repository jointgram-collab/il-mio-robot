import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date, timedelta
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V11.41 - Dual Mode", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
TARGET_FINALE = 5000.0

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "888sport"]

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", "soccer_england_efl_championship": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Championship",
    "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie", "soccer_spain_la_liga": "🇪🇸 La Liga",
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

# --- AUTO-CHECK RISULTATI (Aggiornato per Gol/NoGol) ---
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
                        s1, s2 = int(s[0]['score']), int(s[1]['score'])
                        score_str = f"{s1}-{s2}"
                        
                        # Logica Esito
                        vinto = False
                        if r['Scelta'] == "OVER 2.5": vinto = (s1 + s2) > 2.5
                        elif r['Scelta'] == "UNDER 2.5": vinto = (s1 + s2) < 2.5
                        elif r['Scelta'] == "GOL": vinto = s1 > 0 and s2 > 0
                        elif r['Scelta'] == "NO GOL": vinto = s1 == 0 or s2 == 0
                        
                        df.at[i, 'Esito'] = "VINTO" if vinto else "PERSO"
                        df.at[i, 'Risultato'] = score_str
                        df.at[i, 'Profitto'] = round((r['Stake']*r['Quota'])-r['Stake'], 2) if vinto else -r['Stake']
                        cambiamenti = True
    if cambiamenti: salva_db(df); st.rerun()

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11.41 - Dual Mode")
if 'api_data' not in st.session_state: st.session_state['api_data'] = []

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    df_tot = carica_db()
    match_pendenti = df_tot[df_tot['Esito'] == "Pendente"]['Match'].tolist()

    with st.sidebar:
        st.header("⚙️ Parametri")
        budget_cassa = st.number_input("Budget (€)", value=250.0)
        rischio = st.slider("Kelly", 0.05, 0.50, 0.20)
        soglia_val = st.slider("Valore Min %", 0, 15, 5) / 100
        st.divider()
        st.markdown("### 📥 Backup")
        csv_data = df_tot.to_csv(index=False).encode('utf-8')
        st.download_button("DOWNLOAD CSV", data=csv_data, file_name="backup.csv", mime='text/csv')
        uploaded = st.file_uploader("RIPRISTINA CSV", type="csv")
        if uploaded:
            if st.button("CONFERMA UPLOAD"):
                salva_db(pd.read_csv(uploaded)); st.rerun()

    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    c_camp, c_merc = st.columns(2)
    sel_name = c_camp.selectbox("Campionato:", list(leagues.keys()))
    sel_market = c_merc.selectbox("Mercato:", ["Over/Under 2.5", "Gol/No Gol"])
    
    # Mapping mercati API
    api_market = "totals" if sel_market == "Over/Under 2.5" else "btts"

    if st.button("🚀 AVVIA SCANSIONE DUAL"):
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_name]}/odds/', params={'api_key': API_KEY, 'regions': 'eu', 'markets': api_market})
        if res.status_code == 200: st.session_state['api_data'] = res.json()

    if st.session_state['api_data']:
        for m in st.session_state['api_data']:
            try:
                nome_match = f"{m['home_team']}-{m['away_team']}"
                date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
                opts = []
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_EURO_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == api_market), None)
                        if mk:
                            # Logica dinamica per estrarre quote
                            if api_market == "totals":
                                q_1 = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), None)
                                q_2 = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), None)
                                label_1, label_2 = "OVER 2.5", "UNDER 2.5"
                            else: # btts
                                q_1 = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Yes'), None)
                                q_2 = next((o['price'] for o in mk['outcomes'] if o['name'] == 'No'), None)
                                label_1, label_2 = "GOL", "NO GOL"
                            
                            if q_1 and q_2:
                                margin = (1/q_1) + (1/q_2)
                                opts.append({"T": label_1, "Q": q_1, "P": ((1/q_1)/margin)+0.06, "BK": b['title']})
                                opts.append({"T": label_2, "Q": q_2, "P": ((1/q_2)/margin)+0.06, "BK": b['title']})
                
                if opts:
                    best = max(opts, key=lambda x: (x['P'] * x['Q']) - 1)
                    val = round(((best['P'] * best['Q']) - 1) * 100, 2)
                    if val/100 > soglia_val:
                        col_txt, col_btn = st.columns([3, 1])
                        if nome_match in match_pendenti:
                            col_txt.write(f"📅 {date_m} | {nome_match} | ✅ **IN LISTA**")
                        else:
                            col_txt.write(f"📅 {date_m} | **{nome_match}** | {best['BK']}")
                            if col_btn.button(f"ADD {best['T']} @{best['Q']} (+{val}%)", key=f"add_{nome_match}_{best['T']}"):
                                val_k = (best['P'] * best['Q']) - 1
                                stake = round(max(2.0, min(budget_cassa * (val_k/(best['Q']-1)) * rischio, budget_cassa*0.15)), 2)
                                n = {"Data Match": date_m, "Match": nome_match, "Scelta": best['T'], "Quota": best['Q'], "Stake": stake, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": leagues[sel_name], "Risultato": "-"}
                                salva_db(pd.concat([carica_db(), pd.DataFrame([n])], ignore_index=True))
                                st.rerun()
                        st.divider()
            except: continue

# --- TAB 2 & 3: Rimasti identici alla tua versione 11.39/40 per stabilità ---
with t2:
    st.subheader("💼 Portafoglio Pendente")
    df_p = carica_db()
    pend = df_p[df_p['Esito'] == "Pendente"]
    st.button("🔄 AGGIORNA RISULTATI", on_click=check_results, use_container_width=True)
    st.dataframe(pend, use_container_width=True)

with t3:
    st.subheader("📊 Analisi Fiscale")
    df_f = carica_db()
    if not df_f.empty:
        netto = round(df_f['Profitto'].sum(), 2)
        st.info(f"🏆 Goal: {TARGET_FINALE}€ | Attuale: {netto}€")
        st.progress(min(1.0, max(0.0, netto / TARGET_FINALE)))
        st.dataframe(df_f.sort_index(ascending=False), use_container_width=True)
