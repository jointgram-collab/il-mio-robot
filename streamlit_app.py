import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="AI SNIPER V11.7 - Direct Links", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- MAPPA URL BOOKMAKERS ---
BK_URLS = {
    "Bet365": "https://www.bet365.it",
    "Snai": "https://www.snai.it",
    "Better": "https://www.lottomatica.it/scommesse",
    "Planetwin365": "https://www.planetwin365.it",
    "Eurobet": "https://www.eurobet.it",
    "Goldbet": "https://www.goldbet.it",
    "Sisal": "https://www.sisal.it"
}

def get_bk_link(name):
    url = BK_URLS.get(name, f"https://www.google.com/search?q={name}")
    return f"[{name}]({url})"

# --- FUNZIONI DATABASE ---
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
    giocata = {
        "Data Match": data, "Match": match, "Scelta": scelta,
        "Quota": quota, "Stake": stake, "Bookmaker": book,
        "Esito": "Pendente", "Profitto": 0.0
    }
    salva_giocata(giocata)
    st.toast(f"✅ Sincronizzato Cloud: {match}")

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V11.7")

if 'ultimi_risultati' not in st.session_state:
    st.session_state['ultimi_risultati'] = []

t1, t2, t3 = st.tabs(["🔍 SCANNER VALORE", "💼 PORTAFOGLIO CLOUD", "📊 ANDAMENTO FISCALE"])

with t1:
    with st.sidebar:
        st.header("⚙️ Parametri")
        budget_cassa = st.number_input("Cassa (€)", value=1000.0)
        rischio = st.slider("Aggressività (Kelly)", 0.10, 0.50, 0.25)
        soglia = st.slider("Filtro Valore (%)", 0.0, 10.0, 2.0) / 100
        
    leagues = {
        "EUROPA: Champions League": "soccer_uefa_champions_league",
        "EUROPA: Europa League": "soccer_uefa_europa_league",
        "ITALIA: Serie A": "soccer_italy_serie_a", 
        "ITALIA: Serie B": "soccer_italy_serie_b",
        "UK: Premier League": "soccer_england_league_1",
        "SPAGNA: La Liga": "soccer_spain_la_liga",
        "GERMANIA: Bundesliga": "soccer_germany_bundesliga"
    }
    sel_league = st.selectbox("Campionato:", list(leagues.keys()))

    if st.button("🚀 AVVIA SCANSIONE"):
        API_KEY = '01f1c8f2a314814b17de03eeb6c53623'
        url = f'https://api.the-odds-api.com/v4/sports/{leagues[sel_league]}/odds/'
        params = {'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals', 'oddsFormat': 'decimal'}
        res = requests.get(url, params=params)
        if res.status_code == 200:
            st.session_state['ultimi_risultati'] = res.json()
            st.success(f"Dati caricati! API Residue: {res.headers.get('x-requests-remaining')}")

    if st.session_state['ultimi_risultati']:
        priorita = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal"]
        for m in st.session_state['ultimi_risultati']:
            home, away = m['home_team'], m['away_team']
            date_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
            best_bk = next((b for p in priorita for b in m.get('bookmakers', []) if p.lower() in b['title'].lower()), None)
            if not best_bk and m.get('bookmakers'): best_bk = m['bookmakers'][0]
            
            if best_bk:
                mk = next((x for x in best_bk['markets'] if x['key'] == 'totals'), None)
                if mk:
                    q_over = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and o['point'] == 2.5), 1.0)
                    q_under = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and o['point'] == 2.5), 1.0)
                    p_ov_e, p_un_e = get_totals_value(q_over, q_under)
                    opzioni = [{"T": "OVER 2.5", "Q": q_over, "P": p_ov_e + 0.07}, {"T": "UNDER 2.5", "Q": q_under, "P": p_un_e + 0.07}]
                    best = max(opzioni, key=lambda x: (x['P'] * x['Q']) - 1)
                    val = (best['P'] * best['Q']) - 1
                    
                    if val > soglia:
                        stake = calc_stake(best['P'], best['Q'], budget_cassa, rischio)
                        poss_v = round(stake * best['Q'], 2)
                        bk_name = best_bk['title']
                        bk_link = get_bk_link(bk_name) # Genera il link Markdown
                        
                        c1, c2, c3 = st.columns([3, 2, 1])
                        c1.write(f"📅 {date_m}\n**{home}-{away}**")
                        c2.markdown(f"🎯 **{best['T']}** @**{best['Q']}** ({bk_link})\n💰 Stake: **{stake}€** | 💸 Vincita: **{poss_v}€**")
                        u_key = f"btn_{home}_{away}_{best['T']}_{bk_name}_{date_m}".replace(" ", "_")
                        c3.button("AGGIUNGI", key=u_key, on_click=aggiungi_a_cloud, args=(f"{home}-{away}", best['T'], best['Q'], stake, bk_name, date_m))
                        st.divider()

with t2:
    st.subheader("💼 Portafoglio Cloud")
    df_c = carica_db()
    if not df_c.empty:
        pendenti = df_c[df_c['Esito'] == "Pendente"]
        tot_impegnato = round(pendenti['Stake'].sum(), 2)
        tot_potenziale = round((pendenti['Stake'] * pendenti['Quota']).sum(), 2)
        col_m1, col_m2 = st.columns(2)
        col_m1.info(f"💰 Totale Scommesso: **{tot_impegnato}€**")
        col_m2.success(f"📈 Ritorno Potenziale Totale: **{tot_potenziale}€**")
        st.divider()
        for i, r in pendenti.iterrows():
            vinc_s = round(r['Stake'] * r['Quota'], 2)
            bk_link = get_bk_link(r['Bookmaker'])
            with st.expander(f"📌 {r['Match']} ({r['Bookmaker']}) - Vincita: {vinc_s}€"):
                col1, col2, col3, col4 = st.columns(4)
                col1.markdown(f"**{r['Scelta']}** @{r['Quota']}\nStake: {r['Stake']}€\nBk: **{bk_link}**")
                if col2.button("✅ VINTO", key=f"win_cl_{i}"):
                    df_c.at[i, 'Esito'] = "VINTO"
                    df_c.at[i, 'Profitto'] = round((r['Stake']*r['Quota'])-r['Stake'], 2)
                    salva_db_completo(df_c); st.rerun()
                if col3.button("❌ PERSO", key=f"loss_cl_{i}"):
                    df_c.at[i, 'Esito'] = "PERSO"
                    df_c.at[i, 'Profitto'] = -r['Stake']
                    salva_db_completo(df_c); st.rerun()
                if col4.button("🗑️", key=f"del_cl_{i}"):
                    df_c = df_c.drop(i)
                    salva_db_completo(df_c); st.rerun()
    else:
        st.info("Portafoglio vuoto.")

with t3:
    st.subheader("📊 Gestione Fiscale e Storico")
    df_f = carica_db()
    
    if not df_f.empty:
        prof_netto = round(df_f['Profitto'].sum(), 2)
        m1, m2 = st.columns(2)
        m1.metric("Profitto Netto", f"{prof_netto} €")
        m2.metric("Target 5.000€", f"{round(5000 - prof_netto, 2)} €")
        
        with st.sidebar:
            st.divider()
            st.warning("⚠️ ZONA PERICOLOSA")
            if st.button("🗑️ CANCELLA TUTTO IL DATABASE"):
                df_reset = pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto"])
                salva_db_completo(df_reset)
                st.rerun()

        st.write("### 📝 Registro Operazioni")
        for i, row in df_f.iterrows():
            with st.container():
                bk_link = get_bk_link(row['Bookmaker'])
                c1, c2, c3, c4, c5 = st.columns([2, 3, 2, 2, 1])
                c1.write(f"{row['Data Match']}")
                c2.markdown(f"**{row['Match']}**\n*{row['Scelta']}* su **{bk_link}**")
                
                if row['Esito'] == "VINTO":
                    c3.success(f"✅ {row['Esito']}")
                elif row['Esito'] == "PERSO":
                    c3.error(f"❌ {row['Esito']}")
                else:
                    c3.warning(f"⏳ {row['Esito']}")
                
                c4.write(f"Profitto: **{row['Profitto']}€**\nQuota: @{row['Quota']}")
                
                if c5.button("🗑️", key=f"del_row_{i}"):
                    df_f = df_f.drop(i)
                    salva_db_completo(df_f)
                    st.rerun()
                st.divider()
    else:
        st.info("Lo storico è attualmente vuoto.")
