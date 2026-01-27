import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V11.47 - Universal", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

# Estendiamo la lista per sicurezza
BK_TARGET = ["Bet365", "Snai", "Eurobet", "Sisal", "Goldbet", "Better", "Planetwin365", "888sport", "Bwin", "William Hill"]

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie",
    "soccer_spain_la_liga": "🇪🇸 La Liga", "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_uefa_champions_league": "🇪🇺 Champions", "soccer_france_ligue_1": "🇫🇷 Ligue 1"
}

def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        return df.dropna(subset=["Match"]) if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def salva_db(df):
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

st.title("🎯 AI SNIPER V11.47")

with st.sidebar:
    st.header("⚙️ Parametri")
    budget = st.number_input("Budget (€)", value=250.0)
    rischio = st.slider("Kelly", 0.05, 0.50, 0.20)
    soglia = st.slider("Soglia Valore %", -5, 10, -2) / 100
    st.info("Soglia negativa = mostra tutti i match trovati.")

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    c1, c2 = st.columns(2)
    sel_name = c1.selectbox("Campionato:", list(leagues.keys()))
    sel_market = c2.selectbox("Mercato:", ["Over/Under 2.5", "Gol/No Gol"])
    
    m_api = "totals" if sel_market == "Over/Under 2.5" else "btts"

    if st.button("🚀 AVVIA SCANSIONE", use_container_width=True):
        # Chiamata API semplificata per evitare errori 422
        url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_name]}/odds/'
        params = {'api_key': API_KEY, 'regions': 'eu', 'markets': m_api, 'oddsFormat': 'decimal'}
        
        res = requests.get(url, params=params)
        
        if res.status_code == 200:
            data = res.json()
            if not data:
                st.warning("L'API non ha restituito match per questa lega in questo momento.")
            else:
                matches_data = []
                for m in data:
                    match_name = f"{m['home_team']} - {m['away_team']}"
                    start_time = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
                    
                    for bk in m.get('bookmakers', []):
                        market_data = next((mk for mk in bk['markets'] if mk['key'] == m_api), None)
                        if market_data:
                            try:
                                if m_api == "totals":
                                    o = next(x['price'] for x in market_data['outcomes'] if x['name'].lower() == 'over' and x['point'] == 2.5)
                                    u = next(x['price'] for x in market_data['outcomes'] if x['name'].lower() == 'under' and x['point'] == 2.5)
                                    sel_label = "OVER 2.5"
                                    q_val = o
                                else: # btts
                                    o = next(x['price'] for x in market_data['outcomes'] if x['name'].lower() in ['yes', 'gol', 'both'])
                                    u = next(x['price'] for x in market_data['outcomes'] if x['name'].lower() in ['no', 'nogol', 'neither'])
                                    sel_label = "GOL"
                                    q_val = o
                                
                                margin = (1/o) + (1/u)
                                prob = ((1/o)/margin) + 0.05
                                val_calc = (prob * o) - 1
                                
                                matches_data.append({
                                    "Ora": start_time, "Match": match_name, "BK": bk['title'],
                                    "Scelta": sel_label, "Quota": q_val, "Valore": val_calc, "S_Key": leagues[sel_name]
                                })
                            except: continue

                if matches_data:
                    df_final = pd.DataFrame(matches_data)
                    # Filtro soglia
                    df_show = df_final[df_final['Valore'] >= soglia].sort_values(by="Valore", ascending=False)
                    
                    if df_show.empty:
                        st.warning(f"Nessun match sopra la soglia del {soglia*100}%. Ecco i migliori:")
                        st.table(df_final.sort_values(by="Valore", ascending=False).head(10))
                    else:
                        for i, r in df_show.iterrows():
                            c_a, c_b = st.columns([4, 1])
                            v_perc = round(r['Valore']*100, 1)
                            c_a.write(f"📅 {r['Ora']} | **{r['Match']}** | {r['BK']} | Valore: **{v_perc}%**")
                            if c_b.button(f"PUNTA @{r['Quota']}", key=f"btn_{i}"):
                                v_kelly = r['Valore']
                                s_calc = round(max(2.0, min(budget * (v_kelly/(r['Quota']-1)) * rischio, budget*0.1)), 2)
                                new_row = pd.DataFrame([{
                                    "Data Match": r['Ora'], "Match": r['Match'], "Scelta": r['Scelta'],
                                    "Quota": r['Quota'], "Stake": s_calc, "Bookmaker": r['BK'],
                                    "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": r['S_Key'], "Risultato": "-"
                                }])
                                salva_db(pd.concat([carica_db(), new_row], ignore_index=True))
                                st.success("Giocata salvata!")
                else:
                    st.error("Dati ricevuti ma non è stato possibile calcolare le quote. Verifica i bookmaker.")
        else:
            st.error(f"Errore API {res.status_code}. Riprova tra poco.")
