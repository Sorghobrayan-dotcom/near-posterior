"""Rebuild every result, THESIS.md and history.csv offline, in order.

Run: `python -m near_posterior.build`. Reads `data/raw/` and the frozen `data/refclass/`; never
touches the network.
"""

import csv
import io
import json

from near_posterior import audit, backtest, coverage, out, refclass, site, speccurve, thesis

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
    }
    res = {name: json.loads(files[f"results/{name}.json"]) for name in
           ("coverage", "refclass_counts", "backtest", "audit", "speccurve", "headline")}
    res["audit_rows"] = list(csv.DictReader(io.StringIO(files["results/audit.csv"])))
    res["speccurve_rows"] = list(csv.DictReader(io.StringIO(files["results/speccurve.csv"])))
    res["deviations"] = (out.ROOT / "DEVIATIONS.md").read_text(encoding="ascii")
    files["THESIS.md"] = thesis.render(res)
    files["site/index.html"] = site.render(res)
    files["history.csv"] = history_text(previous_history, res["headline"])
    files["_headline"] = thesis.headline_line(res)
    return files


def main() -> None:
    """Write every generated file and print the headline line."""
    previous = HISTORY.read_text(encoding="ascii") if HISTORY.exists() else ""
    files = compute(previous)
    headline = files.pop("_headline")
    for rel, text in files.items():
        out.write_text(out.ROOT / rel, text)
    print(headline)


if __name__ == "__main__":
    main()
