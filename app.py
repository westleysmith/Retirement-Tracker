"""Streamlit UI for the retirement tracker.

Run with:
    streamlit run app.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from models import (
    AssetAllocation,
    CareerStage,
    ScenarioInputs,
    default_scenario,
)
from simulation import ReturnModel, run_simulation
import branding


SCENARIOS_DIR = Path(__file__).parent / "scenarios"
SCENARIOS_DIR.mkdir(exist_ok=True)

NUM_SIMULATIONS = 10_000


# ---------------------------------------------------------------------------
# Risk-profile presets
#
# Three target-date-style glide paths from Conservative (bond-heavy) through
# Balanced (industry-standard default) to Aggressive (growth-focused).
# Each preset defines both the current allocation and the retirement-age
# allocation; the simulator linearly interpolates between them.
# ---------------------------------------------------------------------------
ALLOCATION_PRESETS: dict[str, dict] = {
    "Conservative": {
        "now":         AssetAllocation(0.50, 0.45, 0.05),
        "retirement":  AssetAllocation(0.30, 0.65, 0.05),
        "description": "Lower volatility, bond-heavy. Prioritizes capital preservation over growth.",
    },
    "Balanced": {
        "now":         AssetAllocation(0.80, 0.15, 0.05),
        "retirement":  AssetAllocation(0.55, 0.40, 0.05),
        "description": "Industry-standard target-date glide path. A reasonable default for most people.",
    },
    "Aggressive": {
        "now":         AssetAllocation(0.95, 0.04, 0.01),
        "retirement":  AssetAllocation(0.70, 0.25, 0.05),
        "description": "Growth-focused. Higher expected return with higher volatility through retirement.",
    },
}


def _match_risk_profile(alloc_now: AssetAllocation, alloc_ret: AssetAllocation) -> str:
    """Return the preset whose allocations are closest to the given pair."""
    best_name, best_dist = "Balanced", float("inf")
    for name, preset in ALLOCATION_PRESETS.items():
        dist = (
            abs(preset["now"].stocks - alloc_now.stocks)
            + abs(preset["retirement"].stocks - alloc_ret.stocks)
        )
        if dist < best_dist:
            best_name, best_dist = name, dist
    return best_name


# ---------------------------------------------------------------------------
# Page config + theming
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Retirement Tracker · Pocket Check",
    page_icon="🟢",
    layout="wide",
)

# Theme mode must be resolved before CSS is injected.
if "pc_theme" not in st.session_state:
    st.session_state.pc_theme = "Auto"

st.markdown(branding.build_css(st.session_state.pc_theme), unsafe_allow_html=True)

# --- Top-right theme toggle ---
_spacer, _t1, _t2, _t3 = st.columns([10, 1, 1, 1], gap="small")
_THEME_BUTTONS = [
    (_t1, "Light", "☀️", "Light mode"),
    (_t2, "Dark", "🌙", "Dark mode"),
    (_t3, "Auto", "🖥", "Match system"),
]
for _col, _mode, _icon, _help in _THEME_BUTTONS:
    with _col:
        _is_active = st.session_state.pc_theme == _mode
        if st.button(
            _icon,
            key=f"theme_btn_{_mode}",
            help=_help,
            type="primary" if _is_active else "secondary",
            use_container_width=True,
        ):
            if st.session_state.pc_theme != _mode:
                st.session_state.pc_theme = _mode
                st.rerun()

st.markdown(branding.NAV_HTML, unsafe_allow_html=True)

st.title("Retirement Tracker")
st.caption(
    "Monte Carlo projection in real (today's) dollars. "
    "Map out your career stages, set retirement assumptions, and see the "
    "probability distribution of outcomes."
)


def _career_stages_to_df(stages: list[CareerStage]) -> pd.DataFrame:
    """Build the editor dataframe. Percent columns are displayed on a 0-100
    scale so they read naturally; the model stores them as 0.0-1.0."""
    if not stages:
        return pd.DataFrame({
            "start_age": pd.Series(dtype="int64"),
            "title": pd.Series(dtype="object"),
            "salary": pd.Series(dtype="float64"),
            "contribution_pct": pd.Series(dtype="float64"),
            "employer_match_pct": pd.Series(dtype="float64"),
        })
    return pd.DataFrame([{
        "start_age": int(s.start_age),
        "title": s.title,
        "salary": float(s.salary),
        "contribution_pct": float(s.contribution_pct) * 100.0,
        "employer_match_pct": float(s.employer_match_pct) * 100.0,
    } for s in stages])


def _df_to_career_stages(df: pd.DataFrame) -> list[CareerStage]:
    out = []
    for _, row in df.iterrows():
        if pd.isna(row.get("start_age")) or pd.isna(row.get("salary")):
            continue
        out.append(CareerStage(
            start_age=int(row["start_age"]),
            title=str(row.get("title", "") or ""),
            salary=float(row["salary"]),
            contribution_pct=float(row.get("contribution_pct", 15.0) or 15.0) / 100.0,
            employer_match_pct=float(row.get("employer_match_pct", 5.0) or 5.0) / 100.0,
        ))
    return sorted(out, key=lambda s: s.start_age)


def _load_scenario(name: str) -> ScenarioInputs | None:
    path = SCENARIOS_DIR / f"{name}.json"
    if not path.exists():
        return None
    return ScenarioInputs.from_dict(json.loads(path.read_text()))


def _save_scenario(name: str, inputs: ScenarioInputs) -> None:
    path = SCENARIOS_DIR / f"{name}.json"
    path.write_text(json.dumps(inputs.to_dict(), indent=2))


def _reset_career_editor(source_df: pd.DataFrame) -> None:
    st.session_state.career_df_source = source_df
    if "career_editor" in st.session_state:
        del st.session_state["career_editor"]


# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
if "inputs" not in st.session_state:
    st.session_state.inputs = default_scenario()

if "career_df_source" not in st.session_state:
    st.session_state.career_df_source = _career_stages_to_df(
        st.session_state.inputs.career_stages
    )

inputs: ScenarioInputs = st.session_state.inputs


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Basics")
    inputs.current_age = st.number_input("Current age", 16, 90, inputs.current_age)
    inputs.retirement_age = st.number_input(
        "Retirement age", inputs.current_age + 1, 95,
        max(inputs.retirement_age, inputs.current_age + 1),
    )
    inputs.end_age = st.number_input(
        "Plan through age", inputs.retirement_age + 1, 110,
        max(inputs.end_age, inputs.retirement_age + 1),
    )

    st.subheader("Current balances")
    inputs.balance_taxable = st.number_input(
        "Taxable brokerage", 0.0, 1e9, float(inputs.balance_taxable), step=1000.0
    )
    inputs.balance_tax_deferred = st.number_input(
        "Tax-deferred (401k/IRA)", 0.0, 1e9, float(inputs.balance_tax_deferred), step=1000.0
    )
    inputs.balance_tax_free = st.number_input(
        "Tax-free (Roth/HSA)", 0.0, 1e9, float(inputs.balance_tax_free), step=1000.0
    )

    st.subheader("Retirement")
    inputs.annual_retirement_spending = st.number_input(
        "Annual spending (today's $)", 0.0, 1e7,
        float(inputs.annual_retirement_spending), step=1000.0
    )
    inputs.retirement_tax_rate = st.slider(
        "Effective retirement tax rate", 0.0, 0.50,
        float(inputs.retirement_tax_rate), 0.01,
    )
    inputs.social_security_annual = st.number_input(
        "Social Security (annual, today's $)", 0.0, 200_000.0,
        float(inputs.social_security_annual), step=500.0,
    )
    inputs.social_security_claim_age = st.number_input(
        "SS claim age", 62, 70, int(inputs.social_security_claim_age)
    )

    st.subheader("Risk profile")
    default_profile = _match_risk_profile(
        inputs.allocation_now, inputs.allocation_at_retirement
    )
    risk_profile = st.radio(
        "Risk profile",
        list(ALLOCATION_PRESETS.keys()),
        index=list(ALLOCATION_PRESETS.keys()).index(default_profile),
        horizontal=True,
        label_visibility="collapsed",
    )
    preset = ALLOCATION_PRESETS[risk_profile]
    inputs.allocation_now = preset["now"]
    inputs.allocation_at_retirement = preset["retirement"]

    def _fmt_alloc(a: AssetAllocation) -> str:
        return f"{a.stocks * 100:.0f}% stocks / {a.bonds * 100:.0f}% bonds / {a.cash * 100:.0f}% cash"

    st.caption(preset["description"])
    st.caption(f"**Now:** {_fmt_alloc(preset['now'])}")
    st.caption(f"**At retirement:** {_fmt_alloc(preset['retirement'])}")

    # Simulation settings held constant: 10k sims, random seed.
    inputs.num_simulations = NUM_SIMULATIONS
    inputs.seed = None


# ---------------------------------------------------------------------------
# Career stages editor
# ---------------------------------------------------------------------------
st.subheader("Career stages")
st.caption(
    "One row per phase of your career. Salary is flat within a stage in today's "
    "dollars. For a raise or role change, add another row at that age. "
    "Press Tab or Enter after editing a cell to commit the change before "
    "clicking buttons."
)

edited_career_df = st.data_editor(
    st.session_state.career_df_source,
    num_rows="dynamic",
    use_container_width=True,
    key="career_editor",
    column_config={
        "start_age": st.column_config.NumberColumn(
            "Age", min_value=14, max_value=90, step=1, format="%d",
            help="Age at which this stage begins.",
        ),
        "title": st.column_config.TextColumn("Title"),
        "salary": st.column_config.NumberColumn(
            "Salary", min_value=0.0, step=1000.0, format="$%.0f",
            help="Gross annual salary in today's dollars.",
        ),
        "contribution_pct": st.column_config.NumberColumn(
            "Contribution %", min_value=0.0, max_value=90.0, step=1.0, format="%d%%",
            help="Your savings rate as a percent (e.g. 15 = 15%). Assumes you save enough to get the full match.",
        ),
        "employer_match_pct": st.column_config.NumberColumn(
            "Employer match %", min_value=0.0, max_value=15.0, step=0.5, format="%.1f%%",
            help="Percent of salary your employer contributes (e.g. 5 = 5%). Most employers are in the 3-6% range.",
        ),
    },
)


# ---------------------------------------------------------------------------
# Run / Save / Load
# ---------------------------------------------------------------------------
col_run, col_save, col_load = st.columns([2, 1, 1])

with col_run:
    run = st.button("Run simulation", type="primary", use_container_width=True)

with col_save:
    scenario_name = st.text_input("Scenario name", value="my_plan", label_visibility="collapsed")
    if st.button("Save scenario", use_container_width=True):
        inputs.career_stages = _df_to_career_stages(edited_career_df)
        _save_scenario(scenario_name, inputs)
        st.success(f"Saved `{scenario_name}`")

with col_load:
    existing = sorted(p.stem for p in SCENARIOS_DIR.glob("*.json"))
    load_choice = st.selectbox("Load", [""] + existing, label_visibility="collapsed")
    if st.button("Load scenario", use_container_width=True) and load_choice:
        loaded = _load_scenario(load_choice)
        if loaded:
            st.session_state.inputs = loaded
            _reset_career_editor(_career_stages_to_df(loaded.career_stages))
            st.rerun()


if run:
    inputs.career_stages = _df_to_career_stages(edited_career_df)
    with st.spinner(f"Running {NUM_SIMULATIONS:,} simulations..."):
        result = run_simulation(inputs, ReturnModel())
    st.session_state.result = result

result = st.session_state.get("result")

if result is None:
    st.info("Adjust inputs and click **Run simulation**.")
    st.stop()


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
success = result["success_rate"]
final = result["final_balances"]
paths = result["paths_df"]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Success rate", f"{success * 100:.1f}%",
          help="Fraction of simulations that reach plan end-age without depleting.")
m2.metric("Median final balance", f"${np.median(final):,.0f}")
m3.metric("10th percentile final", f"${np.percentile(final, 10):,.0f}")
m4.metric("90th percentile final", f"${np.percentile(final, 90):,.0f}")

plot = branding.plot_tokens(st.session_state.pc_theme)

st.subheader("Portfolio trajectory (real dollars)")
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=paths["age"], y=paths["p90"],
    mode="lines", line=dict(width=0), name="90th pct", showlegend=False,
))
fig.add_trace(go.Scatter(
    x=paths["age"], y=paths["p10"],
    mode="lines", line=dict(width=0), fill="tonexty",
    fillcolor=plot["fill"], name="10-90% range",
))
fig.add_trace(go.Scatter(
    x=paths["age"], y=paths["p50"],
    mode="lines", line=dict(width=3, color=plot["primary"]), name="Median",
))
fig.add_vline(
    x=inputs.retirement_age, line_dash="dash",
    line_color=plot["font_color"],
    annotation_text="Retirement", annotation_position="top",
    annotation_font_color=plot["font_color"],
)
fig.update_layout(
    height=450, xaxis_title="Age", yaxis_title="Portfolio value (today's $)",
    hovermode="x unified",
    plot_bgcolor=plot["plot_bg"], paper_bgcolor=plot["paper_bg"],
    font=dict(color=plot["font_color"]),
    xaxis=dict(gridcolor=plot["grid"]),
    yaxis=dict(gridcolor=plot["grid"]),
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Final balance distribution")
hist = go.Figure()
hist.add_trace(go.Histogram(x=final, nbinsx=60, marker_color=plot["accent"]))
hist.update_layout(
    height=350, xaxis_title="Final balance (today's $)", yaxis_title="Simulation count",
    plot_bgcolor=plot["plot_bg"], paper_bgcolor=plot["paper_bg"],
    font=dict(color=plot["font_color"]),
    xaxis=dict(gridcolor=plot["grid"]),
    yaxis=dict(gridcolor=plot["grid"]),
    bargap=0.02,
)
st.plotly_chart(hist, use_container_width=True)

with st.expander("Salary by age"):
    salary_df = paths[paths["salary"] > 0][["age", "salary"]]
    if not salary_df.empty:
        sfig = go.Figure()
        sfig.add_trace(go.Scatter(
            x=salary_df["age"], y=salary_df["salary"],
            mode="lines+markers",
            line=dict(color=plot["primary"], width=3),
            marker=dict(color=plot["accent"], size=8),
        ))
        sfig.update_layout(
            height=300, xaxis_title="Age", yaxis_title="Salary (today's $)",
            plot_bgcolor=plot["plot_bg"], paper_bgcolor=plot["paper_bg"],
            font=dict(color=plot["font_color"]),
            xaxis=dict(gridcolor=plot["grid"]),
            yaxis=dict(gridcolor=plot["grid"]),
        )
        st.plotly_chart(sfig, use_container_width=True)
    else:
        st.caption("No working years projected from current age.")

with st.expander("Assumptions and limitations"):
    st.markdown("""
- **All figures are in real (today's) dollars.** Inflation is not added back.
- **Real return assumptions** (annual): stocks 6.8% / σ=17%, bonds 2.0% / σ=6%, cash 0.3% / σ=1%. Stock-bond correlation 0.10.
- **Withdrawal order in retirement:** taxable → tax-deferred → tax-free.
- **Taxes:** a single effective rate is applied to tax-deferred withdrawals only. No bracket logic, RMDs, or state tax.
- **Contribution routing:** 70% of your savings into tax-deferred, 30% into taxable. Employer match all goes tax-deferred.
- **Salary is flat within a stage.** To model a raise, add another stage.
- **Allocation:** same across all account types. Linear glide path from now → retirement age.
- **Social Security:** fixed real annual benefit starting at claim age.
- **Not modeled:** health shocks, variable spending, Roth conversions, RMD-forced withdrawals.
""")

st.markdown(branding.FOOTER_HTML, unsafe_allow_html=True)
