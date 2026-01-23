import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="AI SNIPER V11.9 - Auto & Fixed", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

# --- MAPPA URL BOOKMAKERS ---
BK_URLS = {"Bet365": "https://www.bet365.it", "Snai": "https://www.snai.it", "Better": "https://www.lottomatica.it/scommesse", "Planetwin365": "https://www.planetwin365.it", "Eurobet": "https://www.eurobet.it", "Goldbet": "https://www.goldbet.it", "Sisal": "https://www.sisal.it"}

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

def salva_giocata(nuova_giocata):
    df_attuale = carica_db()
    df_finale = pd.concat([df_attuale, pd.DataFrame([nuova_giocata])], ignore_index=True)
    salva_db_completo(df_finale)

# --- AUTO-CHECK RISULTATI ---
def check_results():
    df = carica_db()
    pendenti = df[df['Esito'] == "Pendente"]
    if pendenti.empty:
        st.info("Nessuna giocata pendente da controllare.")
        return

    cambiamenti = False
    with st.spinner("Verifica risultati in corso..."):
        for sport_key in pendenti['Sport_Key'].unique():
            url_scores = f'https://api.the-odds-api.com/v4/sports/{sport_key}/scores/'
            res = requests.get(url_scores, params={'api_key': API_KEY, 'daysFrom': 3})
            if res.status_code == 200:
                scores_data = res.json()
                for i, r in pendenti[pendenti['Sport_Key'] == sport_key].iterrows():
                    match_res = next((m for m in scores_data if (f"{m['home_team']}-{m['away_team']}" == r['Match']) and m.get('completed')), None)
                    
                    if match_res:
                        total_goals = sum(int(s['score']) for s in match_res['scores'])
                        vinto = (r['Scelta'] == "OVER 2.5" and total_goals > 2.5) or (r['Scelta'] == "UNDER 2.5" and total_goals < 2.5)
                        df.at[i, 'Esito'] = "VINTO" if vinto else "PERSO"
                        df.at[i, 'Profitto'] = round((r['Stake']*r['Quota'])-r['Stake'], 2) if vinto else -r['Stake']
                        cambiamenti = True
    
    if cambiamenti:
        salva_db_completo(df)
        st.success("Risultati aggiornati!")
        st.rerun()
    else:
        st.warning("Nessun match completato trovato.")

# --- LOGICA TECNICA ---
def get_totals_value(q_over, q_under):
    margin = (1/q_over) + (1/q_under)
    return (1/q_over) / margin, (1/q_under) / margin

def calc_stake(prob, quota, budget, frazione):
    valore = (prob * quota) - 1
    if valore <= 0: return 2.0
    importo = budget * (valore / (quota - 1)) * frazione
    return round(max(2.0, min(importo, budget * 0.1)), 2)

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11.9")

if 'ultimi_risultati' not in st.session_state:
    st.session_state['ultimi_risultati'] = []

t1, t2, t3 = st.tabs(["🔍 SCANNER VALORE", "💼 PORTAFOGLIO", "📊 ANDAMENTO FISCALE"])

with t1:
    with st.sidebar:
        st.header("⚙️ Parametri")
        budget_cassa = st.number_input("Cassa (€)", value=250.0)
        rischio = st.slider("Aggressività (Kelly)", 0.10, 0.50, 0.25)
        soglia = st.slider("Filtro Valore (%)", 0.0, 10.0, 2.0) / 100
        
    leagues = {
        "EUROPA: Champions League": "soccer_uefa_champions_league",
        "ITALIA: Serie A": "soccer_italy_serie_a", 
        "UK: Premier League": "soccer_england_league_1",
        "SPAGNA: La Liga": "soccer_spain_la_liga"
    }
    sel_league = st.selectbox("Campionato:", list(leagues.keys()))

    if st.button("🚀 AVVIA SCANSIONE"):
        url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/'
        res = requests.get(url, params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
        if res.status_code == 200:
            st.session_state['ultimi_risultati'] = res.json()

    if st.session_state['ultimi_risultati']:
        for m in st.session_state['ultimi_risultati']:
            home, away = m['home_team'], m['away_team']
            date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
            bk = m['bookmakers'][0] if m.get('bookmakers') else None
            
            if bk:
                mk = next((x for x in bk['markets'] if x['key'] == 'totals'), None)
                if mk:
                    q_ov = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), 1.0)
                    q_un = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), 1.0)
                    p_ov_e, p_un_e = get_totals_value(q_ov, q_un)
                    best = {"T": "OVER 2.5", "Q": q_ov, "P": p_ov_e + 0.07} if q_ov > q_un else {"T": "UNDER 2.5", "Q": q_un, "P": p_un_e + 0.07}
                    
                    if ((best['P'] * best['Q']) - 1) > soglia:
                        stake = calc_stake(best['P'], best['Q'], budget_cassa, rischio)
                        c1, c2, c3 = st.columns([3, 2, 1])
                        c1.write(f"📅 {date_m}\n**{home}-{away}**")
                        c2.write(f"🎯 {best['T']} @{best['Q']}\n💰 Stake: {stake}€")
                        
                        # CHIAVE UNICA COMPLESSA PER IL BOTTONE
                        unique_key = f"add_{home}_{date_m}_{best['Q']}".replace(" ", "_")
                        if c3.button("ADD", key=unique_key):
                            salva_giocata({"Data Match": date_m, "Match": f"{home}-{away}", "Scelta": best['T'], "Quota": best['Q'], "Stake": stake, "Bookmaker": bk['title'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": leagues[sel_league]})
                            st.toast("✅ Aggiunto!")

with t2:
    st.subheader("💼 Portafoglio Cloud")
    if st.button("🔄 VERIFICA RISULTATI API"):
        check_results()
    
    df_p = carica_db()
    pendenti = df_p[df_p['Esito'] == "Pendente"]
    for i, r in pendenti.iterrows():
        with st.expander(f"⏳ {r['Match']} - {r['Stake']}€"):
            st.write(f"Puntata: {r['Scelta']} @{r['Quota']} su {r['Bookmaker']}")
            if st.button("ELIMINA", key=f"del_p_{i}"):
                df_p = df_p.drop(i)
                salva_db_completo(df_p); st.rerun()

with t3:
    st.subheader("📊 Storico & Andamento")
    df_f = carica_db()
    if not df_f.empty:
        st.metric("Profitto Netto", f"{round(df_f['Profitto'].sum(), 2)} €")
        for i, row in df_f.iterrows():
            # Pallino dinamico
            status = "🟢" if row['Esito'] == "VINTO" else "🔴" if row['Esito'] == "PERSO" else "⏳"
            c1, c2, c3 = st.columns([1, 4, 1])
            c1.write(status)
            c2.write(f"**{row['Match']}** | {row['Scelta']} @{row['Quota']} ({row['Bookmaker']})")
            c3.write(f"**{row['Profitto']}€**")
            if st.button("🗑️", key=f"del_f_{i}"):
                df_f = df_f.drop(i)
                salva_db_completo(df_f); st.rerun()
