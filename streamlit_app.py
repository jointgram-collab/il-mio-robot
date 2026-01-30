import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V13.6 - FULL CONTROL", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

if 'api_usage' not in st.session_state:
    st.session_state['api_usage'] = {'remaining': "440", 'used': "0"}
if 'api_data' not in st.session_state:
    st.session_state['api_data'] = []

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", "soccer_uefa_europa_league": "🇪🇺 Europa League",
    "soccer_uefa_champions_league": "🏆 Champions", "soccer_spain_la_liga": "🇪🇸 La Liga",
    "soccer_germany_bundesliga": "🇩🇪 Bundesliga", "soccer_france_ligue_1": "🇫🇷 Ligue 1",
    "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie"
}

# --- MOTORE DATABASE ---
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        return df.dropna(subset=["Match"]) if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

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

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V13.6")
df_attuale = carica_db()

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 2: PORTAFOGLIO (RIPRISTINATA E POTENZIATA) ---
with t2:
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"] if not df_attuale.empty else pd.DataFrame()
    
    if not df_p.empty:
        # Statistiche in alto
        tot_imp = round(df_p['Stake'].astype(float).sum(), 2)
        rit_pot = round((df_p['Stake'].astype(float) * df_p['Quota'].astype(float)).sum(), 2)
        
        st.markdown(f"""
            <div style='background: #1c2128; padding: 15px; border-radius: 10px; border: 1px solid #30363d; margin-bottom: 20px; display: flex; justify-content: space-around;'>
                <div style='text-align:center;'><small style='color:#8b949e;'>TOTALE IMPEGNATO</small><br><strong style='color:#ffc107; font-size:22px;'>{tot_imp} €</strong></div>
                <div style='text-align:center; border-left: 1px solid #333; padding-left: 20px;'><small style='color:#8b949e;'>RITORNO POTENZIALE</small><br><strong style='color:#39d353; font-size:22px;'>{rit_pot} €</strong></div>
            </div>
        """, unsafe_allow_html=True)
        
        st.button("🔄 AGGIORNA AUTOMATICO (API)", on_click=lambda: None, use_container_width=True)
        st.divider()

        for i, r in df_p.iterrows():
            # Recupero nome campionato
            campionato = LEAGUE_NAMES.get(r['Sport_Key'], "ALTRO")
            
            c1, c2, c3, c4 = st.columns([12, 1.2, 1.2, 1.2])
            
            # Info completa: DATA | CAMPIONATO | MATCH | GIOCATA | STAKE
            info_text = f"📅 **{r['Data Match']}** | {campionato}<br>**{r['Match']}** | {r['Scelta']} @{r['Quota']} | Stake: **{r['Stake']}€** | 🏦 {r['Bookmaker']}"
            c1.info(info_text)
            
            # Pulsanti di controllo
            if c2.button("✅", key=f"w_{i}", help="Segna come VINTO"):
                chiudi_manualmente(i, "VINTO")
            
            if c3.button("❌", key=f"l_{i}", help="Segna come PERSO"):
                chiudi_manualmente(i, "PERSO")
            
            if c4.button("🗑️", key=f"d_{i}", help="Elimina"):
                salva_db(df_attuale.drop(i))
                st.rerun()
    else:
        st.info("Nessuna giocata pendente nel portafoglio.")

# --- TAB 3: FISCALE ---
with t3:
    if not df_attuale.empty:
        vinto = df_attuale[df_attuale['Esito'] == "VINTO"]['Profitto'].sum()
        perso = abs(df_attuale[df_attuale['Esito'] == "PERSO"]['Profitto'].sum())
        
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Vinto Netto", f"{round(vinto,2)} €")
        m2.metric("❌ Perso Totale", f"{round(perso,2)} €")
        m3.metric("📈 Profitto Reale", f"{round(vinto-perso,2)} €", delta=f"{round(vinto-perso,2)} €")
        
        st.divider()
        st.write("### Storico Giocate")
        st.dataframe(df_attuale.sort_index(ascending=False), use_container_width=True)
