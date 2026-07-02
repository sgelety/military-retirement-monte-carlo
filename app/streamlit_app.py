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
from matplotlib.legend_handler import HandlerBase
from matplotlib.lines import Line2D
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

# Monte Carlo iterations — fixed at the value validated for
# convergence in notebook 03b (20K->40K shift < 1% of the
# P10-P90 spread). Not user-adjustable: the only effect of a
# lower count is noisier bands, with no benefit to the reader.
N_ITER = 20_000

# Annual force accessions for scaling per-entrant savings to a
# whole cohort, matching nb04/nb05. Prior-enlisted officers are
# not a separate line: they enter as enlisted accessions, so a
# third line would double-count them.
ACCESSIONS = {"Enlisted": 140_000, "Officer": 18_000}

st.set_page_config(
    page_title="BRS vs. High-Three Explorer",
    layout="wide",
)


def fmt_usd(x):
    """$1,234,567 with a true minus sign for negatives."""
    sign = "−" if x < 0 else ""
    return f"{sign}${abs(x):,.0f}"


def theme():
    """Fixed chart palette: the notebook (light) colors on a solid
    white figure background, applied regardless of the app's light
    or dark mode. Each chart is a self-contained white panel, so it
    renders identically and its titles/labels stay legible on either
    page — instead of depending on runtime theme detection
    (``st.context.theme.type``), which left text near-white on a
    white page when the detected theme and the actual page
    disagreed. Fills are near-opaque so the colors read vividly
    rather than washing out; the single-series difference fan
    (the only banded chart) is the most opaque.
    """
    return {
        "fg": "#262730",
        "bg": "#ffffff",
        "brs": BRS_COLOR,
        "brs_label": "#00274C",
        "h3_label": "#6b540f",
        "profiles": PROFILE_COLORS,
        "region_a": 0.18,
        "diff_a": 0.85,
    }


def theme_fg():
    """Foreground (text/axes) color for the charts."""
    return theme()["fg"]


def apply_chart_theme(tc):
    """Give every matplotlib figure a solid white background with
    dark text/axes/ticks/grid via rcParams, so each chart is a
    self-contained panel that stays legible on a light or dark
    page (rather than a transparent figure that inherits — and can
    clash with — the page color).
    """
    plt.rcParams.update({
        "figure.facecolor": tc["bg"],
        "axes.facecolor": tc["bg"],
        "savefig.facecolor": tc["bg"],
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
# Static copy — long, unchanging blurbs for the expanders and
# the top-of-page summary. Kept here (rather than mid-layout)
# so the render flow below reads as structure. Pass through
# esc_md() at render time.
# ----------------------------------------------------------
SUMMARY = (
    "Compare the Blended Retirement System (BRS) against the "
    "legacy High-Three pension for any military career: what "
    "each is worth to you over a lifetime, and what each costs "
    "the government, all in today's 2026 dollars."
)

ABOUT = (
    "As a U.S. Coast Guard officer, I faced the one-time 2018 "
    "choice between the legacy High-Three pension and the new "
    "Blended Retirement System, and this project is my attempt "
    "to answer that question with simulation instead of a gut "
    "call. I built it independently for the University of "
    "Michigan AI & Data Science Graduate Certificate (2026).\n\n"
    "The choice itself is now historical: everyone who joined "
    "since 2018 is enrolled in BRS automatically. But the "
    "comparison still matters, both for those living with the "
    "2018 decision who want to see how it is likely to play "
    "out, and as a way to judge the reform itself — whether it "
    "actually saves money, and who comes out ahead or "
    "behind.\n\n"
    "The full analysis and source code are on "
    "[GitHub](https://github.com/sgelety/"
    "military-retirement-monte-carlo). I'm also on "
    "[LinkedIn](https://www.linkedin.com/in/steven-gelety/) — "
    "feel free to connect or reach out about the project.\n\n"
    "**How it was built.** I designed the model and made every "
    "analysis decision: which systems to compare, how to treat "
    "the 20-year pension cliff, which variables to simulate and "
    "how, and how to value the cost to the government. Claude "
    "(Anthropic's AI) helped me write and debug the code that "
    "carries out those decisions. The methodology, judgment "
    "calls, and conclusions are entirely my own.\n\n"
    "**Not financial advice.** This is for education and "
    "illustration only. It models typical careers with "
    "simplifying assumptions and can't reflect your full "
    "situation, so consult a personal financial counselor or "
    "qualified advisor before making any retirement decision."
)

HOW_IT_WORKS = (
    "**What's compared.** High-Three pays a pension of 2.5% × "
    "years served × your highest-36-months average pay, but "
    "only if you reach 20 years — leave at 19 and you get "
    "nothing. BRS pays a smaller pension (2.0% per year, same "
    "20-year rule) but adds money to your Thrift Savings Plan "
    "(TSP, the military's 401(k)) that you keep whenever you "
    "leave: 1% of pay automatically, plus a match on your "
    "contributions (full match at 5%).\n\n"
    "**Your pay.** From your profile and promotion timeline, "
    "the app builds your year-by-year basic pay from the 2026 "
    "military pay table — typical promotion timing, or your "
    "own edits in the sidebar.\n\n"
    "**20,000 futures.** Nobody knows future returns, "
    "inflation, or how long they'll live, so the app simulates "
    "20,000 versions of your future and varies all three: "
    "**TSP returns** (from the history of the L funds, "
    "following the same age-based glide path a real L fund "
    "does), **inflation** (from a century of U.S. data — it "
    "drives pay raises, pension COLAs, and the conversion to "
    "today's dollars), and **lifespan** (from SSA actuarial "
    "tables, since a pension's value depends on how many years "
    "it pays). The median is the middle outcome; the band on "
    "the difference chart shows the middle 50% or 80% of "
    "them.\n\n"
    "**\"2026 dollars at separation.\"** A dollar promised in "
    "2055 is worth less than one today, so every future "
    "payment is discounted back to your separation date "
    "(5%/yr) and stated in 2026 purchasing power — so a "
    "pension stream and a TSP balance can be compared "
    "directly.\n\n"
    "**Equal contributions.** Your own TSP rate is set the "
    "same under both systems on purpose: your savings follow "
    "you either way, so holding them equal isolates what the "
    "*government* adds — the match and the pension. That's "
    "also why the difference stops moving above 5%: the match "
    "is maxed.\n\n"
    "**The government side** values the same career as an "
    "actuary would: the pension discounted at 5%, plus the "
    "government's TSP deposits compounded at that rate. "
    "Force-wide figures weight each separation year by DoD's "
    "historical rates.\n\n"
    "**Left out:** taxes, the BRS continuation-pay bonus "
    "(excluding it slightly favors High-Three), reserve/guard "
    "retirement, and withdrawal strategy. Promotion timing is "
    "asserted by you, not predicted.\n\n"
    "*Sources: DFAS 2026 pay table, DoD Office of the Actuary "
    "separation rates, TSP.gov fund history, SSA 2022 life "
    "tables, BLS CPI (1913–present).*"
)

ASSUMPTIONS = (
    "**How the numbers are computed**\n\n"
    "- **Reporting**: net present value at separation (5% "
    "discount rate), in constant 2026 dollars.\n"
    "- **TSP** (Thrift Savings Plan, the military's 401(k)): "
    "you contribute the same rate under both systems; BRS adds "
    "1% automatic plus up to 4% match (from year 3). Balances "
    "ride the Lifecycle (L) fund glide path — stock-heavy when "
    "you're young, shifting to safer funds as you near 60 — "
    "and are priced at the discount rate in the drawdown years "
    "after 60.\n"
    "- **Center-path figures** (the government cost, and the "
    "first-year pension and TSP-at-separation in your table): "
    "one fixed calculation — 2.75% COLA / pay growth (DoD "
    "actuarial), historical-mean returns, SSA 2022 male life "
    "expectancy. Not simulated, because the government cost is "
    "valued the way DoD budgets it (present value of the "
    "promise under fixed assumptions) and the other two are "
    "single snapshots at separation; the return, inflation, "
    "and lifespan uncertainty matters for the decades-long "
    "lifetime totals, which is where the simulation comes "
    "in.\n"
    "- **Simulated figures** (the median lifetime values and "
    "the chart band): 20,000 draws of TSP returns from "
    "historical fund data, lifetime-average COLA (rolling "
    "30-yr CPI fit), and age at death from the SSA 2022 male "
    "table.\n\n"
    "**What your settings change**\n\n"
    "- **Entry age** (default 18 enlisted / 22 officer / 18 "
    "prior-enlisted) shifts every age-based input: the glide "
    "path, how long your balance keeps growing toward age 60, "
    "and the life-expectancy lookup.\n"
    "- **Promotion timeline**: rank is asserted by you (or the "
    "typical table), not predicted; pay comes from the 2026 "
    "DFAS table.\n"
    "- **Expected lifespan**: re-centers your sampled age at "
    "death by the chosen years (0 = the SSA average for your "
    "age), keeping the shape and spread. It moves only your "
    "value — the government's cost stays at the cohort "
    "average.\n"
    "- **Market outlook**: a uniform ±2 pp shift of the mean "
    "returns — a sustained, decades-long bull or bear regime, "
    "separate from the simulation's year-to-year luck. It "
    "doesn't move the government cost.\n\n"
    "**Scope & limitations**\n\n"
    "- **Out of scope**: taxes, reserve retirement, "
    "continuation pay, TSP withdrawal strategy, and behavioral "
    "retention effects.\n"
    "- **Force-wide figures** use DoD separation rates on the "
    "standard profiles; a custom timeline changes your own "
    "results, not the force-wide stats."
)


@st.cache_resource
def get_inputs():
    return sc.load_inputs()


@st.cache_data
def cached_curve(profile, points, max_yos, entry_age,
                 member_rate, disc, outlook, life_offset):
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
        death_age_offset=life_offset,
    )


@st.cache_data
def cached_mc_curve(
    profile, points, max_yos, entry_age, member_rate, disc,
    outlook, life_offset,
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
        member_rate, disc, n_iter=N_ITER,
        death_age_offset=life_offset,
    )


@st.cache_data
def cached_mc_cusp(
    profile, points, max_yos, entry_age, member_rate, disc,
    outlook,
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
        member_rate, disc, n_iter=N_ITER,
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

entry_age = st.sidebar.slider(
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

sep_yos = st.sidebar.slider(
    "Years of service at separation",
    min_value=sc.MIN_SEP_YOS,
    max_value=max_yos,
    value=min(20, max_yos),
    step=1,
    help=(
        "The year you leave service. 20 years is the pension "
        "cliff: reach it and you vest a lifetime pension under "
        "both systems; leave before 20 and High-Three pays no "
        "retirement at all, while BRS still leaves you the "
        "government's TSP contributions."
    ),
)

life_offset = st.sidebar.slider(
    "Expected lifespan vs. average (years)",
    min_value=-15, max_value=15, value=0, step=1,
    help=(
        "0 keeps the SSA 2022 average lifespan for someone "
        "your age. Move right if you expect to live longer "
        "than average (+5 = about five years beyond), left if "
        "shorter. This re-centers your simulated lifespan while "
        "keeping the realistic spread and shape. A longer life "
        "favors High-Three (its larger pension keeps paying); a "
        "shorter life favors BRS (you keep the TSP regardless). "
        "It changes only your personal value — the government's "
        "actuarial cost is priced on the whole cohort, not your "
        "own longevity, so the government ledger doesn't move."
    ),
)

_life_mean = round(float(
    inputs["life_exp"].loc[
        inputs["life_exp"]["Age"] == entry_age + sep_yos,
        "MaleTotalAge",
    ].squeeze()
))
if life_offset:
    st.sidebar.caption(
        f"Expected lifespan: age {_life_mean} → adjusted: "
        f"age {_life_mean + life_offset}. That's the *average* "
        "— each simulated future still draws its own lifespan, "
        "spread years above and below it, so nothing is pinned "
        "to one exact age."
    )
else:
    st.sidebar.caption(
        f"Expected lifespan: age {_life_mean} (SSA average for "
        "your age). Each simulated future still draws its own "
        "lifespan, spread years above and below this."
    )

member_pct = st.sidebar.slider(
    "Your Thrift Savings Plan (TSP) contribution (% of basic pay)",
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

# Difference-chart band width. The radio itself is rendered
# under chart 2 (it's a view toggle, not an input), but its
# value is needed to draw that chart, so read it from session
# state here and instantiate the widget with this key below.
BAND_PCTS = {
    "Middle 50%": ("p25", "p75"),
    "Middle 80%": ("p10", "p90"),
}
band_choice = st.session_state.get("band_view", "Middle 50%")
band_lo, band_hi = BAND_PCTS[band_choice]
band_label = f"{band_choice} of outcomes"

with st.sidebar.expander("Advanced"):
    disc_pct = st.slider(
        "Discount rate (%)",
        min_value=3.0, max_value=7.0, value=5.0, step=0.5,
        help=(
            "How much future dollars are worth today. A "
            "pension paid 30 years from now is worth less to "
            "you than the same amount today, and this rate "
            "sets how much less when adding up a lifetime of "
            "payments. A higher rate discounts the far-off "
            "pension more heavily, which favors BRS's earlier "
            "TSP money; a lower rate favors the High-Three "
            "pension. The 5% default matches the project's "
            "notebooks; it does not change the government "
            "ledger, which is figured on an actuarial basis."
        ),
    )
    disc = disc_pct / 100.0

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
    disc, outlook, life_offset,
)
mcc = cached_mc_curve(
    profile, points_key, max_yos, entry_age, member_rate,
    disc, outlook, life_offset,
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
        disc, outlook,
    )
    if has_cliff
    else None
)

# ----------------------------------------------------------
# Header + career snapshot
# ----------------------------------------------------------
st.title("Beyond the Pension Cliff")
st.caption(esc_md(SUMMARY))

with st.expander("About this project", expanded=True):
    st.markdown(esc_md(ABOUT))

st.subheader("Career overview")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Profile", sc.PROFILE_LABELS[profile])
c2.metric("Rank at separation", str(rank_at_sep))
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

# ----------------------------------------------------------
# Ledgers
# ----------------------------------------------------------
left, right = st.columns(2)

with left:
    st.subheader("What it's worth to you")
    adv = mc["brs_adv"]
    med = adv["p50"]
    # Lead with the payoff as a metric "cell" — a computed value
    # that visibly updates with the inputs, set apart from the
    # static prose. The label names whichever system comes out
    # ahead; the value is the median lifetime gap.
    leader = "BRS" if med >= 0 else "High-Three"
    st.metric(
        f"{leader} advantage over a lifetime (median)",
        fmt_usd(abs(med)),
    )
    if sep_yos < 20:
        st.info(
            f"At {sep_yos} years you separate **before the "
            "20-year pension cliff**: High-Three would pay you "
            "no retirement at all, while BRS still leaves you "
            "the government's TSP contributions."
        )
    gov_value = pd.DataFrame(
        {
            "First Year's Pension": [
                det["H3PensionAnnual"], det["BRSPensionAnnual"],
            ],
            "Govt. TSP at separation": [
                0.0, det["GovtTSP_AtSep"],
            ],
            "Median Lifetime Value": [
                mc["h3_govt"]["p50"], mc["brs_govt"]["p50"],
            ],
        },
        index=["High-Three", "BRS"],
    )
    st.dataframe(
        gov_value.style.format(fmt_usd), width="content"
    )
    st.caption("All amounts are in today's (2026) dollars.")
    st.caption(
        "Government-funded value only — your own TSP "
        "contributions are the same under both systems, so they "
        "cancel out. The first two columns are values at "
        f"separation; lifetime value is the median across "
        f"{N_ITER:,} simulated futures. That median advantage is "
        "figured future-by-future, so it won't exactly equal the "
        "gap between the two lifetime-value figures."
    )
    if life_offset:
        life_mean = float(
            inputs["life_exp"].loc[
                inputs["life_exp"]["Age"] == sep_age,
                "MaleTotalAge",
            ].squeeze()
        )
        st.caption(
            f"Life expectancy set to {life_offset:+d} yr vs. "
            f"average — about age "
            f"{life_mean + life_offset:.0f} here (SSA average ≈ "
            f"{life_mean:.0f}). This shifts only your value; the "
            "government's cost stays at the cohort average."
        )

with right:
    st.subheader("What it costs the government")
    sav = det["DoD_Savings"]
    # Lead with the payoff as a metric "cell" (mirrors the value
    # panel); the subtraction table below shows where it comes
    # from.
    if sav >= 0:
        st.metric("Cost reduction under BRS", fmt_usd(sav))
    else:
        st.metric("Cost increase under BRS", fmt_usd(-sav))
    save_label = (
        "= Cost reduction under BRS" if sav >= 0
        else "= Cost increase under BRS"
    )
    # Laid out as a subtraction: High-Three cost − BRS cost =
    # what BRS saves. Mirrors the value table on the left.
    cost = pd.DataFrame(
        {"Amount": [
            det["H3_GovtCost"],
            det["BRS_GovtCost"],
            abs(sav),
        ]},
        index=[
            "Cost under High-Three",
            "− Cost under BRS",
            save_label,
        ],
    )
    st.dataframe(
        cost.style.format(fmt_usd), width="content"
    )
    st.caption("All amounts are in today's (2026) dollars.")
    st.caption(
        "What the government expects to pay for this career. "
        "These price the average member, not one person's luck, "
        "so they won't match your own simulated value. Market "
        "outlook doesn't move them: the government's cost doesn't "
        "depend on investment performance."
    )

# ----------------------------------------------------------
# Charts
# ----------------------------------------------------------
class _VLineHandler(HandlerBase):
    """Render a legend entry as a short vertical line.

    The separation marker is a vertical line on the chart; a
    vertical swatch keeps it distinct from the horizontal data
    lines.
    """

    def create_artists(self, legend, orig_handle, xdescent,
                        ydescent, width, height, fontsize,
                        trans):
        x = width / 2.0
        line = Line2D(
            [x, x], [0, height],
            linestyle=orig_handle.get_linestyle(),
            linewidth=orig_handle.get_linewidth(),
            color=orig_handle.get_color(),
            alpha=orig_handle.get_alpha(),
        )
        line.set_transform(trans)
        return [line]


def legend_with_sep(ax, sep_yos, fg, **kw):
    """Axes legend plus a vertical-line entry for the
    separation reference line (drawn vertical to set it apart
    from the horizontal data lines)."""
    sep = Line2D([], [], color=fg, lw=1.8, ls="--", alpha=0.9)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles + [sep],
        labels + [f"Your separation (YOS {sep_yos})"],
        handler_map={sep: _VLineHandler()},
        fontsize=8, **kw,
    )


st.subheader("Where your career sits on the cliff")
life_note = (
    f" Expected lifespan: {life_offset:+d} yr vs. average."
    if life_offset else ""
)
st.caption(
    f"Across every separation year, from {N_ITER:,} simulated "
    "futures. Both charts show government-funded value only "
    "(pension plus government TSP) — your own contributions are "
    f"equal under both systems, so they cancel out.{life_note}"
)
# Stacked vertically, not side-by-side: the two charts share
# the x-axis (Years of Service), not the y-axis,
# so aligning their x-axes top-to-bottom lets you read a given
# separation year — the 20-year cliff, your-YOS line — straight
# down both. On the wide layout each also gets the full page
# width, which the dense 4–40 YOS axis needs.
ch1 = st.container()
ch2 = st.container()

with ch1:
    # Structure/levels only: the median value per system, no
    # bands. The spread of each system's value in isolation is
    # dominated by shared mortality/COLA luck that cancels in
    # the BRS-vs-H3 comparison, so the uncertainty story belongs
    # on the difference chart (ch2), not on two overlapping
    # marginal bands here.
    fig, ax = plt.subplots(figsize=(11, 4.5))
    pre = mcc[mcc["SepYOS"] < 20]
    post = mcc[mcc["SepYOS"] >= 20]
    for key, color, label in [
        ("h3_govt", H3_COLOR, "High-Three Median"),
        ("brs_govt", tc["brs"], "BRS Median"),
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
            ax.plot(
                mcc["SepYOS"], mcc[f"{key}_p50"] / 1000,
                color=color, lw=2, label=label,
                path_effects=line_pe,
            )
        ax.plot(
            [sep_yos], [mc[key]["p50"] / 1000], "o",
            color=color,
        )
    # Label each selected-point median ($M, 2 dp), offset toward
    # chart center so the text clears the panel edge; the higher
    # value sits above its dot and the lower below, so the two
    # don't collide. Maize is unreadable as text on white, so the
    # H3 label uses dark gold (tc["h3_label"]).
    x_lo, x_hi = ax.get_xlim()
    dx, lab_ha = ((-6, "right") if sep_yos > (x_lo + x_hi) / 2
                  else (6, "left"))
    pts = {
        "h3_govt": (mc["h3_govt"]["p50"], tc["h3_label"]),
        "brs_govt": (mc["brs_govt"]["p50"], tc["brs_label"]),
    }
    hi_key = max(pts, key=lambda k: pts[k][0])
    for pkey, (pval, ptext) in pts.items():
        above = pkey == hi_key
        ax.annotate(
            f"${pval / 1e6:.2f}M",
            xy=(sep_yos, pval / 1000),
            xytext=(dx, 9 if above else -9),
            textcoords="offset points",
            ha=lab_ha, va="bottom" if above else "top",
            fontsize=8, fontweight="bold", color=ptext,
            bbox=dict(
                boxstyle="round,pad=0.2", fc="white",
                ec="none", alpha=0.75,
            ),
            zorder=7,
        )
    ax.axvline(
        sep_yos, color=fg, linewidth=1.8, linestyle="--",
        alpha=0.9, zorder=5,
    )
    ax.set_xlabel("Years of Service")
    ax.set_ylabel("Lifetime Value (2026 $)")
    ax.set_title("Total Lifetime Value")
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"${v / 1000:,.1f}M")
    )
    legend_with_sep(ax, sep_yos, fg)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

with ch2:
    pcolor = tc["profiles"][profile]
    # The median sits on a near-opaque fill of the same profile
    # color; a thin dark outline keeps the line readable on it.
    med_pe = [pe.Stroke(linewidth=3.4, foreground=fg), pe.Normal()]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    pre = mcc[mcc["SepYOS"] < 20]
    post = mcc[mcc["SepYOS"] >= 20]
    if has_cliff:
        cu = cusp["brs_adv"]
        xp = list(pre["SepYOS"]) + [20]
        # Bands extended to the cusp (TSP-only difference at
        # 20, where both pensions are still zero).
        ax.fill_between(
            xp,
            list(pre[f"brs_adv_{band_lo}"] / 1000)
            + [cu[band_lo] / 1000],
            list(pre[f"brs_adv_{band_hi}"] / 1000)
            + [cu[band_hi] / 1000],
            alpha=tc["diff_a"], color=pcolor,
            label=band_label,
        )
        ax.fill_between(
            post["SepYOS"], post[f"brs_adv_{band_lo}"] / 1000,
            post[f"brs_adv_{band_hi}"] / 1000,
            alpha=tc["diff_a"], color=pcolor,
        )
        # Median, broken at the cliff the same way.
        ax.plot(
            xp,
            list(pre["brs_adv_p50"] / 1000)
            + [cu["p50"] / 1000],
            color=pcolor, lw=2, label="Median",
            path_effects=med_pe,
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
            color=pcolor, lw=2, path_effects=med_pe,
        )
    else:
        ax.fill_between(
            mcc["SepYOS"], mcc[f"brs_adv_{band_lo}"] / 1000,
            mcc[f"brs_adv_{band_hi}"] / 1000,
            alpha=tc["diff_a"], color=pcolor,
            label=band_label,
        )
        ax.plot(
            mcc["SepYOS"], mcc["brs_adv_p50"] / 1000,
            color=pcolor, lw=2, label="Median",
            path_effects=med_pe,
        )
    ax.plot(
        [sep_yos], [mc["brs_adv"]["p50"] / 1000], "o",
        color=fg,
    )
    ax.axhline(0, color=fg, linewidth=0.8, linestyle=":")
    ax.axvline(
        sep_yos, color=fg, linewidth=1.8, linestyle="--",
        alpha=0.9, zorder=5,
    )
    ax.set_xlabel("Years of Service")
    ax.set_ylabel("Lifetime Value Advantage (2026 $)")
    # Extra title pad leaves room for the legend, which sits
    # between the title and the plot area (set below).
    ax.set_title("Lifetime Value Difference", pad=34)
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"${abs(v):,.0f}K")
    )
    # Fix the y-axis to the widest (80%) band extent, regardless
    # of the selected band width, so toggling 50%/80% rescales
    # nothing — the median curve stays put and the narrower 50%
    # band just sits inside the same frame, making the change in
    # spread easy to see. Always include 0 so both advantage
    # regions show.
    y_cands = [
        0.0,
        (mcc["brs_adv_p10"] / 1000).min(),
        (mcc["brs_adv_p90"] / 1000).max(),
        mc["brs_adv"]["p50"] / 1000,
    ]
    if has_cliff:
        y_cands += [
            cusp["brs_adv"]["p10"] / 1000,
            cusp["brs_adv"]["p90"] / 1000,
        ]
    y_lo, y_hi = min(y_cands), max(y_cands)
    pad = 0.05 * (y_hi - y_lo)
    # All-positive magnitude axis; shade which system leads
    # (light blue = BRS advantage, light maize = High-Three).
    ymin, ymax = y_lo - pad, y_hi + pad
    ax.axhspan(
        0, ymax, color=BRS_REGION, alpha=tc["region_a"], zorder=0
    )
    ax.axhspan(
        ymin, 0, color=H3_REGION, alpha=tc["region_a"], zorder=0
    )
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
    # Legend above the plot, between it and the title (not in a
    # corner): the difference fan is often wide and crosses the
    # whole panel, so any in-axes corner can collide with it.
    # Sitting it just above the top spine keeps the plot width
    # unchanged, so the x-axis still aligns with the chart above.
    # Streamlit saves with bbox_inches="tight", so it's not
    # clipped.
    legend_with_sep(
        ax, sep_yos, fg,
        loc="lower center", bbox_to_anchor=(0.5, 1.0),
        ncol=3,
    )
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    # Band-width view toggle, under this chart. It is a view
    # control rather than a model input, so it lives here instead
    # of the sidebar; session_state["band_view"] feeds the draw
    # above on the next rerun. Streamlit can't truly center the
    # radio's contents (they left-align inside whatever column
    # holds them), so the spacer ratio just nudges it toward the
    # middle: a wider left spacer starts the toggle further right.
    _, mid, _ = st.columns([2, 2, 1])
    with mid:
        st.radio(
            "Uncertainty band",
            list(BAND_PCTS),
            key="band_view",
            horizontal=True,
            help=(
                "How much of the simulated spread the shaded "
                "band covers: the middle 50% (the tighter, "
                "more typical range) or the middle 80% (wider, "
                "reaching further into the good- and bad-luck "
                "tails)."
            ),
        )

# ----------------------------------------------------------
# Across the force — the zoom-out from this one career to the
# whole yearly intake of entrants. Sits after the charts: the
# cliff charts show value/cost at every separation year, and
# these are those same per-year numbers weighted by how many
# members actually leave at each year (DoD separation rates).
# ----------------------------------------------------------
st.subheader("Across the force")
reach20 = {
    p: sc.population_context(inputs, p, 20)["share_reaching_sep"]
    for p in ("Enlisted", "Officer")
}
st.caption(
    "Expected government cost for each person who joins, "
    "weighted by how often members separate (DoD rates). BRS "
    "costs less for every profile, but the savings are far "
    "larger for officers than enlisted. That's because only "
    f"about {reach20['Enlisted']:.0%} of enlisted reach 20 "
    f"years and draw a pension, versus {reach20['Officer']:.0%} "
    "of officers."
)

# Government cost per entrant, High-Three vs BRS, for all three
# profiles — the fiscal story across the force. System colors
# (maize H3 / navy BRS) match the government ledger above.
# These expected costs are weighted over every career length,
# so they don't depend on the separation slider and the chart
# is stable as it moves.
tc = theme()
fg = tc["fg"]
order = list(tc["profiles"])  # Enlisted, PEO, Officer
pctx = {
    p: sc.population_context(inputs, p, sep_yos) for p in order
}
xmax = max(c["expected_h3_cost"] for c in pctx.values()) / 1000
fig, ax = plt.subplots(figsize=(10, 3.3))
for i, p in enumerate(order):
    cy = len(order) - 1 - i  # Enlisted on top
    c = pctx[p]
    ax.barh(
        cy + 0.19, c["expected_h3_cost"] / 1000, height=0.34,
        color=H3_COLOR, edgecolor=BRS_COLOR, linewidth=0.5,
        zorder=3,
    )
    ax.barh(
        cy - 0.19, c["expected_brs_cost"] / 1000, height=0.34,
        color=BRS_COLOR, edgecolor=BRS_COLOR, linewidth=0.5,
        zorder=3,
    )
    ax.text(
        xmax * 1.04, cy,
        f"saves ${c['expected_savings'] / 1000:,.0f}K",
        va="center", ha="left", fontsize=9, fontweight="bold",
        color=fg,
    )
ax.set_xlim(0, xmax * 1.32)
ax.set_yticks(range(len(order)))
ax.set_yticklabels(
    [sc.PROFILE_LABELS[p] for p in reversed(order)]
)
ax.xaxis.set_major_formatter(
    plt.FuncFormatter(lambda v, _: f"${v:,.0f}K")
)
ax.set_xlabel("Expected cost per entrant (2026 $)")
ax.tick_params(length=0)
for side in ("top", "right", "left"):
    ax.spines[side].set_visible(False)
ax.grid(True, axis="x", alpha=0.3)
ax.set_axisbelow(True)
ax.legend(
    handles=[
        Patch(facecolor=H3_COLOR, edgecolor=BRS_COLOR,
              linewidth=0.5, label="High-Three"),
        Patch(facecolor=BRS_COLOR, edgecolor=BRS_COLOR,
              linewidth=0.5, label="BRS"),
    ],
    loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2,
    fontsize=8, frameon=False,
)
fig.tight_layout()
st.pyplot(fig)
plt.close(fig)

# Scale per-entrant costs to a full annual cohort — the
# project's headline aggregate. Enlisted + Officer accessions
# only (PEOs are inside the enlisted line); deterministic, to
# match the per-entrant chart above. Deriving the saving as the
# difference keeps the from/to and the saving arithmetically
# consistent at the displayed precision.
total_h3 = sum(
    pctx[p]["expected_h3_cost"] * n
    for p, n in ACCESSIONS.items()
)
total_brs = sum(
    pctx[p]["expected_brs_cost"] * n
    for p, n in ACCESSIONS.items()
)
total_save = total_h3 - total_brs
st.markdown(esc_md(
    "**Scaled to one year's cohort** (about 140,000 enlisted "
    "and 18,000 officers), BRS lowers the government's cost of "
    f"retirement benefits from about **${total_h3 / 1e9:.1f} "
    f"billion to ${total_brs / 1e9:.1f} billion** — roughly "
    f"**${total_save / 1e9:.1f} billion** less."
))
st.caption(
    "Per-entrant savings times annual accessions; "
    "prior-enlisted officers count as enlisted, not a separate "
    "line."
)

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
# Reference detail — the plain-language method and the
# technical fine print, both at the bottom for readers who
# want depth after seeing their own numbers.
# ----------------------------------------------------------
with st.expander("How this works — where these numbers come from"):
    st.markdown(esc_md(HOW_IT_WORKS))
with st.expander("Model assumptions & limitations"):
    st.markdown(ASSUMPTIONS)

# Footer — author + contact links, repeated here (also in the
# About block up top) so they're reachable after using the tool
# even if the About expander is collapsed.
st.divider()
st.caption(
    "Built by Steven Gelety · "
    "[GitHub](https://github.com/sgelety/"
    "military-retirement-monte-carlo) · "
    "[LinkedIn](https://www.linkedin.com/in/steven-gelety/)"
)
