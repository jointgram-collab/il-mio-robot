import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V11.17 - Professional Default", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

# --- LISTA BOOKMAKER AUTORIZZATI EUROPA ---
BK_EURO_AUTH = {
    "Bet365": "https://www.bet365.it", "Snai": "https://www.snai.it",
    "Better": "https://www.lottomatica.it/scommesse", "Planetwin365": "https://www.planetwin365.it",
    "Eurobet": "https://www.eurobet.it", "Goldbet": "https://www.goldbet.it", 
    "Sisal": "https://www.sisal.it", "Bwin": "https://www.bwin.it",
    "William Hill": "https://www.williamhill.it", "888sport": "https://www.888sport.it"
}

def get_bk_link(name):
    url = BK_EURO_AUTH.get(name, f"https://www.google.com/search?q={name}")
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
    return round(max(2.0, min(importo, budget * 0.15)), 2) # Limite max 15% per sicurezza

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11.17")

t1, t2, t3 = st.tabs(["🔍 SCANNER VALORE", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    with st.sidebar:
        st.header("⚙️ Parametri Ottimizzati")
        # --- IMPOSTAZIONE DEFAULT PROFESSIONALI ---
        budget_cassa = st.number_input("Budget (€)", value=250.0)
        rischio = st.slider("Aggressività (Kelly Frazionario)", 0.05, 0.50, 0.20) # Default 0.20
        soglia_val = st.slider("Soglia Valore Minima %", 0, 15, 5) / 100 # Default 5%
        
    leagues = {
        "ITALIA: Serie A": "soccer_italy_serie_a", "ITALIA: Serie B": "soccer_italy_serie_b",
        "UK: Premier League": "soccer_england_league_1", "SPAGNA: La Liga": "soccer_spain_la_liga",
        "GERMANIA: Bundesliga": "soccer_germany_bundesliga", "EUROPA: Champions": "soccer_uefa_champions_league",
        "EUROPA: Europa League": "soccer_uefa_europa_league", "FRANCIA: Ligue 1": "soccer_france_ligue_1"
    }
    sel_league = st.selectbox("Campionato:", list(leagues.keys()))

    if st.button("🚀 AVVIA SCANSIONE"):
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/', 
                           params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
        if res.status_code == 200:
            st.session_state['api_data'] = res.json()
            st.session_state['api_rem'] = res.headers.get('x-requests-remaining')

    if 'api_rem' in st.session_state:
        st.write(f"💳 **Credito API:** {st.session_state['api_rem']}")

    if st.session_state.get('api_data'):
        for m in st.session_state['api_data']:
            try:
                home, away = m['home_team'], m['away_team']
                date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
                
                valid_options = []
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_EURO_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == 'totals'), None)
                        if mk:
                            q_ov = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), None)
                            q_un = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), None)
                            if q_ov and q_un:
                                p_ov_e, p_un_e = get_totals_value(q_ov, q_un)
                                # Robot edge: +6% di precisione stimata sui totals
                                valid_options.append({"T": "OVER 2.5", "Q": q_ov, "P": p_ov_e + 0.06, "BK": b['title']})
                                valid_options.append({"T": "UNDER 2.5", "Q": q_un, "P": p_un_e + 0.06, "BK": b['title']})
                
                if valid_options:
                    best = max(valid_options, key=lambda x: (x['P'] * x['Q']) - 1)
                    val_perc = round(((best['P'] * best['Q']) - 1) * 100, 2)
                    
                    if val_perc/100 > soglia_val:
                        stake = calc_stake(best['P'], best['Q'], budget_cassa, rischio)
                        poss_v = round(stake * best['Q'], 2)
                        
                        col1, col2, col3 = st.columns([3, 2, 1])
                        col1.write(f"📅 **{date_m}**\n**{home}-{away}**\nBK: {get_bk_link(best['BK'])}")
                        col2.write(f"🎯 {best['T']} @{best['Q']} | 💎 **+{val_perc}%**\nStake: **{stake}€** | Vincita: **{poss_v}€**")
                        
                        u_key = f"add_{home}_{date_m}_{best['Q']}_{best['BK']}".replace(" ","_")
                        if col3.button("ADD", key=u_key):
                            nuova = {"Data Match": date_m, "Match": f"{home}-{away}", "Scelta": best['T'], "Quota": best['Q'], "Stake": stake, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": leagues[sel_league]}
                            salva_db(pd.concat([carica_db(), pd.DataFrame([nuova])], ignore_index=True))
                            st.toast(f"✅ Ottimizzato su {best['BK']}!")
                        st.divider()
            except Exception: continue

with t2:
    st.subheader("💼 Portafoglio")
    df_p = carica_db()
    pendenti = df_p[df_p['Esito'] == "Pendente"]
    c1, c2 = st.columns(2)
    c1.metric("Esposizione", f"{round(pendenti['Stake'].sum(), 2)} €")
    c2.metric("Ritorno Atteso", f"{round((pendenti['Stake'] * pendenti['Quota']).sum(), 2)} €")
    st.write("---")
    for i, r in pendenti.iterrows():
        col_a, col_b, col_c = st.columns([3, 2, 1])
        col_a.write(f"📅 **{r['Data Match']}**\n**{r['Match']}**\n{r['Scelta']} @{r['Quota']} ({r['Bookmaker']})")
        col_b.write(f"Stake: **{r['Stake']}€**\nPotenziale: **{round(r['Stake']*r['Quota'], 2)}€**")
        if col_c.button("🗑️", key=f"del_p_{i}"):
            salva_db(df_p.drop(i)); st.rerun()

with t3:
    st.subheader("📊 Fiscale")
    df_f = carica_db()
    if not df_f.empty:
        prof = round(df_f['Profitto'].sum(), 2)
        st.metric("Profitto Netto", f"{prof} €", delta=f"{round(5000-prof, 2)}€ al target")
        for i, row in df_f.iterrows():
            st.write(f"{'🟢' if row['Esito']=='VINTO' else '🔴' if row['Esito']=='PERSO' else '⏳'} **{row['Match']}**: {row['Profitto']}€")
