"""Streamlit UI for the retirement tracker.

Run with:
    streamlit run app.py
"""
from __future__ import annotations

import json
import uuid
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

PROFILE_KEYS = list(ALLOCATION_PRESETS.keys())


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
# Page config + theming (theme follows OS via prefers-color-scheme)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Retirement Tracker · Pocket Check",
    page_icon="🟢",
    layout="wide",
)
st.markdown(branding.build_css(), unsafe_allow_html=True)
st.markdown(branding.NAV_HTML, unsafe_allow_html=True)

st.title("Retirement Tracker")
st.caption(
    "Monte Carlo projection in real (today's) dollars. "
    "Map out your career stages, set retirement assumptions, and see the "
    "probability distribution of outcomes."
)


def _new_id() -> str:
    """Short stable id for a career-row's widget keys."""
    return uuid.uuid4().hex[:8]


def _stage_to_row(s: CareerStage) -> dict:
    """Build a row dict for the custom editor. Percents are on a 0-100 scale
    in the row; the model stores them as 0.0-1.0."""
    return {
        "id": _new_id(),
        "start_age": int(s.start_age),
        "title": s.title,
        "salary": float(s.salary),
        "contribution_pct": float(s.contribution_pct) * 100.0,
        "employer_match_pct": float(s.employer_match_pct) * 100.0,
    }


def _row_to_stage(row: dict) -> CareerStage:
    return CareerStage(
        start_age=int(row["start_age"]),
        title=str(row.get("title", "") or ""),
        salary=float(row["salary"]),
        contribution_pct=float(row.get("contribution_pct", 15.0)) / 100.0,
        employer_match_pct=float(row.get("employer_match_pct", 5.0)) / 100.0,
    )


def _default_row(age_hint: int = 30) -> dict:
    return {
        "id": _new_id(),
        "start_age": int(age_hint),
        "title": "",
        "salary": 60_000.0,
        "contribution_pct": 15.0,
        "employer_match_pct": 5.0,
    }


def _load_scenario(name: str) -> ScenarioInputs | None:
    path = SCENARIOS_DIR / f"{name}.json"
    if not path.exists():
        return None
    return ScenarioInputs.from_dict(json.loads(path.read_text()))


def _save_scenario(name: str, inputs: ScenarioInputs) -> None:
    path = SCENARIOS_DIR / f"{name}.json"
    path.write_text(json.dumps(inputs.to_dict(), indent=2))


def _reset_career_list(stages: list[CareerStage]) -> None:
    """Rebuild career_list from a CareerStage list and clear any widget
    state tied to the old IDs so loaded values display correctly."""
    old_ids = [r["id"] for r in st.session_state.get("career_list", [])]
    st.session_state.career_list = [_stage_to_row(s) for s in stages]
    for rid in old_ids:
        for prefix in ("age_", "title_", "salary_", "contrib_", "match_"):
            st.session_state.pop(f"{prefix}{rid}", None)


# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
if "inputs" not in st.session_state:
    st.session_state.inputs = default_scenario()

inputs: ScenarioInputs = st.session_state.inputs

if "career_list" not in st.session_state:
    st.session_state.career_list = [_stage_to_row(s) for s in inputs.career_stages]

# Widget-backed session_state for risk profile - initialized from the
# current scenario so loading preserves the selection.
if "risk_profile" not in st.session_state:
    st.session_state.risk_profile = _match_risk_profile(
        inputs.allocation_now, inputs.allocation_at_retirement
    )


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Basics")
    inputs.current_age = st.number_input(
        "Current age", 16, 90, inputs.current_age, format="%d",
    )
    inputs.retirement_age = st.number_input(
        "Retirement age", inputs.current_age + 1, 95,
        max(inputs.retirement_age, inputs.current_age + 1), format="%d",
    )
    inputs.end_age = st.number_input(
        "Plan through age", inputs.retirement_age + 1, 110,
        max(inputs.end_age, inputs.retirement_age + 1), format="%d",
    )

    st.subheader("Current balances")
    inputs.balance_taxable = st.number_input(
        "Taxable brokerage", 0.0, 1e9,
        float(inputs.balance_taxable), step=1000.0, format="%.0f",
    )
    inputs.balance_tax_deferred = st.number_input(
        "Tax-deferred (401k/IRA)", 0.0, 1e9,
        float(inputs.balance_tax_deferred), step=1000.0, format="%.0f",
    )
    inputs.balance_tax_free = st.number_input(
        "Tax-free (Roth/HSA)", 0.0, 1e9,
        float(inputs.balance_tax_free), step=1000.0, format="%.0f",
    )

    st.subheader("Retirement")
    inputs.annual_retirement_spending = st.number_input(
        "Annual spending (today's $)", 0.0, 1e7,
        float(inputs.annual_retirement_spending), step=1000.0, format="%.0f",
    )
    inputs.retirement_tax_rate = st.slider(
        "Effective retirement tax rate", 0.0, 0.50,
        float(inputs.retirement_tax_rate), 0.01,
    )
    inputs.social_security_annual = st.number_input(
        "Social Security (annual, today's $)", 0.0, 200_000.0,
        float(inputs.social_security_annual), step=500.0, format="%.0f",
    )
    inputs.social_security_claim_age = st.number_input(
        "SS claim age", 62, 70, int(inputs.social_security_claim_age), format="%d",
    )

    st.subheader("Risk profile")
    selected_profile = st.radio(
        "Risk profile",
        PROFILE_KEYS,
        key="risk_profile",
        horizontal=True,
        label_visibility="collapsed",
    )
    preset = ALLOCATION_PRESETS[selected_profile]
    inputs.allocation_now = preset["now"]
    inputs.allocation_at_retirement = preset["retirement"]

    def _fmt_alloc(a: AssetAllocation) -> str:
        return f"{a.stocks * 100:.0f}% stocks / {a.bonds * 100:.0f}% bonds / {a.cash * 100:.0f}% cash"

    st.caption(preset["description"])
    st.caption(f"**Now:** {_fmt_alloc(preset['now'])}")
    st.caption(f"**At retirement:** {_fmt_alloc(preset['retirement'])}")

    # Simulation settings held constant.
    inputs.num_simulations = NUM_SIMULATIONS
    inputs.seed = None


# ---------------------------------------------------------------------------
# Career stages editor (custom per-row layout with insert-between buttons)
# ---------------------------------------------------------------------------
st.subheader("Career stages")
st.caption(
    "One row per phase of your career. Salary is flat within a stage in today's "
    "dollars. Use the **＋** between rows to insert a stage at that point. "
    "Use **＋ Add stage** at the bottom to append one."
)

# Column widths used by both the header row and each stage row
_COL_WEIGHTS = [1.1, 2.2, 2.2, 1.6, 1.8, 0.6]

header_cols = st.columns(_COL_WEIGHTS)
for col, title in zip(
    header_cols[:-1],
    ["Age", "Title", "Salary", "Contribution %", "Employer match %"],
):
    col.markdown(f"**{title}**")
header_cols[-1].markdown("&nbsp;", unsafe_allow_html=True)


def _render_insert_button(position: int, prev_id: str, next_id: str, hint_age: int) -> None:
    """Render a centered + button that inserts a new stage at `position`."""
    cols = st.columns([5, 1, 5])
    with cols[1]:
        if st.button(
            "＋",
            key=f"ins_{prev_id}_{next_id}",
            help="Insert a stage here",
            use_container_width=True,
        ):
            st.session_state.career_list.insert(position, _default_row(hint_age))
            st.rerun()


def _render_stage_row(idx: int, row: dict) -> None:
    cols = st.columns(_COL_WEIGHTS)
    rid = row["id"]
    with cols[0]:
        row["start_age"] = int(st.number_input(
            "Age", min_value=14, max_value=90, value=int(row["start_age"]),
            step=1, key=f"age_{rid}", label_visibility="collapsed", format="%d",
        ))
    with cols[1]:
        row["title"] = st.text_input(
            "Title", value=row.get("title", ""),
            key=f"title_{rid}", label_visibility="collapsed",
            placeholder="e.g. Senior Engineer",
        )
    with cols[2]:
        row["salary"] = float(st.number_input(
            "Salary", min_value=0.0, max_value=1e7,
            value=float(row["salary"]), step=1000.0,
            key=f"salary_{rid}", label_visibility="collapsed", format="%.0f",
        ))
    with cols[3]:
        row["contribution_pct"] = float(st.number_input(
            "Contribution %", min_value=0.0, max_value=90.0,
            value=float(row["contribution_pct"]), step=1.0,
            key=f"contrib_{rid}", label_visibility="collapsed", format="%.0f",
        ))
    with cols[4]:
        row["employer_match_pct"] = float(st.number_input(
            "Employer match %", min_value=0.0, max_value=15.0,
            value=float(row["employer_match_pct"]), step=0.5,
            key=f"match_{rid}", label_visibility="collapsed", format="%.1f",
        ))
    with cols[5]:
        if st.button("🗑", key=f"del_{rid}", help="Delete this stage"):
            st.session_state.career_list = [
                r for r in st.session_state.career_list if r["id"] != rid
            ]
            for prefix in ("age_", "title_", "salary_", "contrib_", "match_"):
                st.session_state.pop(f"{prefix}{rid}", None)
            st.rerun()


career_list = st.session_state.career_list
for i, row in enumerate(career_list):
    if i > 0:
        prev_row = career_list[i - 1]
        hint = (int(prev_row["start_age"]) + int(row["start_age"])) // 2
        _render_insert_button(i, prev_row["id"], row["id"], hint)
    _render_stage_row(i, row)

# Append button below the list
if st.button("＋ Add stage", key="add_stage_end"):
    last_age = int(career_list[-1]["start_age"]) if career_list else 22
    st.session_state.career_list.append(_default_row(last_age + 5))
    st.rerun()


# ---------------------------------------------------------------------------
# Run / Save / Load
# ---------------------------------------------------------------------------
col_run, col_save, col_load = st.columns([2, 1, 1])

with col_run:
    run = st.button("Run simulation", type="primary", use_container_width=True)

with col_save:
    scenario_name = st.text_input("Scenario name", value="my_plan", label_visibility="collapsed")
    if st.button("Save scenario", use_container_width=True):
        inputs.career_stages = sorted(
            [_row_to_stage(r) for r in st.session_state.career_list],
            key=lambda s: s.start_age,
        )
        _save_scenario(scenario_name, inputs)
        st.success(f"Saved `{scenario_name}`")

with col_load:
    existing = sorted(p.stem for p in SCENARIOS_DIR.glob("*.json"))
    load_choice = st.selectbox("Load", [""] + existing, label_visibility="collapsed")
    if st.button("Load scenario", use_container_width=True) and load_choice:
        loaded = _load_scenario(load_choice)
        if loaded:
            st.session_state.inputs = loaded
            st.session_state.risk_profile = _match_risk_profile(
                loaded.allocation_now, loaded.allocation_at_retirement
            )
            _reset_career_list(loaded.career_stages)
            st.rerun()


if run:
    inputs.career_stages = sorted(
        [_row_to_stage(r) for r in st.session_state.career_list],
        key=lambda s: s.start_age,
    )
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

plot = branding.plot_tokens()

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
