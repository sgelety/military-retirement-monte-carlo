"""Numeric backend for the interactive BRS explorer app.

No new modeling lives here. Every quantity is recomputed with
the project's src/ functions on a (possibly user-customized)
pay series:

- deterministic lifetime values mirror notebook 03a
  (fixed 2.75% COLA / pay growth, 5% discount, glide-path
  L Fund means, SSA 2022 male life expectancy)
- the Monte Carlo at the selected point is src.monte_carlo
  .run_scenario, identical to notebook 03b
- government costs use notebook 04's actuarial basis
  (pension NPV; govt TSP contributions compounded at the
  discount rate)

All dollar outputs are NPV at separation in constant 2026 $.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from monte_carlo import (  # noqa: E402
    fit_cola_stats,
    fit_fund_stats,
    govt_tsp_pv_vec,
    run_scenario,
)
from pay_builder import (  # noqa: E402
    grades_from_points,
    pay_series_from_grades,
    promotion_points,
)
from pension_calcs import (  # noqa: E402
    annual_pension_brs,
    annual_pension_high3,
    high_three_base,
)
from tsp_calcs import (  # noqa: E402
    brs_total_rate,
    compute_fund_means,
    tsp_at_separation,
    tsp_grow_to_60,
)
from utils import (  # noqa: E402
    npv_pension,
    percentile_summary,
    pv_lump_sum,
)

PROCESSED = ROOT / "data" / "processed"

PROFILES = ["Enlisted", "PriorEnlistedOfficer", "Officer"]
PROFILE_LABELS = {
    "Enlisted": "Enlisted",
    "PriorEnlistedOfficer": "Prior-Enlisted Officer",
    "Officer": "Officer",
}
ENTRY_AGE = {
    "Officer": 22,
    "Enlisted": 18,
    "PriorEnlistedOfficer": 18,
}
PROFILE_MAX_YOS = {
    "Officer": 40,
    "Enlisted": 30,
    "PriorEnlistedOfficer": 40,
}
# Per-year survival column for the "% serve N+ years" stat. PEOs
# are modeled on the officer separation schedule (their scenario
# weights are identical to Officer).
SURVIVAL_COL = {
    "Officer": "OfficerSurvival",
    "PriorEnlistedOfficer": "OfficerSurvival",
    "Enlisted": "EnlistedSurvival",
}
MIN_SEP_YOS = 4

# Deterministic baseline assumptions (match notebook 03a)
COLA_RATE = 0.0275
DISCOUNT_RATE = 0.05
COLA_WINDOW = 30
SEED = 42


def load_inputs():
    """Load processed data and fit input distributions."""
    basic_pay = pd.read_csv(
        PROCESSED / "basic_pay.csv", index_col="PayGrade"
    )
    basic_pay.columns = basic_pay.columns.astype(int)
    promotion = pd.read_csv(
        PROCESSED / "promotion_timing.csv"
    ).set_index("YOS")
    tsp_returns = pd.read_csv(PROCESSED / "tsp_returns.csv")
    cpi = pd.read_csv(PROCESSED / "cpi_inflation.csv")
    life_exp = pd.read_csv(
        PROCESSED / "life_expectancy.csv"
    )
    fiscal = pd.read_csv(PROCESSED / "fiscal_results.csv")
    weights = pd.read_csv(
        PROCESSED / "scenario_weights.csv"
    )
    withdrawal = pd.read_csv(
        PROCESSED / "withdrawal_rates.csv"
    ).set_index("YOS")
    return {
        "basic_pay": basic_pay,
        "promotion": promotion,
        "life_exp": life_exp,
        "fiscal": fiscal,
        "weights": weights,
        "withdrawal": withdrawal,
        "fund_means": compute_fund_means(tsp_returns),
        "fund_stats": fit_fund_stats(tsp_returns),
        "cola_stats": fit_cola_stats(
            cpi, window=COLA_WINDOW
        ),
    }


def typical_points(inputs, profile):
    """Typical promotion pin-points for a profile."""
    return promotion_points(inputs["promotion"], profile)


def pay_from_points(points, max_yos, basic_pay):
    """
    Full-career pay series (2026 $) from pin-points.

    Raises ValueError for invalid timelines (non-monotonic
    YOS, unknown grade, or a grade/YOS combination the pay
    table does not support).
    """
    grades = grades_from_points(points, max_yos)
    pay = pay_series_from_grades(grades, basic_pay)
    return pay, grades


def _brs_rate_fn(member_rate):
    """BRS total contribution rate as a callable of YOS."""
    def rate(yos):
        return brs_total_rate(yos, member_rate)
    return rate


def deterministic_values(
    pay_full,
    entry_age,
    sep_yos,
    life_exp,
    fund_means,
    member_rate=0.05,
    discount_rate=DISCOUNT_RATE,
    cola_rate=COLA_RATE,
):
    """
    Deterministic lifetime + government values for one point.

    Mirrors notebook 03a's calc_lifetime (member side) and
    notebook 04's actuarial government cost. Constant 2026 $.
    """
    sep_age = entry_age + sep_yos
    pay = pay_full.loc[:sep_yos]
    pay_nom = pay * (1 + cola_rate) ** (
        pay.index.to_numpy() - 1
    )
    defl = (1 + cola_rate) ** sep_yos

    h3_base = high_three_base(pay_nom)
    life_row = life_exp.loc[
        life_exp["Age"] == sep_age
    ].squeeze()
    n_pens = life_row["MaleTotalAge"] - sep_age

    gap = max(0, 60 - sep_age)
    tsp_pv_brs = pv_lump_sum(
        tsp_grow_to_60(
            tsp_at_separation(
                pay_nom, entry_age, fund_means,
                _brs_rate_fn(member_rate),
            ),
            sep_age, fund_means,
        ),
        gap, discount_rate,
    ) / defl
    tsp_pv_h3 = pv_lump_sum(
        tsp_grow_to_60(
            tsp_at_separation(
                pay_nom, entry_age, fund_means,
                member_rate,
            ),
            sep_age, fund_means,
        ),
        gap, discount_rate,
    ) / defl

    if sep_yos >= 20:
        h3_npv = npv_pension(
            annual_pension_high3(h3_base, sep_yos),
            cola_rate, discount_rate, n_pens,
        ) / defl
        brs_npv = npv_pension(
            annual_pension_brs(h3_base, sep_yos),
            cola_rate, discount_rate, n_pens,
        ) / defl
    else:
        h3_npv = brs_npv = 0.0

    govt_tsp_pv = float(
        govt_tsp_pv_vec(
            pay, np.array([cola_rate]), sep_yos,
            discount_rate, member_rate,
        )[0]
    ) / defl

    h3_total = h3_npv + tsp_pv_h3
    brs_total = brs_npv + tsp_pv_brs
    return {
        "SepYOS": sep_yos,
        "SepAge": sep_age,
        "H3PensionNPV": h3_npv,
        "BRSPensionNPV": brs_npv,
        "H3TSP_PV": tsp_pv_h3,
        "BRS_TSP_PV": tsp_pv_brs,
        "H3Total": h3_total,
        "BRSTotal": brs_total,
        "BRSAdv": brs_total - h3_total,
        "H3_GovtCost": h3_npv,
        "GovtTSP_PV": govt_tsp_pv,
        "BRS_GovtCost": brs_npv + govt_tsp_pv,
        "DoD_Savings": h3_npv - (brs_npv + govt_tsp_pv),
    }


def deterministic_curve(
    pay_full,
    entry_age,
    life_exp,
    fund_means,
    member_rate=0.05,
    discount_rate=DISCOUNT_RATE,
):
    """
    Deterministic values at every separation YOS.

    Returns a DataFrame with one row per YOS from MIN_SEP_YOS
    through the end of pay_full.
    """
    rows = [
        deterministic_values(
            pay_full, entry_age, sep_yos, life_exp,
            fund_means, member_rate, discount_rate,
        )
        for sep_yos in range(
            MIN_SEP_YOS, int(pay_full.index.max()) + 1
        )
    ]
    return pd.DataFrame(rows)


# Market-outlook regimes: a sustained shift of all glide-path
# fund mean returns, matching notebook 05's Bear/Base/Bull
# scenario construct (regime stress, distinct from the MC's
# year-to-year randomness).
REGIME_SHIFTS = {
    "Pessimistic (−2 pp)": -0.02,
    "Historical average": 0.0,
    "Optimistic (+2 pp)": 0.02,
}

_PCTS = ["p10", "p25", "p50", "p75", "p90", "mean"]
_MC_KEYS = ["brs_adv", "h3_total", "brs_total"]


def shift_fund_stats(fund_stats, delta):
    """Fund stats with all mean returns shifted by delta."""
    return {
        f: {"mean": s["mean"] + delta, "std": s["std"]}
        for f, s in fund_stats.items()
    }


def shift_fund_means(fund_means, delta):
    """Deterministic fund means shifted by delta."""
    return {f: m + delta for f, m in fund_means.items()}


def mc_curve(
    profile,
    pay_full,
    entry_age,
    life_exp,
    fund_stats,
    cola_stats,
    member_rate=0.05,
    discount_rate=DISCOUNT_RATE,
    n_iter=20_000,
    seed=SEED,
):
    """
    Monte Carlo at every separation YOS on a pay series.

    One run_scenario call per YOS (seeded per YOS, so the
    curve is stable as sliders move). Returns a DataFrame
    with percentile columns for brs_adv / h3_total /
    brs_total plus additive component means per row.
    """
    pay_df = pd.DataFrame(
        {
            "Profile": profile,
            "YOS": pay_full.index,
            "MonthlyPay": pay_full.values,
        }
    )
    rows = []
    for sep_yos in range(
        MIN_SEP_YOS, int(pay_full.index.max()) + 1
    ):
        res = run_scenario(
            profile,
            sep_yos,
            pay_df,
            life_exp,
            fund_stats,
            cola_stats,
            {profile: entry_age},
            n_iter=n_iter,
            discount_rate=discount_rate,
            seed=seed + sep_yos,
            member_rate=member_rate,
        )
        row = {"SepYOS": sep_yos}
        for key in _MC_KEYS:
            summ = percentile_summary(res[key])
            for p in _PCTS:
                row[f"{key}_{p}"] = summ[p]
        # Means are additive across components; medians aren't.
        row["h3_pension_mean"] = float(
            res["h3_pension_npv"].mean()
        )
        row["brs_pension_mean"] = float(
            res["brs_pension_npv"].mean()
        )
        row["member_tsp_mean"] = float(
            res["h3_tsp_pv"].mean()
        )
        row["govt_tsp_mean"] = float(
            (res["brs_tsp_pv"] - res["h3_tsp_pv"]).mean()
        )
        rows.append(row)
    return pd.DataFrame(rows)


def mc_from_curve_row(row):
    """One mc_curve row as the nested dict explain.py expects."""
    out = {
        key: {p: float(row[f"{key}_{p}"]) for p in _PCTS}
        for key in _MC_KEYS
    }
    out["component_means"] = {
        "h3_pension": float(row["h3_pension_mean"]),
        "brs_pension": float(row["brs_pension_mean"]),
        "member_tsp": float(row["member_tsp_mean"]),
        "govt_tsp": float(row["govt_tsp_mean"]),
        "h3_total": float(row["h3_total_mean"]),
        "brs_total": float(row["brs_total_mean"]),
    }
    return out


def population_context(inputs, profile, sep_yos):
    """
    Force-wide context stats for the selected profile.

    The cost-weighted stats (expected costs, spending shares)
    come from notebook 04's persisted outputs
    (fiscal_results.csv, scenario_weights.csv), which are binned
    to the even modeled-scenario grid that the per-scenario
    costs live on. The "% serve N+ years" stat instead uses the
    exact per-year DoD survival curve (withdrawal_rates.csv), so
    it is correct at every integer slider value rather than
    dropping a whole bin between grid points. All describe the
    standard career profiles — not the user's custom timeline.
    """
    fiscal = inputs["fiscal"]
    weights = inputs["weights"]
    f = (
        fiscal[fiscal["Profile"] == profile]
        .set_index("SepYOS")
        .sort_index()
    )
    w = (
        weights[weights["Profile"] == profile]
        .set_index("SepYOS")["Weight"]
        .sort_index()
    )
    f = f.loc[w.index]

    exp_h3 = float((w * f["H3_GovtCost"]).sum())
    exp_brs = float((w * f["BRS_GovtCost"]).sum())
    pre20 = w.index < 20
    brs_spend = w * f["BRS_GovtCost"]
    share_pre20_members = float(w[pre20].sum())
    share_pre20_spend = float(
        brs_spend[pre20].sum() / brs_spend.sum()
    )
    # Share serving sep_yos+ years = probability of still being
    # in service at the start of year sep_yos = survival after
    # year (sep_yos - 1). Exact at every integer YOS, unlike the
    # binned weights tail, which steps a whole bin at a time.
    surv = inputs["withdrawal"][SURVIVAL_COL[profile]]
    reach_sep = float(surv.loc[sep_yos - 1])

    return {
        "expected_h3_cost": exp_h3,
        "expected_brs_cost": exp_brs,
        "expected_savings": exp_h3 - exp_brs,
        "share_pre20_members": share_pre20_members,
        "share_pre20_spend": share_pre20_spend,
        "share_reaching_sep": reach_sep,
    }
