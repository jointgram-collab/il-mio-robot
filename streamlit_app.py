import streamlit as st

# --- CSS RADICALE PER REPLICARE L'IMMAGINE e368ba ---
st.markdown("""
    <style>
    /* Forza il contenitore di Streamlit a non allargarsi */
    .block-container { max-width: 800px !important; padding-left: 1rem; padding-right: 1rem; }

    /* LA RIGA NERA STRETTA */
    .ultra-compact-row {
        background-color: #0d1117; /* Nero profondo come immagine */
        border: 1px solid #30363d;
        border-radius: 4px;
        padding: 4px 10px;
        margin-bottom: 4px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }

    .left-side {
        display: flex;
        align-items: center;
        gap: 10px;
        overflow: hidden;
    }

    .match-title { font-size: 13px; font-weight: 700; color: #ffffff; white-space: nowrap; }
    .bet-info { font-size: 13px; font-weight: 800; color: #58a6ff; white-space: nowrap; }
    .math-data { font-size: 11px; white-space: nowrap; }
    
    .stk { color: #f1c40f; font-weight: 700; }
    .val { color: #39d353; font-weight: 700; }
    .pipe { color: #30363d; margin: 0 4px; }

    /* IL PULSANTE PICCOLO A DESTRA */
    .stButton > button {
        width: 26px !important;
        height: 26px !important;
        min-width: 26px !important;
        background-color: #21262d !important;
        border: 1px solid #30363d !important;
        color: white !important;
        border-radius: 4px !important;
        padding: 0 !important;
        font-size: 14px !important;
        line-height: 1 !important;
    }

    .stButton > button[disabled] {
        border-color: #39d353 !important;
        color: #39d353 !important;
        background-color: transparent !important;
        opacity: 1 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNZIONE DI RENDERING ---
def render_match(id, squadre, giocata, quota, stake, valore, gestito=False):
    # Creiamo una riga con una colonna piccolissima per il tasto alla fine
    c_main, c_btn = st.columns([0.92, 0.08])
    
    with c_main:
        st.markdown(f"""
            <div class="ultra-compact-row">
                <div class="left-side">
                    <span class="match-title">⚽ {squadre}</span>
                    <span class="bet-info">{giocata} @{quota}</span>
                    <div class="math-data">
                        <span class="stk">S:{stake}€</span>
                        <span class="pipe">|</span>
                        <span class="val">V:+{valore}%</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    with c_btn:
        if not gestito:
            st.button("＋", key=f"bt_{id}")
        else:
            st.button("✔", key=f"bt_{id}", disabled=True)

# --- VISUALIZZAZIONE ---
st.markdown("### 🔍 Scanner Attivo")

render_match(1, "Juve-Inter", "OV 2.5", "1.95", "15.4", "5.2")
render_match(2, "Bari-Palermo", "UN 2.5", "2.05", "11.7", "12.3", gestito=True)
render_match(3, "Real-Barca", "OV 2.5", "1.85", "20.0", "4.1")
