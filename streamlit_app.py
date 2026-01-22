import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="AI SNIPER V7.1", layout="wide")

if 'diario' not in st.session_state:
    st.session_state['diario'] = []

def get_clean_probs(q1, qX, q2):
    allibramento = (1/q1) + (1/qX) + (1/q2)
    return (1/q1)/allibramento, (1/qX)/allibramento, (1/q2)/allibramento

def calc_stake(prob, quota, budget, frazione):
    val = (prob * quota) - 1
    if val <= 0: return 2.0
    importo = budget * (val / (quota - 1)) * frazione
    return round(max(2.0, min(importo, budget * 0.1)), 2)

# --- SIDEBAR ---
st.sidebar.title("TARGET 5000€")
bankroll = st.sidebar.number_input("Budget (€)", value=1000.0)
frazione_kelly = st.sidebar.slider("Rischio Kelly", 0.05, 0.5, 0.1)
soglia_valore = st.sidebar.slider("Filtro Valore Minimo (%)", 0.0, 15.0, 2.0) / 100

leagues = {
    "ITALIA: Serie A": "soccer_italy_serie_a", "ITALIA: Serie B": "soccer_italy_serie_b",
    "UK: Premier League": "soccer_england_league_1", "UK: Championship": "soccer_england_league_2",
    "SPAGNA: La Liga": "soccer_spain_la_liga", "GERMANIA: Bundesliga": "soccer_germany_bundesliga",
    "EUROPA: Europa League": "soccer_uefa_europa_league"
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
                st.success(f"Scansione OK! Partite trovate: {len(data)}")
                
                for m in data:
                    home, away = m['home_team'], m['away_team']
                    if not m.get('bookmakers'): continue
                    bk = m['bookmakers'][0]
                    bk_name = bk['title']
                    mk = next((x for x in bk['markets'] if x['key'] == 'h2h'), None)
                    if not mk: continue
                    
                    q1 = next((o['price'] for o in mk['outcomes'] if o['name'] == home), 1.0)
                    q2 = next((o['price'] for o in mk['outcomes'] if o['name'] == away), 1.0)
                    qX = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Draw'), 1.0)
                    
                    p1_e, pX_e, p2_e = get_clean_probs(q1, qX, q2)
                    
                    # Analizziamo tutti e 3 i segni con un edge simulato del 6%
                    opzioni = [
                        {"tipo": "1", "q": q1, "p_mia": p1_e + 0.06},
                        {"tipo": "X", "q": qX, "p_mia": pX_e + 0.06},
                        {"tipo": "2", "q": q2, "p_mia": p2_e + 0.06}
                    ]
                    
                    # Troviamo il segno con il valore più alto
                    best = max(opzioni, key=lambda x: (x['p_mia'] * x['q']) - 1)
                    valore_perc = (best['p_mia'] * best['q']) - 1
                    
                    if valore_perc > soglia_valore:
                        stake = calc_stake(best['p_mia'], best['q'], bankroll, frazione_kelly)
                        with st.container():
                            c1, c2, c3 = st.columns([3, 2, 1])
                            c1.markdown(f"⚽ **{home} - {away}**\n\n*Book: {bk_name}*")
                            c2.warning(f"🎯 **SEGNO {best['tipo']}** @ **{best['q']}**\n\n💰 Stake: **{stake}€** (Valore: {round(valore_perc*100,1)}%)")
                            
                            key_id = f"reg_{home}_{best['tipo']}_{bk_name}".replace(" ", "_")
                            if c3.button("REGISTRA", key=key_id):
                                st.session_state['diario'].append({
                                    "Match": f"{home}-{away}", "Giocata": best['tipo'],
                                    "Quota": best['q'], "Importo": stake, "Bookmaker": bk_name, "Esito": "IN CORSO"
                                })
                                st.toast("✅ Salvato!")
                                st.rerun()
            else: st.error("Errore API")
        except Exception as e: st.error(f"Errore: {e}")

with t2:
    if st.session_state['diario']:
        for i, b in enumerate(st.session_state['diario']):
            st.write(f"📝 {b['Match']} | **{b['Giocata']}** @ {b['Quota']} | {b['Importo']}€ ({b['Bookmaker']})")
    else: st.info("Diario vuoto.")

with t3:
    if st.session_state['diario']:
        st.table(pd.DataFrame(st.session_state['diario']))
