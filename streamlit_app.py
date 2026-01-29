import streamlit as st

# --- CSS DEFINITIVO PER RIGHE SINGOLE E COMPATTE ---
st.markdown("""
    <style>
    /* Container principale stretto */
    .main-wrapper {
        max-width: 500px;
        margin: 0 auto;
    }

    /* LA CARD: Un unico blocco orizzontale */
    .single-line-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 8px 12px;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        justify-content: space-between; /* Spinge il testo a sx e il tasto a dx */
    }

    /* Area Testo */
    .card-content {
        display: flex;
        flex-direction: column;
        gap: 2px;
        overflow: hidden; /* Evita che il testo lunghi rompa la riga */
    }

    .t-row1 { font-size: 13px; font-weight: 700; color: #ffffff; white-space: nowrap; }
    .t-row2 { font-size: 11px; display: flex; gap: 10px; align-items: center; }
    
    .q-blue { color: #58a6ff; font-weight: 800; }
    .s-yellow { color: #f1c40f; }
    .v-green { color: #39d353; font-weight: 700; }
    .meta-gray { color: #8b949e; font-size: 9px; }

    /* Area Pulsante: Forza il posizionamento a destra */
    .action-area {
        min-width: 40px;
        display: flex;
        justify-content: flex-end;
    }

    /* FIX PULSANTE STREAMLIT */
    .stButton > button {
        width: 32px !important;
        height: 32px !important;
        padding: 0 !important;
        border-radius: 6px !important;
        background-color: #21262d !important;
        border: 1px solid #30363d !important;
        color: #ffffff !important;
        font-size: 16px !important;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .stButton > button[disabled] {
        background-color: rgba(57, 211, 83, 0.1) !important;
        color: #39d353 !important;
        border: 1px solid #39d353 !important;
        opacity: 1 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- RENDERING ---
st.markdown('<div class="main-wrapper">', unsafe_allow_html=True)

# --- ESEMPIO 1: DISPONIBILE ---
# Usiamo un layout a 2 colonne reali di Streamlit ma con CSS per bloccare il wrap
c_txt, c_btn = st.columns([5, 1])

with c_txt:
    st.markdown("""
        <div class="card-content">
            <div class="t-row1">⚽ Juve - Inter <span class="meta-gray">| 20:45</span></div>
            <div class="t-row2">
                <span class="q-blue">OV 2.5 @1.95</span>
                <span class="s-yellow">S: 15€</span>
                <span class="v-green">+5%</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

with c_btn:
    st.button("＋", key="m1")

# --- ESEMPIO 2: GESTITO ---
c_txt2, c_btn2 = st.columns([5, 1])

with c_txt2:
    st.markdown("""
        <div class="card-content" style="border-left: 2px solid #39d353; padding-left: 8px;">
            <div class="t-row1">⚽ Bari - Palermo <span class="meta-gray">| 19:30</span></div>
            <div class="t-row2">
                <span class="q-blue">UN 2.5 @2.05</span>
                <span class="s-yellow">S: 11€</span>
                <span class="v-green">+12%</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

with c_btn2:
    st.button("✔", key="m2", disabled=True)

st.markdown('</div>', unsafe_allow_html=True)
