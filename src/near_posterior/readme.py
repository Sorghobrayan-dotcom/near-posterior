"""Fill the generated blocks of README.md (finding, headline line, limits) from the results."""

import re

from near_posterior import out, thesis

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
