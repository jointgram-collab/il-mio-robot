import streamlit as st

# --- AGGIORNAMENTO CSS STEP 2: COMPACT CARDS ---
st.markdown("""
    <style>
    /* Contenitore per limitare la larghezza delle card al centro */
    .cards-wrapper {
        max-width: 550px;
        margin: 0 auto; /* Centra le card nella pagina */
    }

    .compact-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }

    /* RIGA 1: Match e Info temporali */
    .row-main {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
    }
    .match-name { font-size: 16px; font-weight: 700; color: #ffffff; }
    .match-meta { font-size: 11px; color: #8b949e; text-transform: uppercase; }

    /* RIGA 2: Dati scommessa compatti */
    .row-data {
        display: flex;
        align-items: center;
        gap: 15px;
        font-size: 13px;
    }
    .bet-highlight { color: #58a6ff; font-weight: 800; font-size: 15px; }
    .stat-box { display: flex; align-items: center; gap: 4px; }
    .label-min { color: #8b949e; font-size: 10px; text-transform: uppercase; }
    
    .val-neon { color: #39d353; font-weight: 700; }
    .stk-gold { color: #f1c40f; font-weight: 700; }

    /* Stile per i pulsanti Streamlit allineati */
    div[data-testid="stColumn"] {
        display: flex;
        align-items: center;
    }
    </style>
""", unsafe_allow_html=True)

# --- RENDERING CORPO CENTRALE ---
with st.container():
    # Usiamo un wrapper HTML per forzare la larghezza stretta
    st.markdown('<div class="cards-wrapper">', unsafe_allow_html=True)
    
    # ESEMPIO CARD 1
    st.markdown("""
        <div class="compact-card">
            <div class="row-main">
                <span class="match-name">⚽ Juventus - Inter</span>
                <span class="match-meta">Serie A | 20:45</span>
            </div>
            <div class="row-data">
                <span class="bet-highlight">OVER 2.5 @ 1.95</span>
                <div class="stat-box"><span class="label-min">STAKE:</span><span class="stk-gold">15.40€</span></div>
                <div class="stat-box"><span class="label-min">VAL:</span><span class="val-neon">+5.2%</span></div>
                <div class="stat-box" style="margin-left:auto;"><span class="label-min">🏛️</span><span style="color:white">Bet365</span></div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Pulsante compatto subito sotto
    c1, c2 = st.columns([3, 1])
    with c2:
        st.button("ADD", key="add_1", use_container_width=True)

    st.markdown("---") # Separatore visivo

    # ESEMPIO CARD 2 (Già in portafoglio)
    st.markdown("""
        <div class="compact-card" style="border-left: 3px solid #39d353; opacity: 0.8;">
            <div class="row-main">
                <span class="match-name">⚽ Bari - Palermo</span>
                <span class="match-meta">Serie B | 19:30</span>
            </div>
            <div class="row-data">
                <span class="bet-highlight">UNDER 2.5 @ 2.05</span>
                <div class="stat-box"><span class="label-min">STAKE:</span><span class="stk-gold">11.71€</span></div>
                <div class="stat-box"><span class="label-min">VAL:</span><span class="val-neon">+12.3%</span></div>
                <div class="stat-box" style="margin-left:auto;"><span style="color:white">William Hill</span></div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    with c2:
        st.button("✅ IN PORTAFOGLIO", key="add_2", disabled=True, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True) # Chiude cards-wrapper
