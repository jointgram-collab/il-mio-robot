import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="AI SNIPER V11.10 - Full Dashboard", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

# --- MAPPA URL BOOKMAKERS ---
BK_URLS = {
    "Bet365": "https://www.bet365.it", "Snai": "https://www.snai.it",
    "Better": "https://www.lottomatica.it/scommesse", "Planetwin365": "https://www.planetwin365.it",
    "Eurobet": "https://www.eurobet.it", "Goldbet": "https://www.goldbet.it", "Sisal": "https://www.sisal.it"
}

def get_bk_link(name):
    url = BK_URLS.get(name, f"https://www.google.com/search?q={name}")
    return f"[{name}]({url})"

# --- FUNZIONI DATABASE ---
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl="0")
        return df.dropna(how='all')
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key"])

def salva_db_completo(df):
    conn.update(worksheet="Giocate", data=df)

# --- AUTO-CHECK RISULTATI ---
def check_results():
    df = carica_db()
    pendenti = df[df['Esito'] == "Pendente"]
    if pendenti.empty:
        st.info("Nessuna giocata pendente.")
        return

    cambiamenti = False
    with st.spinner("🔄 Interrogazione API Score..."):
        for sport_key in pendenti['Sport_Key'].unique():
            url_scores = f'https://api.the-odds-api.com/v4/sports/{sport_key}/scores/'
            res = requests.get(url_scores, params={'api_key': API_KEY, 'daysFrom': 3})
            if res.status_code == 200:
                scores_data = res.json()
                for i, r in pendenti[pendenti['Sport_Key'] == sport_key].iterrows():
                    m_res = next((m for m in scores_data if (f"{m['home_team']}-{m['away_team']}" == r['Match']) and m.get('completed')), None)
                    if m_res:
                        total_goals = sum(int(s['score']) for s in m_res['scores'])
                        vinto = (r['Scelta'] == "OVER 2.5" and total_goals > 2.5) or (r['Scelta'] == "UNDER 2.5" and total_goals < 2.5)
                        df.at[i, 'Esito'] = "VINTO" if vinto else "PERSO"
                        df.at[i, 'Profitto'] = round((r['Stake']*r['Quota'])-r['Stake'], 2) if vinto else -r['Stake']
                        cambiamenti = True
    if cambiamenti:
        salva_db_completo(df)
        st.success("Database aggiornato con i risultati reali!")
        st.rerun()

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11.10")

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    with st.sidebar:
        st.header("⚙️ Impostazioni")
        budget_cassa = st.number_input("Budget Iniziale (€)", value=250.0)
        rischio = st.slider("Aggressività", 0.10, 0.50, 0.25)
        
    leagues = {"Serie A": "soccer_italy_serie_a", "Champions League": "soccer_uefa_champions_league", "Premier League": "soccer_england_league_1"}
    sel_league = st.selectbox("Campionato:", list(leagues.keys()))

    if st.button("🚀 CERCA VALORE"):
        url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/'
        res = requests.get(url, params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
        if res.status_code == 200: st.session_state['api_res'] = res.json()

    if st.session_state.get('api_res'):
        for m in st.session_state['api_res']:
            home, away = m['home_team'], m['away_team']
            date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
            bk = m['bookmakers'][0] if m.get('bookmakers') else None
            if bk:
                mk = next((x for x in bk['markets'] if x['key'] == 'totals'), None)
                if mk:
                    q_ov = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), 1.0)
                    # Calcolo rapido Kelly (Semplificato)
                    stake = round(budget_cassa * 0.05, 2) # Esempio fisso 5% per test
                    poss_vincita = round(stake * q_ov, 2)
                    
                    c1, c2, c3 = st.columns([3, 2, 1])
                    c1.write(f"📅 {date_m}\n**{home}-{away}**\nBK: {get_bk_link(bk['title'])}")
                    c2.info(f"🎯 OVER 2.5 @{q_ov}\n💰 Stake: {stake}€ | 💸 Vincita: **{poss_vincita}€**")
                    
                    u_key = f"add_{home}_{date_m}_{q_ov}".replace(" ", "_")
                    if c3.button("AGGIUNGI", key=u_key):
                        nuova = {"Data Match": date_m, "Match": f"{home}-{away}", "Scelta": "OVER 2.5", "Quota": q_ov, "Stake": stake, "Bookmaker": bk['title'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": leagues[sel_league]}
                        df_agg = pd.concat([carica_db(), pd.DataFrame([nuova])], ignore_index=True)
                        salva_db_completo(df_agg)
                        st.toast("Salvato nel Cloud!")

with t2:
    st.subheader("💼 Portafoglio Cloud")
    if st.button("🔄 AUTO-CHECK RISULTATI"): check_results()
    df_p = carica_db()
    pendenti = df_p[df_p['Esito'] == "Pendente"]
    st.metric("Totale Scommesso (Esposizione)", f"{round(pendenti['Stake'].sum(), 2)} €")
    st.write("---")
    for i, r in pendenti.iterrows():
        st.write(f"⏳ {r['Match']} - {r['Scelta']} @{r['Quota']} su {r['Bookmaker']}")

with t3:
    st.subheader("📊 Resoconto Fiscale")
    df_f = carica_db()
    if not df_f.empty:
        vinti = df_f[df_f['Esito'] == "VINTO"]
        prof_netto = round(df_f['Profitto'].sum(), 2)
        tot_vinto_lordo = round((vinti['Stake'] * vinti['Quota']).sum(), 2)
        
        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric("Profitto Netto", f"{prof_netto} €")
        c_m2.metric("Totale Vinto (Lordo)", f"{tot_vinto_lordo} €")
        c_m3.metric("Target 5k", f"{round(5000-prof_netto, 2)} €")
        
        st.write("### 📜 Storico Operazioni")
        for i, row in df_f.iterrows():
            status = "🟢" if row['Esito'] == "VINTO" else "🔴" if row['Esito'] == "PERSO" else "⏳"
            st.write(f"{status} **{row['Match']}**: {row['Profitto']}€ (Quota @{row['Quota']})")
