"""Render site/index.html (and three standalone SVG charts) from results/ only.

Complete without JavaScript; inline JavaScript only drives the explorer. ASCII, no external
request. Run: `python -m near_posterior.site` rewrites the page from the committed results/.
"""

import json
import math

from near_posterior import out, svg, thesis
from near_posterior.svg import ACCENT, ACCENT_LIGHT, INK, LIGHT, MID, Frame
from near_posterior.thesis import f, interval, usd

CSS = """:root{--ink:#111827;--mid:#6b7280;--accent:#c2410c;--line:#e5e7eb;--bg:#f4f1ec;
--card:#fff;--hero:#0f1419;--near:#00ec97}
*{box-sizing:border-box}
body{font-family:"Segoe UI",system-ui,-apple-system,Helvetica,Arial,sans-serif;max-width:880px;
margin:0 auto;padding:16px;color:var(--ink);background:var(--bg);line-height:1.6;font-size:16px}
header{background:var(--hero);color:#e5e7eb;border-radius:18px;padding:32px 28px;margin:8px 0 20px}
header h1{color:#fff;font-family:Georgia,"Times New Roman",serif;font-weight:normal;
font-size:2.1em;line-height:1.15;margin:.2em 0 .3em}header a{color:var(--near)}
header .q{color:#9ca3af}header code{background:#1f2933;color:#e5e7eb}
h2{font-family:Georgia,"Times New Roman",serif;font-weight:normal;font-size:1.35em;
margin:0 0 .5em;line-height:1.3}
section{background:var(--card);border-radius:14px;padding:22px 24px;margin:16px 0;
box-shadow:0 1px 3px rgba(0,0,0,.06)}section svg{max-width:100%;height:auto}
.kicker{color:var(--near);font-size:.75em;letter-spacing:.12em;text-transform:uppercase;
margin:0}.big{font-size:4.2em;font-weight:700;color:#fff;margin:.05em 0;line-height:1}
.big+p strong{color:var(--near)}
ul.brief{list-style:none;padding:0;margin:22px 0;display:grid;gap:10px;
grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}
ul.brief li{background:#1a2129;border:1px solid #2a333d;border-radius:10px;padding:12px 14px;
font-size:.9em;color:#d1d5db}ul.brief strong{display:block;color:var(--near);font-size:.8em;
text-transform:uppercase;letter-spacing:.06em;margin-bottom:2px}
.head{font-family:Consolas,monospace;font-size:.75em;background:#1a2129;color:#9ca3af;
border-radius:8px;padding:10px;overflow-wrap:anywhere}
.chain{border-left:4px solid var(--near)}.chain a{color:#047857}
@media (max-width:520px){header{padding:22px 16px}header h1{font-size:1.6em}.big{font-size:3.2em}
section{padding:16px}}
code{font-size:.85em;background:#f3f4f6;padding:1px 3px;overflow-wrap:anywhere}
.q{font-size:.85em;color:var(--mid)}
.tag{font-size:.65em;font-weight:normal;color:#fff;background:var(--mid);border-radius:3px;
padding:1px 6px;vertical-align:middle;white-space:nowrap}.wrap{overflow-x:auto}
table{border-collapse:collapse;font-size:.8em;width:100%}
td,th{border-bottom:1px solid var(--line);padding:3px 5px;text-align:right;vertical-align:top}
td:first-child,th:first-child{text-align:left}.left{text-align:left}
#explorer form{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:.5em 0}
#explorer input[type=range]{flex:1 1 200px}#ex-out{background:#fff7ed;padding:8px;
border-left:3px solid var(--accent)}"""


def chart(title: str, body: str, query: str, sentence: str, anchor: str = "",
          tag: str = "") -> str:
    """Return one chart block: title (with an optional short tag), the chart, the query behind
    it and one plain sentence."""
    ident = f' id="{anchor}"' if anchor else ""
    label = f' <span class="tag">{svg.esc(tag)}</span>' if tag else ""
    return (f"<section{ident}>\n<h2>{svg.esc(title)}{label}</h2>\n{body}\n"
            f'<p class="q">Query: <code>{svg.esc(query)}</code></p>\n'
            f"<p>{svg.esc(sentence)}</p>\n</section>")


def chain_block() -> str:
    """Return the section on the forecasts written on NEAR, from data/onchain/commitments.json."""
    path = out.ROOT / "data" / "onchain" / "commitments.json"
    if not path.exists():
        return ""
    com = json.loads(path.read_text(encoding="utf-8"))
    host = "testnet.nearblocks.io" if com["network"] == "testnet" else "nearblocks.io"
    acct = svg.esc(com["contract"])
    rows = "".join(
        f'<li>{c["h_months"]} months: P = {f(json.loads(c["record"])["P"])}, resolves '
        f'{svg.esc(json.loads(c["record"])["resolution_date"])} - '
        f'<a href="https://{host}/txns/{svg.esc(c["tx"])}">transaction</a></li>'
        for c in sorted(com["commitments"], key=lambda c: c["h_months"]))
    return (f'<section class="chain">\n<h2>Written on NEAR, before the outcome</h2>\n'
            f'<p>The registered forecasts are stored in the contract '
            f'<a href="https://{host}/address/{acct}">{acct}</a> ({svg.esc(com["network"])}). '
            f"No method can edit or delete them, and the contract refuses a resolution before "
            f"its date.</p>\n<ul>{rows}</ul>\n"
            f'<p class="q">Check: <code>uv run python -m near_posterior.onchain</code></p>\n'
            f"</section>")


def table(header: list[str], rows: list[list], left: int = 1) -> str:
    """Return an HTML table; the first `left` columns are left-aligned."""
    th = "".join(f'<th class="left">{svg.esc(h)}</th>' if i < left else f"<th>{svg.esc(h)}</th>"
                 for i, h in enumerate(header))
    body = "\n".join("<tr>" + "".join(
        f'<td class="left">{svg.esc(c)}</td>' if i < left else f"<td>{svg.esc(c)}</td>"
        for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="wrap"><table>\n<tr>{th}</tr>\n{body}\n</table></div>'


def coverage_fig(res: dict) -> Frame:
    """Return the chart of daily coverage C_30 and C_90 since buybacks started."""
    days = res["coverage"]["daily"]
    n = len(days)
    fr = Frame(0, n - 1, 0, 1.05)
    step = max(1, n // 4)
    fr.axes(list(range(0, n, step)), [0, 0.25, 0.5, 0.75, 1.0], ylabel="coverage",
            xfmt=lambda i: days[int(i)]["date"][:7])
    fr.hline(1.0, label="coverage = 1 (buybacks offset issuance)")
    fr.line([(i, d["C_30"]) for i, d in enumerate(days)], colour=LIGHT, width=1.5)
    fr.line([(i, d["C_90"]) for i, d in enumerate(days)], colour=ACCENT, width=2.5)
    fr.text(fr.x(n - 1) - 2, fr.y(days[-1]["C_90"]) - 8, f"C_90 = {f(days[-1]['C_90'])}",
            anchor="end", colour=ACCENT, weight="bold")
    fr.text(fr.x(n * 0.55), fr.y(days[int(n * 0.55)]["C_30"]) - 10, "C_30 (30-day window)",
            colour=MID, size=11)
    return fr


def exceedance_fig(res: dict, cursor: float | None = None) -> Frame:
    """Return the exceedance curve P(growth >= k) with markers for k* and other theses."""
    rows = res["exceedance_rows"]
    fr = Frame(0.01, 100, 0, 1, xlog=True, bottom=46)
    fr.axes([0.01, 0.1, 1, 10, 100], [0, 0.25, 0.5, 0.75, 1.0], xlabel="required fee growth k "
            "(log scale)", ylabel="share of protocols", xfmt=lambda v: f"{fmt_k(v)}x")
    by_h = {h: [(float(r["k"]), float(r["P"]), float(r["P_lo"]), float(r["P_hi"]))
                for r in rows if r["h"] == h] for h in ("12", "24", "36")}
    b = by_h["24"]
    fr.band([r[0] for r in b], [r[2] for r in b], [r[3] for r in b])
    for h in ("12", "36"):
        fr.line([(r[0], r[1]) for r in by_h[h]], colour=MID, width=1.2, dash="4 3")
    fr.line([(r[0], r[1]) for r in b], colour=ACCENT, width=2.5)
    fr.text(fr.x(0.012), fr.y(0.22), "solid: 24 months (band: 90% interval)", colour=ACCENT,
            size=11)
    fr.text(fr.x(0.012), fr.y(0.12), "dashed: 12 and 36 months", colour=MID, size=11)
    for w in res["coverage"]["windows"]:
        if w["window"] != "90":
            fr.parts.append(f'<line x1="{fr.x(w["k_star_h24"]):.1f}" y1="{fr.h - fr.bottom}" '
                            f'x2="{fr.x(w["k_star_h24"]):.1f}" y2="{fr.h - fr.bottom - 8}" '
                            f'stroke="{INK}" stroke-width="1.5"/>')
    for k in sorted({float(r["k"]) for r in res["forward_claims_rows"]}):
        x = fr.x(k)
        fr.parts.append(f'<path d="M{x - 3:.1f},{fr.top} L{x + 3:.1f},{fr.top} '
                        f'L{x:.1f},{fr.top + 6}Z" fill="{MID}"/>')
    fr.text(fr.x(0.012), fr.top + 9, "triangles: growth other theses say is needed",
            colour=MID, size=10)
    k = res["headline"]["k_star"]
    fr.vline(k, colour=ACCENT, dash="2 2")
    fr.text(fr.x(k) + 4, fr.y(0.45), f"k* = {f(k, 2)}x", colour=ACCENT, size=12, weight="bold")
    if cursor is not None:
        x = fr.x(cursor)
        fr.parts.append(f'<line id="cursor" x1="{x:.1f}" y1="{fr.top}" x2="{x:.1f}" '
                        f'y2="{fr.h - fr.bottom}" stroke="{INK}" stroke-width="1"/>')
    return fr


def fmt_k(v: float) -> str:
    """Return a growth multiple as a short label."""
    return f"{v:g}" if v >= 1 else f"{v:.2f}".rstrip("0")


def coverage_dist_fig(res: dict) -> Frame:
    """Return box plots of coverage at 12, 24 and 36 months in the class."""
    q = res["coverage_quantiles"]["by_h"]
    fr = Frame(-0.6, 2.6, 0.0003, 3, ylog=True)
    fr.axes([0, 1, 2], [0.001, 0.01, 0.1, 1], ylabel="coverage at the horizon (log)",
            xfmt=lambda v: f"{int(v) * 12 + 12} months")
    fr.hline(1.0, label="coverage = 1")
    fr.hline(res["coverage_quantiles"]["C_90_t0"], colour=LIGHT, dash="2 2",
             label=f"today {f(res['coverage_quantiles']['C_90_t0'], 2)}")
    for i, h in enumerate(("12", "24", "36")):
        v = q[h]
        fr.line([(i, v["0.05"]), (i, v["0.95"])], colour=MID, width=1.2)
        fr.rect(i - 0.22, v["0.25"], i + 0.22, v["0.75"], colour=ACCENT_LIGHT, stroke=ACCENT)
        fr.line([(i - 0.22, v["0.5"]), (i + 0.22, v["0.5"])], colour=ACCENT, width=3)
        fr.text(fr.x(i + 0.26), fr.y(v["0.5"]) + 4, f"median {f(v['0.5'], 3)}", size=11)
        fr.text(fr.x(i + 0.26), fr.y(v["0.95"]) + 4, f"95th {f(v['0.95'], 2)}", colour=MID,
                size=10)
    return fr


def levers_fig(res: dict) -> Frame:
    """Return the lever heat map at price factor 1 (rows capture, columns issuance)."""
    rows = res["levers_rows"]
    grid = [r for r in rows if r["label"] == "lever grid" and float(r["G_P"]) == 1.0]
    gov = [r for r in rows if r["label"] != "lever grid" and float(r["G_P"]) == 1.0]
    caps = ["kappa_90", "0.34", "0.5", "0.75", "1.0"]
    issues = ["1.0", "0.75", "0.5", "0.25"]
    gov_label = gov[0]["label"] if gov else None
    cols = issues + ([gov_label] if gov_label else [])
    fr = Frame(0, len(cols), 0, len(caps), w=480, h=300, left=118, right=10, top=30, bottom=48)
    for ci, col in enumerate(cols):
        for ri, cap in enumerate(caps):
            src = [r for r in (gov if col == gov_label else grid) if r["capture"] == cap
                   and (col == gov_label and r["label"] == gov_label
                        or col != gov_label and abs(float(r["issuance_factor"]) - float(col))
                        < 1e-9)]
            if not src:
                continue
            p = float(src[0]["P"])
            fr.rect(ci + 0.04, ri + 0.06, ci + 0.96, ri + 0.94, colour=ACCENT,
                    opacity=min(1.0, 0.08 + p / 0.5 * 0.92))
            fr.text(fr.x(ci + 0.5), fr.y(ri + 0.5) + 4, f(p, 2), anchor="middle",
                    colour="#ffffff" if p > 0.25 else INK, size=12, weight="bold")
    kappa = float(grid[0]["kappa_target"]) if grid else 0.0
    for ri, cap in enumerate(caps):
        lab = f"capture {f(kappa, 2)} (today)" if cap == "kappa_90" else f"capture {f(cap, 2)}"
        fr.text(fr.left - 6, fr.y(ri + 0.5) + 4, lab, anchor="end", size=11)
    for ci, col in enumerate(cols):
        lab = "HSP-029" if col == gov_label else f"issuance x{float(col):g}"
        fr.text(fr.x(ci + 0.5), fr.h - fr.bottom + 15, lab, anchor="middle", colour=MID, size=10)
    fr.text(fr.left, 16, "P at the 24-month mark, price unchanged (cells pass even odds at 0.50)",
            colour=MID, size=11)
    if gov_label:
        fr.text(fr.w - fr.right, fr.h - 8, "HSP-029 column: activation at t0 (assumed)",
                anchor="end", colour=MID, size=10)
    return fr


def calibration_fig(res: dict) -> Frame:
    """Return two reliability panels (12 and 24 months) for C0 and B2, event: fees doubled."""
    fr = Frame(0, 1, 0, 1, w=480, h=280, left=44, right=262, top=26, bottom=42)
    right = Frame(0, 1, 0, 1, w=480, h=280, left=262, right=16, top=26, bottom=42)
    for panel, h in ((fr, "12"), (right, "24")):
        panel.axes([0, 0.5, 1], [0, 0.5, 1], xlabel="forecast", ylabel="observed" if
                   panel is fr else "")
        panel.line([(0, 0), (1, 1)], colour=LIGHT, width=1, dash="3 3")
        panel.text(panel.left, 16, f"{h} months", size=11,
                   weight="bold")
        rel = res["validation"]["S1"][h]["reliability"]
        for name, colour in (("B2", MID), ("C0", ACCENT)):
            pts = [b for b in rel[name]["Y_ge_ln2"] if b["targets"]]
            for b in pts:
                panel.dot(b["mean_forecast"], b["observed"],
                          r=2 + 1.2 * math.sqrt(b["targets"]) ** 0.5, colour=colour, opacity=0.85)
            big = max(pts, key=lambda b: b["targets"])
            panel.text(panel.x(big["mean_forecast"]) + 8, panel.y(big["observed"]) - 6, name,
                       colour=colour, weight="bold", size=12)
    fr.parts += right.parts
    return fr


def backtest_fig(res: dict) -> Frame:
    """Return horizontal bars of mean CRPS with 90 percent intervals for every backtest."""
    bt = res["backtest"]["scores"]["12"]["models"]
    s1 = res["validation"]["S1"]
    bars = [("registered, 12 months", m, bt[m]) for m in thesis.MODEL_ORDER]
    for h in ("12", "24"):
        bars += [(f"target-centred, {h} months", m, s1[h]["models"][m]) for m in ("C0", "B1", "B2")]
    xmax = max(b[2]["crps_interval"][1] for b in bars) * 1.12
    n = len(bars) + len({b[0] for b in bars})
    fr = Frame(0, xmax, 0, n, w=480, h=40 + 20 * n, left=150, right=16, top=10, bottom=34)
    fr.axes([0, xmax / 2, xmax], [], xlabel="mean CRPS (lower is better)")
    row, last = n - 0.5, None
    for group, m, v in bars:
        if group != last:
            fr.text(6, fr.y(row) + 4, group, colour=MID, size=10, weight="bold")
            row -= 1
            last = group
        base = m in ("B0", "C0")
        fr.rect(0, row - 0.32, v["crps"], row + 0.32, colour=ACCENT if base else LIGHT)
        lo, hi = v["crps_interval"]
        fr.line([(lo, row), (hi, row)], colour=INK, width=1.2)
        fr.text(fr.left - 6, fr.y(row) + 4, m, anchor="end", size=11)
        fr.text(fr.x(hi) + 4, fr.y(row) + 4, f(v["crps"], 2), size=10, colour=MID)
        row -= 1
    return fr


def robustness_fig(res: dict) -> Frame:
    """Return dot strips of P: specification curve, class multiverse, leave one year out."""
    curve = [float(r["P"]) for r in res["speccurve_rows"]]
    mv = [float(r["P"]) for r in res["class_multiverse_rows"]]
    loo = [v["P"] for v in res["cohorts"]["leave_one_year_out"].values() if v]
    xmax = max(curve + mv + loo) * 1.1
    fr = Frame(0, xmax, 0, 3, w=480, h=200, left=150, right=16, top=10, bottom=34)
    fr.axes([0, xmax / 2, xmax], [], xlabel="P at the horizon")
    for row, (label, vals) in enumerate((("leave one year out", loo),
                                         ("class multiverse (72)", mv),
                                         ("specification curve (864)", curve))):
        for i, v in enumerate(vals):
            fr.dot(v, row + 0.2 + 0.6 * ((i * 37) % 11) / 10, r=2.2, colour=MID, opacity=0.5)
        fr.text(fr.left - 6, fr.y(row + 0.5) + 4, label, anchor="end", size=11)
    fr.vline(res["headline"]["P"], colour=ACCENT, dash="2 2",
             label=f"headline {f(res['headline']['P'])}")
    return fr


def cohorts_fig(res: dict) -> Frame:
    """Return bars of P with one origin year left out, against the headline."""
    loo = {y: v["P"] for y, v in res["cohorts"]["leave_one_year_out"].items() if v}
    ys = sorted(loo)
    top = max(list(loo.values()) + [res["headline"]["P"]]) * 1.25
    fr = Frame(-0.6, len(ys) - 0.4, 0, top, h=230)
    fr.axes(list(range(len(ys))), [0, top / 2], ylabel="P without that year",
            xfmt=lambda i: f"without {ys[int(i)]}")
    for i, y in enumerate(ys):
        fr.rect(i - 0.3, 0, i + 0.3, loo[y], colour=LIGHT)
        fr.text(fr.x(i), fr.y(loo[y]) - 4, f(loo[y]), anchor="middle", size=11)
    fr.hline(res["headline"]["P"], colour=ACCENT, label=f"all years {f(res['headline']['P'])}")
    return fr


def explorer(res: dict) -> str:
    """Return the explorer: the exceedance chart with a cursor, a k slider and a horizon switch."""
    rows = res["exceedance_rows"]
    ks = [float(r["k"]) for r in rows if r["h"] == "24"]
    h = res["headline"]
    start = min(range(len(ks)), key=lambda i: abs(math.log(ks[i] / h["k_star"])))
    ents = {hh: sorted(([r["name"], r["category"], round(float(r["largest_growth"]), 2)]
                        for r in res["entities_R_rows"] if r["h"] == hh), key=lambda x: -x[2])
            for hh in ("12", "24", "36")}
    data = {
        "k": [round(k, 6) for k in ks],
        "P": {hh: [[round(float(r["P"]), 4), round(float(r["P_lo"]), 4),
                    round(float(r["P_hi"]), 4)] for r in rows if r["h"] == hh]
              for hh in ("12", "24", "36")},
        "ent": ents, "kstar": {hh: round(v, 4) for hh, v in
                                res["growth_quantiles"]["k_star"].items()},
    }
    fr = exceedance_fig(res, cursor=h["k_star"])
    reached = [e for e in ents["24"] if e[2] >= h["k_star"]]
    static = (f"Primary k* = {f(h['k_star'], 2)}x at 24 months: P = {f(h['P'])} "
              f"({interval(h['interval'])}); {len(reached)} of {len(ents['24'])} protocols "
              f"reached it at least once: " + ", ".join(e[0] for e in reached) + ".")
    js = ("(function(){var D=" + json.dumps(data, sort_keys=True, ensure_ascii=True)
          + ";var s=document.getElementById('ex-k'),o=document.getElementById('ex-out'),"
          "c=document.getElementById('cursor'),L=" + f"{fr.left},W={fr.w - fr.left - fr.right}"
          + ";function hz(){var r=document.querySelector('input[name=ex-h]:checked');"
          "return r?r.value:'24';}function up(){var i=+s.value,h=hz(),k=D.k[i],p=D.P[h][i],"
          "e=D.ent[h].filter(function(x){return x[2]>=k;});"
          "o.textContent='k = '+k.toPrecision(3)+'x at '+h+' months: P = '+p[0].toFixed(3)+"
          "' (90% interval '+p[1].toFixed(3)+' to '+p[2].toFixed(3)+'); '+e.length+' of '+"
          "D.ent[h].length+' protocols reached it at least once'+(e.length?': '+e.map("
          "function(x){return x[0];}).slice(0,12).join(', ')+(e.length>12?', ...':''):'')+"
          "'. Primary k* at '+h+' months: '+D.kstar[h].toFixed(2)+'x.';"
          "var x=L+(Math.log10(k)+2)/4*W;c.setAttribute('x1',x);c.setAttribute('x2',x);}"
          "s.addEventListener('input',up);var r=document.querySelectorAll('input[name=ex-h]');"
          "for(var j=0;j<r.length;j++){r[j].addEventListener('change',up);}})();")
    body = (fr.svg("Exceedance curve") + "\n<form>"
            + "".join(f'<label><input type="radio" name="ex-h" value="{hh}"'
                      + (" checked" if hh == "24" else "") + f"> {hh} months</label>"
                      for hh in ("12", "24", "36"))
            + f'<input id="ex-k" type="range" min="0" max="{len(ks) - 1}" step="1" '
              f'value="{start}" aria-label="required fee growth k"></form>\n'
            f'<p id="ex-out">{svg.esc(static)}</p>\n<script>{js}</script>')
    return chart("Explorer: how often did comparable protocols grow fees by k?",
                 body, "near_posterior.exceedance.compute -> results/exceedance.csv, "
                       "results/entities_R.csv; uv run python -m near_posterior.ask --k K --h H",
                 f"Move the slider: the share of class R protocols whose fees grew at least k-fold "
                 f"falls from {f(float(rows[0]['P']))} at k = 0.01 to "
                 f"{f(float([r for r in rows if r['h'] == '24'][-1]['P']))} at k = 100 (24 months);"
                 f" ticks at the bottom mark k* for the 30-day, 180-day and since "
                 f"{res['coverage']['buyback_start']} windows.",
                 "explorer", "secondary")


def correction_fig(res: dict) -> Frame:
    """Return the reliability of the class forecast before and after recalibration on the
    held-out origins (12 months, event: fees at least doubled)."""
    ho = res["recalibration"]["models"]["C0"]["held_out_12"]
    fr = Frame(0, 0.5, 0, 0.5, w=480, h=300)
    fr.axes([0, 0.25, 0.5], [0, 0.25, 0.5], xlabel="forecast probability",
            ylabel="observed share")
    fr.line([(0, 0), (0.5, 0.5)], colour=LIGHT, width=1, dash="3 3")
    fr.text(fr.x(0.36), fr.y(0.39), "calibrated", colour=MID, size=11)
    for key, colour, name in (("raw", MID, "before"), ("recalibrated", ACCENT, "after")):
        pts = [b for b in ho[key]["reliability"]["Y_ge_ln2"] if b["targets"]]
        fr.line([(b["mean_forecast"], b["observed"]) for b in pts], colour=colour, width=1.5)
        for b in pts:
            fr.dot(b["mean_forecast"], b["observed"], r=2 + math.sqrt(b["targets"]) ** 0.5,
                   colour=colour, opacity=0.85)
        if key == "raw":
            big = max(pts, key=lambda b: b["targets"])
            fr.text(fr.x(big["mean_forecast"]) + 6, fr.y(big["observed"]) + 18,
                    f"{name} recalibration", colour=colour, weight="bold", size=12)
        else:
            top = max(pts, key=lambda b: b["mean_forecast"])
            fr.text(fr.x(top["mean_forecast"]) - 4, fr.y(top["observed"]) - 14,
                    f"{name} recalibration", anchor="end", colour=colour, weight="bold", size=12)
    return fr


def correction_block(res: dict) -> str:
    """Return the block 'Correcting for past over-forecasting': chart, three numbers, query."""
    rec, cal = res["recency"], res["recalibration"]["models"]["C0"]
    ho = cal["held_out_12"]
    rows = []
    for h in ("12", "24"):
        prim = thesis.primary_row(res, "R", int(h))
        n = cal["near"][h]
        rows.append([f"{h} months", f"{f(prim['P'])} ({f(prim['P_lo'])} to {f(prim['P_hi'])})",
                     "not used" if rec["choice"]["H_star"] == "inf" else
                     f"{f(rec['near']['by_h'][h]['P'])}",
                     thesis.pcal_text(n, h),
                     "yes, on 2025 origins" if n["tested_out_of_sample"] else "no, in sample"])
    body = (correction_fig(res).svg("Recalibration on held-out origins") + "\n"
            + table(["Horizon", "Registered P", "Recency-weighted P", "P_cal",
                     "P_cal tested out of sample"], rows, 1))
    d = ho["difference"]["brier_2"]
    sentence = ((f"Fitted on origins up to 2024 and tested on {ho['test_targets']} targets from "
                 f"2025, recalibration lowered the Brier score for 'fees doubled' by "
                 f"{f(-d['mean'], 3)} ({f(-d['interval'][1], 3)} to {f(-d['interval'][0], 3)}); "
                 f"the registered P stays the headline and P_cal says how often outcomes at "
                 f"this forecast level happened before.")
                if ho["improves"] else
                (f"Recalibration did not improve the scores on the {ho['test_targets']} held-out "
                 f"2025 targets, so P_cal is not used as a correction; the registered P stays "
                 f"the headline."))
    return chart("Correcting for past over-forecasting", body,
                 "near_posterior.recalibration.compute -> results/recalibration.json; "
                 "results/recency.json", sentence, tag="tertiary")


def tables(res: dict) -> list[str]:
    """Return the three table blocks: who reached k*, nearest analogs, other theses."""
    h = res["headline"]
    hit = sorted((r for r in res["entities_R_rows"] if r["h"] == "24"
                  and int(r["successes_at_k_star"]) > 0), key=lambda r: -float(r["largest_growth"]))
    t1 = table(["Protocol", "Category", "Moments reaching k*", "Largest growth", "From"],
               [[r["name"], r["category"], f"{r['successes_at_k_star']} of {r['moments']}",
                 f"{f(r['largest_growth'], 1)}x", r["largest_growth_origin"][:7]] for r in hit], 2)
    t2 = table(["Protocol", "Category", "Origin", "Fees / yr", "Momentum", "Age (d)", "24m growth"],
               [[r["name"], r["category"], r["origin"], usd(r["F"]), f(r["m"], 2), r["age"],
                 f"{math.exp(r['Y']):.3g}x"] for r in h["analog_table"]], 2)
    meas = table(["Thesis", "Metric", "Theirs", "Ours, their definition", "Status"],
                 [[r["thesis"], r["metric"], f"{float(r['y_common']):.4g}",
                   "" if r["r_common"] == "" else f"{float(r['r_common']):.4g}", r["status"]]
                  for r in res["audit_rows"]], 2)
    fwd = table(["Thesis", "Required multiple", "Condition", "P at 24 months"],
                [[r["thesis"], f"{f(r['k'], 2)}x", r["condition"],
                  f"{f(r['P'])} ({f(r['P_lo'])} to {f(r['P_hi'])})"]
                 for r in res["forward_claims_rows"] if r["h"] == "24"], 3)
    a = res["audit"]
    return [
        chart(f"Who reached k* = {f(h['k_star'], 2)}x in 24 months", t1,
              "results/entities_R.csv (h = 24, successes_at_k_star > 0)",
              f"{len(hit)} of {h['entities']} class R protocols reached the required growth at "
              f"least once; their largest gains start between "
              f"{min(r['largest_growth_origin'][:4] for r in hit)} and "
              f"{max(r['largest_growth_origin'][:4] for r in hit)}."),
        chart("The 30 nearest analogs of NEAR Intents (24 months)", t2,
              "near_posterior.speccurve.headline -> results/headline.json: analog_table",
              f"Nearest on fee size, momentum and age; "
              f"{sum(1 for r in h['analog_table'] if math.exp(r['Y']) >= h['k_star'])} of "
              f"{len(h['analog_table'])} grew fees at least {f(h['k_star'], 2)}x."),
        chart("Other theses: what they measure", meas,
              "near_posterior.audit.run -> results/audit.csv",
              f"{a['claims']} values from {a['theses']} theses: {a['status_counts']['reproduced']} "
              f"reproduced within 2 percent under our reading of their definition; the status "
              f"does not say a figure is wrong."),
        chart("Other theses: what they need to be true", fwd,
              "near_posterior.forward.run -> results/forward_claims.csv",
              "Growth multiples stated by other theses, placed on the class R base rate at 24 "
              "months; applying a fee base rate to revenue or volume assumes a constant take "
              "rate.", tag="secondary"),
    ]


def root_index() -> str:
    """Return the root index.html: a redirect to site/ with a plain link, for GitHub Pages."""
    return "\n".join([
        "<!doctype html>", '<html lang="en">', "<head>", '<meta charset="utf-8">',
        '<meta http-equiv="refresh" content="0; url=site/">',
        "<title>near-posterior</title>", "</head>", "<body>",
        '<p>The page is at <a href="site/">site/</a>. The argument is in '
        '<a href="THESIS.md">THESIS.md</a>.</p>', "</body>", "</html>", ""])


def standalone(res: dict) -> dict:
    """Return the three README charts as standalone SVG files keyed by relative path."""
    return {"site/img/exceedance.svg": exceedance_fig(res).svg("Exceedance curve", True),
            "site/img/levers.svg": levers_fig(res).svg("Lever table", True),
            "site/img/calibration.svg": calibration_fig(res).svg("Calibration", True)}


def render(res: dict) -> str:
    """Return the text of site/index.html built from the parsed results."""
    h, c = res["headline"], res["coverage"]
    w90 = next(w for w in c["windows"] if w["window"] == "90")
    val = res["validation"]["S1"]
    b = thesis.largest_bin(res["validation"], "24")
    lev = [r for r in res["levers_rows"] if r["label"] == "lever grid"]
    best = max(lev, key=lambda r: float(r["P"]))
    q24 = res["coverage_quantiles"]["by_h"]["24"]
    beats_all = (val["12"]["C0_beats_B2"] and val["24"]["C0_beats_B2"]
                 and res["backtest"]["scores"]["12"]["models"]["B2"]
                 ["crps_minus_B0_interval"][0] > 0)
    top_p = max([float(r["P"]) for r in res["speccurve_rows"]]
                + [float(r["P"]) for r in res["class_multiverse_rows"]])
    loo = {y: v for y, v in res["cohorts"]["leave_one_year_out"].items() if v}
    loo_max = max(loo, key=lambda y: abs(loo[y]["P"] - h["P"]))
    blocks = [
        explorer(res),
        chart("Coverage of net issuance by buybacks, since " + c["buyback_start"],
              coverage_fig(res).svg("Coverage over time"),
              "near_posterior.coverage.summary -> results/coverage.json: daily[]",
              f"Over the 90 days to {c['t0']} buybacks equal {f(w90['C'])} of the dollar value of "
              f"net issuance; at 1 they would offset it."),
        chart("Coverage at 12, 24 and 36 months if NEAR Intents grows like class R",
              coverage_dist_fig(res).svg("Coverage distribution"),
              "near_posterior.exceedance.coverage_quantiles -> results/coverage_quantiles.json",
              f"Boxes: middle half of class R outcomes; lines: 5th to 95th percentile. At 24 "
              f"months the median coverage would be {f(q24['0.5'], 3)} and the 95th percentile "
              f"{f(q24['0.95'], 2)}.", tag="secondary"),
        chart("What NEAR controls: the lever table",
              levers_fig(res).svg("Lever table"),
              "near_posterior.levers.compute -> results/levers.csv",
              f"Each cell is P at the 24-month mark for a capture rate and an issuance path at "
              f"today's price; the highest cell in the full table (all prices) is "
              f"{f(best['P'])}, so no combination reaches even odds."
              if float(best["P"]) <= 0.5 else
              f"Each cell is P at the 24-month mark; at least one combination passes 0.50.",
              tag="secondary"),
        chart("Calibration: forecast against observed, event 'fees at least doubled'",
              calibration_fig(res).svg("Calibration"),
              "near_posterior.validation.compute -> results/validation.json: S1.*.reliability",
              f"Dots on the diagonal would be calibrated. The class forecast C0 sits closer to it "
              f"than trend extrapolation B2 but still above the observed share: at 24 months its "
              f"largest bin forecast {f(b['mean_forecast'], 2)} and saw {f(b['observed'], 2)} "
              f"({val['24']['scored']} targets, origins "
              + ", ".join(val["24"]["origins_by_year"]) + ").", tag="secondary"),
        correction_block(res),
        chart("Backtest scores", backtest_fig(res).svg("Backtest scores"),
              "results/backtest.json (registered), results/validation.json (S1)",
              "Bars: mean CRPS, lines: 90 percent intervals. The class forecast (accent) "
              + ("scores better than trend extrapolation (B2) in every backtest shown."
                 if beats_all else
                 "does not score better than trend extrapolation (B2) in every backtest."),
              tag="partly secondary"),
        chart("Robustness: specification curve, class multiverse, cohorts",
              robustness_fig(res).svg("Robustness"),
              "results/speccurve.csv, results/class_multiverse.csv, results/cohorts.json",
              f"Every registered and secondary specification gives P at or below "
              f"{f(top_p)}; the headline is {f(h['P'])}. The multiverse and the "
              f"leave-one-year-out rows are secondary.", tag="partly secondary"),
        chart("Cohorts: P with one origin year left out",
              cohorts_fig(res).svg("Cohorts"), "near_posterior.multiverse.cohorts -> "
              "results/cohorts.json",
              f"Leaving out the {loo_max} origins changes P the most (to "
              f"{f(res['cohorts']['leave_one_year_out'][loo_max]['P'])}); the result leans on "
              f"few market cycles.", tag="secondary"),
    ] + tables(res)
    links = ('<a href="../THESIS.md">THESIS.md</a> (the argument) - <a href="../PREREG.md">'
             'PREREG.md</a> (rules fixed before the data) - <a href="../PREREG_2.md">PREREG_2.md'
             '</a> (secondary analyses)')
    def pc(x):
        return f"{100 * float(x):.1f}%"
    top = [
        "<header>",
        '<p class="kicker">NEAR Hackathon - thesis track - not financial advice</p>',
        "<h1>Will NEAR buybacks cover net issuance at the 24-month mark?</h1>",
        f'<p class="big">{pc(h["P"])}</p>',
        f"<p><strong>90% interval {pc(h['interval'][0])} to {pc(h['interval'][1])}</strong> - "
        f"share of "
        f"{h['entities']} comparable DefiLlama protocols that grew fees enough - snapshot "
        f"t0 = {h['t0']} - verdict: {svg.esc(h['verdict'])}.</p>",
        f"<p>Method: buybacks cover {pc(w90['C'])} of net issuance today, so NEAR Intents fees "
        f"must grow {f(h['k_star'], 2)}x in 24 months; the number above is how often protocols "
        f"of the same size and age did that.</p>",
        '<ul class="brief">'
        + "".join(f"<li><strong>{svg.esc(k)}:</strong> {svg.esc(v.replace('`', ''))}</li>"
                  for k, v in thesis.brief(res)) + "</ul>",
        f"<p>{links}</p>",
        '<p class="q">Charts tagged <span class="tag">secondary</span> come from analyses '
        'specified after the primary results, in <a href="../PREREG_2.md">PREREG_2.md</a>; '
        'charts tagged <span class="tag">tertiary</span> from corrections specified after the '
        'secondary results, in <a href="../PREREG_3.md">PREREG_3.md</a>. Both are reported '
        "whatever they show. The number above follows PREREG.md.</p>",
        f'<p class="head">{svg.esc(thesis.headline_line(res))}</p>',
        "</header>",
    ]
    return "\n".join([
        "<!doctype html>", '<html lang="en">', "<head>", '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>NEAR buybacks vs issuance</title>", f"<style>{CSS}</style>", "</head>", "<body>",
        *top, chain_block(), *blocks,
        "<section>\n<h2>What this cannot tell you</h2>\n<ul>\n"
        + "\n".join(f"<li>{svg.esc(t)}</li>" for t in thesis.limits(res)) + "\n</ul>\n</section>",
        '<p class="q">Data: DefiLlama (NEAR Intents fees, holders revenue, volume; fees of '
        f"{res['refclass_counts']['entities']} reference entities), NearBlocks (supply, price). "
        "Generated from results/ only by <code>uv run python -m near_posterior.build</code>.</p>",
        "</body>", "</html>", ""])


def main() -> None:
    """Rewrite site/index.html and the standalone charts from results/."""
    res = thesis.load_results()
    out.write_text(out.ROOT / "site" / "index.html", render(res))
    for rel, text in standalone(res).items():
        out.write_text(out.ROOT / rel, text)


if __name__ == "__main__":
    main()
