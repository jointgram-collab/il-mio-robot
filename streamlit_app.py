import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- UI & STYLE (Basato sui tuoi screenshot) ---
st.set_page_config(page_title="AI SNIPER V13.9 - ULTRA FORCE", layout="wide")

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

# --- LOGICA DI PULIZIA ---
def ultra_clean(text):
    if not text: return ""
    text = text.upper()
    for s in [" FC", " AS", " AC", " SS", " CF", " FK", " UNITED", " CITY", " CLUB", " REAL"]:
        text = text.replace(s, "")
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

# --- FUNZIONE AGGIORNA 13.9 (LOGICA AGGRESSIVA) ---
def force_update_results():
    df = carica_db()
    if df.empty: return
    pendenti = df[df['Esito'] == "Pendente"]
    if pendenti.empty: return
    
    cambiamenti = False
    with st.spinner("🚀 Forzatura aggiornamento in corso..."):
        for skey in pendenti['Sport_Key'].unique():
            # Chiediamo i punteggi degli ultimi 3 giorni
            res = requests.get(f'https://api.the-odds-api.com/v4/sports/{skey}/scores/', 
                             params={'api_key': API_KEY, 'daysFrom': 3})
            
            if res.status_code == 200:
                scores_api = res.json()
                for idx, row in pendenti[pendenti['Sport_Key'] == skey].iterrows():
                    m_parts = row['Match'].split('-')
                    if len(m_parts) < 2: continue
                    
                    db_h, db_a = ultra_clean(m_parts[0]), ultra_clean(m_parts[1])
                    
                    # Cerchiamo il match
                    match_api = next((m for m in scores_api if 
                                     (db_h in ultra_clean(m['home_team']) or ultra_clean(m['home_team']) in db_h) and 
                                     (db_a in ultra_clean(m['away_team']) or ultra_clean(m['away_team']) in db_a)), None)
                    
                    # LOGICA AGGRESSIVA: Se trovo punteggi, aggiorno a prescindere dal flag 'completed'
                    if match_api and match_api.get('scores'):
                        try:
                            s = match_api['scores']
                            h_score = int(next(x['score'] for x in s if x['name'] == match_api['home_team']))
                            a_score = int(next(x['score'] for x in s if x['name'] == match_api['away_team']))
                            
                            # Calcolo Esito
                            tot_gol = h_score + a_score
                            is_over = "OVER" in row['Scelta'].upper()
                            vinto = tot_gol > 2.5 if is_over else tot_gol < 2.5
                            
                            df.at[idx, 'Esito'] = "VINTO" if vinto else "PERSO"
                            df.at[idx, 'Risultato'] = f"{h_score}-{a_score}"
                            q, stk = float(row['Quota']), float(row['Stake'])
                            df.at[idx, 'Profitto'] = round((stk * q) - stk, 2) if vinto else -stk
                            cambiamenti = True
                        except: continue

    if cambiamenti:
        salva_db(df)
        st.success("✅ Partite chiuse con successo!")
        st.rerun()
    else:
        st.error("❌ Nessun punteggio trovato. Verifica che i nomi nel DB siano corretti.")

# --- UI PRINCIPALE ---
st.title("🎯 AI SNIPER V13.9")
df_attuale = carica_db()

# Tabella Statistiche (come image_8e6bb7.png)
df_p = df_attuale[df_attuale['Esito'] == "Pendente"] if not df_attuale.empty else pd.DataFrame()
tot_imp = round(df_p['Stake'].astype(float).sum(), 2) if not df_p.empty else 0.0
rit_pot = round((df_p['Stake'].astype(float) * df_p['Quota'].astype(float)).sum(), 2) if not df_p.empty else 0.0

st.markdown(f"""
<div class="metric-container">
    <div class="metric-box">
        <div style="color:#8b949e; font-weight:600;">TOTALE IMPEGNATO</div>
        <div class="metric-value" style="color:#ffc107;">{tot_imp} €</div>
    </div>
    <div class="metric-box">
        <div style="color:#8b949e; font-weight:600;">RITORNO POTENZIALE</div>
        <div class="metric-value" style="color:#39d353;">{rit_pot} €</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.button("🔥 FORZA CHIUSURA SCOMMESSE", on_click=force_update_results, use_container_width=True)

st.write("### Portafoglio Attuale")
st.dataframe(df_attuale, use_container_width=True)
