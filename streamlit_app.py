import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="AI SNIPER - Totals & Dates", layout="wide")

# --- FUNZIONI TECNICHE ---
def get_totals_value(q_over, q_under):
    margin = (1/q_over) + (1/q_under)
    return (1/q_over) / margin, (1/q_under) / margin

def calc_stake(prob, quota, budget, frazione):
    valore = (prob * quota) - 1
    if valore <= 0: return 2.0
    importo = budget * (valore / (quota - 1)) * frazione
    return round(max(2.0, min(importo, budget * 0.1)), 2)

# --- INTERFACCIA ---
st.title("⚽ AI SNIPER - Scanner Totals 2.5")

st.sidebar.header("Gestione Cassa")
budget = st.sidebar.number_input("Budget Totale (€)", value=1000.0, step=50.0)
rischio = st.sidebar.slider("Aggressività (Kelly)", 0.05, 0.30, 0.15)
soglia = st.sidebar.slider("Filtro Valore Minimo (%)", 0.0, 10.0, 2.0) / 100

leagues = {
    "ITALIA: Serie A": "soccer_italy_serie_a", "ITALIA: Serie B": "soccer_italy_serie_b",
    "UK: Premier League": "soccer_england_league_1", "UK: Championship": "soccer_england_league_2",
    "SPAGNA: La Liga": "soccer_spain_la_liga", "GERMANIA: Bundesliga": "soccer_germany_bundesliga",
    "EUROPA: Europa League": "soccer_uefa_europa_league", "OLANDA: Eredivisie": "soccer_netherlands_eredivisie"
}

sel_league = st.selectbox("Campionato:", list(leagues.keys()))

if st.button("AVVIA SCANSIONE"):
    API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
    url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/'
    params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals', 'oddsFormat': 'decimal'}
    
    try:
        res = requests.get(url, params=params)
        data = res.json()
        results = []
        
        for m in data:
            home, away = m['home_team'], m['away_team']
            # Formattazione Data
            raw_date = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
            formatted_date = raw_date.strftime("%d/%m %H:%M")
            
            if not m.get('bookmakers'): continue
            
            bk = m['bookmakers'][0]
            mk = next((x for x in bk['markets'] if x['key'] == 'totals'), None)
            if not mk: continue
            
            q_over = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), None)
            q_under = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), None)
            
            if q_over and q_under:
                p_ov_e, p_un_e = get_totals_value(q_over, q_under)
                
                # Modello statistico (Edge 6%)
                opzioni = [
                    {"Tipo": "OVER 2.5", "Quota": q_over, "Prob": p_ov_e + 0.06},
                    {"Tipo": "UNDER 2.5", "Quota": q_under, "Prob": p_un_e + 0.06}
                ]
                
                best = max(opzioni, key=lambda x: (x['Prob'] * x['Quota']) - 1)
                valore_perc = (best['Prob'] * best['Quota']) - 1
                
                if valore_perc > soglia:
                    stake_calcolato = calc_stake(best['Prob'], best['Quota'], budget, rischio)
                    results.append({
                        "Data": formatted_date,
                        "Match": f"{home} - {away}",
                        "Bookmaker": bk['title'],
                        "Esito": best['Tipo'],
                        "Quota": best['Quota'],
                        "Importo (€)": stake_calcolato,
                        "Valore %": round(valore_perc * 100, 2)
                    })
        
        if results:
            df = pd.DataFrame(results).sort_values(by="Valore %", ascending=False)
            st.success(f"Trovate {len(results)} opportunità.")
            
            # Tabella ordinata per Data e Valore
            st.dataframe(df, use_container_width=True)
            
            # Segnale Grafico Rapido
            top = results[0]
            st.warning(f"🚀 **PROSSIMO MATCH DI VALORE:** {top['Data']} | {top['Match']} -> **{top['Esito']}**")
        else:
            st.info("Nessuna partita trovata con questi parametri.")
            
    except Exception as e:
        st.error(f"Errore: {e}")
