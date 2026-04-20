"""Pocket Check brand styling for the Retirement Tracker Streamlit app.

Theme behavior:
- The app automatically follows the OS / browser theme via the
  `prefers-color-scheme` CSS media query. Windows dark → app dark; Windows
  light → app light. No UI toggle needed in the app itself.
- For a manual override, the user can use Streamlit's built-in menu:
  click the ⋮ icon top-right → Settings → Theme → Light/Dark/Custom.
  Streamlit's picker retints Streamlit's own widgets; our CSS here retints
  the rest via `prefers-color-scheme`, so the two align for users whose
  OS matches their Streamlit choice (the common case).

Colors mirror pocket-check-website/css/styles.css: navy nav, green accents,
white surfaces in light mode / deep-navy surfaces in dark mode.
"""
from __future__ import annotations


# --- Brand constants (same across modes) ---
GREEN = "#2ecc71"
GREEN_DARK = "#27ae60"
NAVY = "#0f1f2e"


LIGHT_TOKENS = {
    "bg":      "#f9fafb",
    "surface": "#ffffff",
    "text":    "#1a1a2e",
    "muted":   "#6b7280",
    "border":  "#e5e7eb",
    "heading": NAVY,
}

DARK_TOKENS = {
    "bg":      "#0a1420",
    "surface": "#142538",
    "text":    "#e8eef5",
    "muted":   "#8fa3b8",
    "border":  "#1f3449",
    "heading": "#e8eef5",
}


def plot_tokens() -> dict:
    """Plotly colors tuned to be readable on both light and dark surfaces.
    We can't detect the OS theme from Python, so we pick neutral grays for
    text/grid that stay legible either way. Data colors use the brand."""
    return {
        "font_color":  "#6b7280",
        "grid":        "rgba(128, 128, 128, 0.18)",
        "plot_bg":     "rgba(0, 0, 0, 0)",
        "paper_bg":    "rgba(0, 0, 0, 0)",
        "primary":     GREEN_DARK,
        "accent":      GREEN,
        "fill":        "rgba(46, 204, 113, 0.22)",
        "navy":        NAVY,
    }


def _vars_block(tokens: dict) -> str:
    return f"""
    --pc-bg: {tokens['bg']};
    --pc-surface: {tokens['surface']};
    --pc-text: {tokens['text']};
    --pc-muted: {tokens['muted']};
    --pc-border: {tokens['border']};
    --pc-heading: {tokens['heading']};
"""


def build_css() -> str:
    """Full theme CSS. Uses prefers-color-scheme to follow OS theme."""
    return f"""
<style>
:root {{ {_vars_block(LIGHT_TOKENS)} }}

@media (prefers-color-scheme: dark) {{
    :root {{ {_vars_block(DARK_TOKENS)} }}
}}

/* ---- Base surface (body + app container) ---- */
[data-testid="stApp"], body {{
    background-color: var(--pc-bg) !important;
    color: var(--pc-text) !important;
}}

/* ---- Streamlit's top header bar (where the ⋮ menu lives) ---- */
header[data-testid="stHeader"] {{
    background-color: var(--pc-bg) !important;
    border-bottom: 1px solid var(--pc-border);
}}
header[data-testid="stHeader"] *,
header[data-testid="stHeader"] button,
header[data-testid="stHeader"] svg {{
    color: var(--pc-text) !important;
    fill: var(--pc-text);
}}

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {{
    background-color: var(--pc-surface) !important;
    border-right: 1px solid var(--pc-border);
}}
section[data-testid="stSidebar"] * {{
    color: var(--pc-text);
}}

/* ---- Text / markdown / captions ---- */
[data-testid="stMarkdownContainer"],
[data-testid="stApp"] p,
[data-testid="stApp"] label,
[data-testid="stApp"] li {{
    color: var(--pc-text);
}}
[data-testid="stCaptionContainer"], .stCaption,
[data-testid="stMarkdownContainer"] small {{
    color: var(--pc-muted) !important;
}}

/* ---- Inputs (text, number, textarea, date) ---- */
.stTextInput input, .stNumberInput input, .stTextArea textarea,
.stDateInput input,
[data-baseweb="input"] input, [data-baseweb="input"] textarea,
[data-baseweb="base-input"] input, [data-baseweb="base-input"] textarea {{
    background-color: var(--pc-surface) !important;
    color: var(--pc-text) !important;
    border-color: var(--pc-border) !important;
    -webkit-text-fill-color: var(--pc-text) !important;
}}
.stNumberInput [data-baseweb="input-container"],
.stTextInput [data-baseweb="input-container"] {{
    background-color: var(--pc-surface) !important;
    border-color: var(--pc-border) !important;
}}
.stNumberInput button {{
    background-color: var(--pc-surface) !important;
    color: var(--pc-text) !important;
    border-color: var(--pc-border) !important;
}}

/* ---- Selectbox ---- */
.stSelectbox [data-baseweb="select"] > div,
[data-baseweb="select"] > div {{
    background-color: var(--pc-surface) !important;
    color: var(--pc-text) !important;
    border-color: var(--pc-border) !important;
}}
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="popover"] ul,
[data-baseweb="menu"] {{
    background-color: var(--pc-surface) !important;
    color: var(--pc-text) !important;
    border-color: var(--pc-border) !important;
}}
[data-baseweb="menu"] li,
[data-baseweb="popover"] li {{
    background-color: var(--pc-surface) !important;
    color: var(--pc-text) !important;
}}
[data-baseweb="menu"] li:hover,
[data-baseweb="popover"] li:hover {{
    background-color: var(--pc-bg) !important;
}}

/* ---- Radios, sliders ---- */
.stRadio label, .stRadio div {{
    color: var(--pc-text);
}}
.stSlider [data-baseweb="slider"] span,
.stSlider [data-baseweb="slider"] div {{
    color: var(--pc-text);
}}

/* ---- Expander ---- */
[data-testid="stExpander"] {{
    background-color: var(--pc-surface) !important;
    border: 1px solid var(--pc-border) !important;
    border-radius: 10px;
}}
[data-testid="stExpander"] summary, [data-testid="stExpander"] details > summary {{
    color: var(--pc-text) !important;
}}
[data-testid="stExpander"] div, [data-testid="stExpander"] p,
[data-testid="stExpander"] li {{
    color: var(--pc-text);
}}

/* ---- Data editor / table surfaces ---- */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {{
    background-color: var(--pc-surface) !important;
    border-radius: 10px;
    overflow: hidden;
}}

/* ---- Tooltips, alerts, dividers ---- */
[data-testid="stTooltipIcon"] {{ color: var(--pc-muted) !important; }}
[data-testid="stAlert"] {{
    background-color: var(--pc-surface) !important;
    color: var(--pc-text) !important;
    border-color: var(--pc-border) !important;
}}
hr {{ border-color: var(--pc-border) !important; }}

/* ---- Base font ---- */
html, body, [data-testid="stApp"] {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}}

/* ---- Headings ---- */
h1 {{
    color: var(--pc-heading) !important;
    font-weight: 800 !important;
    letter-spacing: -0.01em;
}}
h2 {{
    color: var(--pc-heading) !important;
    font-weight: 800 !important;
    border-bottom: 2px solid {GREEN};
    padding-bottom: 8px;
    display: inline-block;
}}
h3 {{
    color: var(--pc-heading) !important;
    font-weight: 700 !important;
}}

/* ---- Primary button (always green — readable on both themes) ---- */
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
    color: #ffffff !important;
    box-shadow: 0 4px 12px rgba(46, 204, 113, 0.25);
}}

/* ---- Secondary buttons (outlined) ---- */
.stButton > button:not([kind="primary"]) {{
    background: var(--pc-surface) !important;
    color: var(--pc-text) !important;
    border: 1px solid var(--pc-border) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}}
.stButton > button:not([kind="primary"]):hover {{
    border-color: {GREEN} !important;
    color: {GREEN_DARK} !important;
}}

/* ---- Metric cards ---- */
[data-testid="stMetric"] {{
    background: var(--pc-surface);
    border: 1px solid var(--pc-border);
    border-radius: 10px;
    padding: 18px 22px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}}
[data-testid="stMetricLabel"] {{
    color: var(--pc-muted) !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.08em !important;
}}
[data-testid="stMetricValue"] {{
    color: var(--pc-heading) !important;
    font-weight: 800 !important;
}}

/* ---- Sidebar sub-headings ---- */
section[data-testid="stSidebar"] h2 {{
    border-bottom: none;
    font-size: 1.1rem !important;
}}
section[data-testid="stSidebar"] h3 {{
    font-size: 0.85rem !important;
    color: var(--pc-muted) !important;
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

/* ---- Branded nav bar (always navy+green — brand-consistent) ---- */
.pc-nav {{
    background: {NAVY};
    color: #ffffff;
    padding: 14px 22px;
    border-radius: 10px;
    margin-bottom: 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 2px 12px rgba(15, 31, 46, 0.08);
}}
.pc-nav, .pc-nav *, .pc-brand, .pc-brand * {{
    color: #ffffff !important;
}}
.pc-brand {{
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 700;
    font-size: 1.05rem;
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
    color: {GREEN} !important;
    background: rgba(46, 204, 113, 0.12);
    border: 1px solid rgba(46, 204, 113, 0.28);
    padding: 4px 12px;
    border-radius: 100px;
}}

/* ---- Branded footer (always navy — brand-consistent) ---- */
.pc-footer {{
    background: {NAVY};
    text-align: center;
    padding: 22px 20px;
    border-radius: 10px;
    margin-top: 40px;
    font-size: 0.85rem;
}}
.pc-footer, .pc-footer * {{
    color: rgba(255, 255, 255, 0.75) !important;
}}
.pc-footer a {{
    color: rgba(255, 255, 255, 0.9) !important;
}}
.pc-footer a:hover {{
    color: {GREEN} !important;
}}
.pc-footer .pc-foot-brand {{
    color: #ffffff !important;
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
