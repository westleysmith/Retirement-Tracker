# Retirement Tracker

A Monte Carlo retirement projection tool that models career progression, life events, glide-path asset allocation, and tax-aware withdrawals. Built in Python with a Streamlit UI.

Most retirement calculators assume a flat salary, a flat return, and no life changes. This one doesn't.

## What it models

- **Career stages.** Multiple salary phases with their own real growth rate, savings rate, and employer match.
- **Life events.** One-time expenses and windfalls, plus recurring expenses over a date range (kids, mortgage, etc.).
- **Separate account types.** Taxable, tax-deferred (401k/Traditional IRA), and tax-free (Roth/HSA). Withdrawals follow the standard tax-aware order.
- **Glide-path allocation.** Stocks/bonds/cash mix linearly transitions from your current allocation to your retirement allocation.
- **Correlated returns.** Stocks and bonds are drawn from a correlated bivariate normal, capturing real-world diversification.
- **Social Security** as a fixed real annual benefit starting at claim age.
- **10,000+ Monte Carlo paths** by default, giving you a probability distribution instead of a single number.

All figures are in **real (today's) dollars**, so you can reason about spending without mentally adjusting for decades of inflation.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at http://localhost:8501.

## Usage

1. Fill in your basics in the sidebar (age, balances, retirement spending target).
2. Edit the **Career stages** table - add rows for each phase of your career.
3. Edit the **Life events** table - add home purchases, kids, inheritances, etc.
4. Click **Run simulation**.
5. Save the scenario with a name. Try variations ("base", "if I get promoted", "aggressive FIRE") and compare.

Scenario JSON files are saved to `scenarios/` locally and are gitignored.

## What's intentionally simplified

See the "Assumptions and limitations" section inside the app. Notable omissions: tax brackets (a single effective rate is used), RMDs, Roth conversion strategy, state tax, health shocks, and variable retirement spending.

## Roadmap

- Historical bootstrap option (sample from actual historical sequences vs. parametric returns)
- Tax-bracket-aware withdrawal modeling
- Scenario comparison view (overlay multiple saved scenarios)
- Sequence-of-returns stress tests (run through 1966, 2000, 1929 sequences explicitly)

## License

MIT
