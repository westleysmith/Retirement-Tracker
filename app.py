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


SCENARIOS_DIR = Path(__file__).parent / "scenarios"
SCENARIOS_DIR.mkdir(exist_ok=True)


st.set_page_config(page_title="Retirement Tracker", layout="wide")
st.title("Retirement Tracker")
st.caption(
    "Monte Carlo projection in real (today's) dollars. "
    "Map out your career stages, set retirement assumptions, and see the "
    "probability distribution of outcomes."
)


def _career_stages_to_df(stages: list[CareerStage]) -> pd.DataFrame:
    if not stages:
        return pd.DataFrame(columns=[
            "start_age", "title", "salary", "contribution_pct", "employer_match_pct"
        ])
    return pd.DataFrame([{
        "start_age": s.start_age,
        "title": s.title,
        "salary": s.salary,
        "contribution_pct": s.contribution_pct,
        "employer_match_pct": s.employer_match_pct,
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
            contribution_pct=float(row.get("contribution_pct", 0.15) or 0.15),
            employer_match_pct=float(row.get("employer_match_pct", 0.05) or 0.05),
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


# ---------------------------------------------------------------------------
# Session state: initialize once, then let widgets mutate it directly.
# ---------------------------------------------------------------------------
if "inputs" not in st.session_state:
    st.session_state.inputs = default_scenario()

if "career_df" not in st.session_state:
    st.session_state.career_df = _career_stages_to_df(
        st.session_state.inputs.career_stages
    )

inputs: ScenarioInputs = st.session_state.inputs


# ---------------------------------------------------------------------------
# Sidebar: basics, balances, retirement, allocation, simulation settings
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Scenario")
    existing = sorted(p.stem for p in SCENARIOS_DIR.glob("*.json"))
    scenario_name = st.text_input("Name", value="my_plan")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save", use_container_width=True):
            inputs.career_stages = _df_to_career_stages(st.session_state.career_df)
            _save_scenario(scenario_name, inputs)
            st.success(f"Saved `{scenario_name}`")
    with c2:
        load_choice = st.selectbox("Load", [""] + existing, label_visibility="collapsed")
        if st.button("Load", use_container_width=True) and load_choice:
            loaded = _load_scenario(load_choice)
            if loaded:
                st.session_state.inputs = loaded
                st.session_state.career_df = _career_stages_to_df(loaded.career_stages)
                st.rerun()
    st.divider()

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

    st.subheader("Allocation")
    a1, a2, a3 = st.columns(3)
    with a1:
        s_now = st.slider("Stocks now", 0.0, 1.0, inputs.allocation_now.stocks, 0.05)
    with a2:
        b_now = st.slider("Bonds now", 0.0, 1.0, inputs.allocation_now.bonds, 0.05)
    with a3:
        c_now = st.slider("Cash now", 0.0, 1.0, inputs.allocation_now.cash, 0.05)
    inputs.allocation_now = AssetAllocation(s_now, b_now, c_now).normalized()

    b1, b2, b3 = st.columns(3)
    with b1:
        s_ret = st.slider("Stocks @ ret.", 0.0, 1.0, inputs.allocation_at_retirement.stocks, 0.05)
    with b2:
        b_ret = st.slider("Bonds @ ret.", 0.0, 1.0, inputs.allocation_at_retirement.bonds, 0.05)
    with b3:
        c_ret = st.slider("Cash @ ret.", 0.0, 1.0, inputs.allocation_at_retirement.cash, 0.05)
    inputs.allocation_at_retirement = AssetAllocation(s_ret, b_ret, c_ret).normalized()

    st.subheader("Simulation")
    inputs.num_simulations = st.select_slider(
        "Simulations", [1_000, 2_500, 5_000, 10_000, 20_000], value=inputs.num_simulations
    )
    seed_val = st.number_input("Random seed (0 = random)", 0, 2**31 - 1, 0)
    inputs.seed = None if seed_val == 0 else int(seed_val)


# ---------------------------------------------------------------------------
# Career stages editor
#
# The dataframe lives in st.session_state.career_df and the data_editor both
# reads from and writes to it via its key. This prevents the "edit reverts
# to previous value" bug caused by rebuilding the source df on every rerun.
# ---------------------------------------------------------------------------
st.subheader("Career stages")
st.caption(
    "One row per phase of your career. Salary is flat within a stage "
    "in today's dollars. For a raise or role change, add another row at "
    "that age. Press Enter or Tab after editing a cell to commit the change."
)

career_df = st.data_editor(
    st.session_state.career_df,
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
            "Contribution %", min_value=0.0, max_value=0.90, step=0.01, format="%.2f",
            help="Your savings rate (e.g. 0.15 = 15%). Assumes you save enough to get the full match.",
        ),
        "employer_match_pct": st.column_config.NumberColumn(
            "Employer match %", min_value=0.0, max_value=0.50, step=0.01, format="%.2f",
            help="Percent of salary your employer contributes (e.g. 0.05 = 5%).",
        ),
    },
)
st.session_state.career_df = career_df


# ---------------------------------------------------------------------------
# Run simulation
# ---------------------------------------------------------------------------
run = st.button("Run simulation", type="primary", use_container_width=True)

if run:
    inputs.career_stages = _df_to_career_stages(st.session_state.career_df)
    with st.spinner(f"Running {inputs.num_simulations:,} simulations..."):
        result = run_simulation(inputs, ReturnModel())
    st.session_state.result = result

result = st.session_state.get("result")

if result is None:
    st.info("Adjust inputs and click **Run simulation**.")
    st.stop()

success = result["success_rate"]
final = result["final_balances"]
paths = result["paths_df"]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Success rate", f"{success * 100:.1f}%",
          help="Fraction of simulations that reach plan end-age without depleting.")
m2.metric("Median final balance", f"${np.median(final):,.0f}")
m3.metric("10th percentile final", f"${np.percentile(final, 10):,.0f}")
m4.metric("90th percentile final", f"${np.percentile(final, 90):,.0f}")

st.subheader("Portfolio trajectory (real dollars)")
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=paths["age"], y=paths["p90"],
    mode="lines", line=dict(width=0), name="90th pct", showlegend=False,
))
fig.add_trace(go.Scatter(
    x=paths["age"], y=paths["p10"],
    mode="lines", line=dict(width=0), fill="tonexty",
    fillcolor="rgba(99,110,250,0.2)", name="10-90% range",
))
fig.add_trace(go.Scatter(
    x=paths["age"], y=paths["p50"],
    mode="lines", line=dict(width=3, color="#636EFA"), name="Median",
))
fig.add_vline(x=inputs.retirement_age, line_dash="dash", line_color="gray",
              annotation_text="Retirement", annotation_position="top")
fig.update_layout(
    height=450, xaxis_title="Age", yaxis_title="Portfolio value (today's $)",
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Final balance distribution")
hist = go.Figure()
hist.add_trace(go.Histogram(x=final, nbinsx=60, marker_color="#636EFA"))
hist.update_layout(
    height=350, xaxis_title="Final balance (today's $)", yaxis_title="Simulation count",
)
st.plotly_chart(hist, use_container_width=True)

with st.expander("Salary and contributions by age"):
    salary_df = paths[paths["salary"] > 0][["age", "salary"]]
    if not salary_df.empty:
        sfig = go.Figure()
        sfig.add_trace(go.Scatter(
            x=salary_df["age"], y=salary_df["salary"],
            mode="lines+markers", line=dict(color="#00CC96"),
        ))
        sfig.update_layout(
            height=300, xaxis_title="Age", yaxis_title="Salary (today's $)",
        )
        st.plotly_chart(sfig, use_container_width=True)
    else:
        st.caption("No working years projected (retirement age reached).")

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
