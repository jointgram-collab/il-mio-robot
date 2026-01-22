import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- 1. INIZIALIZZAZIONE MEMORIA ---
if 'portafoglio' not in st.session_state:
    st.session_state['portafoglio'] = []
if 'ultimi_risultati' not in st.session_state:
    st.session_state['ultimi_risultati'] = []
if 'campionato_corrente' not in st.session_state:
    st.session_state['campionato_corrente'] = ""

st.set_page_config(page_title="AI SNIPER V9.2 - Full Leagues", layout="wide")

# --- 2. FUNZIONE DI SALVATAGGIO (CALLBACK) ---
def aggiungi_a_portafoglio(match, scelta, quota, stake, bookmaker, data_match):
    giocata = {
        "Data Match": data_match,
        "Match": match,
        "Scelta": scelta,
        "Quota": quota,
        "Stake": stake,
        "Bookmaker": bookmaker,
        "Esito": "Pendente",
        "Profitto": 0.0,
        "Registrato il": datetime.now().strftime("%H:%M:%S")
    }
    st.session_state['portafoglio'].append(giocata)
    st.toast(f"✅ Registrata nel Portafoglio: {match}")

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
st.title("🎯 AI SNIPER - Goal 5.000€")

t1, t2, t3 = st.tabs(["🔍 SCANNER VALORE", "💼 PORTAFOGLIO ATTIVO", "📊 ANDAMENTO FISCALE"])

with t1:
    with st.sidebar:
        st.header("⚙️ Parametri")
        budget = st.number_input("Budget (€)", value=1000.0)
        rischio = st.slider("Aggressività (Kelly)", 0.10, 0.50, 0.25)
        soglia = st.slider("Filtro Valore (%)", 0.0, 10.0, 2.0) / 100
        
        st.divider()
        st.write("**LEGENDA:**")
        st.write("Priorità Bookmaker: Bet365, Snai, Better")

    leagues = {
        "EUROPA: Champions League": "soccer_uefa_champions_league",
        "EUROPA: Europa League": "soccer_uefa_europa_league",
        "EUROPA: Conference League": "soccer_uefa_europa_conference_league",
        "ITALIA: Serie A": "soccer_italy_serie_a", 
        "ITALIA: Serie B": "soccer_italy_serie_b",
        "UK: Premier League": "soccer_england_league_1", 
        "UK: Championship": "soccer_england_league_2",
        "SPAGNA: La Liga": "soccer_spain_la_liga",
        "GERMANIA: Bundesliga": "soccer_germany_bundesliga", 
        "FRANCIA: Ligue 1": "soccer_france_ligue_1",
        "OLANDA: Eredivisie": "soccer_netherlands_eredivisie"
    }
    
    sel_league = st.selectbox("Seleziona Campionato o Coppa:", list(leagues.keys()))

    if st.button("🚀 AVVIA SCANSIONE"):
        API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
        url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/'
        params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals', 'oddsFormat': 'decimal'}
        
        try:
            res = requests.get(url, params=params)
            if res.status_code == 200:
                st.session_state['ultimi_risultati'] = res.json()
                st.session_state['campionato_corrente'] = sel_league
                st.success(f"Scansione {sel_league} completata! Crediti: {res.headers.get('x-requests-remaining')}")
            else:
                st.error("Errore API. Controlla i crediti.")
        except:
            st.error("Errore di connessione.")

    # Visualizzazione Risultati
    if st.session_state['ultimi_risultati']:
        st.write(f"### Risultati per: {st.session_state['campionato_corrente']}")
        priorita = ["Bet365", "Snai", "Better"]
        
        for m in st.session_state['ultimi_risultati']:
            home, away = m['home_team'], m['away_team']
            date_match = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
            
            # Selezione Bookmaker Prioritario
            best_bk = None
            for nome_pref in priorita:
                found = next((b for b in m.get('bookmakers', []) if nome_pref.lower() in b['title'].lower()), None)
                if found:
                    best_bk = found
                    break
            
            if not best_bk and m.get('bookmakers'):
                best_bk = m['bookmakers'][0]
            
            if best_bk:
                mk = next((x for x in best_bk['markets'] if x['key'] == 'totals'), None)
                if mk:
                    q_over = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), 1.0)
                    q_under = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), 1.0)
                    p_ov_e, p_un_e = get_totals_value(q_over, q_under)
                    
                    opzioni = [
                        {"T": "OVER 2.5", "Q": q_over, "P": p_ov_e + 0.07},
                        {"T": "UNDER 2.5", "Q": q_under, "P": p_un_e + 0.07}
                    ]
                    best = max(opzioni, key=lambda x: (x['P'] * x['Q']) - 1)
                    valore = (best['P'] * best['Q']) - 1
                    
                    if valore > soglia:
                        stake = calc_stake(best['P'], best['Q'], budget, rischio)
                        with st.container():
                            c1, c2, c3 = st.columns([3, 2, 1])
                            c1.markdown(f"📅 {date_match}  \n**{home} - {away}**")
                            c2.markdown(f"🎯 **{best['T']}** @ **{best['Q']}** \n🏟️ {best_bk['title']} | Stake: **{stake}€**")
                            
                            c3.button("AGGIUNGI", key=f"btn_{home}_{best['T']}_{best_bk['title']}", 
                                      on_click=aggiungi_a_portafoglio, 
                                      args=(f"{home}-{away}", best['T'], best['Q'], stake, best_bk['title'], date_match))
                            st.divider()

with t2:
    st.subheader("💼 Portafoglio Strategico")
    if st.session_state['portafoglio']:
        for i, b in enumerate(st.session_state['portafoglio']):
            if b['Esito'] == "Pendente":
                with st.expander(f"📌 {b['Match']} - {b['Scelta']} @ {b['Quota']}", expanded=True):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    col1.write(f"Bookmaker: **{b['Bookmaker']}** | Puntata: **{b['Stake']}€**")
                    if col2.button("✅ VINTO", key=f"win_{i}"):
                        st.session_state['portafoglio'][i]['Esito'] = "VINTO"
                        st.session_state['portafoglio'][i]['Profitto'] = round((b['Stake']*b['Quota'])-b['Stake'], 2)
                        st.rerun()
                    if col3.button("❌ PERSO", key=f"loss_{i}"):
                        st.session_state['portafoglio'][i]['Esito'] = "PERSO"
                        st.session_state['portafoglio'][i]['Profitto'] = -b['Stake']
                        st.rerun()
    else:
        st.info("Nessuna giocata attiva. Usa lo Scanner per aggiungere partite.")

with t3:
    st.subheader("📊 Bilancio Fiscale Target 5.000€")
    if st.session_state['portafoglio']:
        df = pd.DataFrame(st.session_state['portafoglio'])
        profitto_netto = df['Profitto'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Profitto Netto", f"{round(profitto_netto, 2)} €")
        m2.metric("Target Residuo", f"{round(5000 - profitto_netto, 2)} €")
        m3.metric("Giocate Chiuse", len(df[df['Esito'] != "Pendente"]))
        
        st.divider()
        st.write("### Storico Operazioni")
        st.dataframe(df, use_container_width=True)
        
        if st.button("🗑️ CANCELLA TUTTO LO STORICO"):
            st.session_state['portafoglio'] = []
            st.rerun()
    else:
        st.info("Inizia a registrare le giocate per vedere le statistiche.")
