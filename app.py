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
    LifeEvent,
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
    "Models career progression, life events, glide-path allocation, "
    "and tax-aware withdrawals."
)


def _load_scenario(name: str) -> ScenarioInputs | None:
    path = SCENARIOS_DIR / f"{name}.json"
    if not path.exists():
        return None
    return ScenarioInputs.from_dict(json.loads(path.read_text()))


def _save_scenario(name: str, inputs: ScenarioInputs) -> None:
    path = SCENARIOS_DIR / f"{name}.json"
    path.write_text(json.dumps(inputs.to_dict(), indent=2))


# --- Scenario management ---
if "inputs" not in st.session_state:
    st.session_state.inputs = default_scenario()

inputs: ScenarioInputs = st.session_state.inputs

with st.sidebar:
    st.header("Scenario")
    existing = sorted(p.stem for p in SCENARIOS_DIR.glob("*.json"))
    col_a, col_b = st.columns(2)
    with col_a:
        scenario_name = st.text_input("Name", value="my_plan")
        if st.button("Save", use_container_width=True):
            _save_scenario(scenario_name, inputs)
            st.success(f"Saved `{scenario_name}`")
    with col_b:
        load_choice = st.selectbox("Load", [""] + existing)
        if st.button("Load", use_container_width=True) and load_choice:
            loaded = _load_scenario(load_choice)
            if loaded:
                st.session_state.inputs = loaded
                st.rerun()
    st.divider()

    st.header("Basics")
    inputs.current_age = st.number_input("Current age", 18, 90, inputs.current_age)
    inputs.retirement_age = st.number_input(
        "Retirement age", inputs.current_age + 1, 95, max(inputs.retirement_age, inputs.current_age + 1)
    )
    inputs.end_age = st.number_input(
        "Plan through age", inputs.retirement_age + 1, 110, max(inputs.end_age, inputs.retirement_age + 1)
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
        "Annual spending (today's $)", 0.0, 1e7, float(inputs.annual_retirement_spending), step=1000.0
    )
    inputs.retirement_tax_rate = st.slider(
        "Effective retirement tax rate", 0.0, 0.50, float(inputs.retirement_tax_rate), 0.01
    )
    inputs.social_security_annual = st.number_input(
        "Social Security (annual, today's $)", 0.0, 200_000.0, float(inputs.social_security_annual), step=500.0
    )
    inputs.social_security_claim_age = st.number_input(
        "SS claim age", 62, 70, int(inputs.social_security_claim_age)
    )

    st.subheader("Allocation")
    c1, c2, c3 = st.columns(3)
    with c1:
        s_now = st.slider("Stocks now", 0.0, 1.0, inputs.allocation_now.stocks, 0.05)
    with c2:
        b_now = st.slider("Bonds now", 0.0, 1.0, inputs.allocation_now.bonds, 0.05)
    with c3:
        c_now = st.slider("Cash now", 0.0, 1.0, inputs.allocation_now.cash, 0.05)
    inputs.allocation_now = AssetAllocation(s_now, b_now, c_now).normalized()

    c1, c2, c3 = st.columns(3)
    with c1:
        s_ret = st.slider("Stocks @ ret.", 0.0, 1.0, inputs.allocation_at_retirement.stocks, 0.05)
    with c2:
        b_ret = st.slider("Bonds @ ret.", 0.0, 1.0, inputs.allocation_at_retirement.bonds, 0.05)
    with c3:
        c_ret = st.slider("Cash @ ret.", 0.0, 1.0, inputs.allocation_at_retirement.cash, 0.05)
    inputs.allocation_at_retirement = AssetAllocation(s_ret, b_ret, c_ret).normalized()

    st.subheader("Simulation")
    inputs.num_simulations = st.select_slider(
        "Simulations", [1_000, 2_500, 5_000, 10_000, 20_000], value=inputs.num_simulations
    )
    inputs.seed = st.number_input("Random seed (0 = random)", 0, 2**31 - 1, 0)
    if inputs.seed == 0:
        inputs.seed = None


# --- Career stages editor ---
st.subheader("Career stages")
st.caption(
    "Each row is a phase of your career. Salary is in today's dollars at the start of the stage. "
    "`real_growth_rate` is annual raise above inflation within the stage."
)
career_df = pd.DataFrame([s.__dict__ for s in inputs.career_stages])
if career_df.empty:
    career_df = pd.DataFrame(columns=[
        "start_age", "label", "salary", "real_growth_rate",
        "savings_rate", "employer_match_pct", "employer_match_limit_pct",
    ])
edited_career = st.data_editor(
    career_df, num_rows="dynamic", use_container_width=True, key="career_editor",
    column_config={
        "salary": st.column_config.NumberColumn(format="$%.0f"),
        "real_growth_rate": st.column_config.NumberColumn(format="%.2f%%", min_value=-0.1, max_value=0.2, step=0.005),
        "savings_rate": st.column_config.NumberColumn(format="%.2f%%", min_value=0.0, max_value=0.9, step=0.01),
        "employer_match_pct": st.column_config.NumberColumn(format="%.2f%%", min_value=0.0, max_value=0.5, step=0.005),
        "employer_match_limit_pct": st.column_config.NumberColumn(format="%.2f%%", min_value=0.0, max_value=0.5, step=0.005),
    },
)

# --- Life events editor ---
st.subheader("Life events")
st.caption(
    "`expense` and `windfall` are one-time at `age`. `recurring_expense` runs from `age` through `end_age`."
)
event_df = pd.DataFrame([e.__dict__ for e in inputs.life_events])
if event_df.empty:
    event_df = pd.DataFrame(columns=["age", "label", "amount", "event_type", "end_age"])
edited_events = st.data_editor(
    event_df, num_rows="dynamic", use_container_width=True, key="event_editor",
    column_config={
        "amount": st.column_config.NumberColumn(format="$%.0f"),
        "event_type": st.column_config.SelectboxColumn(
            options=["expense", "windfall", "recurring_expense"]
        ),
    },
)

# Commit edits back to inputs
def _coerce_career(df: pd.DataFrame) -> list[CareerStage]:
    out = []
    for _, row in df.iterrows():
        if pd.isna(row.get("start_age")) or pd.isna(row.get("salary")):
            continue
        out.append(CareerStage(
            start_age=int(row["start_age"]),
            label=str(row.get("label", "")),
            salary=float(row["salary"]),
            real_growth_rate=float(row.get("real_growth_rate", 0.02) or 0.02),
            savings_rate=float(row.get("savings_rate", 0.15) or 0.15),
            employer_match_pct=float(row.get("employer_match_pct", 0.05) or 0.05),
            employer_match_limit_pct=float(row.get("employer_match_limit_pct", 0.05) or 0.05),
        ))
    return out


def _coerce_events(df: pd.DataFrame) -> list[LifeEvent]:
    out = []
    for _, row in df.iterrows():
        if pd.isna(row.get("age")) or pd.isna(row.get("amount")):
            continue
        end_age = row.get("end_age")
        end_age_val = None if pd.isna(end_age) else int(end_age)
        out.append(LifeEvent(
            age=int(row["age"]),
            label=str(row.get("label", "")),
            amount=float(row["amount"]),
            event_type=str(row.get("event_type", "expense")),
            end_age=end_age_val,
        ))
    return out


inputs.career_stages = _coerce_career(edited_career)
inputs.life_events = _coerce_events(edited_events)

# --- Run simulation ---
run = st.button("Run simulation", type="primary", use_container_width=True)

if run:
    with st.spinner(f"Running {inputs.num_simulations:,} simulations..."):
        result = run_simulation(inputs, ReturnModel())
    st.session_state.result = result
    st.session_state.last_inputs = inputs.to_dict()

result = st.session_state.get("result")

if result is None:
    st.info("Adjust inputs and click **Run simulation**.")
    st.stop()

# --- Results ---
success = result["success_rate"]
final = result["final_balances"]
paths = result["paths_df"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Success rate", f"{success * 100:.1f}%",
            help="Fraction of simulations that reach plan end-age without depleting.")
col2.metric("Median final balance", f"${np.median(final):,.0f}")
col3.metric("10th percentile final", f"${np.percentile(final, 10):,.0f}")
col4.metric("90th percentile final", f"${np.percentile(final, 90):,.0f}")

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

with st.expander("Salary projection (deterministic)"):
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

with st.expander("Assumptions and limitations"):
    st.markdown("""
- **All figures are real (today's dollars).** Inflation is not added back.
- **Real return assumptions** (annual): stocks 6.8% / σ=17%, bonds 2.0% / σ=6%, cash 0.3% / σ=1%. Stock-bond correlation 0.10.
- **Withdrawal order in retirement:** taxable → tax-deferred → tax-free.
- **Taxes:** a single effective rate is applied to tax-deferred withdrawals only. No bracket logic, RMDs, or state tax.
- **Contributions:** employee savings split 70% tax-deferred / 30% taxable. Employer match goes to tax-deferred.
- **Allocation:** same across all account types. Linear glide path from now → retirement age.
- **Social Security:** fixed real annual benefit starting at claim age.
- **Not modeled:** health shocks, long-term care, mortgage interest, variable spending in retirement, Roth conversions, RMD-forced withdrawals.
""")
