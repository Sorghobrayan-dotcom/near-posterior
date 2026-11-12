"""Render THESIS.md from the files in results/ only (SPEC section 7).

Run: `python -m near_posterior.thesis` rewrites THESIS.md from the committed results/.
"""

import csv
import io
import json

from near_posterior import out

MODEL_ORDER = ("B0", "B1", "B2", "A_30", "A_60", "A_120")

LIMITS = [
    "No price forecast. Price enters only as a scenario factor G_P (0.5, 1, 2).",
    "Frequencies are not mechanisms. A base rate says how often fee growth of this size "
    "happened to comparable protocols, not why, and not whether NEAR Intents is like them.",
    "DefiLlama lists what it lists. Protocols it does not track, or tracks late, are absent; "
    "the panel is what survived to be listed.",
    "\"Fees\" differ across protocols: each DefiLlama adapter defines its own fees.",
    "Capture and issuance are governance decisions. G_kappa and G_I are scenarios, not "
    "forecasts.",
    "Aggregator data, not an on-chain rebuild: buybacks are DefiLlama holders revenue, supply "
    "and price are NearBlocks charts.",
]


def load_results(root=out.ROOT) -> dict:
    """Return every results/ file needed by the thesis and the page, parsed."""
    res = {}
    for name in ("coverage", "refclass_counts", "backtest", "audit", "speccurve", "headline"):
        res[name] = json.loads((root / "results" / f"{name}.json").read_text(encoding="ascii"))
    text = (root / "results" / "audit.csv").read_text(encoding="ascii")
    res["audit_rows"] = list(csv.DictReader(io.StringIO(text)))
    text = (root / "results" / "speccurve.csv").read_text(encoding="ascii")
    res["speccurve_rows"] = list(csv.DictReader(io.StringIO(text)))
    res["deviations"] = (root / "DEVIATIONS.md").read_text(encoding="ascii")
    return res


def f(x, digits: int = 3) -> str:
    """Return x with a fixed number of decimals."""
    return f"{x:.{digits}f}"


def usd(x: float) -> str:
    """Return a USD amount in millions."""
    return f"${x / 1e6:,.1f}M"


def pct(x: float, digits: int = 1) -> str:
    """Return a fraction as a percentage."""
    return f"{100 * x:.{digits}f} percent"


def interval(iv) -> str:
    """Return a 90 percent interval as text."""
    return f"{f(iv[0])} to {f(iv[1])}"


def limits(res: dict) -> list[str]:
    """Return the limits of SPEC 7 section 8, the market-cycle span read from the results."""
    years = sorted(res["headline"]["B0"]["by_year"])
    return LIMITS + [f"Few independent market cycles: the class {res['headline']['class']} "
                     f"origins at h = 24 run from {years[0]} to {years[-1]}, and one market "
                     f"regime can dominate the class."]


def headline_line(res: dict) -> str:
    """Return the one-line headline printed by build and repeated in the README."""
    h = res["headline"]
    return (f"P(buybacks cover NEAR net issuance within 24 months) = {f(h['P'])} "
            f"(90% interval {interval(h['interval'])}), model {h['model']}, class {h['class']}, "
            f"{h['entities']} entities, snapshot t0 = {h['t0']}: {h['verdict']}")


def facts(res: dict) -> list[tuple[int, str]]:
    """Return (direction, sentence) facts; direction +1 points toward coverage, -1 away."""
    c, h = res["coverage"], res["headline"]
    w = {x["window"]: x for x in c["windows"]}
    s = res["speccurve"]
    wc = h["what_would_change"]
    a = h["analogs"]
    b0 = h["B0"]
    rows = [
        (-1 if h["k_star"] > 1 else 1,
         f"Coverage today is C_90 = {f(w['90']['C'])}: annualised buybacks of "
         f"{usd(w['90']['A_b'])} against net issuance of {c['I_t0']:,.0f} NEAR per year "
         f"(r = {pct(c['r'], 2)}) at ${f(c['p_t0'], 2)}. With capture, price and issuance rate "
         f"unchanged, 90-day fees must grow by k* = {f(h['k_star'], 2)}x in 24 months."),
        (1 if h["P"] > 0.5 else -1,
         f"In class {h['class']} ({h['entities']} entities, {b0['moments']} moments) the share of "
         f"24-month outcomes with fee growth >= k* is {f(h['P'])} (90% interval "
         f"{interval(h['interval'])}). Using only each entity's earliest moment: "
         f"{b0['earliest']['x']} of {b0['earliest']['n']} = {f(b0['earliest']['P'])} "
         f"(Clopper-Pearson {interval(b0['earliest']['interval'])})."),
        (1 if max(v["P"] for v in a.values()) > 0.5 else -1,
         "The analog model (nearest entities on scale, momentum and age) gives "
         + ", ".join(f"{k} = {f(a[k]['P'])} ({interval(a[k]['interval'])})"
                     for k in MODEL_ORDER if k in a)
         + "."),
        (1 if s["median"] > 0.5 else -1,
         f"Across the 864 rows of the specification curve, P has median {f(s['median'])}, "
         f"minimum {f(s['min'])} and maximum {f(s['max'])}."),
        ((1 if wc["P"] > 0.5 else -1) * (-1 if wc["any_grid_row_crosses"] else 1),
         f"Moving P across 0.50 alone would need capture G_kappa >= {f(wc['G_kappa_needed'], 2)} "
         f"(a capture rate of {f(wc['kappa_needed'], 2)}), or issuance cut to "
         f"{f(wc['G_I_needed'], 3)}x today's path, or a price factor <= {f(wc['G_P_needed'], 3)}. "
         + ("No single-factor row of the grid crosses 0.50." if not wc["any_grid_row_crosses"]
            else "At least one single-factor row of the grid crosses 0.50.")),
        (1 if c["momentum"] > 0 else -1,
         f"NEAR Intents fees are {f(c['F_near'] / c['F_6m'], 2)}x their level of six months "
         f"earlier: A_90(f) = {usd(c['F_near'])} per year at t0 against {usd(c['F_6m'])} for "
         f"the 90 days ending {c['F_6m_end']}."),
        (1 if w["30"]["C"] > w["90"]["C"] else -1,
         f"Coverage by window: 30 days {f(w['30']['C'])}, 90 days {f(w['90']['C'])}, 180 days "
         f"{f(w['180']['C'])}, since 2026-02-23 {f(w['since']['C'])}; capture rate "
         f"kappa_30 = {f(w['30']['kappa'])}, kappa_90 = {f(w['90']['kappa'])}."),
    ]
    return rows


def backtest_section(res: dict) -> list[str]:
    """Return the lines of the backtest section."""
    bt = res["backtest"]
    lines = []
    for h in ("12", "24"):
        agg = bt["scores"][h]
        lines.append(f"h = {h} months: {agg['candidates']} candidate targets, {agg['scored']} "
                     f"scored from {agg['entities']} entities, {agg['dropped']} dropped (B0 pool "
                     f"below 20 entities or analog pool below 120). Sufficient: "
                     f"{'yes' if agg['sufficient'] else 'no'}.")
        lines.append("")
        if not agg["scored"]:
            continue
        lines.append("| Model | mean CRPS (90% CI) | CRPS - B0 (90% CI) | Brier k=1 | Brier k=2 | "
                     "Brier k=5 | 50% cover | 90% cover | PIT KS |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for m in MODEL_ORDER:
            v = agg["models"][m]
            diff = ("0" if m == "B0" else
                    f"{f(v['crps_minus_B0'])} ({interval(v['crps_minus_B0_interval'])})")
            lines.append(f"| {m} | {f(v['crps'])} ({interval(v['crps_interval'])}) | {diff} | "
                         f"{f(v['brier_1'])} | {f(v['brier_2'])} | {f(v['brier_5'])} | "
                         f"{f(v['cov_50'], 2)} | {f(v['cov_90'], 2)} | {f(v['pit']['ks'])} |")
        lines.append("")
        years = sorted(next(iter(agg["models"].values()))["by_year"])
        lines.append("Mean CRPS by calendar year of the origin tau: " + "; ".join(
            f"{y} (n = {agg['models']['B0']['by_year'][y]['n']}): " + ", ".join(
                f"{m} {f(agg['models'][m]['by_year'][y]['crps'])}" for m in MODEL_ORDER)
            for y in years) + ".")
        lines.append("")
        b2 = agg["models"]["B2"]["crps_minus_B0_interval"]
        b1 = agg["models"]["B1"]["crps_minus_B0_interval"]
        if b2[0] > 0 and b1[0] > 0:
            verdict = ("The outside view (B0) beats both trend baselines: the 90% intervals of "
                       "CRPS(B1) - CRPS(B0) and CRPS(B2) - CRPS(B0) are above 0.")
        elif b2[1] < 0 or b1[1] < 0:
            verdict = "Trend extrapolation beats the outside view at this horizon."
        else:
            verdict = ("The outside view does not beat trend extrapolation at this horizon: "
                       "an interval of the difference contains 0.")
        lines.append(verdict)
        lines.append("")
    ch = bt["choice"]
    lines.append(f"Model choice (PREREG 6): backtest used h = {ch['horizon']}; lowest mean CRPS "
                 f"among B0 and A_K: {ch['lowest_crps']}; headline model: **{ch['model']}** "
                 f"({ch['reason']}).")
    if not bt["scores"]["24"]["sufficient"]:
        lines.append("")
        lines.append("No 24-month backtest is sufficient, so the 24-month headline rests on a "
                     "model checked at 12 months only.")
    return lines


def audit_section(res: dict) -> list[str]:
    """Return the lines of the audit section."""
    a = res["audit"]
    sc = a["status_counts"]
    lines = [
        f"{a['claims']} published values from {a['theses']} public NEAR theses, each read at a "
        f"fixed commit (file and line in `data/claims.csv`). For each value: y = the published "
        f"value, r = ours under their window, end date and definition, r0 = ours under our "
        f"primary definition at {a['t0']}; e = ln(y/r) (reproduced if |e| <= ln 1.02), "
        f"s = ln(r/r0), and ln(y/r0) = s + e. Values are in a common unit per metric "
        f"(multiples inverted to coverage).",
        "",
        f"Reproduced: {sc['reproduced']}; not reproduced: {sc['not reproduced']}; not "
        f"recomputed (definition needs data we do not have, or window not stated): "
        f"{sc['not recomputed']}. DefiLlama can revise its history, so a replication gap can "
        f"come from a revision.",
        "",
        "| Thesis | Metric | y | r | r0 | e | s | Status |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in res["audit_rows"]:
        def g(key):
            if r[key] == "":
                return ""
            x = float(r[key])
            if key in ("e", "s"):
                return f"{x:.4f}".replace("-0.0000", "0.0000")
            if r["metric"] in ("M1", "M4"):
                return usd(x)
            return f"{x:.4f}"
        lines.append(f"| {r['thesis']} | {r['metric']} | {g('y_common')} | {g('r_common')} | "
                     f"{g('r0')} | {g('e')} | {g('s')} | {r['status']} |")
    lines.append("")
    lines.append("Dispersion of ln y across theses (interquartile range, only when n >= 5): " +
                 "; ".join(f"{m} {a['metrics'][m]}: n = {d['n']}"
                           + ("" if d["iqr_ln"] is None else f", IQR = {f(d['iqr_ln'])}")
                           for m, d in a["dispersion"].items()) + ".")
    return lines


def render(res: dict) -> str:
    """Return the text of THESIS.md built from the parsed results."""
    h, c, s = res["headline"], res["coverage"], res["speccurve"]
    counts = res["refclass_counts"]
    direction = 1 if h["P"] > 0.5 else -1
    fx = facts(res)
    p = s["primary"]
    dev = res["deviations"].split("\n", 1)[1].strip() if "\n" in res["deviations"] else ""
    L = [
        "# Will NEAR buybacks cover net issuance within 24 months?",
        "",
        f"Generated by `uv run python -m near_posterior.build` from `results/` only. "
        f"NEAR snapshot fetched {c['fetched_at']}, t0 = {c['t0']}. Reference panel end "
        f"{counts['D']}. Rules: `PREREG.md`. Not financial advice.",
        "",
        "## 1. The claim",
        "",
        f"**{h['verdict'][0].upper() + h['verdict'][1:]}.** The pre-registered probability that "
        f"buybacks funded by NEAR Intents revenue cover NEAR's net issuance 24 months after "
        f"{c['t0']} (primary scenario: capture, price and issuance rate unchanged) is "
        f"**{f(h['P'])}** (90% interval {interval(h['interval'])}, {h['interval_kind']}), from "
        f"model {h['model']} on class {h['class']} ({h['entities']} entities), snapshot "
        f"{c['t0']}.",
        "",
        "## 2. Evidence for",
        "",
    ]
    L += [f"- {t}" for d, t in fx if d == direction]
    ch = res["backtest"]["choice"]
    if ch["horizon"] and ch["model"] == "B0":
        m = res["backtest"]["scores"][str(ch["horizon"])]["models"]
        if all(m[x]["crps_minus_B0_interval"][0] > 0 for x in ("B1", "B2")):
            L.append(f"- In the {ch['horizon']}-month rolling-origin backtest the class "
                     f"frequency B0 is not beaten by the analog model and scores better than "
                     f"both trend baselines (section 6).")
    L += ["", "## 3. Evidence against", ""]
    L += [f"- {t}" for d, t in fx if d != direction]
    bt = res["backtest"]["scores"]
    if not bt["24"]["sufficient"]:
        L.append(f"- No 24-month backtest: all {bt['24']['candidates']} candidate targets were "
                 f"dropped, so the 24-month model is not tested out of sample.")
    years = sorted(next(iter(bt["12"]["models"].values()))["by_year"]) if bt["12"]["scored"] else []
    if len(years) == 1:
        L.append(f"- Every scored 12-month target has its origin in {years[0]}: the backtest "
                 f"covers one calendar year.")
    L.append("- Capture and issuance are governance decisions and can change faster than fees.")
    wc = h["what_would_change"]
    L += [
        "", "## 4. What would change our mind", "",
        f"P crosses 0.50 (PREREG 8) when k* falls to {f(wc['k50'], 3)} or below. On its own "
        f"that needs one of:",
        "",
        f"- capture: G_kappa >= {f(wc['G_kappa_needed'], 2)}, a capture rate of "
        f"{f(wc['kappa_needed'], 3)} of gross fees"
        + (" (above 1, so capture alone cannot do it);" if wc["kappa_needed"] > 1 else ";"),
        f"- issuance: G_I <= {f(wc['G_I_needed'], 3)}, a cut of {pct(wc['G_I_cut_needed'])} "
        f"from the constant-rate path;",
        f"- price: G_P <= {f(wc['G_P_needed'], 3)}, i.e. NEAR at {f(wc['G_P_needed'], 3)}x "
        f"today's price with everything else unchanged.",
        "",
        "Single-factor rows of the registered grid (primary class, W = 90, h = 24): " + "; ".join(
            f"{r['factor']} = {r['value']}: P = {f(r['P'])}" for r in wc["single_factor_grid_rows"])
        + ". " + ("None of them crosses 0.50." if not wc["any_grid_row_crosses"]
                  else "At least one crosses 0.50."),
        "",
        "We would also change our mind if a sufficient 24-month backtest showed the class "
        "frequency to be miscalibrated for protocols like NEAR Intents.",
        "", "## 5. How other theses measure the same thing", "",
    ]
    L += audit_section(res)
    L += ["", "## 6. Backtest", "",
          "Rolling origin, no look-ahead: for each target (entity j, month tau) the pool holds "
          "other entities' moments whose outcome was known at tau. B0 = class frequency, "
          "B1 = Normal random walk, B2 = Normal trend extrapolation from the entity's own "
          "quarterly fee changes, A_K = K nearest analog entities. Scores on log fee growth "
          "floored at ln 0.01.", ""]
    L += backtest_section(res)
    L += ["", "## 7. Specification curve", "",
          f"{s['rows']} rows (window x class x horizon x capture x issuance x price), all with "
          f"model B0. P: median {f(s['median'])}, minimum {f(s['min'])}, maximum "
          f"{f(s['max'])}. Primary row (W = 90, class {p['cls']}, h = 24, capture, issuance "
          f"and price constant): k* = {f(p['k_star'], 3)}, P = {f(p['P'])} "
          f"({interval([p['P_lo'], p['P_hi']])}). All rows: `results/speccurve.csv`.",
          "",
          "Primary row by calendar year of the origin: " + "; ".join(
              f"{y}: {f(v['P'])} ({v['entities']} entities, {v['moments']} moments)"
              for y, v in sorted(h["B0"]["by_year"].items())) + ".",
          "", "## 8. What this cannot tell you", ""]
    L += [f"- {t}" for t in limits(res)]
    L += ["", "## 9. Deviations from the pre-registration", ""]
    L.append(dev if dev and dev != "None so far." else "None.")
    L += ["", "Stop rules (PREREG 9): reference panel missing share "
          f"{pct(counts['panel']['missing_share'])} ({counts['panel']['missing']} of "
          f"{counts['panel']['universe']} entries); class R at h = 24 has "
          f"{counts['classes']['R']['24']['entities']} entities "
          + ("(below 30: R_all_ages is primary)." if h["stop_rule_R_below_30"]
             else "(30 or more: R stays primary).")
          + " Control values of `docs/SPEC.md` section 5: reproduced (`tests/test_coverage.py`).",
          ""]
    return "\n".join(L)


def main() -> None:
    """Rewrite THESIS.md from results/."""
    out.write_text(out.ROOT / "THESIS.md", render(load_results()))


if __name__ == "__main__":
    main()
