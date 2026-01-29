import streamlit as st

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="AI SNIPER V14.2", layout="wide")

# --- CSS STEP 1: SIDEBAR & SLIDERS ---
st.markdown("""
    <style>
    /* 1. Sfondo Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1a1d26;
        border-right: 1px solid #2d313d;
    }

    /* 2. Titoli e Testi Sidebar */
    .sb-title {
        color: #ffffff;
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    /* 3. Styling degli Slider (Verde e Bianco) */
    div[data-testid="stSlider"] > div [data-baseweb="slider"] > div:first-child {
        background: linear-gradient(to right, #39d353 0%, #39d353 var(--progress), #30363d var(--progress), #30363d 100%);
    }
    div[data-testid="stSlider"] [data-baseweb="slider"] [aria-valuenow] {
        background-color: #ffffff;
        border: 2px solid #39d353;
        box-shadow: 0 0 10px rgba(57, 211, 83, 0.4);
    }
    
    /* Colore dei numeri sopra lo slider */
    div[data-testid="stWidgetLabel"] p {
        color: #e1e1e1;
        font-weight: 600;
    }

    /* 4. API Metric Box */
    .api-container {
        background-color: #11141a;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #30363d;
        margin-bottom: 20px;
    }
    .api-row { display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 5px; }
    .api-val { font-weight: 700; color: #ffffff; }
    .api-bar-bg { background: #30363d; height: 6px; border-radius: 3px; overflow: hidden; }
    .api-bar-fill { background: #39d353; height: 100%; border-radius: 3px; }

    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTENT ---
with st.sidebar:
    # Header API Status
    st.markdown('<div class="sb-title">📶 API Status</div>', unsafe_allow_html=True)
    
    # Box API come da immagine
    residui = 440
    usati = 60
    percentuale = (usati / (residui + usati)) * 100
    
    st.markdown(f"""
        <div class="api-container">
            <div class="api-row"><span>Residui: {residui}</span><span class="api-val">{residui}</span></div>
            <div class="api-row"><span>Usati</span><span class="api-val">Fiinett: {usati}</span></div>
            <div style="margin-top:10px; margin-bottom:5px; font-weight:700;">Usati <span style="float:right;">{usati}</span></div>
            <div class="api-bar-bg"><div class="api-bar-fill" style="width: {percentuale}%;"></div></div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Header Strategia
    st.markdown('<div class="sb-title">📊 Parametri Strategia</div>', unsafe_allow_html=True)
    
    # Gli slider ora prendono il CSS sopra per diventare verdi e bianchi
    budget = st.slider("Budget (€)", 0, 1000, 440)
    kelly = st.slider("Kelly", 0, 100, 50)
    kelly2 = st.slider("Kelly ", 0, 100, 73) # Secondo slider come nell'immagine
    valore_min = st.slider("Valore Min %", 0, 100, 14)

    st.markdown("---")
    
    # Sezione Impostazioni
    st.markdown('<div class="sb-title">⚙️ Impostazioni</div>', unsafe_allow_html=True)

# --- CORPO CENTRALE (VUOTO PER ORA) ---
st.write("Configurazione Sidebar completata. Controlla se i colori e gli slider corrispondono a quelli della tua immagine.")
