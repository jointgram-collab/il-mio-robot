import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V11.23 - Pro Dashboard", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

BK_EURO_AUTH = {
    "Bet365": "https://www.bet365.it", "Snai": "https://www.snai.it",
    "Better": "https://www.lottomatica.it/scommesse", "Planetwin365": "https://www.planetwin365.it",
    "Eurobet": "https://www.eurobet.it", "Goldbet": "https://www.goldbet.it", 
    "Sisal": "https://www.sisal.it", "Bwin": "https://www.bwin.it",
    "William Hill": "https://www.williamhill.it", "888sport": "https://www.888sport.it"
}

# --- MOTORE DATABASE ---
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
        return df.dropna(subset=["Match"])
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db_completo(df):
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11.23")

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    with st.sidebar:
        st.header("⚙️ Parametri")
        budget_cassa = st.number_input("Budget Attuale (€)", value=250.0)
        rischio = st.slider("Kelly Frazionario", 0.05, 0.50, 0.20)
        soglia_val = st.slider("Valore Minimo %", 0, 15, 5) / 100
    
    # ... (Logica Scanner V11.22 integrata) ...
    st.info("Usa lo scanner per trovare match con valore > 5%")

with t2:
    st.subheader("💼 Gestione Capitale Esposto")
    df_p = carica_db()
    pendenti = df_p[df_p['Esito'] == "Pendente"]
    
    if not pendenti.empty:
        esposizione = round(pendenti['Stake'].sum(), 2)
        rientro_pot = round((pendenti['Stake'] * pendenti['Quota']).sum(), 2)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Capitale in gioco", f"{esposizione} €")
        c2.metric("Rientro Potenziale", f"{rientro_pot} €")
        c3.metric("Profitto Potenziale", f"{round(rientro_pot - esposizione, 2)} €", delta_color="normal")
        
        st.write("---")
        for i, r in pendenti.iterrows():
            col_a, col_b, col_c = st.columns([3, 2, 1])
            col_a.write(f"📅 **{r['Data Match']}** | **{r['Match']}**\n{r['Scelta']} @{r['Quota']} ({r['Bookmaker']})")
            col_b.write(f"Puntata: **{r['Stake']}€**\nVincita: **{round(r['Stake']*r['Quota'], 2)}€**")
            if col_c.button("🗑️ Elimina", key=f"del_{i}"):
                salva_db_completo(df_p.drop(i))
                st.rerun()
    else:
        st.write("Nessuna scommessa in corso. Vai allo scanner!")

with t3:
    st.subheader("📊 Analisi Performance verso i 5.000€")
    df_f = carica_db()
    finiti = df_f[df_f['Esito'] != "Pendente"]
    
    if not finiti.empty:
        # Calcolo Metriche
        target = 5000.0
        profitto_netto = round(df_f['Profitto'].sum(), 2)
        mancante = round(target - profitto_netto, 2)
        win_rate = round((len(df_f[df_f['Esito'] == "VINTO"]) / len(finiti)) * 100, 1)
        
        # Dashboard Superiore
        col_f1, col_f2, col_f3 = st.columns(3)
        col_f1.metric("Profitto Netto", f"{profitto_netto} €", delta=f"{profitto_netto} €")
        col_f2.metric("Mancano al Target", f"{mancante} €")
        col_f3.metric("Win Rate", f"{win_rate} %")
        
        # Barra di avanzamento
        progress = min(max(profitto_netto / target, 0.0), 1.0)
        st.write(f"**Progresso Obiettivo 5.000€:** {round(progress*100, 1)}%")
        st.progress(progress)
        
        st.write("### 📜 Storico Dettagliato")
        # Visualizzazione tabella con colori (opzionale con dataframe)
        st.dataframe(df_f.sort_index(ascending=False), use_container_width=True)
    else:
        st.warning("Storico vuoto. Le partite appariranno qui dopo l'Auto-Check.")
