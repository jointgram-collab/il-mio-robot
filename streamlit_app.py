import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V15.1.4 - PORTFOLIO FULL INFO", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONFIGURAZIONE COSTANTI ---
API_KEYS = ['01f1c8f2a314814b17de03eeb6c53623', '55f08c25f38fa1006dd9e66282170e1a']
BUDGET_DISPONIBILE = 500.0
OBIETTIVO_TARGET = 5000.0

# Mappatura per nomi leggibili
LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie",
    "soccer_spain_la_liga": "🇪🇸 La Liga", "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_france_ligue_1": "🇫🇷 Ligue 1", "soccer_uefa_europa_league": "🇪🇺 Europa League",
    "soccer_uefa_champions_league": "🏆 Champions"
}

# --- FUNZIONI CORE ---
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        return df.dropna(subset=["Match"]) if df is not None else pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

def chiudi_gara(idx, esito, risultato_score="-"):
    df = carica_db()
    if idx in df.index:
        q, s = float(df.at[idx, 'Quota']), float(df.at[idx, 'Stake'])
        df.at[idx, 'Esito'] = esito
        df.at[idx, 'Risultato'] = risultato_score
        df.at[idx, 'Profitto'] = round((s * q) - s, 2) if esito == "VINTO" else -s
        salva_db(df)
        st.rerun()

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V15.1.4")
df_attuale = carica_db()

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER (Logica standard) ---
with t1:
    st.write("Utilizza lo scanner per aggiungere nuove partite.")

# --- TAB 2: PORTAFOGLIO (INFO AGGIORNATE) ---
with t2:
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"].copy()
    
    if not df_p.empty:
        # Calcoli totali
        df_p['Stake'] = pd.to_numeric(df_p['Stake'], errors='coerce').fillna(0)
        df_p['Quota'] = pd.to_numeric(df_p['Quota'], errors='coerce').fillna(0)
        t_scommesso = round(df_p['Stake'].sum(), 2)
        t_vincita = round((df_p['Stake'] * df_p['Quota']).sum(), 2)
        
        c_p1, c_p2 = st.columns(2)
        c_p1.metric("Stake in Gioco", f"{t_scommesso} €")
        c_p2.metric("Vincita Potenziale", f"{t_vincita} €")
        st.divider()

        for i, r in df_p.iterrows():
            # Recupero nome campionato e calcolo vincita
            camp_label = LEAGUE_NAMES.get(r['Sport_Key'], r['Sport_Key'])
            vinc_pot = round(float(r['Stake']) * float(r['Quota']), 2)
            
            # --- TESTATA RICHIESTA: Campionato e Giocata in GRASSETTO ---
            label_main = f"{r['Data Match']} | {r['Match']} | **{camp_label}** | **{r['Scelta']}** | Stake: {r['Stake']}€ | Pot: {vinc_pot}€"
            
            with st.expander(label_main):
                st.write(f"Bookmaker: {r['Bookmaker']} | Quota: @{r['Quota']}")
                b1, b2, b3 = st.columns(3)
                if b1.button("VINTO ✅", key=f"w_{i}", use_container_width=True): chiudi_gara(i, "VINTO", "MAN")
                if b2.button("PERSO ❌", key=f"l_{i}", use_container_width=True): chiudi_gara(i, "PERSO", "MAN")
                if b3.button("ELIMINA 🗑️", key=f"d_{i}", use_container_width=True): salva_db(df_attuale.drop(i)); st.rerun()
    else:
        st.info("Nessuna scommessa pendente.")

# --- TAB 3: FISCALE (METRICHE COLORATE) ---
with t3:
    if not df_attuale.empty:
        df_stats = df_attuale.copy()
        df_stats[['Stake', 'Quota', 'Profitto']] = df_stats[['Stake', 'Quota', 'Profitto']].apply(pd.to_numeric, errors='coerce').fillna(0)
        df_chiuse = df_stats[df_stats['Esito'].isin(["VINTO", "PERSO"])]
        
        profitto_netto = round(df_chiuse['Profitto'].sum(), 2)
        t_scommesso_st = round(df_chiuse['Stake'].sum(), 2)
        t_incassato = round(df_chiuse[df_chiuse['Esito'] == "VINTO"]['Stake'].sum() + df_chiuse[df_chiuse['Esito'] == "VINTO"]['Profitto'].sum(), 2)
        roi = round((profitto_netto/t_scommesso_st*100), 2) if t_scommesso_st > 0 else 0

        st.subheader("📈 Performance Generale")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Profitto Netto", f"{profitto_netto} €", delta=f"{profitto_netto} €", delta_color="normal" if profitto_netto >= 0 else "inverse")
        m2.metric("Win Rate", f"{round((len(df_chiuse[df_chiuse['Esito']=='VINTO'])/len(df_chiuse)*100),1) if len(df_chiuse)>0 else 0} %")
        m3.metric("Goal Target", f"{OBIETTIVO_TARGET} €")
        m4.metric("Giocate Chiuse", len(df_chiuse))
        
        c_v1, c_v2, c_v3 = st.columns(3)
        c_v1.metric("Volume Scommesso", f"{t_scommesso_st} €")
        c_v2.metric("Totale Incassato", f"{t_incassato} €")
        c_v3.metric("ROI Medio", f"{roi} %", delta=f"{roi} %", delta_color="normal" if roi >= 0 else "inverse")

        st.divider()
        st.dataframe(df_stats.sort_index(ascending=False), use_container_width=True)
