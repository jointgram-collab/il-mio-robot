import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V11.40 - COMPLETE", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
TARGET_FINALE = 5000.0

if 'api_usage' not in st.session_state:
    st.session_state['api_usage'] = {'remaining': "N/D", 'used': "N/D"}
if 'api_data' not in st.session_state:
    st.session_state['api_data'] = []

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "William Hill", "888sport"]

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie",
    "soccer_spain_la_liga": "🇪🇸 La Liga", "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_uefa_champions_league": "🇪🇺 Champions", "soccer_france_ligue_1": "🇫🇷 Ligue 1"
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

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11.40")
df_attuale = carica_db()

with st.sidebar:
    st.header("📊 Stato API")
    c1, c2 = st.columns(2)
    c1.metric("Residui", st.session_state['api_usage']['remaining'])
    c2.metric("Usati", st.session_state['api_usage']['used'])
    st.divider()
    budget_cassa = st.number_input("Budget (€)", value=250.0)
    rischio = st.slider("Kelly", 0.05, 0.50, 0.20)
    soglia_val = st.slider("Valore Min %", 0, 15, 5) / 100

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER ---
with t1:
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    sel_name = st.selectbox("Campionato:", list(leagues.keys()))
    if st.button("🚀 AVVIA SCANSIONE", use_container_width=True):
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_name]}/odds/', params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
        if res.status_code == 200:
            st.session_state['api_usage']['remaining'] = res.headers.get('x-requests-remaining', "N/D")
            st.session_state['api_usage']['used'] = res.headers.get('x-requests-used', "N/D")
            st.session_state['api_data'] = res.json()
            st.rerun()

    if st.session_state['api_data']:
        pend_list = df_attuale[df_attuale['Esito'] == "Pendente"]['Match'].tolist()
        for m in st.session_state['api_data']:
            try:
                nome_m = f"{m['home_team']}-{m['away_team']}"
                dt_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
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
                        stk_c = round(max(2.0, min(budget_cassa * (val/(best['Q']-1)) * rischio, budget_cassa*0.15)), 2)
                        c_a, c_b = st.columns([3, 1])
                        is_p = " ✅" if nome_m in pend_list else ""
                        c_a.write(f"📅 {dt_m} | **{nome_m}** | {best['BK']} | Val: **{round(val*100,1)}%** | Suggerito: **{stk_c}€**{is_p}")
                        if c_b.button(f"ADD @{best['Q']}", key=f"add_{nome_m}", disabled=(nome_m in pend_list)):
                            nuova = pd.DataFrame([{"Data Match": dt_m, "Match": nome_m, "Scelta": best['T'], "Quota": best['Q'], "Stake": stk_c, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": leagues[sel_name], "Risultato": "-"}])
                            salva_db(pd.concat([carica_db(), nuova], ignore_index=True))
                            st.rerun()
                        st.divider()
            except: continue

# --- TAB 2: PORTAFOGLIO ---
with t2:
    st.subheader("💼 Scommesse in Corso")
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"]
    if not df_p.empty:
        for i, r in df_p.iterrows():
            vinc_p = round(r['Stake'] * r['Quota'], 2)
            c1, c2 = st.columns([12, 1])
            c1.warning(f"🏟️ **{r['Match']}** | {r['Scelta']} @**{r['Quota']}** | Stake: **{r['Stake']}€** | Vincita: **{vinc_p}€** | 🏦 {r['Bookmaker']}")
            if c2.button("🗑️", key=f"del_{i}"):
                salva_db(df_attuale.drop(i))
                st.rerun()
            st.divider()
    else: st.write("Nessuna giocata pendente.")

# --- TAB 3: FISCALE ---
with t3:
    st.subheader("🏁 Cruscotto Finanziario")
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
    st.write("### 💾 Gestione Backup")
    exp_col, imp_col = st.columns(2)
    with exp_col:
        csv_data = df_attuale.to_csv(index=False).encode('utf-8')
        st.download_button("📥 ESPORTA CSV", data=csv_data, file_name=f"sniper_backup_{date.today()}.csv", use_container_width=True)
    with imp_col:
        up_file = st.file_uploader("📤 Importa CSV", type="csv")
        if up_file and st.button("🔄 RIPRISTINA DATI"):
            salva_db(pd.read_csv(up_file))
            st.rerun()

    st.divider()
    def color_row(row):
        if row['Esito'] == "VINTO": return ['background-color: rgba(0, 255, 0, 0.15)'] * len(row)
        if row['Esito'] == "PERSO": return ['background-color: rgba(255, 0, 0, 0.15)'] * len(row)
        if row['Esito'] == "Pendente": return ['background-color: rgba(255, 255, 0, 0.15)'] * len(row)
        return [''] * len(row)

    if not df_attuale.empty:
        st.write("### Storico Operazioni")
        view_df = df_attuale[["Data Match", "Match", "Scelta", "Quota", "Stake", "Esito", "Profitto", "Risultato", "Bookmaker"]]
        st.dataframe(view_df.sort_index(ascending=False).style.apply(color_row, axis=1), use_container_width=True)
