"""Plain-language explanation of app results.

Two-tier chain, so the explain button always works:

1. **Gemini 2.5 Flash** (free API tier) when GEMINI_API_KEY or
   GOOGLE_API_KEY is set — live LLM narration of the numbers
   the app computed.
2. **Built-in summary** otherwise (no key, rate-limited, or any
   API error): a deterministic narrative generated locally from
   the same numbers. Zero dependencies, works offline forever.

Both tiers follow the project's framing rules: the neutral
"lifetime value difference (BRS - H3)", constant 2026 dollars,
and no claim that either system is "better". The LLM is given
every number it may cite and instructed never to invent figures.
"""

import os

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1beta/models/{GEMINI_MODEL}:generateContent"
)

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


def _gemini_key():
    return os.environ.get("GEMINI_API_KEY") or os.environ.get(
        "GOOGLE_API_KEY"
    )


def _fmt(x):
    return f"-${abs(x):,.0f}" if x < 0 else f"${x:,.0f}"


def _fmt_k(x):
    """Round to the nearest thousand for narrative prose."""
    sign = "-" if x < 0 else ""
    return f"{sign}${abs(round(x, -3)):,.0f}"


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
- Difference, middle 50% (P25 to P75): \
{_fmt(adv['p25'])} to {_fmt(adv['p75'])}
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


def _explain_gemini(facts):
    """Live Gemini call. Returns text, or raises on any error."""
    import requests

    body = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "Explain these retirement-system "
                            "modeling results:\n\n" + facts
                        )
                    }
                ],
            }
        ],
    }
    resp = requests.post(
        GEMINI_URL,
        json=body,
        headers={"x-goog-api-key": _gemini_key()},
        timeout=60,
    )
    resp.raise_for_status()
    parts = resp.json()["candidates"][0]["content"]["parts"]
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise ValueError("empty Gemini response")
    return text


def _explain_builtin(
    profile_label, rank_at_sep, timing_label, sep_yos, sep_age,
    member_pct, mc, det, ctx,
):
    """Deterministic narrative built locally from the numbers."""
    adv = mc["brs_adv"]
    cm = mc["component_means"]
    med = adv["p50"]
    direction = (
        "in favor of BRS"
        if med >= 0
        else "in favor of the legacy High-Three"
    )

    if sep_yos < 20:
        p1 = (
            f"Separating at {sep_yos} years as {rank_at_sep} "
            f"({timing_label}), this {profile_label.lower()} "
            "career ends before the 20-year pension cliff, so "
            "neither system pays a pension. Under High-Three "
            "the member leaves with only their own TSP savings "
            f"(about {_fmt_k(cm['member_tsp'])}); under BRS the "
            "government's automatic 1% and matching "
            "contributions add about "
            f"{_fmt_k(cm['govt_tsp'])} more. The median "
            "lifetime value difference (BRS − H3) is "
            f"{_fmt_k(med)} — {direction}."
        )
    else:
        p1 = (
            f"Separating at {sep_yos} years as {rank_at_sep} "
            f"({timing_label}), this {profile_label.lower()} "
            "career clears the 20-year cliff and earns a "
            "lifetime pension under both systems. High-Three "
            "pays 2.5% of the high-three pay base per year of "
            "service versus 2.0% under BRS (pension NPV "
            f"{_fmt_k(cm['h3_pension'])} vs "
            f"{_fmt_k(cm['brs_pension'])}), while BRS adds "
            f"about {_fmt_k(cm['govt_tsp'])} in government TSP "
            "contributions. Netting the two, the median "
            "lifetime value difference (BRS − H3) is "
            f"{_fmt_k(med)} — {direction}."
        )

    sav = det["DoD_Savings"]
    if sav >= 0:
        sav_txt = (
            f"so BRS saves the government {_fmt_k(sav)} on "
            "this career"
        )
    else:
        sav_txt = (
            f"so BRS costs the government {_fmt_k(-sav)} more "
            "for this career"
        )
    p2 = (
        "On the government's side, this career costs "
        f"{_fmt_k(det['H3_GovtCost'])} under High-Three and "
        f"{_fmt_k(det['BRS_GovtCost'])} under BRS — {sav_txt}. "
        f"Across the force, {ctx['share_pre20_members']:.0%} of "
        f"{profile_label.lower()} entrants separate before 20 "
        "years and receive only "
        f"{ctx['share_pre20_spend']:.1%} of expected BRS "
        f"spending; about {ctx['share_reaching_sep']:.0%} of "
        f"entrants serve {sep_yos} or more years, and the "
        "expected per-entrant saving from BRS is "
        f"{_fmt_k(ctx['expected_savings'])}."
    )

    p3 = (
        "These figures are medians across 20,000 simulated "
        "futures; the middle 50% of outcomes for the difference "
        f"runs from {_fmt_k(adv['p25'])} to "
        f"{_fmt_k(adv['p75'])}, in constant 2026 dollars at "
        "separation."
    )

    return f"{p1}\n\n{p2}\n\n{p3}"


def explain_scenario(
    profile_label, rank_at_sep, timing_label, sep_yos, sep_age,
    member_pct, mc, det, ctx,
):
    """
    Return (narrative_text, source_caption) for one scenario.

    Tries Gemini when a key is present; otherwise (or on any
    API failure) falls back to the built-in summary, so this
    always returns usable text.
    """
    args = (
        profile_label, rank_at_sep, timing_label, sep_yos,
        sep_age, member_pct, mc, det, ctx,
    )
    if _gemini_key():
        try:
            text = _explain_gemini(_facts(*args))
            return text, f"Narrated live by Gemini ({GEMINI_MODEL})."
        except Exception as err:  # noqa: BLE001 — always fall back
            note = (
                f"Live narration unavailable "
                f"({type(err).__name__}) — showing the "
                "built-in summary."
            )
            return _explain_builtin(*args), note
    return _explain_builtin(*args), (
        "Built-in summary (set GEMINI_API_KEY for live AI "
        "narration)."
    )
