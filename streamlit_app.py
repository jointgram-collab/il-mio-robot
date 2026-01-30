import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V13.6 - STABLE FULL", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)
API_KEY = '01f1c8f2a314814b17de03eeb6c53623'

if 'api_usage' not in st.session_state:
    st.session_state['api_usage'] = {'remaining': "N/D", 'used': "N/D"}
if 'api_data' not in st.session_state:
    st.session_state['api_data'] = []

BK_EURO_AUTH = ["Bet365", "Snai", "Better", "Planetwin365", "Eurobet", "Goldbet", "Sisal", "Bwin", "William Hill", "888sport"]

LEAGUE_NAMES = {
    "soccer_italy_serie_a": "🇮🇹 Serie A", "soccer_italy_serie_b": "🇮🇹 Serie B",
    "soccer_epl": "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie",
    "soccer_spain_la_liga": "🇪🇸 La Liga", "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_france_ligue_1": "🇫🇷 Ligue 1", "soccer_uefa_europa_league": "🇪🇺 Europa League",
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

def chiudi_manualmente(idx, esito):
    df = carica_db()
    if idx in df.index:
        q, s = float(df.at[idx, 'Quota']), float(df.at[idx, 'Stake'])
        df.at[idx, 'Esito'] = esito
        df.at[idx, 'Risultato'] = "MANUALE"
        df.at[idx, 'Profitto'] = round((s * q) - s, 2) if esito == "VINTO" else -s
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

# --- TAB 1: SCANNER ---
with t1:
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    c_sel, c_all, c_sing, c_ore = st.columns([1.5, 1, 1, 1])
    sel_name = c_sel.selectbox("Seleziona Campionato:", list(leagues.keys()))
    ore_limite = c_ore.selectbox("Finestra Ore:", [24, 48, 72, 96, 120, 168], index=2)
    
    if c_all.button("🚀 TOTALE", use_container_width=True):
        all_found = []
        keys_to_scan = list(LEAGUE_NAMES.keys())
        pbar = st.progress(0)
        limit_date = datetime.utcnow() + timedelta(hours=ore_limite)
        for idx, k in enumerate(keys_to_scan):
            r = requests.get(f'https://api.the-odds-api.com/v4/sports/{k}/odds/', params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
            if r.status_code == 200:
                data = r.json()
                filtered = [m for m in data if datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ") <= limit_date]
                all_found.extend(filtered)
                st.session_state['api_usage']['remaining'] = r.headers.get('x-requests-remaining')
            time.sleep(0.4)
            pbar.progress((idx + 1) / len(keys_to_scan))
        st.session_state['api_data'] = all_found
        st.rerun()

    if c_sing.button("🔍 SINGOLA", use_container_width=True):
        target_key = leagues[sel_name]
        res = requests.get(f'https://api.the-odds-api.com/v4/sports/{target_key}/odds/', params={'api_key': API_KEY, 'regions': 'eu', 'markets': 'totals'})
        if res.status_code == 200:
            data = res.json()
            limit_date = datetime.utcnow() + timedelta(hours=ore_limite)
            st.session_state['api_data'] = [m for m in data if datetime.strptime(m['commence_time'], "%Y-%m-%dT%H:%M:%SZ") <= limit_date]
            st.session_state['api_usage']['remaining'] = res.headers.get('x-requests-remaining')
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
                        c_a.markdown(f"📅 {dt_m} | **{nome_m}**<br>🎯 **{best['T']}** @{best['Q']} | Stake: **{stk_c}€** | 🏦 {best['BK']}", unsafe_allow_html=True)
                        if nome_m in pend_list:
                            c_b.button("✅", key=f"add_{i}", disabled=True, use_container_width=True)
                        else:
                            if c_b.button(f"ADD", key=f"add_{i}", use_container_width=True):
                                nuova = pd.DataFrame([{"Data Match": dt_m, "Match": nome_m, "Scelta": best['T'], "Quota": best['Q'], "Stake": stk_c, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": m['sport_key'], "Risultato": "-"}])
                                salva_db(pd.concat([df_attuale, nuova], ignore_index=True)); st.rerun()
                        st.divider()
            except: continue

# --- TAB 2: PORTAFOGLIO ---
with t2:
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"]
    if not df_p.empty:
        tot_imp = round(df_p['Stake'].astype(float).sum(), 2)
        rit_pot = round((df_p['Stake'].astype(float) * df_p['Quota'].astype(float)).sum(), 2)
        # Fix Colore Testo Bianco
        st.markdown(f"""
            <div style='background:#1c2128; padding:15px; border-radius:10px; display:flex; justify-content:space-around; text-align:center;'>
                <div><small style='color:white;'>IMPEGNATO</small><br><strong style='color:#ffc107; font-size:20px;'>{tot_imp}€</strong></div>
                <div style='border-left:1px solid #333; padding-left:20px;'><small style='color:white;'>RITORNO POT.</small><br><strong style='color:#00ff00; font-size:20px;'>{rit_pot}€</strong></div>
            </div>
        """, unsafe_allow_html=True)
        st.divider()
        for i, r in df_p.iterrows():
            nome_camp = LEAGUE_NAMES.get(r['Sport_Key'], "Campionato")
            c1, c2, c3, c4 = st.columns([12, 1.2, 1.2, 1.2])
            c1.info(f"📅 **{r['Data Match']}** | **{nome_camp}**\n\n**{r['Match']}** | {r['Scelta']} @{r['Quota']} | Stake: **{r['Stake']}€** | 🏦 {r['Bookmaker']}")
            if c2.button("✅", key=f"w_{i}"): chiudi_manualmente(i, "VINTO")
            if c3.button("❌", key=f"l_{i}"): chiudi_manualmente(i, "PERSO")
            if c4.button("🗑️", key=f"d_{i}"): salva_db(df_attuale.drop(i)); st.rerun()
    else: st.info("Nessuna giocata pendente.")

# --- TAB 3: FISCALE ---
with t3:
    if not df_attuale.empty:
        df_vis = df_attuale.copy()
        df_vis['Campionato'] = df_vis['Sport_Key'].map(LEAGUE_NAMES).fillna("Altro")
        v_df = df_vis[df_vis['Esito'] == "VINTO"]
        p_df = df_vis[df_vis['Esito'] == "PERSO"]
        win_rate = round((len(v_df) / (len(v_df) + len(p_df)) * 100), 1) if (len(v_df) + len(p_df)) > 0 else 0
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📈 Profitto Netto", f"{round(df_vis['Profitto'].sum(), 2)} €")
        m2.metric("🎯 Win Rate", f"{win_rate} %")
        m3.metric("💰 Tot. Giocato", f"{round(df_vis['Stake'].sum(), 2)} €")
        m4.metric("📊 Match Chiusi", len(v_df) + len(p_df))
        
        st.divider()
        c_exp, c_imp = st.columns(2)
        with c_exp:
            csv = df_attuale.to_csv(index=False).encode('utf-8')
            st.download_button("📥 SCARICA BACKUP", data=csv, file_name=f"sniper_backup_{date.today()}.csv", use_container_width=True)
        with c_imp:
            up = st.file_uploader("Ripristina Backup", type="csv")
            if up and st.button("🔄 CARICA CSV", use_container_width=True):
                salva_db(pd.read_csv(up)); st.rerun()
        
        st.divider()
        def color_esito(row):
            if row['Esito'] == "VINTO": return ['background-color: rgba(40, 167, 69, 0.2)'] * len(row)
            if row['Esito'] == "PERSO": return ['background-color: rgba(220, 53, 69, 0.2)'] * len(row)
            return ['background-color: rgba(255, 193, 7, 0.2)'] * len(row)

        st.write("### Storico Operazioni")
        cols_ordine = ["Data Match", "Campionato", "Match", "Scelta", "Quota", "Stake", "Esito", "Profitto", "Risultato", "Bookmaker"]
        st.dataframe(df_vis[cols_ordine].sort_index(ascending=False).style.apply(color_esito, axis=1), use_container_width=True)
