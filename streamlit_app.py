import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V14.6 - FULL STABLE", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- GESTIONE DOPPIA CHIAVE ---
# Ho inserito la tua nuova chiave sniper.sport2026@gmail.com come seconda opzione
API_KEYS = [
    '01f1c8f2a314814b17de03eeb6c53623', # Chiave 1
    '55f08c25f38fa1006dd9e66282170e1a'  # Chiave 2 (sniper.sport2026@gmail.com)
]

# Costanti Obiettivo e Budget (Basate sulle tue preferenze salvate)
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
    """Tenta la chiamata con la chiave attiva. Se fallisce (429/401), ruota sulla successiva."""
    idx = st.session_state['api_usage'].get('active_index', 0)
    for _ in range(len(API_KEYS)):
        current_key = API_KEYS[idx]
        params = {'api_key': current_key, 'regions': 'eu', 'markets': 'totals'}
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

# --- INTERFACCIA ---
st.title("🎯 AI SNIPER V14.6")
df_attuale = carica_db()

with st.sidebar:
    st.header("📊 Stato API")
    st.info(f"Slot Attivo: {st.session_state['api_usage']['active_index'] + 1} / {len(API_KEYS)}")
    c1, c2 = st.columns(2)
    c1.metric("Residui", st.session_state['api_usage']['remaining'])
    c2.metric("Usati", st.session_state['api_usage']['used'])
    st.divider()
    budget_cassa = st.number_input("Cassa Operativa (€)", value=BUDGET_DISPONIBILE)
    rischio = st.slider("Aggressività (Kelly)", 0.05, 0.50, 0.15)
    soglia_val = st.slider("Filtro Valore Min %", 0, 15, 3) / 100

t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

# --- TAB 1: SCANNER ---
with t1:
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    c_sel, c_all, c_sing, c_ore = st.columns([1.5, 1, 1, 1])
    sel_name = c_sel.selectbox("Campionato:", list(leagues.keys()))
    ore_limite = c_ore.selectbox("Window Ore:", [24, 48, 72, 96, 120, 168], index=2)
    
    if c_all.button("🚀 SCAN TOTALE", use_container_width=True):
        all_found = []
        pbar = st.progress(0)
        for idx, k in enumerate(LEAGUE_NAMES.keys()):
            data = chiamata_sicura_api(f'https://api.the-odds-api.com/v4/sports/{k}/odds/')
            if data: all_found.extend(data)
            time.sleep(0.3)
            pbar.progress((idx + 1) / len(LEAGUE_NAMES))
        st.session_state['api_data'] = all_found
        st.rerun()

    if c_sing.button("🔍 SCAN SINGOLO", use_container_width=True):
        data = chiamata_sicura_api(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_name]}/odds/')
        if data: st.session_state['api_data'] = data
        st.rerun()

    if st.session_state['api_data']:
        pend_list = df_attuale[df_attuale['Esito'] == "Pendente"]['Match'].tolist()
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
                                    if val >= soglia_val:
                                        opts.append({"T": f"{o['name'].upper()} 2.5", "Q": q, "V": val, "BK": b['title']})
                if opts:
                    best = max(opts, key=lambda x: x['V'])
                    stk = round(max(2.0, min(budget_cassa * (best['V']/(best['Q']-1)) * rischio, budget_cassa*0.15)), 2)
                    c_a, c_b = st.columns([3, 1])
                    c_a.markdown(f"📅 {dt_m.strftime('%d/%m %H:%M')} | **{nome_m}**<br>🎯 **{best['T']}** @{best['Q']} | 🏦 {best['BK']}", unsafe_allow_html=True)
                    if nome_m in pend_list:
                        c_b.button("✅", key=f"add_{i}", disabled=True, use_container_width=True)
                    elif c_b.button("ADD", key=f"add_{i}", use_container_width=True):
                        nuova = pd.DataFrame([{"Data Match": dt_m.strftime('%d/%m %H:%M'), "Match": nome_m, "Scelta": best['T'], "Quota": best['Q'], "Stake": stk, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": m['sport_key'], "Risultato": "-"}])
                        salva_db(pd.concat([df_attuale, nuova], ignore_index=True)); st.rerun()
            except: continue

# --- TAB 2: PORTAFOGLIO ---
with t2:
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"]
    if st.button("🤖 AUTO-CHECK RISULTATI", use_container_width=True, type="primary"):
        with st.spinner("Controllo esiti in corso..."):
            for idx, row in df_p.iterrows():
                data = chiamata_sicura_api(f"https://api.the-odds-api.com/v4/sports/{row['Sport_Key']}/scores/", {'daysFrom': 3})
                if data:
                    m_res = next((s for s in data if s['home_team'] in row['Match'] and s['completed']), None)
                    if m_res:
                        h, a = m_res['scores'][0]['score'], m_res['scores'][1]['score']
                        vinto = (row['Scelta'] == "OVER 2.5" and (int(h)+int(a)) > 2.5) or (row['Scelta'] == "UNDER 2.5" and (int(h)+int(a)) < 2.5)
                        chiudi_gara(idx, "VINTO" if vinto else "PERSO", f"{h}-{a}")
        st.rerun()
    
    if not df_p.empty:
        for i, r in df_p.iterrows():
            label = f"{r['Match']} | @{r['Quota']} | {r['Stake']}€"
            with st.expander(label):
                st.write(f"🏦 {r['Bookmaker']} | 🎯 {r['Scelta']}")
                b1, b2, b3 = st.columns(3)
                if b1.button("VINTO ✅", key=f"w_{i}", use_container_width=True): chiudi_gara(i, "VINTO", "MAN")
                if b2.button("PERSO ❌", key=f"l_{i}", use_container_width=True): chiudi_gara(i, "PERSO", "MAN")
                if b3.button("ELIMINA 🗑️", key=f"d_{i}", use_container_width=True): salva_db(df_attuale.drop(i)); st.rerun()
    else:
        st.info("Nessuna operazione pendente.")

# --- TAB 3: FISCALE ---
with t3:
    if not df_attuale.empty:
        df_vis = df_attuale.copy()
        v_df = df_vis[df_vis['Esito'] == "VINTO"]
        p_df = df_vis[df_vis['Esito'] == "PERSO"]
        
        profitto_netto = round(df_vis['Profitto'].sum(), 2)
        win_rate = round((len(v_df) / (len(v_df) + len(p_df)) * 100), 1) if (len(v_df) + len(p_df)) > 0 else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("📈 Profitto Netto", f"{profitto_netto} €")
        m2.metric("🎯 Win Rate", f"{win_rate} %")
        m3.metric("📊 Match Chiusi", len(v_df) + len(p_df))
        
        st.write(f"### 🚀 Obiettivo Scalata: {OBIETTIVO_TARGET}€")
        progresso = min(1.0, max(0.0, profitto_netto / OBIETTIVO_TARGET)) if profitto_netto > 0 else 0.0
        st.progress(progresso)
        st.caption(f"Completato: {int(progresso*100)}% (Cassa Target: {OBIETTIVO_TARGET}€)")
        
        st.divider()
        st.write("### Storico Operazioni")
        def color_esito(row):
            if row['Esito'] == "VINTO": return ['background-color: rgba(40, 167, 69, 0.2)'] * len(row)
            if row['Esito'] == "PERSO": return ['background-color: rgba(220, 53, 69, 0.2)'] * len(row)
            return [''] * len(row)

        st.dataframe(df_vis.sort_index(ascending=False).style.apply(color_esito, axis=1), use_container_width=True)
        
        c_exp, c_imp = st.columns(2)
        c_exp.download_button("📥 SCARICA BACKUP CSV", data=df_attuale.to_csv(index=False).encode('utf-8'), file_name=f"sniper_backup_{date.today()}.csv", use_container_width=True)
        up_file = c_imp.file_uploader("Ripristina Database", type="csv")
        if up_file and st.button("🔄 AVVIA RIPRISTINO"):
            salva_db(pd.read_csv(up_file)); st.rerun()
    else:
        st.info("Inizia a scommettere per vedere le statistiche della scalata!")
