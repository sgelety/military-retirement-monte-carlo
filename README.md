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

For a narrative walkthrough of the pipeline, the modeling decisions
and their rationale, and where the answers stand, see
[docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md).

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
- For members reaching **20+ years**, High-Three yields higher
  lifetime value at baseline; the gap is most sensitive to TSP
  return and inflation assumptions, and a sustained bull-market
  scenario can flip it.
- Per entrant, expected government cost is **roughly 10% lower
  under BRS**, and this holds across the modeled uncertainty range
  and a separation-timing what-if.

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
  comparison isolates the government-funded difference. BRS matching
  begins after 2 years of service, per policy.
- Basic pay grows with inflation (internally consistent nominal
  model); all results are reported in **constant 2026 dollars**.
- TSP returns follow an age-based L Fund glide path parameterized
  from TSP historical data (extended to 2002 via regression-based
  synthetic backfill, R² > 0.99).
- The COLA draw is held constant within each simulated future, so it
  represents lifetime-average inflation; it is fit on rolling 30-year
  average CPI (mean ≈ 3.4%, std ≈ 1.3%). The DoD Board of
  Actuaries 2.75% assumption anchors the deterministic baseline.
- Government TSP cost is measured on an **actuarial basis** (PV of
  contributions at the 5% discount rate), not at market returns.
- Out of scope: reserve retirement, continuation pay, withdrawal
  strategy, and behavioral retention effects (a mechanical
  separation-timing sensitivity is included instead).

## Limitations

- Annual returns are drawn i.i.d. from fitted normals (no serial
  correlation or fat tails), and returns are drawn independently of
  inflation; the Bull/Bear scenarios in notebook 05 partially probe
  joint movements.
- The COLA std comes from overlapping 30-year windows, which are
  heavily autocorrelated (a century of data holds only ~3–4
  independent 30-year periods), so it is itself uncertain; the
  notebook 05 OAT bounds (1.5% / 5.0%) cover that estimation risk.
- Individual-level TSP values discount expected risky returns at 5%,
  a member's-expected-value perspective that does not haircut for
  risk (a certainty-equivalent view would value the TSP lower). The
  government-cost side avoids this via the actuarial basis.
- Death age uses SSA 2022 male tables with a normal approximation
  (std 13 yr), matching the ~83%-male active force. A female-table
  sensitivity in notebook 05 shifts the Officer/20 median ~\$31K
  further toward High-Three — within the ±10-yr OAT band — and a
  population-weighted blend moves the baseline by under \$6K, so
  gender is not modeled as a full dimension.
- Continuation pay (a mid-career BRS cash incentive) is excluded,
  which biases the comparison slightly against BRS.

Full assumptions and data provenance are documented in
[CLAUDE.md](CLAUDE.md).
