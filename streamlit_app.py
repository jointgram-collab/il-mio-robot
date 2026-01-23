import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="AI SNIPER V11 - Cloud Sync", layout="wide")

# --- CONNESSIONE AL DATABASE GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carica_db():
    try:
        # Legge i dati dal foglio Google
        return conn.read(worksheet="Giocate", ttl="0")
    except:
        # Se il foglio è vuoto, crea la struttura
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto"])

def salva_giocata(nuova_giocata):
    df_attuale = carica_db()
    # Rimuove righe vuote o corrotte
    df_attuale = df_attuale.dropna(how='all')
    nuova_riga = pd.DataFrame([nuova_giocata])
    df_finale = pd.concat([df_attuale, nuova_riga], ignore_index=True)
    # Sovrascrive il foglio Google con i nuovi dati
    conn.update(worksheet="Giocate", data=df_finale)

# --- INIZIALIZZAZIONE ---
if 'ultimi_risultati' not in st.session_state:
    st.session_state['ultimi_risultati'] = []

# --- LOGICA CALLBACK ---
def btn_aggiungi(match, scelta, quota, stake, book, data):
    giocata = {
        "Data Match": data, "Match": match, "Scelta": scelta,
        "Quota": quota, "Stake": stake, "Bookmaker": book,
        "Esito": "Pendente", "Profitto": 0.0
    }
    salva_giocata(giocata)
    st.toast(f"✅ Sincronizzato su Cloud: {match}")

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11 - Cloud Sync")
t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO CLOUD", "📊 FISCALE"])

with t1:
    # ... (Qui inserisci la stessa logica di scansione della V9.3) ...
    # Ricordati di usare 'on_click=btn_aggiungi' nel tasto AGGIUNGI
    pass

with t2:
    st.subheader("💼 Giocate Sincronizzate (PC/Smartphone)")
    df_cloud = carica_db()
    
    if not df_cloud.empty:
        pendenti = df_cloud[df_cloud['Esito'] == "Pendente"]
        st.info(f"💰 Totale Impegnato: {round(pendenti['Stake'].sum(), 2)}€")
        
        for i, r in pendenti.iterrows():
            with st.expander(f"📌 {r['Match']} - {r['Scelta']}"):
                c1, c2, c3 = st.columns(3)
                if c1.button("✅ VINTO", key=f"w_{i}"):
                    # Logica per aggiornare l'esito nel DF e salvare
                    df_cloud.at[i, 'Esito'] = "VINTO"
                    df_cloud.at[i, 'Profitto'] = round((r['Stake']*r['Quota'])-r['Stake'], 2)
                    conn.update(worksheet="Giocate", data=df_cloud)
                    st.rerun()
                # ... (Aggiungi qui i tasti PERSO ed ELIMINA con la stessa logica) ...
    else:
        st.info("Nessuna giocata trovata nel database Google.")
