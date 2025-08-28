# accessibility.py
import streamlit as st
import plotly.graph_objects as go

def add_accessibility_features():
    """Přidá accessibility features do aplikace"""
    
    # Custom CSS pro lepší accessibility
    st.markdown("""
    <style>
    /* Vylepšení kontrastů */
    .metric-container {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 10px;
        margin: 5px;
    }
    
    /* Lepší focus indikátory */
    button:focus, .stSelectbox > div > div:focus {
        outline: 3px solid #4CAF50 !important;
        outline-offset: 2px !important;
    }
    
    /* Vyšší kontrast pro texty */
    .stMarkdown p, .stMarkdown li {
        color: #1f2937 !important;
    }
    
    /* Screen reader friendly */
    .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
    }
    
    /* High contrast mode support */
    @media (prefers-contrast: high) {
        .stApp {
            background-color: white !important;
            color: black !important;
        }
        
        .metric-container {
            border: 2px solid black !important;
        }
    }
    
    /* Reduced motion support */
    @media (prefers-reduced-motion: reduce) {
        * {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
    
    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
        .metric-container {
            background-color: #374151;
            border-color: #6B7280;
        }
    }
    </style>
    """, unsafe_allow_html=True)

def make_chart_accessible(fig, title, description, data_summary=""):
    """Přidá accessibility features do plotly grafů"""
    
    # Přidání alt textu a ARIA labelu
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'color': '#1f2937'}
        },
        # Lepší barvy pro colorblind uživatele
        colorway=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b'],
    )
    
    # Přidání textového popisu pro screen readery
    if description:
        st.markdown(f"""
        <div class="chart-description" role="img" aria-label="{title}">
            <span class="sr-only">Graf: {title}. {description}</span>
            {data_summary}
        </div>
        """, unsafe_allow_html=True)
    
    return fig

def create_accessible_metric_card(label, value, delta=None, help_text=""):
    """Vytvoří accessibility-friendly metric card"""
    
    delta_text = f" ({delta})" if delta else ""
    aria_label = f"{label}: {value}{delta_text}"
    
    st.markdown(f"""
    <div class="metric-container" role="region" aria-label="{aria_label}">
        <h3 style="margin:0; font-size:14px; color:#6B7280;">{label}</h3>
        <div style="font-size:24px; font-weight:bold; color:#1f2937;" aria-live="polite">
            {value}
        </div>
        {f'<div style="font-size:12px; color:#059669;">{delta}</div>' if delta else ''}
        {f'<div class="sr-only">{help_text}</div>' if help_text else ''}
    </div>
    """, unsafe_allow_html=True)

def add_keyboard_navigation_hints():
    """Přidá hints pro keyboard navigation"""
    
    with st.expander("♿ Accessibility nápověda"):
        st.markdown("""
        **Navigace pomocí klávesnice:**
        - `Tab` / `Shift+Tab` - přepínání mezi prvky
        - `Enter` / `Space` - aktivace tlačítek
        - `Escape` - zavření dialogů
        - `Arrow keys` - navigace v grafech (pokud je podporována)
        
        **Screen reader podpora:**
        - Všechny grafy mají textové alternativy
        - Metriky jsou označeny pomocí ARIA labelů
        - Struktura je sémanticky správná
        
        **Kontrasty:**
        - Aplikace respektuje systémové nastavení high contrast
        - Podporuje dark/light mode
        - Barvy jsou vybírány s ohledem na barvoslepost
        """)

def add_language_support():
    """Přidá základní podporu pro více jazyků"""
    
    # Detekce jazyka z browseru (můžete rozšířit)
    lang = st.query_params.get("lang", "cs")
    
    if lang == "en":
        return {
            "title": "Your Personal Emotional Profile",
            "download_pdf": "Download Personal PDF Report",
            "insights": "Personal Insights",
            "privacy": "Privacy Protection: This report is intended only for you.",
            "help_text": """
**How to read emotional space:**
- **X-axis = Valence** (negative ↔ positive)
- **Z-axis = Arousal** (low ↔ high)
- **Y-axis = Dominance** (low ↔ high control)
            """
        }
    else:  # Czech (default)
        return {
            "title": "Tvůj osobní emoční profil",
            "download_pdf": "Stáhnout osobní PDF report", 
            "insights": "Osobní insighty",
            "privacy": "Ochrana soukromí: Tento report je určen pouze pro tebe.",
            "help_text": """
**Jak číst prostor emocí:**
- **Osa X = Valence** (negativní ↔ pozitivní)
- **Osa Z = Arousal** (nízký ↔ vysoký)
- **Osa Y = Dominance** (nízká ↔ vysoká kontrola)
            """
        }
