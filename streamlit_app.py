import streamlit as st

# --- CSS DEFINITIVO: SINGLE LINE DESIGN ---
st.markdown("""
    <style>
    /* Reset per Mobile */
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    
    .main-wrapper {
        max-width: 650px;
        margin: 0 auto;
    }

    /* CARD ORIZZONTALE */
    .inline-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 6px 10px;
        margin-bottom: 5px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    /* CONTENUTO IN LINEA */
    .card-data {
        display: flex;
        align-items: center;
        gap: 8px; /* Spazio tra gli elementi */
        flex-wrap: nowrap;
        overflow: hidden;
    }

    .t-name { font-size: 13px; font-weight: 700; color: #ffffff; white-space: nowrap; }
    .t-bet { font-size: 13px; font-weight: 800; color: #58a6ff; white-space: nowrap; }
    .t-math { font-size: 11px; color: #8b949e; white-space: nowrap; }
    
    .val-neon { color: #39d353; font-weight: 700; }
    .stk-gold { color: #f1c40f; font-weight: 700; }

    /* ICONA AZIONE PICCOLA */
    .stButton > button {
        width: 28px !important;
        height: 28px !important;
        min-width: 28px !important;
        padding: 0 !important;
        border-radius: 4px !important;
        font-size: 14px !important;
        background-color: #21262d !important;
        border: 1px solid #30363d !important;
        color: white !important;
    }

    /* Icona GESTITO (Verde) */
    .stButton > button[disabled] {
        background-color: transparent !important;
        color: #39d353 !important;
        border: 1px solid #39d353 !important;
        opacity: 1 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- RENDERING ---
st.markdown('<div class="main-wrapper">', unsafe_allow_html=True)

# --- FUNZIONE PER GENERARE LA RIGA ---
def riga_match(id, squadre, giocata, quota, stake, valore, gestito=False):
    c_info, c_btn = st.columns([10, 1]) # Rapporto molto sbilanciato per tenere tutto a sinistra
    
    with c_info:
        # Tutto il testo viene generato in un unico blocco flex
        st.markdown(f"""
            <div class="inline-card">
                <div class="card-data">
                    <span class="t-name">⚽ {squadre}</span>
                    <span class="t-bet">{giocata} @{quota}</span>
                    <span class="t-math">
                        <span class="stk-gold">S:{stake}€</span> | 
                        <span class="val-neon">V:+{valore}%</span>
                    </span>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    with c_btn:
        if not gestito:
            st.button("＋", key=f"add_{id}")
        else:
            st.button("✔", key=f"chk_{id}", disabled=True)

# --- ESEMPI REALI ---
riga_match(1, "Juve-Inter", "OV 2.5", "1.95", "15.4", "5.2")
riga_match(2, "Bari-Palermo", "UN 2.5", "2.05", "11.7", "12.3", gestito=True)
riga_match(3, "Real-Barca", "OV 2.5", "1.85", "20.0", "4.1")

st.markdown('</div>', unsafe_allow_html=True)
