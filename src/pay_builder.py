"""Build monthly basic-pay series from promotion timelines.

`lookup_pay` and `build_pay_series` are extracted from
notebook 02 unchanged, so the notebook and the interactive
app share one implementation. The *_points helpers support
user-edited promotion timelines in the app: a timeline is a
list of (grade, yos_attained) pin-points, forward-filled to
a grade-at-each-YOS series and then priced against the pay
table.
"""

import pandas as pd


def lookup_pay(grade, yos, pay_table):
    """Monthly basic pay for a grade at a given YOS."""
    breakpoints = pay_table.columns.tolist()
    col = max(bp for bp in breakpoints if bp <= yos)
    return pay_table.loc[grade, col]


def build_pay_series(profile, sep_yos, promotion, basic_pay):
    """
    Monthly basic pay by YOS from 1 through sep_yos.

    Returns None if the profile column has NaN values within
    [1, sep_yos] (e.g., enlisted beyond YOS 30).
    """
    grades = promotion[profile].loc[1:sep_yos]
    if grades.isna().any():
        return None
    return pd.Series(
        {
            yos: lookup_pay(grade, yos, basic_pay)
            for yos, grade in grades.items()
        },
        name=f"{profile}_sep{sep_yos}",
    )


def promotion_points(promotion, profile):
    """
    Promotion pin-points for a profile's typical timeline.

    Parameters
    ----------
    promotion : pd.DataFrame  promotion_timing.csv indexed
                              by YOS
    profile   : str  column name

    Returns
    -------
    list of (grade, yos_attained) in career order, where
    yos_attained is the first YOS spent at that grade.
    """
    grades = promotion[profile].dropna()
    points = []
    prev = None
    for yos, grade in grades.items():
        if grade != prev:
            points.append((grade, int(yos)))
            prev = grade
    return points


def grades_from_points(points, max_yos):
    """
    Grade-at-each-YOS series from promotion pin-points.

    Each grade is held from its yos_attained until the next
    promotion (forward fill). Pin-points beyond max_yos are
    never reached and are ignored, which is how a user says
    "I top out at E-7": drop or postpone the E-8 pin-point.

    Parameters
    ----------
    points  : list of (grade, yos_attained); YOS values must
              be strictly increasing and start at 1
    max_yos : int  final YOS of the series

    Returns
    -------
    pd.Series  index YOS 1..max_yos, values pay grades
    """
    if not points:
        raise ValueError("at least one pin-point is required")
    yos_vals = [yos for _, yos in points]
    if yos_vals[0] != 1:
        raise ValueError(
            "the first grade must start at YOS 1"
        )
    if any(b <= a for a, b in zip(yos_vals, yos_vals[1:])):
        raise ValueError(
            "promotion YOS must be strictly increasing"
        )
    grades = {}
    for grade, start in points:
        if start > max_yos:
            break
        for yos in range(start, max_yos + 1):
            grades[yos] = grade
    return pd.Series(grades).sort_index()


def pay_series_from_grades(grades, basic_pay, name="Custom"):
    """
    Price a grade-at-YOS series against the pay table.

    Raises ValueError naming the offending (grade, YOS) when
    the pay table has no value for that combination — a blank
    cell means the combination does not exist (e.g., E-9 at
    YOS 4).

    Returns
    -------
    pd.Series  index YOS, values monthly basic pay (2026 $)
    """
    out = {}
    for yos, grade in grades.items():
        if grade not in basic_pay.index:
            raise ValueError(
                f"unknown pay grade {grade!r}"
            )
        pay = lookup_pay(grade, yos, basic_pay)
        if pd.isna(pay):
            raise ValueError(
                f"{grade} at YOS {yos} does not exist in"
                " the pay table"
            )
        out[yos] = float(pay)
    return pd.Series(out, name=name)
