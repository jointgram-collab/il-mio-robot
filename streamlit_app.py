import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- 1. CONFIGURAZIONE E MEMORIA ---
st.set_page_config(page_title="AI SNIPER V9 - GOAL 5000€", layout="wide")

# Inizializzazione del Portafoglio in memoria
if 'portafoglio' not in st.session_state:
    st.session_state['portafoglio'] = []

# --- 2. FUNZIONI TECNICHE ---
def get_totals_value(q_over, q_under):
    margin = (1/q_over) + (1/q_under)
    return (1/q_over) / margin, (1/q_under) / margin

def calc_stake(prob, quota, budget, frazione):
    valore = (prob * quota) - 1
    if valore <= 0: return 2.0
    importo = budget * (valore / (quota - 1)) * frazione
    return round(max(2.0, min(importo, budget * 0.1)), 2)

# --- 3. SIDEBAR (GESTIONE TARGET) ---
st.sidebar.title("📈 TARGET 5.000€/MESE")
budget_iniziale = st.sidebar.number_input("Cassa Iniziale (€)", value=1000.0, step=100.0)
rischio = st.sidebar.slider("Aggressività (Kelly)", 0.10, 0.50, 0.25)
soglia = st.sidebar.slider("Filtro Valore (%)", 0.0, 10.0, 2.0) / 100

# --- 4. TABS ---
t1, t2, t3 = st.tabs(["🔍 SCANNER VALORE", "💼 PORTAFOGLIO ATTIVO", "📊 ANDAMENTO FISCALE"])

# --- TAB 1: SCANNER ---
with t1:
    leagues = {
        "EUROPA: Champions League": "soccer_uefa_champions_league",
        "EUROPA: Europa League": "soccer_uefa_europa_league",
        "ITALIA: Serie A": "soccer_italy_serie_a", 
        "ITALIA: Serie B": "soccer_italy_serie_b",
        "UK: Premier League": "soccer_england_league_1",
        "OLANDA: Eredivisie": "soccer_netherlands_eredivisie"
    }
    sel_league = st.selectbox("Campionato:", list(leagues.keys()))
    
    if st.button("AVVIA SCANSIONE"):
        API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
        url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/'
        params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals', 'oddsFormat': 'decimal'}
        
        try:
            res = requests.get(url, params=params)
            data = res.json()
            priorita = ["Bet365", "Snai", "Better"]
            
            for m in data:
                home, away = m['home_team'], m['away_team']
                date_obj = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
                
                # Selezione Bookmaker Prioritario
                best_bk = next((b for p in priorita for b in m.get('bookmakers', []) if p.lower() in b['title'].lower()), None)
                if not best_bk and m.get('bookmakers'): best_bk = m['bookmakers'][0]
                
                if best_bk:
                    mk = next((x for x in best_bk['markets'] if x['key'] == 'totals'), None)
                    if mk:
                        q_over = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), None)
                        q_under = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), None)
                        
                        if q_over and q_under:
                            p_ov_e, p_un_e = get_totals_value(q_over, q_under)
                            opzioni = [{"Tipo": "OVER 2.5", "Q": q_over, "P": p_ov_e + 0.07}, {"Tipo": "UNDER 2.5", "Q": q_under, "P": p_un_e + 0.07}]
                            best = max(opzioni, key=lambda x: (x['P'] * x['Q']) - 1)
                            valore = (best['P'] * best['Q']) - 1
                            
                            if valore > soglia:
                                stake = calc_stake(best['P'], best['Q'], budget_iniziale, rischio)
                                with st.container():
                                    c1, c2, c3 = st.columns([3, 2, 1])
                                    c1.write(f"📅 {date_obj.strftime('%d/%m %H:%M')}\n**{home} - {away}**")
                                    c2.write(f"🎯 {best['Tipo']} @ **{best['Q']}** ({best_bk['title']})\n💰 Stake: **{stake}€**")
                                    
                                    if c3.button("AGGIUNGI", key=f"add_{home}_{best['Tipo']}"):
                                        st.session_state['portafoglio'].append({
                                            "Data": date_obj.strftime('%d/%m'),
                                            "Match": f"{home}-{away}",
                                            "Scelta": best['Tipo'],
                                            "Quota": best['Q'],
                                            "Stake": stake,
                                            "Esito": "Pendente",
                                            "Profitto": 0.0
                                        })
                                        st.toast("Aggiunto al portafoglio!")
        except: st.error("Errore API")

# --- TAB 2: PORTAFOGLIO ---
with t2:
    st.subheader("💼 Giocate in Corso")
    if st.session_state['portafoglio']:
        for i, bet in enumerate(st.session_state['portafoglio']):
            if bet['Esito'] == "Pendente":
                cols = st.columns([2, 1, 1, 1, 1])
                cols[0].write(f"{bet['Match']} ({bet['Scelta']})")
                cols[1].write(f"@{bet['Quota']}")
                cols[2].write(f"{bet['Stake']}€")
                if cols[3].button("✅ VINTO", key=f"win_{i}"):
                    st.session_state['portafoglio'][i]['Esito'] = "VINTO"
                    st.session_state['portafoglio'][i]['Profitto'] = round((bet['Stake'] * bet['Quota']) - bet['Stake'], 2)
                    st.rerun()
                if cols[4].button("❌ PERSO", key=f"loss_{i}"):
                    st.session_state['portafoglio'][i]['Esito'] = "PERSO"
                    st.session_state['portafoglio'][i]['Profitto'] = -bet['Stake']
                    st.rerun()
    else: st.info("Il portafoglio è vuoto.")

# --- TAB 3: ANDAMENTO FISCALE ---
with t3:
    st.subheader("📊 Analisi Performance Mensile")
    if st.session_state['portafoglio']:
        df = pd.DataFrame(st.session_state['portafoglio'])
        profitto_totale = df['Profitto'].sum()
        investimento_totale = df[df['Esito'] != "Pendente"]['Stake'].sum()
        roi = (profitto_totale / investimento_totale * 100) if investimento_totale > 0 else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Profitto Netto", f"{round(profitto_totale, 2)} €")
        m2.metric("ROI %", f"{round(roi, 1)} %")
        m3.metric("Mancante al Target", f"{round(5000 - profitto_totale, 2)} €", delta_color="inverse")
        
        st.write("### Registro Storico")
        st.dataframe(df, use_container_width=True)
        
        if st.button("RESET TOTALE"):
            st.session_state['portafoglio'] = []
            st.rerun()
    else: st.info("Nessun dato fiscale disponibile.")
