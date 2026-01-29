import streamlit as st

# --- AGGIORNAMENTO CSS STEP 2: EMBEDDED BUTTONS ---
st.markdown("""
    <style>
    .main-content-wrapper {
        max-width: 550px;
        margin: 0 auto;
    }

    /* Container relativo per permettere al pulsante di sovrapporsi */
    .card-container {
        position: relative;
        margin-bottom: 10px;
    }

    .compact-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 10px 14px;
        /* Lasciamo spazio a destra per l'icona */
        padding-right: 50px; 
    }

    .r1 { display: flex; justify-content: space-between; margin-bottom: 4px; }
    .teams { font-size: 14px; font-weight: 700; color: #ffffff; }
    .meta { font-size: 10px; color: #8b949e; }

    .r2 { display: flex; gap: 12px; align-items: center; }
    .bet { color: #58a6ff; font-weight: 800; font-size: 13px; }
    .stat { font-size: 11px; color: #ffffff; }
    .dim { color: #8b949e; font-size: 9px; margin-right: 2px; }

    /* POSIZIONAMENTO PULSANTE DENTRO LA CARD */
    .button-overlay {
        position: absolute;
        top: 12px;
        right: 12px;
        z-index: 10;
    }

    /* Reset stile pulsante Streamlit per farlo sembrare un'icona */
    .button-overlay .stButton>button {
        width: 30px !important;
        height: 30px !important;
        padding: 0 !important;
        border-radius: 4px !important;
        background-color: #21262d !important;
        border: 1px solid #444c56 !important;
        color: #ffffff !important;
        font-size: 14px !important;
        line-height: 1 !important;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .button-overlay .stButton>button:hover {
        border-color: #58a6ff !important;
        color: #58a6ff !important;
    }

    /* Icona GESTITO (Verde) */
    .button-overlay .stButton>button[disabled] {
        background-color: transparent !important;
        color: #39d353 !important;
        border: 1px solid #39d353 !important;
        opacity: 1 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- RENDERING ---
st.markdown('<div class="main-content-wrapper">', unsafe_allow_html=True)

# ESEMPIO 1: MATCH DISPONIBILE
st.markdown('<div class="card-container">', unsafe_allow_html=True)
# Sfondo della card
st.markdown("""
    <div class="compact-card">
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
""", unsafe_allow_html=True)
# Pulsante sovrapposto
st.markdown('<div class="button-overlay">', unsafe_allow_html=True)
st.button("＋", key="add_inner_1")
st.markdown('</div></div>', unsafe_allow_html=True)

# ESEMPIO 2: MATCH GIÀ GESTITO
st.markdown('<div class="card-container">', unsafe_allow_html=True)
st.markdown("""
    <div class="compact-card" style="border-left: 3px solid #39d353;">
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
""", unsafe_allow_html=True)
st.markdown('<div class="button-overlay">', unsafe_allow_html=True)
st.button("✔", key="add_inner_2", disabled=True)
st.markdown('</div></div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
