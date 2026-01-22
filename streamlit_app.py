import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- 1. INIZIALIZZAZIONE MEMORIA ---
if 'portafoglio' not in st.session_state:
    st.session_state['portafoglio'] = []
if 'ultimi_risultati' not in st.session_state:
    st.session_state['ultimi_risultati'] = []
if 'api_residue' not in st.session_state:
    st.session_state['api_residue'] = "N/D"

st.set_page_config(page_title="AI SNIPER V9.3 - Professional Mode", layout="wide")

# --- 2. FUNZIONI DI CALLBACK ---
def aggiungi_a_portafoglio(match, scelta, quota, stake, bookmaker, data_match):
    giocata = {
        "Data Match": data_match,
        "Match": match,
        "Scelta": scelta,
        "Quota": quota,
        "Stake": stake,
        "Bookmaker": bookmaker,
        "Esito": "Pendente",
        "Profitto": 0.0
    }
    st.session_state['portafoglio'].append(giocata)
    st.toast(f"✅ Registrata: {match}")

def elimina_schedina(index):
    st.session_state['portafoglio'].pop(index)
    st.toast("🗑️ Schedina eliminata")

# --- 3. FUNZIONI TECNICHE ---
def get_totals_value(q_over, q_under):
    margin = (1/q_over) + (1/q_under)
    return (1/q_over) / margin, (1/q_under) / margin

def calc_stake(prob, quota, budget, frazione):
    valore = (prob * quota) - 1
    if valore <= 0: return 2.0
    importo = budget * (valore / (quota - 1)) * frazione
    return round(max(2.0, min(importo, budget * 0.1)), 2)

# --- 4. INTERFACCIA ---
st.title("🎯 AI SNIPER - Goal 5.000€")

t1, t2, t3 = st.tabs(["🔍 SCANNER VALORE", "💼 PORTAFOGLIO ATTIVO", "📊 ANDAMENTO FISCALE"])

with t1:
    with st.sidebar:
        st.header("⚙️ Parametri")
        budget_cassa = st.number_input("Budget Cassa (€)", value=1000.0)
        rischio = st.slider("Aggressività (Kelly)", 0.10, 0.50, 0.25)
        soglia = st.slider("Filtro Valore (%)", 0.0, 10.0, 2.0) / 100
        st.divider()
        st.metric("Crediti API Residui", st.session_state['api_residue'])

    leagues = {
        "EUROPA: Champions League": "soccer_uefa_champions_league",
        "EUROPA: Europa League": "soccer_uefa_europa_league",
        "EUROPA: Conference League": "soccer_uefa_europa_conference_league",
        "ITALIA: Serie A": "soccer_italy_serie_a", 
        "ITALIA: Serie B": "soccer_italy_serie_b",
        "UK: Premier League": "soccer_england_league_1", 
        "SPAGNA: La Liga": "soccer_spain_la_liga",
        "GERMANIA: Bundesliga": "soccer_germany_bundesliga", 
        "FRANCIA: Ligue 1": "soccer_france_ligue_1",
        "OLANDA: Eredivisie": "soccer_netherlands_eredivisie"
    }
    
    sel_league = st.selectbox("Seleziona competizione:", list(leagues.keys()))

    if st.button("🚀 AVVIA SCANSIONE"):
        API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
        url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/'
        params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals', 'oddsFormat': 'decimal'}
        
        try:
            res = requests.get(url, params=params)
            if res.status_code == 200:
                st.session_state['ultimi_risultati'] = res.json()
                st.session_state['api_residue'] = res.headers.get('x-requests-remaining', 'N/D')
                st.rerun()
            else:
                st.error("Errore API. Controlla i crediti.")
        except:
            st.error("Errore di connessione.")

    if st.session_state['ultimi_risultati']:
        priorita = ["Bet365", "Snai", "Better"]
        for m in st.session_state['ultimi_risultati']:
            home, away = m['home_team'], m['away_team']
            date_match = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
            
            best_bk = next((b for p in priorita for b in m.get('bookmakers', []) if p.lower() in b['title'].lower()), None)
            if not best_bk and m.get('bookmakers'): best_bk = m['bookmakers'][0]
            
            if best_bk:
                mk = next((x for x in best_bk['markets'] if x['key'] == 'totals'), None)
                if mk:
                    q_over = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), 1.0)
                    q_under = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), 1.0)
                    p_ov_e, p_un_e = get_totals_value(q_over, q_under)
                    
                    opzioni = [{"T": "OVER 2.5", "Q": q_over, "P": p_ov_e + 0.07}, {"T": "UNDER 2.5", "Q": q_under, "P": p_un_e + 0.07}]
                    best = max(opzioni, key=lambda x: (x['P'] * x['Q']) - 1)
                    valore = (best['P'] * best['Q']) - 1
                    
                    if valore > soglia:
                        stake = calc_stake(best['P'], best['Q'], budget_cassa, rischio)
                        c1, c2, c3 = st.columns([3, 2, 1])
                        c1.markdown(f"📅 {date_match}  \n**{home} - {away}**")
                        c2.markdown(f"🎯 **{best['T']}** @ **{best['Q']}** \n🏟️ {best_bk['title']} | Stake: **{stake}€**")
                        c3.button("AGGIUNGI", key=f"btn_{home}_{best['T']}", on_click=aggiungi_a_portafoglio, 
                                  args=(f"{home}-{away}", best['T'], best['Q'], stake, best_bk['title'], date_match))
                        st.divider()

with t2:
    # --- CALCOLO TOTALI ---
    investimento_pendente = sum(b['Stake'] for b in st.session_state['portafoglio'] if b['Esito'] == "Pendente")
    st.subheader("💼 Portafoglio Strategico")
    st.info(f"💰 Importo Totale Scommesso (Pendenti): **{round(investimento_pendente, 2)} €**")

    if st.session_state['portafoglio']:
        # Mostriamo le schedine in ordine inverso (l'ultima aggiunta in alto)
        for i, b in enumerate(reversed(st.session_state['portafoglio'])):
            real_index = len(st.session_state['portafoglio']) - 1 - i
            if b['Esito'] == "Pendente":
                with st.expander(f"📌 {b['Match']} - {b['Scelta']} @ {b['Quota']}", expanded=True):
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    col1.write(f"Book: **{b['Bookmaker']}** \nPuntata: **{b['Stake']}€**")
                    if col2.button("✅ VINTO", key=f"win_{real_index}"):
                        st.session_state['portafoglio'][real_index]['Esito'] = "VINTO"
                        st.session_state['portafoglio'][real_index]['Profitto'] = round((b['Stake']*b['Quota'])-b['Stake'], 2)
                        st.rerun()
                    if col3.button("❌ PERSO", key=f"loss_{real_index}"):
                        st.session_state['portafoglio'][real_index]['Esito'] = "PERSO"
                        st.session_state['portafoglio'][real_index]['Profitto'] = -b['Stake']
                        st.rerun()
                    if col4.button("🗑️ ELIMINA", key=f"del_{real_index}"):
                        elimina_schedina(real_index)
                        st.rerun()
    else:
        st.info("Portafoglio vuoto.")

with t3:
    st.subheader("📊 Bilancio Fiscale Target 5.000€")
    if st.session_state['portafoglio']:
        df = pd.DataFrame(st.session_state['portafoglio'])
        profitto_netto = df['Profitto'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Profitto Netto", f"{round(profitto_netto, 2)} €")
        m2.metric("Target Residuo", f"{round(5000 - profitto_netto, 2)} €")
        m3.metric("ROI Medio %", f"{round((profitto_netto / df[df['Esito']!='Pendente']['Stake'].sum() * 100), 1) if not df[df['Esito']!='Pendente'].empty else 0}%")
        
        st.divider()
        st.write("### Registro Storico Completo")
        st.dataframe(df, use_container_width=True)
