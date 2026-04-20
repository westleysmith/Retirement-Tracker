"""Data models for the retirement tracker inputs."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal


AccountType = Literal["taxable", "tax_deferred", "tax_free"]
EventType = Literal["expense", "windfall", "recurring_expense"]


@dataclass
class CareerStage:
    """A phase of your career with a salary and savings rate.

    Salary is in today's dollars. Real growth is applied year-over-year within
    a stage (on top of inflation, which the simulation handles by working in
    real dollars throughout).
    """
    start_age: int
    label: str
    salary: float
    real_growth_rate: float = 0.02
    savings_rate: float = 0.15
    employer_match_pct: float = 0.05
    employer_match_limit_pct: float = 0.05


@dataclass
class LifeEvent:
    """A one-time or recurring cash flow event.

    For a one-time event, set end_age == age. For recurring, set end_age
    to the last year it applies.
    """
    age: int
    label: str
    amount: float
    event_type: EventType = "expense"
    end_age: int | None = None


@dataclass
class AssetAllocation:
    """Target stock/bond/cash allocation - sums to 1.0."""
    stocks: float = 0.80
    bonds: float = 0.15
    cash: float = 0.05

    def normalized(self) -> "AssetAllocation":
        total = self.stocks + self.bonds + self.cash
        if total <= 0:
            return AssetAllocation(0.6, 0.3, 0.1)
        return AssetAllocation(
            self.stocks / total, self.bonds / total, self.cash / total
        )


@dataclass
class ScenarioInputs:
    """Complete set of inputs for a retirement projection."""
    current_age: int = 30
    retirement_age: int = 65
    end_age: int = 95

    # Starting balances by tax treatment
    balance_taxable: float = 0.0
    balance_tax_deferred: float = 0.0
    balance_tax_free: float = 0.0

    # Retirement spending in today's dollars
    annual_retirement_spending: float = 80_000.0

    # Effective tax rate applied to tax-deferred withdrawals in retirement
    retirement_tax_rate: float = 0.18

    # Social Security - annual benefit in today's dollars, starting at claim age
    social_security_annual: float = 0.0
    social_security_claim_age: int = 67

    # Asset allocation - target at start and at retirement (glide path interpolates)
    allocation_now: AssetAllocation = field(default_factory=lambda: AssetAllocation(0.90, 0.05, 0.05))
    allocation_at_retirement: AssetAllocation = field(default_factory=lambda: AssetAllocation(0.60, 0.35, 0.05))

    # Career and life events
    career_stages: list[CareerStage] = field(default_factory=list)
    life_events: list[LifeEvent] = field(default_factory=list)

    # Simulation settings
    num_simulations: int = 10_000
    seed: int | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @staticmethod
    def from_dict(d: dict) -> "ScenarioInputs":
        career = [CareerStage(**s) for s in d.get("career_stages", [])]
        events = [LifeEvent(**e) for e in d.get("life_events", [])]
        alloc_now = AssetAllocation(**d.get("allocation_now", {}))
        alloc_ret = AssetAllocation(**d.get("allocation_at_retirement", {}))
        base = {k: v for k, v in d.items() if k not in {
            "career_stages", "life_events", "allocation_now", "allocation_at_retirement"
        }}
        return ScenarioInputs(
            **base,
            career_stages=career,
            life_events=events,
            allocation_now=alloc_now,
            allocation_at_retirement=alloc_ret,
        )


def default_scenario() -> ScenarioInputs:
    """A sensible starter scenario with no personal data."""
    return ScenarioInputs(
        current_age=30,
        retirement_age=65,
        end_age=95,
        balance_taxable=10_000,
        balance_tax_deferred=50_000,
        balance_tax_free=15_000,
        annual_retirement_spending=80_000,
        retirement_tax_rate=0.18,
        social_security_annual=25_000,
        social_security_claim_age=67,
        career_stages=[
            CareerStage(start_age=30, label="Current role", salary=100_000,
                        real_growth_rate=0.03, savings_rate=0.15,
                        employer_match_pct=0.05, employer_match_limit_pct=0.05),
            CareerStage(start_age=35, label="Senior role", salary=140_000,
                        real_growth_rate=0.02, savings_rate=0.20,
                        employer_match_pct=0.05, employer_match_limit_pct=0.05),
            CareerStage(start_age=45, label="Late career", salary=180_000,
                        real_growth_rate=0.01, savings_rate=0.25,
                        employer_match_pct=0.05, employer_match_limit_pct=0.05),
        ],
        life_events=[
            LifeEvent(age=32, label="Home down payment", amount=80_000, event_type="expense"),
            LifeEvent(age=34, label="First child", amount=15_000,
                      event_type="recurring_expense", end_age=52),
            LifeEvent(age=50, label="Inheritance", amount=100_000, event_type="windfall"),
        ],
    )
