# Beyond the Pension Cliff

**Monte Carlo Analysis of U.S. Military Retirement Systems**

This project compares lifetime retirement outcomes under the U.S.
military's legacy **High-Three** pension and the **Blended
Retirement System (BRS)** introduced in 2018. It uses *Monte Carlo
simulation* — running tens of thousands of randomized possible
futures and reading the spread of outcomes, rather than betting on a
single forecast. The analysis operates at two levels:

1. **Individual** — lifetime retirement value (the value today of
   decades of future pension payments, plus the present value of the
   member's retirement-savings balance) across three career profiles
   (Enlisted, Officer, Prior-Enlisted Officer) and 52 career-length
   scenarios spanning career lengths up to 40 years for officers and
   30 for enlisted.
2. **Fiscal** — expected government cost per person who joins, and
   aggregate Department of Defense (DoD) cost per yearly intake of
   new members, weighted by how likely members are to separate at
   each career length.

> The **Key terms** section below defines the military and
> statistics vocabulary used throughout this README.

Full modeling specifications and data provenance are documented in
[CLAUDE.md](CLAUDE.md).

## Key terms

**Military / retirement terms**

| Term | Plain meaning |
|---|---|
| **High-Three** | The pre-2018 ("legacy") pension: 2.5% × years of service × the average of your highest 36 months of basic pay. Pays nothing unless you serve 20 years. No government TSP contributions. |
| **BRS** (Blended Retirement System) | The 2018 system: a smaller 2.0% pension multiplier, *plus* government contributions to your TSP. |
| **TSP** (Thrift Savings Plan) | The federal government's version of a 401(k) retirement account. |
| **Basic pay** | Military base salary. Excludes allowances (housing, subsistence, etc.). |
| **YOS** | Years of service. |
| **COLA** | Cost-of-living adjustment — the inflation rate that, in this model, drives yearly pay growth, the pension's annual increase, and the conversion to 2026 dollars. |
| **Separation** | Leaving the service. In common military usage this refers to departing before 20 years (20+ is "retirement"), but this model uses "separation" for leaving at any career length. |
| **Accession / entrant / cohort** | A person who joins in a given year; a cohort is one year's intake of new members. |
| **Pension cliff** ("20-year cliff") | Under *both* systems you earn no pension unless you reach 20 years of service. Under High-Three that meant leaving with nothing; BRS softens the cliff by adding portable TSP contributions (which vest at 2 years). |
| **Vesting** | The point at which a benefit becomes yours to keep. |
| **DoD / DFAS** | Department of Defense / Defense Finance and Accounting Service (publishes military pay tables). |

**Statistics / finance terms**

| Term | Plain meaning |
|---|---|
| **Monte Carlo simulation** | Instead of one prediction, run many thousands of randomized possible futures (here 20,000) and look at the full range of outcomes. |
| **NPV / present value** | Present value (PV) is the value *today* of money received over future years — a dollar paid 30 years from now is worth less than one now. Net present value (NPV) is the same idea applied across a whole stream of payments, netting any costs against benefits. |
| **Discount rate** | The rate used to convert future dollars into today's value (5% here). It reflects the *time value of money*: a dollar in hand today is worth more than a dollar years from now because you could invest it in the meantime. This is separate from inflation — even with zero inflation, future money is still worth less today because of that lost earning opportunity. |
| **Constant 2026 dollars** | Every figure is inflation-adjusted to 2026 purchasing power, so amounts across different years are comparable. |
| **Median (P50)** | The middle outcome: half the simulated futures come out better, half worse. |
| **P10–P90 band** | The range from the 10th to the 90th percentile — the middle 80% of simulated outcomes (a measure of uncertainty). |
| **Deterministic** | A single calculation with all assumptions fixed — no randomness. The baseline before simulation. |
| **Stochastic** | Having built-in randomness; the simulated part of the model. |

## The policy question

Under High-Three, a service member who separates before 20 years of
service receives **no** retirement benefit — the "pension cliff."
Historically only ~19% of enlisted members and ~41% of officers reach
20 years. BRS trades a smaller pension multiplier (2.0% vs 2.5% per
year of service) for government TSP contributions (1% automatic +
up to 4% matching) that vest at 2 years and are portable (you keep
them even if you leave before 20 years). The simulation quantifies
who gains, who loses, and what it costs DoD.

The choice itself is now historical. BRS took effect January 1,
2018: members already serving with fewer than 12 years had a
one-time window during 2018 to opt in or stay under High-Three, and
everyone who has joined since is enrolled in BRS automatically. So
this is no longer a decision aid for someone weighing the two
systems. It is still useful in two ways — retrospectively, for those
who made (or live with) the 2018 choice to see how it is likely to
play out, and as policy evaluation: whether the reform is actually
saving the government money, how much, and whether those savings are
durable or a further adjustment may eventually be warranted.

## Headline findings (baseline assumptions)

- **Short/medium careers (< 20 YOS):** BRS yields strictly higher
  lifetime value in every scenario and essentially every draw — it
  is the only retirement benefit these members get.
- **20+ year careers:** High-Three yields higher lifetime value at
  the median in every base-case scenario — worth **\$99K to \$310K
  more to the member** than BRS, depending on profile and length —
  and the gap *grows* with career length, though a sustained bull
  market can flip it.
- **Sensitivity:** COLA (inflation) is the largest driver (\~\$234K
  range at the **Officer/20 anchor** — the officer-who-serves-20-years
  reference case used throughout), narrowly ahead of TSP returns
  (\~\$216K); the discount rate matters least.
- **Government cost:** BRS is unambiguously cheaper for DoD —
  roughly **10.5–12.5% less per entrant** (about \$95K less per
  officer, \$24K less per enlisted member), or ~\$5.1B less per
  annual accession cohort, and it stays cheaper across the modeled
  uncertainty range and a separation-timing what-if.
- **Where the money goes:** Only ~1–4% of DoD's retirement
  spending reaches the majority who serve fewer than 20 years; the
  savings come from the smaller pension BRS pays each career retiree
  (12–14% less), which outweighs the cost of the new TSP
  contributions BRS pays to all members.
- **The two-sided story:** BRS spread the benefit across the ~80%
  who previously got nothing and cut DoD's costs — financed largely
  by the career force, whose 20+ year members are \$99–310K worse
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
from the underlying individual funds.

### 02 — Pay profiles

Builds the year-by-year basic pay series for three career
profiles — Enlisted (entry age 18), Commissioned Officer (entry
22), Prior-Enlisted Officer (enlists at 18, commissions at 26) —
and computes the High-Three pension base for every
(profile, separation-year) combination. Each profile is evaluated at
two-year intervals up to a maximum career length of 40 years for
officers and 30 years for enlisted, producing 52 scenarios in total.

### 03a — Deterministic baseline

The center-path calculation under both systems, with everything
fixed: 2.75% COLA / pay growth (the DoD actuaries' long-term
assumption), 5% discount rate, historical-mean TSP returns, median
male life expectancy. Its purpose is to validate the pension and
TSP math transparently (there is a step-by-step Officer/20-YOS
walkthrough) before adding randomness. Headline: at Officer/20,
High-Three comes out ahead by about **\$110K**, in constant 2026
dollars.

### 03b — Monte Carlo

Adds the three stochastic variables — TSP returns (year-by-year
draws per glide-path fund — the standard target-date approach that
automatically shifts from higher-risk to lower-risk funds as
retirement nears), COLA (one draw per iteration, driving pay growth,
the pension COLA, and the 2026-\$ deflator), and death
age — at 20,000 iterations per scenario, with a quantitative
convergence check (confirming that running more simulations would
not move the answer: 20K vs 40K shift < 1% of the P10–P90 spread).
Key design choice: BRS and High-Three TSP accounts share the same
return draws, so the difference isolates contributions, not luck.
Headline: at Officer/20 the median (P50) outcome favors High-Three
by about **\$155K**, but pre-20 separations favor BRS in essentially
every draw.

### 04 — Government fiscal impact

Shifts the perspective from the individual member to the
government's cost. Two decisions carry this notebook:

- **Actuarial cost basis** — the government's TSP cost is the PV
  of its contributions at the 5% discount rate, *not* the market
  value they grow to, since investment returns are earned by
  markets, not paid by DoD (using market value would overstate
  DoD's cost by 1.5 to 2.6 times).
- **Separation weighting** — each scenario is weighted by how
  likely a member is to separate at that career length (from DoD
  actuarial data), so the expected cost per *entrant* properly mixes
  the many who leave early with the few who stay for a pension.

A fiscal-side Monte Carlo adds COLA/longevity uncertainty.

### 05 — Sensitivity analysis

Three cuts:

1. A one-at-a-time (OAT) **tornado** at the Officer/20 anchor —
   which inputs shift the outcome the most.
2. Four named **scenarios** across all 52 cases (Base, Bull
   Market, Bear Market, Low Participation), each combining several
   input changes at once rather than varying one — showing that
   which system comes out ahead at 20 YOS depends on the scenario.
3. The **separation-distribution what-if** — a test of how much the
   fiscal result depends on *when* members leave. We shift the
   assumed separation timing toward earlier exits (one possible
   effect of BRS's portable benefits) and recompute: DoD's
   savings shrink but stay positive even at large shifts. This is a
   deliberate stress test, not a prediction that BRS causes earlier
   separation.

## Key modeling choices

| Decision | Rationale |
|---|---|
| Member contributes 5% under *both* systems | Isolates the government-funded difference; 5% is also the rate that earns BRS's full government match. Member behavior is varied separately in notebook 05 |
| BRS matching starts after 2 YOS | Matches actual policy; worth ~\$19K at Officer/20 because early dollars compound longest |
| Pay grows at COLA; results in constant 2026 \$ | Keeps the model internally consistent in nominal terms (pay, returns, and discounting all nominal), then deflates everything to constant 2026 dollars for comparability |
| COLA fit on rolling 30-year average CPI (mean ≈ 3.4%, standard deviation ≈ 1.3%) | One draw is held for an entire career + retirement, so it represents *lifetime-average* inflation; annual volatility would overstate it. The DoD Board of Actuaries 2.75% assumption anchors the deterministic baseline |
| Actuarial basis for government TSP cost | DoD pays contributions, not market growth |
| Age-based L Fund glide path with synthetic backfill | Realistic investor behavior; the backfill extends the funds' short return histories so they capture a fuller range of market conditions (a brief record would otherwise understate risk) |
| Out of scope: continuation pay, reserve retirement, TSP withdrawal strategy | Keeps the comparison focused on the active-duty pension and TSP difference; continuation pay's bias direction is noted in Limitations |
| Behavioral retention not modeled | Tested as a separation-timing what-if in notebook 05, not predicted as behavior |

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
under each system — plus where it sits on the pension-cliff curve.

**[▶ Try it live](https://military-retirement-monte-carlo.streamlit.app/)** — no install required.

Or run it locally:

```
streamlit run app/streamlit_app.py
```

- Inputs: career profile, entry age, an editable promotion timeline
  (shift promotion years, or top out at a rank), separation year
  (any year, not just the notebook grid), expected lifespan offset,
  and TSP contribution rate. A market-outlook setting (bull/bear
  return stress) and a discount-rate control (under "Advanced") are
  also available.
- All numbers are recomputed with the same `src/` functions the
  notebooks use; on the default timelines the app reproduces the
  committed `deterministic_results.csv` / `fiscal_results.csv`
  values exactly.
- An **"Explain my numbers"** button produces a plain-language
  narrative of the computed results. With a `GEMINI_API_KEY`
  environment variable set, the narration is generated live by
  Gemini 2.5 Flash; without one — or on any API failure — the app
  falls back to a built-in summary generated locally from the same
  numbers, so the feature always works.

## Limitations

- Each year's investment return is drawn independently from a normal
  distribution — in plain terms, the model does not make good or bad
  years cluster (no serial correlation) or build in rare extreme
  crashes and booms (no fat tails), and it draws returns
  independently of inflation; the Bull/Bear scenarios in notebook 05
  partially probe such joint movements.
- The COLA standard deviation comes from overlapping 30-year
  windows, which are heavily autocorrelated (a century of data holds
  only ~3–4 independent 30-year periods), so it is itself uncertain;
  the notebook 05 OAT bounds (1.5% / 5.0%) cover that estimation
  risk.
- Individual-level TSP values discount expected risky returns at 5%
  without applying a penalty for the risk the member takes on — they
  reflect the member's expected (average) outcome, not a risk-adjusted
  (certainty-equivalent) view, which would value the TSP lower. The
  government-cost side avoids this via the actuarial basis.
- Death age is sampled from the **empirical SSA 2022 conditional
  age-at-death distribution** (left-skewed, table-bounded), using
  the male table for the ~83%-male active force. Notebook 05 checks
  the female table separately: because women live longer on average,
  they collect more years of pension, which shifts the Officer/20
  result about 21% (≈ \$34K) further toward High-Three — still
  within the ±10-year life-expectancy range already tested. But the
  force is only ~17% female, so blending the two tables by that
  actual mix moves the Officer/20 baseline by only about a sixth of
  that — under \$6K. That effect is small enough that gender is not
  modeled as a separate dimension.
- Continuation pay (a mid-career BRS cash incentive) is excluded,
  which biases the comparison slightly against BRS.

## About this project

This project was completed independently for the University of
Michigan AI & Data Science Graduate Certificate (2026). It grew out
of the author's experience as a U.S. Coast Guard officer, who faced
the one-time legacy-vs-BRS election when the system was introduced in
2018.

The analysis and any opinions expressed are solely the author's own
and do not represent an official position or endorsement of the U.S.
Coast Guard, the Department of Defense, or any other organization.
Nothing here is financial, tax, or retirement advice.
