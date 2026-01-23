import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="AI SNIPER V11.12", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

BK_URLS = {
    "Bet365": "https://www.bet365.it", "Snai": "https://www.snai.it",
    "Better": "https://www.lottomatica.it/scommesse", "Planetwin365": "https://www.planetwin365.it",
    "Eurobet": "https://www.eurobet.it", "Goldbet": "https://www.goldbet.it", "Sisal": "https://www.sisal.it"
}

def get_bk_link(name):
    url = BK_URLS.get(name, f"https://www.google.com/search?q={name}")
    return f"[{name}]({url})"

# --- FUNZIONI CORE ---
def carica_db():
    try:
        return conn.read(worksheet="Giocate", ttl="0").dropna(how='all')
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key"])

def salva_db(df):
    conn.update(worksheet="Giocate", data=df)

def get_totals_value(q_over, q_under):
    margin = (1/q_over) + (1/q_under)
    return (1/q_over) / margin, (1/q_under) / margin

def calc_stake(prob, quota, budget, frazione):
    valore = (prob * quota) - 1
    if valore <= 0: return 2.0
    importo = budget * (valore / (quota - 1)) * frazione
    return round(max(2.0, min(importo, budget * 0.1)), 2)

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11.12")

t1, t2, t3 = st.tabs(["🔍 SCANNER VALORE", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    with st.sidebar:
        st.header("⚙️ Parametri")
        budget_cassa = st.number_input("Budget (€)", value=250.0)
        rischio = st.slider("Aggressività (Kelly)", 0.1, 0.5, 0.25)
        soglia_val = st.slider("Soglia Valore %", 0, 15, 3) / 100
        
    leagues = {
        "ITALIA: Serie A": "soccer_italy_serie_a", "ITALIA: Serie B": "soccer_italy_serie_b",
        "UK: Premier League": "soccer_england_league_1", "SPAGNA: La Liga": "soccer_spain_la_liga",
        "GERMANIA: Bundesliga": "soccer_germany_bundesliga", "EUROPA: Champions": "soccer_uefa_champions_league",
        "EUROPA: Europa League": "soccer_uefa_europa_league", "FRANCIA: Ligue 1": "soccer_france_ligue_1"
    }
    sel_league = st.selectbox("Seleziona Campionato:", list(leagues.keys()))

    if st.button("🚀 AVVIA SCANSIONE"):
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/', 
                           params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
        if res.status_code == 200: 
            st.session_state['api_data'] = res.json()
            st.session_state['api_rem'] = res.headers.get('x-requests-remaining')
        else:
            st.error("Errore API: Controlla la tua chiave o il limite.")

    if 'api_rem' in st.session_state:
        st.write(f"💳 **Credito Residuo API:** {st.session_state['api_rem']}")

    if st.session_state.get('api_data'):
        for m in st.session_state['api_data']:
            home, away = m['home_team'], m['away_team']
            date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
            bk = m['bookmakers'][0] if m.get('bookmakers') else None
            if bk:
                mk = next((x for x in bk['markets'] if x['key'] == 'totals'), None)
                if mk:
                    q_ov = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), 1.0)
                    q_un = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), 1.0)
                    p_ov_e, p_un_e = get_totals_value(q_ov, q_un)
                    best = {"T": "OVER 2.5", "Q": q_ov, "P": p_ov_e + 0.06} if q_ov > q_un else {"T": "UNDER 2.5", "Q": q_un, "P": p_un_e + 0.06}
                    valore_perc = round(((best['P'] * best['Q']) - 1) * 100, 2)
                    
                    if valore_perc/100 > soglia_val:
                        stake = calc_stake(best['P'], best['Q'], budget_cassa, rischio)
                        poss_v = round(stake * best['Q'], 2)
                        col1, col2, col3 = st.columns([3, 2, 1])
                        col1.write(f"📅 **{date_m}**\n**{home}-{away}**\nBK: {get_bk_link(bk['title'])}")
                        col2.warning(f"🎯 {best['T']} @{best['Q']} | 💎 **+{valore_perc}%**")
                        col2.write(f"Stake: **{stake}€** | Vincita: **{poss_v}€**")
                        u_key = f"add_{home}_{date_m}_{best['Q']}".replace(" ", "_")
                        if col3.button("ADD", key=u_key):
                            nuova = {"Data Match": date_m, "Match": f"{home}-{away}", "Scelta": best['T'], "Quota": best['Q'], "Stake": stake, "Bookmaker": bk['title'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": leagues[sel_league]}
                            salva_db(pd.concat([carica_db(), pd.DataFrame([nuova])], ignore_index=True))
                            st.toast("Aggiunto!")

with t2:
    st.subheader("💼 Portafoglio Cloud")
    df_p = carica_db()
    pendenti = df_p[df_p['Esito'] == "Pendente"]
    
    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Esposizione Attuale", f"{round(pendenti['Stake'].sum(), 2)} €")
    col_m2.metric("Ritorno Atteso", f"{round((pendenti['Stake'] * pendenti['Quota']).sum(), 2)} €")
    st.write("---")
    
    for i, r in pendenti.iterrows():
        vinc_pot = round(r['Stake'] * r['Quota'], 2)
        with st.container():
            col_a, col_b, col_c = st.columns([3, 2, 1])
            col_a.write(f"📅 {r['Data Match']}\n**{r['Match']}**\n{r['Scelta']} @{r['Quota']} ({r['Bookmaker']})")
            col_b.write(f"Puntati: **{r['Stake']}€**\nVincita: **{vinc_pot}€**")
            if col_c.button("🗑️", key=f"del_p_{i}"):
                salva_db(df_p.drop(i)); st.rerun()
            st.divider()

with t3:
    st.subheader("📊 Fiscale & Obiettivi")
    df_f = carica_db()
    if not df_f.empty:
        prof_netto = round(df_f['Profitto'].sum(), 2)
        vinti = df_f[df_f['Esito'] == "VINTO"]
        tot_vinto_lordo = round((vinti['Stake'] * vinti['Quota']).sum(), 2)
        
        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric("Profitto Netto", f"{prof_netto} €")
        c_m2.metric("Totale Incassato", f"{tot_vinto_lordo} €")
        c_m3.metric("Mancante a 5k", f"{round(5000-prof_netto, 2)} €")
        
        st.write("### 📜 Storico Completo")
        for i, row in df_f.iterrows():
            status = "🟢" if row['Esito'] == "VINTO" else "🔴" if row['Esito'] == "PERSO" else "⏳"
            st.write(f"{status} **{row['Match']}** ({row['Data Match']}): {row['Profitto']}€")
