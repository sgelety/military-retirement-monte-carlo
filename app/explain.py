"""Plain-language explanation of app results.

Two-tier chain, so the explain button always works:

1. **Gemini 2.5 Flash** (free API tier) when GEMINI_API_KEY or
   GOOGLE_API_KEY is set — live LLM narration of the numbers
   the app computed.
2. **Built-in summary** otherwise (no key, rate-limited, or any
   API error): a deterministic narrative generated locally from
   the same numbers. Zero dependencies, works offline forever.

Both tiers follow the project's framing rules: the neutral
"lifetime value difference (BRS - High-Three)", constant 2026 dollars,
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
  extrapolate figures. In particular, do NOT compute the
  member's difference by subtracting the two lifetime-value
  totals — use the provided median difference, and describe it
  as the typical gap when the two systems are compared for the
  SAME simulated career (these are medians, which don't add up
  by subtraction).
- Frame results as the neutral "lifetime value difference
  between BRS and High-Three". State every difference as a
  positive dollar amount in favor of whichever system leads
  (e.g. "about $30,000 in BRS's favor" or "in High-Three's
  favor") — never write a negative or minus-signed difference.
  A provided figure with a minus sign favors High-Three; one
  without favors BRS. Never call either system "better" — which
  one favors a member depends on career length.
- All dollar figures are net present value at separation in
  constant 2026 dollars. Round to the nearest thousand when
  narrating.
- The government's cost figures use an actuarial AVERAGE-member
  basis, so they come out a little different from the member's
  own simulated medians. When you cite them, note they price the
  average member rather than one person's luck — never present
  the gap as a contradiction.
- Describe the government TSP as a balance in the member's
  account at separation (still growing afterward), not as a
  separate lifetime total.
- Write 2-3 short paragraphs: (1) what this member's numbers say
  and the mechanics behind them (the 20-year pension cliff, the
  BRS government TSP match, the 2.5% vs 2.0% multiplier), using
  the lifetime values, first-year pensions, and government TSP
  balance; (2) the government's side of the same career and how
  this member fits the force-wide pattern; (3) one sentence on
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
    plabel = profile_label.lower()
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
systems (identical, so it cancels out of the comparison).
Pension status: {pension}.

Member side — what this career is worth to the member (median of
20,000 simulated futures, NPV at separation in constant 2026 $;
these match the app's on-screen tables):
- High-Three median lifetime value (its pension only): \
{_fmt(mc['h3_govt']['p50'])}
- BRS median lifetime value (smaller pension + government TSP): \
{_fmt(mc['brs_govt']['p50'])}
- First-year pension: High-Three {_fmt(det['H3PensionAnnual'])}, \
BRS {_fmt(det['BRSPensionAnnual'])}
- Government TSP balance in the member's account at separation \
(BRS only, still growing afterward): {_fmt(det['GovtTSP_AtSep'])}
- Median difference comparing the two systems for the SAME \
simulated career (BRS - High-Three): {_fmt(adv['p50'])}
- Middle 50% of that difference (P25 to P75): \
{_fmt(adv['p25'])} to {_fmt(adv['p75'])}

Government side — actuarial cost of this career (prices the \
AVERAGE member, not one person's luck; constant 2026 $; comes out
a little different from the member's simulated medians):
- Cost under High-Three: {_fmt(det['H3_GovtCost'])}
- Cost under BRS: {_fmt(det['BRS_GovtCost'])}
- DoD savings (High-Three - BRS): {_fmt(det['DoD_Savings'])}

Force-wide context ({plabel} entrants, DoD actuarial separation \
rates, typical careers):
- {ctx['share_pre20_members']:.0%} separate before 20 years; \
they receive only {ctx['share_pre20_spend']:.1%} of expected \
BRS spending
- {ctx['share_reaching_sep']:.0%} of {plabel} entrants serve \
{sep_yos}+ years
- Expected savings per {plabel} entrant from BRS: \
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


def _band_phrase(lo, hi):
    """P25-P75 difference band as plain, minus-free prose.

    lo (P25) <= hi (P75); a negative value favors High-Three.
    """
    if lo >= 0:  # both ends favor BRS
        return f"{_fmt_k(lo)} to {_fmt_k(hi)} in BRS's favor"
    if hi <= 0:  # both ends favor High-Three
        return (
            f"{_fmt_k(abs(hi))} to {_fmt_k(abs(lo))} in "
            "High-Three's favor"
        )
    return (  # straddles zero
        f"{_fmt_k(abs(lo))} in High-Three's favor to "
        f"{_fmt_k(hi)} in BRS's favor"
    )


def _explain_builtin(
    profile_label, rank_at_sep, timing_label, sep_yos, sep_age,
    member_pct, mc, det, ctx,
):
    """Deterministic narrative built locally from the numbers."""
    adv = mc["brs_adv"]
    med = adv["p50"]
    plabel = profile_label.lower()
    direction = "in BRS's favor" if med >= 0 else (
        "in High-Three's favor"
    )
    h3_life = mc["h3_govt"]["p50"]
    brs_life = mc["brs_govt"]["p50"]
    govt_tsp = det["GovtTSP_AtSep"]

    if sep_yos < 20:
        p1 = (
            f"Separating at {sep_yos} years as {rank_at_sep} "
            f"({timing_label}), this {plabel} career ends "
            "before the 20-year pension cliff, so neither "
            "system pays a pension. Under High-Three the "
            "member's government-funded value is $0. Under BRS "
            "the government's automatic 1% and matching TSP "
            f"contributions are worth about {_fmt_k(govt_tsp)} "
            "in the account at separation (and still growing), "
            f"for a lifetime value of about {_fmt_k(brs_life)}. "
            "When the two systems are compared for the same "
            "simulated career, the typical difference comes out "
            f"to about {_fmt_k(abs(med))} — {direction}."
        )
    else:
        p1 = (
            f"Separating at {sep_yos} years as {rank_at_sep} "
            f"({timing_label}), this {plabel} career clears the "
            "20-year pension cliff and earns a lifetime pension "
            "under both systems. High-Three's higher "
            "2.5%-per-year multiplier makes its pension the "
            "member's entire government-funded value — about "
            f"{_fmt_k(h3_life)} over a lifetime, starting near "
            f"{_fmt_k(det['H3PensionAnnual'])} in the first "
            "year. BRS uses a 2.0% multiplier, so its pension "
            f"is smaller (about {_fmt_k(det['BRSPensionAnnual'])}"
            " in the first year), but it adds the government's "
            "automatic and matching TSP — about "
            f"{_fmt_k(govt_tsp)} in the account at separation, "
            "and still growing — for a lifetime value of about "
            f"{_fmt_k(brs_life)}. When the two systems are "
            "compared for the same simulated career, the "
            f"typical difference comes out to about "
            f"{_fmt_k(abs(med))} — {direction}."
        )

    sav = det["DoD_Savings"]
    if sav >= 0:
        sav_txt = (
            f"so BRS saves the government about {_fmt_k(sav)} "
            "on this career"
        )
    else:
        sav_txt = (
            f"so BRS costs the government about {_fmt_k(-sav)} "
            "more on this career"
        )
    p2 = (
        "By the government's actuarial accounting — which "
        "prices the average member rather than one person's "
        f"luck — this career costs about {_fmt_k(det['H3_GovtCost'])} "
        f"under High-Three and about {_fmt_k(det['BRS_GovtCost'])} "
        f"under BRS, {sav_txt}. Across the force, "
        f"{ctx['share_pre20_members']:.0%} of {plabel} entrants "
        "separate before 20 years and receive only "
        f"{ctx['share_pre20_spend']:.1%} of expected BRS "
        f"spending; about {ctx['share_reaching_sep']:.0%} serve "
        f"{sep_yos} or more years like this one, and the "
        f"expected saving per {plabel} entrant from BRS is "
        f"{_fmt_k(ctx['expected_savings'])}."
    )

    p3 = (
        "These member figures are medians across 20,000 "
        "simulated futures; the middle 50% of the difference "
        f"runs from {_band_phrase(adv['p25'], adv['p75'])}, in "
        "constant 2026 dollars at separation."
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
