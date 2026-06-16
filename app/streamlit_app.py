"""Interactive BRS vs. High-Three explorer.

Run from the repo root:
    streamlit run app/streamlit_app.py

Pick a career profile, separation point, TSP contribution
rate, and (optionally) a custom promotion timeline; see the
lifetime value difference (BRS - H3) for that career and what
the same career costs the government under each system.

All values are NPV at separation in constant 2026 dollars.
"""

import sys
from pathlib import Path

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scenario_calcs as sc  # noqa: E402
from explain import explain_scenario  # noqa: E402

# System colors — the notebooks' palette: BRS bright
# Michigan blue, High-Three Michigan maize. The light blue /
# maize versions shade the difference chart's two halves.
H3_COLOR = "#FFCB05"
BRS_COLOR = "#00274C"
BRS_REGION = "#4B6C8F"
H3_REGION = "#FFE57F"
PROFILE_COLORS = {
    "Enlisted": "#D86018",
    "PriorEnlistedOfficer": "#75988d",
    "Officer": "#575294",
}

st.set_page_config(
    page_title="BRS vs. High-Three Explorer",
    layout="wide",
)


def fmt_usd(x):
    """$1,234,567 with a true minus sign for negatives."""
    sign = "−" if x < 0 else ""
    return f"{sign}${abs(x):,.0f}"


def theme():
    """Theme-aware chart colors so figures blend into the app's
    light or dark page. On dark, the few palette colors that would
    vanish against the dark background (the navy BRS line and the
    navy / dark-gold advantage labels) are lightened; maize and
    profile colors carry over unchanged. Falls back to light.
    """
    try:
        is_dark = st.context.theme.type == "dark"
    except Exception:  # noqa: BLE001 — theme may be unavailable
        is_dark = False
    if is_dark:
        return {
            "dark": True,
            "fg": "#fafafa",
            "bg": "#0e1117",
            "brs": "#7fb2e8",       # brightened Michigan blue
            "brs_label": "#9bbfe0",
            "h3_label": "#ddbb66",  # light gold
            # Brightened profile colors so the difference fan
            # pops against the dark page (the sage green and
            # violet read dim at full saturation on dark).
            "profiles": {
                "Enlisted": "#F0843C",
                "PriorEnlistedOfficer": "#93C7B2",
                "Officer": "#8F89CE",
            },
        }
    return {
        "dark": False,
        "fg": "#262730",
        "bg": "#ffffff",
        "brs": BRS_COLOR,
        "brs_label": "#00274C",
        "h3_label": "#6b540f",
        "profiles": PROFILE_COLORS,
    }


def theme_fg():
    """Foreground (text/axes) color for the current app theme."""
    return theme()["fg"]


def apply_chart_theme(tc):
    """Blend every matplotlib figure into the app theme via
    rcParams: transparent backgrounds, foreground-colored text,
    axes, ticks, grid, and a page-colored legend box.
    """
    plt.rcParams.update({
        "figure.facecolor": "none",
        "axes.facecolor": "none",
        "savefig.facecolor": "none",
        "savefig.edgecolor": "none",
        "text.color": tc["fg"],
        "axes.labelcolor": tc["fg"],
        "axes.edgecolor": tc["fg"],
        "axes.titlecolor": tc["fg"],
        "xtick.color": tc["fg"],
        "ytick.color": tc["fg"],
        "grid.color": tc["fg"],
        "legend.facecolor": tc["bg"],
        "legend.edgecolor": tc["fg"],
        "legend.framealpha": 0.85,
    })


def esc_md(text):
    """Escape $ so paired dollars don't render as LaTeX math.

    Streamlit markdown (st.markdown / st.caption) treats
    $...$ as math, same as notebook markdown — escape any
    dollar amounts before rendering.
    """
    return text.replace("$", "\\$")


# ----------------------------------------------------------
# Static copy — long, unchanging blurbs for the two expanders.
# Kept here (rather than mid-layout) so the render flow below
# reads as structure. Pass through esc_md() at render time.
# ----------------------------------------------------------
HOW_IT_WORKS = (
    "**What's being compared.** Two retirement systems. "
    "The legacy **High-Three** pays a pension of 2.5% × "
    "years served × your highest 36 months of basic pay — "
    "but only if you reach 20 years. Leave at 19 and you "
    "get nothing. The **BRS** (everyone joining since 2018) "
    "pays a smaller pension (2.0% per year, same 20-year "
    "rule) but adds money to your TSP that you keep no "
    "matter when you leave: 1% of basic pay automatically, "
    "plus matching on your own contributions (full match at "
    "5%). This app asks: over a whole lifetime, which "
    "package is worth more for *your* career — and what "
    "does each cost the government?\n\n"
    "**Step 1 — your pay history.** From your profile and "
    "promotion timeline, the app builds your year-by-year "
    "basic pay using the official 2026 military pay table "
    "(including the higher O-1E/O-2E/O-3E rates for "
    "prior-enlisted officers). Rank comes from typical "
    "promotion timing — or your own edits in the sidebar.\n\n"
    "**Step 2 — 20,000 possible futures.** Nobody knows "
    "future market returns, inflation, or how long they'll "
    "live, so instead of pretending to, the app simulates "
    "20,000 versions of your future and varies all three:\n"
    "- **TSP returns** are drawn from the actual history of "
    "the TSP Lifecycle (L) funds, and your money follows "
    "the same glide path a real L fund does — aggressive "
    "stock-heavy funds when you're young, shifting toward "
    "safer funds as you near 60.\n"
    "- **Inflation** for each future is drawn from over a "
    "century of U.S. inflation data, and drives pay raises, "
    "pension cost-of-living adjustments, and the conversion "
    "to today's dollars — consistently, all at once.\n"
    "- **Lifespan** is drawn from the Social Security "
    "Administration's actuarial tables, given your age at "
    "separation — because a pension's value depends "
    "enormously on how many years it actually pays.\n\n"
    "The chart line and the shaded band show the spread "
    "across those 20,000 futures: the median is the middle "
    "outcome, and the band holds the middle 50% — half of "
    "all simulated futures land inside it.\n\n"
    "**Why everything is in \"2026 dollars at separation\".** "
    "A dollar promised in 2055 is worth less than a dollar "
    "today — both because of inflation and because money in "
    "hand earns returns. Every future payment (pension "
    "checks, TSP balance at 60) is discounted back to your "
    "separation date at 5% per year and stated in 2026 "
    "purchasing power, so a pension stream and a TSP "
    "balance can be compared apples-to-apples.\n\n"
    "**Why your contribution is the same under both "
    "systems.** The slider sets *your* TSP contribution "
    "identically under H3 and BRS. That's deliberate: your "
    "own savings would follow you either way, so holding it "
    "equal isolates what the *government* provides "
    "differently — the match and the pension multiplier. "
    "That's also why the headline difference doesn't move "
    "above 5%: the match is maxed, and beyond that it's "
    "your money under both systems.\n\n"
    "**The market-outlook setting** answers a different "
    "question than the shaded bands. The bands show *luck* "
    "— good and bad return sequences around the historical "
    "average. The outlook setting shifts the *average "
    "itself* by 2 percentage points, sustained for your "
    "whole career — a decades-long bull or bear regime. "
    "It's a strong assumption, and it's the strongest "
    "single lever on the answer for 20+ year careers.\n\n"
    "**The government side** values the same career the way "
    "an actuary would: the pension promise discounted at "
    "5%, plus the government's TSP deposits compounded at "
    "that same rate. Force-wide statistics weight each "
    "possible separation point by the DoD actuary's "
    "historical separation rates.\n\n"
    "**What's deliberately left out:** taxes, the BRS "
    "continuation-pay bonus (a mid-career cash incentive — "
    "excluding it slightly favors High-Three), reserve/"
    "guard retirement, and personal withdrawal strategy. "
    "Promotion timing is asserted by you, not predicted.\n\n"
    "*Data sources: DFAS 2026 pay table, DoD Office of the "
    "Actuary separation rates, TSP.gov fund history, SSA "
    "2022 life tables, BLS CPI (1913–present).*"
)

ASSUMPTIONS = (
    "- **Reporting**: NPV at separation, constant 2026 "
    "dollars; framing is the neutral difference "
    "(BRS − H3), not a recommendation.\n"
    "- **Deterministic path**: 2.75% COLA / pay growth "
    "(DoD actuarial), glide-path L Fund historical "
    "means, SSA 2022 male life expectancy.\n"
    "- **Monte Carlo**: stochastic TSP returns "
    "(glide-path L Fund distributions), lifetime-"
    "average COLA (rolling 30-yr CPI fit), and age at "
    "death (SSA 2022 male, ±13 yr).\n"
    "- **TSP**: member contributes the same rate under "
    "both systems; BRS adds 1% automatic plus up to 4% "
    "match (from YOS 3). Returns follow the L Fund "
    "glide path to age 60, then drawdown pricing at "
    "the discount rate.\n"
    "- **Market outlook**: a uniform ±2 pp shift of all "
    "glide-path mean returns — the return component of "
    "notebook 05's Bull/Bear regime stress (the notebook "
    "scenarios additionally vary COLA and discount rate; "
    "here the discount rate is its own Advanced control). "
    "A separate construct from the Monte Carlo's "
    "year-to-year variation.\n"
    "- **Promotion timeline**: rank is asserted by you "
    "(or the typical table), not predicted; pay is "
    "priced from the 2026 DFAS table.\n"
    "- **Entry age** (default 18 enlisted / 22 officer / "
    "18 prior-enlisted) shifts every age-keyed input: "
    "the TSP glide path, the growth window to 60, and "
    "the life-expectancy lookup. Separations past age "
    "60 are handled (no growth window).\n"
    "- **Out of scope**: reserve retirement, "
    "continuation pay, TSP withdrawal strategy, and "
    "behavioral retention effects.\n"
    "- Force-wide context uses DoD actuarial "
    "separation rates on the standard profiles; your "
    "custom timeline changes your ledger, not the "
    "force-wide stats."
)


@st.cache_resource
def get_inputs():
    return sc.load_inputs()


@st.cache_data
def cached_curve(profile, points, max_yos, entry_age,
                 member_rate, disc, outlook):
    inputs = get_inputs()
    pay, _ = sc.pay_from_points(
        list(points), max_yos, inputs["basic_pay"]
    )
    means = sc.shift_fund_means(
        inputs["fund_means"], sc.REGIME_SHIFTS[outlook]
    )
    return sc.deterministic_curve(
        pay, entry_age, inputs["life_exp"],
        means, member_rate, disc,
    )


@st.cache_data
def cached_mc_curve(
    profile, points, max_yos, entry_age, member_rate, disc,
    n_iter, outlook,
):
    inputs = get_inputs()
    pay, _ = sc.pay_from_points(
        list(points), max_yos, inputs["basic_pay"]
    )
    stats = sc.shift_fund_stats(
        inputs["fund_stats"], sc.REGIME_SHIFTS[outlook]
    )
    return sc.mc_curve(
        profile, pay, entry_age,
        inputs["life_exp"], stats, inputs["cola_stats"],
        member_rate, disc, n_iter=n_iter,
    )


@st.cache_data
def cached_mc_cusp(
    profile, points, max_yos, entry_age, member_rate, disc,
    n_iter, outlook,
):
    inputs = get_inputs()
    pay, _ = sc.pay_from_points(
        list(points), max_yos, inputs["basic_pay"]
    )
    stats = sc.shift_fund_stats(
        inputs["fund_stats"], sc.REGIME_SHIFTS[outlook]
    )
    return sc.mc_cusp(
        profile, pay, entry_age,
        inputs["life_exp"], stats, inputs["cola_stats"],
        member_rate, disc, n_iter=n_iter,
    )


inputs = get_inputs()

# ----------------------------------------------------------
# Sidebar — inputs
# ----------------------------------------------------------
st.sidebar.header("Your career")

profile = st.sidebar.radio(
    "Career profile",
    sc.PROFILES,
    format_func=sc.PROFILE_LABELS.get,
    key="profile",
)
max_yos = sc.PROFILE_MAX_YOS[profile]

sep_yos = st.sidebar.slider(
    "Years of service at separation",
    min_value=sc.MIN_SEP_YOS,
    max_value=max_yos,
    value=min(20, max_yos),
    step=1,
)

entry_age = st.sidebar.number_input(
    "Age when you entered service",
    min_value=17, max_value=40,
    value=sc.ENTRY_AGE[profile],
    step=1,
    key=f"entry_age_{profile}",
    help=(
        "Drives your age at every point of the career: the "
        "TSP glide path (how long your money rides the "
        "aggressive funds before age 60), the growth window "
        "between separation and 60, and the life-expectancy "
        "lookup behind the pension value. For prior-enlisted "
        "officers this is the age you enlisted — "
        "commissioning happens at the timeline's YOS."
    ),
)

member_pct = st.sidebar.slider(
    "Your TSP contribution (% of basic pay)",
    min_value=0, max_value=10, value=5, step=1,
    help=(
        "Held equal under both systems to isolate the "
        "government-funded difference. BRS adds a 1% "
        "automatic government contribution from entry, plus "
        "matching from year 3: dollar-for-dollar on your "
        "first 3%, then 50 cents per dollar on the next 2% "
        "— the full 4% match (5% total government) requires "
        "contributing at least 5%."
    ),
)
member_rate = member_pct / 100.0

outlook = st.sidebar.radio(
    "Market outlook",
    list(sc.REGIME_SHIFTS),
    index=1,
    help=(
        "Shifts the average TSP return 2 percentage points "
        "below or above its long-run history — sustained for "
        "your entire career. This is the return stress from "
        "the analysis's Bear/Bull scenarios (which also vary "
        "inflation and discount rate; here only returns "
        "move). The simulation still varies year-to-year "
        "luck around that average. The government ledger "
        "doesn't move: DoD's cost is valued at the discount "
        "rate, not market returns."
    ),
)

with st.sidebar.expander("Adjust my promotion timeline"):
    st.caption(
        "Typical timing shown. Edit the YOS at which you "
        "reach each grade. To remove a rank you won't reach "
        "(e.g., topping out at E-7): tick the checkbox at "
        "the left edge of its row, then press Delete or the "
        "trash icon in the table's toolbar."
    )
    if "editor_reset" not in st.session_state:
        st.session_state["editor_reset"] = 0
    if st.button("Reset to typical"):
        st.session_state["editor_reset"] += 1
    default_pts = sc.typical_points(inputs, profile)
    seed_df = pd.DataFrame(
        default_pts, columns=["Grade", "Promoted at YOS"]
    )
    edited = st.data_editor(
        seed_df,
        num_rows="dynamic",
        hide_index=True,
        key=(
            f"timeline_{profile}_"
            f"{st.session_state['editor_reset']}"
        ),
        column_config={
            "Grade": st.column_config.SelectboxColumn(
                options=list(inputs["basic_pay"].index),
                required=True,
            ),
            "Promoted at YOS": st.column_config.NumberColumn(
                min_value=1, max_value=max_yos, step=1,
                required=True,
            ),
        },
    )

with st.sidebar.expander("Advanced"):
    disc_pct = st.slider(
        "Discount rate (%)",
        min_value=3.0, max_value=7.0, value=5.0, step=0.5,
    )
    disc = disc_pct / 100.0
    n_iter = st.select_slider(
        "Monte Carlo iterations",
        options=[5_000, 20_000],
        value=20_000,
    )

# ----------------------------------------------------------
# Build the pay series from the (possibly edited) timeline
# ----------------------------------------------------------
clean = edited.dropna()
points = [
    (str(row["Grade"]), int(row["Promoted at YOS"]))
    for _, row in clean.iterrows()
]
is_custom = points != default_pts

try:
    pay_full, grades = sc.pay_from_points(
        points, max_yos, inputs["basic_pay"]
    )
except ValueError as err:
    st.error(
        f"Promotion timeline problem: {err}. Fix the "
        "timeline in the sidebar (or reset to typical)."
    )
    st.stop()

points_key = tuple(points)
sep_age = entry_age + sep_yos
rank_at_sep = grades.loc[sep_yos]
timing_label = (
    "your timeline" if is_custom else "typical timing"
)

curve = cached_curve(
    profile, points_key, max_yos, entry_age, member_rate,
    disc, outlook,
)
mcc = cached_mc_curve(
    profile, points_key, max_yos, entry_age, member_rate,
    disc, n_iter, outlook,
)
mc = sc.mc_from_curve_row(
    mcc.set_index("SepYOS").loc[sep_yos]
)
det = curve.set_index("SepYOS").loc[sep_yos]
ctx = sc.population_context(inputs, profile, sep_yos)

# Cliff split: the pension vests at 20, so the fans jump
# there. Recover the TSP-only "cusp" the pre-20 lines reach.
career_max = int(mcc["SepYOS"].max())
has_cliff = career_max >= 20
cusp = (
    cached_mc_cusp(
        profile, points_key, max_yos, entry_age, member_rate,
        disc, n_iter, outlook,
    )
    if has_cliff
    else None
)
drow20 = (
    curve.set_index("SepYOS").loc[20] if has_cliff else None
)

# ----------------------------------------------------------
# Header + career snapshot
# ----------------------------------------------------------
st.title("Beyond the Pension Cliff")
st.caption(
    "Blended Retirement System (BRS) vs. legacy High-Three "
    "— lifetime value to you, and cost to the government. "
    "All values are NPV at separation in constant 2026 "
    "dollars. Positive difference = BRS yields more."
)

with st.expander("How this works — where these numbers come from"):
    st.markdown(esc_md(HOW_IT_WORKS))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Profile", sc.PROFILE_LABELS[profile])
c2.metric(
    "Rank at separation",
    str(rank_at_sep),
    timing_label,
    delta_color="off",
)
c3.metric("Age at separation", f"{sep_age}")
c4.metric(
    "Final monthly basic pay (2026 $)",
    fmt_usd(pay_full.loc[sep_yos]),
)
# Rank timeline: how long the member holds each grade
runs = []
for yos, grade in grades.loc[:sep_yos].items():
    if runs and runs[-1][0] == grade:
        runs[-1][2] = yos
    else:
        runs.append([grade, yos, yos])

tc = theme()
apply_chart_theme(tc)
fg = tc["fg"]
fig, ax = plt.subplots(figsize=(10, 0.9))
fig.patch.set_alpha(0.0)  # blend with the app's page background
ax.patch.set_alpha(0.0)
for grade, start, end in runs:
    color = (
        "#F0C9A8"  # light Ross-orange tint (E grades)
        if str(grade).startswith("E")
        else "#C3C0DA"  # light Matthaei-violet tint (O grades)
    )
    ax.barh(
        0, end - start + 1, left=start, height=0.8,
        color=color, edgecolor="white",
    )
    # Grade label sits on the light-colored bar, so keep it dark.
    ax.text(
        (start + end + 1) / 2, 0, str(grade),
        ha="center", va="center", fontsize=9, color="#262730",
    )
ax.set_xlim(1, sep_yos + 1)
ax.set_yticks([])
ax.set_xlabel("Years of Service", fontsize=9, color=fg)
ax.tick_params(colors=fg)
ax.spines["bottom"].set_color(fg)
for side in ("top", "right", "left"):
    ax.spines[side].set_visible(False)
fig.tight_layout()
st.pyplot(fig)
plt.close(fig)
st.caption(f"Rank timeline ({timing_label})")

# One-line takeaway — colored headline number (blue is neutral;
# red would read as a warning).
adv_med = mc["brs_adv"]["p50"]
if adv_med >= 0:
    headline = (
        f"For this career, **BRS yields about {fmt_usd(adv_med)} "
        "more** over a lifetime than High-Three (median)."
    )
else:
    headline = (
        "For this career, **legacy High-Three yields about "
        f"{fmt_usd(-adv_med)} more** over a lifetime than BRS "
        "(median)."
    )
st.markdown(f"#### :blue[{esc_md(headline)}]")

if sep_yos < 20:
    st.info(
        f"Separating at {sep_yos} years — **before the "
        "20-year pension cliff**. Under High-Three you "
        "would leave with no government-funded retirement "
        "benefit at all; under BRS you keep the "
        "government's TSP contributions."
    )

# ----------------------------------------------------------
# Ledgers
# ----------------------------------------------------------
left, right = st.columns(2)

with left:
    st.subheader("Your ledger")
    adv = mc["brs_adv"]
    st.metric(
        "Lifetime value difference (BRS − H3), median",
        fmt_usd(adv["p50"]),
    )
    st.caption(esc_md(
        f"Monte Carlo middle 50% of outcomes: "
        f"{fmt_usd(adv['p25'])} to {fmt_usd(adv['p75'])} · mean "
        f"{fmt_usd(adv['mean'])} · N={n_iter:,}"
    ))
    cm = mc["component_means"]
    comp = pd.DataFrame(
        {
            "High-Three": [
                cm["h3_pension"], cm["member_tsp"], 0.0,
                cm["h3_total"],
            ],
            "BRS": [
                cm["brs_pension"], cm["member_tsp"],
                cm["govt_tsp"], cm["brs_total"],
            ],
        },
        index=[
            "Pension NPV",
            "Member TSP PV",
            "Govt TSP PV",
            "Total",
        ],
    )
    st.dataframe(comp.style.format(fmt_usd), width="stretch")
    st.caption(
        "Component values are Monte Carlo means (means add "
        "up; medians don't). Member TSP is identical under "
        "both systems by design."
    )

with right:
    st.subheader("Government ledger")
    g1, g2, g3 = st.columns(3)
    g1.metric(
        "Cost under High-Three", fmt_usd(det["H3_GovtCost"])
    )
    g2.metric(
        "Cost under BRS", fmt_usd(det["BRS_GovtCost"])
    )
    g3.metric(
        "DoD savings (H3 − BRS)",
        fmt_usd(det["DoD_Savings"]),
    )
    st.caption(
        "Deterministic actuarial basis (notebook 04): "
        "pension NPV plus government TSP contributions "
        "compounded at the discount rate. The market-outlook "
        "setting doesn't move this side — DoD's cost is "
        "valued at the discount rate, not market returns."
    )
    st.markdown(esc_md(
        f"**Across the force** (typical "
        f"{sc.PROFILE_LABELS[profile].lower()} careers, "
        "DoD separation rates):\n"
        f"- {ctx['share_pre20_members']:.0%} of entrants "
        "separate before 20 years; they receive only "
        f"{ctx['share_pre20_spend']:.1%} of expected BRS "
        "spending\n"
        f"- {ctx['share_reaching_sep']:.0%} of entrants "
        f"serve {sep_yos}+ years\n"
        f"- Expected per-entrant savings from BRS: "
        f"{fmt_usd(ctx['expected_savings'])} "
        f"({fmt_usd(ctx['expected_h3_cost'])} → "
        f"{fmt_usd(ctx['expected_brs_cost'])})"
    ))

# ----------------------------------------------------------
# Charts
# ----------------------------------------------------------
st.subheader("Where your career sits on the cliff")
st.caption(
    f"Market outlook: {outlook}. Lines are Monte Carlo "
    "medians across every possible separation year; the "
    f"shaded band is the middle 50% of {n_iter:,} simulated "
    "futures."
)
ch1, ch2 = st.columns(2)

with ch1:
    fig, ax = plt.subplots(figsize=(7, 4.2))
    pre = mcc[mcc["SepYOS"] < 20]
    post = mcc[mcc["SepYOS"] >= 20]
    bands = [("p25", "p75", 0.22)]
    for key, color, label in [
        ("h3_govt", H3_COLOR, "High-Three"),
        ("brs_govt", tc["brs"], "BRS"),
    ]:
        # The maize H3 line is faint on white; give it a thin
        # navy outline (matching the maize bars' navy edge).
        line_pe = (
            [pe.Stroke(linewidth=2.8, foreground=BRS_COLOR),
             pe.Normal()]
            if key == "h3_govt" else None
        )
        if has_cliff:
            cu = cusp[key]
            xp = list(pre["SepYOS"]) + [20]
            # P25–P75 band, extended to its value on the cusp
            # of vesting at 20 (TSP only, no pension yet).
            for lo, hi, a in bands:
                ax.fill_between(
                    xp,
                    list(pre[f"{key}_{lo}"] / 1000)
                    + [cu[lo] / 1000],
                    list(pre[f"{key}_{hi}"] / 1000)
                    + [cu[hi] / 1000],
                    alpha=a, color=color,
                )
                ax.fill_between(
                    post["SepYOS"], post[f"{key}_{lo}"] / 1000,
                    post[f"{key}_{hi}"] / 1000,
                    alpha=a, color=color,
                )
            # Median: pre to the cusp (open marker = limit not
            # attained), dotted drop = the cliff, then 20+.
            ax.plot(
                xp,
                list(pre[f"{key}_p50"] / 1000)
                + [cu["p50"] / 1000],
                color=color, lw=2, label=label,
                path_effects=line_pe,
            )
            vested = post[f"{key}_p50"].iloc[0] / 1000
            ax.plot(
                [20], [cu["p50"] / 1000], "o", mfc=tc["bg"],
                mec=color, mew=1.4, zorder=6,
            )
            ax.plot(
                [20, 20], [cu["p50"] / 1000, vested],
                ls=":", color=color, lw=1.1, alpha=0.8,
            )
            ax.plot(
                post["SepYOS"], post[f"{key}_p50"] / 1000,
                color=color, lw=2, path_effects=line_pe,
            )
        else:
            for lo, hi, a in bands:
                ax.fill_between(
                    mcc["SepYOS"], mcc[f"{key}_{lo}"] / 1000,
                    mcc[f"{key}_{hi}"] / 1000,
                    alpha=a, color=color,
                )
            ax.plot(
                mcc["SepYOS"], mcc[f"{key}_p50"] / 1000,
                color=color, lw=2, label=label,
                path_effects=line_pe,
            )
        ax.plot(
            [sep_yos], [mc[key]["p50"] / 1000], "o",
            color=color,
        )
    ax.axvline(
        sep_yos, color=fg, linewidth=0.8, linestyle=":",
    )
    ax.set_xlabel("Years of Service at Separation")
    ax.set_ylabel("Government-Funded Value (2026 $)")
    ax.set_title(
        "Government-Funded Value by System\n"
        "(excludes your TSP contribution — identical under both)"
    )
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"${v / 1000:,.1f}M")
    )
    # Gray proxies explain the (per-system colored) bands.
    sys_h, sys_l = ax.get_legend_handles_labels()
    band_h = [
        Patch(facecolor="0.5", alpha=0.45,
              label="Middle 50% of outcomes"),
    ]
    ax.legend(
        sys_h + band_h,
        sys_l + [h.get_label() for h in band_h],
        fontsize=8,
    )
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

with ch2:
    pcolor = tc["profiles"][profile]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    pre = mcc[mcc["SepYOS"] < 20]
    post = mcc[mcc["SepYOS"] >= 20]
    if has_cliff:
        cu = cusp["brs_adv"]
        xp = list(pre["SepYOS"]) + [20]
        # Bands extended to the cusp (TSP-only difference at
        # 20, where both pensions are still zero).
        ax.fill_between(
            xp,
            list(pre["brs_adv_p25"] / 1000)
            + [cu["p25"] / 1000],
            list(pre["brs_adv_p75"] / 1000)
            + [cu["p75"] / 1000],
            alpha=0.38, color=pcolor,
            label="Middle 50% of outcomes",
        )
        ax.fill_between(
            post["SepYOS"], post["brs_adv_p25"] / 1000,
            post["brs_adv_p75"] / 1000,
            alpha=0.38, color=pcolor,
        )
        # Median, broken at the cliff the same way.
        ax.plot(
            xp,
            list(pre["brs_adv_p50"] / 1000)
            + [cu["p50"] / 1000],
            color=pcolor, lw=2, label="Median",
        )
        vested = post["brs_adv_p50"].iloc[0] / 1000
        ax.plot(
            [20], [cu["p50"] / 1000], "o", mfc=tc["bg"],
            mec=pcolor, mew=1.4, zorder=6,
        )
        ax.plot(
            [20, 20], [cu["p50"] / 1000, vested],
            ls=":", color=pcolor, lw=1.1, alpha=0.8,
        )
        ax.plot(
            post["SepYOS"], post["brs_adv_p50"] / 1000,
            color=pcolor, lw=2,
        )
        # Deterministic (03a), broken at the cliff too.
        dpre = curve[curve["SepYOS"] < 20]
        dpost = curve[curve["SepYOS"] >= 20]
        dcusp = (
            drow20["BRS_TSP_PV"] - drow20["H3TSP_PV"]
        ) / 1000
        ax.plot(
            list(dpre["SepYOS"]) + [20],
            list(dpre["BRSAdv"] / 1000) + [dcusp],
            color=fg, ls="--", lw=1.2, label="Deterministic",
        )
        ax.plot(
            dpost["SepYOS"], dpost["BRSAdv"] / 1000,
            color=fg, ls="--", lw=1.2,
        )
    else:
        ax.fill_between(
            mcc["SepYOS"], mcc["brs_adv_p25"] / 1000,
            mcc["brs_adv_p75"] / 1000,
            alpha=0.38, color=pcolor,
            label="Middle 50% of outcomes",
        )
        ax.plot(
            mcc["SepYOS"], mcc["brs_adv_p50"] / 1000,
            color=pcolor, lw=2, label="Median",
        )
        ax.plot(
            curve["SepYOS"], curve["BRSAdv"] / 1000,
            color=fg, ls="--", lw=1.2, label="Deterministic",
        )
    ax.plot(
        [sep_yos], [mc["brs_adv"]["p50"] / 1000], "o",
        color=fg,
    )
    ax.axhline(0, color=fg, linewidth=0.8, linestyle=":")
    ax.axvline(
        sep_yos, color=fg, linewidth=0.8, linestyle=":",
    )
    ax.set_xlabel("Years of Service at Separation")
    ax.set_ylabel("Lifetime Value Advantage (2026 $)")
    ax.set_title(
        "Lifetime Value Difference: BRS vs. High-Three"
    )
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"${abs(v):,.0f}K")
    )
    # All-positive magnitude axis; shade which system leads
    # (light blue = BRS advantage, light maize = High-Three).
    ymin, ymax = ax.get_ylim()
    ax.axhspan(0, ymax, color=BRS_REGION, alpha=0.18, zorder=0)
    ax.axhspan(ymin, 0, color=H3_REGION, alpha=0.18, zorder=0)
    ax.set_ylim(ymin, ymax)
    ax.text(
        0.03, 0.93, "BRS advantage", transform=ax.transAxes,
        fontsize=9, style="italic", color=tc["brs_label"],
    )
    ax.text(
        0.03, 0.07, "High-Three advantage",
        transform=ax.transAxes, fontsize=9, style="italic",
        color=tc["h3_label"],
    )
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

# ----------------------------------------------------------
# Plain-language explanation (Gemini, built-in fallback)
# ----------------------------------------------------------
st.subheader("Explain my numbers")
if st.button("Explain my scenario in plain language"):
    with st.spinner("Writing explanation..."):
        text, source = explain_scenario(
            profile_label=sc.PROFILE_LABELS[profile],
            rank_at_sep=str(rank_at_sep),
            timing_label=timing_label,
            sep_yos=sep_yos,
            sep_age=sep_age,
            member_pct=member_pct,
            mc=mc,
            det=det.to_dict(),
            ctx=ctx,
        )
    st.markdown(esc_md(text))
    st.caption(source)

# ----------------------------------------------------------
# Assumptions
# ----------------------------------------------------------
with st.expander("Model assumptions & limitations"):
    st.markdown(ASSUMPTIONS)
