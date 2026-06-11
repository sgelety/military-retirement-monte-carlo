"""TSP accumulation and glide-path growth calculations."""

MEMBER_RATE = 0.05
GOVT_AUTO = 0.01
GOVT_MATCH_CAP = 0.04

# Steady-state total annual contribution rates (YOS 3+),
# assuming the member contributes MEMBER_RATE under both
# systems. Kept for printouts and quick reference; per-YOS
# rates come from brs_total_rate below.
BRS_CONTRIB_RATE = MEMBER_RATE + GOVT_AUTO + GOVT_MATCH_CAP  # 0.10
H3_MEMBER_RATE = MEMBER_RATE                                  # 0.05

# Glide path: (years_remaining_threshold, L_fund_name)
# Checked in descending order; first threshold met is used.
# Only funds with >= 10 years of history are included.
_GLIDE_PATH = [
    (30, "L 2050"),
    (20, "L 2040"),
    (10, "L 2030"),
    (0, "L Income"),
]


def brs_govt_rate(yos, member_rate=MEMBER_RATE):
    """
    BRS government TSP contribution rate at a given YOS.

    The 1% automatic contribution applies from entry (it
    actually begins after 60 days; treated as year 1 here).
    Matching begins after 2 years of service (YOS 3 onward)
    and follows the statutory tier schedule:
    dollar-for-dollar on the first 3% the member contributes,
    then 50 cents per dollar on the next 2% — so the match
    maxes out at 4% when the member contributes 5%.

    At member rates of 0-3%, 5%, and above, this equals the
    simpler min(member_rate, 4%); the schedules differ only
    between 3% and 5% (e.g., a 4% contribution draws a 3.5%
    match, not 4%).
    """
    if yos <= 2:
        return GOVT_AUTO
    match = min(member_rate, 0.03) + 0.5 * (
        min(member_rate, 0.05) - min(member_rate, 0.03)
    )
    return GOVT_AUTO + match


def brs_total_rate(yos, member_rate=MEMBER_RATE):
    """Total BRS contribution rate (member + govt) at a YOS."""
    return member_rate + brs_govt_rate(yos, member_rate)


def select_fund(years_to_60):
    """L Fund for a given number of years remaining to age 60."""
    for threshold, fund in _GLIDE_PATH:
        if years_to_60 >= threshold:
            return fund
    return "L Income"


def compute_fund_means(tsp_df):
    """
    Mean annual return as decimal for each glide-path fund.

    Parameters
    ----------
    tsp_df : pd.DataFrame
        Processed TSP returns (% as floats, one row per year).

    Returns
    -------
    dict  {fund_name: mean_return_decimal}
    """
    funds = [f for _, f in _GLIDE_PATH]
    return {f: tsp_df[f].dropna().mean() / 100 for f in funds}


def tsp_at_separation(pay_series, entry_age, means, rate):
    """
    TSP balance at end of service.

    Each year: balance = (balance + contributions) * (1 + r)
    Contributions = rate * annual_pay. Return r comes from the
    glide-path fund for that service year.

    Parameters
    ----------
    pay_series : pd.Series  index=YOS, values=monthly_basic_pay
                 (pass nominal pay if modeling pay growth)
    entry_age : int
    means : dict  {fund_name: mean_return_decimal}
    rate : float or callable
        Total contribution rate. A float applies every year;
        a callable is evaluated as rate(yos) — pass
        brs_total_rate for BRS match-timing behavior, or
        H3_MEMBER_RATE for High-Three.

    Returns
    -------
    float  TSP balance at separation
    """
    rate_fn = rate if callable(rate) else (lambda yos: rate)
    balance = 0.0
    for yos, monthly_pay in pay_series.items():
        age = entry_age + yos - 1
        r = means[select_fund(max(0, 60 - age))]
        contrib = monthly_pay * 12 * rate_fn(yos)
        balance = (balance + contrib) * (1 + r)
    return balance


def tsp_grow_to_60(balance, sep_age, means):
    """
    Grow TSP from separation to age 60 with no contributions.

    Parameters
    ----------
    balance : float  TSP balance at separation
    sep_age : int  age at separation
    means : dict  {fund_name: mean_return_decimal}

    Returns
    -------
    float  TSP balance at age 60 (unchanged if sep_age >= 60)
    """
    b = balance
    for age in range(sep_age, 60):
        r = means[select_fund(60 - age)]
        b *= (1 + r)
    return b
