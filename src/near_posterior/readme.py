"""Fill the generated blocks of README.md (finding, headline line, limits) from the results."""

import json
import re

from near_posterior import onchain, out, thesis

README = out.ROOT / "README.md"


def blocks(res: dict) -> dict:
    """Return the text of each generated README block."""
    h, c = res["headline"], res["coverage"]
    w90 = next(w for w in c["windows"] if w["window"] == "90")
    def pc(x):
        return f"{100 * float(x):.1f}%"
    finding = (f"**Finding:** on the snapshot of {h['t0']}, buybacks cover {pc(w90['C'])} of "
               f"NEAR's net issuance; to cover it at the 24-month mark NEAR Intents fees must grow "
               f"{thesis.f(h['k_star'], 2)}x in 24 months. Among {h['entities']} comparable "
               f"DefiLlama protocols, the share that did so is **{pc(h['P'])}** (90% interval "
               f"{pc(h['interval'][0])} to {pc(h['interval'][1])}): {h['verdict']}.")
    m = res["recalibration"]["models"]["C0"]
    if m["held_out_12"]["improves"]:
        finding += (f" Corrected for past over-forecasting (tertiary analysis, `PREREG_3.md`), "
                    f"how often outcomes at this forecast level happened before: at 24 months, "
                    f"{thesis.pcal_text(m['near']['24'], '24', percent=True)} (fitted on the "
                    f"same origins); at 12 months, "
                    f"{thesis.pcal_text(m['near']['12'], '12', percent=True)} (tested on later "
                    f"origins).")
    parts = {
        "brief": "\n".join(f"- **{k}:** {v}" for k, v in thesis.brief(res)),
        "finding": finding,
        "headline": "```\n" + thesis.headline_line(res) + "\n```",
        "limits": "\n".join(f"- {t}" for t in thesis.limits(res)),
    }
    site = "https://sorghobrayan-dotcom.github.io/near-posterior/site/"
    parts["judges"] = "\n".join([
        f"- **No install:** [the page]({site}), [the same on-chain checks run by your browser]"
        f"({site}verify.html), [the contract `brayan-posterior.testnet`]"
        f"(https://testnet.nearblocks.io/address/brayan-posterior.testnet).",
        "- **Three commands:** `uv sync` (installs `numpy` and `pytest` into `.venv`); "
        "`uv run python -m near_posterior.verify` (rebuilds everything offline, one line per check, "
        "every line starts with `PASS`); `uv run python -m near_posterior.onchain` (read-only: "
        "`PASS` lines for the contract's code hash, each record read back from the chain equal to "
        "the repository copy, and its only key limited to `resolve`).",
        "- **Two limits:** the headline number is an upper bound: it holds price and issuance "
        "fixed, and replayed on past data the method was too optimistic. Everything written on "
        "chain is on NEAR testnet, not mainnet.",
        f"- **Two snapshots:** \"registered\" numbers (t0 = {res['registered_forecast']['t0']}) "
        f"are the ones written on chain and never recomputed; \"daily\" numbers (t0 = "
        f"{h['t0']} today) are refreshed every day, hence small differences between them.",
    ])
    if "onchain_coverage" in res:
        o = res["onchain_coverage"]
        parts["onchain"] = (
            f"- **Coverage measured from the chain alone.** Mainnet RPC readings only (total "
            f"supply from block headers, balance of `{o['account']}` at blocks "
            f"{o['heights'][0]} and {o['heights'][1]}) give a coverage of "
            f"{pc(o['coverage_onchain'])} over the {o['window_days']} days to {o['t0']}, against "
            f"{pc(o['C_90_model'])} for the model's dollar-weighted C_90 on the same date "
            f"(`results/onchain_coverage.json`). It is the wallet's net NEAR inflow, and a "
            f"buyback is not a burn.")
    if "live" in res:
        lv = res["live"]
        com = json.loads(onchain.FILE.read_text(encoding="utf-8")) if onchain.FILE.exists() else {}
        acct = com.get("live", {}).get("contract")
        if acct:
            parts["judges"] += (
                f"\n- **Resolves during judging:** a short forecast sits on a second locked "
                f"contract, [`{acct}`](https://testnet.nearblocks.io/address/{acct}), due "
                f"{lv['resolution_due'][:10]}. After that date the author writes the outcome next "
                f"to it and any NEAR account can add its own reading with `attest`.")
        parts["live"] = (
            f"- **A forecast that resolves during judging.** Specified after the primary results "
            f"(`PREREG_4.md`), it tests the machinery, not the 24-month thesis: P = "
            f"{thesis.f(lv['P'])} that C_90 on {lv['event_day']} is at least C_90 on "
            f"{lv['anchor_day']} ({lv['hits']} of {lv['n']} past {lv['k']}-day pairs), due "
            f"{lv['resolution_due']} on a second testnet contract "
            f"(`data/live/forecast.json`, `results/live.json`).")
    return parts


def fill(text: str, parts: dict) -> str:
    """Return text with each `<!-- BEGIN GENERATED name -->` block replaced by parts[name]."""
    for name, body in parts.items():
        pat = re.compile(rf"(<!-- BEGIN GENERATED {name} -->\n).*?(<!-- END GENERATED {name} -->)",
                         re.S)
        if not pat.search(text):
            raise ValueError(f"README.md has no generated block {name}")
        text = pat.sub(lambda m: m.group(1) + body + "\n" + m.group(2), text)
    return text
