import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="AI SNIPER - Priority Bookmakers", layout="wide")

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
st.title("⚽ AI SNIPER - Under/Over 2.5 (Priorità Bookmaker)")
st.info("Priorità impostata su: **Bet365, Snai, Better**")

st.sidebar.header("Gestione Cassa")
budget = st.sidebar.number_input("Budget Totale (€)", value=1000.0, step=50.0)
rischio = st.sidebar.slider("Aggressività (Kelly)", 0.10, 0.50, 0.25)
soglia = st.sidebar.slider("Filtro Valore Minimo (%)", 0.0, 10.0, 1.0) / 100

leagues = {
    "ITALIA: Serie A": "soccer_italy_serie_a", "ITALIA: Serie B": "soccer_italy_serie_b",
    "UK: Premier League": "soccer_england_league_1", "SPAGNA: La Liga": "soccer_spain_la_liga",
    "GERMANIA: Bundesliga": "soccer_germany_bundesliga", "OLANDA: Eredivisie": "soccer_netherlands_eredivisie"
}

sel_league = st.selectbox("Scegli Campionato:", list(leagues.keys()))

if st.button("AVVIA SCANSIONE PRIORITARIA"):
    API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
    url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/'
    params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals', 'oddsFormat': 'decimal'}
    
    try:
        res = requests.get(url, params=params)
        if res.status_code == 200:
            remaining_requests = res.headers.get('x-requests-remaining', 'N/D')
            data = res.json()
            results = []
            
            # Elenco priorità (nomi come appaiono nelle API)
            priorita = ["Bet365", "Snai", "Better"]
            
            for m in data:
                home, away = m['home_team'], m['away_team']
                raw_date = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
                formatted_date = raw_date.strftime("%d/%m %H:%M")
                
                if not m.get('bookmakers'): continue
                
                # --- LOGICA DI SELEZIONE BOOKMAKER ---
                # Cerchiamo prima se esiste uno dei preferiti
                best_bk = None
                for nome_pref in priorita:
                    found = next((b for b in m['bookmakers'] if nome_pref.lower() in b['title'].lower()), None)
                    if found:
                        best_bk = found
                        break
                
                # Se non troviamo i preferiti, prendiamo il primo della lista (il "migliore" generico)
                if not best_bk:
                    best_bk = m['bookmakers'][0]
                
                mk = next((x for x in best_bk['markets'] if x['key'] == 'totals'), None)
                if not mk: continue
                
                q_over = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), None)
                q_under = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), None)
                
                if q_over and q_under:
                    p_ov_e, p_un_e = get_totals_value(q_over, q_under)
                    
                    opzioni = [
                        {"Tipo": "OVER 2.5", "Quota": q_over, "Prob": p_ov_e + 0.07},
                        {"Tipo": "UNDER 2.5", "Quota": q_under, "Prob": p_un_e + 0.07}
                    ]
                    
                    best_opt = max(opzioni, key=lambda x: (x['Prob'] * x['Quota']) - 1)
                    valore_perc = (best_opt['Prob'] * best_opt['Quota']) - 1
                    
                    if valore_perc > soglia:
                        stake = calc_stake(best_opt['Prob'], best_opt['Quota'], budget, rischio)
                        results.append({
                            "Data": formatted_date,
                            "Match": f"{home} - {away}",
                            "Bookmaker": best_bk['title'],
                            "Esito": best_opt['Tipo'],
                            "Quota": best_opt['Quota'],
                            "Puntata (€)": stake,
                            "Valore %": round(valore_perc * 100, 2)
                        })
            
            if results:
                df = pd.DataFrame(results).sort_values(by="Valore %", ascending=False)
                st.success(f"✅ Analisi completata! | Crediti API Residui: **{remaining_requests}**")
                st.dataframe(df, use_container_width=True)
            else:
                st.info(f"Nessuna partita di valore trovata. (Crediti: {remaining_requests})")
        else:
            st.error(f"Errore API: {res.status_code}")
            
    except Exception as e:
        st.error(f"Errore: {e}")
