"""Pocket Check brand styling for the Retirement Tracker Streamlit app.

Colors and visual motifs mirror pocket-check-website's css/styles.css:
navy nav, green accents, white surfaces in light mode / deep-navy surfaces in
dark mode.

The theme is selectable at runtime via `build_css(mode)` where `mode` is one
of "Light", "Dark", or "Auto" (system preference).
"""
from __future__ import annotations


# --- Brand constants (same across modes) ---
GREEN = "#2ecc71"
GREEN_DARK = "#27ae60"
NAVY = "#0f1f2e"


# --- Light-mode surface tokens (from pocket-check-website) ---
LIGHT_TOKENS = {
    "bg":      "#f9fafb",
    "surface": "#ffffff",
    "text":    "#1a1a2e",
    "muted":   "#6b7280",
    "border":  "#e5e7eb",
    "heading": NAVY,
    "grid":    "rgba(0, 0, 0, 0.08)",
}

# --- Dark-mode surface tokens (derived, same hue family as NAVY) ---
DARK_TOKENS = {
    "bg":      "#0a1420",
    "surface": "#142538",
    "text":    "#e8eef5",
    "muted":   "#8fa3b8",
    "border":  "#1f3449",
    "heading": "#e8eef5",
    "grid":    "rgba(255, 255, 255, 0.08)",
}


def plot_tokens(mode: str) -> dict:
    """Return theme-appropriate Plotly colors for `mode` in {Light, Dark, Auto}."""
    if mode == "Dark":
        t = DARK_TOKENS
    else:
        t = LIGHT_TOKENS
    return {
        "font_color":  t["text"],
        "grid":        t["grid"],
        "plot_bg":     "rgba(0, 0, 0, 0)",
        "paper_bg":    "rgba(0, 0, 0, 0)",
        "primary":     GREEN_DARK,
        "accent":      GREEN,
        "fill":        "rgba(46, 204, 113, 0.22)",
        "navy":        NAVY,
    }


def _tokens_block(selector: str, tokens: dict) -> str:
    """Render a CSS block that forces both our custom vars and Streamlit's
    theme vars for the given selector."""
    return f"""
{selector} {{
    --pc-bg: {tokens['bg']};
    --pc-surface: {tokens['surface']};
    --pc-text: {tokens['text']};
    --pc-muted: {tokens['muted']};
    --pc-border: {tokens['border']};
    --pc-heading: {tokens['heading']};
    --background-color: {tokens['bg']};
    --secondary-background-color: {tokens['surface']};
    --text-color: {tokens['text']};
}}
"""


def build_css(mode: str) -> str:
    """Build the full theme CSS for the requested mode.

    `mode` is one of:
      - "Light": force light surfaces, regardless of system preference
      - "Dark":  force dark surfaces
      - "Auto":  follow OS prefers-color-scheme
    """
    light_css = _tokens_block(":root", LIGHT_TOKENS)
    dark_css = _tokens_block(":root", DARK_TOKENS)

    if mode == "Light":
        theme_vars = light_css
    elif mode == "Dark":
        theme_vars = dark_css
    else:
        # Auto: default to light, override under prefers-color-scheme: dark
        theme_vars = light_css + f"""
@media (prefers-color-scheme: dark) {{
    {_tokens_block(":root", DARK_TOKENS).strip()}
}}
"""

    forced_bg = "" if mode == "Auto" else f"""
[data-testid="stApp"], body {{
    background-color: var(--pc-bg) !important;
    color: var(--pc-text) !important;
}}
section[data-testid="stSidebar"] {{
    background-color: var(--pc-surface) !important;
}}
section[data-testid="stSidebar"] * {{
    color: var(--pc-text);
}}
[data-testid="stApp"] p,
[data-testid="stApp"] label,
[data-testid="stApp"] span,
[data-testid="stApp"] div {{
    color: var(--pc-text);
}}
"""

    return f"""
<style>
{theme_vars}

{forced_bg}

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

/* ---- Data editor rounded ---- */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {{
    border-radius: 10px;
    overflow: hidden;
}}

/* ---- Branded nav bar (always navy+green — brand consistent) ---- */
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
.pc-brand {{
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 700;
    font-size: 1.05rem;
    color: #ffffff;
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

/* ---- Branded footer (always navy — brand consistent) ---- */
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
    color: #ffffff;
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
