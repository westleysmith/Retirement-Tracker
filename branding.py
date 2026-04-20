"""Pocket Check brand styling for the Retirement Tracker Streamlit app.

Colors and visual motifs mirror pocket-check-website's css/styles.css:
navy nav, green accents, white card surfaces, bold display type.
"""
from __future__ import annotations


# --- Color tokens (keep in sync with pocket-check-website/css/styles.css) ---
GREEN = "#2ecc71"
GREEN_DARK = "#27ae60"
NAVY = "#0f1f2e"
TEXT = "#1a1a2e"
MUTED = "#6b7280"
BORDER = "#e5e7eb"
BG = "#f9fafb"
WHITE = "#ffffff"

# Plotly palette derived from the brand
PLOT_PRIMARY = GREEN_DARK
PLOT_FILL = "rgba(46, 204, 113, 0.18)"
PLOT_ACCENT = GREEN
PLOT_NEUTRAL = "#94a3b8"


CUSTOM_CSS = f"""
<style>
/* ---- Base ---- */
html, body, [data-testid="stApp"] {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: {BG};
    color: {TEXT};
}}

/* ---- Headings ---- */
h1 {{
    color: {NAVY} !important;
    font-weight: 800 !important;
    letter-spacing: -0.01em;
}}
h2 {{
    color: {NAVY} !important;
    font-weight: 800 !important;
    border-bottom: 2px solid {GREEN};
    padding-bottom: 8px;
    display: inline-block;
}}
h3 {{
    color: {NAVY} !important;
    font-weight: 700 !important;
}}

/* ---- Primary button (green) ---- */
.stButton > button[kind="primary"] {{
    background: {GREEN} !important;
    color: {NAVY} !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 12px 20px !important;
    transition: all 0.2s !important;
}}
.stButton > button[kind="primary"]:hover {{
    background: {GREEN_DARK} !important;
    color: {WHITE} !important;
    box-shadow: 0 4px 12px rgba(46, 204, 113, 0.25);
}}

/* ---- Secondary buttons (outlined) ---- */
.stButton > button:not([kind="primary"]) {{
    background: {WHITE} !important;
    color: {NAVY} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}}
.stButton > button:not([kind="primary"]):hover {{
    background: {BG} !important;
    border-color: {GREEN} !important;
    color: {GREEN_DARK} !important;
}}

/* ---- Metric cards ---- */
[data-testid="stMetric"] {{
    background: {WHITE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 18px 22px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}}
[data-testid="stMetricLabel"] {{
    color: {MUTED} !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.08em !important;
}}
[data-testid="stMetricValue"] {{
    color: {NAVY} !important;
    font-weight: 800 !important;
}}

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {{
    background: {WHITE};
    border-right: 1px solid {BORDER};
}}
section[data-testid="stSidebar"] h2 {{
    border-bottom: none;
    font-size: 1.1rem !important;
}}
section[data-testid="stSidebar"] h3 {{
    font-size: 0.85rem !important;
    color: {MUTED} !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 700 !important;
    margin-top: 18px;
}}

/* ---- Links ---- */
a {{
    color: {GREEN_DARK} !important;
    text-decoration: none;
}}
a:hover {{
    color: {GREEN} !important;
    text-decoration: underline;
}}

/* ---- Data editor rounded ---- */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {{
    border-radius: 10px;
    overflow: hidden;
}}

/* ---- Hide Streamlit chrome ---- */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header[data-testid="stHeader"] {{background: transparent;}}

/* ---- Branded nav bar ---- */
.pc-nav {{
    background: {NAVY};
    color: {WHITE};
    padding: 14px 22px;
    border-radius: 10px;
    margin-bottom: 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 2px 12px rgba(15, 31, 46, 0.08);
}}
.pc-brand {{
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 700;
    font-size: 1.05rem;
    color: {WHITE};
}}
.pc-dot {{
    width: 10px;
    height: 10px;
    background: {GREEN};
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 0 4px rgba(46, 204, 113, 0.15);
}}
.pc-nav-badge {{
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: {GREEN};
    background: rgba(46, 204, 113, 0.12);
    border: 1px solid rgba(46, 204, 113, 0.28);
    padding: 4px 12px;
    border-radius: 100px;
}}

/* ---- Branded footer ---- */
.pc-footer {{
    background: {NAVY};
    color: rgba(255, 255, 255, 0.6);
    text-align: center;
    padding: 22px 20px;
    border-radius: 10px;
    margin-top: 40px;
    font-size: 0.85rem;
}}
.pc-footer a {{
    color: rgba(255, 255, 255, 0.85) !important;
}}
.pc-footer a:hover {{
    color: {GREEN} !important;
}}
.pc-footer .pc-foot-brand {{
    color: {WHITE};
    font-weight: 700;
}}
</style>
"""


NAV_HTML = f"""
<div class="pc-nav">
    <div class="pc-brand">
        <span class="pc-dot"></span>
        <span>Retirement Tracker</span>
    </div>
    <span class="pc-nav-badge">by Pocket Check</span>
</div>
"""


FOOTER_HTML = """
<div class="pc-footer">
    <div>
        Part of the <span class="pc-foot-brand">Pocket Check</span> family.
        &nbsp;·&nbsp;
        <a href="https://pocketcheck.app" target="_blank" rel="noopener">pocketcheck.app</a>
    </div>
</div>
"""
