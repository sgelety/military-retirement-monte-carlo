"""Claude-powered plain-language explanation of app results.

Single Messages API call: the app passes the numbers it already
computed; Claude narrates them under the project's framing rules
(neutral BRS - H3 difference, constant 2026 dollars, no "better").
Reads ANTHROPIC_API_KEY from the environment; the numeric app
works fully without it.
"""

import os

MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """\
You explain U.S. military retirement modeling results in plain
language to service members at a research poster session.

Rules:
- Use ONLY the numbers provided. Never invent, recompute, or
  extrapolate figures.
- Frame results as the neutral "lifetime value difference
  (BRS minus High-Three)". Positive means BRS yields more over a
  lifetime; negative means the legacy High-Three yields more.
  Never call either system "better" — which one favors a member
  depends on career length.
- All dollar figures are net present value at separation in
  constant 2026 dollars. Round to the nearest thousand when
  narrating.
- Write 2-3 short paragraphs: (1) what this member's numbers say
  and the mechanics behind them (the 20-year pension cliff, the
  BRS government TSP match, the 2.5% vs 2.0% multiplier);
  (2) the government's side of the same career and how this
  member fits the force-wide pattern; (3) one sentence on
  uncertainty, using the percentile band provided.
- Plain, direct prose a 22-year-old service member could follow.
  No headers, no bullet lists, no LaTeX, no markdown tables.
"""


def explainer_status():
    """None if the explainer is ready, else a user-facing note."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return (
            "Plain-language explanations need an Anthropic API "
            "key. Set the ANTHROPIC_API_KEY environment variable "
            "and restart — everything else in this app works "
            "without it."
        )
    return None


def _fmt(x):
    return f"-${abs(x):,.0f}" if x < 0 else f"${x:,.0f}"


def _facts(
    profile_label, rank_at_sep, timing_label, sep_yos, sep_age,
    member_pct, mc, det, ctx,
):
    """One scenario as a plain-text fact sheet for the prompt."""
    adv = mc["brs_adv"]
    cm = mc["component_means"]
    pension = (
        "eligible for the lifetime pension (20+ years)"
        if sep_yos >= 20
        else "NOT pension-eligible (separates before 20 years; "
        "under High-Three this member leaves with no "
        "government-funded retirement benefit)"
    )
    return f"""\
Member profile: {profile_label}, separating at {sep_yos} years \
of service (age {sep_age}) as {rank_at_sep} ({timing_label}).
Member TSP contribution: {member_pct}% of basic pay under both \
systems.
Pension status: {pension}.

Member lifetime value (NPV at separation, constant 2026 $):
- Difference (BRS - H3), median: {_fmt(adv['p50'])}
- Difference percentile band (P10 to P90): \
{_fmt(adv['p10'])} to {_fmt(adv['p90'])}
- Components (Monte Carlo means):
  - Pension NPV: High-Three {_fmt(cm['h3_pension'])}, \
BRS {_fmt(cm['brs_pension'])}
  - Member's own TSP (same under both): \
{_fmt(cm['member_tsp'])}
  - Government TSP contributions (BRS only): \
{_fmt(cm['govt_tsp'])}
  - Totals: High-Three {_fmt(cm['h3_total'])}, \
BRS {_fmt(cm['brs_total'])}

Government cost of this career (deterministic, actuarial basis):
- Under High-Three: {_fmt(det['H3_GovtCost'])}
- Under BRS: {_fmt(det['BRS_GovtCost'])}
- DoD savings (H3 - BRS): {_fmt(det['DoD_Savings'])}

Force-wide context ({profile_label} entrants, DoD actuarial \
separation rates, typical careers):
- {ctx['share_pre20_members']:.0%} separate before 20 years; \
they receive only {ctx['share_pre20_spend']:.1%} of expected \
BRS spending
- {ctx['share_reaching_sep']:.0%} of entrants serve \
{sep_yos}+ years
- Expected per-entrant DoD savings from BRS: \
{_fmt(ctx['expected_savings'])}
"""


def explain_scenario(
    profile_label, rank_at_sep, timing_label, sep_yos, sep_age,
    member_pct, mc, det, ctx,
):
    """Return a plain-language narrative of one scenario."""
    import anthropic

    facts = _facts(
        profile_label, rank_at_sep, timing_label, sep_yos,
        sep_age, member_pct, mc, det, ctx,
    )
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Explain these retirement-system "
                        "modeling results:\n\n" + facts
                    ),
                }
            ],
        )
        return "".join(
            block.text
            for block in response.content
            if block.type == "text"
        )
    except anthropic.APIError as err:
        return (
            f"Explanation unavailable "
            f"({type(err).__name__}: {err.message}). "
            "The numeric results above are unaffected."
        )
