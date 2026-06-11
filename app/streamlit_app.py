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

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scenario_calcs as sc  # noqa: E402
from explain import explain_scenario  # noqa: E402

# System colors — deliberately distinct from the project's
# profile palette (darkorange / forestgreen / steelblue)
H3_COLOR = "dimgray"
BRS_COLOR = "crimson"

st.set_page_config(
    page_title="BRS vs. High-Three Explorer",
    layout="wide",
)


def fmt_usd(x):
    """$1,234,567 with a true minus sign for negatives."""
    sign = "−" if x < 0 else ""
    return f"{sign}${abs(x):,.0f}"


def esc_md(text):
    """Escape $ so paired dollars don't render as LaTeX math.

    Streamlit markdown (st.markdown / st.caption) treats
    $...$ as math, same as notebook markdown — escape any
    dollar amounts before rendering.
    """
    return text.replace("$", "\\$")


@st.cache_resource
def get_inputs():
    return sc.load_inputs()


@st.cache_data
def cached_curve(points, max_yos, member_rate, disc):
    inputs = get_inputs()
    pay, _ = sc.pay_from_points(
        list(points), max_yos, inputs["basic_pay"]
    )
    entry = sc.ENTRY_AGE[st.session_state["profile"]]
    return sc.deterministic_curve(
        pay, entry, inputs["life_exp"],
        inputs["fund_means"], member_rate, disc,
    )


@st.cache_data
def cached_mc(
    profile, points, max_yos, sep_yos, member_rate, disc,
    n_iter,
):
    inputs = get_inputs()
    pay, _ = sc.pay_from_points(
        list(points), max_yos, inputs["basic_pay"]
    )
    return sc.mc_at_point(
        profile, pay, sc.ENTRY_AGE[profile], sep_yos,
        inputs["life_exp"], inputs["fund_stats"],
        inputs["cola_stats"], member_rate, disc,
        n_iter=n_iter,
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

member_pct = st.sidebar.slider(
    "Your TSP contribution (% of basic pay)",
    min_value=0, max_value=10, value=5, step=1,
    help=(
        "Held equal under both systems to isolate the "
        "government-funded difference. BRS matches up to 4%."
    ),
)
member_rate = member_pct / 100.0

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
entry_age = sc.ENTRY_AGE[profile]
sep_age = entry_age + sep_yos
rank_at_sep = grades.loc[sep_yos]
timing_label = (
    "your timeline" if is_custom else "typical timing"
)

curve = cached_curve(points_key, max_yos, member_rate, disc)
mc = cached_mc(
    profile, points_key, max_yos, sep_yos, member_rate,
    disc, n_iter,
)
det = curve.set_index("SepYOS").loc[sep_yos]
ctx = sc.population_context(inputs, profile, sep_yos)

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

fig, ax = plt.subplots(figsize=(10, 0.9))
for grade, start, end in runs:
    color = (
        "navajowhite"
        if str(grade).startswith("E")
        else "lightsteelblue"
    )
    ax.barh(
        0, end - start + 1, left=start, height=0.8,
        color=color, edgecolor="white",
    )
    ax.text(
        (start + end + 1) / 2, 0, str(grade),
        ha="center", va="center", fontsize=9,
    )
ax.set_xlim(1, sep_yos + 1)
ax.set_yticks([])
ax.set_xlabel("Years of Service", fontsize=9)
for side in ("top", "right", "left"):
    ax.spines[side].set_visible(False)
fig.tight_layout()
st.pyplot(fig)
plt.close(fig)
st.caption(f"Rank timeline ({timing_label})")

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
        f"Monte Carlo P10–P90: {fmt_usd(adv['p10'])} "
        f"to {fmt_usd(adv['p90'])} · mean "
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
        "compounded at the discount rate."
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
ch1, ch2 = st.columns(2)

with ch1:
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(
        curve["SepYOS"], curve["H3Total"] / 1000,
        color=H3_COLOR, linewidth=2, label="High-Three",
    )
    ax.plot(
        curve["SepYOS"], curve["BRSTotal"] / 1000,
        color=BRS_COLOR, linewidth=2, label="BRS",
    )
    for key, color in [
        ("h3_total", H3_COLOR), ("brs_total", BRS_COLOR),
    ]:
        s = mc[key]
        ax.errorbar(
            [sep_yos], [s["p50"] / 1000],
            yerr=[
                [(s["p50"] - s["p10"]) / 1000],
                [(s["p90"] - s["p50"]) / 1000],
            ],
            fmt="o", color=color, capsize=4,
        )
    ax.axvline(
        sep_yos, color="black", linewidth=0.8,
        linestyle=":",
    )
    ax.set_xlabel("Years of Service at Separation")
    ax.set_ylabel("Lifetime Value (2026 $ thousands)")
    ax.set_title(
        "Lifetime Value by System (deterministic path;\n"
        "dots: Monte Carlo median and P10–P90 at your "
        "point)"
    )
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"${x:,.0f}K")
    )
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

with ch2:
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(
        curve["SepYOS"], curve["BRSAdv"] / 1000,
        color="black", linewidth=2,
    )
    adv = mc["brs_adv"]
    ax.errorbar(
        [sep_yos], [adv["p50"] / 1000],
        yerr=[
            [(adv["p50"] - adv["p10"]) / 1000],
            [(adv["p90"] - adv["p50"]) / 1000],
        ],
        fmt="o", color="black", capsize=4,
    )
    ax.axhline(
        0, color="gray", linewidth=0.8, linestyle="--"
    )
    ax.axvline(
        sep_yos, color="black", linewidth=0.8,
        linestyle=":",
    )
    ax.set_xlabel("Years of Service at Separation")
    ax.set_ylabel(
        "Difference, BRS − H3 (2026 $ thousands)"
    )
    ax.set_title(
        "Lifetime Value Difference\n"
        "(above zero: BRS yields more)"
    )
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"${x:,.0f}K")
    )
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
    st.markdown(
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
        "- **Promotion timeline**: rank is asserted by you "
        "(or the typical table), not predicted; pay is "
        "priced from the 2026 DFAS table.\n"
        "- **Out of scope**: reserve retirement, "
        "continuation pay, TSP withdrawal strategy, and "
        "behavioral retention effects.\n"
        "- Force-wide context uses DoD actuarial "
        "separation rates on the standard profiles; your "
        "custom timeline changes your ledger, not the "
        "force-wide stats."
    )
