import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="AI SNIPER V11.22 - Ironclad Edition", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

BK_EURO_AUTH = {
    "Bet365": "https://www.bet365.it", "Snai": "https://www.snai.it",
    "Better": "https://www.lottomatica.it/scommesse", "Planetwin365": "https://www.planetwin365.it",
    "Eurobet": "https://www.eurobet.it", "Goldbet": "https://www.goldbet.it", 
    "Sisal": "https://www.sisal.it", "Bwin": "https://www.bwin.it",
    "William Hill": "https://www.williamhill.it", "888sport": "https://www.888sport.it"
}

# --- MOTORE DI DATABASE PROTETTO ---
def carica_db():
    try:
        # Lettura diretta senza cache per la massima precisione
        df = conn.read(worksheet="Giocate", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
        return df.dropna(subset=["Match"])
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def aggiungi_giocata(nuova_riga_dict):
    db_attuale = carica_db()
    nuova_riga_df = pd.DataFrame([nuova_riga_dict])
    # Protezione: Uniamo i dati assicurandoci di non perdere il pregresso
    db_completo = pd.concat([db_attuale, nuova_riga_df], ignore_index=True)
    conn.update(worksheet="Giocate", data=db_completo)
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

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11.22")

t1, t2, t3 = st.tabs(["🔍 SCANNER VALORE", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    with st.sidebar:
        st.header("⚙️ Parametri")
        budget_cassa = st.number_input("Budget (€)", value=250.0)
        rischio = st.slider("Aggressività (Kelly)", 0.05, 0.50, 0.20)
        soglia_val = st.slider("Soglia Valore %", 0, 15, 5) / 100
        
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

    if st.session_state.get('api_data'):
        for m in st.session_state['api_data']:
            try:
                home, away = m['home_team'], m['away_team']
                date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
                
                # Selezione miglior quota EU...
                valid_options = []
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_EURO_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == 'totals'), None)
                        if mk:
                            q_ov = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), None)
                            q_un = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), None)
                            if q_ov and q_un:
                                p_ov_e, p_un_e = get_totals_value(q_ov, q_un)
                                valid_options.append({"T": "OVER 2.5", "Q": q_ov, "P": p_ov_e + 0.06, "BK": b['title']})
                                valid_options.append({"T": "UNDER 2.5", "Q": q_un, "P": p_un_e + 0.06, "BK": b['title']})
                
                if valid_options:
                    best = max(valid_options, key=lambda x: (x['P'] * x['Q']) - 1)
                    val_perc = round(((best['P'] * best['Q']) - 1) * 100, 2)
                    
                    if (val_perc/100) > soglia_val:
                        stake_calc = calc_stake(best['P'], best['Q'], budget_cassa, rischio)
                        c1, c2, c3 = st.columns([3, 2, 1])
                        c1.write(f"📅 **{date_m}**\n**{home}-{away}**\nBK: {best['BK']}")
                        c2.write(f"🎯 {best['T']} @{best['Q']} (+{val_perc}%)\nStake: **{stake_calc}€**")
                        if c3.button("ADD", key=f"btn_{home}_{date_m}"):
                            nuova_giocata = {
                                "Data Match": date_m, "Match": f"{home}-{away}", "Scelta": best['T'],
                                "Quota": best['Q'], "Stake": stake_calc, "Bookmaker": best['BK'],
                                "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": leagues[sel_league], "Risultato": "-"
                            }
                            aggiungi_giocata(nuova_giocata)
                            st.toast("✅ Salvataggio sicuro completato!")
                        st.divider()
            except: continue

with t2:
    st.subheader("💼 Portafoglio")
    df_p = carica_db()
    pendenti = df_p[df_p['Esito'] == "Pendente"]
    for i, r in pendenti.iterrows():
        col_a, col_b, col_c = st.columns([3, 2, 1])
        col_a.write(f"📅 **{r['Data Match']}**\n**{r['Match']}**\n{r['Scelta']} @{r['Quota']}")
        col_b.write(f"Stake: **{r['Stake']}€**")
        if col_c.button("🗑️", key=f"del_{i}"):
            df_p = df_p.drop(i)
            conn.update(worksheet="Giocate", data=df_p)
            st.rerun()

with t3:
    st.subheader("📊 Fiscale")
    df_f = carica_db()
    if not df_f.empty:
        # Calcolo Win Rate e Profitto
        prof_n = round(df_f['Profitto'].sum(), 2)
        st.metric("Profitto Netto", f"{prof_n} €")
        st.dataframe(df_f.sort_index(ascending=False))
