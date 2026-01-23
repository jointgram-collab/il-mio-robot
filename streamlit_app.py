import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI COMPATTA ---
st.set_page_config(page_title="SNIPER COMPACT V12.3", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0f1116 !important; }
    label, p, span, .stMarkdown { color: #ffffff !important; font-size: 14px !important; }
    
    /* Riga compatta */
    .compact-row {
        background: rgba(255, 255, 255, 0.03);
        padding: 8px 15px;
        border-radius: 8px;
        margin-bottom: 5px;
        border-left: 3px solid #00ff88;
        display: flex;
        align-items: center;
    }
    
    /* Pulsanti compatti */
    .stButton > button {
        background: #00ff88 !important;
        color: #000000 !important;
        font-weight: bold !important;
        border-radius: 5px !important;
        height: 35px !important;
        padding: 0px 20px !important;
    }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def carica_db():
    try: return conn.read(worksheet="Giocate", ttl="0").dropna(how='all')
    except: return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto"])

def salva_db(df): conn.update(worksheet="Giocate", data=df)

def aggiungi_a_cloud(match, scelta, quota, stake, book, data):
    df_attuale = carica_db()
    nuova = {"Data Match": data, "Match": match, "Scelta": scelta, "Quota": quota, "Stake": stake, "Bookmaker": book, "Esito": "Pendente", "Profitto": 0.0}
    df_finale = pd.concat([df_attuale, pd.DataFrame([nuova])], ignore_index=True)
    salva_db(df_finale)
    st.toast(f"✅ {match} AGGIUNTO")

# --- INTERFACCIA ---
st.markdown("### 🎯 SNIPER <span style='color:#00ff88'>COMPACT</span>", unsafe_allow_html=True)

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    c1, c2, c3 = st.columns([2, 2, 1])
    budget = c1.number_input("Cassa €", value=1000.0)
    risk = c2.slider("Rischio", 0.1, 0.5, 0.2)
    
    leagues = {"Serie A": "soccer_italy_serie_a", "Champions": "soccer_uefa_champions_league", "Premier": "soccer_england_league_1"}
    sel_league = st.selectbox("Campionato", list(leagues.keys()))

    if st.button("🚀 AVVIA"):
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/', 
                           params={'api_key': '01f1c8f2a314814b17de03eeb6c53623', 'regions': 'eu', 'markets': 'totals'})
        if res.status_code == 200: st.session_state['api_data'] = res.json()

    if 'api_data' in st.session_state:
        st.markdown("---")
        for m in st.session_state['api_data']:
            home, away = m['home_team'], m['away_team']
            date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
            
            if m.get('bookmakers'):
                bk = m['bookmakers'][0]
                # RIGA COMPATTA
                col_data, col_match, col_odd, col_btn = st.columns([1, 3, 1.5, 1])
                
                col_data.markdown(f"<small>{date_m}</small>", unsafe_allow_html=True)
                col_match.markdown(f"**{home}-{away}**")
                col_odd.markdown(f"<span style='color:#00ff88'>OV2.5 @2.00</span>", unsafe_allow_html=True)
                
                btn_key = f"add_{home}_{away}_{date_m}".replace(" ", "_")
                if col_btn.button("ADD", key=btn_key):
                    aggiungi_a_cloud(f"{home}-{away}", "OVER 2.5", 2.0, 10.0, bk['title'], date_m)
                st.divider()

# --- TAB PORTAFOGLIO & FISCALE (Mantenute stabili) ---
with t2:
    st.subheader("💼 Operazioni Pendenti")
    df_c = carica_db()
    pendenti = df_c[df_c['Esito'] == "Pendente"]
    for i, r in pendenti.iterrows():
        with st.expander(f"📌 {r['Match']} - {r['Stake']}€"):
            c1, c2, c3 = st.columns(3)
            if c1.button("✅", key=f"w_{i}"):
                df_c.at[i, 'Esito'] = "VINTO"; df_c.at[i, 'Profitto'] = round((r['Stake']*r['Quota'])-r['Stake'], 2)
                salva_db(df_c); st.rerun()
            if c2.button("❌", key=f"l_{i}"):
                df_c.at[i, 'Esito'] = "PERSO"; df_c.at[i, 'Profitto'] = -r['Stake']
                salva_db(df_c); st.rerun()
            if c3.button("🗑️", key=f"del_{i}"):
                df_c = df_c.drop(i); salva_db(df_c); st.rerun()

with t3:
    df_f = carica_db()
    if not df_f.empty:
        prof = round(df_f['Profitto'].sum(), 2)
        st.metric("PROFITTO NETTO", f"{prof} €")
        st.dataframe(df_f[["Data Match", "Match", "Esito", "Profitto"]], use_container_width=True)
