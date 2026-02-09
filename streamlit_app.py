import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V15.1.23", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. COSTANTI ---
API_KEYS = ['01f1c8f2a314814b17de03eeb6c53623', '55f08c25f38fa1006dd9e66282170e1a']
BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "William Hill", "888sport", "Unibet", "Betfair"]
OBIETTIVO_TARGET = 5000.0

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie",
    "soccer_spain_la_liga": "🇪🇸 La Liga", "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_france_ligue_1": "🇫🇷 Ligue 1", "soccer_uefa_europa_league": "🇪🇺 Europa League",
    "soccer_uefa_champions_league": "🏆 Champions"
}

MARKET_MAP = {
    "Goal/No Goal": "both_teams_to_score",
    "Under/Over 2.5": "totals",
    "Esito Finale (1X2)": "h2h"
}

if 'api_data' not in st.session_state: st.session_state['api_data'] = []
if 'api_usage' not in st.session_state: st.session_state['api_usage'] = {'remaining': "Verifica...", 'active_index': 0}

# --- 3. FUNZIONI CORE ---
def fetch_api(endpoint, p_extra={}):
    idx = st.session_state['api_usage']['active_index']
    for _ in range(len(API_KEYS)):
        current_key = API_KEYS[idx]
        p = {'api_key': current_key, 'regions': 'eu', 'oddsFormat': 'decimal'}
        p.update(p_extra)
        try:
            r = requests.get(endpoint, params=p, timeout=12)
            if r.status_code == 200:
                st.session_state['api_usage']['remaining'] = r.headers.get('x-requests-remaining', "N/D")
                st.session_state['api_usage']['active_index'] = idx
                return r.json()
            idx = (idx + 1) % len(API_KEYS)
        except: idx = (idx + 1) % len(API_KEYS)
    return None

def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        return df.dropna(subset=["Match"]) if df is not None else pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

def chiudi_gara(idx, esito, risultato_score="-"):
    df = carica_db()
    if idx in df.index:
        q, s = float(df.at[idx, 'Quota']), float(df.at[idx, 'Stake'])
        df.at[idx, 'Esito'], df.at[idx, 'Risultato'] = esito, risultato_score
        df.at[idx, 'Profitto'] = round((s * q) - s, 2) if esito == "VINTO" else -s
        salva_db(df); st.rerun()

# --- 4. INTERFACCIA ---
st.title("🎯 AI SNIPER V15.1.23")
df_attuale = carica_db()

with st.sidebar:
    st.header("📊 Parametri")
    budget_cassa = st.number_input("Budget Attuale (€)", value=500.0)
    rischio_kelly = st.slider("Aggressività Kelly", 0.05, 0.50, 0.15)
    soglia_valore = st.slider("Min Value %", 0, 15, 0) / 100
    st.info(f"API Residue: {st.session_state['api_usage']['remaining']}")

tab1, tab2, tab3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 DASHBOARD FISCALE"])

# --- TAB 1: SCANNER ---
with tab1:
    c1, c2, c3, c4 = st.columns([1.5, 1, 1.5, 0.8])
    sel_league = c1.selectbox("Campionato:", ["TUTTI"] + list(LEAGUE_NAMES.values()))
    sel_market = c2.selectbox("Mercato:", list(MARKET_MAP.keys()))
    ore = c4.selectbox("Fino a (Ore):", [24, 48, 72, 96, 120, 168], index=3)
    
    if c3.button("🚀 AVVIA SCANNER", use_container_width=True, type="primary"):
        m_key = MARKET_MAP[sel_market]
        l_keys = [k for k, v in LEAGUE_NAMES.items() if v == sel_league or sel_league == "TUTTI"]
        all_matches = []
        bar = st.progress(0)
        for i, lk in enumerate(l_keys):
            data = fetch_api(f'https://api.the-odds-api.com/v4/sports/{lk}/odds/', {'markets': m_key})
            if data: all_matches.extend(data)
            bar.progress((i+1)/len(l_keys))
        st.session_state['api_data'] = all_matches
        st.rerun()

    if st.session_state['api_data']:
        m_key = MARKET_MAP[sel_market]
        # Creiamo un set di tuple (Match, Scelta) per il controllo rapido
        giocate_esistenti = set(zip(df_attuale['Match'], df_attuale['Scelta']))
        found = 0
        for m in st.session_state['api_data']:
            try:
                nome = f"{m['home_team']}-{m['away_team']}"
                dt = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
                if dt > datetime.utcnow() + timedelta(hours=ore): continue
                options = []
                for bk in m.get('bookmakers', []):
                    if bk['title'] in BK_EURO_AUTH:
                        mkt = next((x for x in bk['markets'] if x['key'] == m_key), None)
                        if mkt:
                            for o in mkt['outcomes']:
                                if m_key == "totals" and o.get('point') != 2.5: continue
                                q, marg = o['price'], (0.03 if m_key == "both_teams_to_score" else 0.06)
                                val = ((1/q + marg) * q) - 1
                                if val >= soglia_valore:
                                    lbl = o['name']
                                    if m_key == "both_teams_to_score":
                                        lbl = "GOAL (GG)" if o['name'].lower() in ["yes", "both"] else "NO GOAL (NG)"
                                    elif m_key == "totals":
                                        lbl = f"{o['name'].upper()} 2.5"
                                    options.append({"T": lbl, "Q": q, "V": val, "BK": bk['title']})
                if options:
                    found += 1
                    best = max(options, key=lambda x: x['V'])
                    stk = round(max(2.0, min(budget_cassa * (best['V']/(best['Q']-1)) * rischio_kelly, budget_cassa*0.15)), 2)
                    col1, col2, col3, col4 = st.columns([3, 1.5, 1.5, 1])
                    col1.write(f"📅 {dt.strftime('%d/%m %H:%M')} | **{nome}**")
                    col2.write(f"🎯 {best['T']} @**{best['Q']}**")
                    col3.write(f"🏦 {best['BK']} ({round(best['V']*100,1)}%)")
                    
                    # MODIFICA QUI: Controllo incrociato Match + Scelta
                    if (nome, best['T']) in giocate_esistenti:
                        col4.button("✅", key=f"ok_{nome}_{best['T']}", disabled=True, help="Giocata già in portafoglio")
                    elif col4.button("ADD", key=f"add_{nome}_{found}"):
                        nuova = pd.DataFrame([{"Data Match": dt.strftime('%d/%m %H:%M'), "Match": nome, "Scelta": best['T'], "Quota": best['Q'], "Stake": stk, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": m['sport_key'], "Risultato": "-"}])
                        salva_db(pd.concat([df_attuale, nuova], ignore_index=True)); st.rerun()
                    st.divider()
            except: continue

# --- TAB 2: PORTAFOGLIO + AGGIORNAMENTO AUTOMATICO ---
with tab2:
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"].copy()
    if not df_p.empty:
        if st.button("🔄 AGGIORNA RISULTATI", use_container_width=True, type="primary"):
            for idx, r in df_p.iterrows():
                scores = fetch_api(f"https://api.the-odds-api.com/v4/sports/{r['Sport_Key']}/scores/", {"daysFrom": 1})
                if scores:
                    match_data = next((s for s in scores if f"{s['home_team']}-{s['away_team']}" == r['Match']), None)
                    if match_data and match_data.get('completed'):
                        s = match_data['scores']
                        h_score = int(next(x['score'] for x in s if x['name'] == match_data['home_team']))
                        a_score = int(next(x['score'] for x in s if x['name'] == match_data['away_team']))
                        res_str = f"{h_score}-{a_score}"
                        
                        vittoria = False
                        sc = r['Scelta']
                        if sc == "GOAL (GG)": vittoria = (h_score > 0 and a_score > 0)
                        elif sc == "NO GOAL (NG)": vittoria = (h_score == 0 or a_score == 0)
                        elif "OVER" in sc: vittoria = (h_score + a_score > 2.5)
                        elif "UNDER" in sc: vittoria = (h_score + a_score < 2.5)
                        elif sc == match_data['home_team']: vittoria = (h_score > a_score)
                        elif sc == match_data['away_team']: vittoria = (a_score > h_score)
                        elif sc == "Draw": vittoria = (h_score == a_score)
                        
                        chiudi_gara(idx, "VINTO" if vittoria else "PERSO", res_str)
            st.rerun()

        for i, r in df_p.iterrows():
            with st.expander(f"📅 {r['Data Match']} | {r['Match']} | {r['Stake']}€"):
                st.write(f"🎯 **{r['Scelta']}** @{r['Quota']} su {r['Bookmaker']}")
                b1, b2, b3 = st.columns(3)
                if b1.button("VINTO ✅", key=f"v_{i}"): chiudi_gara(i, "VINTO")
                if b2.button("PERSO ❌", key=f"p_{i}"): chiudi_gara(i, "PERSO")
                if b3.button("ELIMINA 🗑️", key=f"e_{i}"): salva_db(df_attuale.drop(i)); st.rerun()
    else: st.info("Nessuna giocata in corso.")

# --- TAB 3: DASHBOARD FISCALE ---
with tab3:
    df_chiuse = df_attuale[df_attuale['Esito'].isin(["VINTO", "PERSO"])].copy()
    if not df_chiuse.empty:
        df_chiuse['Profitto'] = pd.to_numeric(df_chiuse['Profitto'])
        df_chiuse['Stake'] = pd.to_numeric(df_chiuse['Stake'])
        net_profit = df_chiuse['Profitto'].sum()
        mancante = max(0.0, OBIETTIVO_TARGET - net_profit)
        perc = min(100, int((net_profit / OBIETTIVO_TARGET) * 100)) if net_profit > 0 else 0
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Scommesso", f"{round(df_chiuse['Stake'].sum(), 2)}€")
        m2.metric("Profitto Netto", f"{round(net_profit, 2)}€")
        m3.metric("Progresso", f"{perc}%")
        m4.metric("Mancante", f"{round(mancante, 2)}€")
        st.progress(perc/100)
        
        st.markdown("### 📜 Storico Giocate")
        for i, r in df_chiuse[::-1].iterrows():
            icon, bg, border, txt = ("✅", "#e6ffed", "#34d058", "#155724") if r['Esito'] == "VINTO" else ("❌", "#ffeef0", "#f97583", "#721c24")
            st.markdown(f"""
                <div style="background-color:{bg}; border-left: 5px solid {border}; padding: 6px 12px; border-radius: 4px; margin-bottom: 4px; color:{txt}; font-size: 0.9rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>{icon} <b>{r['Match']}</b> ({r['Data Match']})</span>
                        <span>{r['Scelta']} @{r['Quota']} | Res: {r.get('Risultato','-')} | <b>{r['Profitto']}€</b></span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else: st.info("Nessuna giocata chiusa.")
    st.divider()
    st.download_button("📥 Backup CSV", df_attuale.to_csv(index=False), "sniper_data.csv", use_container_width=True)
