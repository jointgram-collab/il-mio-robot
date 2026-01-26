import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="AI SNIPER V11.24 - Pro Analytics", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

# --- FUNZIONI CORE ---
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
        
        # Pulizia e conversione date per il filtro
        df = df.dropna(subset=["Match"])
        # Cerchiamo di convertire la colonna Data Match in formato datetime per il filtro
        # Nota: assumiamo il formato salvato "GG/MM HH:MM" dell'anno corrente
        df['dt_obj'] = pd.to_datetime(df['Data Match'] + f"/{date.today().year}", format="%d/%m/%Y %H:%M", errors='coerce')
        return df
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    if 'dt_obj' in df.columns: df = df.drop(columns=['dt_obj'])
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11.24")

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# ... [Tab 1 e Tab 2 rimangono invariati rispetto alla V11.23] ...

with t3:
    st.subheader("📊 Analisi Performance & Filtri Temporali")
    
    df_f = carica_db()
    
    if not df_f.empty:
        # --- FILTRO DATE ---
        col_d1, col_d2 = st.columns(2)
        min_date = df_f['dt_obj'].min().date() if not df_f['dt_obj'].isnull().all() else date.today()
        max_date = date.today()
        
        filtro_date = col_d1.date_input("Seleziona Range Temporale", 
                                        value=(min_date, max_date),
                                        min_value=min_date,
                                        max_value=max_date + pd.Timedelta(days=365))
        
        # Applicazione filtro
        if isinstance(filtro_date, tuple) and len(filtro_date) == 2:
            start_date, end_date = filtro_date
            mask = (df_f['dt_obj'].dt.date >= start_date) & (df_f['dt_obj'].dt.date <= end_date)
            df_filtrato = df_f[mask]
        else:
            df_filtrato = df_f

        # --- CALCOLI DINAMICI ---
        partite_concluse = df_filtrato[df_filtrato['Esito'] != "Pendente"]
        
        tot_scommesso = round(partite_concluse['Stake'].sum(), 2)
        # La somma vinta è il profitto + lo stake delle vinte
        tot_vinto = round(partite_concluse[partite_concluse['Esito'] == "VINTO"]['Profitto'].sum() + 
                          partite_concluse[partite_concluse['Esito'] == "VINTO"]['Stake'].sum(), 2)
        profitto_netto = round(partite_concluse['Profitto'].sum(), 2)
        roi = round((profitto_netto / tot_scommesso * 100), 2) if tot_scommesso > 0 else 0
        
        # --- DASHBOARD METRICHE ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Totale Scommesso", f"{tot_scommesso} €")
        m2.metric("Totale Rientrato", f"{tot_vinto} €", delta=f"{profitto_netto} € Netto")
        m3.metric("ROI Periodo", f"{roi} %")
        m4.metric("Target 5000€", f"{round(5000 - df_f['Profitto'].sum(), 2)} €")

        st.divider()
        
        # Tabella Storico Filtrata
        st.write(f"📂 Mostrando **{len(df_filtrato)}** operazioni nel periodo selezionato")
        st.dataframe(df_filtrato.drop(columns=['dt_obj']).sort_index(ascending=False), use_container_width=True)
        
        # Export pulsante
        csv = df_filtrato.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Scarica Report CSV", data=csv, file_name=f"report_sniper_{date.today()}.csv", mime='text/csv')

    else:
        st.info("Nessun dato disponibile nel database per generare il report.")
