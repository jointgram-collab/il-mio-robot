import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V13.8 - FIXED", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #11141a; border-right: 1px solid #30363d; }
    .metric-container { display: flex; gap: 20px; margin-bottom: 20px; }
    .metric-box { 
        flex: 1; background: #1c2128; padding: 25px; border-radius: 12px; 
        border: 1px solid #30363d; text-align: center;
    }
    .metric-value { font-size: 32px; font-weight: 800; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- MOTORE DI PULIZIA NOMI (IL CUORE DEL FIX) ---
def ultra_clean(text):
    """Pulisce radicalmente i nomi delle squadre per il confronto."""
    if not text: return ""
    text = text.upper()
    # Rimuove sigle comuni che creano discrepanze
    sigle = [" FC", " AS", " AC", " SS", " CF", " FK", " UNITED", " CITY", "TOWN", " CLUB", " REAL", " DE "]
    for s in sigle:
        text = text.replace(s, "")
    # Tiene solo lettere e numeri
    return "".join(re.findall(r'[A-Z0-9]', text))

# --- GESTIONE DATI ---
conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        return df.dropna(subset=["Match"]) if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

# --- FUNZIONE AGGIORNA POTENZIATA ---
def check_results_v13_8():
    df = carica_db()
    if df.empty: return
    pendenti = df[df['Esito'] == "Pendente"]
    if pendenti.empty:
        st.info("Nessuna scommessa pendente da controllare.")
        return
    
    cambiamenti = False
    with st.spinner("🔄 Analisi profonda dei risultati in corso..."):
        # Raggruppiamo per sport per risparmiare chiamate API
        for skey in pendenti['Sport_Key'].unique():
            res = requests.get(f'https://api.the-odds-api.com/v4/sports/{skey}/scores/', params={'api_key': API_KEY, 'daysFrom': 3})
            
            if res.status_code == 200:
                scores_api = res.json()
                for idx, row in pendenti[pendenti['Sport_Key'] == skey].iterrows():
                    m_parts = row['Match'].split('-')
                    if len(m_parts) < 2: continue
                    
                    # Pulizia nomi database
                    db_h = ultra_clean(m_parts[0])
                    db_a = ultra_clean(m_parts[1])
                    
                    # Cerca il match con logica "contiene"
                    match_trovato = None
                    for m_api in scores_api:
                        api_h = ultra_clean(m_api['home_team'])
                        api_a = ultra_clean(m_api['away_team'])
                        
                        # Controllo incrociato: se i nomi puliti combaciano o sono contenuti l'uno nell'altro
                        if (db_h in api_h or api_h in db_h) and (db_a in api_a or api_a in db_a):
                            match_trovato = m_api
                            break
                    
                    if match_trovato and match_trovato.get('scores'):
                        try:
                            s = match_trovato['scores']
                            h_score = int(next(x['score'] for x in s if x['name'] == match_trovato['home_team']))
                            a_score = int(next(x['score'] for x in s if x['name'] == match_trovato['away_team']))
                            
                            tot_gol = h_score + a_score
                            is_over = "OVER 2.5" in row['Scelta'].upper()
                            vinto = tot_gol > 2.5 if is_over else tot_gol < 2.5
                            
                            df.at[idx, 'Esito'] = "VINTO" if vinto else "PERSO"
                            df.at[idx, 'Risultato'] = f"{h_score}-{a_score}"
                            
                            q = float(row['Quota'])
                            stk = float(row['Stake'])
                            df.at[idx, 'Profitto'] = round((stk * q) - stk, 2) if vinto else -stk
                            cambiamenti = True
                        except Exception as e:
                            continue

    if cambiamenti:
        salva_db(df)
        st.success(f"✅ Aggiornati {df[df['Esito'] != 'Pendente'].shape[0]} risultati!")
        st.rerun()
    else:
        st.warning("⚠️ L'API ha restituito i dati ma i match non sono ancora marcati come conclusi con punteggio finale.")

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V13.8")
df_attuale = carica_db()

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t2:
    # Mostriamo i box statistiche basati sulle immagini
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"] if not df_attuale.empty else pd.DataFrame()
    tot_imp = round(df_p['Stake'].astype(float).sum(), 2) if not df_p.empty else 0.0
    rit_pot = round((df_p['Stake'].astype(float) * df_p['Quota'].astype(float)).sum(), 2) if not df_p.empty else 0.0

    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-box">
            <div style="color:#8b949e;">TOTALE IMPEGNATO</div>
            <div class="metric-value" style="color:#ffc107;">{tot_imp} €</div>
        </div>
        <div class="metric-box">
            <div style="color:#8b949e;">RITORNO POTENZIALE</div>
            <div class="metric-value" style="color:#39d353;">{rit_pot} €</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.button("🔄 FORZA AGGIORNAMENTO RISULTATI", on_click=check_results_v13_8, use_container_width=True)
    
    if not df_p.empty:
        st.dataframe(df_p, use_container_width=True)
    else:
        st.info("Tutti i risultati sono aggiornati.")

with t3:
    st.dataframe(df_attuale, use_container_width=True)
