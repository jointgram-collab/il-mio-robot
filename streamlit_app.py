import streamlit as st

# --- CONFIGURAZIONE CSS STEP 2 (Aggiungere al CSS precedente) ---
st.markdown("""
    <style>
    /* 1. Sfondo Area Centrale */
    .stApp { background-color: #0b0e14; }

    /* 2. Container Card Scanner */
    .scanner-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        transition: transform 0.2s, border-color 0.2s;
    }
    .scanner-card:hover {
        border-color: #58a6ff;
        transform: translateY(-2px);
    }

    /* 3. Testi Interni Card */
    .match-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .teams { font-size: 20px; font-weight: 800; color: #ffffff; }
    .league-badge { 
        background-color: #21262d; 
        color: #8b949e; 
        padding: 4px 10px; 
        border-radius: 6px; 
        font-size: 12px; 
        font-weight: 600;
    }

    .bet-type { 
        font-size: 24px; 
        font-weight: 900; 
        color: #58a6ff; 
        margin-bottom: 15px;
    }

    /* 4. Riga Dati (Stake, Valore, BK) */
    .data-row {
        display: flex;
        gap: 25px;
        padding-top: 15px;
        border-top: 1px solid #30363d;
        font-size: 14px;
    }
    .data-label { color: #8b949e; margin-right: 5px; }
    .val-green { color: #39d353; font-weight: 800; }
    .stk-yellow { color: #f1c40f; font-weight: 800; }
    .bk-white { color: #ffffff; font-weight: 700; }

    /* 5. Pulsante "IN PORTAFOGLIO" (Stile Success) */
    .stButton>button[disabled] {
        background-color: #238636 !important;
        color: white !important;
        border: none !important;
        opacity: 1 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- CORPO CENTRALE ---
t1, t2, t3 = st.tabs(["🔍 SCANNER", "💼 PORTAFOGLIO", "📊 FISCALE"])

with t1:
    # Esempio di come apparirà una card nello scanner
    st.markdown("""
        <div class="scanner-card">
            <div class="match-header">
                <span class="teams">Juventus - Inter</span>
                <span class="league-badge">🇮🇹 SERIE A | 20:45</span>
            </div>
            <div class="bet-type">OVER 2.5 @ 1.95</div>
            <div class="data-row">
                <span><span class="data-label">💰 STAKE:</span><span class="stk-highlight stk-yellow">15.40€</span></span>
                <span><span class="data-label">🔥 VALORE:</span><span class="val-green">+5.2%</span></span>
                <span><span class="data-label">🏛️ BOOK:</span><span class="bk-white">Bet365</span></span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Pulsante Streamlit sincronizzato con la card
    c1, c2 = st.columns([4, 1])
    with c2:
        if st.button("AGGIUNGI", key="btn_test"):
            st.toast("Match aggiunto!")

    # Esempio di match già in portafoglio
    st.markdown("""
        <div class="scanner-card" style="border-left: 4px solid #238636;">
            <div class="match-header">
                <span class="teams">Real Madrid - Barcelona</span>
                <span class="league-badge">🇪🇸 LA LIGA | 21:00</span>
            </div>
            <div class="bet-type">UNDER 2.5 @ 2.10</div>
            <div class="data-row">
                <span><span class="data-label">💰 STAKE:</span><span class="stk-yellow">12.80€</span></span>
                <span><span class="data-label">🔥 VALORE:</span><span class="val-green">+4.8%</span></span>
                <span><span class="data-label">🏛️ BOOK:</span><span class="bk-white">William Hill</span></span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    with c2:
        st.button("✅ IN PORTAFOGLIO", key="btn_disabled", disabled=True)

# --- FINE STEP 2 ---
