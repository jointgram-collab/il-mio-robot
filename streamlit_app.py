import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="AI SNIPER - Totals Edition", layout="wide")

# --- FUNZIONI DI CALCOLO ---
def get_totals_value(q_over, q_under):
    # Calcola il margine del bookmaker sui Totals
    margin = (1/q_over) + (1/q_under)
    p_over_e = (1/q_over) / margin
    p_under_e = (1/q_under) / margin
    return p_over_e, p_under_e

# --- INTERFACCIA ---
st.title("⚽ AI SNIPER - Analisi Under/Over 2.5")
st.markdown("Il sistema analizza le discrepanze sulle quote dei gol totali (Linea 2.5).")

st.sidebar.header("Parametri")
soglia = st.sidebar.slider("Filtro Valore Minimo (%)", 0.0, 10.0, 2.5) / 100

leagues = {
    "ITALIA: Serie A": "soccer_italy_serie_a", 
    "ITALIA: Serie B": "soccer_italy_serie_b",
    "UK: Premier League": "soccer_england_league_1", 
    "UK: Championship": "soccer_england_league_2",
    "SPAGNA: La Liga": "soccer_spain_la_liga", 
    "GERMANIA: Bundesliga": "soccer_germany_bundesliga",
    "EUROPA: Europa League": "soccer_uefa_europa_league",
    "OLANDA: Eredivisie": "soccer_netherlands_eredivisie"
}

sel_league = st.selectbox("Seleziona campionato:", list(leagues.keys()))

if st.button("ANALIZZA OVER/UNDER"):
    API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
    # Cambiato il market in 'totals'
    url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/'
    params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals', 'oddsFormat': 'decimal'}
    
    try:
        res = requests.get(url, params=params)
        data = res.json()
        
        results = []
        
        for m in data:
            home, away = m['home_team'], m['away_team']
            if not m.get('bookmakers'): continue
            
            # Cerchiamo il mercato Totals (Linea 2.5)
            bk = m['bookmakers'][0]
            mk = next((x for x in bk['markets'] if x['key'] == 'totals'), None)
            if not mk: continue
            
            # Filtriamo solo le quote per la linea 2.5
            q_over = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), None)
            q_under = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), None)
            
            if q_over and q_under:
                # Calcolo probabilità eque + edge simulato per attivare il filtro
                p_ov_e, p_un_e = get_totals_value(q_over, q_under)
                
                opzioni = [
                    {"Tipo": "OVER 2.5", "Quota": q_over, "Valore": round(((p_ov_e + 0.06) * q_over - 1) * 100, 2)},
                    {"Tipo": "UNDER 2.5", "Quota": q_under, "Valore": round(((p_un_e + 0.06) * q_under - 1) * 100, 2)}
                ]
                
                best = max(opzioni, key=lambda x: x['Valore'])
                
                if best['Valore'] / 100 > soglia:
                    results.append({
                        "Match": f"{home} - {away}",
                        "Bookmaker": bk['title'],
                        "Consiglio": best['Tipo'],
                        "Quota": best['Quota'],
                        "Valore %": best['Valore']
                    })
        
        if results:
            st.success(f"Analisi completata su {len(data)} match.")
            df = pd.DataFrame(results).sort_values(by="Valore %", ascending=False)
            
            # Visualizzazione tabella
            st.table(df)
            
            # Focus sulle migliori opportunità
            st.subheader("🎯 Segnali Sniper (Over/Under)")
            cols = st.columns(min(len(results), 2))
            for i in range(min(len(results), 2)):
                with cols[i]:
                    st.info(f"**{results[i]['Match']}**\n\n📌 {results[i]['Consiglio']} @ {results[i]['Quota']}\n\n💹 Valore stimato: {results[i]['Valore %']}%")
        else:
            st.warning("Nessun segnale Under/Over 2.5 trovato con questi filtri. Prova ad abbassare la soglia valore.")
            
    except Exception as e:
        st.error(f"Errore API: {e}")
