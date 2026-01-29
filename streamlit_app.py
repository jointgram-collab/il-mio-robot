import streamlit as st

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="AI SNIPER V14.2", layout="wide")

# --- CSS STEP 1: SIDEBAR HIGH-CONTRAST ---
st.markdown("""
    <style>
    /* Sfondo Sidebar Scuro Profondo */
    [data-testid="stSidebar"] {
        background-color: #11141a;
        border-right: 1px solid #30363d;
    }

    /* Testi e Titoli: Bianco Puro e Grigio Chiaro */
    .sb-title {
        color: #ffffff !important; /* Bianco puro per i titoli */
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .label-text {
        color: #8b949e; /* Grigio chiaro leggibile per le etichette */
        font-size: 14px;
        font-weight: 500;
    }

    .value-text {
        color: #ffffff; /* Bianco per i numeri e i valori */
        font-weight: 700;
    }

    /* Styling degli Slider (Verde Neon e Bianco) */
    div[data-testid="stSlider"] [data-baseweb="slider"] {
        margin-top: 10px;
    }
    
    /* Il cerchietto dello slider deve essere Bianco */
    div[data-testid="stSlider"] [data-baseweb="slider"] [aria-valuenow] {
        background-color: #ffffff !important;
        border: 2px solid #39d353 !important;
    }

    /* API Metric Box */
    .api-container {
        background-color: #1c2128;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #444c56;
        margin-bottom: 20px;
    }
    
    .api-row { display: flex; justify-content: space-between; margin-bottom: 5px; }
    
    /* Barra di progresso verde */
    .api-bar-bg { background: #30363d; height: 8px; border-radius: 4px; overflow: hidden; margin-top: 10px; }
    .api-bar-fill { background: #39d353; height: 100%; border-radius: 4px; box-shadow: 0 0 8px #39d353; }

    /* Fix per le scritte standard di Streamlit in Sidebar */
    [data-testid="stWidgetLabel"] p {
        color: #ffffff !important; /* Forza i nomi degli slider in bianco */
        font-size: 15px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTENT ---
with st.sidebar:
    st.markdown('<div class="sb-title">🔥 API Status</div>', unsafe_allow_html=True)
    
    # Dati API
    residui = 440
    usati = 60
    percentuale = (usati / (residui + usati)) * 100
    
    st.markdown(f"""
        <div class="api-container">
            <div class="api-row">
                <span class="label-text">Residui:</span>
                <span class="value-text">{residui}</span>
            </div>
            <div class="api-row">
                <span class="label-text">Usati:</span>
                <span class="value-text">{usati}</span>
            </div>
            <div style="margin-top:15px; display:flex; justify-content:space-between;">
                <span class="label-text">Utilizzo</span>
                <span style="color:#39d353; font-weight:bold;">{int(percentuale)}%</span>
            </div>
            <div class="api-bar-bg"><div class="api-bar-fill" style="width: {percentuale}%;"></div></div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown('<div class="sb-title">📊 Parametri</div>', unsafe_allow_html=True)
    
    # Slider con contrasto migliorato
    st.slider("Budget (€)", 0, 1000, 500)
    st.slider("Kelly Criterion", 0.05, 0.50, 0.20)
    st.slider("Valore Minimo %", 0, 100, 14)

    st.markdown("---")
    st.markdown('<div class="sb-title">⚙️ Impostazioni</div>', unsafe_allow_html=True)

# --- CORPO CENTRALE ---
st.title("Test Leggibilità Sidebar")
st.write("Verifica se ora i testi bianchi sulla sidebar scura sono ben visibili.")
