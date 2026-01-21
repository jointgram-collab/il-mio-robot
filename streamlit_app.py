import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime

# --- CONFIGURAZIONE ---
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
st.set_page_config(page_title="AI Pro Scanner & Diario", layout="wide")

# --- INIZIALIZZAZIONE DIARIO (DATABASE TEMPORANEO) ---
if 'diario' not in st.session_state:
    st.session_state.diario = []

# --- FUNZIONI ---
def get_poisson_probs(h_exp, a_exp):
    m = np.outer(poisson.pmf(range(7), h_exp), poisson.pmf(range(7), a_exp))
    return np.sum(np.tril(m, -1)), np.sum(np.diag(m)), np.sum(np.triu(m, 1)), \
           1 - (m[0,0] + m[0,1] + m[0,2] + m[1,0] + m[1,1] + m[2,0]), \
           (1 - poisson.pmf(0, h_exp)) * (1 - poisson.pmf(0, a_exp))

def calc_stake(prob, quota, budget, frazione):
    if quota <= 1: return 0
    value = (prob * quota) - 1
    if value <= 0: return 0
    kelly = value / (quota - 1)
    return round(budget * kelly * frazione, 2)

# --- INTERFACCIA ---
st.title("🤖 AI Terminal & Diario Profitto")

# Sidebar per Budget e Statistiche
st.sidebar.header("💰 Gestione Finanziaria")
bankroll_iniziale = st.sidebar.number_input("Budget Attuale (€)", value=3000)
frazione_kelly = st.sidebar.slider("Rischio (Kelly)", 0.05, 0.5, 0.2)

# Calcolo Statistiche Diario
df_diario = pd.DataFrame(st.session_state.diario)
if not df_diario.empty:
    tot_investito = df_diario['Puntata'].sum()
    tot_vinto = df_diario[df_diario['Esito'] == 'Vinta ✅']['Ritorno'].sum()
    profitto_netto = tot_vinto - df_diario[df_diario['Esito'] != 'In corso ⏳']['Puntata'].sum()
    
    st.sidebar.metric("Profitto Netto", f"{profitto_netto:.2f}€", delta=f"{profitto_netto:.2f}€")
    st.sidebar.progress(min(max(tot_vinto / 5000, 0.0), 1.0), text=f"Progresso Obiettivo 5000€")

# --- SEZIONE SCANNER ---
tab1, tab2 = st.tabs(["🔍 Scanner Mercati", "📖 Diario Giocate"])

with tab1:
    leagues = {"Serie A": "soccer_italy_serie_a", "Serie B": "soccer_italy_serie_b", "Champions": "soccer_uefa_champs_league"}
    sel_league = st.selectbox("Campionato", list(leagues.keys()))
    
    if st.button("Avvia Scansione"):
        url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/'
        params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'h2h,totals', 'oddsFormat': 'decimal'}
        data = requests.get(url, params=params).json()
        
        results = []
        for match in data:
            # Estrazione quote semplificata
            q1 = match['bookmakers'][0]['markets'][0]['outcomes'][0]['price'] if match.get('bookmakers') else 1.0
            p1, pX, p2, pO, pGG = get_poisson_probs(1.6, 1.2)
            stake = calc_stake(p1, q1, bankroll_iniziale, frazione_kelly)
            
            results.append({
                "Match": f"{match['home_team']} - {match['away_team']}",
                "Quota 1": q1,
                "Consiglio": f"Punta {stake}€" if stake > 0 else "No Value",
                "Azione": stake # Usato per il form sotto
            })
        st.table(results)

# --- SEZIONE DIARIO ---
with tab2:
    st.subheader("Registra una nuova scommessa")
    with st.form("add_bet"):
        c1, c2, c3, c4 = st.columns(4)
        m_name = c1.text_input("Partita")
        m_stake = c2.number_input("Importo (€)", min_value=0.0)
        m_quote = c3.number_input("Quota", min_value=1.0)
        m_status = c4.selectbox("Esito", ["In corso ⏳", "Vinta ✅", "Persa ❌"])
        
        if st.form_submit_button("Salva nel Diario"):
            ritorno = m_stake * m_quote if m_status == "Vinta ✅" else 0
            st.session_state.diario.append({
                "Data": datetime.now().strftime("%d/%m %H:%M"),
                "Match": m_name,
                "Puntata": m_stake,
                "Quota": m_quote,
                "Esito": m_status,
                "Ritorno": ritorno
            })
            st.rerun()

    if not df_diario.empty:
        st.write("### Storico Giocate")
        st.dataframe(df_diario, use_container_width=True)
        if st.button("Cancella Diario"):
            st.session_state.diario = []
            st.rerun()
