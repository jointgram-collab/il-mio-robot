import streamlit as st

# --- AGGIORNAMENTO CSS STEP 2: SIDE-BY-SIDE LAYOUT ---
st.markdown("""
    <style>
    /* Wrapper per centrare e stringere il contenuto */
    .main-content-wrapper {
        max-width: 700px;
        margin: 0 auto;
    }

    .compact-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 10px 14px;
        height: 85px; /* Altezza fissa per allineamento perfetto col pulsante */
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    /* Riga 1: Match */
    .card-row-top {
        display: flex;
        justify-content: space-between;
        margin-bottom: 4px;
    }
    .text-teams { font-size: 15px; font-weight: 700; color: #ffffff; }
    .text-meta { font-size: 10px; color: #8b949e; }

    /* Riga 2: Dati */
    .card-row-bottom {
        display: flex;
        gap: 12px;
        align-items: center;
    }
    .text-bet { color: #58a6ff; font-weight: 800; font-size: 14px; }
    .text-stat { font-size: 12px; color: #ffffff; font-weight: 600; }
    .label-dim { color: #8b949e; font-size: 9px; margin-right: 3px; }

    /* Colori neon */
    .neon-green { color: #39d353; }
    .neon-yellow { color: #f1c40f; }

    /* Forza l'allineamento verticale del pulsante Streamlit */
    div[data-testid="stColumn"] > div {
        display: flex;
        align-items: center;
        height: 100%;
    }
    
    /* Stile pulsante ADD */
    .stButton>button {
        height: 85px !important; /* Stessa altezza della card */
        border-radius: 8px !important;
        background-color: #21262d !important;
        color: #ffffff !important;
        border: 1px solid #30363d !important;
    }
    
    /* Stile pulsante GESTITO (In Portafoglio) */
    .stButton>button[disabled] {
        background-color: rgba(57, 211, 83, 0.15) !important;
        color: #39d353 !important;
        border: 1px solid #39d353 !important;
        opacity: 1 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- RENDERING ---
st.markdown('<div class="main-content-wrapper">', unsafe_allow_html=True)

# CARD 1: DISPONIBILE
col_card, col_btn = st.columns([3.5, 1])

with col_card:
    st.markdown("""
        <div class="compact-card">
            <div class="card-row-top">
                <span class="text-teams">⚽ Juventus - Inter</span>
                <span class="text-meta">IT SERIE A | 20:45</span>
            </div>
            <div class="card-row-bottom">
                <span class="text-bet">OVER 2.5 @ 1.95</span>
                <span class="text-stat"><span class="label-dim">STAKE:</span><span class="neon-yellow">15.40€</span></span>
                <span class="text-stat"><span class="label-dim">VAL:</span><span class="neon-green">+5.2%</span></span>
            </div>
        </div>
    """, unsafe_allow_html=True)

with col_btn:
    st.button("ADD", key="add_1", use_container_width=True)

st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

# CARD 2: GESTITA
col_card2, col_btn2 = st.columns([3.5, 1])

with col_card2:
    st.markdown("""
        <div class="compact-card" style="border-left: 3px solid #39d353;">
            <div class="card-row-top">
                <span class="text-teams">⚽ Bari - Palermo</span>
                <span class="text-meta">IT SERIE B | 19:30</span>
            </div>
            <div class="card-row-bottom">
                <span class="text-bet">UNDER 2.5 @ 2.05</span>
                <span class="text-stat"><span class="label-dim">STAKE:</span><span class="neon-yellow">11.71€</span></span>
                <span class="text-stat"><span class="label-dim">VAL:</span><span class="neon-green">+12.3%</span></span>
            </div>
        </div>
    """, unsafe_allow_html=True)

with col_btn2:
    st.button("✅ GESTITO", key="add_2", disabled=True, use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)
