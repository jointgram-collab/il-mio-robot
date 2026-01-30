import streamlit as st
import pandas as pd
import requests
import time
import re
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="AI SNIPER V13.6 - ULTRA", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #11141a; border-right: 1px solid #30363d; }
    .sb-title { color: #ffffff !important; font-size: 18px; font-weight: 700; margin-bottom: 20px; }
    .api-container { background-color: #1c2128; padding: 15px; border-radius: 8px; border: 1px solid #444c56; }
    .api-bar-bg { background: #30363d; height: 8px; border-radius: 4px; margin-top: 10px; }
    .api-bar-fill { background: #39d353; height: 100%; border-radius: 4px; box-shadow: 0 0 8px #39d353; }
    .metric-card { background: #1c2128; padding: 20px; border-radius: 10px; border: 1px solid #30363d; text-align: center; }
    [data-testid="stWidgetLabel"] p { color: #ffffff !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGICA DI PULIZIA NOMI (SOLUZIONE EUROPA LEAGUE) ---
def clean_name(name):
    """Rimuove suffissi comuni per facilitare il matching dei risultati."""
    name = name.upper()
    suffixes = [
        " FC", " AS", " SS", " AC", " CF", " UD", " JSC", " FK", " GFE", 
        " BC", " CLUB", " DE FÚTBOL", "TOWN", "UNITED", "CITY"
    ]
    for s in suffixes:
        name = name.replace(s, "")
    return re.sub(r'\W+', '', name).strip()

# --- 3. FUNZIONI DATABASE ---
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

# --- 4. MOTORE AGGIORNAMENTO RISULTATI (POTENZIATO) ---
def check_results():
    df = carica_db()
    if df.empty: return
    
    pendenti = df[df['Esito'] == "Pendente"]
    if pendenti.empty:
        st.info("Nessuna scommessa pendente.")
        return
    
    cambiamenti = False
    with st.spinner("🔄 Analisi risultati in corso..."):
        for skey in pendenti['Sport_Key'].unique():
            url = f'https://api.the-odds-api.com/v4/sports/{skey}/scores/'
            res = requests.get(url, params={'api_key': API_KEY, 'daysFrom': 3})
            
            if res.status_code == 200:
                st.session_state['api_rem'] = res.headers.get('x-requests-remaining')
                scores = res.json()
                
                for idx, row in pendenti[pendenti['Sport_Key'] == skey].iterrows():
                    m_parts = row['Match'].split('-')
                    if len(m_parts) < 2: continue
                    
                    # Nomi puliti dal DB
                    db_t1, db_t2 = clean_name(m_parts[0]), clean_name(m_parts[1])
                    
                    # Cerca il match nell'API
                    match_data = None
                    for m in scores:
                        api_t1, api_t2 = clean_name(m['home_team']), clean_name(m['away_team'])
                        # Match se i team corrispondono (anche invertiti)
                        if (db_t1 in api_t1 or api_t1 in db_t1) and (db_t2 in api_t2 or api_t2 in db_t2):
                            match_data = m
                            break
                    
                    if match_data and match_data.get('scores'):
                        try:
                            s_list = match_data['scores']
                            h_score = int(next(x['score'] for x in s_list if x['name'] == match_data['home_team']))
                            a_score = int(next(x['score'] for x in s_list if x['name'] == match_data['away_team']))
                            tot = h_score + a_score
                            
                            vinto = tot > 2.5 if row['Scelta'] == "OVER 2.5" else tot < 2.5
                            
                            df.at[idx, 'Esito'] = "VINTO" if vinto else "PERSO"
                            df.at[idx, 'Risultato'] = f"{h_score}-{a_score}"
                            quota = float(row['Quota'])
                            stake = float(row['Stake'])
                            df.at[idx, 'Profitto'] = round((stake * quota) - stake, 2) if vinto else -stake
                            cambiamenti = True
                        except: continue
                        
    if cambiamenti:
        salva_db(df)
        st.success("✅ Risultati aggiornati con successo!")
        st.rerun()
    else:
        st.warning("⚠️ L'API non ha ancora i dati definitivi per questi match.")

# --- 5. SIDEBAR ---
df_attuale = carica_db()
with st.sidebar:
    st.markdown('<div class="sb-title">🔥 API Status</div>', unsafe_allow_html=True)
    rem = st.session_state.get('api_rem', "440")
    st.markdown(f"""
        <div class="api-container">
            <div style="display:flex; justify-content:space-between;">
                <span style="color:#8b949e;">Residui:</span>
                <span style="font-weight:bold;">{rem}</span>
            </div>
            <div class="api-bar-bg"><div class="api-bar-fill" style="width: 20%;"></div></div>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    budget = st.number_input("Budget Totale (€)", value=500.0)
    kelly = st.slider("Kelly Criterion", 0.05, 0.50, 0.20)
    val_min = st.slider("Valore Minimo %", 0, 15, 3) / 100

# --- 6. INTERFACCIA PRINCIPALE ---
st.title("🎯 AI SNIPER V13.6")

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    st.info("Logica Scanner Attiva - Seleziona un campionato per iniziare.")
    # Inserire qui la logica di visualizzazione card dello scanner

with t2:
    st.markdown("### 💼 Gestione Portafoglio")
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"] if not df_attuale.empty else pd.DataFrame()
    
    if not df_p.empty:
        # --- CRUSCOTTO STATISTICHE ---
        c1, c2 = st.columns(2)
        tot_imp = round(df_p['Stake'].astype(float).sum(), 2)
        rit_pot = round((df_p['Stake'].astype(float) * df_p['Quota'].astype(float)).sum(), 2)
        
        with c1:
            st.markdown(f"<div class='metric-card'><small>TOTALE IMPEGNATO</small><br><h2 style='color:#ffc107;'>{tot_imp} €</h2></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='metric-card'><small>RITORNO POTENZIALE</small><br><h2 style='color:#39d353;'>{rit_pot} €</h2></div>", unsafe_allow_html=True)
        
        st.button("🔄 AGGIORNA RISULTATI", on_click=check_results, use_container_width=True)
        
        # Tabella con tasto elimina
        for idx, row in df_p.iterrows():
            col_data, col_del = st.columns([10, 1])
            col_data.info(f"📅 {row['Data Match']} | **{row['Match']}** | {row['Scelta']} @{row['Quota']} | Stake: {row['Stake']}€")
            if col_del.button("🗑️", key=f"del_{idx}"):
                salva_db(df_attuale.drop(idx))
                st.rerun()
    else:
        st.info("Nessuna giocata pendente nel portafoglio.")

with t3:
    st.markdown("### 📊 Cruscotto Fiscale")
    if not df_attuale.empty:
        vinto = df_attuale[df_attuale['Esito'] == "VINTO"]['Profitto'].sum()
        perso = abs(df_attuale[df_attuale['Esito'] == "PERSO"]['Profitto'].sum())
        netto = vinto - perso
        
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Vinto Netto", f"{round(vinto,2)} €")
        m2.metric("❌ Perso", f"{round(perso,2)} €")
        m3.metric("📈 Profitto Totale", f"{round(netto,2)} €", delta=f"{round(netto,2)} €")
        
        st.divider()
        csv = df_attuale.to_csv(index=False).encode('utf-8')
        st.download_button("📥 SCARICA BACKUP CSV", csv, f"backup_{date.today()}.csv", use_container_width=True)
        
        st.write("#### Storico Completo")
        st.dataframe(df_attuale.sort_index(ascending=False), use_container_width=True)
