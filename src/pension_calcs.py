"""Pension formula calculations for High-Three and BRS."""


def high_three_base(pay_series):
    """
    Average monthly pay over the top 36 months.

    Since pay is constant within each year of service, the top
    36 months equal the 3 highest annual values (each spanning
    12 months), so this returns the mean of the top 3 entries.
    """
    return pay_series.nlargest(3).mean()


def annual_pension_high3(high3_monthly, yos):
    """Annual High-Three pension: 2.5% x YOS x (base x 12)."""
    return high3_monthly * 12 * 0.025 * yos


def annual_pension_brs(high3_monthly, yos):
    """Annual BRS pension: 2.0% x YOS x (base x 12)."""
    return high3_monthly * 12 * 0.020 * yos
