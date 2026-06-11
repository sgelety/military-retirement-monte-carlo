# Beyond the Pension Cliff: Monte Carlo Analysis of Military Retirement Systems

## Project Overview

This project uses Monte Carlo simulation to compare lifetime retirement outcomes under the U.S. military's legacy High-Three retirement system and the Blended Retirement System (BRS), implemented in 2018. The analysis operates at two levels: individual lifetime retirement earnings across representative career profiles, and aggregate fiscal impact on the Department of Defense.

The project is implemented in Python using Jupyter Notebooks in VS Code.

---

## Key Modeling Decisions

**Two retirement systems being compared:**
- **High-Three (legacy):** 2.5% × YOS × average of highest 36 months basic pay. Requires 20 years to vest. No government TSP contributions.
- **BRS:** 2.0% multiplier (same pension base). Adds government TSP contributions: 1% automatic + up to 4% matching. TSP vests at 2 years and is portable.

**Three career profiles:**
- **Enlisted:** Grade progression defined in `PromotionTiming.csv`. Entry age 18.
- **Commissioned Officer:** Grade progression from RAND DOPMA data in `PromotionTiming.csv`. Entry age 22.
- **Prior-Enlisted Officer:** Assumes 8 years enlisted before commissioning. Uses `PriorEnlistedOfficer` column in `PromotionTiming.csv`. Entry age 26 at commissioning (18 at enlistment).

**Career-length scenarios (YOS):** Uniform 2-year spacing spanning the statutory service maxima (officer 40 years, enlisted 30), per profile — Officers and PEOs: 4–40 (19 scenarios each); Enlisted: 4–30 (14 scenarios). Total: 52 valid (profile, sep_yos) combinations. Officer/40 separates at age 62 (> 60); the TSP growth-to-60 step is a handled no-op there (balance at separation taken as-is).

**TSP contribution rates:** Member contributes 5% of basic pay under **both** systems — this is held constant to isolate the government-funded difference. BRS adds a 1% automatic government contribution from entry plus matching beginning after 2 years of service (6% total in YOS 1–2, 10% from YOS 3). Matching follows the statutory tier schedule: dollar-for-dollar on the first 3% the member contributes, then 50¢/dollar on the next 2% (full 4% match requires a 5% contribution; e.g., a 4% contribution draws 3.5%). At the 0%/5%/10% member rates used in all committed results the tiers equal the simpler min(rate, 4%), so correcting the schedule (2026-06-11) changed no notebook output — it only affects intermediate rates in the app's slider. High-Three has no government contribution (5% member only). Functions: `brs_govt_rate(yos, member_rate)` / `brs_total_rate(yos, member_rate)` in `src/tsp_calcs.py`; steady-state constants `BRS_CONTRIB_RATE = 0.10`, `H3_MEMBER_RATE = 0.05`.

**Dollar convention:** basic pay grows at the COLA rate (military raises assumed to track inflation) — fixed 2.75% in deterministic runs, the iteration's COLA draw in Monte Carlo — making the model internally consistent in nominal terms. All reported values are deflated by the price level at separation and expressed in **constant 2026 dollars**. (A frozen 2026 pay table mixed with nominal returns/discounting was found to overstate TSP relative to the pension and produced spurious BRS sign-flips for 26+ YOS careers.)

**TSP investment return modeling — glide path approach:**
- Accumulation phase (during service): year-by-year L Fund return based on years remaining to age 60
- Growth continuation phase (separation to age 60): same glide path
- Drawdown phase (age 60+): L Income Fund return distribution
- Glide path fund mapping (synthetic backfill extends all four funds to n=24, 2002–2025):
  - ≥ 30 years to age 60 → L 2050 (mean 9.47%, std 14.87%, n=24)
  - 20–29 years → L 2040 (mean 8.93%, std 13.79%, n=24)
  - 10–19 years → L 2030 (mean 8.09%, std 11.89%, n=24)
  - < 10 years → L Income (mean 4.80%, std 3.74%, n=24)
- C Fund and G Fund used as upper/lower bound sensitivity references

**Discount rate:** 5.0% nominal for all NPV calculations. Varied in sensitivity analysis (notebook 05).

**Results framing:** Expressed as "lifetime value difference (BRS − H3)." Positive values indicate BRS yields higher lifetime value; negative values indicate High-Three yields higher lifetime value. Avoids editorializing about which system is "better."

**Presentation conventions:** Cross-profile displays (charts, pivots, printed tables) use the order Enlisted → Prior-Enlisted Officer → Officer via a `PROFILE_ORDER` constant in each notebook; computation/run loops keep their original order to preserve per-scenario seeds and MC draw sequences. Profile colors: Enlisted darkorange, PEO forestgreen, Officer steelblue. Escape `$` as `\$` in notebook markdown (paired dollars otherwise render as LaTeX math).

**Monte Carlo stochastic variables (all others held fixed within each scenario):**
1. TSP investment returns (parameterized from TSP L Fund historical data)
2. Inflation/COLA rates — one draw per iteration, held for the full career + retirement, so it represents **lifetime-average inflation**. Fit on rolling 30-year average CPI (mean ≈ 3.39%, std ≈ 1.27%; `fit_cola_stats(cpi, window=30)` on the full 1914+ history), used consistently in 03b/04/05; DoD Board of Actuaries long-term assumption (2.75%) is the deterministic baseline. Annual-inflation std (~3%) would overstate the uncertainty of a multi-decade average; overlapping-window autocorrelation makes the std estimate itself uncertain, which the nb05 OAT bounds (1.5%/5.0% ≈ historical range of 30-yr averages, 0.8%–5.4%) cover. The COLA draw also drives basic-pay growth and the 2026-$ deflator, so it is shared across all components within an iteration.
3. Life expectancy (Normal around the SSA 2022 male expected total age conditional on separation age, std 13 yr; nb05 includes a female-table sensitivity at the Officer/20 anchor via `death_age_offset` — gender is intentionally not a full model dimension since a ~17.5%-female population blend moves the baseline < $6K)

**Results reported in:** net present value at separation, expressed in constant 2026 dollars

**Explicitly out of scope:** reserve component retirement, continuation pay, TSP withdrawal strategy, behavioral retention effects of BRS (not modeled as behavior — nb05 includes a mechanical what-if sensitivity to the separation distribution, which is a sensitivity test, not a behavioral prediction)

---

## Data Files

Raw data files are in `data/raw/`. Processed outputs go to `data/processed/`.

### Processed outputs (`data/processed/`)
- `basic_pay.csv` — pay table indexed by PayGrade; columns are integer YOS breakpoints
- `promotion_timing.csv` — YOS × profile grade lookup (no SepYOS; slice at query time)
- `withdrawal_rates.csv` — YOS × component survival/withdrawal rates
- `tsp_returns.csv` — annual L Fund returns (% as floats; metadata rows stripped); L Fund columns extended back to 2002 via synthetic reconstruction using regression weights on individual funds (C, S, I, F, G); see notebook 01 section 4b
- `cpi_inflation.csv` — annual CPI index + derived year-over-year inflation rate
- `life_expectancy.csv` — SSA 2022 actuarial table
- `pay_profiles.csv` — (Profile, YOS, MonthlyPay); one row per career year per profile; **no SepYOS column** — notebooks filter with `YOS <= sep_yos` at query time
- `high_three_matrix.csv` — Profile × SepYOS matrix of High-Three monthly base values on the uniform 52-scenario grid; reference output only — downstream notebooks recompute High-3 from `pay_profiles.csv` at query time
- `deterministic_results.csv` — full lifetime value comparison under both systems for all 52 valid (profile, sep_yos) scenarios, in constant 2026 dollars (`H3Annual`/`BRSAnnual` are nominal at separation); output of 03a
- `mc_results.csv` — Monte Carlo percentile summary (p10/p25/p50/p75/p90/mean) for BRSAdv, H3Total, BRSTotal across all 52 scenarios; output of 03b
- `fiscal_results.csv` — per-scenario government cost (H3_GovtCost, BRS_GovtCost, GovtTSP_PV, DoD_Savings) plus separation-weighted expected costs per entrant by profile; output of 04
- `scenario_weights.csv` — (Profile, SepYOS, Weight) separation probabilities binned to the modeled scenarios, summing to 1 per profile; output of 04, consumed by nb05 section 4

### `BasicPay_2026.csv`
- 2026 DFAS military basic pay table
- Columns: `PayGrade`, then YOS breakpoints: 0, 2, 3, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40
- Rows: O-10 through E-1 (22 pay grades)
- Values are monthly pay in dollars (no commas — already cleaned)
- Many cells are blank where that grade/YOS combination doesn't exist

### `PromotionTiming.csv`
- Defines grade at each YOS for all three career profiles
- Columns: `YOS`, `Officer`, `Enlisted`, `PriorEnlistedOfficer`
- YOS 1–40; officer column based on RAND DOPMA data; enlisted reflects typical progression
- Officer/PEO columns deliberately top out at O-8 for late-career YOS: basic pay is capped at those YOS (the pay table flat-lines at ~$19,000/mo from YOS 34), so promoting to O-9/O-10 would not change modeled pay
- PEO column uses **O-1E/O-2E/O-3E** for YOS 9–17: officers with more than 4 years of prior enlisted service draw the higher "E" pay tables (the modeled PEO commissions after 8 enlisted years, so they qualify; an officer commissioning before 4 years would use standard O-1/O-2/O-3). No E variant exists at O-4+, so YOS 18+ is unchanged. Fixed 2026-06-11; effect is +8.6–10.7% pay in YOS 9–11, +0–3.7% in the O-3E years, shifting PEO BRSAdv +$1.6–6.2K (TSP-side only — PEO 20+ pensions unchanged since the High-3 comes from O-4+ years)
- Entry ages are model constants defined in code, not in this file: enlisted = 18, officer = 22, prior-enlisted officer = 18 (enlists) / 26 (commissions after 8 enlisted years)
- Use this to look up the correct pay grade from `BasicPay_2026.csv` at each YOS

### `ActiveDutyWithdrawalRates.csv`
- Source: DoD Office of the Actuary Technical Reference to the FY 2024 Valuation of the Military Retirement Fund
- Columns: `YOS`, `OfficerWithdrawal`, `OfficerSurvival`, `EnlistedWithdrawal`, `EnlistedSurvival`
- YOS 1–40
- For YOS 1–19: withdrawal rates represent voluntary/involuntary separations (pre-retirement)
- For YOS 20+: withdrawal rates represent non-disability retirement rates (from the same source document). The two rate types are combined into the same column since they serve the same purpose in the model — probability of separating at that YOS.
- Survival columns are the pre-calculated cumulative survival rates (probability of reaching that YOS from entry)
- Approximately 41% of officers and 19% of enlisted reach YOS 20, consistent with DoD published figures

### `TSP_FundPerformance.csv`
- Source: TSP.gov historical fund performance
- Columns: Year, L Income, L 2030, L 2035, L 2040, L 2045, L 2050, L 2055, L 2060, L 2065, L 2070, L 2075, G Fund, F Fund, C Fund, S Fund, I Fund (plus benchmark index columns)
- **Important:** First six rows are metadata — inception date, 1 year, 3 year, 5 year, 10 year, and since inception averages. Skip all six when loading annual return data. These multi-year averages can be used as sanity checks against calculated means from the annual data.
- Values are percentage strings (e.g., "12.45%") — strip % and convert to float on load
- Some L Funds have limited history due to recent inception dates — evaluate whether to exclude funds with insufficient data

### `CPI.csv`
- Source: Bureau of Labor Statistics, Series CUUR0000SA0
- Columns: `Year`, `Annual`
- 1913 to present
- Use to parameterize the inflation/COLA distribution for Monte Carlo simulation
- DoD Board of Actuaries long-term assumption (2.75%) serves as baseline reference

### `LifeExpectancy_2022.csv`
- Source: SSA Actuarial Life Tables, 2022
- Columns: `Age`, `MaleLifeExpectancy`, `MaleTotalAge`, `FemaleLifeExpectancy`, `FemaleTotalAge`
- Ages 0–119
- `MaleLifeExpectancy` = remaining years expected at that age
- `MaleTotalAge` = expected total age at death (Age + MaleLifeExpectancy)
- Use `MaleTotalAge` / `FemaleTotalAge` to draw stochastic end-of-life age in Monte Carlo simulation, conditioned on the member's age at separation

---

## Notebook Build Order

### `01_data_prep.ipynb`
Load and clean all raw data files. Output processed CSVs to `data/processed/`. Key tasks:
- Parse TSP returns (skip metadata rows, convert % strings to floats)
- Verify BasicPay table loads correctly with blank cells handled
- Confirm survival curve endpoints (~41% officer, ~19% enlisted at YOS 20)

### `02_pay_profiles.ipynb`
Build the full career pay series for each profile (one row per YOS, no scenario dimension). Compute the High-Three base (average of the 3 highest annual pay values) for each (profile, sep_yos) combination. Outputs `pay_profiles.csv` and `high_three_matrix.csv`.

### `03a_deterministic.ipynb`
Deterministic (center-path) lifetime value calculation under both systems for all 52 valid scenarios. Uses fixed COLA / pay growth (2.75%), discount rate (5.0%), glide-path L Fund means, and SSA 2022 male life expectancy; values in constant 2026 dollars. Validates the pension and TSP math before introducing stochastic variation. Outputs `deterministic_results.csv`.

### `03b_monte_carlo.ipynb`
Monte Carlo simulation adding stochastic variation to TSP returns, COLA, and life expectancy. Uses 20,000 iterations; validated via half-to-full convergence check (20K→40K shift < 1% of P10-P90 spread on Officer/20 YOS, the most volatile scenario). Report results at 10th, 25th, 50th, 75th, 90th percentiles plus mean. Outputs `mc_results.csv`.

### `04_government_fiscal.ipynb`
Scale individual results to DoD aggregate cost.
- Government TSP cost measured on **actuarial basis**: PV of contributions compounded at the 5% discount rate (not TSP market returns), matching the reference date used for pension NPV. This avoids a 1.5–2.6× overstatement of DoD's fiscal cost.
- Weight each YOS scenario by its DoD actuarial separation probability; sum to get expected government cost per entrant
- Monte Carlo section adds stochastic COLA and life expectancy (N=20,000 iterations). COLA fit on rolling 30-year average CPI, matching 03b. COLA draws are shared across all scenarios per iteration; death age is independent per scenario. The COLA draw drives pay growth, so the High-Three base and `GovtTSP_PV` are stochastic too; all values deflated to 2026 dollars per iteration.
- Convergence validated via 20K→40K half-to-full check: max shift 0.23% of P10-P90 spread (Officer per-entrant savings, most volatile metric) — PASS at 1% threshold
- Spending decomposition splits expected per-entrant cost by recipient group (≤19 vs 20+ YOS): under H3 100% of spending goes to the 20+ minority by construction; under BRS only ~1–4% reaches the <20 majority — savings come from paying retirees 12–14% less, not redistribution. Also prices the cliff in govt dollars (the 20th year adds ~$0.8–1.7M to the obligation). Caveat in-notebook: actuarial cost ≈ half the member-side value of the early-separatee TSP benefit.
- Force-level scaling uses 18,000 officer + 140,000 enlisted annual accessions; PEOs are deliberately excluded there (they enter as enlisted accessions — a separate line would double-count)
- Outputs `fiscal_results.csv` and `scenario_weights.csv`

### `05_sensitivity_analysis.ipynb`
- One-at-a-time (OAT) sensitivity analysis with tornado chart. Anchor:
  Officer/20 YOS. Reported quantity is the neutral "BRS − H3 difference"
  (no "BRS Advantage"), matching nb03b/nb04 framing.
- OAT variables and bounds: TSP return (±1 SE per fund, n=24), COLA mean
  (1.5% / 5.0%), discount rate (3% / 7%), life expectancy (±10 yr), member
  TSP contribution (0% / 10%, baseline 5%). The discarded "real pay growth"
  variable is intentionally not included.
- Female life-table sensitivity at the Officer/20 anchor via
  `death_age_offset` (+4.1 yr): median deepens ~20% toward H3, within the
  ±10-yr OAT band; gender is deliberately not a full model dimension.
- Scenario-based analysis (Base, Bull Market, Bear Market, Low Participation),
  3-panel profile plot with shared y-axis. Bull/Bear use a uniform ±2 pp
  market-regime return stress — a deliberately separate construct from the
  OAT's per-fund ±1 SE bound (regime stress vs. estimation uncertainty).
- Note: nb05 centers COLA on the rolling 30-yr average CPI mean (~3.39%),
  the same empirical basis as nb03b/nb04; nb03a's deterministic path uses
  the 2.75% actuarial assumption. This is an intentional
  empirical-vs-actuarial difference, not a discrepancy, and is why the
  Officer/20 baseline is more negative here (≈ −$154K) than nb03a's
  deterministic ≈ −$110K.

**Separation-distribution sensitivity (per-entrant only)**

Purpose: quantify how sensitive the fiscal comparison is to the assumed
separation timing — the loose end flagged at the end of nb04 (BRS may shift
separations earlier/mid-career). This is a *mechanical what-if*, NOT a
behavioral prediction. State the assumed shift explicitly in every output and
never claim BRS causes it.

Scope guardrails:
- **Per-entrant metrics ONLY** — expected H3_GovtCost, BRS_GovtCost, and
  DoD_Savings per entrant. Do NOT involve force size, accessions, or
  force-level totals. They are irrelevant to the per-entrant comparison and
  out of scope for this cut.
- Operates entirely on the modeled-scenario separation weights from nb04
  (`scenario_weights` — a per-profile pd.Series indexed by SepYOS, summing
  to 1). Per-scenario costs (`fiscal` / `deterministic_results.csv`) are
  unchanged. Do NOT re-run 03a/03b or the Monte Carlo.

The shift is defined at the **career-phase (band) level**, not at hand-picked
YOS points (the earlier `{4, 8, 10, 12, 20}` dict was arbitrary). nb05
loads nb04's persisted `scenario_weights.csv` rather than re-deriving
the binning logic.

Mechanism:
1. `apply_weight_shift(base_weights: pd.Series, adjustments: dict[int, float]) -> pd.Series`
   - `adjustments` maps SepYOS → delta.
   - Assert `abs(sum(adjustments.values())) < 1e-9` — zero-sum, so it stays a
     probability distribution.
   - Apply deltas, then assert all weights ≥ 0 (can't remove more mass than a
     YOS holds) and `sum ≈ 1`. Return the shifted Series.
2. `band_deltas_to_yos(base_weights, band_deltas, bands) -> dict[int, float]`
   - Bands are career phases: First term (≤6), Early mid (7–12),
     Late mid (13–19), Career (20+).
   - `band_deltas` maps each band → net probability mass moved (must sum to 0).
   - Each band's delta is distributed across the modeled YOS inside it in
     proportion to baseline weight, so within-phase shape is preserved and the
     shift adapts to each profile automatically. Returns a per-YOS dict for
     `apply_weight_shift`.
3. Expected per-entrant value under any weight vector:
   `(w * fiscal_profile.set_index("SepYOS")[col]).sum()` for col in
   {H3_GovtCost, BRS_GovtCost, DoD_Savings}. Identical to nb04's expected-cost
   cell, just with reshaped weights.
4. Report baseline vs scenario per-entrant DoD_Savings and the delta, per profile.

Default hypothesis scenario — `BAND_DELTAS` (magnitudes are assumptions, not
data — adjustable):
- First term (≤6): −4 pts — more retained past first term.
- Early mid (7–12): +4 pts — more mid-career separation.
- Late mid (13–19): +2 pts — more pre-20 separation.
- Career (20+): −2 pts — slightly fewer reach 20.
- Must net to zero. The same band deltas apply to all three profiles; the
  proportional distribution adapts to each profile's own weights (Enlisted
  scenarios end at YOS 28).

Presentation:
- Bar chart: baseline vs shifted separation weights per profile (1×3, shared
  y), mirroring nb04's "Separation Probability by YOS".
- Report per-entrant DoD_Savings at baseline vs full shift, with the delta and
  %, per profile. Expected cost is linear in the weights, so erosion is
  monotonic between the two endpoints by construction — no sweep plot needed
  (state the linearity in text rather than charting a straight line).

---

## Interactive App (`app/` directory)

Streamlit explorer ("your slice of the \$5B"): for one user-chosen
career it shows the member ledger (BRS − H3 difference, live
`run_scenario` Monte Carlo at N=20,000) and the government ledger
(deterministic actuarial cost under each system), plus nb03b-style
fan charts (median + P10–P90 / P25–P75 bands across every
separation year, deterministic dashed overlay, user's point
marked). The MC runs as a full curve — one seeded `run_scenario`
per YOS (`mc_curve`, seed = SEED + sep_yos), cached per input
combo (~3 s at 20K iterations; separation-slider moves are then
free). A **Market outlook** radio applies the ±2 pp return-regime
stress from nb05's Bull/Bear scenarios (returns only — the
notebook scenarios also bundle COLA/discount changes; the app
keeps discount as its own Advanced control). Outlook deliberately
does not move the government ledger (actuarial basis). Run from
repo root: `streamlit run app/streamlit_app.py`.

- **No new modeling.** `app/scenario_calcs.py` recomputes everything
  with the existing `src/` functions; member math mirrors nb03a,
  government cost mirrors nb04. On the default timelines it
  reproduces `deterministic_results.csv` and `fiscal_results.csv` to
  float precision (validated at ~1e-10).
- Separation YOS is a 1-year-step slider (4 to the statutory max):
  the 52-scenario grid only constrains the *precomputed* CSVs;
  `run_scenario` works at any integer YOS since `pay_profiles.csv`
  has every career year.
- **Entry age is user-adjustable** (17–40, per-profile defaults
  18/18/22 via per-profile widget keys): flows through to the
  glide path, growth-to-60 window, and life-expectancy lookup.
  `run_scenario` always supported it; the app just exposes it.
- **Custom promotion timelines:** the sidebar editor seeds from
  `promotion_timing.csv` pin-points; users can shift promotion years
  or delete rows ("top out at E-7"). Helpers live in
  `src/pay_builder.py`; validation rejects non-monotonic timelines
  and grade/YOS combos the pay table doesn't support. Rank is
  asserted by the user, never predicted. The pay table is filled
  through YOS 40 for every grade, so held junior grades price fine.
- Force-wide context stats (spending split, share reaching the
  user's YOS, expected per-entrant savings) come from nb04's
  persisted `fiscal_results.csv` + `scenario_weights.csv` and always
  describe the *standard* profiles — a custom timeline changes the
  user's ledgers only.
- **Explanation layer** (`app/explain.py`), two tiers so the button
  always works: (1) Gemini 2.5 Flash via REST (free API tier; reads
  `GEMINI_API_KEY`/`GOOGLE_API_KEY` from env) narrating the computed
  numbers under the neutral framing rules, never inventing figures;
  (2) a deterministic built-in summary generated locally from the
  same numbers as the fallback on any API failure / missing key —
  chosen so a public deployment never has a dead or billing-risky
  feature. The Anthropic API is deliberately not used (user
  decision: no paid key; Gemini free tier + built-in fallback).
- System colors in the app: H3 dimgray, BRS crimson — deliberately
  disjoint from the profile palette.
- Streamlit markdown treats `$...$` as LaTeX exactly like notebook
  markdown: every dollar amount rendered via `st.markdown` /
  `st.caption` must pass through the app's `esc_md` helper
  (`st.metric` and dataframes are plain text — no escaping there).
- A plain-language "How this works" expander sits under the title
  (lay explanation of the two systems, the 20K-future simulation,
  the 2026-$ NPV convention, the equal-contribution design, and
  exclusions); the technical "Model assumptions & limitations"
  expander at the bottom remains the fine print. Keep both in sync
  with any model change.
- A rank-timeline strip (horizontal bar of grade tenures, E grades
  navajowhite / O grades lightsteelblue) sits under the snapshot
  metrics; a native multi-handle slider for promotion input was
  considered and rejected (needs a custom JS component).
- Headless testing: `streamlit.testing.v1.AppTest` runs the app
  script and surfaces exceptions (`st.data_editor` returns its
  seeded default there, which exercises the typical-timing path).

---

## Reusable Functions (src/ directory)

Keep these as importable .py modules, not inline in notebooks:
- `pension_calcs.py` — `high_three_base`, `annual_pension_high3`, `annual_pension_brs` ✓
- `pay_builder.py` — `lookup_pay`, `build_pay_series` (extracted from nb02 unchanged; nb02 imports them), plus app-facing timeline helpers `promotion_points`, `grades_from_points`, `pay_series_from_grades` ✓
- `tsp_calcs.py` — `tsp_at_separation(pay, entry_age, means, rate)` where `rate` is a float or callable(yos), `tsp_grow_to_60`, `compute_fund_means`, `select_fund`, `brs_govt_rate`, `brs_total_rate`; exports `BRS_CONTRIB_RATE=0.10` and `H3_MEMBER_RATE=0.05` (steady-state) ✓
- `utils.py` — `npv_pension`, `pv_lump_sum`, `percentile_summary` ✓
- `monte_carlo.py` — `fit_fund_stats`, `fit_cola_stats`, `npv_pension_vec`, `grown_pay_matrix`, `high3_base_vec`, `govt_tsp_pv_vec`, `run_scenario(..., member_rate=0.05)` (outputs constant 2026 $); exports `DEATH_AGE_STD=13.0` ✓

---

## Libraries

- `numpy`, `scipy` — numerical computation, statistical distributions
- `pandas` — data manipulation
- `matplotlib` — visualization
- `streamlit` — interactive app (`app/` only)
- `requests` — Gemini REST call in `app/explain.py` only
- Pinned versions in `requirements.txt` (seaborn/statsmodels turned out
  not to be needed and are not installed)
