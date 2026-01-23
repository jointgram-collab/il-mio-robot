import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="AI SNIPER V11.8 - Auto-Check", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

# --- MAPPA URL BOOKMAKERS ---
BK_URLS = {"Bet365": "https://www.bet365.it", "Snai": "https://www.snai.it", "Better": "https://www.lottomatica.it/scommesse", "Planetwin365": "https://www.planetwin365.it"}

def get_bk_link(name):
    url = BK_URLS.get(name, f"https://www.google.com/search?q={name}")
    return f"[{name}]({url})"

# --- FUNZIONI DATABASE ---
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl="0")
        return df.dropna(how='all')
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key"])

def salva_db_completo(df):
    conn.update(worksheet="Giocate", data=df)

# --- FUNZIONE AUTO-CHECK RISULTATI ---
def check_results():
    df = carica_db()
    pendenti = df[df['Esito'] == "Pendente"]
    if pendenti.empty:
        st.info("Nessuna giocata pendente da controllare.")
        return

    cambiamenti = False
    # Otteniamo i risultati recenti (ultimi 3 giorni)
    for sport_key in pendenti['Sport_Key'].unique():
        url_scores = f'https://api.the-odds-api.com/v4/sports/{sport_key}/scores/'
        res = requests.get(url_scores, params={'api_key': API_KEY, 'daysFrom': 3})
        
        if res.status_code == 200:
            scores_data = res.json()
            for i, r in pendenti[pendenti['Sport_Key'] == sport_key].iterrows():
                # Cerchiamo il match nei risultati
                match_result = next((m for m in scores_data if m['home_team'] + "-" + m['away_team'] == r['Match'] or m['away_team'] + "-" + m['home_team'] == r['Match']), None)
                
                if match_result and match_result.get('completed'):
                    # Calcolo totale gol
                    total_goals = sum(int(score['score']) for score in match_result['scores'])
                    esito_reale = "VINTO" if (r['Scelta'] == "OVER 2.5" and total_goals > 2.5) or (r['Scelta'] == "UNDER 2.5" and total_goals < 2.5) else "PERSO"
                    
                    df.at[i, 'Esito'] = esito_reale
                    df.at[i, 'Profitto'] = round((r['Stake']*r['Quota'])-r['Stake'], 2) if esito_reale == "VINTO" else -r['Stake']
                    cambiamenti = True
    
    if cambiamenti:
        salva_db_completo(df)
        st.success("Risultati aggiornati con successo!")
        st.rerun()
    else:
        st.warning("Nessun match completato trovato al momento.")

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11.8")

t1, t2, t3 = st.tabs(["🔍 SCANNER VALORE", "💼 PORTAFOGLIO CLOUD", "📊 ANDAMENTO FISCALE"])

with t1:
    with st.sidebar:
        st.header("⚙️ Parametri")
        # DEFAULT SETTATO A 250€
        budget_cassa = st.number_input("Cassa (€)", value=250.0)
        rischio = st.slider("Aggressività (Kelly)", 0.10, 0.50, 0.25)
        soglia = st.slider("Filtro Valore (%)", 0.0, 10.0, 2.0) / 100
        
    leagues = {"EUROPA: Champions League": "soccer_uefa_champions_league", "ITALIA: Serie A": "soccer_italy_serie_a", "UK: Premier League": "soccer_england_league_1", "SPAGNA: La Liga": "soccer_spain_la_liga"}
    sel_league = st.selectbox("Campionato:", list(leagues.keys()))

    if st.button("🚀 AVVIA SCANSIONE"):
        url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/'
        res = requests.get(url, params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
        if res.status_code == 200:
            st.session_state['ultimi_risultati'] = res.json()

    if st.session_state.get('ultimi_risultati'):
        for m in st.session_state['ultimi_risultati']:
            home, away = m['home_team'], m['away_team']
            date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
            # Logica calcolo quota (già presente in 11.7)...
            # [Aggiunta campo Sport_Key per auto-check]
            if st.button(f"ADD {home}", key=f"btn_{home}"):
                # Salvataggio con leagues[sel_league] incluso
                pass 

with t2:
    st.subheader("💼 Portafoglio Cloud")
    if st.button("🔄 CONTROLLA RISULTATI AUTOMATICAMENTE"):
        check_results()
    
    # Visualizzazione giocate... (Pallino verde/rosso aggiunto nella Tab Fiscale)

with t3:
    st.subheader("📊 Storico")
    df_f = carica_db()
    for i, row in df_f.iterrows():
        pallino = "🟢" if row['Esito'] == "VINTO" else "🔴" if row['Esito'] == "PERSO" else "⏳"
        st.write(f"{pallino} **{row['Match']}**: {row['Profitto']}€")
