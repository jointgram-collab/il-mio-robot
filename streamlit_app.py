import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="SNIPER ELITE V12", layout="wide", initial_sidebar_state="collapsed")

# CSS Personalizzato per Look Sport Premium e Mobile
st.markdown("""
    <style>
    /* Sfondo Generale */
    .stApp {
        background: linear-gradient(180deg, #0e1117 0%, #1a1c24 100%);
    }
    
    /* Card delle Partite */
    .stMetric {
        background-color: #1e222d;
        border-radius: 15px;
        padding: 15px;
        border: 1px solid #2e3344;
    }
    
    /* Pulsanti Full Width per Mobile */
    .stButton > button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #2e3344;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        border-color: #00ff88;
        color: #00ff88;
    }

    /* Stile personalizzato per i link */
    a {
        color: #00ff88 !important;
        text-decoration: none;
        font-weight: bold;
    }
    
    /* Divider più eleganti */
    hr {
        margin: 1em 0;
        border-bottom: 1px solid #2e3344;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONNESSIONE ---
conn = st.connection("gsheets", type=GSheetsConnection)

BK_URLS = {
    "Bet365": "https://www.bet365.it", "Snai": "https://www.snai.it",
    "Better": "https://www.lottomatica.it/scommesse", "Planetwin365": "https://www.planetwin365.it",
    "Eurobet": "https://www.eurobet.it", "Goldbet": "https://www.goldbet.it", "Sisal": "https://www.sisal.it"
}

def get_bk_link(name):
    url = BK_URLS.get(name, f"https://www.google.com/search?q={name}")
    return f"[{name}]({url})"

# --- LOGICA DATABASE ---
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl="0")
        return df.dropna(how='all')
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto"])

def salva_db_completo(df):
    conn.update(worksheet="Giocate", data=df)

def salva_giocata(nuova_giocata):
    df_attuale = carica_db()
    df_finale = pd.concat([df_attuale, pd.DataFrame([nuova_giocata])], ignore_index=True)
    salva_db_completo(df_finale)

# --- LOGICA TECNICA ---
def get_totals_value(q_over, q_under):
    margin = (1/q_over) + (1/q_under)
    return (1/q_over) / margin, (1/q_under) / margin

def calc_stake(prob, quota, budget, frazione):
    valore = (prob * quota) - 1
    if valore <= 0: return 2.0
    importo = budget * (valore / (quota - 1)) * frazione
    return round(max(2.0, min(importo, budget * 0.1)), 2)

def aggiungi_a_cloud(match, scelta, quota, stake, book, data):
    giocata = {"Data Match": data, "Match": match, "Scelta": scelta, "Quota": quota, "Stake": stake, "Bookmaker": book, "Esito": "Pendente", "Profitto": 0.0}
    salva_giocata(giocata)
    st.toast(f"✅ Sincronizzato Cloud: {match}")

# --- INTERFACCIA ---
st.title("🎯 SNIPER ELITE")

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    with st.expander("⚙️ IMPOSTAZIONI STRATEGIA"):
        c_p1, c_p2 = st.columns(2)
        budget_cassa = c_p1.number_input("Cassa (€)", value=1000.0)
        rischio = c_p2.slider("Aggressività", 0.10, 0.50, 0.25)
        
    leagues = {
        "Champions League": "soccer_uefa_champions_league", "Serie A": "soccer_italy_serie_a", 
        "Serie B": "soccer_italy_serie_b", "Premier League": "soccer_england_league_1",
        "La Liga": "soccer_spain_la_liga", "Bundesliga": "soccer_germany_bundesliga"
    }
    sel_league = st.selectbox("Seleziona Campionato:", list(leagues.keys()))

    if st.button("🚀 AVVIA ANALISI"):
        API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
        url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/'
        params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals', 'oddsFormat': 'decimal'}
        res = requests.get(url, params=params)
        if res.status_code == 200:
            st.session_state['ultimi_risultati'] = res.json()
            st.success("Dati Ricevuti!")

    if 'ultimi_risultati' in st.session_state:
        priorita = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal"]
        for m in st.session_state['ultimi_risultati']:
            home, away = m['home_team'], m['away_team']
            date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
            best_bk = next((b for p in priorita for b in m.get('bookmakers', []) if p.lower() in b['title'].lower()), None)
            
            if best_bk:
                mk = next((x for x in best_bk['markets'] if x['key'] == 'totals'), None)
                if mk:
                    q_over = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), 1.0)
                    q_under = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), 1.0)
                    p_ov_e, p_un_e = get_totals_value(q_over, q_under)
                    opzioni = [{"T": "OVER 2.5", "Q": q_over, "P": p_ov_e + 0.07}, {"T": "UNDER 2.5", "Q": q_under, "P": p_un_e + 0.07}]
                    best = max(opzioni, key=lambda x: (x['P'] * x['Q']) - 1)
                    
                    if ((best['P'] * best['Q']) - 1) > 0.02:
                        stake = calc_stake(best['P'], best['Q'], budget_cassa, rischio)
                        poss_v = round(stake * best['Q'], 2)
                        
                        # CARD PARTITA
                        with st.container():
                            st.markdown(f"### {home} vs {away}")
                            col_a, col_b = st.columns([2,1])
                            col_a.markdown(f"**Data:** {date_m} | **Book:** {get_bk_link(best_bk['title'])}")
                            col_a.info(f"🎯 **{best['T']}** @{best['Q']} | Stake: **{stake}€**")
                            col_b.metric("Potenziale", f"{poss_v}€")
                            st.button("📥 AGGIUNGI AL CLOUD", key=f"add_{home}_{date_m}", on_click=aggiungi_a_cloud, args=(f"{home}-{away}", best['T'], best['Q'], stake, best_bk['title'], date_m))
                            st.divider()

with t2:
    st.subheader("💼 Portafoglio Cloud")
    df_c = carica_db()
    if not df_c.empty:
        pendenti = df_c[df_c['Esito'] == "Pendente"]
        c_m1, c_m2 = st.columns(2)
        c_m1.metric("Capitale Impegnato", f"{round(pendenti['Stake'].sum(), 2)} €")
        c_m2.metric("Ritorno Totale Atteso", f"{round((pendenti['Stake'] * pendenti['Quota']).sum(), 2)} €")
        
        for i, r in pendenti.iterrows():
            with st.expander(f"📌 {r['Match']} - {r['Stake']}€"):
                st.write(f"**{r['Scelta']}** @{r['Quota']} su {get_bk_link(r['Bookmaker'])}")
                c1, c2, c3 = st.columns(3)
                if c1.button("✅ VINTO", key=f"w_{i}"):
                    df_c.at[i, 'Esito'] = "VINTO"
                    df_c.at[i, 'Profitto'] = round((r['Stake']*r['Quota'])-r['Stake'], 2)
                    salva_db_completo(df_c); st.rerun()
                if c2.button("❌ PERSO", key=f"l_{i}"):
                    df_c.at[i, 'Esito'] = "PERSO"
                    df_c.at[i, 'Profitto'] = -r['Stake']
                    salva_db_completo(df_c); st.rerun()
                if c3.button("🗑️", key=f"d_{i}"):
                    df_c = df_c.drop(i)
                    salva_db_completo(df_c); st.rerun()
    else:
        st.info("Nessuna operazione in corso.")

with t3:
    df_f = carica_db()
    if not df_f.empty:
        prof_netto = round(df_f['Profitto'].sum(), 2)
        st.markdown(f"""
        <div style="background-color: #1e222d; padding: 20px; border-radius: 15px; border-left: 5px solid #00ff88; margin-bottom: 20px;">
            <h2 style="margin:0; color: white;">Profitto Netto: {prof_netto} €</h2>
            <p style="margin:0; color: #888;">Mancano {round(5000-prof_netto, 2)} € al traguardo dei 5.000€</p>
        </div>
        """, unsafe_allow_html=True)
        
        for i, row in df_f.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([3, 1, 1])
                color = "#00ff88" if row['Esito'] == "VINTO" else "#ff4b4b" if row['Esito'] == "PERSO" else "#ffaa00"
                c1.markdown(f"**{row['Match']}**<br><small>{row['Data Match']} - {row['Bookmaker']}</small>", unsafe_allow_html=True)
                c2.markdown(f"<span style='color:{color}; font-weight:bold;'>{row['Profitto']} €</span>", unsafe_allow_html=True)
                if c3.button("🗑️", key=f"del_h_{i}"):
                    df_f = df_f.drop(i)
                    salva_db_completo(df_f); st.rerun()
