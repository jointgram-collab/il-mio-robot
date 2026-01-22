import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- 1. INIZIALIZZAZIONE MEMORIA ---
if 'portafoglio' not in st.session_state:
    st.session_state['portafoglio'] = []
if 'ultimi_risultati' not in st.session_state:
    st.session_state['ultimi_risultati'] = []

st.set_page_config(page_title="AI SNIPER V9.1 - STABILE", layout="wide")

# --- 2. FUNZIONE DI SALVATAGGIO (CALLBACK) ---
def aggiungi_a_portafoglio(match, scelta, quota, stake, bookmaker, data_match):
    giocata = {
        "Data": data_match,
        "Match": match,
        "Scelta": scelta,
        "Quota": quota,
        "Stake": stake,
        "Bookmaker": bookmaker,
        "Esito": "Pendente",
        "Profitto": 0.0
    }
    st.session_state['portafoglio'].append(giocata)
    st.toast(f"✅ Registrata: {match}")

# --- 3. FUNZIONI TECNICHE ---
def get_totals_value(q_over, q_under):
    margin = (1/q_over) + (1/q_under)
    return (1/q_over) / margin, (1/q_under) / margin

def calc_stake(prob, quota, budget, frazione):
    valore = (prob * quota) - 1
    if valore <= 0: return 2.0
    importo = budget * (valore / (quota - 1)) * frazione
    return round(max(2.0, min(importo, budget * 0.1)), 2)

# --- 4. INTERFACCIA ---
st.title("⚽ AI SNIPER V9 - Portfolio Mode")

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    st.sidebar.header("Parametri")
    budget = st.sidebar.number_input("Cassa (€)", value=1000.0)
    rischio = st.sidebar.slider("Kelly", 0.10, 0.50, 0.25)
    soglia = st.sidebar.slider("Valore (%)", 0.0, 10.0, 2.0) / 100

    leagues = {
        "ITALIA: Serie A": "soccer_italy_serie_a",
        "UK: Premier League": "soccer_england_league_1",
        "EUROPA: Champions League": "soccer_uefa_champions_league"
    }
    sel_league = st.selectbox("Campionato", list(leagues.keys()))

    if st.button("AVVIA SCANSIONE"):
        API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
        url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/'
        params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals', 'oddsFormat': 'decimal'}
        
        res = requests.get(url, params=params)
        if res.status_code == 200:
            st.session_state['ultimi_risultati'] = res.json()
            st.success("Scansione completata!")
        else:
            st.error("Errore API")

    # Mostra i risultati memorizzati
    if st.session_state['ultimi_risultati']:
        priorita = ["Bet365", "Snai", "Better"]
        for m in st.session_state['ultimi_risultati']:
            home, away = m['home_team'], m['away_team']
            date_match = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
            
            # Logica Bookmaker
            best_bk = next((b for p in priorita for b in m.get('bookmakers', []) if p.lower() in b['title'].lower()), None)
            if not best_bk and m.get('bookmakers'): best_bk = m['bookmakers'][0]
            
            if best_bk:
                mk = next((x for x in best_bk['markets'] if x['key'] == 'totals'), None)
                if mk:
                    q_over = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), 1.0)
                    q_under = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), 1.0)
                    p_ov_e, p_un_e = get_totals_value(q_over, q_under)
                    
                    opzioni = [{"T": "OVER 2.5", "Q": q_over, "P": p_ov_e + 0.07}, {"T": "UNDER 2.5", "Q": q_under, "P": p_un_e + 0.07}]
                    best = max(opzioni, key=lambda x: (x['P'] * x['Q']) - 1)
                    valore = (best['P'] * best['Q']) - 1
                    
                    if valore > soglia:
                        stake = calc_stake(best['P'], best['Q'], budget, rischio)
                        c1, c2, c3 = st.columns([3, 2, 1])
                        c1.write(f"📅 {date_match}\n**{home}-{away}**")
                        c2.write(f"🎯 {best['T']} @{best['Q']}\nBook: {best_bk['title']}")
                        
                        # USO DI ON_CLICK PER EVITARE IL RESET
                        c3.button("AGGIUNGI", key=f"btn_{home}_{best['T']}", 
                                  on_click=aggiungi_a_portafoglio, 
                                  args=(f"{home}-{away}", best['T'], best['Q'], stake, best_bk['title'], date_match))

with t2:
    st.subheader("💼 Portafoglio Attivo")
    if st.session_state['portafoglio']:
        for i, b in enumerate(st.session_state['portafoglio']):
            if b['Esito'] == "Pendente":
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.write(f"📌 {b['Match']} | **{b['Scelta']}** @{b['Quota']} ({b['Stake']}€)")
                if col2.button("✅", key=f"w_{i}"):
                    st.session_state['portafoglio'][i]['Esito'] = "VINTO"
                    st.session_state['portafoglio'][i]['Profitto'] = round((b['Stake']*b['Quota'])-b['Stake'], 2)
                    st.rerun()
                if col3.button("❌", key=f"l_{i}"):
                    st.session_state['portafoglio'][i]['Esito'] = "PERSO"
                    st.session_state['portafoglio'][i]['Profitto'] = -b['Stake']
                    st.rerun()
    else:
        st.info("Aggiungi giocate dallo Scanner.")

with t3:
    if st.session_state['portafoglio']:
        df = pd.DataFrame(st.session_state['portafoglio'])
        st.metric("Profitto Totale", f"{round(df['Profitto'].sum(), 2)} €")
        st.dataframe(df, use_container_width=True)
        if st.button("RESET DATI"):
            st.session_state['portafoglio'] = []
            st.rerun()
