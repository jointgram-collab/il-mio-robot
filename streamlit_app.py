import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V15.1.7 - AUTO-SYNC", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONFIGURAZIONE COSTANTI ---
API_KEYS = ['01f1c8f2a314814b17de03eeb6c53623', '55f08c25f38fa1006dd9e66282170e1a']
BUDGET_DISPONIBILE = 500.0 
OBIETTIVO_TARGET = 5000.0   

if 'api_usage' not in st.session_state:
    st.session_state['api_usage'] = {'remaining': "N/D", 'used': "N/D", 'active_index': 0}
if 'api_data' not in st.session_state:
    st.session_state['api_data'] = []

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie",
    "soccer_spain_la_liga": "🇪🇸 La Liga", "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_france_ligue_1": "🇫🇷 Ligue 1", "soccer_uefa_europa_league": "🇪🇺 Europa League",
    "soccer_uefa_champions_league": "🏆 Champions"
}

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "William Hill", "888sport"]

# --- FUNZIONI CORE API ---
def chiamata_sicura_api(endpoint, params_extra={}):
    idx = st.session_state['api_usage'].get('active_index', 0)
    for _ in range(len(API_KEYS)):
        current_key = API_KEYS[idx]
        params = {'api_key': current_key}
        params.update(params_extra)
        try:
            r = requests.get(endpoint, params=params)
            if r.status_code in [401, 429]:
                idx = (idx + 1) % len(API_KEYS)
                st.session_state['api_usage']['active_index'] = idx
                continue
            if r.status_code == 200:
                st.session_state['api_usage']['remaining'] = r.headers.get('x-requests-remaining', "0")
                st.session_state['api_usage']['used'] = r.headers.get('x-requests-used', "0")
                return r.json()
        except:
            idx = (idx + 1) % len(API_KEYS)
            st.session_state['api_usage']['active_index'] = idx
    return None

# --- FUNZIONI DATABASE ---
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
        df.at[idx, 'Esito'] = esito
        df.at[idx, 'Risultato'] = risultato_score
        df.at[idx, 'Profitto'] = round((s * q) - s, 2) if esito == "VINTO" else -s
        salva_db(df)
        st.rerun()

# --- SIDEBAR ---
with st.sidebar:
    st.header("📊 Sistema & API")
    st.info(f"Slot API: {st.session_state['api_usage']['active_index'] + 1}")
    c1, c2 = st.columns(2)
    c1.metric("Residui", st.session_state['api_usage']['remaining'])
    c2.metric("Usati", st.session_state['api_usage']['used'])
    st.divider()
    budget_cassa = st.number_input("Cassa (€)", value=BUDGET_DISPONIBILE)
    rischio_kelly = st.slider("Aggressività Kelly", 0.05, 0.50, 0.15)
    soglia_valore = st.slider("Filtro Valore %", 0, 15, 3) / 100

# --- INTERFACCIA PRINCIPALE ---
st.title("🎯 AI SNIPER V15.1.7")
df_attuale = carica_db()
t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER ---
with t1:
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    c_sel, c_sing, c_all, c_ore = st.columns([1.5, 1, 1, 1])
    sel_name = c_sel.selectbox("Campionato:", list(leagues.keys()))
    ore_limite = c_ore.selectbox("Fino a (Ore):", [24, 48, 72, 96, 120, 168], index=2)
    
    if c_sing.button("🎯 SCAN SINGOLO", use_container_width=True):
        sport_key = leagues[sel_name]
        data = chiamata_sicura_api(f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds/', {'regions': 'eu', 'markets': 'totals'})
        if data: st.session_state['api_data'] = data
        st.rerun()

    if c_all.button("🚀 SCAN TOTALE", use_container_width=True):
        all_found = []
        pbar = st.progress(0)
        for idx, k in enumerate(LEAGUE_NAMES.keys()):
            data = chiamata_sicura_api(f'https://api.the-odds-api.com/v4/sports/{k}/odds/', {'regions': 'eu', 'markets': 'totals'})
            if data: all_found.extend(data)
            time.sleep(0.3)
            pbar.progress((idx + 1) / len(LEAGUE_NAMES))
        st.session_state['api_data'] = all_found
        st.rerun()

    if st.session_state['api_data']:
        for i, m in enumerate(st.session_state['api_data']):
            try:
                nome_m = f"{m['home_team']}-{m['away_team']}"
                dt_m = datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
                if dt_m > datetime.utcnow() + timedelta(hours=ore_limite): continue
                
                opts = []
                for b in m.get('bookmakers', []):
                    if b['title'] in BK_EURO_AUTH:
                        mk = next((x for x in b['markets'] if x['key'] == 'totals'), None)
                        if mk:
                            for o in mk['outcomes']:
                                if o.get('point') == 2.5:
                                    q = o['price']
                                    val = ((1/q + 0.06) * q) - 1
                                    if val >= soglia_valore:
                                        opts.append({"T": f"{o['name'].upper()} 2.5", "Q": q, "V": val, "BK": b['title']})
                if opts:
                    best = max(opts, key=lambda x: x['V'])
                    stk = round(max(2.0, min(budget_cassa * (best['V']/(best['Q']-1)) * rischio_kelly, budget_cassa*0.15)), 2)
                    c_a, c_b = st.columns([3, 1])
                    c_a.markdown(f"📅 {dt_m.strftime('%d/%m %H:%M')} | **{nome_m}**<br>🎯 **{best['T']}** @{best['Q']} | Val: {round(best['V']*100,1)}% | 🏦 {best['BK']}", unsafe_allow_html=True)
                    if c_b.button("ADD", key=f"add_{i}", use_container_width=True):
                        nuova = pd.DataFrame([{"Data Match": dt_m.strftime('%d/%m %H:%M'), "Match": nome_m, "Scelta": best['T'], "Quota": best['Q'], "Stake": stk, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": m['sport_key'], "Risultato": "-"}])
                        salva_db(pd.concat([df_attuale, nuova], ignore_index=True)); st.rerun()
            except: continue

# --- TAB 2: PORTAFOGLIO (CON AUTO-SYNC) ---
with t2:
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"].copy()
    
    # PULSANTE SYNC AUTOMATICO
    if st.button("🔄 CONTROLLO AUTOMATICO RISULTATI", use_container_width=True):
        with st.status("Verifica risultati in corso..."):
            sport_attivi = df_p['Sport_Key'].unique()
            updates = 0
            for skey in sport_attivi:
                res_data = chiamata_sicura_api(f'https://api.the-odds-api.com/v4/sports/{skey}/scores/', {'daysFrom': 3})
                if res_data:
                    for match_res in res_data:
                        if match_res.get('completed'):
                            m_name = f"{match_res['home_team']}-{match_res['away_team']}"
                            scores = match_res.get('scores', [])
                            if len(scores) == 2:
                                tot = int(scores[0]['score']) + int(scores[1]['score'])
                                final_s = f"{scores[0]['score']}-{scores[1]['score']}"
                                
                                for idx, row in df_p[df_p['Match'] == m_name].iterrows():
                                    esito_final = "VINTO" if (tot > 2.5 and "OVER" in row['Scelta']) or (tot < 2.5 and "UNDER" in row['Scelta']) else "PERSO"
                                    df_attuale.at[idx, 'Esito'] = esito_final
                                    df_attuale.at[idx, 'Risultato'] = final_s
                                    q, s = float(row['Quota']), float(row['Stake'])
                                    df_attuale.at[idx, 'Profitto'] = round((s * q) - s, 2) if esito_final == "VINTO" else -s
                                    updates += 1
            if updates > 0:
                salva_db(df_attuale)
                st.success(f"Aggiornate {updates} partite!")
                st.rerun()
            else:
                st.info("Nessun nuovo risultato trovato.")

    if not df_p.empty:
        st.divider()
        for i, r in df_p.iterrows():
            camp_label = LEAGUE_NAMES.get(r['Sport_Key'], r['Sport_Key'])
            label_main = f"{r['Data Match']} | {r['Match']} | **{camp_label}** | **{r['Scelta']}** | {r['Stake']}€"
            with st.expander(label_main):
                b1, b2, b3 = st.columns(3)
                if b1.button("VINTO ✅", key=f"w_{i}"): chiudi_gara(i, "VINTO", "MAN")
                if b2.button("PERSO ❌", key=f"l_{i}"): chiudi_gara(i, "PERSO", "MAN")
                if b3.button("ELIMINA 🗑️", key=f"d_{i}"): salva_db(df_attuale.drop(i)); st.rerun()

# --- TAB 3: FISCALE ---
with t3:
    if not df_attuale.empty:
        df_stats = df_attuale.copy()
        df_stats[['Stake', 'Quota', 'Profitto']] = df_stats[['Stake', 'Quota', 'Profitto']].apply(pd.to_numeric, errors='coerce').fillna(0)
        df_chiuse = df_stats[df_stats['Esito'].isin(["VINTO", "PERSO"])]
        
        p_netto = round(df_chiuse['Profitto'].sum(), 2)
        v_scommesso = round(df_chiuse['Stake'].sum(), 2)
        roi_avg = round((p_netto/v_scommesso*100), 2) if v_scommesso > 0 else 0

        m1, m2, m3 = st.columns(3)
        m1.metric("Profitto Netto", f"{p_netto} €", delta=f"{p_netto} €", delta_color="normal" if p_netto >= 0 else "inverse")
        m2.metric("ROI", f"{roi_avg} %", delta=f"{roi_avg} %", delta_color="normal" if roi_avg >= 0 else "inverse")
        m3.metric("Volume", f"{v_scommesso} €")
        
        st.divider()
        st.dataframe(df_stats.sort_index(ascending=False), use_container_width=True)
