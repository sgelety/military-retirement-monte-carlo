"""NPV and percentile reporting utilities."""

import numpy as np


def npv_pension(annual_payment, cola_rate, discount_rate, n_years):
    """
    NPV of a COLA-adjusted annual pension stream.

    Payments begin at t=0 (annuity-due). Fractional final year
    is included proportionally.

    Parameters
    ----------
    annual_payment : float  First-year annual payment
    cola_rate : float  Annual COLA as decimal
    discount_rate : float  Nominal discount rate as decimal
    n_years : float  Total years of payments

    Returns
    -------
    float  NPV as of the first payment date
    """
    n_full = int(n_years)
    frac = n_years - n_full
    total = 0.0
    payment = annual_payment
    for t in range(n_full):
        total += payment / (1 + discount_rate) ** t
        payment *= (1 + cola_rate)
    if frac > 0:
        total += frac * payment / (1 + discount_rate) ** n_full
    return total


def pv_lump_sum(amount, years, discount_rate):
    """Present value of a lump sum received 'years' from now."""
    return amount / (1 + discount_rate) ** years


def percentile_summary(values):
    """
    Percentile summary of a distribution for MC reporting.

    Returns
    -------
    dict  keys: p10, p25, p50, p75, p90, mean
    """
    arr = np.asarray(values)
    return {
        "p10": float(np.percentile(arr, 10)),
        "p25": float(np.percentile(arr, 25)),
        "p50": float(np.percentile(arr, 50)),
        "p75": float(np.percentile(arr, 75)),
        "p90": float(np.percentile(arr, 90)),
        "mean": float(np.mean(arr)),
    }
