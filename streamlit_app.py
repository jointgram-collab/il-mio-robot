import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE ELITE UI ---
st.set_page_config(page_title="SNIPER ELITE V12.2", layout="wide")

# CSS PER VISIBILITÀ TOTALE E LOOK PREMIUM
st.markdown("""
    <style>
    /* Forza sfondo scuro e testi chiari ovunque */
    [data-testid="stAppViewContainer"], .main {
        background-color: #0f1116 !important;
        color: #ffffff !important;
    }
    
    /* Forza testi bianchi per sidebar, widget e tabelle */
    label, p, span, .stMarkdown, [data-testid="stExpander"] {
        color: #ffffff !important;
    }

    /* Card Stile Glassmorphism con bordo luminoso */
    div.stBox, [data-testid="stExpander"], .stMetric {
        background: rgba(30, 34, 45, 0.9) !important;
        border: 1px solid rgba(0, 255, 136, 0.3) !important;
        border-radius: 15px !important;
    }

    /* Metriche Giganti Verde Neon */
    [data-testid="stMetricValue"] {
        font-size: 40px !important;
        font-weight: 900 !important;
        color: #00ff88 !important;
    }

    /* Pulsanti ad alto contrasto */
    .stButton > button {
        background: #1e222d !important;
        color: #00ff88 !important;
        border: 2px solid #00ff88 !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        height: 50px !important;
        width: 100% !important;
    }
    
    /* Link cliccabili */
    a { color: #00ff88 !important; text-decoration: underline !important; }

    /* Fix per input form (scritte nere su bianco) */
    input { color: #000000 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGICA CORE ---
conn = st.connection("gsheets", type=GSheetsConnection)
BK_URLS = {"Bet365": "https://www.bet365.it", "Snai": "https://www.snai.it", "Better": "https://www.lottomatica.it/scommesse", "Planetwin365": "https://www.planetwin365.it"}

def get_bk_link(name):
    url = BK_URLS.get(name, f"https://www.google.com/search?q={name}")
    return f"[{name}]({url})"

def carica_db():
    try: return conn.read(worksheet="Giocate", ttl="0").dropna(how='all')
    except: return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto"])

def salva_db(df): conn.update(worksheet="Giocate", data=df)

def aggiungi_a_cloud(match, scelta, quota, stake, book, data):
    df_attuale = carica_db()
    nuova_giocata = {"Data Match": data, "Match": match, "Scelta": scelta, "Quota": quota, "Stake": stake, "Bookmaker": book, "Esito": "Pendente", "Profitto": 0.0}
    df_finale = pd.concat([df_attuale, pd.DataFrame([nuova_giocata])], ignore_index=True)
    salva_db(df_finale)
    st.toast("✅ SINCRONIZZATO!")

# --- INTERFACCIA ---
st.markdown("# 🎯 SNIPER <span style='color:#00ff88'>ELITE</span>", unsafe_allow_html=True)

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    with st.expander("⚙️ IMPOSTAZIONI STRATEGIA"):
        c_p1, c_p2 = st.columns(2)
        budget = c_p1.number_input("Cassa (€)", value=1000.0)
        risk = c_p2.slider("Aggressività", 0.1, 0.5, 0.2)
        
    leagues = {"Champions League": "soccer_uefa_champions_league", "Serie A": "soccer_italy_serie_a", "Premier League": "soccer_england_league_1"}
    sel_league = st.selectbox("Seleziona Campionato:", list(leagues.keys()))

    if st.button("🚀 AVVIA ANALISI"):
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/', 
                           params={'api_key': '01f1c8f2a314814b17de03eeb6c53623', 'regions': 'eu', 'markets': 'totals'})
        if res.status_code == 200:
            st.session_state['api_data'] = res.json()
            st.success("Dati caricati!")

    if 'api_data' in st.session_state:
        for m in st.session_state['api_data']:
            home, away = m['home_team'], m['away_team']
            date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
            
            # Simuliamo il calcolo valore (prendiamo il primo bookmaker per brevità)
            if m.get('bookmakers'):
                bk = m['bookmakers'][0]
                st.markdown(f"""
                    <div style='background:rgba(255,255,255,0.05); padding:15px; border-radius:15px; margin-bottom:10px; border: 1px solid #00ff88;'>
                        <h3 style='margin:0; color:#ffffff;'>{home} - {away}</h3>
                        <p style='color:#00ff88; margin:0;'>DATA: {date_m} | BK: {bk['title']}</p>
                    </div>
                """, unsafe_allow_html=True)
                
                # CHIAVE UNICA PER IL BOTTONE (Risolve l'errore DuplicateElementKey)
                btn_key = f"add_{home}_{away}_{date_m}".replace(" ", "_")
                if st.button(f"📥 AGGIUNGI {home}", key=btn_key):
                    aggiungi_a_cloud(f"{home}-{away}", "OVER 2.5", 2.0, 10.0, bk['title'], date_m)

with t2:
    st.subheader("💼 Operazioni Pendenti")
    df_c = carica_db()
    pendenti = df_c[df_c['Esito'] == "Pendente"]
    if not pendenti.empty:
        for i, r in pendenti.iterrows():
            with st.expander(f"📌 {r['Match']} (@{r['Quota']})"):
                c1, c2, c3 = st.columns(3)
                if c1.button("✅ VINTO", key=f"win_{i}"):
                    df_c.at[i, 'Esito'] = "VINTO"
                    df_c.at[i, 'Profitto'] = round((r['Stake']*r['Quota'])-r['Stake'], 2)
                    salva_db(df_c); st.rerun()
                if c2.button("❌ PERSO", key=f"loss_{i}"):
                    df_c.at[i, 'Esito'] = "PERSO"
                    df_c.at[i, 'Profitto'] = -r['Stake']
                    salva_db(df_c); st.rerun()
                if c3.button("🗑️", key=f"del_{i}"):
                    df_c = df_c.drop(i)
                    salva_db(df_c); st.rerun()
    else:
        st.info("Nessuna giocata attiva.")

with t3:
    df_f = carica_db()
    if not df_f.empty:
        prof_netto = round(df_f['Profitto'].sum(), 2)
        st.metric("PROFITTO NETTO", f"{prof_netto} €")
        
        st.write("### 📝 STORICO")
        for i, row in df_f.iterrows():
            color = "#00ff88" if row['Esito'] == "VINTO" else "#ff4b4b"
            st.markdown(f"""
                <div style='display:flex; justify-content:space-between; padding:10px; border-bottom:1px solid #333;'>
                    <span style='color:white;'>{row['Match']}</span>
                    <span style='color:{color}; font-weight:bold;'>{row['Profitto']}€</span>
                </div>
            """, unsafe_allow_html=True)
            if st.button("ELIMINA RIGA", key=f"del_row_f_{i}"):
                df_f = df_f.drop(i)
                salva_db(df_f); st.rerun()
