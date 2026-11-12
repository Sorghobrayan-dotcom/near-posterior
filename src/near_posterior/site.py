"""Render site/index.html from results/ only: inline SVG, no script, no external request.

Run: `python -m near_posterior.site` rewrites site/index.html from the committed results/.
"""

import math

from near_posterior import out, svg, thesis
from near_posterior.thesis import f, interval, usd

CSS = """body{font-family:Georgia,serif;max-width:760px;margin:0 auto;padding:16px;color:#111;
background:#fff;line-height:1.45}h1{font-size:1.5em}h2{font-size:1.15em;margin-top:2em}
code{font-size:.85em;background:#f3f3f3;padding:1px 3px}table{border-collapse:collapse;
font-size:.8em;width:100%}td,th{border-bottom:1px solid #ddd;padding:2px 4px;text-align:right}
td:first-child,th:first-child{text-align:left}.q{font-size:.85em;color:#333}
.head{border:1px solid #999;padding:8px;background:#fafafa}"""


def chart(title: str, body: str, query: str, sentence: str) -> str:
    """Return one chart block: title, the chart, the query behind it and one plain sentence."""
    return (f"<section>\n<h2>{svg.esc(title)}</h2>\n{body}\n"
            f'<p class="q">Query: <code>{svg.esc(query)}</code></p>\n'
            f"<p>{svg.esc(sentence)}</p>\n</section>")


def coverage_chart(res: dict) -> str:
    """Return the coverage-over-time chart."""
    c = res["coverage"]
    days = c["daily"]
    body = svg.line_chart([("C_30", [d["C_30"] for d in days], "#3060a0"),
                           ("C_90", [d["C_90"] for d in days], "#e07020")],
                          [d["date"] for d in days], "coverage", hline=(1.0, "coverage = 1"))
    w90 = next(w for w in c["windows"] if w["window"] == "90")
    return chart("Coverage of net issuance by buybacks, since " + c["buyback_start"], body,
                 "near_posterior.coverage.summary -> results/coverage.json: daily[].C_30, "
                 "daily[].C_90",
                 f"Over the 90 days to {c['t0']}, buybacks equal {f(w90['C'])} of the dollar value "
                 f"of net issuance; at 1 they would offset it.")


def multiple_chart(res: dict) -> str:
    """Return the required-multiple-by-window chart."""
    c = res["coverage"]
    rows = c["windows"]
    labels = [f"{r['W']} days" if r["window"] != "since" else f"since {c['buyback_start']}"
              for r in rows]
    body = svg.bar_chart(labels, [r["k_star_h24"] for r in rows], "k* at h = 24")
    lo = min(rows, key=lambda r: r["k_star_h24"])
    hi = max(rows, key=lambda r: r["k_star_h24"])
    return chart("Required fee growth k* by window (h = 24, capture, price, issuance rate constant)",
                 body, "near_posterior.coverage.summary -> results/coverage.json: windows[].k_star_h24",
                 f"Fees would have to grow between {f(lo['k_star_h24'], 2)}x ({lo['W']}-day window) "
                 f"and {f(hi['k_star_h24'], 2)}x ({hi['W']}-day window) in 24 months for buybacks "
                 f"to cover issuance.")


def distribution_chart(res: dict) -> str:
    """Return the histogram of 24-month log fee growth in the headline class, k* marked."""
    h = res["headline"]
    floor = math.log(0.01)
    Y = [max(y, floor) for y in h["class_Y"]]
    width = 0.5
    lk = math.log(h["k_star"])
    lo = lk - math.ceil((lk - min(Y)) / width) * width
    edges = [lo + i * width for i in range(int((max(Y) - lo) // width) + 1)]
    counts = [sum(1 for y in Y if e <= y < e + width) for e in edges]
    colours = ["#b00020" if e >= lk - 1e-9 else "#3060a0" for e in edges]
    body = svg.bar_chart([f"{math.exp(e):.2g}x" for e in edges], counts, "moments",
                         colours=colours, every=2)
    n_hit = sum(1 for y in h["class_Y"] if y >= lk)
    return chart(f"24-month fee growth in class {h['class']} (red: bins reaching k* = "
                 f"{f(h['k_star'], 2)}x)", body,
                 "near_posterior.speccurve.headline -> results/headline.json: class_Y, k_star",
                 f"{n_hit} of {len(Y)} moments from {h['entities']} entities reached k*; weighting "
                 f"each entity equally gives P = {f(h['P'])}. Growth below 0.01x is shown at 0.01x.")


def curve_chart(res: dict) -> str:
    """Return the specification-curve chart (sorted P, primary row in red)."""
    rows = sorted(res["speccurve_rows"], key=lambda r: (float(r["P"]), r["cls"], r["window"],
                                                        r["h"], r["capture"], r["issuance"],
                                                        r["G_P"]))
    p = res["speccurve"]["primary"]
    mark = next(i for i, r in enumerate(rows) if r["cls"] == p["cls"] and r["window"] == "90"
                and r["h"] == "24" and r["capture"] == "constant" and r["issuance"] == "constant"
                and float(r["G_P"]) == 1.0)
    body = svg.dot_chart([float(r["P"]) for r in rows], "P_B0(k*)", mark)
    s = res["speccurve"]
    return chart("Specification curve: 864 registered rows, sorted (red: primary row)", body,
                 "near_posterior.speccurve.run -> results/speccurve.csv: P",
                 f"Across all registered choices of window, class, horizon, capture, issuance and "
                 f"price, P runs from {f(s['min'])} to {f(s['max'])} with median {f(s['median'])}.")


def backtest_chart(res: dict) -> str:
    """Return the backtest-score chart (mean CRPS with 90 percent intervals)."""
    bt = res["backtest"]
    h = str(bt["choice"]["horizon"] or 12)
    models = bt["scores"][h].get("models", {})
    names = [m for m in thesis.MODEL_ORDER if m in models]
    body = svg.bar_chart(names, [models[m]["crps"] for m in names], f"mean CRPS, h = {h}",
                         errors=[models[m]["crps_interval"] for m in names])
    return chart(f"Backtest scores by model (h = {h} months, lower is better)", body,
                 "near_posterior.backtest.run_all -> results/backtest.json: scores." + h
                 + ".models[].crps",
                 f"{bt['scores'][h]['scored']} targets from {bt['scores'][h]['entities']} entities; "
                 f"headline model {bt['choice']['model']} ({bt['choice']['reason']}).")


def analog_table(res: dict) -> str:
    """Return the table of the 30 nearest analogs of NEAR Intents."""
    h = res["headline"]
    lk = math.log(h["k_star"])
    rows = "\n".join(
        f"<tr><td>{svg.esc(r['name'])}</td><td>{svg.esc(r['category'])}</td>"
        f"<td>{r['origin']}</td><td>{usd(r['F'])}</td><td>{f(r['m'], 2)}</td><td>{r['age']}</td>"
        f"<td>{math.exp(r['Y']):.3g}x</td></tr>" for r in h["analog_table"])
    body = ("<table><tr><th>Entity</th><th>Category</th><th>Origin</th><th>F (per year)</th>"
            "<th>momentum</th><th>age (days)</th><th>24-month growth</th></tr>\n" + rows
            + "\n</table>")
    hit = sum(1 for r in h["analog_table"] if r["Y"] >= lk)
    return chart("The 30 nearest analogs of NEAR Intents (h = 24)", body,
                 "near_posterior.speccurve.headline -> results/headline.json: analog_table",
                 f"Nearest on ln fees, momentum and ln age; {hit} of {len(h['analog_table'])} "
                 f"grew fees by at least k* = {f(h['k_star'], 2)}x in 24 months.")


def dispersion_chart(res: dict) -> str:
    """Return the strip chart of other theses' figures relative to our primary values."""
    metrics = sorted(res["audit"]["metrics"])
    pts = [(metrics.index(r["metric"]), float(r["ln_y_over_r0"])) for r in res["audit_rows"]]
    body = svg.strip_chart(metrics, pts, "ln(published / ours at t0)")
    d = res["audit"]["dispersion"]
    return chart("Other theses' figures against ours", body,
                 "near_posterior.audit.run -> results/audit.csv: ln_y_over_r0",
                 "Each dot is one published value; 0 means equal to our primary value at "
                 f"{res['audit']['t0']}. Interquartile range of ln y: " + "; ".join(
                     f"{m} {f(v['iqr_ln'])} (n = {v['n']})" for m, v in d.items()
                     if v["iqr_ln"] is not None) + ".")


def render(res: dict) -> str:
    """Return the text of site/index.html built from the parsed results."""
    h = res["headline"]
    blocks = [coverage_chart(res), multiple_chart(res), distribution_chart(res), curve_chart(res),
              backtest_chart(res), analog_table(res), dispersion_chart(res)]
    return "\n".join([
        "<!doctype html>", '<html lang="en">', "<head>", '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>NEAR buybacks vs issuance</title>", f"<style>{CSS}</style>", "</head>", "<body>",
        "<h1>Will NEAR buybacks cover net issuance within 24 months?</h1>",
        f'<p class="head">{svg.esc(thesis.headline_line(res))}</p>',
        f"<p>Snapshot fetched {svg.esc(res['coverage']['fetched_at'])}. Rules fixed in "
        "<code>PREREG.md</code> before the reference panel was downloaded. Full argument: "
        '<a href="../THESIS.md">THESIS.md</a>. Rebuild: <code>uv run python -m '
        "near_posterior.build</code>. Not financial advice.</p>",
        *blocks,
        "<p class=\"q\">Data: DefiLlama (NEAR Intents fees, holders revenue, volume; fees of "
        f"{res['refclass_counts']['entities']} reference entities), NearBlocks (supply, price). "
        "Generated from results/ only.</p>",
        "</body>", "</html>", ""])


def main() -> None:
    """Rewrite site/index.html from results/."""
    out.write_text(out.ROOT / "site" / "index.html", render(thesis.load_results()))


if __name__ == "__main__":
    main()
