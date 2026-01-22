import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# --- 1. CONFIGURAZIONE E MEMORIA ---
st.set_page_config(page_title="AI SNIPER V7", layout="wide")

if 'diario' not in st.session_state:
    st.session_state['diario'] = []

# --- 2. FUNZIONI TECNICHE ---
def get_clean_probs(q1, qX, q2):
    # Trova la probabilità reale togliendo il margine del bookmaker
    allibramento = (1/q1) + (1/qX) + (1/q2)
    return (1/q1)/allibramento, (1/qX)/allibramento, (1/q2)/allibramento

def calc_stake(prob, quota, budget, frazione):
    # Formula di Kelly per calcolare l'importo esatto
    val = (prob * quota) - 1
    if val <= 0: return 2.0
    suggerito = budget * (val / (quota - 1)) * frazione
    # Limita l'importo massimo al 10% del budget per sicurezza
    importo = min(suggerito, budget * 0.1)
    return round(max(2.0, importo), 2)

# --- 3. SIDEBAR ---
st.sidebar.title("TARGET 5000€")
bankroll = st.sidebar.number_input("Budget Attuale (€)", value=1000.0)
frazione_kelly = st.sidebar.slider("Rischio (Kelly)", 0.05, 0.5, 0.1)
soglia_valore = st.sidebar.slider("Filtro Valore Minimo (%)", 0.0, 15.0, 2.0) / 100

leagues = {
    "ITALIA: Serie A": "soccer_italy_serie_a", "ITALIA: Serie B": "soccer_italy_serie_b",
    "UK: Premier League": "soccer_england_league_1", "UK: Championship": "soccer_england_league_2",
    "SPAGNA: La Liga": "soccer_spain_la_liga", "GERMANIA: Bundesliga": "soccer_germany_bundesliga",
    "EUROPA: Europa League": "soccer_uefa_europa_league", "OLANDA: Eredivisie": "soccer_netherlands_eredivisie"
}

t1, t2, t3 = st.tabs(["🔍 SCANNER", "📖 DIARIO", "📊 TARGET"])

with t1:
    sel_league = st.selectbox("Scegli Campionato", list(leagues.keys()))
    if st.button("AVVIA SCANSIONE"):
        API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
        url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/'
        params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'}
        
        try:
            res = requests.get(url, params=params)
            if res.status_code == 200:
                data = res.json()
                st.success(f"Scansione OK! Crediti API: {res.headers.get('x-requests-remaining')}")
                
                for m in data:
                    home, away = m['home_team'], m['away_team']
                    if not m.get('bookmakers'): continue
                    
                    bk = m['bookmakers'][0] # Il primo bookmaker della lista
                    bk_name = bk['title']
                    mk = next((x for x in bk['markets'] if x['key'] == 'h2h'), None)
                    if not mk: continue
                    
                    # Estrazione quote
                    q1 = next((o['price'] for o in mk['outcomes'] if o['name'] == home), 1.0)
                    q2 = next((o['price'] for o in mk['outcomes'] if o['name'] == away), 1.0)
                    qX = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Draw'), 1.0)
                    
                    # Calcolo Valore (Edge simulato del 6% per testare il filtro)
                    p1_e, pX_e, p2_e = get_clean_probs(q1, qX, q2)
                    prob_mia = p1_e + 0.06 
                    valore_perc = (prob_mia * q1) - 1
                    
                    if valore_perc > soglia_valore:
                        stake_finale = calc_stake(prob_mia, q1, bankroll, frazione_kelly)
                        
                        with st.container():
                            c1, c2, c3 = st.columns([3, 2, 1])
                            c1.markdown(f"⚽ **{home} - {away}**\n\n*Bookmaker: {bk_name}*")
                            c2.warning(f"🎯 **SEGNO 1** @ **{q1}**\n\n💰 Puntare: **{stake_finale}€**")
                            
                            # ID Unico rinforzato per il salvataggio
                            key_id = f"reg_{home}_{bk_name}_{q1}".replace(" ", "_")
                            if c3.button("REGISTRA", key=key_id):
                                st.session_state['diario'].append({
                                    "Match": f"{home}-{away}",
                                    "Giocata": "1",
                                    "Quota": q1,
                                    "Importo": stake_finale,
                                    "Bookmaker": bk_name,
                                    "Esito": "IN CORSO"
                                })
                                st.toast(f"✅ Registrato: {home}")
                                st.rerun()
                if len(data) == 0:
                    st.info("Nessuna partita disponibile per questo campionato.")
            else:
                st.error(f"Errore API {res.status_code}. Attendi un minuto.")
        except Exception as e:
            st.error(f"Errore tecnico: {e}")

with t2:
    if st.session_state['diario']:
        for i, b in enumerate(st.session_state['diario']):
            with st.expander(f"📍 {b['Match']} ({b['Bookmaker']})"):
                st.write(f"Giocata: **{b['Giocata']}** @ **{b['Quota']}** | Importo: **{b['Importo']}€**")
                if st.button("ELIMINA GIOCATA", key=f"del_{i}"):
                    st.session_state['diario'].pop(i)
                    st.rerun()
    else:
        st.info("Diario vuoto. Registra le tue giocate dallo Scanner.")

with t3:
    if st.session_state['diario']:
        df = pd.DataFrame(st.session_state['diario'])
        st.write("### Riepilogo Schedine")
        st.table(df[["Match", "Bookmaker", "Quota", "Importo", "Esito"]])
        if st.button("SVUOTA TUTTO"):
            st.session_state['diario'] = []
            st.rerun()
