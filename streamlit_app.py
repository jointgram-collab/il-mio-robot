import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V11.38 - Goal Tracker", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
TARGET_FINALE = 5000.0  # Obiettivo della scalata

# --- MOTORE DATABASE ---
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
        df = df.dropna(subset=["Match"])
        df['dt_obj'] = pd.to_datetime(df['Data Match'] + f"/{date.today().year}", format="%d/%m %H:%M/%Y", errors='coerce')
        return df
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    if 'dt_obj' in df.columns: df = df.drop(columns=['dt_obj'])
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11.38")
df_f = carica_db()

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# ... [Tab 1 e 2 rimangono invariati come nella V11.37] ...

with t3:
    st.subheader("📊 Analisi Fiscale e Avanzamento Obiettivo")
    
    if not df_f.empty:
        # Calcoli Globali per l'Obiettivo (su tutto il database)
        tot_scommesso = round(df_f['Stake'].sum(), 2)
        tot_vinto_lordo = round(df_f[df_f['Esito'] == "VINTO"]['Profitto'].sum() + df_f[df_f['Esito'] == "VINTO"]['Stake'].sum(), 2)
        profitto_netto_reale = round(tot_vinto_lordo - tot_scommesso, 2)
        mancante_target = round(TARGET_FINALE - profitto_netto_reale, 2)
        percentuale_completamento = min(100.0, max(0.0, (profitto_netto_reale / TARGET_FINALE) * 100))

        # --- TESTATA OBIETTIVO ---
        st.info(f"🏆 **Obiettivo Scalata: 5.000€** | Attuale: **{profitto_netto_reale}€** | Mancano: **{mancante_target}€**")
        st.progress(percentuale_completamento / 100)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Totale Speso", f"{tot_scommesso} €")
        col2.metric("Totale Vinto (Lordo)", f"{tot_vinto_lordo} €")
        col3.metric("Profitto Netto", f"{profitto_netto_reale} €", delta=f"{profitto_netto_reale}€")
        
        st.divider()

        # --- FILTRO E STORICO ---
        df_valid = df_f.dropna(subset=['dt_obj'])
        s_range = st.date_input("Filtra Periodo:", [df_valid['dt_obj'].min().date() if not df_valid.empty else date.today(), date.today()])
        
        if len(s_range) == 2:
            mask = (df_f['dt_obj'].dt.date >= s_range[0]) & (df_f['dt_obj'].dt.date <= s_range[1])
            df_fil = df_f[mask].sort_index(ascending=False)
            
            for i, row in df_fil.iterrows():
                camp = row.get('Sport_Key', 'Vari')
                vincita_pot = round(row['Stake'] * row['Quota'], 2)
                
                if row['Esito'] == "VINTO":
                    st.success(f"🟢 **VINTO** | {row['Data Match']} | {row['Match']} | **{row['Scelta']} @{row['Quota']}** | Risultato: {row['Risultato']} | Profitto: +{row['Profitto']}€")
                elif row['Esito'] == "PERSO":
                    st.error(f"🔴 **PERSO** | {row['Data Match']} | {row['Match']} | **{row['Scelta']} @{row['Quota']}** | Risultato: {row['Risultato']} | Perdita: {row['Profitto']}€")
                else:
                    # Visualizzazione Pendente con possibile vincita
                    st.warning(f"🟡 **PENDENTE** | {row['Data Match']} | {row['Match']} | **{row['Scelta']} @{row['Quota']}** | 💰 Possibile Rientro: **{vincita_pot}€**")
    else:
        st.info("Database vuoto. Inizia a giocare per vedere le statistiche!")
