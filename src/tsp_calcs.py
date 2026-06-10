"""TSP accumulation and glide-path growth calculations."""

MEMBER_RATE = 0.05
GOVT_AUTO = 0.01
GOVT_MATCH_CAP = 0.04

# Total annual contribution rates, assuming member contributes
# MEMBER_RATE under both systems. Pass these to tsp_at_separation.
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


def tsp_at_separation(
    pay_series, entry_age, means, total_contrib_rate
):
    """
    TSP balance at end of service.

    Each year: balance = (balance + contributions) * (1 + r)
    Contributions = total_contrib_rate * annual_pay.
    Return r comes from the glide-path fund for that service year.

    Pass BRS_CONTRIB_RATE for BRS or H3_MEMBER_RATE for High-Three.

    Parameters
    ----------
    pay_series : pd.Series  index=YOS, values=monthly_basic_pay
    entry_age : int
    means : dict  {fund_name: mean_return_decimal}
    total_contrib_rate : float

    Returns
    -------
    float  TSP balance at separation
    """
    balance = 0.0
    for yos, monthly_pay in pay_series.items():
        age = entry_age + yos - 1
        r = means[select_fund(max(0, 60 - age))]
        contrib = monthly_pay * 12 * total_contrib_rate
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
