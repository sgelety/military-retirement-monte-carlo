# Beyond the Pension Cliff

**Monte Carlo Analysis of U.S. Military Retirement Systems**

This project compares lifetime retirement outcomes under the U.S.
military's legacy **High-Three** retirement system and the **Blended
Retirement System (BRS)** introduced in 2018, using Monte Carlo
simulation. The analysis operates at two levels:

1. **Individual** — lifetime retirement value (pension NPV + TSP
   present value) across three career profiles (Enlisted, Officer,
   Prior-Enlisted Officer) and 52 career-length scenarios spanning
   the statutory service maxima (4–40 officer, 4–30 enlisted).
2. **Fiscal** — expected government cost per entrant and aggregate
   DoD cost per annual accession cohort, weighted by actuarial
   separation probabilities.

Full modeling specifications and data provenance are documented in
[CLAUDE.md](CLAUDE.md).

## The policy question

Under High-Three, a service member who separates before 20 years of
service receives **no** retirement benefit — the "pension cliff."
Historically only ~19% of enlisted members and ~41% of officers reach
20 years. BRS trades a smaller pension multiplier (2.0% vs 2.5% per
year of service) for government TSP contributions (1% automatic +
up to 4% matching) that vest at 2 years and are portable. The
simulation quantifies who gains, who loses, and what it costs DoD.

The hook for a lay audience: under High-Three, ~81% of enlisted
members and ~59% of officers left with *nothing*. BRS gives nearly
everyone something — but pays career members less. Who wins, who
loses, and what does it cost?

## Headline findings (baseline assumptions)

- **Short/medium careers (< 20 YOS):** BRS yields strictly higher
  lifetime value in every scenario and essentially every draw — it
  is the only retirement benefit these members get.
- **20+ year careers:** High-Three yields higher lifetime value at
  the median in every base-case scenario (−\$99K to −\$310K
  depending on profile and length), and the gap *grows* with career
  length. The result is most sensitive to TSP return and inflation
  assumptions, and a sustained bull market can flip it.
- **Sensitivity:** COLA is the largest driver (~\$234K range at the
  Officer/20 anchor), narrowly ahead of TSP returns (~\$216K); the
  discount rate matters least.
- **Government cost:** BRS is unambiguously cheaper — roughly
  **10.5–12.5% less per entrant** (~\$95K/officer, ~\$24K/enlisted),
  ~\$5.1B per annual accession cohort, and positive across the
  modeled uncertainty range and a separation-timing what-if.
- **Where the money goes:** Only ~1–4% of DoD's retirement
  spending reaches the ≤19-YOS majority; the savings come from
  the smaller pension BRS pays each career retiree (12–14%
  less), which outweighs the cost of the new TSP contributions
  BRS pays to all members. The 20th year of service
  still raises DoD's High-Three obligation by \$1.0–1.7M per
  member, so BRS softens the government-side cliff only modestly.
- **The two-sided story:** BRS spread the benefit across the ~80%
  who previously got nothing and cut DoD's costs — financed largely
  by the career force, whose 20+ year members are \$100–290K worse
  off at the median.

See the notebooks for exact figures, uncertainty bands, and
sensitivity analyses.

## How the analysis works

Run the notebooks in order (01 → 02 → 03a → 03b → 04 → 05); each
reads the processed CSVs written by its predecessors. All random
draws are seeded, so results are reproducible.

### 01 — Data prep

Loads and validates six raw sources: the 2026 DFAS pay table,
promotion timing (RAND DOPMA-based), DoD actuarial
withdrawal/survival rates, TSP fund returns, CPI back to 1913, and
SSA 2022 life tables. The notable methodological piece is the
**synthetic L Fund backfill** — the target-date funds only have
14–20 years of history, so regression recovers each fund's implied
asset allocation (R² > 0.99) and reconstructs returns back to 2002
from the underlying individual funds. This matters because
L 2050's short window missed the dot-com bust and understated its
risk.

### 02 — Pay profiles

Builds the year-by-year basic pay series for three career
archetypes — Enlisted (entry age 18), Commissioned Officer (entry
22), Prior-Enlisted Officer (enlists at 18, commissions at 26) —
and computes the High-Three pension base for every
(profile, separation-year) combination. The scenario grid is
uniform 2-year spacing to the statutory service maxima (4–40
officer/PEO, 4–30 enlisted): 52 scenarios total.

### 03a — Deterministic baseline

The center-path calculation under both systems, with everything
fixed: 2.75% COLA / pay growth (the DoD actuaries' long-term
assumption), 5% discount rate, historical-mean TSP returns, median
male life expectancy. Its purpose is to validate the pension and
TSP math transparently (there is a step-by-step Officer/20-YOS
walkthrough) before adding randomness. Headline: Officer/20 reads
**−\$110K** (High-Three ahead), in constant 2026 dollars.

### 03b — Monte Carlo

Adds the three stochastic variables — TSP returns (year-by-year
draws per glide-path fund), COLA (one draw per iteration, driving
pay growth, the pension COLA, and the 2026-\$ deflator), and death
age — at 20,000 iterations per scenario, with a quantitative
convergence check (20K vs 40K shift < 1% of the P10–P90 spread).
Key design choice: BRS and H3 TSP accounts share the same return
draws, so the difference isolates contributions, not luck.
Headline: Officer/20 P50 ≈ **−\$155K**, but pre-20 separations
favor BRS in essentially every draw.

### 04 — Government fiscal impact

Flips the lens to DoD's cost. Two decisions carry this notebook:

- **Actuarial cost basis** — the government's TSP cost is the PV
  of its contributions at the 5% discount rate, *not* the market
  value they grow to, since investment returns are earned by
  markets, not paid by DoD (using market value would overstate
  DoD's cost 1.5–2.6×).
- **Separation weighting** — each scenario is weighted by its DoD
  actuarial probability, so the expected cost per *entrant*
  properly mixes the many early separatees with the few
  pensioners.

A fiscal-side Monte Carlo adds COLA/longevity uncertainty.

### 05 — Sensitivity analysis

Three cuts:

1. A one-at-a-time **tornado** at the Officer/20 anchor — which
   inputs move the answer most.
2. Four named **scenarios** across all 52 cases (Base, Bull
   Market, Bear Market, Low Participation) — showing the 20-YOS
   sign is regime-dependent.
3. The **separation-distribution what-if** — if BRS shifts people
   toward earlier separation, DoD's savings erode but never flip
   sign at plausible magnitudes. A mechanical bound, deliberately
   not a behavioral prediction.

## Key modeling choices

| Decision | Rationale |
|---|---|
| Member contributes 5% under *both* systems | Isolates the government-funded difference; member behavior is varied separately in notebook 05 |
| BRS matching starts after 2 YOS | Matches actual policy; worth ~\$19K at Officer/20 because early dollars compound longest |
| Pay grows at COLA; results in constant 2026 \$ | An internally consistent nominal model; a frozen pay table mixed with nominal returns overstated TSP and produced spurious sign-flips for long careers |
| COLA fit on rolling 30-year average CPI (mean ≈ 3.4%, std ≈ 1.3%) | One draw is held for an entire career + retirement, so it represents *lifetime-average* inflation; annual volatility would overstate it. The DoD Board of Actuaries 2.75% assumption anchors the deterministic baseline |
| Actuarial basis for government TSP cost | DoD pays contributions, not market growth |
| Age-based L Fund glide path with synthetic backfill | Realistic investor behavior; the backfill fixes survivorship bias in the funds' short return history |
| Neutral "BRS − H3 difference" framing | Avoids editorializing about which system is "better" |
| Out of scope: continuation pay, reserve retirement, withdrawal strategy, behavioral retention | A mechanical separation-timing sensitivity is included instead; bias direction is stated in Limitations |

## Repository structure

| Path | Contents |
|---|---|
| `notebooks/01_data_prep.ipynb` | Load/clean raw data; synthetic L Fund backfill |
| `notebooks/02_pay_profiles.ipynb` | Career pay series; High-Three base matrix |
| `notebooks/03a_deterministic.ipynb` | Center-path lifetime values (validates the math) |
| `notebooks/03b_monte_carlo.ipynb` | Stochastic returns, COLA, life expectancy (N=20,000) |
| `notebooks/04_government_fiscal.ipynb` | DoD cost per entrant and per cohort |
| `notebooks/05_sensitivity_analysis.ipynb` | OAT tornado, scenario analysis, separation what-if |
| `src/` | Importable modules: pension/TSP math, pay-series builder, NPV utilities, MC engine |
| `app/` | Interactive Streamlit explorer (see below) |
| `data/raw/` | Source data (DFAS pay table, DoD actuarial rates, TSP returns, CPI, SSA life tables) |
| `data/processed/` | Cleaned inputs and result CSVs produced by the notebooks |

## Setup

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Open the notebooks in VS Code or Jupyter and select the `.venv`
kernel.

## Interactive explorer

A Streamlit app shows both sides of the ledger for any single
career — what the system change is worth to the member (live
Monte Carlo, N=20,000) and what that career costs the government
under each system — plus where it sits on the pension-cliff curve:

```
streamlit run app/streamlit_app.py
```

- Inputs: career profile, separation year (any year, not just the
  notebook grid), entry age, TSP contribution rate, expected
  lifespan offset, and an editable promotion timeline (shift
  promotion years, or top out at a rank).
- All numbers are recomputed with the same `src/` functions the
  notebooks use; on the default timelines the app reproduces the
  committed `deterministic_results.csv` / `fiscal_results.csv`
  values exactly.
- An **"Explain my numbers"** button produces a plain-language
  narrative of the computed results under the project's neutral
  framing rules. With a `GEMINI_API_KEY` environment variable set
  (Google's free API tier), the narration is generated live by
  Gemini 2.5 Flash; without one — or on any API failure — the app
  falls back to a built-in summary generated locally from the same
  numbers, so the feature works offline and costs nothing.

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
- Death age is sampled from the **empirical SSA 2022 conditional
  age-at-death distribution** (left-skewed, table-bounded), using
  the male table for the ~83%-male active force. A female-table
  sensitivity in notebook 05 deepens the Officer/20 median ~21%
  toward High-Three — within the ±10-yr OAT band — and a
  population-weighted blend moves the baseline by under \$6K, so
  gender is not modeled as a full dimension.
- Continuation pay (a mid-career BRS cash incentive) is excluded,
  which biases the comparison slightly against BRS.
