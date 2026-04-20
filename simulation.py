"""Monte Carlo retirement simulation engine.

All figures are in real (inflation-adjusted) dollars. The engine works in
today's dollars throughout, so users can reason about spending without
mentally discounting decades of inflation.

Return assumptions are real returns calibrated roughly to 20th-century
US historical data. These are adjustable in `ReturnModel`.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from models import (
    AssetAllocation,
    CareerStage,
    ScenarioInputs,
)


@dataclass
class ReturnModel:
    """Real return assumptions for each asset class."""
    stock_mean: float = 0.068
    stock_std: float = 0.170
    bond_mean: float = 0.020
    bond_std: float = 0.060
    cash_mean: float = 0.003
    cash_std: float = 0.010
    stock_bond_corr: float = 0.10


def _interpolate_allocation(
    start: AssetAllocation,
    end: AssetAllocation,
    age: int,
    start_age: int,
    end_age: int,
) -> AssetAllocation:
    """Linear glide path between current and retirement allocation."""
    if end_age <= start_age:
        return end.normalized()
    t = max(0.0, min(1.0, (age - start_age) / (end_age - start_age)))
    return AssetAllocation(
        stocks=start.stocks + (end.stocks - start.stocks) * t,
        bonds=start.bonds + (end.bonds - start.bonds) * t,
        cash=start.cash + (end.cash - start.cash) * t,
    ).normalized()


def _salary_at(age: int, stages: list[CareerStage]) -> tuple[float, CareerStage | None]:
    """Return (salary_in_todays_dollars, stage) for the given age.

    Flat within a stage. Returns the stage whose start_age is the most
    recent one <= age.
    """
    if not stages:
        return 0.0, None
    sorted_stages = sorted(stages, key=lambda s: s.start_age)
    active = None
    for s in sorted_stages:
        if age >= s.start_age:
            active = s
        else:
            break
    if active is None:
        return 0.0, None
    return float(active.salary), active


def _sample_asset_returns(
    rng: np.random.Generator,
    n_sims: int,
    model: ReturnModel,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Draw one year of returns for N simulations.

    Stocks and bonds are correlated via a Cholesky-factored bivariate normal.
    Cash is independent.
    """
    corr = model.stock_bond_corr
    cov = np.array([
        [model.stock_std ** 2, corr * model.stock_std * model.bond_std],
        [corr * model.stock_std * model.bond_std, model.bond_std ** 2],
    ])
    L = np.linalg.cholesky(cov)
    z = rng.standard_normal((2, n_sims))
    correlated = L @ z
    stock_ret = model.stock_mean + correlated[0]
    bond_ret = model.bond_mean + correlated[1]
    cash_ret = model.cash_mean + rng.standard_normal(n_sims) * model.cash_std
    return stock_ret, bond_ret, cash_ret


def run_simulation(
    inputs: ScenarioInputs,
    return_model: ReturnModel | None = None,
) -> dict:
    """Run the Monte Carlo projection.

    Returns a dict with:
      - ages: array of ages simulated
      - total_by_year: (n_sims, n_years) array of portfolio totals
      - success_rate: fraction of sims that reach end_age without depleting
      - final_balances: (n_sims,) array of ending balances
      - paths_df: DataFrame with age / p10 / p50 / p90 / salary
      - depleted: (n_sims,) boolean array
    """
    if return_model is None:
        return_model = ReturnModel()
    rng = np.random.default_rng(inputs.seed)
    n = inputs.num_simulations

    ages = np.arange(inputs.current_age, inputs.end_age + 1)
    n_years = len(ages)

    taxable = np.full(n, float(inputs.balance_taxable), dtype=np.float64)
    tax_deferred = np.full(n, float(inputs.balance_tax_deferred), dtype=np.float64)
    tax_free = np.full(n, float(inputs.balance_tax_free), dtype=np.float64)

    total_by_year = np.zeros((n, n_years))
    salary_by_age = np.zeros(n_years)
    depleted = np.zeros(n, dtype=bool)

    for i, age in enumerate(ages):
        alloc = _interpolate_allocation(
            inputs.allocation_now,
            inputs.allocation_at_retirement,
            int(age),
            inputs.current_age,
            inputs.retirement_age,
        )
        stock_r, bond_r, cash_r = _sample_asset_returns(rng, n, return_model)
        portfolio_r = (
            alloc.stocks * stock_r + alloc.bonds * bond_r + alloc.cash * cash_r
        )
        growth = 1.0 + portfolio_r
        taxable *= growth
        tax_deferred *= growth
        tax_free *= growth

        # Contributions while working
        if age < inputs.retirement_age:
            salary, stage = _salary_at(int(age), inputs.career_stages)
            salary_by_age[i] = salary
            if stage is not None and salary > 0:
                employee_contrib = salary * stage.contribution_pct
                match = salary * stage.employer_match_pct
                # Simplified routing: 70% of employee savings to tax-deferred,
                # 30% to taxable; all employer match to tax-deferred.
                tax_deferred += employee_contrib * 0.70 + match
                taxable += employee_contrib * 0.30

        # Retirement withdrawals (tax-aware order)
        if age >= inputs.retirement_age:
            ss = (
                float(inputs.social_security_annual)
                if age >= inputs.social_security_claim_age
                else 0.0
            )
            need = float(max(0.0, inputs.annual_retirement_spending - ss))
            remaining = np.full(n, need, dtype=np.float64)

            take_taxable = np.minimum(taxable, remaining)
            taxable -= take_taxable
            remaining -= take_taxable

            if inputs.retirement_tax_rate < 0.999:
                gross_needed = remaining / (1 - inputs.retirement_tax_rate)
            else:
                gross_needed = remaining * 1e9
            take_tax_def_gross = np.minimum(tax_deferred, gross_needed)
            tax_deferred -= take_tax_def_gross
            net_from_tax_def = take_tax_def_gross * (1 - inputs.retirement_tax_rate)
            remaining -= net_from_tax_def

            take_tax_free = np.minimum(tax_free, remaining)
            tax_free -= take_tax_free
            remaining -= take_tax_free

            depleted |= remaining > 1.0

        np.clip(taxable, 0, None, out=taxable)
        np.clip(tax_deferred, 0, None, out=tax_deferred)
        np.clip(tax_free, 0, None, out=tax_free)

        total_by_year[:, i] = taxable + tax_deferred + tax_free

    final_balances = total_by_year[:, -1]
    success_rate = float(np.mean(~depleted))

    p10 = np.percentile(total_by_year, 10, axis=0)
    p50 = np.percentile(total_by_year, 50, axis=0)
    p90 = np.percentile(total_by_year, 90, axis=0)

    df_paths = pd.DataFrame({
        "age": ages,
        "p10": p10,
        "p50": p50,
        "p90": p90,
        "salary": salary_by_age,
    })

    return {
        "ages": ages,
        "total_by_year": total_by_year,
        "final_balances": final_balances,
        "success_rate": success_rate,
        "paths_df": df_paths,
        "depleted": depleted,
    }
