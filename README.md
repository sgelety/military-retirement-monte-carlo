# Beyond the Pension Cliff

**Monte Carlo Analysis of U.S. Military Retirement Systems**

This project compares lifetime retirement outcomes under the U.S.
military's legacy **High-Three** retirement system and the **Blended
Retirement System (BRS)** introduced in 2018, using Monte Carlo
simulation. The analysis operates at two levels:

1. **Individual** — lifetime retirement value (pension NPV + TSP
   present value) across three career profiles (Enlisted, Officer,
   Prior-Enlisted Officer) and 49 career-length scenarios.
2. **Fiscal** — expected government cost per entrant and aggregate
   DoD cost per annual accession cohort, weighted by actuarial
   separation probabilities.

## The policy question

Under High-Three, a service member who separates before 20 years of
service receives **no** retirement benefit — the "pension cliff."
Historically only ~19% of enlisted members and ~41% of officers reach
20 years. BRS trades a smaller pension multiplier (2.0% vs 2.5% per
year of service) for government TSP contributions (1% automatic +
up to 4% matching) that vest at 2 years and are portable. The
simulation quantifies who gains, who loses, and what it costs DoD.

## Headline findings (baseline assumptions)

- For members separating **before 20 years** (the large majority),
  BRS yields strictly higher lifetime value — High-Three gives them
  nothing.
- For members reaching **20+ years**, High-Three generally yields
  higher lifetime value at baseline; the gap is most sensitive to
  TSP return assumptions, which can flip the sign.
- Per entrant, expected government cost is **modestly lower under
  BRS**, and this holds across the modeled uncertainty range and a
  separation-timing what-if.

See the notebooks for exact figures, uncertainty bands, and
sensitivity analyses.

## Repository structure

| Path | Contents |
|---|---|
| `notebooks/01_data_prep.ipynb` | Load/clean raw data; synthetic L Fund backfill |
| `notebooks/02_pay_profiles.ipynb` | Career pay series; High-Three base matrix |
| `notebooks/03a_deterministic.ipynb` | Center-path lifetime values (validates the math) |
| `notebooks/03b_monte_carlo.ipynb` | Stochastic returns, COLA, life expectancy (N=20,000) |
| `notebooks/04_government_fiscal.ipynb` | DoD cost per entrant and per cohort |
| `notebooks/05_sensitivity_analysis.ipynb` | OAT tornado, scenario analysis, separation what-if |
| `src/` | Importable modules: pension/TSP math, NPV utilities, MC engine |
| `data/raw/` | Source data (DFAS pay table, DoD actuarial rates, TSP returns, CPI, SSA life tables) |
| `data/processed/` | Cleaned inputs and result CSVs produced by the notebooks |

Run the notebooks in order (01 → 02 → 03a → 03b → 04 → 05); each
reads the processed CSVs written by its predecessors. All random
draws are seeded, so results are reproducible.

## Setup

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Open the notebooks in VS Code or Jupyter and select the `.venv`
kernel.

## Key modeling choices

- Member contributes 5% of basic pay under **both** systems, so the
  comparison isolates the government-funded difference.
- TSP returns follow an age-based L Fund glide path parameterized
  from TSP historical data (extended to 2002 via regression-based
  synthetic backfill, R² > 0.99).
- COLA is parameterized from post-1947 CPI; the DoD Board of
  Actuaries 2.75% assumption anchors the deterministic baseline.
- Government TSP cost is measured on an **actuarial basis** (PV of
  contributions at the 5% discount rate), not at market returns.
- Out of scope: reserve retirement, continuation pay, withdrawal
  strategy, and behavioral retention effects (a mechanical
  separation-timing sensitivity is included instead).

Full assumptions and data provenance are documented in
[CLAUDE.md](CLAUDE.md).
