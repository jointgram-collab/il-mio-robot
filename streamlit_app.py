import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAZIONE UI ---
st.set_page_config(page_title="AI SNIPER V15.1.12 - FULL ARCHIVE", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. COSTANTI GLOBALI (NON RIMUOVERE) ---
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

# --- 3. FUNZIONI DI SISTEMA ---
def chiamata_sicura_api(endpoint, params_extra={}):
    idx = st.session_state['api_usage'].get('active_index', 0)
    for _ in range(len(API_KEYS)):
        current_key = API_KEYS[idx]
        params = {'api_key': current_key}
        params.update(params_extra)
        try:
            r = requests.get(endpoint, params=params)
            if r.status_code == 200:
                st.session_state['api_usage']['remaining'] = r.headers.get('x-requests-remaining', "0")
                st.session_state['api_usage']['used'] = r.headers.get('x-requests-used', "0")
                return r.json()
            idx = (idx + 1) % len(API_KEYS)
            st.session_state['api_usage']['active_index'] = idx
        except:
            idx = (idx + 1) % len(API_KEYS)
    return None

def carica_db():
    try:
        df = conn.read(worksheet="Giocate", ttl=0)
        # Assicura che le colonne esistano
        colonne_necessarie = ["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"]
        if df is None or df.empty:
            return pd.DataFrame(columns=colonne_necessarie)
        return df.dropna(subset=["Match"])
    except:
        return pd.DataFrame(columns=["Data Match", "Match", "Scelta", "Quota", "Stake", "Bookmaker", "Esito", "Profitto", "Sport_Key", "Risultato"])

def salva_db(df):
    conn.update(worksheet="Giocate", data=df)
    st.cache_data.clear()

def chiudi_gara(idx, esito, risultato_score="-"):
    df = carica_db()
    if idx in df.index:
        q = pd.to_numeric(df.at[idx, 'Quota'], errors='coerce')
        s = pd.to_numeric(df.at[idx, 'Stake'], errors='coerce')
        df.at[idx, 'Esito'] = esito
        df.at[idx, 'Risultato'] = risultato_score
        df.at[idx, 'Profitto'] = round((s * q) - s, 2) if esito == "VINTO" else -s
        salva_db(df)
        st.rerun()

def check_risultati_automatico():
    df = carica_db()
    pendenti = df[df['Esito'] == "Pendente"]
    if pendenti.empty:
        st.info("Nessuna partita da controllare.")
        return
    
    st.toast("Interrogazione API Risultati...")
    keys_da_controllare = pendenti['Sport_Key'].unique()
    aggiornati = False
    
    for skey in keys_da_controllare:
        res = chiamata_sicura_api(f'https://api.the-odds-api.com/v4/sports/{skey}/scores/', {'daysFrom': 3})
        if res:
            for match_api in res:
                if not match_api['completed']: continue
                nome_api = f"{match_api['home_team']}-{match_api['away_team']}"
                
                for idx, r_db in pendenti[pendenti['Match'] == nome_api].iterrows():
                    score_list = match_api['scores']
                    if score_list:
                        tot_goal = sum(int(s['score']) for s in score_list)
                        sc_clean = str(r_db['Scelta']).upper()
                        # Logica di verifica esito
                        esito = "VINTO" if ("OVER" in sc_clean and tot_goal > 2.5) or ("UNDER" in sc_clean and tot_goal < 2.5) else "PERSO"
                        
                        q, s = float(r_db['Quota']), float(r_db['Stake'])
                        df.at[idx, 'Esito'] = esito
                        df.at[idx, 'Risultato'] = f"{score_list[0]['score']}-{score_list[1]['score']}"
                        df.at[idx, 'Profitto'] = round((s * q) - s, 2) if esito == "VINTO" else -s
                        aggiornati = True
    
    if aggiornati:
        salva_db(df)
        st.success("Tutti i risultati sono stati sincronizzati!")
        st.rerun()
    else:
        st.warning("Nessun match completato trovato nelle ultime ore.")

# --- 4. INTERFACCIA ---
st.title("🎯 AI SNIPER V15.1.12")
df_attuale = carica_db()

with st.sidebar:
    st.header("⚙️ Parametri")
    budget_cassa = st.number_input("Budget Attuale (€)", value=BUDGET_DISPONIBILE)
    rischio_kelly = st.slider("Aggressività Kelly", 0.05, 0.50, 0.15)
    soglia_valore = st.slider("Min Value %", 0, 15, 3) / 100
    st.divider()
    st.write(f"API utilizzate oggi: {st.session_state['api_usage']['used']}")

tab1, tab2, tab3 = st.tabs(["🔍 SCANNER LIVE", "💼 PORTAFOGLIO", "📊 FISCALE & BACKUP"])

# --- TAB 1: SCANNER ---
with tab1:
    leagues = {v: k for k, v in LEAGUE_NAMES.items()}
    c1, c2, c3 = st.columns([2, 1, 1])
    sel_name = c1.selectbox("Seleziona Campionato:", list(leagues.keys()))
    ore_limite = c3.selectbox("Ore max:", [24, 48, 72, 96, 120], index=2)
    
    if c2.button("🎯 AVVIA SCAN", use_container_width=True):
        data = chiamata_sicura_api(f'https://api.the-odds-api.com/v4/sports/{leagues[sel_name]}/odds/', {'regions': 'eu', 'markets': 'totals'})
        if data: st.session_state['api_data'] = data
        st.rerun()

    if st.session_state['api_data']:
        st.divider()
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
                                    if val >= soglia_valore:
                                        opts.append({"T": o['name'].upper(), "Q": q, "V": val, "BK": b['title']})
                if opts:
                    best = max(opts, key=lambda x: x['V'])
                    stk = round(max(2.0, min(budget_cassa * (best['V']/(best['Q']-1)) * rischio_kelly, budget_cassa*0.15)), 2)
                    
                    col1, col2, col3, col4, col5 = st.columns([3, 1, 1.5, 1, 0.8])
                    col1.markdown(f"📅 {dt_m.strftime('%d/%m %H:%M')} | **{nome_m}**")
                    col2.markdown(f"🎯 {best['T']} | **@{best['Q']}**")
                    col3.markdown(f"🏦 {best['BK']} | **{round(best['V']*100,1)}%**")
                    col4.markdown(f"💰 **{stk}€**")
                    if col5.button("ADD", key=f"a_{i}"):
                        nuova = pd.DataFrame([{"Data Match": dt_m.strftime('%d/%m %H:%M'), "Match": nome_m, "Scelta": f"{best['T']} 2.5", "Quota": best['Q'], "Stake": stk, "Bookmaker": best['BK'], "Esito": "Pendente", "Profitto": 0.0, "Sport_Key": m['sport_key'], "Risultato": "-"}])
                        salva_db(pd.concat([df_attuale, nuova], ignore_index=True)); st.rerun()
                    st.divider()
            except: continue

# --- TAB 2: PORTAFOGLIO ---
with tab2:
    df_p = df_attuale[df_attuale['Esito'] == "Pendente"].copy()
    c_m1, c_m2, c_m3 = st.columns([1, 1, 1])
    
    if not df_p.empty:
        df_p['Stake'] = pd.to_numeric(df_p['Stake']).fillna(0)
        df_p['Quota'] = pd.to_numeric(df_p['Quota']).fillna(0)
        stk_tot = round(df_p['Stake'].sum(), 2)
        vinc_pot = round((df_p['Stake'] * df_p['Quota']).sum(), 2)
        c_m1.metric("Stake Impegnato", f"{stk_tot} €")
        c_m2.metric("Vincita Potenziale", f"{vinc_pot} €")
    
    if c_m3.button("🔄 AGGIORNA RISULTATI API", use_container_width=True, type="primary"):
        check_risultati_automatico()
    
    st.divider()
    for i, r in df_p.iterrows():
        with st.expander(f"📅 {r['Data Match']} | {r['Match']} | 🏦 {r['Bookmaker']} | 💰 STAKE: {r['Stake']}€"):
            st.write(f"🎯 Scommessa: **{r['Scelta']}** @{r['Quota']} | Vincita Lorda: {round(float(r['Stake'])*float(r['Quota']),2)}€")
            b1, b2, b3 = st.columns(3)
            if b1.button("VINTO ✅", key=f"w_{i}"): chiudi_gara(i, "VINTO")
            if b2.button("PERSO ❌", key=f"l_{i}"): chiudi_gara(i, "PERSO")
            if b3.button("ELIMINA 🗑️", key=f"d_{i}"): salva_db(df_attuale.drop(i)); st.rerun()

# --- TAB 3: FISCALE & BACKUP ---
with tab3:
    if not df_attuale.empty:
        df_stats = df_attuale.copy()
        df_stats[['Stake', 'Profitto']] = df_stats[['Stake', 'Profitto']].apply(pd.to_numeric, errors='coerce').fillna(0)
        df_chiuse = df_stats[df_stats['Esito'].isin(["VINTO", "PERSO"])].copy()
        
        # Metriche
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Profitto Netto", f"{round(df_chiuse['Profitto'].sum(), 2)} €")
        f2.metric("Volume Scommesso", f"{round(df_chiuse['Stake'].sum(), 2)} €")
        f3.metric("Goal Target", f"{OBIETTIVO_TARGET} €")
        f4.metric("Incasso Lordo", f"{round(df_chiuse[df_chiuse['Esito']=='VINTO']['Profitto'].sum() + df_chiuse[df_chiuse['Esito']=='VINTO']['Stake'].sum(), 2)} €")
        
        # Storico Colorato
        st.subheader("📜 Storico Giocate")
        for i, r in df_chiuse[::-1].iterrows():
            col, bor = ("#d4edda", "#155724") if r['Esito'] == "VINTO" else ("#f8d7da", "#721c24")
            st.markdown(f"""<div style="background-color:{col}; border-radius:10px; padding:15px; margin-bottom:10px; border: 1px solid {bor}; color:{bor};">
                <b>{r['Esito']}</b> | {r['Data Match']} | {r['Match']} | {r['Scelta']} @{r['Quota']} | Stake: {r['Stake']}€ | <b>Profitto: {r['Profitto']}€</b> | Ris: {r['Risultato']}
                </div>""", unsafe_allow_html=True)
        
        st.divider()
        st.subheader("⚙️ Gestione Database")
        b_col1, b_col2 = st.columns(2)
        
        # Download
        b_col1.download_button("📥 SCARICA BACKUP CSV", data=df_attuale.to_csv(index=False).encode('utf-8'), file_name=f"sniper_backup_{datetime.now().strftime('%d%m')}.csv", use_container_width=True)
        
        # Upload
        up_file = b_col2.file_uploader("📤 RIPRISTINA DA CSV", type="csv")
        if up_file:
            if st.button("🔄 CONFERMA SOVRASCRITTURA", use_container_width=True):
                new_df = pd.read_csv(up_file)
                salva_db(new_df); st.success("Database Ripristinato!"); st.rerun()
        
        # Reset
        if st.checkbox("Abilita cancellazione totale"):
            if st.button("⚠️ RESET DATABASE"):
                salva_db(pd.DataFrame(columns=df_attuale.columns)); st.rerun()
