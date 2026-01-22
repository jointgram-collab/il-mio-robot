import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="AI SNIPER PRO", layout="wide", initial_sidebar_state="expanded")

# --- CSS PER GRAFICA ACCATTIVANTE ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1f2937; padding: 15px; border-radius: 10px; border: 1px solid #374151; }
    .value-box { background-color: #059669; color: white; padding: 20px; border-radius: 10px; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- INIZIALIZZAZIONE DIARIO ---
if 'diario' not in st.session_state:
    st.session_state.diario = []

# --- FUNZIONI TECNICHE ---
def get_poisson_probs(h_exp, a_exp):
    m = np.outer(poisson.pmf(range(7), h_exp), poisson.pmf(range(7), a_exp))
    return np.sum(np.tril(m, -1)), np.sum(np.diag(m)), np.sum(np.triu(m, 1)), \
           1 - (m[0,0] + m[0,1] + m[0,2] + m[1,0] + m[1,1] + m[2,0]), \
           (1 - poisson.pmf(0, h_exp)) * (1 - poisson.pmf(0, a_exp))

def calc_stake(prob, quota, budget, frazione):
    if quota <= 1.05: return 0
    val = (prob * quota) - 1
    if val <= 0: return 0
    return round(budget * (val / (quota - 1)) * frazione, 2)

# --- SIDEBAR STATISTICHE ---
st.sidebar.title("MENU PRO")
bankroll = st.sidebar.number_input("Capitale Attuale (Euro)", value=1000)
frazione_kelly = st.sidebar.slider("Livello Rischio", 0.05, 0.5, 0.2)

df_diario = pd.DataFrame(st.session_state.diario)
profitto_totale = 0
if not df_diario.empty:
    vincite = df_diario[df_diario['Esito'] == 'VINTO']['Ritorno'].sum()
    perdite = df_diario[df_diario['Esito'] == 'PERSO']['Puntata'].sum()
    profitto_totale = vincite - perdite

st.sidebar.divider()
st.sidebar.metric("PROFITTO NETTO", f"{profitto_totale:.2f} EUR")
st.sidebar.progress(min(max((profitto_totale + 1000) / 5000, 0.0), 1.0), text="Verso i 5000 Euro")

# --- INTERFACCIA PRINCIPALE ---
tab1, tab2, tab3 = st.tabs(["SCANNER LIVE", "DIARIO GIOCATE", "ANALISI TARGET"])

with tab1:
    st.header("Ricerca Opportunita di Mercato")
    leagues = {
        "ITALIA Serie A": "soccer_italy_serie_a", "ITALIA Serie B": "soccer_italy_serie_b",
        "EUROPA Champions": "soccer_uefa_champs_league", "EUROPA Europa League": "soccer_uefa_europa_league",
        "UK Premier League": "soccer_england_league_1", "UK Championship": "soccer_england_league_2",
        "GERMANIA Bundesliga": "soccer_germany_bundesliga", "SPAGNA La Liga": "soccer_spain_la_liga"
    }
    sel_league = st.selectbox("Seleziona il Campionato da analizzare", list(leagues.keys()))
    
    if st.button("AVVIA SCANSIONE INTELLIGENTE"):
        API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
        url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/'
        params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'h2h,totals,btts', 'oddsFormat': 'decimal'}
        
        try:
            data = requests.get(url, params=params).json()
            results = []
            for m in data:
                # Estrazione quote (logica semplificata per velocita)
                q1 = m['bookmakers'][0]['markets'][0]['outcomes'][0]['price'] if m.get('bookmakers') else 1.0
                p1, pX, p2, pO, pGG = get_poisson_probs(1.65, 1.25)
                
                # Calcolo Value migliore
                valore = (p1 * q1) - 1
                if valore > 0.05:
                    stake = calc_stake(p1, q1, bankroll, frazione_kelly)
                    results.append({
                        "PARTITA": f"{m['home_team']} - {m['away_team']}",
                        "GIOCATA CONSIGLIATA": f"SEGNO 1 (Quota {q1})",
                        "IMPORTO DA PUNTARE": f"{stake} EUR",
                        "VALORE ATTESO": f"+{round(valore*100,1)}%"
                    })
            
            if results:
                st.table(pd.DataFrame(results).style.set_properties(**{'background-color': '#059669', 'color': 'white'}))
            else:
                st.info("Nessuna anomalia trovata nelle quote attuali.")
        except:
            st.error("Errore di connessione API.")

with tab2:
    st.header("Registro Scommesse Effettuate")
    with st.form("nuova_giocata"):
        c1, c2, c3, c4 = st.columns(4)
        match = c1.text_input("Partita")
        puntata = c2.number_input("Puntata (EUR)", min_value=0.0)
        quota = c3.number_input("Quota Giocata", min_value=1.0)
        esito = c4.selectbox("Esito", ["IN CORSO", "VINTO", "PERSO"])
        
        if st.form_submit_button("REGISTRA SCOMMESSA"):
            ritorno = puntata * quota if esito == "VINTO" else 0
            st.session_state.diario.append({
                "Data": datetime.now().strftime("%d/%m"),
                "Match": match,
                "Puntata": puntata,
                "Quota": quota,
                "Esito": esito,
                "Ritorno": ritorno
            })
            st.rerun()

    if not df_diario.empty:
        st.dataframe(df_diario, use_container_width=True)

with tab3:
    st.header("Analisi Verso Obiettivo 5000 Euro")
    st.write(f"Capitale Iniziale: 1000 EUR | Profitto Attuale: {profitto_totale} EUR")
    # Qui potresti aggiungere un grafico dell'andamento
