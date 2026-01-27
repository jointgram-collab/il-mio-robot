import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V11.46", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "888sport"]

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", "soccer_england_efl_championship": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Championship",
    "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie", "soccer_spain_la_liga": "🇪🇸 La Liga",
    "soccer_germany_bundesliga": "🇩🇪 Bundesliga", "soccer_uefa_champions_league": "🇪🇺 Champions",
    "soccer_france_ligue_1": "🇫🇷 Ligue 1"
}

def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        return df.dropna(subset=["Match"]) if df is not None else pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

st.title("🎯 AI SNIPER V11.46")

with st.sidebar:
    st.header("⚙️ Parametri")
    budget_cassa = st.number_input("Budget (€)", value=250.0)
    rischio = st.slider("Kelly", 0.05, 0.50, 0.20)
    soglia_val = st.slider("Soglia Valore %", -5, 10, 1) / 100
    st.divider()
    if st.button("🗑️ Reset Cache"):
        st.session_state.clear()
        st.rerun()

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    c1, c2 = st.columns(2)
    sel_name = c1.selectbox("Campionato:", list(leagues.keys()))
    sel_market = c2.selectbox("Mercato:", ["Over/Under 2.5", "Gol/No Gol"])
    
    m_key = "totals" if sel_market == "Over/Under 2.5" else "btts"

    if st.button("🚀 AVVIA SCANSIONE", use_container_width=True):
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_name]}/odds/', 
                           params={'api_key': API_KEY, 'regions': 'eu', 'markets': m_key})
        
        if res.status_code == 200:
            data = res.json()
            st.info(f"Ricevuti {len(data)} eventi. Elaborazione quote...")
            
            results_found = []
            for m in data:
                nome_match = f"{m['home_team']}-{m['away_team']}"
                date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
                
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_EURO_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == m_key), None)
                        if mk:
                            try:
                                if m_key == "totals":
                                    q1 = next(o['price'] for o in mk['outcomes'] if o['name'].lower() == 'over' and o['point'] == 2.5)
                                    q2 = next(o['price'] for o in mk['outcomes'] if o['name'].lower() == 'under' and o['point'] == 2.5)
                                    label = "OVER 2.5"
                                else:
                                    q1 = next(o['price'] for o in mk['outcomes'] if o['name'].lower() in ['yes', 'gol', 'both'])
                                    q2 = next(o['price'] for o in mk['outcomes'] if o['name'].lower() in ['no', 'nogol', 'neither'])
                                    label = "GOL"
                                
                                margin = (1/q1) + (1/q2)
                                prob_stimata = ((1/q1)/margin) + 0.05 # Aggiustamento aggio
                                valore = (prob_stimata * q1) - 1
                                
                                results_found.append({
                                    "Match": nome_match, "Data": date_m, "Scelta": label, 
                                    "Quota": q1, "Valore": valore, "BK": b['title'], "S_Key": leagues[sel_name]
                                })
                            except: continue
            
            if results_found:
                df_res = pd.DataFrame(results_found)
                # Filtriamo per la soglia impostata
                df_filtrato = df_res[df_res['Valore'] >= soglia_val].sort_values(by="Valore", ascending=False)
                
                if not df_filtrato.empty:
                    for _, row in df_filtrato.iterrows():
                        with st.container():
                            col_a, col_b = st.columns([3, 1])
                            col_a.write(f"📅 {row['Data']} | **{row['Match']}** | {row['BK']} | Valore: **{round(row['Valore']*100, 1)}%**")
                            if col_b.button(f"PUNTA {row['Scelta']} @{row['Quota']}", key=f"btn_{row['Match']}"):
                                stake = round(max(2.0, min(budget_cassa * (row['Valore']/(row['Quota']-1)) * rischio, budget_cassa*0.1)), 2)
                                n = {"Data Match": row['Data'], "Match": row['Match'], "Scelta": row['Scelta'], "Quota": row['Quota'], "Stake": stake, "Bookmaker": row['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": row['S_Key'], "Risultato": "-"}
                                salva_db(pd.concat([carica_db(), pd.DataFrame([n])], ignore_index=True))
                                st.success("Aggiunto!")
                        st.divider()
                else:
                    st.warning("Nessun match sopra la soglia. Ecco i migliori trovati (sotto soglia):")
                    st.table(df_res.sort_values(by="Valore", ascending=False).head(5))
            else:
                st.error("L'API non ha restituito quote valide per i bookmaker selezionati.")
        else:
            st.error(f"Errore API: {res.status_code}")
