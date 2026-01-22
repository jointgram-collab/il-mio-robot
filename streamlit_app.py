import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="AI SNIPER GLOBAL PRO", layout="wide")

if 'diario' not in st.session_state:
    st.session_state.diario = []

# --- FUNZIONI ---
def get_poisson_probs(h_exp, a_exp):
    m = np.outer(poisson.pmf(range(7), h_exp), poisson.pmf(range(7), a_exp))
    p1 = np.sum(np.tril(m, -1))
    pX = np.sum(np.diag(m))
    p2 = np.sum(np.triu(m, 1))
    p_over = 1 - (m[0,0] + m[0,1] + m[0,2] + m[1,0] + m[1,1] + m[2,0])
    p_gg = (1 - poisson.pmf(0, h_exp)) * (1 - poisson.pmf(0, a_exp))
    return p1, pX, p2, p_over, p_gg

def calc_stake(prob, quota, budget, frazione):
    if quota <= 1.05: return 0
    val = (prob * quota) - 1
    if val <= 0: return 0
    return round(budget * (val / (quota - 1)) * frazione, 2)

# --- SIDEBAR ---
st.sidebar.title("TARGET 5000 EURO")
bankroll = st.sidebar.number_input("Budget Attuale (€)", value=1000)
frazione_kelly = st.sidebar.slider("Rischio (Kelly)", 0.05, 0.5, 0.15)
soglia_valore = st.sidebar.slider("Filtro Valore (Minimo %)", 0.0, 10.0, 1.0) / 100

# --- MAPPA CAMPIONATI COMPLETA ---
leagues_map = {
    "ITALIA: Serie A": "soccer_italy_serie_a", 
    "ITALIA: Serie B": "soccer_italy_serie_b",
    "EUROPA: Champions League": "soccer_uefa_champs_league", 
    "EUROPA: Europa League": "soccer_uefa_europa_league",
    "UK: Premier League": "soccer_england_league_1", 
    "UK: Championship": "soccer_england_league_2",
    "UK: League One": "soccer_england_league_3",
    "GERMANIA: Bundesliga": "soccer_germany_bundesliga",
    "GERMANIA: Bundesliga 2": "soccer_germany_bundesliga_2",
    "SPAGNA: La Liga": "soccer_spain_la_liga", 
    "SPAGNA: La Liga 2": "soccer_spain_segunda_division",
    "FRANCIA: Ligue 1": "soccer_france_ligue_1",
    "FRANCIA: Ligue 2": "soccer_france_ligue_2",
    "OLANDA: Eredivisie": "soccer_netherlands_eredivisie"
}

tab1, tab2, tab3 = st.tabs(["🔍 SCANNER", "📖 DIARIO", "📊 TARGET"])

with tab1:
    sel_league = st.selectbox("Seleziona Competizione", list(leagues_map.keys()))
    if st.button("AVVIA RICERCA"):
        API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
        # Chiediamo solo H2H inizialmente per evitare l'errore 422
        url = f'https://api.the-odds-api.com/v4/sports/{leagues_map[sel_league]}/odds/'
        params = {
            'api_key': API_KEY, 
            'regions': 'eu', 
            'markets': 'h2h', # Solo il mercato principale per stabilità
            'oddsFormat': 'decimal'
        }
        
        try:
            res = requests.get(url, params=params)
            if res.status_code == 422:
                st.error("Errore 422: Questo campionato non ha mercati attivi in questo momento. Prova Premier League o Serie A.")
            elif res.status_code != 200:
                st.error(f"Errore API {res.status_code}")
            else:
                data = res.json()
                if not data:
                    st.warning("Nessuna partita trovata.")
                else:
                    st.success(f"Dati Ricevuti! Crediti: {res.headers.get('x-requests-remaining')}")
                    found = False
                    for m in data:
                        home, away = m['home_team'], m['away_team']
                        if not m.get('bookmakers'): continue
                        bk = m['bookmakers'][0]
                        
                        # Estraiamo la quota 1X2 in sicurezza
                        mk_h2h = next((mk for mk in bk['markets'] if mk['key'] == 'h2h'), None)
                        if not mk_h2h: continue
                        
                        q1 = next((o['price'] for o in mk_h2h['outcomes'] if o['name'] == home), 1.0)
                        q2 = next((o['price'] for o in mk_h2h['outcomes'] if o['name'] == away), 1.0)
                        qX = next((o['price'] for o in mk_h2h['outcomes'] if o['name'] == 'Draw'), 1.0)

                        # Per i test usiamo Poisson su 1X2
                        p1, pX, p2, pO, pGG = get_poisson_probs(1.65, 1.25)
                        
                        # Cerchiamo valore sui 3 segni principali
                        opzioni = [
                            {"tipo": "1", "q": q1, "v": (p1*q1)-1, "p": p1},
                            {"tipo": "X", "q": qX, "v": (pX*qX)-1, "p": pX},
                            {"tipo": "2", "q": q2, "v": (p2*q2)-1, "p": p2}
                        ]
                        best = max(opzioni, key=lambda x: x['v'])
                        
                        if best['v'] > soglia_valore:
                            found = True
                            stake = calc_stake(best['p'], best['q'], bankroll, frazione_kelly)
                            col_a, col_b = st.columns([3, 1])
                            col_a.write(f"⚽ **{home}-{away}** | {best['tipo']} @ {best['q']} (Val: {round(best['v']*100,1)}%)")
                            if col_b.button("REGISTRA", key=f"btn_{home}_{best['tipo']}"):
                                st.session_state.diario.append({"Match": f"{home}-{away}", "Giocata": best['tipo'], "Quota": best['q'], "Stake": stake, "Esito": "IN CORSO"})
                                st.rerun()

with tab2:
    if st.session_state.diario:
        for i, b in enumerate(st.session_state.diario):
            with st.expander(f"{b['Match']} - {b['Giocata']} ({b['Esito']})"):
                col_e, col_s, col_d = st.columns(3)
                nuovo = col_e.selectbox("Esito", ["IN CORSO", "VINTO", "PERSO"], key=f"esito_{i}")
                if col_s.button("SALVA", key=f"save_{i}"):
                    st.session_state.diario[i]['Esito'] = nuovo
                    st.session_state.diario[i]['Ritorno'] = b['Stake'] * b['Quota'] if nuovo == "VINTO" else 0
                    st.rerun()
                if col_d.button("ELIMINA", key=f"del_{i}"):
                    st.session_state.diario.pop(i)
                    st.rerun()
    else: st.info("Diario vuoto.")

with tab3:
    if st.session_state.diario:
        df = pd.DataFrame(st.session_state.diario)
        giocato = df['Stake'].sum()
        vinto = df['Ritorno'].sum()
        st.metric("P/L NETTO", f"{vinto - giocato:.2f}€", delta=f"{vinto - giocato:.2f}€")
        st.dataframe(df)
