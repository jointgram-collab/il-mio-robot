import streamlit as st
import pandas as pd
import requests
import time
import io
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V15.1.12 - COMPLETE SUITE", layout="wide")

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
    st.info(f"Slot API in uso: {st.session_state['api_usage']['active_index'] + 1}")
    c1, c2 = st.columns(2)
    c1.metric("Residui", st.session_state['api_usage']['remaining'])
    c2.metric("Usati", st.session_state['api_usage']['used'])
    st.divider()
    budget_cassa = st.number_input("Cassa (€)", value=BUDGET_DISPONIBILE)
    rischio_kelly = st.slider("Aggressività Kelly", 0.05, 0.50, 0.15)
    soglia_valore = st.slider("Filtro Valore %", 0, 15, 3) / 100

# --- INTERFACCIA PRINCIPALE ---
st.title("🎯 AI SNIPER V15.1.12")
df_attuale = carica_db()
t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER (VERSIONE COMPATTA SU RIGA UNICA) ---
with t1:
    pend_list = df_attuale[df_attuale['Esito'] == "Pendente"]['Match'].tolist()
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

    st.divider()

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
                                        opts.append({"T": f"{o['name'].upper()}", "Q": q, "V": val, "BK": b['title']})
                
                if opts:
                    best = max(opts, key=lambda x: x['V'])
                    # Calcolo Stake (Budget 500€)
                    stk = round(max(2.0, min(budget_cassa * (best['V']/(best['Q']-1)) * rischio_kelly, budget_cassa*0.15)), 2)
                    
                    # RIGA UNICA: Organizzazione in 6 colonne + tasto
                    col1, col2, col3, col4, col5 = st.columns([4, 1.2, 1.2, 1.2, 0.8])
                    
                    with col1:
                        st.markdown(f"📅 {dt_m.strftime('%d/%m %H:%M')} | **{nome_m}**")
                    with col2:
                        st.markdown(f"🎯 {best['T']} 2.5")
                    with col3:
                        st.markdown(f"📈 **@{best['Q']}** ({round(best['V']*100,1)}%)")
                    with col4:
                        st.markdown(f"💰 **STAKE: {stk}€**")
                    with col5:
                        if nome_m in pend_list:
                            st.button("✅", key=f"add_{i}", disabled=True)
                        elif st.button("ADD", key=f"add_{i}"):
                            nuova = pd.DataFrame([{"Data Match": dt_m.strftime('%d/%m %H:%M'), "Match": nome_m, "Scelta": f"{best['T']} 2.5", "Quota": best['Q'], "Stake": stk, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": m['sport_key'], "Risultato": "-"}])
                            salva_db(pd.concat([df_attuale, nuova], ignore_index=True))
                            st.rerun()
                    st.divider()
            except: continue

# --- TAB 2: PORTAFOGLIO ---
with t2:
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"].copy()
    if st.button("🔄 CONTROLLO AUTOMATICO RISULTATI", use_container_width=True):
        with st.status("Verifica risultati..."):
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
            if updates > 0: salva_db(df_attuale); st.rerun()
            else: st.info("Nessun nuovo risultato trovato.")

    if not df_p.empty:
        df_p['Stake'] = pd.to_numeric(df_p['Stake'], errors='coerce').fillna(0)
        df_p['Quota'] = pd.to_numeric(df_p['Quota'], errors='coerce').fillna(0)
        c_p1, c_p2 = st.columns(2)
        c_p1.metric("Stake in Gioco", f"{round(df_p['Stake'].sum(), 2)} €")
        c_p2.metric("Vincita Potenziale", f"{round((df_p['Stake'] * df_p['Quota']).sum(), 2)} €")
        st.divider()
        for i, r in df_p.iterrows():
            camp_label = LEAGUE_NAMES.get(r['Sport_Key'], r['Sport_Key'])
            label_main = f"{r['Data Match']} | {r['Match']} | **{camp_label}** | **{r['Scelta']}** | {r['Stake']}€"
            with st.expander(label_main):
                b1, b2, b3 = st.columns(3)
                if b1.button("VINTO ✅", key=f"w_{i}"): chiudi_gara(i, "VINTO", "MAN")
                if b2.button("PERSO ❌", key=f"l_{i}"): chiudi_gara(i, "PERSO", "MAN")
                if b3.button("ELIMINA 🗑️", key=f"d_{i}"): salva_db(df_attuale.drop(i)); st.rerun()

# --- TAB 3: FISCALE & BACKUP ---
with t3:
    if not df_attuale.empty:
        df_stats = df_attuale.copy()
        df_stats[['Stake', 'Quota', 'Profitto']] = df_stats[['Stake', 'Quota', 'Profitto']].apply(pd.to_numeric, errors='coerce').fillna(0)
        df_chiuse = df_stats[df_stats['Esito'].isin(["VINTO", "PERSO"])]
        
        p_netto = round(df_chiuse['Profitto'].sum(), 2)
        v_scommesso = round(df_chiuse['Stake'].sum(), 2)
        v_vinte = df_chiuse[df_chiuse['Esito'] == "VINTO"]
        t_incassato_lordo = round(v_vinte['Stake'].sum() + v_vinte['Profitto'].sum(), 2)
        roi_avg = round((p_netto/v_scommesso*100), 2) if v_scommesso > 0 else 0

        st.subheader("📈 Performance")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Profitto Netto", f"{p_netto} €", delta=f"{p_netto} €")
        m2.metric("Incasso Lordo", f"{t_incassato_lordo} €")
        m3.metric("Goal Target", f"{OBIETTIVO_TARGET} €")
        m4.metric("ROI", f"{roi_avg} %")

        st.divider()
        st.subheader("💾 Backup")
        bk1, bk2 = st.columns(2)
        with bk1: st.download_button("📥 Esporta Backup CSV", data=df_attuale.to_csv(index=False).encode('utf-8'), file_name=f"backup_sniper_{datetime.now().strftime('%d_%m')}.csv", use_container_width=True)
        with bk2:
            up = st.file_uploader("Ripristina Database", type="csv")
            if up and st.button("⚠️ CONFERMA OVERWRITE"): salva_db(pd.read_csv(up)); st.rerun()

        def color_rows(row):
            if row['Esito'] == 'VINTO': return ['background-color: rgba(40, 167, 69, 0.3)'] * len(row)
            elif row['Esito'] == 'PERSO': return ['background-color: rgba(220, 53, 69, 0.3)'] * len(row)
            elif row['Esito'] == 'Pendente': return ['background-color: rgba(255, 193, 7, 0.2)'] * len(row)
            return [''] * len(row)

        st.divider()
        st.dataframe(df_stats.sort_index(ascending=False).style.apply(color_rows, axis=1), use_container_width=True)
