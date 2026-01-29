import streamlit as st

# --- AGGIORNAMENTO CSS STEP 2: ICON-ONLY ACTIONS ---
st.markdown("""
    <style>
    .main-content-wrapper {
        max-width: 600px;
        margin: 0 auto;
    }

    .compact-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .card-left { flex-grow: 1; }

    /* Riga 1: Squadre e Lega */
    .r1 { display: flex; justify-content: space-between; margin-bottom: 4px; }
    .teams { font-size: 14px; font-weight: 700; color: #ffffff; }
    .meta { font-size: 10px; color: #8b949e; }

    /* Riga 2: Dati tecnici */
    .r2 { display: flex; gap: 12px; align-items: center; }
    .bet { color: #58a6ff; font-weight: 800; font-size: 13px; }
    .stat { font-size: 11px; color: #ffffff; }
    .dim { color: #8b949e; font-size: 9px; margin-right: 2px; }

    /* Icona Azione */
    .action-col {
        margin-left: 15px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* Stile per i piccoli bottoni icona di Streamlit */
    .stButton>button {
        width: 35px !important;
        height: 35px !important;
        padding: 0 !important;
        border-radius: 6px !important;
        line-height: 1 !important;
        font-size: 18px !important;
        background-color: #21262d !important;
        border: 1px solid #30363d !important;
    }

    /* Pulsante già in lista (Verde) */
    .stButton>button[disabled] {
        background-color: rgba(57, 211, 83, 0.1) !important;
        color: #39d353 !important;
        border: 1px solid #39d353 !important;
        opacity: 1 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- RENDERING ---
st.markdown('<div class="main-content-wrapper">', unsafe_allow_html=True)

# ESEMPIO 1: DISPONIBILE
c_body, c_act = st.columns([5, 1])

with c_body:
    st.markdown("""
        <div class="compact-card">
            <div class="card-left">
                <div class="r1">
                    <span class="teams">⚽ Juventus - Inter</span>
                    <span class="meta">SERIE A | 20:45</span>
                </div>
                <div class="r2">
                    <span class="bet">OVER 2.5 @ 1.95</span>
                    <span class="stat"><span class="dim">STK:</span><span style="color:#f1c40f">15.4€</span></span>
                    <span class="stat"><span class="dim">VAL:</span><span style="color:#39d353">+5.2%</span></span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

with c_act:
    # Piccolo tasto "+" invece del pulsante enorme
    st.button("➕", key="add_icon_1", help="Aggiungi al portafoglio")

# ESEMPIO 2: GIÀ GESTITO
c_body2, c_act2 = st.columns([5, 1])

with c_body2:
    st.markdown("""
        <div class="compact-card" style="border-left: 3px solid #39d353;">
            <div class="card-left">
                <div class="r1">
                    <span class="teams">⚽ Bari - Palermo</span>
                    <span class="meta">SERIE B | 19:30</span>
                </div>
                <div class="r2">
                    <span class="bet">UNDER 2.5 @ 2.05</span>
                    <span class="stat"><span class="dim">STK:</span><span style="color:#f1c40f">11.7€</span></span>
                    <span class="stat"><span class="dim">VAL:</span><span style="color:#39d353">+12.3%</span></span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

with c_act2:
    # Icona check per indicare che è già presente
    st.button("✔️", key="add_icon_2", disabled=True)

st.markdown('</div>', unsafe_allow_html=True)
