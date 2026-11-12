"""Rebuild every result, THESIS.md and history.csv offline, in order.

Run: `python -m near_posterior.build`. Reads `data/raw/` and the frozen `data/refclass/`; never
touches the network.
"""

import csv
import io
import json

import numpy as np

from near_posterior import (audit, backtest, coverage, exceedance, levers, multiverse, out,
                            readme, refclass, rpc_check, site, speccurve, thesis, within)

CURVE_HEADER = ["cls", "window", "W", "h", "capture", "issuance", "G_P", "G_kappa", "G_I", "C_W",
                "kappa_W", "k_star", "P", "P_lo", "P_hi", "entities", "moments"]
HISTORY_HEADER = ["fetched_at", "t0", "model", "class", "P", "P_lo", "P_hi", "entities",
                  "k_star", "C_90", "verdict"]
HISTORY = out.ROOT / "history.csv"


def history_text(previous: str, head: dict) -> str:
    """Return history.csv with the row of this snapshot added or replaced, sorted by time."""
    rows = {}
    if previous:
        for r in csv.reader(io.StringIO(previous)):
            if r and r[0] != "fetched_at":
                rows[r[0]] = r
    new = [head["fetched_at"], head["t0"], head["model"], head["class"], head["P"],
           head["interval"][0], head["interval"][1], head["entities"], head["k_star"],
           head["C_90"], head["verdict"]]
    rows[head["fetched_at"]] = list(csv.reader(io.StringIO(out.csv_text(HISTORY_HEADER, [new]))))[1]
    return out.csv_text(HISTORY_HEADER, [rows[k] for k in sorted(rows)])


def compute(previous_history: str = "") -> dict:
    """Return {relative path: text} of every generated file, computed in memory."""
    snap = coverage.load()
    cov = coverage.summary(snap)
    F_near = cov["F_near"]
    panel = refclass.load_panel()
    counts, excluded = refclass.summary(panel, F_near)
    ov = refclass.origin_values(panel)
    moms = {h: refclass.moments(panel, h, ov) for h in refclass.HORIZONS}
    bt, bt_rows = backtest.run_all(panel, F_near)
    audit_rows, audit_summary = audit.run(audit.load_snapshot(), audit.load_claims())
    curve = speccurve.run(panel, snap, F_near, moms)
    head = speccurve.headline(panel, cov, bt["choice"], moms, counts, curve)
    summary = speccurve.summarise(curve, head["class"])
    exc = exceedance.compute(panel, cov, moms, curve)
    primary = {r["h"]: r for r in curve if r["cls"] == "R" and r["window"] == "90"
               and r["capture"] == "constant" and r["issuance"] == "constant" and r["G_P"] == 1.0}
    wit = within.compute(panel, cov, moms, ov, primary)
    sample24 = exceedance.class_sample(panel, moms[24], F_near)
    lev = levers.compute(sample24, cov, levers.load_governance())
    mv = multiverse.run(panel, moms[24], F_near, head["k_star"])
    years24 = np.array([refclass.month_start(int(m)).year for m in sample24["month"]])
    coh = multiverse.cohorts(sample24["Y"], sample24["e"], years24, head["k_star"])
    files = {
        "results/coverage.json": out.json_text(cov),
        "results/refclass_counts.json": out.json_text(counts),
        "data/refclass/excluded.csv": out.csv_text(
            ["h", "entity_id", "origin", "present_days_in_outcome_window"], excluded),
        "results/backtest.json": out.json_text(bt),
        "results/backtest_targets.csv": out.csv_text(backtest.CSV_HEADER, bt_rows),
        "results/audit.csv": out.csv_text(audit.HEADER, audit_rows),
        "results/audit.json": out.json_text(audit_summary),
        "results/speccurve.csv": out.csv_text(CURVE_HEADER,
                                              [[r[k] for k in CURVE_HEADER] for r in curve]),
        "results/speccurve.json": out.json_text(summary),
        "results/headline.json": out.json_text(head),
        "results/exceedance.csv": out.csv_text(["h", "k", "P", "P_lo", "P_hi"], exc["exceedance"]),
        "results/growth_quantiles.json": out.json_text(exc["growth"]),
        "results/coverage_quantiles.json": out.json_text(exc["coverage"]),
        "results/entities_R.csv": out.csv_text(exceedance.ENTITY_HEADER, exc["entities"]),
        "results/within.json": out.json_text(wit),
        "results/levers.csv": out.csv_text(levers.HEADER, lev),
        "results/class_multiverse.csv": out.csv_text(multiverse.HEADER, mv),
        "results/class_multiverse.json": out.json_text(multiverse.summary(mv)),
        "results/cohorts.json": out.json_text(dict(coh, k_star=head["k_star"], h=24,
                                                   label="secondary (specified after the "
                                                         "primary results)")),
    }
    if rpc_check.RPC_FILE.exists():
        rpc = json.loads(rpc_check.RPC_FILE.read_text(encoding="ascii"))
        files["results/rpc_supply.json"] = out.json_text(rpc_check.compare(snap, rpc))
    res = {name: json.loads(files[f"results/{name}.json"]) for name in
           ("coverage", "refclass_counts", "backtest", "audit", "speccurve", "headline")}
    res["audit_rows"] = list(csv.DictReader(io.StringIO(files["results/audit.csv"])))
    res["speccurve_rows"] = list(csv.DictReader(io.StringIO(files["results/speccurve.csv"])))
    res["deviations"] = (out.ROOT / "DEVIATIONS.md").read_text(encoding="ascii")
    if "results/rpc_supply.json" in files:
        res["rpc_supply"] = json.loads(files["results/rpc_supply.json"])
    files["THESIS.md"] = thesis.render(res)
    files["site/index.html"] = site.render(res)
    files["history.csv"] = history_text(previous_history, res["headline"])
    files["_headline"] = thesis.headline_line(res)
    files["_fetched_at"] = res["headline"]["fetched_at"]
    files["_readme_blocks"] = readme.blocks(res)
    files["README.md"] = readme.fill(readme.README.read_text(encoding="ascii"),
                                     files["_readme_blocks"])
    return files


def main() -> None:
    """Write every generated file and print the headline line."""
    previous = HISTORY.read_text(encoding="ascii") if HISTORY.exists() else ""
    files = compute(previous)
    for rel, text in files.items():
        if not rel.startswith("_"):
            out.write_text(out.ROOT / rel, text)
    print(files["_headline"])


if __name__ == "__main__":
    main()
