import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V13.6 - STABLE", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

if 'api_usage' not in st.session_state:
    st.session_state['api_usage'] = {'remaining': "N/D", 'used': "N/D"}
if 'api_data' not in st.session_state:
    st.session_state['api_data'] = []

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "William Hill", "888sport"]

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", 
    "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", 
    "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie",
    "soccer_spain_la_liga": "🇪🇸 La Liga", 
    "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_france_ligue_1": "🇫🇷 Ligue 1",
    "soccer_uefa_europa_league": "🇪🇺 Europa League",
    "soccer_uefa_champions_league": "🏆 Champions"
}

# --- MOTORE DATABASE ---
def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        return df.dropna(subset=["Match"]) if df is not None else pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

# --- LOGICA CHIUSURA MANUALE ---
def chiudi_manualmente(idx, esito):
    df = carica_db()
    if idx in df.index:
        q = float(df.at[idx, 'Quota'])
        s = float(df.at[idx, 'Stake'])
        df.at[idx, 'Esito'] = esito
        df.at[idx, 'Risultato'] = "MANUALE"
        df.at[idx, 'Profitto'] = round((s * q) - s, 2) if esito == "VINTO" else -s
        salva_db(df)
        st.rerun()

def check_results():
    df = carica_db()
    pendenti = df[df['Esito'] == "Pendente"]
    if pendenti.empty:
        st.info("Nessuna scommessa pendente.")
        return
    cambiamenti = False
    with st.spinner("🔄 Verifica risultati..."):
        for skey in pendenti['Sport_Key'].unique():
            res = requests.get(f'https://api.the-odds-api.com/v4/sports/{skey}/scores/', params={'api_key': API_KEY, 'daysFrom': 3})
            if res.status_code == 200:
                scores = res.json()
                for i, r in pendenti[pendenti['Sport_Key'] == skey].iterrows():
                    m_res = next((m for m in scores if f"{m['home_team']}-{m['away_team']}" == r['Match'] and m.get('completed')), None)
                    if m_res:
                        s = m_res['scores']
                        if s:
                            s1, s2 = int(s[0]['score']), int(s[1]['score'])
                            vinto = (s1 + s2) > 2.5 if r['Scelta'] == "OVER 2.5" else (s1 + s2) < 2.5
                            df.at[i, 'Esito'] = "VINTO" if vinto else "PERSO"
                            df.at[i, 'Risultato'] = f"{s1}-{s2}"
                            df.at[i, 'Profitto'] = round((float(r['Stake']) * float(r['Quota'])) - float(r['Stake']), 2) if vinto else -float(r['Stake'])
                            cambiamenti = True
    if cambiamenti:
        salva_db(df)
        st.rerun()

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V13.6")
df_attuale = carica_db()

with st.sidebar:
    st.header("📊 Stato API")
    c1, c2 = st.columns(2)
    c1.metric("Residui", st.session_state['api_usage']['remaining'])
    c2.metric("Usati", st.session_state['api_usage']['used'])
    st.divider()
    budget_cassa = st.number_input("Budget (€)", value=500.0)
    rischio = st.slider("Kelly", 0.05, 0.50, 0.20)
    soglia_val = st.slider("Valore Min %", 0, 15, 3) / 100

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER (Logica Originale V13.6) ---
with t1:
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    c_sel, c_all, c_sing, c_ore = st.columns([1.5, 1, 1, 1])
    sel_name = c_sel.selectbox("Campionato Singolo:", list(leagues.keys()))
    ore_limite = c_ore.selectbox("Finestra Ore:", [24, 48, 72, 96, 120, 168], index=2)
    
    if c_all.button("🚀 TOTALE", use_container_width=True):
        all_found = []
        keys_to_scan = list(LEAGUE_NAMES.keys())
        pbar = st.progress(0)
        limit_date = datetime.utcnow() + timedelta(hours=ore_limite)
        for idx, k in enumerate(set(keys_to_scan)):
            r = requests.get(f'https://api.the-odds-api.com/v4/sports/{k}/odds/', params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
            if r.status_code == 200:
                data = r.json()
                filtered = [m for m in data if datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ") <= limit_date]
                all_found.extend(filtered)
                st.session_state['api_usage']['remaining'] = r.headers.get('x-requests-remaining')
            time.sleep(0.4)
            pbar.progress((idx + 1) / len(set(keys_to_scan)))
        st.session_state['api_data'] = all_found
        st.rerun()

    if st.session_state['api_data']:
        pend_list = df_attuale[df_attuale['Esito'] == "Pendente"]['Match'].tolist()
        for i, m in enumerate(st.session_state['api_data']):
            try:
                nome_m = f"{m['home_team']}-{m['away_team']}"
                dt_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m %H:%M")
                opts = []
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_EURO_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == 'totals'), None)
                        if mk:
                            q_ov = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Over' and float(o.get('point',0)) == 2.5), None)
                            q_un = next((o['price'] for o in mk['outcomes'] if o['name'] == 'Under' and float(o.get('point',0)) == 2.5), None)
                            if q_ov: opts.append({"T": "OVER 2.5", "Q": q_ov, "P": (1/q_ov)+0.06, "BK": b['title']})
                            if q_un: opts.append({"T": "UNDER 2.5", "Q": q_un, "P": (1/q_un)+0.06, "BK": b['title']})
                if opts:
                    best = max(opts, key=lambda x: (x['P'] * x['Q']) - 1)
                    val = (best['P'] * best['Q']) - 1
                    if val >= soglia_val:
                        stk_c = round(max(2.0, min(budget_cassa * (val/(best['Q']-1)) * rischio, budget_cassa*0.15)), 2)
                        c_a, c_b = st.columns([3, 1])
                        c_a.markdown(f"📅 {dt_m} | **{nome_m}**<br>🎯 Giocata: **{best['T']}** @{best['Q']} | Stake: **{stk_c}€** | 🏦 {best['BK']}", unsafe_allow_html=True)
                        if nome_m in pend_list:
                            c_b.button("✅", key=f"add_{i}", disabled=True, use_container_width=True)
                        else:
                            if c_b.button(f"ADD", key=f"add_{i}", use_container_width=True):
                                nuova = pd.DataFrame([{"Data Match": dt_m, "Match": nome_m, "Scelta": best['T'], "Quota": best['Q'], "Stake": stk_c, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": m['sport_key'], "Risultato": "-"}])
                                salva_db(pd.concat([df_attuale, nuova], ignore_index=True))
                                st.rerun()
                        st.divider()
            except: continue

# --- TAB 2: PORTAFOGLIO (Con Controllo Manuale) ---
with t2:
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"]
    if not df_p.empty:
        tot_imp = round(df_p['Stake'].astype(float).sum(), 2)
        rit_pot = round((df_p['Stake'].astype(float) * df_p['Quota'].astype(float)).sum(), 2)
        st.markdown(f"""
            <div style='background: #1c2128; padding: 15px; border-radius: 10px; border: 1px solid #30363d; margin-bottom: 20px; display: flex; justify-content: space-around; text-align: center;'>
                <div><span style='color: white; font-size: 0.9em; font-weight: bold;'>IMPEGNATO</span><br><span style='font-size: 1.5em; font-weight: bold; color: #ffc107;'>{tot_imp} €</span></div>
                <div style='border-left: 1px solid #333; padding-left: 20px;'><span style='color: white; font-size: 0.9em; font-weight: bold;'>RITORNO POTENZIALE</span><br><span style='font-size: 1.5em; font-weight: bold; color: #00ff00;'>{rit_pot} €</span></div>
            </div>
        """, unsafe_allow_html=True)
    
    st.button("🔄 AGGIORNA AUTOMATICO", on_click=check_results, use_container_width=True)
    st.divider()
    
    if not df_p.empty:
        for i, r in df_p.iterrows():
            campionato = LEAGUE_NAMES.get(r['Sport_Key'], "Campionato")
            c1, c2, c3, c4 = st.columns([12, 1.2, 1.2, 1.2])
            
            # Info completa ripristinata: DATA | CAMPIONATO | MATCH
            c1.info(f"📅 **{r['Data Match']}** | {campionato}\n\n**{r['Match']}** | {r['Scelta']} @{r['Quota']} | Stake: **{r['Stake']}€** | 🏦 {r['Bookmaker']}")
            
            if c2.button("✅", key=f"w_{i}", help="Vinta"):
                chiudi_manualmente(i, "VINTO")
            if c3.button("❌", key=f"l_{i}", help="Persa"):
                chiudi_manualmente(i, "PERSO")
            if c4.button("🗑️", key=f"d_{i}", help="Elimina"):
                salva_db(df_attuale.drop(i))
                st.rerun()
    else:
        st.info("Nessuna giocata pendente.")

# --- TAB 3: FISCALE ---
with t3:
    st.subheader("🏁 Cruscotto Finanziario")
    if not df_attuale.empty:
        vinto = df_attuale[df_attuale['Esito'] == "VINTO"]['Profitto'].sum()
        perso = abs(df_attuale[df_attuale['Esito'] == "PERSO"]['Profitto'].sum())
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Giocato", f"{round(df_attuale['Stake'].sum(), 2)} €")
        m2.metric("📈 Profitto Netto", f"{round(vinto-perso, 2)} €", delta=f"{round(vinto-perso, 2)} €")
        m3.metric("🎯 Match Totali", len(df_attuale))
        st.divider()
        st.dataframe(df_attuale.sort_index(ascending=False), use_container_width=True)
