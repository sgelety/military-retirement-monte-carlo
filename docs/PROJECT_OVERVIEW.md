# Project Overview: Beyond the Pension Cliff

A narrative walkthrough of the analysis — where it started, the
decisions made along the way, and the questions it answers. For
build instructions and data provenance, see the
[README](../README.md); for full modeling specifications, see
[CLAUDE.md](../CLAUDE.md).

## The questions

The 2018 Blended Retirement System (BRS) traded a smaller pension
(2.0% vs 2.5% multiplier per year of service) for portable,
government-funded TSP contributions. The project answers two
questions that point in opposite directions, which is the core
tension of the analysis:

1. **Individual:** For a service member, which system yields more
   lifetime retirement value — and how does the answer depend on
   career length, career type, and luck (markets, inflation,
   longevity)?
2. **Fiscal:** What does BRS do to the government's retirement
   bill per entrant and per annual accession cohort?

The hook for a lay audience: under the legacy High-Three system,
~81% of enlisted members and ~59% of officers left with *nothing*.
BRS gives nearly everyone something — but pays career members
less. Who wins, who loses, and what does it cost?

## The pipeline

### 01 — Data prep

Loads and validates six raw sources: the 2026 DFAS pay table,
promotion timing (RAND DOPMA-based), DoD actuarial
withdrawal/survival rates, TSP fund returns, CPI back to 1913, and
SSA 2022 life tables. The notable methodological piece:
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
Headline: Officer/20 P50 ≈ **−\$154K**, but pre-20 separations
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
Headline: BRS saves **\$95K/officer, \$24K/enlisted per entrant
(~10–13%)**, ~\$5.1B per annual accession cohort, positive across
the entire p10–p90 range.

### 05 — Sensitivity analysis

Three cuts:

1. A one-at-a-time **tornado** at the Officer/20 anchor — which
   inputs move the answer most.
2. Four named **scenarios** across all 52 cases (Base, Bull
   Market, Bear Market, Low Participation) — showing the 20-YOS
   sign is regime-dependent.
3. The **separation-distribution what-if** — if BRS shifts people
   toward earlier separation, DoD's savings erode ~8–19% but never
   flip sign. A mechanical bound, deliberately not a behavioral
   prediction.

## Decisions made along the way (and why)

| Decision | Rationale |
|---|---|
| Member contributes 5% under *both* systems | Isolates the government-funded difference; member behavior varied separately in nb05 |
| BRS matching starts after 2 YOS | Matches actual policy; worth ~\$19K at Officer/20 because early dollars compound longest |
| Pay grows at COLA; results in constant 2026 \$ | The original frozen pay table mixed with nominal returns overstated TSP and produced a spurious "BRS recovers for 30+ year careers" result — 12 of 49 scenarios flipped sign when fixed |
| COLA fit on rolling 30-year average CPI (mean 3.39%, std 1.27%) | One draw is held for an entire career + retirement, so it represents *lifetime-average* inflation; annual volatility overstated it, and post-1985 was rejected because its own 2022 data point is a 3.6σ event under that fit |
| Actuarial basis for government TSP cost | DoD pays contributions, not market growth |
| Glide-path returns with synthetic backfill | Realistic investor behavior; backfill fixes survivorship bias in fund history |
| Neutral "BRS − H3 difference" framing | Avoids editorializing about which system is "better" |
| Out of scope: continuation pay, reserve retirement, behavioral retention | Documented in README limitations with bias direction stated |

## Where the answers stand

- **Short/medium careers (< 20 YOS):** BRS wins in every scenario
  and essentially every draw — it is the only retirement benefit
  these members get.
- **20+ year careers:** High-Three wins at the median in every
  base-case scenario (−\$98K to −\$294K depending on profile and
  length), and the gap *grows* with career length. Only a
  sustained bull market flips it.
- **Sensitivity:** COLA is the largest driver (~\$222K range at
  Officer/20), narrowly ahead of TSP returns (~\$211K); the
  discount rate matters least.
- **Government:** BRS is unambiguously cheaper — ~10–13% per
  entrant, ~\$5.1B per cohort, robust to the full uncertainty
  range and to plausible separation-timing shifts.
- **Where the money goes:** BRS barely redistributes on a cost
  basis — only ~1–4% of DoD's retirement spending reaches the
  ≤19-YOS majority; the savings come from paying retirees 12–14%
  less per retiree. The 20th year of service still raises DoD's
  obligation by \$0.8–1.7M, so BRS softens the government-side
  cliff only modestly.
- **The two-sided story** (the poster's thesis): BRS spread the
  benefit across the ~80% who previously got nothing and cut DoD's
  costs — financed largely by the career force, whose 20+ year
  members are \$100–290K worse off at the median.
