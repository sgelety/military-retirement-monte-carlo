"""Monte Carlo simulation for BRS vs. High-Three comparison.

Dollar convention: basic pay grows at each iteration's COLA
draw (military raises are assumed to track inflation), pension
COLA uses the same draw, and all outputs are deflated by the
price level at separation — i.e., reported in constant
entry-year (2026) dollars.
"""

import numpy as np

from pension_calcs import (
    annual_pension_brs,
    annual_pension_high3,
)
from tsp_calcs import (
    MEMBER_RATE,
    _GLIDE_PATH,
    brs_govt_rate,
    brs_total_rate,
    select_fund,
)

# Approximate std dev of age at death for males conditioned on
# reaching middle age; consistent with SSA 2022 mortality tables.
DEATH_AGE_STD = 13.0


def fit_fund_stats(tsp_df):
    """
    Return mean and std (decimal) for each glide-path L Fund.

    Parameters
    ----------
    tsp_df : pd.DataFrame
        Annual TSP returns (% as floats, one row per year).

    Returns
    -------
    dict  {fund: {"mean": float, "std": float}}
    """
    funds = [f for _, f in _GLIDE_PATH]
    return {
        f: {
            "mean": float(
                tsp_df[f].dropna().values.mean() / 100
            ),
            "std": float(
                tsp_df[f].dropna().values.std(ddof=1) / 100
            ),
        }
        for f in funds
    }


def fit_cola_stats(cpi_df):
    """
    Return mean and std (decimal) of historical CPI inflation.

    Parameters
    ----------
    cpi_df : pd.DataFrame
        Inflation column in percent (e.g., 3.2 means 3.2%).

    Returns
    -------
    dict  {"mean": float, "std": float}
    """
    rates = cpi_df["Inflation"].dropna().values / 100.0
    return {
        "mean": float(rates.mean()),
        "std": float(rates.std(ddof=1)),
    }


def grown_pay_matrix(pay_series, cola_arr):
    """
    Nominal monthly pay by service year under pay growth.

    Pay in YOS y is the 2026 table value times
    (1 + cola)^(y - 1), so year 1 is at the 2026 level.

    Parameters
    ----------
    pay_series : pd.Series  index=YOS, values=monthly pay (2026 $)
    cola_arr   : ndarray shape (n,)  growth rates, decimal

    Returns
    -------
    ndarray  shape (n_yos, n)
    """
    g = 1.0 + np.asarray(cola_arr, dtype=float)
    return np.vstack(
        [mp * g ** (yos - 1) for yos, mp in pay_series.items()]
    )


def high3_base_vec(pay_series, cola_arr):
    """
    Per-iteration High-Three monthly base under pay growth.

    Mean of the 3 highest nominal annual pay values for each
    COLA draw.

    Returns
    -------
    ndarray  shape (n,)
    """
    mat = grown_pay_matrix(pay_series, cola_arr)
    return np.sort(mat, axis=0)[-3:, :].mean(axis=0)


def govt_tsp_pv_vec(
    pay_series, cola_arr, sep_yos, discount_rate,
    member_rate=MEMBER_RATE,
):
    """
    Actuarial PV at separation of BRS govt TSP contributions.

    Each year's government contribution (brs_govt_rate x
    nominal annual pay) is compounded forward to the
    separation date at discount_rate. Nominal at-separation
    dollars; deflate by (1 + cola)^sep_yos for 2026 dollars.

    Returns
    -------
    ndarray  shape (n,)
    """
    mat = grown_pay_matrix(pay_series, cola_arr)
    total = np.zeros(mat.shape[1])
    for i, yos in enumerate(pay_series.index):
        rate = brs_govt_rate(yos, member_rate)
        total += (
            mat[i] * 12.0 * rate
            * (1.0 + discount_rate) ** (sep_yos - yos)
        )
    return total


def npv_pension_vec(
    annual_payment, cola_arr, discount_rate, n_years_arr
):
    """
    Vectorized NPV of a COLA-adjusted pension (annuity-due).

    Closed-form growing annuity formula; fractional final year
    included. Equivalent to utils.npv_pension for a single rate
    but vectorized over n_iter draws.

    Parameters
    ----------
    annual_payment : float or ndarray (n,)  first-year payment
    cola_arr       : ndarray shape (n,)  COLA rates, decimal
    discount_rate  : float
    n_years_arr    : ndarray shape (n,)  pension duration

    Returns
    -------
    ndarray  shape (n,)
    """
    g = np.asarray(cola_arr, dtype=float)
    n = np.asarray(n_years_arr, dtype=float)
    n_f = np.floor(n).astype(int)
    frac = n - n_f
    x = (1.0 + g) / (1.0 + discount_rate)
    x_n = x ** n_f
    denom = 1.0 - x
    near_zero = np.abs(denom) < 1e-12
    full = np.where(
        near_zero,
        annual_payment * n_f.astype(float),
        annual_payment
        * (1.0 - x_n)
        / np.where(near_zero, 1.0, denom),
    )
    return full + frac * annual_payment * x_n


def run_scenario(
    profile,
    sep_yos,
    pay_profiles_df,
    life_exp_df,
    fund_stats,
    cola_stats,
    entry_ages,
    n_iter=10_000,
    discount_rate=0.05,
    seed=None,
    death_age_offset=0.0,
    member_rate=MEMBER_RATE,
):
    """
    Run Monte Carlo simulation for one (profile, sep_yos).

    BRS and H3 TSP accounts share the same annual return draws,
    so the TSP difference reflects contribution amounts only
    (not return-path luck). Basic pay grows at the iteration's
    COLA draw; the High-Three base is therefore stochastic.
    All outputs are deflated to constant 2026 dollars.

    Parameters
    ----------
    profile           : str  "Officer", "Enlisted", or
                             "PriorEnlistedOfficer"
    sep_yos           : int  years of service at separation
    pay_profiles_df   : pd.DataFrame  from pay_profiles.csv
    life_exp_df       : pd.DataFrame  from life_expectancy.csv
    fund_stats        : dict  from fit_fund_stats()
    cola_stats        : dict  from fit_cola_stats()
    entry_ages        : dict  {profile: int}
    n_iter            : int   iterations (default 10,000)
    discount_rate     : float (default 0.05)
    seed              : int or None
    death_age_offset  : float  added to SSA mean death age;
                               use for life-expectancy
                               sensitivity (default 0.0)
    member_rate       : float  member TSP contribution rate
                               under both systems (default
                               0.05). BRS adds the government
                               1% auto + match per
                               brs_total_rate; H3 adds nothing.

    Returns
    -------
    dict  ndarrays of shape (n_iter,), constant 2026 dollars:
        "brs_total", "h3_total", "brs_adv",
        "h3_pension_npv", "brs_pension_npv",
        "h3_tsp_pv", "brs_tsp_pv"
    """
    rng = np.random.default_rng(seed)
    entry_age = entry_ages[profile]
    sep_age = entry_age + sep_yos

    pay = (
        pay_profiles_df
        .query("Profile == @profile and YOS <= @sep_yos")
        .set_index("YOS")["MonthlyPay"]
    )

    # COLA drives pay growth, pension COLA, and the deflator
    cola = rng.normal(
        cola_stats["mean"], cola_stats["std"], n_iter
    )
    cola = np.maximum(cola, 0.0)
    deflator = (1.0 + cola) ** sep_yos

    pay_nom = grown_pay_matrix(pay, cola)

    # TSP accumulation — same return draws for BRS and H3
    bal_brs = np.zeros(n_iter)
    bal_h3 = np.zeros(n_iter)
    for i, yos in enumerate(pay.index):
        age = entry_age + yos - 1
        fund = select_fund(max(0, 60 - age))
        r = rng.normal(
            fund_stats[fund]["mean"],
            fund_stats[fund]["std"],
            n_iter,
        )
        annual_pay = pay_nom[i] * 12.0
        bal_brs = (
            bal_brs
            + annual_pay * brs_total_rate(yos, member_rate)
        ) * (1.0 + r)
        bal_h3 = (
            bal_h3 + annual_pay * member_rate
        ) * (1.0 + r)

    # TSP growth from separation to age 60 — same draws
    for age in range(sep_age, 60):
        fund = select_fund(60 - age)
        r = rng.normal(
            fund_stats[fund]["mean"],
            fund_stats[fund]["std"],
            n_iter,
        )
        bal_brs = bal_brs * (1.0 + r)
        bal_h3 = bal_h3 * (1.0 + r)

    gap = max(0, 60 - sep_age)
    disc = (1.0 + discount_rate) ** gap
    tsp_pv_brs = bal_brs / disc / deflator
    tsp_pv_h3 = bal_h3 / disc / deflator

    if sep_yos >= 20:
        h3_base = high3_base_vec(pay, cola)
        h3_ann = annual_pension_high3(h3_base, sep_yos)
        brs_ann = annual_pension_brs(h3_base, sep_yos)

        mean_death = float(
            life_exp_df.loc[
                life_exp_df["Age"] == sep_age,
                "MaleTotalAge",
            ].squeeze()
        ) + death_age_offset
        death_age = rng.normal(
            mean_death, DEATH_AGE_STD, n_iter
        )
        death_age = np.clip(
            death_age, float(sep_age), 120.0
        )
        n_pens = death_age - float(sep_age)

        h3_npv = npv_pension_vec(
            h3_ann, cola, discount_rate, n_pens
        ) / deflator
        brs_npv = npv_pension_vec(
            brs_ann, cola, discount_rate, n_pens
        ) / deflator
    else:
        h3_npv = np.zeros(n_iter)
        brs_npv = np.zeros(n_iter)

    h3_total = h3_npv + tsp_pv_h3
    brs_total = brs_npv + tsp_pv_brs
    return {
        "brs_total": brs_total,
        "h3_total": h3_total,
        "brs_adv": brs_total - h3_total,
        "h3_pension_npv": h3_npv,
        "brs_pension_npv": brs_npv,
        "h3_tsp_pv": tsp_pv_h3,
        "brs_tsp_pv": tsp_pv_brs,
    }
