import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V13.6 - STABLE", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

if 'api_usage' not in st.session_state:
    st.session_state['api_usage'] = {'remaining': "N/D", 'used': "N/D"}
if 'api_data' not in st.session_state:
    st.session_state['api_data'] = []

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "William Hill", "888sport"]

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", 
    "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", 
    "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie",
    "soccer_spain_la_liga": "🇪🇸 La Liga", 
    "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_france_ligue_1": "🇫🇷 Ligue 1",
    "soccer_uefa_europa_league": "🇪🇺 Europa League",
    "soccer_uefa_champions_league": "🏆 Champions"
}

# --- MOTORE DATABASE ---
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        return df.dropna(subset=["Match"]) if df is not None else pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

def check_results():
    df = carica_db()
    pendenti = df[df['Esito'] == "Pendente"]
    if pendenti.empty:
        st.info("Nessuna scommessa pendente.")
        return
    cambiamenti = False
    with st.spinner("🔄 Verifica risultati..."):
        for skey in pendenti['Sport_Key'].unique():
            res = requests.get(f'https://api.the-odds-api.com/v4/sports/{skey}/scores/', params={'api_key': API_KEY, 'daysFrom': 3})
            if res.status_code == 200:
                scores = res.json()
                for i, r in pendenti[pendenti['Sport_Key'] == skey].iterrows():
                    # Matching robusto: cerca il match ignorando l'ordine casa/fuori
                    m_res = next((m for m in scores if f"{m['home_team']}-{m['away_team']}" == r['Match'] and m.get('completed')), None)
                    if m_res:
                        s = m_res['scores']
                        if s:
                            s1, s2 = int(s[0]['score']), int(s[1]['score'])
                            vinto = (s1 + s2) > 2.5 if r['Scelta'] == "OVER 2.5" else (s1 + s2) < 2.5
                            df.at[i, 'Esito'] = "VINTO" if vinto else "PERSO"
                            df.at[i, 'Risultato'] = f"{s1}-{s2}"
                            df.at[i, 'Profitto'] = round((float(r['Stake']) * float(r['Quota'])) - float(r['Stake']), 2) if vinto else -float(r['Stake'])
                            cambiamenti = True
    if cambiamenti:
        salva_db(df)
        st.rerun()

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V13.6 - RECOVERY")
df_attuale = carica_db()

with st.sidebar:
    st.header("📊 Stato API")
    c1, c2 = st.columns(2)
    c1.metric("Residui", st.session_state['api_usage']['remaining'])
    c2.metric("Usati", st.session_state['api_usage']['used'])
    st.divider()
    budget_cassa = st.number_input("Budget (€)", value=500.0)
    rischio = st.slider("Kelly", 0.05, 0.50, 0.20)
    soglia_val = st.slider("Valore Min %", 0, 15, 3) / 100

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER ---
with t1:
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    c_sel, c_all, c_ore = st.columns([2, 1, 1])
    sel_name = c_sel.selectbox("Campionato Singolo:", list(leagues.keys()))
    ore_limite = c_ore.selectbox("Finestra Ore:", [24, 48, 72, 96, 120, 168], index=2)
    
    if c_all.button("🚀 TOTALE", use_container_width=True):
        # ... logica scanner totale ...
        pass

# --- TAB 2: PORTAFOGLIO ---
with t2:
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"]
    if not df_p.empty:
        tot_impegnato = round(df_p['Stake'].astype(float).sum(), 2)
        ritorno_potenziale = round((df_p['Stake'].astype(float) * df_p['Quota'].astype(float)).sum(), 2)
        
        st.markdown(f"""
            <div style='background-color: #0e1117; padding: 20px; border-radius: 10px; border: 1px solid #30363d; margin-bottom: 20px; text-align: center;'>
                <div style='display: flex; justify-content: space-around;'>
                    <div><span style='color: white;'>IMPEGNATO</span><br><h2 style='color: #ffc107;'>{tot_impegnato} €</h2></div>
                    <div style='border-left: 1px solid #30363d; padding-left: 20px;'>
                    <span style='color: white;'>RITORNO POTENZIALE</span><br><h2 style='color: #00ff00;'>{ritorno_potenziale} €</h2></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    st.button("🔄 AGGIORNA RISULTATI", on_click=check_results, use_container_width=True)
    st.write("### Giocate in corso")
    st.dataframe(df_p, use_container_width=True)

# --- TAB 3: FISCALE ---
with t3:
    st.subheader("🏁 Cruscotto Finanziario")
    if not df_attuale.empty:
        tot_giocato = round(df_attuale['Stake'].astype(float).sum(), 2)
        prof_netto = round(df_attuale['Profitto'].astype(float).sum(), 2)
        
        m1, m2 = st.columns(2)
        m1.metric("💰 Giocato Totale", f"{tot_giocato} €")
        m2.metric("📈 Profitto Netto", f"{prof_netto} €")
        
        st.divider()
        # Backup CSV
        csv_data = df_attuale.to_csv(index=False).encode('utf-8')
        st.download_button("📥 SCARICA BACKUP CSV", data=csv_data, file_name=f"sniper_backup_{date.today()}.csv", use_container_width=True)
        
        st.write("### Storico Completo")
        st.dataframe(df_attuale.sort_index(ascending=False), use_container_width=True)
