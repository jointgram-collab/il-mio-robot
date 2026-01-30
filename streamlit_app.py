import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="AI SNIPER V13.7 - PRO", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #11141a; border-right: 1px solid #30363d; }
    
    /* Box Statistiche (Portafoglio) */
    .metric-container { display: flex; gap: 20px; margin-bottom: 20px; }
    .metric-box { 
        flex: 1; background: #1c2128; padding: 25px; border-radius: 12px; 
        border: 1px solid #30363d; text-align: center;
    }
    .metric-label { color: #8b949e; font-size: 14px; font-weight: 600; text-transform: uppercase; }
    .metric-value { font-size: 32px; font-weight: 800; margin-top: 10px; }

    /* Card Scanner (Stile Originale) */
    .scan-card {
        background: #161b22; border-radius: 10px; border: 1px solid #30363d;
        padding: 15px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;
    }
    .card-info { flex-grow: 1; }
    .card-title { color: #ffffff; font-size: 18px; font-weight: bold; margin-bottom: 5px; }
    .card-bet { color: #58a6ff; font-size: 20px; font-weight: 800; }
    .card-meta { color: #8b949e; font-size: 13px; margin-top: 8px; }
    .val-neon { color: #39d353; font-weight: bold; }
    .stake-gold { color: #ffc107; font-weight: bold; }

    /* API Progress Bar */
    .api-bar-bg { background: #30363d; height: 6px; border-radius: 3px; margin-top: 8px; }
    .api-bar-fill { background: #39d353; height: 100%; border-radius: 3px; box-shadow: 0 0 10px #39d353; }
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGICA DI MATCHING (EUROPA LEAGUE FIX) ---
def clean_team_name(name):
    """Pulisce i nomi per il confronto (es. 'Panathinaikos FC' -> 'PANATHINAIKOS')"""
    name = name.upper()
    # Rimuove sigle e suffissi comuni
    for s in [" FC", " AS", " AC", " SS", " CF", " FK", " UNITED", " CITY", "TOWN", " CLUB"]:
        name = name.replace(s, "")
    # Rimuove caratteri non alfanumerici
    return "".join(re.findall(r'[A-Z0-9]', name))

# --- 3. GESTIONE DATI ---
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

# --- 4. FUNZIONE AGGIORNA (VERSIONE DEFINITIVA) ---
def check_results():
    df = carica_db()
    if df.empty: return
    pendenti = df[df['Esito'] == "Pendente"]
    if pendenti.empty: return
    
    cambiamenti = False
    with st.spinner("🔄 Analisi API in corso..."):
        for skey in pendenti['Sport_Key'].unique():
            res = requests.get(f'https://api.the-odds-api.com/v4/sports/{skey}/scores/', params={'api_key': API_KEY, 'daysFrom': 3})
            if res.status_code == 200:
                scores = res.json()
                for idx, row in pendenti[pendenti['Sport_Key'] == skey].iterrows():
                    m_parts = row['Match'].split('-')
                    if len(m_parts) < 2: continue
                    
                    db_h, db_a = clean_team_name(m_parts[0]), clean_team_name(m_parts[1])
                    
                    # Ricerca flessibile nell'API
                    match = next((m for m in scores if (db_h in clean_team_name(m['home_team']) or clean_team_name(m['home_team']) in db_h) 
                                 and (db_a in clean_team_name(m['away_team']) or clean_team_name(m['away_team']) in db_a)), None)
                    
                    if match and match.get('scores'):
                        try:
                            s = match['scores']
                            h_score = int(next(x['score'] for x in s if x['name'] == match['home_team']))
                            a_score = int(next(x['score'] for x in s if x['name'] == match['away_team']))
                            tot = h_score + a_score
                            vinto = tot > 2.5 if row['Scelta'] == "OVER 2.5" else tot < 2.5
                            
                            df.at[idx, 'Esito'] = "VINTO" if vinto else "PERSO"
                            df.at[idx, 'Risultato'] = f"{h_score}-{a_score}"
                            q, stk = float(row['Quota']), float(row['Stake'])
                            df.at[idx, 'Profitto'] = round((stk * q) - stk, 2) if vinto else -stk
                            cambiamenti = True
                        except: continue
    if cambiamenti:
        salva_db(df)
        st.success("Risultati aggiornati!")
        st.rerun()

# --- 5. SIDEBAR ---
df_attuale = carica_db()
with st.sidebar:
    st.markdown('<h2 style="color:white; margin-bottom:20px;">🔥 AI SNIPER Status</h2>', unsafe_allow_html=True)
    rem = st.session_state.get('api_rem', "438")
    st.markdown(f"""
        <div style="background:#1c2128; padding:15px; border-radius:8px; border:1px solid #444c56;">
            <div style="display:flex; justify-content:space-between; font-size:14px;">
                <span style="color:#8b949e;">Crediti Residui:</span><span style="color:white; font-weight:bold;">{rem}</span>
            </div>
            <div class="api-bar-bg"><div class="api-bar-fill" style="width:20%;"></div></div>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    budget = st.number_input("Cassa (€)", value=500.0)
    kelly = st.slider("Rischio (Kelly %)", 0.05, 0.50, 0.20)

# --- 6. INTERFACCIA ---
st.title("🎯 AI SNIPER V13.7")
t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    st.markdown("### 🔍 Opportunità del Momento")
    # Qui simuliamo una card per farti vedere il design ripristinato
    st.markdown(f"""
    <div class="scan-card">
        <div class="card-info">
            <div class="card-title">⚽ Juventus - Inter <small style="color:#8b949e; float:right;">IT SERIE A | 20:45</small></div>
            <div class="card-bet">OVER 2.5 @ 1.95</div>
            <div class="card-meta">
                💰 STAKE: <span class="stake-gold">15.40€</span> &nbsp;&nbsp; 
                🔥 VALORE: <span class="val-neon">+5.2%</span> &nbsp;&nbsp; 
                🏛️ BOOK: Bet365
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("➕ AGGIUNGI AL PORTAFOGLIO (Simulazione)", use_container_width=True):
        st.toast("Match aggiunto!")

with t2:
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"] if not df_attuale.empty else pd.DataFrame()
    
    # BOX STATISTICHE (RIPRISTINATI)
    tot_imp = round(df_p['Stake'].astype(float).sum(), 2) if not df_p.empty else 0.0
    rit_pot = round((df_p['Stake'].astype(float) * df_p['Quota'].astype(float)).sum(), 2) if not df_p.empty else 0.0
    
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-box">
            <div class="metric-label">Totale Impegnato</div>
            <div class="metric-value" style="color:#ffc107;">{tot_imp} €</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">Ritorno Potenziale</div>
            <div class="metric-value" style="color:#39d353;">{rit_pot} €</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.button("🔄 AGGIORNA RISULTATI", on_click=check_results, use_container_width=True)
    
    if not df_p.empty:
        for idx, row in df_p.iterrows():
            with st.container():
                c1, c2 = st.columns([9, 1])
                c1.markdown(f"""
                <div style="background:#161b22; padding:10px; border-radius:5px; border-left:4px solid #58a6ff; margin-bottom:5px;">
                    📅 {row['Data Match']} | <b>{row['Match']}</b> | {row['Scelta']} @{row['Quota']} | {row['Stake']}€
                </div>
                """, unsafe_allow_html=True)
                if c2.button("🗑️", key=f"del_{idx}"):
                    salva_db(df_attuale.drop(idx))
                    st.rerun()
    else:
        st.info("Portafoglio vuoto.")

with t3:
    st.header("📊 Resoconto Fiscale")
    if not df_attuale.empty:
        vinto = df_attuale[df_attuale['Esito'] == "VINTO"]['Profitto'].sum()
        perso = abs(df_attuale[df_attuale['Esito'] == "PERSO"]['Profitto'].sum())
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Vinto", f"{round(vinto,2)} €")
        c2.metric("Perso", f"{round(perso,2)} €")
        c3.metric("Netto", f"{round(vinto-perso,2)} €", delta=f"{round(vinto-perso,2)} €")
        
        st.dataframe(df_attuale.sort_index(ascending=False), use_container_width=True)
