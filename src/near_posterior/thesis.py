"""Render THESIS.md from the files in results/ only, as a plain argument (TASKS_V2 U8).

Run: `python -m near_posterior.thesis` rewrites THESIS.md from the committed results/.
"""

import csv
import io
import json

from near_posterior import out

MODEL_ORDER = ("B0", "B1", "B2", "A_30", "A_60", "A_120")
SECONDARY = "secondary (specified after the primary results)"
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
    "Age is the age in DefiLlama's data (days since the first day with fees > 0 in the panel), "
    "not the age since launch.",
    "Dead fill uses the panel end D: an entity silent for more than 30 days before D is filled "
    "with zeros, so a backtest pool outcome can use knowledge of D rather than of its tau.",
    "Class R selects protocols at a high point of their fees (scale band around NEAR Intents' "
    "current fees), so part of the typical decline in the class is regression to the mean.",
]


def parse(texts: dict) -> dict:
    """Return parsed results: `name.json` as res[name], `name.csv` rows as res[name_rows]."""
    res = {}
    for name in sorted(texts):
        stem, ext = name.rsplit(".", 1)
        if ext == "json":
            res[stem] = json.loads(texts[name])
        elif ext == "csv":
            res[f"{stem}_rows"] = list(csv.DictReader(io.StringIO(texts[name])))
    return res


def load_results(root=out.ROOT) -> dict:
    """Return every file of results/ parsed, plus the text of DEVIATIONS.md."""
    texts = {p.name: p.read_text(encoding="ascii") for p in (root / "results").iterdir()
             if p.suffix in (".json", ".csv")}
    res = parse(texts)
    res["deviations"] = (root / "DEVIATIONS.md").read_text(encoding="ascii")
    return res


def f(x, digits: int = 3) -> str:
    """Return x with a fixed number of decimals."""
    return f"{float(x):.{digits}f}"


def usd(x: float) -> str:
    """Return a USD amount in millions."""
    return f"${float(x) / 1e6:,.1f}M"


def pct(x: float, digits: int = 1) -> str:
    """Return a fraction as a percentage."""
    return f"{100 * float(x):.{digits}f} percent"


def interval(iv) -> str:
    """Return a 90 percent interval as text."""
    return f"{f(iv[0])} to {f(iv[1])}"


def headline_line(res: dict) -> str:
    """Return the one-line headline printed by build and repeated in the README."""
    h = res["headline"]
    return (f"P(buybacks cover NEAR net issuance at the 24-month mark) = {f(h['P'])} "
            f"(90% interval {interval(h['interval'])}), model {h['model']}, class {h['class']}, "
            f"{h['entities']} entities, snapshot t0 = {h['t0']}: {h['verdict']}")


def primary_row(res: dict, cls: str, h: int = 24) -> dict:
    """Return the primary row of the specification curve for a class and horizon."""
    return next(r for r in res["speccurve_rows"] if r["cls"] == cls and r["window"] == "90"
                and int(r["h"]) == h and r["capture"] == "constant"
                and r["issuance"] == "constant" and float(r["G_P"]) == 1.0)


def limits(res: dict) -> list[str]:
    """Return the limits, the market-cycle span and the trading-only class read from results."""
    h = res["headline"]
    years = sorted(h["B0"]["by_year"])
    rt = primary_row(res, "R_trading")
    return LIMITS + [
        f"Few independent market cycles: the class {h['class']} origins at h = 24 run from "
        f"{years[0]} to {years[-1]}, and one market regime can dominate the class.",
        f"Class {h['class']} mixes fee types (trading fees, interest, staking yield). Restricted "
        f"to trading-type categories (R_trading, {rt['entities']} entities) the primary "
        f"probability is {f(rt['P'])} ({f(rt['P_lo'])} to {f(rt['P_hi'])}), "
        f"against {f(h['P'])} for {h['class']}."]


def lever(res: dict, label: str, capture: str, factor: float, g_p: float) -> dict:
    """Return one row of the lever table."""
    return next(r for r in res["levers_rows"] if r["label"] == label and r["capture"] == capture
                and abs(float(r["issuance_factor"]) - factor) < 1e-9 and float(r["G_P"]) == g_p)


def calibration_table(rel: dict) -> list[str]:
    """Return a markdown table of the non-empty reliability bins of C0 and B2, both events."""
    L = ["| Model | Event | Forecast bin | Targets | Mean forecast | Observed |",
         "|---|---|---|---|---|---|"]
    for name in ("C0", "B2"):
        for key, event in (("Y_ge_ln2", "fees at least doubled"), ("Y_ge_ln5", "fees at least 5x")):
            for b in rel[name][key]:
                if b["targets"]:
                    L.append(f"| {name} | {event} | {f(b['bin'][0], 2)} to {f(b['bin'][1], 2)} | "
                             f"{b['targets']} | {f(b['mean_forecast'], 3)} | "
                             f"{f(b['observed'], 3)} |")
    return L


def largest_bin(val: dict, h: str) -> dict:
    """Return the most populated reliability bin of C0 for the doubling event at horizon h."""
    return max(val["S1"][h]["reliability"]["C0"]["Y_ge_ln2"], key=lambda b: b["targets"])


def summary(res: dict) -> list[str]:
    """Return the summary sentences."""
    h, c = res["headline"], res["coverage"]
    w90 = next(w for w in c["windows"] if w["window"] == "90")
    reg = res["registered_forecast"]["forecasts"]["24"]
    grid = [r for r in res["levers_rows"] if r["label"] == "lever grid"]
    best = max(grid, key=lambda r: float(r["P"]))
    gov = [r for r in res["levers_rows"] if r["label"] != "lever grid"
           and r["capture"] == "kappa_90" and float(r["G_P"]) == 1.0]
    val = res["validation"]["S1"]
    s12, s24 = val["12"], val["24"]
    beats = all(v["C0_beats_B2"] for v in (s12, s24))
    b = largest_bin(res["validation"], "24")
    over = b["mean_forecast"] > b["observed"]
    years24 = sorted(s24["origins_by_year"])
    if float(best["P"]) > 0.5:
        gov_text = (f"A combination of levers in the lever table reaches even odds "
                    f"(P = {f(best['P'])} at capture {best['capture']}, issuance x "
                    f"{f(best['issuance_factor'], 2)}, price x {f(best['G_P'], 1)})")
    else:
        gov_text = (f"No combination in the lever table reaches even odds: the highest is "
                    f"P = {f(best['P'])}, with capture {best['capture']}, issuance x "
                    f"{f(best['issuance_factor'], 2)} and price x {f(best['G_P'], 1)}")
    gp = sorted({f(r["P"]) for r in gov})
    gov_text += ("; the HSP-029 issuance ramp, read at its primary source, gives P = "
                 + " or ".join(gp) + (" depending on its start date." if len(gp) > 1 else
                                      " for both assumed start dates.") if gov else ".")
    return [
        f"The question is whether NEAR's buybacks, funded by NEAR Intents revenue, will cover "
        f"NEAR's net issuance at the 24-month mark ({reg['resolution_date']}).",
        f"Today they cover {pct(w90['C'])} of it (90-day window, {c['t0']}), so with capture, "
        f"price and issuance rate unchanged NEAR Intents fees would have to grow "
        f"{f(h['k_star'], 2)}x in 24 months.",
        f"Among {h['entities']} DefiLlama protocols of similar size and age, fee growth of that "
        f"size at the 24-month mark happened with a frequency of {f(h['P'])} (90 percent "
        f"interval {interval(h['interval'])}): {h['verdict']}.",
        gov_text,
        f"Checked on {s12['scored']} past 12-month and {s24['scored']} past 24-month forecasts "
        f"[{SECONDARY}], the class method "
        + ("beat trend extrapolation at both horizons" if beats else
           "did not beat trend extrapolation at both horizons")
        + (f", but it forecast more growth than happened (the doubling event was forecast at "
           f"{f(b['mean_forecast'], 2)} and observed at {f(b['observed'], 2)} in its largest "
           f"24-month bin)" if over else "")
        + ", and its weakest point is that the 24-month check rests on origins in "
        + " and ".join(years24) + " only.",
    ] + correction_sentence(res) + investor(res)


def investor(res: dict) -> list[str]:
    """Return one or two sentences on what the result means for an investor (no advice, no
    price view), chosen from the verdict and the lever table."""
    P = res["headline"]["P"]
    cap1 = lever(res, "lever grid", "1.0", 1.0, 1.0)
    iss = lever(res, "lever grid", "kappa_90", 0.25, 1.0)
    both = lever(res, "lever grid", "1.0", 0.25, 1.0)
    if P < 0.10:
        first = ("For an investor, this means that on base rates the buyback does not offset "
                 "dilution by the 24-month mark: net supply growth stays the base case.")
    elif P <= 0.50:
        first = ("For an investor, this means that on base rates offsetting dilution by the "
                 "24-month mark is possible but not the base case.")
    else:
        first = ("For an investor, this means that on base rates the buyback offsets dilution "
                 "by the 24-month mark in most comparable cases.")
    return [first,
            f"The levers that move these odds most are governance ones: spending all fees on "
            f"buybacks gives P = {f(cap1['P'])}, cutting issuance to a quarter of its path "
            f"{f(iss['P'])}, and both together {f(both['P'])}, at today's price."]


def section_question(res: dict) -> list[str]:
    """Return section 2."""
    c = res["coverage"]
    w = {x["window"]: x for x in c["windows"]}
    ks = [x["k_star_h24"] for x in c["windows"]]
    return [
        "## 2. The question", "",
        f"Since {c['buyback_start']}, NEAR Intents revenue buys NEAR on the market. Net issuance "
        f"over the year to {c['t0']} was {c['I_t0']:,.0f} NEAR (supply growth "
        f"r = {pct(c['r'], 2)}), worth {usd(c['I_t0'] * c['p_t0'])} a year at "
        f"${f(c['p_t0'], 2)}. Annualised buybacks over the last 90 days were "
        f"{usd(w['90']['A_b'])}, so coverage C_90 = {f(w['90']['C'])}.", "",
        "Coverage depends on the window used to annualise buybacks: "
        + ", ".join(f"{x['W']} days {f(x['C'])}" for x in c["windows"])
        + f" (the last is the period since {c['buyback_start']}). The fee growth needed for "
        f"coverage at the 24-month mark, k*, moves from {f(min(ks), 2)}x to {f(max(ks), 2)}x "
        f"with the window alone. The registered window is 90 days: k* = "
        f"{f(w['90']['k_star_h24'], 3)}.", "",
    ]


def section_outside_view(res: dict) -> list[str]:
    """Return section 3."""
    h, c = res["headline"], res["coverage"]
    g = res["growth_quantiles"]["by_h"]["24"]
    q = g["quantiles_exp_Y"]
    pa = g["P_at"]
    counts = res["refclass_counts"]
    hit = sorted((r for r in res["entities_R_rows"] if r["h"] == "24"
                  and int(r["successes_at_k_star"]) > 0),
                 key=lambda r: -float(r["largest_growth"]))
    cats = sorted({r["category"] for r in hit})
    trading = [r for r in hit if r["category"] in ("Dexs", "Derivatives")]
    L = [
        "## 3. The outside view", "",
        f"The reference panel is every DefiLlama protocol above the fee floor of `PREREG.md` "
        f"2.2, merged by parent protocol ({counts['entities']} entities, frozen on "
        f"{counts['panel']['fetched_at'][:10]}). A moment is a protocol on the first day of a "
        f"month; its outcome is the change of annualised 90-day fees 24 months later. Class R "
        f"keeps the moments of protocols within a factor 3 of NEAR Intents' current fees "
        f"({usd(c['F_near'])} a year) and 270 to 1095 days old (NEAR Intents is {c['age_t0']} "
        f"days old in DefiLlama's data): protocols of the same size at the same stage, which is "
        f"the comparison an outside view asks for.", "",
        f"What happened to them, weighting each protocol equally ({g['entities']} protocols, "
        f"{g['moments']} moments): fees were at least maintained after 24 months in "
        f"{f(pa['1']['P'])} of cases, at least doubled in {f(pa['2']['P'])}, grew at least 5x in "
        f"{f(pa['5']['P'])} and at least 10x in {f(pa['10']['P'])}. The median protocol ended "
        f"with {f(q['0.5'], 2)}x its starting fees; the middle half ended between "
        f"{f(q['0.25'], 3)}x and {f(q['0.75'], 2)}x; {pct(g['share_floor_entity_weighted'])} "
        f"ended at zero or below. At k* = {f(h['k_star'], 2)}x the frequency is {f(h['P'])} "
        f"(90 percent interval {interval(h['interval'])}). The full curve is in "
        f"`results/exceedance.csv` [{SECONDARY}].", "",
        f"{len(hit)} protocols of class R reached k* at least once:", "",
        "| Protocol | Category | Moments reaching k* | Largest 24-month growth | From |",
        "|---|---|---|---|---|",
    ]
    L += [f"| {r['name']} | {r['category']} | {r['successes_at_k_star']} of {r['moments']} | "
          f"{f(r['largest_growth'], 1)}x | {r['largest_growth_origin'][:7]} |" for r in hit]
    L += ["", f"They earn {len(cats)} kinds of fees ({', '.join(cats)}); {len(trading)} of the "
          f"{len(hit)} are trading venues (DEXs and derivatives), the kind of fee NEAR Intents "
          f"earns.", ""]
    return L


def section_momentum(res: dict) -> list[str]:
    """Return section 4."""
    h, c = res["headline"], res["coverage"]
    a = h["analogs"]
    ch = res["backtest"]["choice"]
    return [
        "## 4. Does NEAR Intents' own momentum change this?", "",
        f"NEAR Intents' fees are {f(c['F_near'] / c['F_6m'], 2)}x their level six months "
        f"earlier (momentum m = {f(c['momentum'], 3)}). The analog model picks, among protocols "
        f"with at least 1M USD of 90-day fees and 270 days of age, the nearest ones on size, "
        f"momentum and age: "
        + ", ".join(f"the {k[2:]} nearest give {f(a[k]['P'])} ({interval(a[k]['interval'])})"
                    for k in ("A_30", "A_60", "A_120")) + ". "
        + ("Momentum does not raise the base rate: no analog model gives a probability above "
           "the class. " if max(a[k]["P"] for k in a) <= h["P"] else
           "At least one analog model gives a probability above the class. ")
        + f"In the registered backtest the analogs did not beat the class frequency "
        f"({ch['reason']}), so the headline stays on the class.", "",
    ]


def section_within(res: dict) -> list[str]:
    """Return section 5."""
    w = res["within"]["by_h"]
    return [
        "## 5. At month 24, and at any point within 24 months", "",
        f"The registered event is coverage at the 24-month mark. Coverage could also be reached "
        f"for a while and lost again. Counting a protocol as a success if its fees cleared the "
        f"(slowly rising) bar at any month up to 24 [{SECONDARY}]: P = "
        f"{f(w['24']['P_within'])} ({interval(w['24']['interval_within'])}), against "
        f"{f(w['24']['P_at_month_h'])} at the mark. At 12 months: {f(w['12']['P_within'])} "
        f"against {f(w['12']['P_at_month_h'])}; at 36 months: {f(w['36']['P_within'])} against "
        f"{f(w['36']['P_at_month_h'])}. "
        + ("Even the looser event stays below even odds." if w["24"]["P_within"] < 0.5 else
           "The looser event passes even odds."), "",
    ]


def section_levers(res: dict) -> list[str]:
    """Return section 6."""
    rows = res["levers_rows"]
    grid = [r for r in rows if r["label"] == "lever grid"]
    base = lever(res, "lever grid", "kappa_90", 1.0, 1.0)
    cap1 = lever(res, "lever grid", "1.0", 1.0, 1.0)
    iss = lever(res, "lever grid", "kappa_90", 0.25, 1.0)
    price = lever(res, "lever grid", "kappa_90", 1.0, 0.5)
    best = max(grid, key=lambda r: float(r["P"]))
    even = [r for r in grid if float(r["P"]) > 0.5]
    gov = [r for r in rows if r["label"] != "lever grid" and r["capture"] == "kappa_90"
           and float(r["G_P"]) == 1.0]
    L = [
        "## 6. What NEAR controls", "",
        f"The lever table [{SECONDARY}] recomputes the probability at the 24-month mark for "
        f"capture rates, issuance paths and prices (`results/levers.csv`).", "",
        f"- Growth alone: with today's capture ({f(base['kappa_target'], 3)}), issuance and "
        f"price, fees must grow {f(base['k_star'], 2)}x; P = {f(base['P'])}.",
        f"- Capture alone: spending all fees on buybacks lowers the requirement to "
        f"{f(cap1['k_star'], 2)}x; P = {f(cap1['P'])} ({f(cap1['P_lo'])} to {f(cap1['P_hi'])}).",
        f"- Issuance alone: cutting issuance to a quarter of its path lowers it to "
        f"{f(iss['k_star'], 2)}x; P = {f(iss['P'])} ({f(iss['P_lo'])} to {f(iss['P_hi'])}).",
        f"- Price: a halved NEAR price makes buybacks buy twice as much; P = {f(price['P'])}.",
    ]
    if gov:
        L.append("- HSP-029 (governance forum text: issuance cap from 2.5 to 1.6 percent over 24 "
                 "months after activation; the ratification date is not in the source): "
                 + "; ".join(f"{r['label']}: issuance factor {f(r['issuance_factor'], 3)}, "
                             f"P = {f(r['P'])}" for r in gov) + ".")
    else:
        L.append("- No primary source for the governance proposal was reachable; no scenario "
                 "was added.")
    L += ["", (f"Even odds need a combination: {len(even)} of the {len(grid)} cells pass 0.50."
               if even else
               f"No cell of the table reaches even odds. The highest is P = {f(best['P'])} "
               f"({f(best['P_lo'])} to {f(best['P_hi'])}) with capture {best['capture']}, "
               f"issuance x {f(best['issuance_factor'], 2)} and price x {f(best['G_P'], 1)}."),
          ""]
    return L


def scores_table(agg: dict, names: tuple, base: str) -> list[str]:
    """Return a markdown table of mean CRPS and differences to the base model."""
    L = [f"| Model | mean CRPS (90% CI) | CRPS - {base} (90% CI) | Brier, doubling | "
         "50% cover | 90% cover |", "|---|---|---|---|---|---|"]
    for m in names:
        v = agg["models"][m]
        d = ("0" if m == base else
             f"{f(v[f'crps_minus_{base}'])} ({interval(v[f'crps_minus_{base}_interval'])})")
        L.append(f"| {m} | {f(v['crps'])} ({interval(v['crps_interval'])}) | {d} | "
                 f"{f(v['brier_2'])} | {f(v['cov_50'], 2)} | {f(v['cov_90'], 2)} |")
    return L


def section_method(res: dict) -> list[str]:
    """Return section 7: thin evidence first, then the scores and the calibration."""
    bt = res["backtest"]["scores"]
    val = res["validation"]
    s1, s2 = val["S1"], val["S2"]
    L = ["## 7. How we know the method works", "",
         "Where the evidence is thin, first. "
         f"The registered backtest scored no 24-month target ({bt['24']['candidates']} "
         f"candidates, all dropped by the 120-entity analog rule) and {bt['12']['scored']} "
         f"12-month targets from {bt['12']['entities']} protocols, all with origins in "
         + ", ".join(sorted(bt["12"]["models"]["B0"]["by_year"])) + ". "
         f"The secondary check below [{SECONDARY}] centres a class on every eligible protocol of "
         f"the panel; its 24-month part covers origins in "
         + ", ".join(sorted(s1["24"]["origins_by_year"])) + " only. The class R backtest "
         f"without the analog rule (S2) scores {s2['scored']} targets from {s2['entities']} "
         f"protocols and is {'sufficient' if s2['sufficient'] else 'not sufficient'}.", "",
         f"Registered 12-month backtest ({bt['12']['scored']} targets): "
         + "; ".join(f"{m} {f(bt['12']['models'][m]['crps'])}" for m in MODEL_ORDER)
         + f" (mean CRPS, lower is better). Headline model: "
         f"{res['backtest']['choice']['model']}.", ""]
    for h in ("12", "24"):
        a = s1[h]
        L += [f"Target-centred classes, h = {h} months: {a['scored']} targets from "
              f"{a['entities']} protocols (origins "
              + ", ".join(f"{y}: {n}" for y, n in a["origins_by_year"].items()) + ").", ""]
        L += scores_table(a, ("C0", "B1", "B2"), "C0")
        L += ["", ("The class forecast C0 beats trend extrapolation B2: the interval of "
                   "CRPS(B2) - CRPS(C0) is above 0." if a["C0_beats_B2"] else
                   "The class forecast C0 does not beat trend extrapolation B2 at this "
                   "horizon."), ""]
        rel = a["reliability"]
        L += [f"Calibration at h = {h} months (reliability by forecast bin; a calibrated forecast "
              f"has observed close to mean forecast):", ""]
        L += calibration_table(rel)
        L += [""]
    b = largest_bin(val, "24")
    if b["mean_forecast"] > b["observed"]:
        L += [f"Reading: the class forecast scores better than trend extrapolation, which "
              f"projects recent growth forward. But the class forecast itself forecast more growth "
              f"than the {', '.join(sorted(s1['24']['origins_by_year']))} origins delivered: in "
              f"its largest 24-month bin the doubling event was forecast at "
              f"{f(b['mean_forecast'], 2)} and observed at {f(b['observed'], 2)}. If that "
              f"pattern holds, the headline overstates the chance of coverage rather than "
              f"understating it.", ""]
    else:
        L += ["Reading: in its largest 24-month bin the class forecast did not over-forecast "
              "the doubling event.", ""]
    return L


TERTIARY = "tertiary (specified after the secondary results)"


def correction_sentence(res: dict) -> list[str]:
    """Return the summary sentence on the correction for past over-forecasting, or nothing."""
    m = res["recalibration"]["models"]["C0"]
    if not m["held_out_12"]["improves"]:
        return []
    n12, n24 = m["near"]["12"], m["near"]["24"]
    return [f"Corrected for past over-forecasting [{TERTIARY}]: in the past, outcomes at this "
            f"forecast level happened with a frequency of {f(n24['P_cal'])} at 24 months "
            f"(map fitted on the same origins, not tested out of sample) and {f(n12['P_cal'])} "
            f"at 12 months (map tested out of sample on later origins), against the "
            f"registered {f(res['headline']['P'])}."]


def section_correction(res: dict) -> list[str]:
    """Return the section 'Correcting for past over-forecasting' (PREREG_3 T1 to T4)."""
    rec, cal, tot = res["recency"], res["recalibration"], res["total_uncertainty"]
    ch = rec["choice"]
    m = cal["models"]["C0"]
    ho, ins = m["held_out_12"], m["in_sample_24"]
    hd = ch["held_out_difference"]
    L = ["## 8. Correcting for past over-forecasting", "",
         f"Everything in this section is {TERTIARY}, fixed in `PREREG_3.md` before it was run, "
         f"and reported whatever it shows. The registered probability does not change.", "",
         "**Recency weighting (T1).** Older outcomes may describe a faster-growing period, so "
         "class moments were down-weighted by their age with half-life H. Mean CRPS on the "
         "12-month targets with origins up to 2024: "
         + ", ".join(f"H = {k} months: {f(v)}" if k != "inf" else f"no weighting: {f(v)}"
                     for k, v in ch["choice_mean_crps"].items()) + ". "
         + (f"On the {hd['targets']} later targets (origins 2025), CRPS(C_{ch['best_on_choice_set']})"
            f" - CRPS(C0) = {f(hd['mean'], 4)} ({f(hd['interval'][0], 4)} to "
            f"{f(hd['interval'][1], 4)}). " if hd else "")
         + ("Recency weighting did not help on data it did not see, so it is not used."
            if ch["H_star"] == "inf" else
            f"Recency weighting with H = {ch['H_star']} months beat the class forecast on data "
            f"it did not see, and is used below."), "",
         f"**Recalibration (T2).** The map from forecast to observed frequency was fitted on the "
         f"PIT values of the {ho['train_targets']} 12-month targets with origins up to 2024 and "
         f"tested on the {ho['test_targets']} targets with origins 2025 "
         f"({ho['test_entities']} protocols):", "",
         "| Score (origins 2025) | Raw class forecast | Recalibrated | Difference (90% CI) |",
         "|---|---|---|---|"]
    d = ho["difference"]
    for k, name in (("brier_1", "Brier, fees maintained"), ("brier_2", "Brier, fees doubled"),
                    ("brier_5", "Brier, fees at least 5x")):
        L.append(f"| {name} | {f(ho['raw'][k], 4)} | {f(ho['recalibrated'][k], 4)} | "
                 f"{f(d[k]['mean'], 4)} ({f(d[k]['interval'][0], 4)} to "
                 f"{f(d[k]['interval'][1], 4)}) |")
    L.append(f"| KS distance of PIT to uniform | {f(ho['raw']['ks'], 3)} | "
             f"{f(ho['recalibrated']['ks'], 3)} | {f(d['ks']['mean'], 3)} "
             f"({f(d['ks']['interval'][0], 3)} to {f(d['ks']['interval'][1], 3)}) |")
    for c in ("cov_50", "cov_90"):
        L.append(f"| Coverage of the central {c[4:]}% interval | {f(ho['raw'][c], 3)} | "
                 f"{f(ho['recalibrated'][c], 3)} | |")
    L += ["", "Reliability on origins 2025, event 'fees at least doubled':", "",
          "| Forecast | Bin | Targets | Mean forecast | Observed |", "|---|---|---|---|---|"]
    for name, key in (("raw", "raw"), ("recalibrated", "recalibrated")):
        for b in ho[key]["reliability"]["Y_ge_ln2"]:
            if b["targets"]:
                L.append(f"| {name} | {f(b['bin'][0], 2)} to {f(b['bin'][1], 2)} | "
                         f"{b['targets']} | {f(b['mean_forecast'], 3)} | "
                         f"{f(b['observed'], 3)} |")
    L += ["", ("Recalibration improved the held-out scores (lower Brier score for all three "
               "events, with at least one interval below 0 and none above)."
               if ho["improves"] else
               "Recalibration did not improve the held-out scores by the rule fixed for this "
               "section (lower Brier score for all three events, at least one interval below 0, "
               "none above), so it is not quoted as a correction."), "",
          f"At 24 months the map is fitted on all {ins['targets']} targets ({ins['note']}): "
          f"Brier for 'fees doubled' {f(ins['raw']['brier_2'], 4)} raw against "
          f"{f(ins['recalibrated']['brier_2'], 4)} recalibrated, in sample.", "",
          "**For NEAR Intents.** The registered probability comes first; then how often "
          "outcomes at this forecast level happened in the past:", "",
          "| Horizon | Registered P (90% CI) | Recency-weighted P | P_cal (90% CI) | "
          "P_cal tested out of sample |", "|---|---|---|---|---|"]
    for h in ("12", "24"):
        prim = primary_row(res, "R", int(h))
        n = m["near"][h]
        recency_text = ("not used" if ch["H_star"] == "inf" else
                        f"{f(rec['near']['by_h'][h]['P'])} "
                        f"({interval(rec['near']['by_h'][h]['interval'])})")
        L.append(f"| {h} months | {f(prim['P'])} ({f(prim['P_lo'])} to {f(prim['P_hi'])}) | "
                 f"{recency_text} | {f(n['P_cal'])} ({interval(n['interval'])}) | "
                 f"{'yes (origins 2025)' if n['tested_out_of_sample'] else 'no (in sample)'} |")
    L += ["", f"P_cal = 1 - G(F_R(ln k*)): F_R(ln k*) is where k* sits in the class R forecast "
          f"({f(m['near']['24']['F_R'], 3)} at 24 months), and G says how often past outcomes "
          f"fell above that forecast level. At 24 months it rests on {m['near']['24']['targets']}"
          f" targets from {m['near']['24']['entities']} protocols with origins in one year.", "",
          f"**One interval for sampling and class definition (T3).** Pooling the 2000 bootstrap "
          f"values of each of the {tot['groups']} class definitions of the multiverse: 5th "
          f"percentile {f(tot['p5'])}, median {f(tot['p50'])}, 95th percentile {f(tot['p95'])}. "
          f"{pct(tot['between_share'])} of the pooled variance lies between class definitions.",
          "", "**Tail model (T4, optional).** Not reported: in exploratory runs the share of "
          "bootstrap fits of the generalised Pareto tail that did not converge was close to the "
          "5 percent stop line of `PREREG_3.md` and depended on the numerical definition of "
          "convergence (details in `PROGRESS.md`).", ""]
    return L


def section_robustness(res: dict) -> list[str]:
    """Return section 8."""
    s, mv, coh = res["speccurve"], res["class_multiverse"], res["cohorts"]
    loo = coh["leave_one_year_out"]
    tb = coh["two_stage_bootstrap"]
    return [
        "## 9. Robustness", "",
        f"Specification curve (registered): {s['rows']} combinations of window, class, horizon, "
        f"capture, issuance and price, all with the class frequency. P has median "
        f"{f(s['median'])}, minimum {f(s['min'])}, maximum {f(s['max'])}.", "",
        f"Class multiverse [{SECONDARY}]: {mv['specifications']} ways to build the class (scale "
        f"band, age band, weighting, categories). P has median {f(mv['median'])}, minimum "
        f"{f(mv['min'])}, maximum {f(mv['max'])}; {mv['below_30_entities']} specifications "
        f"have fewer than 30 protocols (`results/class_multiverse.csv`).", "",
        f"Origin-year cohorts [{SECONDARY}]: leaving one origin year out gives "
        + ", ".join(f"without {y}: {f(v['P'])}" for y, v in loo.items() if v)
        + f". A two-stage bootstrap over years and (protocol, year) blocks, indicative only, "
        f"gives {interval(tb['interval'])}.", "",
    ]


def section_others(res: dict) -> list[str]:
    """Return section 9: the audit and the forward requirements of other theses."""
    a = res["audit"]
    sc = a["status_counts"]
    fwd = [r for r in res["forward_claims_rows"] if r["h"] == "24"]
    L = [
        "## 10. How other theses measure the same thing, and what they need to be true", "",
        f"{a['claims']} published values from {a['theses']} public NEAR theses, each read at a "
        f"fixed commit (file and line in `data/claims.csv`). For each: y = their value, r = ours "
        f"under their window, end date and definition, r0 = ours under our primary definition "
        f"at {a['t0']}; e = ln(y/r) (reproduced if |e| <= ln 1.02), s = ln(r/r0), "
        f"ln(y/r0) = s + e. Reproduced: {sc['reproduced']}; not reproduced by us: "
        f"{sc['not reproduced by us']}; not recomputed: {sc['not recomputed']}. The status "
        f"compares their figure with our recomputation under our reading of their definition, "
        f"to 2 percent; it does not say their figure is wrong. DefiLlama can revise its "
        f"history.", "",
        "| Thesis | Metric | y | r | r0 | e | s | Status |", "|---|---|---|---|---|---|---|---|",
    ]
    for r in res["audit_rows"]:
        def g(key):
            if r[key] == "":
                return ""
            x = float(r[key])
            if key in ("e", "s"):
                return f"{x:.4f}".replace("-0.0000", "0.0000")
            return usd(x) if r["metric"] in ("M1", "M4") else f"{x:.4f}"
        L.append(f"| {r['thesis']} | {r['metric']} | {g('y_common')} | {g('r_common')} | "
                 f"{g('r0')} | {g('e')} | {g('s')} | {r['status']} |")
    L += ["", "Dispersion of ln y across theses (IQR, only when n >= 5): " + "; ".join(
        f"{m}: n = {d['n']}" + ("" if d["iqr_ln"] is None else f", IQR = {f(d['iqr_ln'])}")
        for m, d in a["dispersion"].items()) + ".", "",
          f"What they need to be true [{SECONDARY}]: {len({r['thesis'] for r in fwd})} theses "
          f"state a growth multiple that would make buybacks offset issuance, or reach another "
          f"target. Placed on the class R curve at 24 months (none states a horizon; 12 and 36 "
          f"months are in `results/forward_claims.csv`):", "",
          "| Thesis | Required multiple | Condition | P at 24 months (90% CI) |",
          "|---|---|---|---|"]
    L += [f"| {r['thesis']} | {f(r['k'], 2)}x | {r['condition']} | {f(r['P'])} "
          f"({f(r['P_lo'])} to {f(r['P_hi'])}) |" for r in fwd]
    L += ["", "The base rate is about fee growth in class R; applying it to revenue or volume "
          "assumes a constant take rate.", ""]
    return L


def section_change(res: dict) -> list[str]:
    """Return section 10."""
    wc = res["headline"]["what_would_change"]
    reg = res["registered_forecast"]["forecasts"]
    return [
        "## 11. What would change our mind", "",
        f"P crosses 0.50 (PREREG 8) when the required growth k* falls to {f(wc['k50'], 3)}x or "
        f"below. On its own that needs a capture rate of {f(wc['kappa_needed'], 3)} of gross "
        f"fees" + (" (above 1, impossible)" if wc["kappa_needed"] > 1 else "")
        + f", or issuance cut by {pct(wc['G_I_cut_needed'])}, or a NEAR price at "
        f"{f(wc['G_P_needed'], 3)}x today's. Single-factor rows of the registered grid: "
        + "; ".join(f"{r['factor']} = {r['value']}: P = {f(r['P'])}"
                    for r in wc["single_factor_grid_rows"])
        + (". None crosses 0.50." if not wc["any_grid_row_crosses"] else
           ". At least one crosses 0.50."), "",
        "The data would change our mind if coverage C_90 rises toward 1 on the daily snapshots "
        "(`history.csv`), if a later backtest with more origin years shows the class frequency "
        "under-forecasting growth, or if the registered forecasts resolve against us on "
        + ", ".join(v["resolution_date"] for v in reg.values()) + " (`RESOLUTION.md`).", "",
    ]


def section_registration(res: dict) -> list[str]:
    """Return section 12."""
    reg = res["registered_forecast"]
    dev = res["deviations"].split("\n", 1)[1].strip() if "\n" in res["deviations"] else ""
    dev = "\n".join(("**" + line[3:] + "**") if line.startswith("## ") else line
                    for line in dev.splitlines())
    counts = res["refclass_counts"]
    L = ["## 13. Pre-registration, addenda, deviations, resolution", "",
         "`PREREG.md` fixed the question, data, estimators, backtest and decision rules before "
         "any reference-class fee history was downloaded. `PREREG_2.md` added the secondary "
         "analyses after the primary results were known; everything it specifies is labelled "
         f"\"{SECONDARY}\" and reported whatever it shows. `PREREG_3.md` added the corrections "
         f"for past over-forecasting after the secondary results; they are labelled "
         f"\"{TERTIARY}\".", "",
         f"Stop rules (PREREG 9): reference panel missing share "
         f"{pct(counts['panel']['missing_share'])} ({counts['panel']['missing']} of "
         f"{counts['panel']['universe']} entries); class R at h = 24 has "
         f"{counts['classes']['R']['24']['entities']} entities "
         + ("(below 30: R_all_ages is primary)." if res["headline"]["stop_rule_R_below_30"]
            else "(30 or more: R stays primary).")
         + " Control values of `docs/SPEC.md` section 5: reproduced (`tests/test_coverage.py`).",
         ""]
    if "rpc_supply" in res:
        rp = res["rpc_supply"]
        worst = max(abs(r["rel_diff"]) for r in rp["supply"] if r["edge"] == rp["closest_edge"])
        L += [f"Second route for total supply: the NEAR block header at the "
              f"{rp['closest_edge'].replace('_', ' ')} (UTC) of {rp['days'][0]} and "
              f"{rp['days'][1]}, read from {rp['rpc']}, differs from NearBlocks by at most "
              f"{worst:.2e} in relative terms (`results/rpc_supply.json`).", ""]
    L += ["Deviations and errata (`DEVIATIONS.md`):", "", dev if dev else "None.", "",
          f"Resolution [{SECONDARY}, S11]: the registered forecasts of {reg['t0']} are frozen in "
          f"`results/registered_forecast.json`: "
          + "; ".join(f"{h} months: P = {f(v['P'])}, resolves on {v['resolution_date']}"
                      for h, v in reg["forecasts"].items())
          + ". Command: `uv run python -m near_posterior.resolve`.", ""]
    return L


def render(res: dict) -> str:
    """Return the text of THESIS.md built from the parsed results."""
    c = res["coverage"]
    L = [
        "# Will NEAR buybacks cover net issuance at the 24-month mark?", "",
        f"Generated by `uv run python -m near_posterior.build` from `results/` only. NEAR "
        f"snapshot fetched {c['fetched_at']}, t0 = {c['t0']}. Rules: `PREREG.md` (registered) "
        f"and `PREREG_2.md` (secondary). Not financial advice.", "",
        "## 1. Summary", "",
        " ".join(summary(res)), "",
    ]
    L += section_question(res)
    L += section_outside_view(res)
    L += section_momentum(res)
    L += section_within(res)
    L += section_levers(res)
    L += section_method(res)
    L += section_correction(res)
    L += section_robustness(res)
    L += section_others(res)
    L += section_change(res)
    L += ["## 12. What this cannot tell you", ""] + [f"- {t}" for t in limits(res)] + [""]
    L += section_registration(res)
    return "\n".join(L)


def main() -> None:
    """Rewrite THESIS.md from results/."""
    out.write_text(out.ROOT / "THESIS.md", render(load_results()))


if __name__ == "__main__":
    main()
