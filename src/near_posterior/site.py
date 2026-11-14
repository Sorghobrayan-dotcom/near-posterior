"""Render site/index.html (and three standalone SVG charts) from results/ only.

Complete without JavaScript; inline JavaScript only drives the explorer. ASCII, no external
request. Run: `python -m near_posterior.site` rewrites the page from the committed results/.
"""

import json
import math

from near_posterior import out, svg, thesis
from near_posterior.svg import ACCENT, ACCENT_LIGHT, INK, LIGHT, MID, Frame
from near_posterior.thesis import f, interval, usd

CSS = """:root{--ink:#e6e8eb;--mid:#8b929b;--accent:#f97316;--line:#262a31;--bg:#0b0d10;
--card:#14171c;--card2:#1b1f26;--near:#00ec97;--blue:#2f80ed}
*{box-sizing:border-box}
body{font-family:Inter,"Segoe UI",system-ui,-apple-system,Helvetica,Arial,sans-serif;
max-width:1040px;margin:0 auto;padding:16px;color:var(--ink);background:var(--bg);
line-height:1.6;font-size:15px}
a{color:var(--blue)}
header{background:linear-gradient(180deg,#12161b,#0e1115);border:1px solid var(--line);
border-radius:14px;padding:28px;margin:8px 0 16px}
header h1{color:#fff;font-weight:700;font-size:2em;line-height:1.2;margin:.25em 0 .6em;
letter-spacing:-.01em}
h2{font-size:1.15em;font-weight:650;margin:0 0 .7em;line-height:1.3;color:#fff}
section{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:20px 22px;margin:14px 0}section svg{max-width:100%;height:auto;border-radius:8px}
.kicker{color:var(--near);font-size:.72em;letter-spacing:.12em;text-transform:uppercase;margin:0}
.big{font-size:4em;font-weight:800;color:var(--accent);margin:.1em 0 0;line-height:1;
font-variant-numeric:tabular-nums}.big+p strong{color:var(--near)}
.tiles{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin:12px 0}
.tiles div{background:var(--card2);border:1px solid var(--line);border-radius:10px;padding:12px}
.tiles span{display:block;color:var(--mid);font-size:.75em;text-transform:uppercase;
letter-spacing:.05em}.tiles b{display:block;font-size:1.6em;color:#fff;
font-variant-numeric:tabular-nums}.tiles i{display:block;font-style:normal;color:var(--mid);
font-size:.75em}.problem .tiles b{color:var(--accent)}
ul.brief{list-style:none;padding:0;margin:18px 0;display:grid;gap:10px;
grid-template-columns:repeat(auto-fit,minmax(230px,1fr))}
ul.brief li{background:var(--card2);border:1px solid var(--line);border-radius:10px;
padding:12px 14px;font-size:.88em;color:#c9cdd3}ul.brief strong{display:block;color:var(--near);
font-size:.78em;text-transform:uppercase;letter-spacing:.06em;margin-bottom:2px}
.head,pre{font-family:Consolas,"SFMono-Regular",monospace;font-size:.8em;background:#0b0d10;
color:#a7f3d0;border:1px solid var(--line);border-radius:8px;padding:12px;overflow-x:auto}
.head{color:var(--mid);overflow-wrap:anywhere}
.chain{border-left:3px solid var(--near)}
.simgrid{display:grid;gap:18px;grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.sl{display:block;margin:0 0 14px}.sl span{display:flex;justify-content:space-between;gap:8px;
font-size:.9em}.sl b{color:var(--near);font-variant-numeric:tabular-nums}
.sl input{width:100%;accent-color:var(--near)}.rp{display:flex;gap:18px;align-items:center;flex-wrap:wrap;margin-bottom:6px}.rp select{background:var(--bg);color:inherit;border:1px solid #2a2f37;border-radius:6px;padding:7px 9px;font:inherit;max-width:100%}.rp-y{color:var(--near);font-weight:600}.rp-n{color:var(--mid)}.sl input[type=number]{box-sizing:border-box;background:var(--bg);color:inherit;border:1px solid #2a2f37;border-radius:6px;padding:7px 9px;font:inherit}.sl i{color:var(--mid);font-size:.75em;font-style:normal}
.hz label{margin-right:14px;font-size:.9em}
.out{background:var(--card2);border:1px solid var(--line);border-radius:10px;padding:16px}
.out span{color:var(--mid);font-size:.75em;text-transform:uppercase;letter-spacing:.05em}
.out>b{display:block;font-size:3.2em;font-weight:800;color:var(--accent);line-height:1.1;
font-variant-numeric:tabular-nums}.out em{color:#c9cdd3;font-style:normal}
.bar{height:8px;background:#0b0d10;border-radius:4px;margin:10px 0;overflow:hidden}
.bar div{height:100%;background:var(--accent)}
.flow{display:grid;gap:8px;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
counter-reset:s}.flow div{background:var(--card2);border:1px solid var(--line);
border-top:3px solid var(--blue);border-radius:8px;padding:10px;font-size:.85em}
.flow b{display:block;color:#fff}.flow span{color:#b4bac2}
.flow div:nth-child(4){border-top-color:var(--near)}
.punch{border-color:var(--accent)}
code{font-size:.85em;background:var(--card2);color:#d1d5db;padding:1px 4px;border-radius:4px;
overflow-wrap:anywhere}
.q{font-size:.82em;color:var(--mid)}
.tag{font-size:.62em;font-weight:600;color:#0b0d10;background:var(--mid);border-radius:3px;
padding:1px 6px;vertical-align:middle;white-space:nowrap;text-transform:uppercase}
.wrap{overflow-x:auto}
table{border-collapse:collapse;font-size:.8em;width:100%;font-variant-numeric:tabular-nums}
th{color:var(--mid);font-weight:600;text-transform:uppercase;font-size:.85em}
td,th{border-bottom:1px solid var(--line);padding:6px 6px;text-align:right;vertical-align:top}
tr:hover td{background:var(--card2)}
td:first-child,th:first-child{text-align:left}.left{text-align:left}
#explorer form{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:.5em 0}
#explorer input[type=range]{flex:1 1 200px;accent-color:var(--accent)}
#ex-out{background:var(--card2);padding:10px;border-left:3px solid var(--accent);border-radius:6px}
svg rect[fill="#ffffff"]{fill:#101317}svg [fill="#1f2933"]{fill:#e6e8eb}
svg [stroke="#1f2933"]{stroke:#9aa1a9}svg [stroke="#d1d5db"]{stroke:#2a2f37}
svg [fill="#d1d5db"]{fill:#3a4049}svg [fill="#f6d3c1"]{fill:#5b2a12}
svg [stroke="#c2410c"]{stroke:#f97316}svg [fill="#c2410c"]{fill:#f97316}
@media (max-width:520px){header{padding:18px 14px}header h1{font-size:1.5em}.big{font-size:3em}
section{padding:14px}}"""


def chart(title: str, body: str, query: str, sentence: str, anchor: str = "",
          tag: str = "") -> str:
    """Return one chart block: title (with an optional short tag), the chart, the query behind
    it and one plain sentence."""
    ident = f' id="{anchor}"' if anchor else ""
    label = f' <span class="tag">{svg.esc(tag)}</span>' if tag else ""
    return (f"<section{ident}>\n<h2>{svg.esc(title)}{label}</h2>\n{body}\n"
            f'<p class="q">Query: <code>{svg.esc(query)}</code></p>\n'
            f"<p>{svg.esc(sentence)}</p>\n</section>")


def problem_block(res: dict) -> str:
    """Return the problem: what comparable protocols did, what other theses assume."""
    h = res["headline"]
    up = next(float(r["P"]) for r in res["exceedance_rows"]
              if r["h"] == "24" and abs(float(r["k"]) - 1.0) < 1e-9)
    fwd = [r for r in res["forward_claims_rows"] if r["h"] == "24"]
    ks, ps = [float(r["k"]) for r in fwd], [float(r["P"]) for r in fwd]
    def pc(x):
        return f"{100 * float(x):.0f}%"
    return (
        '<section class="problem">\n<h2>The problem: token theses promise, nobody keeps score'
        "</h2>\n<div class=\"tiles light\">"
        f"<div><span>Comparable protocols with higher fees 24 months later</span>"
        f"<b>{pc(up)}</b><i>{h['entities']} DeFi protocols at NEAR Intents' size and age, "
        f"DefiLlama</i></div>"
        f"<div><span>Growth other NEAR theses need</span><b>{min(ks):.1f}x to {max(ks):.1f}x</b>"
        f"<i>{len({r['thesis'] for r in fwd})} public theses, read at a fixed commit</i></div>"
        f"<div><span>How often comparable protocols did that</span><b>{pc(min(ps))} to "
        f"{pc(max(ps))}</b><i>same reference class, 24 months</i></div></div>\n"
        "<p>NEAR now spends NEAR Intents revenue on buying back NEAR, and many investment theses "
        "read this as a path to scarcity. What they do today is extrapolate recent growth: a "
        "trend, a multiple, a chart. Most of the protocols that once looked like NEAR Intents "
        "did not keep growing, and no one records which forecasts were right once the date "
        "has passed.</p>\n</section>")


def scoreboard(res: dict) -> str:
    """Return the scoreboard: the multiple each public thesis needs and how often it happened."""
    h = res["headline"]
    rows = [(float(r["k"]), r["thesis"], r["condition"], r["P"], r["P_lo"], r["P_hi"])
            for r in res["forward_claims_rows"] if r["h"] == "24"]
    rows.append((float(h["k_star"]), "near-posterior (this repository)",
                 "issuance rate, capture and price as today", h["P"], *h["interval"]))
    def pc(x):
        return f"{100 * float(x):.1f}%"
    body = table(["Thesis", "Fee growth it needs", "Condition", "How often that happened",
                  "90% interval"],
                 [[t, f"{k:.2f}x", c, pc(P), f"{pc(lo)} to {pc(hi)}"]
                  for k, t, c, P, lo, hi in sorted(rows)], 1)
    n = len({r[1] for r in rows}) - 1
    return chart(f"The scoreboard: {n} NEAR theses name a multiple, one base rate scores them",
                 body, "near_posterior.forward.run -> results/forward_claims.csv",
                 f"Each row is a growth multiple stated in a public NEAR thesis, read at a fixed "
                 f"commit, next to the share of {h['entities']} comparable protocols that grew "
                 f"that much in 24 months; applying a fee base rate to revenue or volume assumes "
                 f"a constant take rate.", anchor="scoreboard", tag="secondary")


def milestones_block(res: dict) -> str:
    """Return the dated milestones before the 24-month resolution."""
    m = res["milestones"]
    def pc(x):
        return f"{100 * float(x):.1f}%"
    body = table(["Date", "Month", "Coverage needed to be on the line", "Observed", "Status"],
                 [[r["date"], str(r["month"]), pc(r["C_needed"]),
                   pc(r["C_90"]) if "C_90" in r else "-", r["status"]] for r in m["milestones"]], 1)
    t = m["today"]
    return chart("Milestones: what to check before 2028", body,
                 "near_posterior.milestones.compute -> results/milestones.json",
                 f"The line goes from {pc(m['C0'])} at {m['t0']} to 100% in {m['h']} months at a "
                 f"constant growth rate; on {t['date']} coverage is {pc(t['C_90'])} against "
                 f"{pc(t['C_path'])} on the line ({t['status']}). It is a yardstick refreshed "
                 f"daily, not a forecast.", anchor="milestones", tag="descriptive")


def replay(res: dict) -> str:
    """Return the replay: every forecast of the validation backtest next to what happened."""
    rows = res["validation_targets_rows"]
    ents, taus = sorted({r["entity"] for r in rows}), sorted({r["tau"] for r in rows})
    ei, ti = {e: i for i, e in enumerate(ents)}, {t: i for i, t in enumerate(taus)}
    data = {"e": [e.replace("parent#", "") for e in ents], "t": [t[:7] for t in taus],
            "r": {}, "d": {}}
    for h in ("12", "24"):
        x = [r for r in rows if r["h"] == h]
        data["r"][h] = [[ei[r["entity"]], ti[r["tau"]], round(math.exp(float(r["Y"])), 2),
                         round(100 * float(r["C0_prob_2"])), round(100 * float(r["B2_prob_2"])),
                         int(float(r["Y"]) >= math.log(2))] for r in x]
        n = {}
        for r in x:
            n[r["entity"]] = n.get(r["entity"], 0) + 1
        data["d"][h] = ei[min(n, key=lambda e: (-n[e], e))]
    x = [r for r in rows if r["h"] == "12"]
    def mean(v):
        return f"{100 * sum(v) / len(v):.1f}%"
    js = ("(function(){var D=" + json.dumps(data, sort_keys=True, ensure_ascii=True,
                                            separators=(",", ":")) + ";"
          "function g(i){return document.getElementById(i);}"
          "var sel=g('rp-e'),tb=document.querySelector('#rp-w table'),sm=g('rp-s');"
          "function hz(){var r=document.querySelector('input[name=rp-h]:checked');"
          "return r?r.value:'12';}"
          "function show(){var h=hz(),e=+sel.value,k=0,c=0,b=0,n=0,"
          "t='<tr><th class=\"left\">Forecast made</th><th>Class method: chance fees double</th>"
          "<th>Trend extrapolation: chance fees double</th><th>Fee growth '+h+' months later</th>"
          "<th>Doubled?</th></tr>';"
          "D.r[h].forEach(function(x){if(x[0]!==e){return;}n++;k+=x[5];c+=x[3];b+=x[4];"
          "t+='<tr><td class=\"left\">'+D.t[x[1]]+'</td><td>'+x[3]+'%</td><td>'+x[4]+'%</td><td>'"
          "+x[2].toFixed(2)+'x</td><td class=\"'+(x[5]?'rp-y':'rp-n')+'\">'+(x[5]?'yes':'no')"
          "+'</td></tr>';});tb.innerHTML=t;"
          "sm.textContent=n?D.e[e]+': '+n+' past forecast'+(n===1?'':'s')+' at '+h+"
          "' months; fees doubled '+k+"
          "' time'+(k===1?'':'s')+'. On average the class method gave '+Math.round(c/n)+"
          "'% and trend extrapolation '+Math.round(b/n)+'%.':'';}"
          "function fill(){var h=hz(),seen={},cur=sel.value;"
          "D.r[h].forEach(function(x){seen[x[0]]=1;});sel.textContent='';"
          "D.e.forEach(function(name,i){if(seen[i]){var o=document.createElement('option');"
          "o.value=i;o.textContent=name;sel.appendChild(o);}});"
          "sel.value=seen[cur]?cur:D.d[h];show();}"
          "sel.addEventListener('change',show);"
          "var a=document.querySelectorAll('input[name=rp-h]');"
          "for(var j=0;j<a.length;j++){a[j].addEventListener('change',fill);}fill();})();")
    body = ('<div class="rp"><label>Protocol <select id="rp-e"></select></label><div class="hz">'
            + "".join(f'<label><input type="radio" name="rp-h" value="{h}"'
                      + (" checked" if h == "12" else "") + f"> {h} months</label>"
                      for h in ("12", "24"))
            + '</div></div>\n<p id="rp-s" class="q"></p>\n<div class="wrap" id="rp-w"><table>\n'
            f"</table></div>\n<script>{js}</script>")
    return chart(f"Replay: {len(rows)} past forecasts, each next to what happened", body,
                 "near_posterior.validation.compute -> results/validation_targets.csv",
                 f"Each row is the forecast the method gives for that protocol at that date from "
                 f"what was known then, next to what happened; over the {len(x)} forecasts at 12 "
                 f"months the class method gave a doubling "
                 f"{mean([float(r['C0_prob_2']) for r in x])} on average, trend extrapolation "
                 f"{mean([float(r['B2_prob_2']) for r in x])}, and fees doubled "
                 f"{mean([float(r['Y']) >= math.log(2) for r in x])} of the time.",
                 anchor="replay", tag="secondary")


def simulator(res: dict) -> str:
    """Return the live simulator: capture, issuance, price and horizon move k* and P."""
    rows = res["exceedance_rows"]
    w90 = next(w for w in res["coverage"]["windows"] if w["window"] == "90")
    data = {"k": [round(float(r["k"]), 6) for r in rows if r["h"] == "24"],
            "P": {hh: [round(float(r["P"]), 4) for r in rows if r["h"] == hh]
                  for hh in ("12", "24", "36")},
            "ks": {hh: round(v, 4) for hh, v in res["growth_quantiles"]["k_star"].items()},
            "c0": round(float(w90["kappa"]), 3), "reg": round(float(res["headline"]["P"]), 4)}
    # put the exact primary point (k*, P) on the 24-month curve so the defaults show the headline
    ks, i = data["ks"]["24"], 0
    while i < len(data["k"]) and data["k"][i] < ks:
        i += 1
    if 0 < i < len(data["k"]):
        t = (math.log(ks) - math.log(data["k"][i - 1])) / (math.log(data["k"][i])
                                                           - math.log(data["k"][i - 1]))
        for hh, P in data["P"].items():
            P.insert(i, data["reg"] if hh == "24" else round(P[i - 1] + t * (P[i] - P[i - 1]), 4))
        data["k"].insert(i, ks)
    data["ks"]["24"] = round(float(res["headline"]["k_star"]), 4)
    c0 = round(100 * float(w90["kappa"]), 1)
    js = ("(function(){var D=" + json.dumps(data, sort_keys=True, ensure_ascii=True) + ";"
          "function g(i){return document.getElementById(i);}"
          "function pk(h,k){var K=D.k,P=D.P[h];if(k<=K[0])return P[0];"
          "for(var i=1;i<K.length;i++){if(k<=K[i]){var t=(Math.log(k)-Math.log(K[i-1]))/"
          "(Math.log(K[i])-Math.log(K[i-1]));return P[i-1]+t*(P[i]-P[i-1]);}}return P[P.length-1];}"
          "function up(e){var c=+g('s-cap').value/100,s=+g('s-iss').value/100,"
          "p=+g('s-px').value/100,r=document.querySelector('input[name=s-h]:checked'),"
          "h=r?r.value:'24',k=D.ks[h]*s*p*D.c0/c,x=g('s-k');"
          "if(e&&e.target===x&&+x.value>0){k=+x.value;}else{x.value=k.toFixed(2);}"
          "var P=pk(h,k);"
          "g('v-cap').textContent=Math.round(c*100)+'%';g('v-iss').textContent=Math.round(s*100)+'%';"
          "g('v-px').textContent=Math.round(p*100)+'%';"
          "g('o-p').textContent=(100*P).toFixed(1)+'%';g('o-k').textContent=k.toFixed(2)+'x';"
          "g('o-n').textContent=P>0?'about 1 chance in '+Math.max(1,Math.round(1/P)):'no case in "
          "the class';g('o-b').style.width=Math.min(100,100*P)+'%';}"
          "var a=document.querySelectorAll('#sim input');for(var j=0;j<a.length;j++)"
          "{a[j].addEventListener('input',up);}up();})();")
    def slider(i, label, lo, hi, v, note):
        return (f'<label class="sl"><span>{label} <b id="v-{i}">{v}%</b></span>'
                f'<input id="s-{i}" type="range" min="{lo}" max="{hi}" step="0.1" value="{v}">'
                f"<i>{note}</i></label>")
    return (
        '<section id="sim">\n<h2>Try it: change the assumptions, watch the odds</h2>\n'
        '<div class="simgrid"><div>'
        + slider("cap", "Share of NEAR Intents fees spent on buybacks", 10, 100, c0,
                 f"today {c0}% (last 90 days)")
        + slider("iss", "NEAR issuance, % of today's path", 25, 150, 100,
                 "governance can cut it (HSP-029)")
        + slider("px", "NEAR price, % of today", 25, 400, 100,
                 "a higher price makes new supply cost more to absorb")
        + '<div class="hz">' + "".join(
            f'<label><input type="radio" name="s-h" value="{hh}"'
            + (" checked" if hh == "24" else "") + f"> {hh} months</label>"
            for hh in ("12", "24", "36")) + "</div>"
        '<label class="sl"><span>Or score any thesis: the fee multiple it needs</span>'
        f'<input id="s-k" type="number" min="0.1" max="100" step="0.01" '
        f'value="{data["ks"]["24"]:.2f}">'
        "<i>type the multiple a thesis assumes; the sliders are then ignored</i></label></div>"
        '<div class="out"><span>Chance that buybacks offset new supply</span>'
        f'<b id="o-p">{100 * data["reg"]:.1f}%</b><em id="o-n"></em>'
        '<div class="bar"><div id="o-b"></div></div>'
        '<p>Fee growth needed: <b id="o-k"></b></p>'
        f'<p class="q">Registered forecast, written on NEAR: {100 * data["reg"]:.1f}% '
        "(24 months, today's settings). The simulator explores; it does not change the "
        "registered number.</p></div></div>\n"
        '<p class="q">k* = k*(today) x issuance x price x (capture today / capture); the chance '
        "is the share of comparable protocols whose fees grew at least k* (results/exceedance.csv)."
        f"</p>\n<script>{js}</script>\n</section>")


def hood_block(res: dict) -> str:
    """Return 'under the hood': the pipeline in five steps and the core function."""
    n = res["refclass_counts"]["entities"]
    h = res["headline"]
    steps = [("1. Data", f"Fees of {n} DeFi protocols and of NEAR Intents (DefiLlama); NEAR "
              "supply and price (NearBlocks), checked on the NEAR RPC."),
             ("2. Frozen", "Rules written in PREREG.md before the download; every file "
              "pinned by sha256."),
             ("3. Model", f"Keep the {h['entities']} protocols that once had NEAR Intents' size "
              "and age; count how many grew fees at least k* in 24 months."),
             ("4. On NEAR", "The forecast goes into a NEAR contract that cannot edit or delete "
              "it."),
             ("5. Resolution", f"On {res['registered_forecast']['forecasts']['24']['resolution_date']}"
              " the outcome is written next to the forecast and scored.")]
    code = ("k_star = issuance_in_dollars / buybacks        # growth the fees need\n"
            "peers  = protocols at NEAR Intents' size and age, at any past month\n"
            "P      = mean over peers of share(fee growth in 24 months >= k_star)\n"
            "band   = bootstrap over peers (90 percent)\n"
            "# replayed on past forecasts: beats trend extrapolation, still too optimistic")
    return ('<section class="hood">\n<h2>Under the hood</h2>\n<div class="flow">'
            + "".join(f"<div><b>{svg.esc(a)}</b><span>{svg.esc(b)}</span></div>"
                      for a, b in steps)
            + "</div>\n<p>The core of the method, simplified "
              "(<code>near_posterior.forecast.b0</code>):</p>\n"
            f"<pre>{svg.esc(code)}</pre>\n</section>")


def punchline(res: dict) -> str:
    """Return the closing section."""
    due = res["registered_forecast"]["forecasts"]["24"]["resolution_date"]
    return ('<section class="punch">\n<h2>A thesis that can be proven wrong, in public</h2>\n'
            f"<p>Every number here rebuilds from one command, and the forecast sits on NEAR "
            f"until {due}. If token theses were published this way, investors could check "
            f"track records instead of promises, and this one will be checked too.</p>\n"
            "</section>")


def chain_block(res: dict) -> str:
    """Return the section on the forecasts written on NEAR, from data/onchain/commitments.json."""
    path = out.ROOT / "data" / "onchain" / "commitments.json"
    if not path.exists():
        return ""
    supply = ""
    if "rpc_supply" in res:
        r = res["rpc_supply"]
        i = r["issuance"][r["closest_edge"]]
        supply = (f"<p>The chain is also a data source: NEAR total supply is read from block "
                  f"headers on an archival RPC node. Between {r['days'][0]} and {r['days'][1]} "
                  f"that gives a net issuance of {i['I_rpc'] / 1e6:.2f} million NEAR "
                  f"({100 * i['r_rpc']:.2f}% a year), {100 * abs(i['rel_diff']):.2f}% away from "
                  f"the NearBlocks figure used in the model.</p>\n")
    com = json.loads(path.read_text(encoding="utf-8"))
    host = "testnet.nearblocks.io" if com["network"] == "testnet" else "nearblocks.io"
    acct = svg.esc(com["contract"])
    rows = "".join(
        f'<li>{c["h_months"]} months: P = {f(json.loads(c["record"])["P"])}, resolves '
        f'{svg.esc(json.loads(c["record"])["resolution_date"])} - '
        f'<a href="https://{host}/txns/{svg.esc(c["tx"])}">transaction</a></li>'
        for c in sorted(com["commitments"], key=lambda c: c["h_months"]))
    rows += "".join(
        f'<li>{svg.esc(e["kind"])} - <a href="https://{host}/txns/{svg.esc(e["tx"])}">'
        f"transaction</a></li>" for e in com.get("extras", []))
    lock = ""
    if "lock" in com:
        lock = (f' Since <a href="https://{host}/txns/{svg.esc(com["lock"]["tx"])}">this '
                f"transaction</a> the account holds no full-access key: its only key can call "
                f"<code>resolve</code>, so nobody, the author included, can replace the code or "
                f"the records.")
    return (f'<section class="chain">\n<h2>Written on NEAR, before the outcome</h2>\n'
            f'<p>The registered forecasts, the scoreboard and the milestones are stored in the '
            f'contract <a href="https://{host}/address/{acct}">{acct}</a> '
            f'({svg.esc(com["network"])}). No method can edit or delete them.{lock}</p>\n'
            f"<p>The contract refuses a resolution before its date. Once the date has passed, "
            f"any NEAR account can write its own reading of the outcome next to the author's "
            f"(<code>attest</code>): the author's word is one line among others.</p>\n"
            f"<ul>{rows}</ul>\n{supply}"
            f'<p class="q">Check: <code>uv run python -m near_posterior.onchain</code>, or '
            f'<a href="verify.html">run the same checks in your browser</a>.</p>\n'
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
    ]


VERIFY_JS = """(function(){
var RPCS={testnet:"https://rpc.testnet.fastnear.com",mainnet:"https://rpc.mainnet.fastnear.com"};
var B58="123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
var out=document.getElementById("checks"),sum=document.getElementById("sum");
function b58(u){var n=0n,s="",i;for(i=0;i<u.length;i++){n=n*256n+BigInt(u[i]);}
while(n>0n){s=B58[Number(n%58n)]+s;n=n/58n;}for(i=0;i<u.length&&u[i]===0;i++){s="1"+s;}return s;}
function hex(u){var s="",i;for(i=0;i<u.length;i++){s+=(u[i]<16?"0":"")+u[i].toString(16);}return s;}
async function sha(buf){return new Uint8Array(await crypto.subtle.digest("SHA-256",buf));}
async function file(rel){var r=await fetch("../"+rel,{cache:"no-store"});
if(!r.ok){throw new Error(rel+": "+r.status);}return r.arrayBuffer();}
async function rpc(url,params){var r=await fetch(url,{method:"POST",
headers:{"content-type":"application/json"},
body:JSON.stringify({jsonrpc:"2.0",id:"v",method:"query",params:params})});
var j=await r.json();if(j.error){throw new Error(JSON.stringify(j.error));}return j.result;}
async function view(url,acct,method,args){var r=await rpc(url,{request_type:"call_function",
finality:"final",account_id:acct,method_name:method,args_base64:btoa(args)});
return new TextDecoder().decode(new Uint8Array(r.result));}
var n=0,ko=0;
function line(ok,text){n++;if(!ok){ko++;}var li=document.createElement("li"),b=document.createElement("b");
li.className=ok?"ok":"ko";b.textContent=ok?"PASS":"FAIL";li.appendChild(b);
li.appendChild(document.createTextNode(text));out.appendChild(li);}
async function run(){out.textContent="";n=0;ko=0;sum.textContent="Reading the chain...";
var com=JSON.parse(new TextDecoder().decode(await file("data/onchain/commitments.json")));
var url=RPCS[com.network],acct=com.contract;
document.getElementById("acct").textContent=acct+" ("+com.network+")";
var acc=await rpc(url,{request_type:"view_account",finality:"final",account_id:acct});
line(acc.code_hash===b58(await sha(await file("contract/posterior_registry.wasm"))),
"The code running on "+acct+" is contract/posterior_registry.wasm of this repository (code hash "
+acc.code_hash+").");
var keys=(await rpc(url,{request_type:"view_access_key_list",finality:"final",account_id:acct})).keys;
var locked=keys.length>0&&keys.every(function(k){var p=k.access_key.permission;
return p!=="FullAccess"&&p.FunctionCall&&p.FunctionCall.method_names.join()==="resolve";});
line(locked,"The account holds no full-access key ("+keys.length+" key, limited to the method "
+"resolve): nobody, the author included, can replace the code or the records.");
var known={},files={};
com.commitments.forEach(function(c){known[c.index]={label:c.h_months+"-month forecast",record:c.record};});
(com.extras||[]).forEach(function(e){known[e.index]={label:e.kind,record:e.record};});
var count=Number(await view(url,acct,"count",""));
line(count===Object.keys(known).length,"The contract holds "+count+" records, as listed in "
+"data/onchain/commitments.json.");
for(var i=0;i<count;i++){var g=JSON.parse(await view(url,acct,"get",String(i))),k=known[i];
var same=!!k&&JSON.stringify(g.record)===JSON.stringify(JSON.parse(k.record));
var when=new Date(g.block_timestamp_ns/1e6),due=new Date(g.resolution_unix_s*1000);
line(same&&when<due,(k?k.label:"record "+i)+(g.record.P===undefined?"":" (P = "+g.record.P+")")
+": on chain since "+when.toISOString().slice(0,16).replace("T"," ")+" UTC, block "
+g.block_height+", equal to the repository copy; resolves on "+due.toISOString().slice(0,10)+", "
+(g.outcome?"outcome written":"no outcome yet")+".");
if(g.record.type===undefined&&g.record.sha256){for(var f in g.record.sha256){files[f]=g.record.sha256[f];}}}
for(var f in files){line(hex(await sha(await file(f)))===files[f],
f+" on this site has the sha256 written on chain ("+files[f].slice(0,12)+"...).");}
sum.textContent=(ko?ko+" of "+n+" checks failed":"All "+n+" checks passed")
+", read from "+url+" by your browser at "+new Date().toISOString().slice(0,19).replace("T"," ")+" UTC.";}
document.getElementById("go").addEventListener("click",function(){run().catch(function(e){
sum.textContent="Could not finish: "+e.message;});});
run().catch(function(e){sum.textContent="Could not finish: "+e.message;});})();"""


def verify_page() -> str:
    """Return site/verify.html: the checks of `near_posterior.onchain`, run by the reader's browser."""
    extra = (".chk{list-style:none;padding:0;margin:0}.chk li{padding:9px 4px;"
             "border-bottom:1px solid #20242b;font-size:.9em}.chk b{display:inline-block;"
             "width:3.6em;font-variant-numeric:tabular-nums}.ok b{color:var(--near)}"
             ".ko b{color:var(--accent)}#go{background:var(--near);color:#0b0d10;border:0;"
             "border-radius:6px;padding:8px 14px;font:inherit;font-weight:600;cursor:pointer}")
    return "\n".join([
        "<!doctype html>", '<html lang="en">', "<head>", '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Check the forecasts on NEAR</title>", f"<style>{CSS}{extra}</style>", "</head>",
        "<body>", "<header>",
        '<p class="kicker">near-posterior - check it yourself - <a href="index.html">back to the '
        "page</a></p>",
        "<h1>Do not trust this repository: ask the chain</h1>",
        '<p>Your browser reads the NEAR contract <strong id="acct"></strong> through a public RPC '
        "node and compares what it finds with the files of this site. Nothing goes through a "
        "server of ours, and the same checks run offline with "
        "<code>uv run python -m near_posterior.onchain</code>.</p>",
        '<p><button id="go" type="button">Run the checks again</button></p>',
        "</header>", "<section>", "<h2>Checks</h2>", '<p id="sum"></p>',
        '<ul class="chk" id="checks"></ul>', "</section>",
        f"<script>{VERIFY_JS}</script>", "</body>", "</html>", ""])


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
    tiles = [("Buybacks / new supply today", pc(w90["C"])),
             ("Fee growth needed in 24 months", f"{f(h['k_star'], 2)}x"),
             ("Comparable protocols", str(h["entities"])),
             ("Base rate (registered)", pc(h["P"])),
             ("Forecast stored on", "NEAR")]
    top = [
        "<header>",
        '<p class="kicker">near-posterior - NEAR Buyback Coverage Forecast - thesis track - '
        'not financial advice</p>',
        "<h1>Will NEAR's buybacks offset its new supply within 24 months?</h1>",
        '<div class="tiles">' + "".join(f'<div><span>{svg.esc(a)}</span><b>{svg.esc(b)}</b></div>'
                                        for a, b in tiles) + "</div>",
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
        "<title>NEAR Buyback Coverage Forecast</title>", f"<style>{CSS}</style>", "</head>",
        "<body>", *top, problem_block(res), scoreboard(res), simulator(res), replay(res),
        milestones_block(res), chain_block(res), hood_block(res), *blocks, punchline(res),
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
    out.write_text(out.ROOT / "site" / "verify.html", verify_page())
    for rel, text in standalone(res).items():
        out.write_text(out.ROOT / rel, text)


if __name__ == "__main__":
    main()
