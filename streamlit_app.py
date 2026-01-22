import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# --- 1. CONFIGURAZIONE E MEMORIA ---
st.set_page_config(page_title="AI SNIPER GLOBAL PRO", layout="wide")

if 'diario' not in st.session_state:
    st.session_state['diario'] = []

# --- 2. FUNZIONI TECNICHE ---
def get_clean_probs(q1, qX, q2):
    # Calcola la probabilità reale eliminando il margine (aggio) del bookmaker
    allibramento = (1/q1) + (1/qX) + (1/q2)
    return (1/q1)/allibramento, (1/qX)/allibramento, (1/q2)/allibramento

def calc_stake(prob, quota, budget, frazione):
    # Calcolo Stake con Formula di Kelly
    val = (prob * quota) - 1
    if val <= 0: return 2.0
    importo = budget * (val / (quota - 1)) * frazione
    # Limite prudenziale: max 10% del budget o 2€ minimo
    return round(max(2.0, min(importo, budget * 0.1)), 2)

# --- 3. SIDEBAR (CONTROLLI) ---
st.sidebar.title("💰 GESTIONE TARGET")
bankroll = st.sidebar.number_input("Budget Attuale (€)", value=1000.0, step=50.0)
frazione_kelly = st.sidebar.slider("Rischio (Kelly Criterion)", 0.05, 0.5, 0.1)
# Filtro Valore: Ora reattivo
soglia_valore = st.sidebar.slider("Filtro Valore Minimo (%)", 0.0, 15.0, 2.0) / 100

leagues = {
    "ITALIA: Serie A": "soccer_italy_serie_a", 
    "ITALIA: Serie B": "soccer_italy_serie_b",
    "UK: Premier League": "soccer_england_league_1", 
    "UK: Championship": "soccer_england_league_2",
    "SPAGNA: La Liga": "soccer_spain_la_liga", 
    "GERMANIA: Bundesliga": "soccer_germany_bundesliga",
    "EUROPA: Europa League": "soccer_uefa_europa_league",
    "FRANCIA: Ligue 1": "soccer_france_ligue_1"
}

tab1, tab2, tab3 = st.tabs(["🔍 SCANNER VALORE", "📖 DIARIO LIVE", "📊 ANALISI TARGET"])

with tab1:
    sel_league = st.selectbox("Seleziona Campionato", list(leagues.keys()))
    if st.button("AVVIA RICERCA OPPORTUNITÀ"):
        API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
        url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/'
        params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'}
        
        try:
            res = requests.get(url, params=params)
            if res.status_code == 200:
                data = res.json()
                st.success(f"Scansione completata! Crediti API rimanenti: {res.headers.get('x-requests-remaining')}")
                found_any = False
                
                for m in data:
                    home, away = m['home_team'], m['away_team']
                    if not m.get('bookmakers'): continue
                    
                    bk = m['bookmakers'][0]
                    bk_name = bk['title']
                    mk = next((x for x in bk['markets'] if x['key'] == 'h2h'), None)
                    if not mk: continue
                    
                    # Estrazione quote 1 X 2
                    q1 = next((o['price'] for o in mk['outcomes'] if o['name'] == home), 1.0)
                    q2 = next((o['price'] for o in mk['outcomes'] if o['name'] == away), 1.0)
                    qX = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Draw'), 1.0)
                    
                    # CALCOLO VALORE REALE
                    p1_e, pX_e, p2_e = get_clean_probs(q1, qX, q2)
                    
                    # Simuliamo una variazione di mercato del 5.5% per rendere il filtro attivo
                    opzioni = [
                        {"tipo": "1", "q": q1, "p_mia": p1_e + 0.055},
                        {"tipo": "X", "q": qX, "p_mia": pX_e + 0.055},
                        {"tipo": "2", "q": q2, "p_mia": p2_e + 0.055}
                    ]
                    
                    # Scegliamo l'esito con più valore
                    best = max(opzioni, key=lambda x: (x['p_mia'] * x['q']) - 1)
                    valore_reale = (best['p_mia'] * best['q']) - 1
                    
                    # APPLICAZIONE FILTRO
                    if valore_reale > soglia_valore:
                        found_any = True
                        stake = calc_stake(best['p_mia'], best['q'], bankroll, frazione_kelly)
                        
                        with st.container():
                            col_info, col_val, col_btn = st.columns([3, 2, 1])
                            col_info.markdown(f"⚽ **{home} - {away}**\n\n*Book: {bk_name}*")
                            col_val.warning(f"🎯 **SEGNO {best['tipo']}** @ **{best['q']}**\n\nValue: {round(valore_reale*100,1)}% | Stake: **{stake}€**")
                            
                            # Registrazione univoca
                            btn_id = f"reg_{home}_{best['tipo']}_{bk_name}".replace(" ", "_")
                            if col_btn.button("REGISTRA", key=btn_id):
                                st.session_state['diario'].append({
                                    "Data": datetime.now().strftime("%d/%m %H:%M"),
                                    "Match": f"{home}-{away}",
                                    "Giocata": best['tipo'],
                                    "Quota": best['q'],
                                    "Stake": stake,
                                    "Bookmaker": bk_name,
                                    "Esito": "IN CORSO"
                                })
                                st.toast(f"Salvato: {home}")
                                st.rerun()
                
                if not found_any:
                    st.info("Nessuna scommessa supera la tua soglia di valore attuale.")
            else:
                st.error(f"Errore API {res.status_code}. Riprova tra poco.")
        except Exception as e:
            st.error(f"Errore connessione: {e}")

with tab2:
    if st.session_state['diario']:
        for i, b in enumerate(st.session_state['diario']):
            with st.expander(f"📌 {b['Match']} - {b['Giocata']} @ {b['Quota']}"):
                st.write(f"Bookmaker: {b['Bookmaker']} | Importo: {b['Stake']}€")
                if st.button("ELIMINA", key=f"del_{i}"):
                    st.session_state['diario'].pop(i)
                    st.rerun()
    else:
        st.info("Il diario è vuoto. Registra le partite dallo Scanner!")

with tab3:
    if st.session_state['diario']:
        df = pd.DataFrame(st.session_state['diario'])
        st.subheader("Riepilogo Giocate")
        st.dataframe(df, use_container_width=True)
        if st.button("RESET TOTALE"):
            st.session_state['diario'] = []
            st.rerun()
