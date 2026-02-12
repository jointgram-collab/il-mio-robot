import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V15.1.30 - BATCH UPDATE", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. COSTANTI E DEFAULT ---
API_KEYS = ['01f1c8f2a314814b17de03eeb6c53623', '55f08c25f38fa1006dd9e66282170e1a']
BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "William Hill", "888sport", "Unibet", "Betfair"]
OBIETTIVO_MENSILE = 1000.0
OBIETTIVO_FINALE = 5000.0

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
    for attempt in range(len(API_KEYS)):
        current_idx = (idx + attempt) % len(API_KEYS)
        current_key = API_KEYS[current_idx]
        p = {'api_key': current_key, 'regions': 'eu', 'oddsFormat': 'decimal'}
        p.update(p_extra)
        try:
            r = requests.get(endpoint, params=p, timeout=12)
            if r.status_code == 200:
                st.session_state['api_usage']['remaining'] = r.headers.get('x-requests-remaining', "N/D")
                st.session_state['api_usage']['active_index'] = current_idx
                return r.json()
        except: continue
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

# --- 4. INTERFACCIA ---
st.title("🎯 AI SNIPER V15.1.30")
df_attuale = carica_db()

with st.sidebar:
    st.header("📊 Piano 30 Giorni")
    budget_cassa = st.number_input("Budget Attuale (€)", value=500.0)
    rischio_kelly = st.slider("Aggressività Kelly", 0.05, 0.50, 0.10)
    soglia_valore = st.slider("Min Value %", 0, 15, 3) / 100
    st.divider()
    st.info(f"💳 API Residue: **{st.session_state['api_usage']['remaining']}**")
    st.success(f"🔌 API Attiva: **Slot {st.session_state['api_usage']['active_index'] + 1}**")

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
            if data:
                for match in data: match['league_label'] = LEAGUE_NAMES.get(lk, lk)
                all_matches.extend(data)
            bar.progress((i+1)/len(l_keys))
        st.session_state['api_data'] = all_matches
        st.rerun()

    if st.session_state['api_data']:
        m_key = MARKET_MAP[sel_market]
        giocate_esistenti = set(zip(df_attuale['Match'], df_attuale['Scelta']))
        found = 0
        for m in st.session_state['api_data']:
            try:
                nome = f"{m['home_team']}-{m['away_team']}"
                lega = m.get('league_label', 'N/D')
                dt = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
                if dt > datetime.utcnow() + timedelta(hours=ore): continue
                
                match_options = []
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
                                    elif m_key == "totals": lbl = f"{o['name'].upper()} 2.5"
                                    match_options.append({"T": lbl, "Q": q, "V": val, "BK": bk['title']})
                
                if match_options:
                    best_signal = max(match_options, key=lambda x: x['V'])
                    found += 1
                    stk = round(max(2.0, min(budget_cassa * (best_signal['V']/(best_signal['Q']-1)) * rischio_kelly, budget_cassa*0.12)), 2)
                    col1, col2, col3, col4 = st.columns([2.5, 1.8, 1.7, 1])
                    col1.write(f"{lega}\n**{nome}**")
                    col2.write(f"🎯 **{best_signal['T']}** @**{best_signal['Q']}**\n💰 Stake: **{stk}€**")
                    col3.write(f"🏛️ {best_signal['BK']}\n📈 Val: {round(best_signal['V']*100,1)}%")
                    if (nome, best_signal['T']) in giocate_esistenti:
                        col4.button("✅", key=f"ok_{nome}_{found}", disabled=True)
                    elif col4.button("ADD", key=f"add_{nome}_{found}"):
                        nuova = pd.DataFrame([{"Data Match": dt.strftime('%d/%m %H:%M'), "Match": nome, "Scelta": best_signal['T'], "Quota": best_signal['Q'], "Stake": stk, "Bookmaker": best_signal['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": m['sport_key'], "Risultato": "-"}])
                        salva_db(pd.concat([df_attuale, nuova], ignore_index=True)); st.rerun()
                    st.divider()
            except: continue

# --- TAB 2: PORTAFOGLIO (BATCH UPDATE) ---
with tab2:
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"].copy()
    if not df_p.empty:
        tot_impegnato = df_p['Stake'].astype(float).sum()
        tot_potenziale = (df_p['Stake'].astype(float) * df_p['Quota'].astype(float)).sum()
        c_p1, c_p2 = st.columns(2)
        c_p1.metric("Totale Impegnato 💸", f"{round(tot_impegnato, 2)}€")
        c_p2.metric("Vincita Potenziale Lorda 🏆", f"{round(tot_potenziale, 2)}€")
        st.divider()

        if st.button("🔄 AGGIORNA TUTTI I RISULTATI", use_container_width=True, type="primary"):
            counter_chiuse = 0
            # Otteniamo i campionati unici coinvolti per minimizzare le chiamate API
            sport_keys = df_p['Sport_Key'].unique()
            for sk in sport_keys:
                scores = fetch_api(f"https://api.the-odds-api.com/v4/sports/{sk}/scores/", {"daysFrom": 2})
                if scores:
                    for idx, r in df_p[df_p['Sport_Key'] == sk].iterrows():
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
                            
                            # Aggiorniamo il DataFrame locale
                            q, stk = float(r['Quota']), float(r['Stake'])
                            df_attuale.at[idx, 'Esito'] = "VINTO" if vittoria else "PERSO"
                            df_attuale.at[idx, 'Risultato'] = res_str
                            df_attuale.at[idx, 'Profitto'] = round((stk * q) - stk, 2) if vittoria else -stk
                            counter_chiuse += 1
            
            if counter_chiuse > 0:
                salva_db(df_attuale)
                st.success(f"✅ Aggiornamento completato: {counter_chiuse} partite chiuse!")
                st.rerun()
            else:
                st.info("Nessun nuovo risultato completato trovato.")

        for i, r in df_p.iterrows():
            with st.expander(f"📅 {r['Data Match']} | {r['Match']} | {r['Stake']}€"):
                st.write(f"🎯 **{r['Scelta']}** @{r['Quota']} su {r['Bookmaker']}")
                b1, b2, b3 = st.columns(3)
                if b1.button("VINTO ✅", key=f"v_{i}"):
                    q, s = float(r['Quota']), float(r['Stake'])
                    df_attuale.at[i, 'Esito'], df_attuale.at[i, 'Profitto'] = "VINTO", round((s*q)-s, 2)
                    salva_db(df_attuale); st.rerun()
                if b2.button("PERSO ❌", key=f"p_{i}"):
                    df_attuale.at[i, 'Esito'], df_attuale.at[i, 'Profitto'] = "PERSO", -float(r['Stake'])
                    salva_db(df_attuale); st.rerun()
                if b3.button("ELIMINA 🗑️", key=f"e_{i}"): salva_db(df_attuale.drop(i)); st.rerun()
    else: st.info("Nessuna giocata in corso.")

# --- TAB 3: DASHBOARD FISCALE ---
with tab3:
    df_chiuse = df_attuale[df_attuale['Esito'].isin(["VINTO", "PERSO"])].copy()
    if not df_chiuse.empty:
        df_chiuse['Profitto'] = pd.to_numeric(df_chiuse['Profitto'])
        net_profit = df_chiuse['Profitto'].sum()
        mancante_mese = max(0.0, OBIETTIVO_MENSILE - net_profit)
        perc_mese = min(100, int((net_profit / OBIETTIVO_MENSILE) * 100)) if net_profit > 0 else 0
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Profitto Netto", f"{round(net_profit, 2)}€")
        m2.metric("Target 30gg", f"1.000€")
        m3.metric("Mancante", f"{round(mancante_mese, 2)}€")
        m4.metric("Progresso Totale", f"{round((net_profit/OBIETTIVO_FINALE)*100, 1)}%")
        st.write(f"**Avanzamento Obiettivo Mensile**")
        st.progress(perc_mese/100)
        st.markdown("### 📜 Storico Giocate")
        for i, r in df_chiuse[::-1].iterrows():
            icon, bg, border, txt = ("✅", "#e6ffed", "#34d058", "#155724") if r['Esito'] == "VINTO" else ("❌", "#ffeef0", "#f97583", "#721c24")
            st.markdown(f"""<div style="background-color:{bg}; border-left: 5px solid {border}; padding: 8px; border-radius: 4px; margin-bottom: 5px; color:{txt};">
                <b>{icon} {r['Match']}</b> | {r['Scelta']} @{r['Quota']} | Res: {r.get('Risultato','-')} | <b>{r['Profitto']}€</b>
            </div>""", unsafe_allow_html=True)
    else: st.info("Aggiungi giocate per visualizzare le metriche fiscali.")
