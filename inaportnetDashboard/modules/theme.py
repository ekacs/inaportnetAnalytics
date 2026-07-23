"""
modules/theme.py
Pengaturan dan pengalih tema Tampilan (Light Mode / Dark Mode) untuk Streamlit.
"""

import streamlit as st
import modules.visualization as vis

LIGHT_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: #1e293b;
}

/* Light Theme Variables */
:root {
    --bg-main: #f8fafc;
    --bg-card: #ffffff;
    --text-color: #1e293b;
    --text-muted: #64748b;
    --border-color: #e2e8f0;
    --header-bg: linear-gradient(90deg, #0f2d52, #1a4a7a);
    --header-text: #ffffff;
    --metric-val: #1a4a7a;
    --info-bg: #eaf3fb;
    --info-border: #1a4a7a;
}

.stApp {
    background-color: var(--bg-main);
}

.section-header {
    background: var(--header-bg);
    color: var(--header-text);
    padding: 0.75rem 1.25rem;
    border-radius: 10px;
    font-size: 1.05rem;
    font-weight: 600;
    margin: 1.2rem 0 0.8rem;
    box-shadow: 0 2px 6px rgba(15, 45, 82, 0.1);
}

.info-box {
    background: var(--info-bg);
    border-left: 4px solid var(--info-border);
    border-radius: 0 8px 8px 0;
    padding: 0.85rem 1.1rem;
    font-size: 0.9rem;
    color: var(--text-color);
    margin-bottom: 1rem;
}

.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 1.1rem 1rem;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.metric-card .val   { font-size: 1.8rem; font-weight: 700; color: var(--metric-val); }
.metric-card .label { font-size: 0.83rem; color: var(--text-muted); margin-top: 2px; }
.metric-card .sub   { font-size: 0.75rem; color: #94a3b8; margin-top: 1px; }

.nav-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 1.2rem;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

footer{visibility:hidden;} #MainMenu{visibility:hidden;}
</style>
"""

DARK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: #f8fafc;
}

/* Dark Theme Variables */
:root {
    --bg-main: #0f172a;
    --bg-card: #1e293b;
    --text-color: #f8fafc;
    --text-muted: #94a3b8;
    --border-color: #334155;
    --header-bg: linear-gradient(90deg, #1e3a8a, #3b82f6);
    --header-text: #ffffff;
    --metric-val: #38bdf8;
    --info-bg: #1e293b;
    --info-border: #38bdf8;
}

.stApp {
    background-color: var(--bg-main) !important;
    color: var(--text-color) !important;
}

[data-testid="stSidebar"] {
    background-color: #1e293b !important;
    border-right: 1px solid #334155 !important;
}

[data-testid="stSidebar"] * {
    color: #f8fafc !important;
}

.section-header {
    background: var(--header-bg);
    color: var(--header-text);
    padding: 0.75rem 1.25rem;
    border-radius: 10px;
    font-size: 1.05rem;
    font-weight: 600;
    margin: 1.2rem 0 0.8rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.info-box {
    background: var(--info-bg);
    border-left: 4px solid var(--info-border);
    border-radius: 0 8px 8px 0;
    padding: 0.85rem 1.1rem;
    font-size: 0.9rem;
    color: #f8fafc;
    margin-bottom: 1rem;
}

.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 1.1rem 1rem;
    text-align: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.25);
}
.metric-card .val   { font-size: 1.8rem; font-weight: 700; color: var(--metric-val); }
.metric-card .label { font-size: 0.83rem; color: var(--text-muted); margin-top: 2px; }
.metric-card .sub   { font-size: 0.75rem; color: #64748b; margin-top: 1px; }

.nav-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 1.2rem;
    text-align: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.25);
}

footer{visibility:hidden;} #MainMenu{visibility:hidden;}
</style>
"""


def render_theme_selector():
    """
    Renders standard theme selector in sidebar and applies CSS & Plotly theme.
    Returns current active theme ("light" or "dark").
    """
    if "theme" not in st.session_state:
        st.session_state["theme"] = "light"

    current = st.session_state["theme"]
    idx = 0 if current == "light" else 1

    st.sidebar.markdown("**🎨 Tema Tampilan**")
    selected = st.sidebar.radio(
        "Pilih Tema",
        options=["☀️ Light Mode", "🌙 Dark Mode"],
        index=idx,
        horizontal=True,
        label_visibility="collapsed"
    )

    new_theme = "light" if "Light" in selected else "dark"
    if new_theme != st.session_state["theme"]:
        st.session_state["theme"] = new_theme
        st.rerun()

    # Apply CSS & Plotly Template
    if new_theme == "dark":
        st.markdown(DARK_CSS, unsafe_allow_html=True)
        vis.PLOTLY_TEMPLATE = "plotly_dark"
    else:
        st.markdown(LIGHT_CSS, unsafe_allow_html=True)
        vis.PLOTLY_TEMPLATE = "plotly_white"

    return new_theme
