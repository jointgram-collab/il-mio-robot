import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="AI SNIPER V11.20 - Data Recovery", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

# --- FUNZIONI DATABASE RINFORZATE ---
def carica_db():
    try:
        # Forziamo il refresh totale dei dati (ttl=0)
        df = conn.read(worksheet="Giocate", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
        # Pulizia righe vuote per evitare errori di visualizzazione
        df = df.dropna(subset=["Match"])
        if "Risultato" not in df.columns: df["Risultato"] = "-"
        return df
    except Exception as e:
        st.error(f"Errore caricamento Cloud: {e}")
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db_sicuro(nuova_riga_df):
    # Recupera il DB attuale per non sovrascrivere
    db_attuale = carica_db()
    # Unisce i dati vecchi con i nuovi
    db_aggiornato = pd.concat([db_attuale, nuova_riga_df], ignore_index=True)
    # Salva la lista completa
    conn.update(worksheet="Giocate", data=db_aggiornato)
    st.cache_data.clear() # Svuota la cache locale

# ... (Manteniamo le funzioni get_totals_value e calc_stake della V11.19) ...

# --- AUTO-CHECK OTTIMIZZATO ---
def check_results():
    df = carica_db()
    pendenti = df[df['Esito'] == "Pendente"]
    if pendenti.empty:
        st.info("Nessuna giocata pendente.")
        return

    cambiamenti = False
    with st.spinner("🔄 Recupero dati dal Cloud..."):
        for sport_key in pendenti['Sport_Key'].unique():
            url_scores = f'https://api.the-odds-api.com/v4/sports/{sport_key}/scores/'
            res = requests.get(url_scores, params={'api_key': API_KEY, 'daysFrom': 3})
            if res.status_code == 200:
                scores_data = res.json()
                for i, r in pendenti[pendenti['Sport_Key'] == sport_key].iterrows():
                    m_res = next((m for m in scores_data if (f"{m['home_team']}-{m['away_team']}" == r['Match']) and m.get('completed')), None)
                    if m_res:
                        s = m_res['scores']
                        score_str = f"{s[0]['score']}-{s[1]['score']}"
                        total_goals = sum(int(x['score']) for x in s)
                        vinto = (r['Scelta'] == "OVER 2.5" and total_goals > 2.5) or (r['Scelta'] == "UNDER 2.5" and total_goals < 2.5)
                        df.at[i, 'Esito'] = "VINTO" if vinto else "PERSO"
                        df.at[i, 'Risultato'] = score_str
                        df.at[i, 'Profitto'] = round((r['Stake']*r['Quota'])-r['Stake'], 2) if vinto else -r['Stake']
                        cambiamenti = True
    if cambiamenti:
        conn.update(worksheet="Giocate", data=df)
        st.success("Tutte le partite del weekend sono state aggiornate!")
        st.rerun()

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11.20")
# ... (Resto dell'interfaccia scanner e portafoglio) ...

with t3:
    st.subheader("📊 Fiscale")
    # Forziamo il ricaricamento premendo un tasto se i dati mancano
    if st.button("🔌 RICONNETTI E SINCRONIZZA STORICO"):
        st.cache_data.clear()
        st.rerun()
        
    df_f = carica_db()
    if not df_f.empty:
        # Ordiniamo per data per vedere sempre le ultime in alto
        df_f = df_f.sort_index(ascending=False)
        prof = round(df_f['Profitto'].sum(), 2)
        st.metric("Profitto Netto Totale", f"{prof} €", delta=f"{round(5000-prof, 2)}€ al target")
        
        st.write("### 📜 Storico Completo (Weekend + Oggi)")
        st.dataframe(df_f)
