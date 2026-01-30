import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V13.6 - MANUAL CONTROL", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

if 'api_usage' not in st.session_state:
    st.session_state['api_usage'] = {'remaining': "N/D", 'used': "N/D"}
if 'api_data' not in st.session_state:
    st.session_state['api_data'] = []

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "William Hill", "888sport"]

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", "soccer_uefa_europa_league": "🇪🇺 Europa League",
    "soccer_uefa_champions_league": "🏆 Champions", "soccer_spain_la_liga": "🇪🇸 La Liga",
    "soccer_germany_bundesliga": "🇩🇪 Bundesliga"
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

# --- AGGIORNAMENTO MANUALE ---
def chiudi_manualmente(idx, esito):
    df = carica_db()
    row = df.loc[idx]
    q = float(row['Quota'])
    s = float(row['Stake'])
    
    df.at[idx, 'Esito'] = esito
    df.at[idx, 'Risultato'] = "MANUALE"
    df.at[idx, 'Profitto'] = round((s * q) - s, 2) if esito == "VINTO" else -s
    salva_db(df)
    st.rerun()

# --- TAB 2: PORTAFOGLIO (CON CONTROLLI MANUALI) ---
def render_portafoglio(df_attuale):
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"]
    
    if not df_p.empty:
        # Calcolo statistiche veloci
        tot_imp = round(df_p['Stake'].astype(float).sum(), 2)
        rit_pot = round((df_p['Stake'].astype(float) * df_p['Quota'].astype(float)).sum(), 2)
        
        st.markdown(f"""
            <div style='background: #1c2128; padding: 15px; border-radius: 10px; border: 1px solid #30363d; margin-bottom: 20px; display: flex; justify-content: space-around;'>
                <div style='text-align:center;'><small style='color:#8b949e;'>IMPEGNATO</small><br><strong style='color:#ffc107; font-size:20px;'>{tot_imp} €</strong></div>
                <div style='text-align:center; border-left: 1px solid #333; padding-left: 20px;'><small style='color:#8b949e;'>RIENTRO POT.</small><br><strong style='color:#39d353; font-size:20px;'>{rit_pot} €</strong></div>
            </div>
        """, unsafe_allow_html=True)
        
        st.button("🔄 AGGIORNA AUTOMATICO", on_click=lambda: None, use_container_width=True) # Aggiorna API (logica esistente)
        st.divider()

        for i, r in df_p.iterrows():
            c1, c2, c3, c4 = st.columns([12, 1.5, 1.5, 1.5])
            
            # Info Match
            c1.info(f"**{r['Match']}** | {r['Scelta']} @{r['Quota']} | **{r['Stake']}€** | 🏦 {r['Bookmaker']}")
            
            # Tasto Vinto
            if c2.button("✅", key=f"win_{i}", help="Segna come VINTO"):
                chiudi_manualmente(i, "VINTO")
            
            # Tasto Perso
            if c3.button("❌", key=f"lose_{i}", help="Segna come PERSO"):
                chiudi_manualmente(i, "PERSO")
            
            # Tasto Elimina
            if c4.button("🗑️", key=f"del_{i}", help="Elimina riga"):
                salva_db(df_attuale.drop(i))
                st.rerun()
    else:
        st.info("Nessuna giocata pendente.")

# --- INTERFACCIA PRINCIPALE ---
st.title("🎯 AI SNIPER V13.6")
df_attuale = carica_db()

with st.sidebar:
    st.header("📊 Stato API")
    st.metric("Crediti Residui", st.session_state['api_usage']['remaining'])
    st.divider()
    budget_cassa = st.number_input("Cassa (€)", value=500.0)

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    st.write("Sezione Scanner attiva. Cerca i match per aggiungerli.")

with t2:
    render_portafoglio(df_attuale)

with t3:
    st.subheader("📊 Resoconto Fiscale")
    if not df_attuale.empty:
        # Metriche Fiscali
        vinto = df_attuale[df_attuale['Esito'] == "VINTO"]['Profitto'].sum()
        perso = abs(df_attuale[df_attuale['Esito'] == "PERSO"]['Profitto'].sum())
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Vinto Netto", f"{round(vinto,2)} €")
        m2.metric("Perso", f"{round(perso,2)} €")
        m3.metric("Profitto Totale", f"{round(vinto-perso,2)} €", delta=f"{round(vinto-perso,2)} €")
        
        st.divider()
        st.dataframe(df_attuale.sort_index(ascending=False), use_container_width=True)
