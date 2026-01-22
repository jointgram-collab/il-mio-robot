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

# --- FUNZIONI MATEMATICHE ---
def get_poisson_probs(h_exp, a_exp):
    m = np.outer(poisson.pmf(range(7), h_exp), poisson.pmf(range(7), a_exp))
    p1 = np.sum(np.tril(m, -1))
    pX = np.sum(np.diag(m))
    p2 = np.sum(np.triu(m, 1))
    return p1, pX, p2

def calc_stake(prob, quota, budget, frazione):
    if quota <= 1.05: return 0
    val = (prob * quota) - 1
    if val <= 0: return 0
    # Formula di Kelly: Budget * (Vantaggio / (Quota - 1)) * Frazione di rischio
    stake_suggerito = budget * (val / (quota - 1)) * frazione
    return round(max(2.0, stake_suggerito), 2) # Minimo 2€ come per legge

# --- SIDEBAR ---
st.sidebar.title("IMPOSTAZIONI TARGET")
bankroll = st.sidebar.number_input("Budget Attuale (€)", value=1000.0, step=50.0)
frazione_kelly = st.sidebar.slider("Rischio (Kelly)", 0.05, 0.5, 0.15)
soglia_valore = st.sidebar.slider("Filtro Valore (Minimo %)", 0.0, 10.0, 1.0) / 100

leagues_map = {
    "ITALIA: Serie A": "soccer_italy_serie_a", "ITALIA: Serie B": "soccer_italy_serie_b",
    "UK: Premier League": "soccer_england_league_1", "UK: Championship": "soccer_england_league_2",
    "SPAGNA: La Liga": "soccer_spain_la_liga", "GERMANIA: Bundesliga": "soccer_germany_bundesliga",
    "FRANCIA: Ligue 1": "soccer_france_ligue_1", "EUROPA: Europa League": "soccer_uefa_europa_league"
}

tab1, tab2, tab3 = st.tabs(["🔍 SCANNER", "📖 DIARIO", "📊 TARGET"])

with tab1:
    sel_league = st.selectbox("Seleziona Competizione", list(leagues_map.keys()))
    if st.button("AVVIA RICERCA"):
        API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
        url = f'https://api.the-odds-api.com/v4/sports/{leagues_map[sel_league]}/odds/'
        params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'}
        
        try:
            res = requests.get(url, params=params)
            if res.status_code == 200:
                data = res.json()
                st.success(f"Dati Ricevuti! Crediti: {res.headers.get('x-requests-remaining')}")
                found = False
                for m in data:
                    home, away = m['home_team'], m['away_team']
                    if not m.get('bookmakers'): continue
                    
                    bk = m['bookmakers'][0] # Prende il primo bookmaker disponibile
                    bk_name = bk['title']
                    
                    mk_h2h = next((mk for mk in bk['markets'] if mk['key'] == 'h2h'), None)
                    if not mk_h2h: continue
                    
                    q1 = next((o['price'] for o in mk_h2h['outcomes'] if o['name'] == home), 1.0)
                    q2 = next((o['price'] for o in mk_h2h['outcomes'] if o['name'] == away), 1.0)
                    qX = next((o['price'] for o in mk_h2h['outcomes'] if o['name'] == 'Draw'), 1.0)

                    p1, pX, p2 = get_poisson_probs(1.65, 1.25)
                    opzioni = [
                        {"tipo": "1", "q": q1, "v": (p1*q1)-1, "p": p1},
                        {"tipo": "X", "q": qX, "v": (pX*qX)-1, "p": pX},
                        {"tipo": "2", "q": q2, "v": (p2*q2)-1, "p": p2}
                    ]
                    best = max(opzioni, key=lambda x: x['v'])
                    
                    if best['v'] > soglia_valore:
                        found = True
                        stake = calc_stake(best['p'], best['q'], bankroll, frazione_kelly)
                        with st.container():
                            c1, c2, c3 = st.columns([3, 2, 1])
                            c1.markdown(f"⚽ **{home} vs {away}** \n*Bookmaker: {bk_name}*")
                            c2.warning(f"🎯 **SEGNO {best['tipo']}** @ {best['q']}  \n💰 Stake: **{stake}€** (Val: {round(best['v']*100,1)}%)")
                            
                            # Logica di registrazione corretta
                            if c3.button("REGISTRA", key=f"reg_{home}_{best['tipo']}"):
                                st.session_state.diario.append({
                                    "Data": datetime.now().strftime("%d/%m %H:%M"),
                                    "Match": f"{home}-{away}",
                                    "Giocata": best['tipo'],
                                    "Quota": best['q'],
                                    "Stake": stake,
                                    "Bookmaker": bk_name,
                                    "Esito": "IN CORSO",
                                    "Ritorno": 0.0
                                })
                                st.toast(f"Registrato: {home}!")
                                st.rerun()
                if not found: st.info("Nessuna scommessa di valore trovata con i filtri attuali.")
            else: st.error("Errore API.")
        except Exception as e: st.error(f"Errore: {e}")

with tab2:
    if st.session_state.diario:
        for i, b in enumerate(st.session_state.diario):
            with st.expander(f"📌 {b['Match']} - {b['Giocata']} @ {b['Quota']}"):
                st.write(f"Bookmaker: {b['Bookmaker']} | Puntata: {b['Stake']}€")
                c1, c2, c3 = st.columns(3)
                nuovo = c1.selectbox("Cambia Esito", ["IN CORSO", "VINTO", "PERSO"], key=f"sel_{i}")
                if c2.button("AGGIORNA", key=f"upd_{i}"):
                    st.session_state.diario[i]['Esito'] = nuovo
                    st.session_state.diario[i]['Ritorno'] = b['Stake'] * b['Quota'] if nuovo == "VINTO" else 0.0
                    st.rerun()
                if c3.button("ELIMINA", key=f"del_{i}"):
                    st.session_state.diario.pop(i)
                    st.rerun()
    else: st.info("Il tuo diario è vuoto. Registra una giocata dallo Scanner!")

with tab3:
    if st.session_state.diario:
        df = pd.DataFrame(st.session_state.diario)
        conclusi = df[df['Esito'] != 'IN CORSO']
        giocato = conclusi['Stake'].sum()
        vinto = conclusi['Ritorno'].sum()
        netto = vinto - giocato
        
        st.header("📊 Performance Scalata")
        c1, c2 = st.columns(2)
        c1.metric("Profitto Netto", f"{netto:.2f}€", delta=f"{netto:.2f}€")
        c2.metric("Target Rimanente", f"{5000 - (bankroll + netto):.2f}€")
        
        st.subheader("Storico Giocate")
        st.table(df[["Data", "Match", "Giocata", "Quota", "Stake", "Esito"]])
        
        if st.button("SVUOTA DIARIO (RESET TEST)"):
            st.session_state.diario = []
            st.rerun()
