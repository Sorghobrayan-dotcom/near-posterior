"""Many-analysts audit of other public NEAR theses (PREREG section 10). Descriptive only.

Run: `python -m near_posterior.audit` writes `results/audit.csv` and `results/audit.json` from
`data/claims.csv` and `data/raw/`.
"""

import csv
import datetime as dt
import math

import numpy as np

from near_posterior import coverage, out, series

CLAIMS = out.ROOT / "data" / "claims.csv"
TOLERANCE = math.log(1.02)
METRICS = {
    "M1": "annualised buybacks or captured revenue (USD per year)",
    "M2": "capture rate (buybacks / gross fees)",
    "M3": "coverage of net issuance (required multiples inverted)",
    "M4": "30-day NEAR Intents volume (USD)",
    "M5": "net inflation rate (per year)",
}


def load_claims(path=CLAIMS) -> list[dict]:
    """Return the rows of data/claims.csv."""
    with open(path, encoding="ascii", newline="") as fh:
        return list(csv.DictReader(fh))


def window_sum(x: dict, end: dt.date, W: int) -> float:
    """Return the sum of x over the W days ending on end."""
    return math.fsum(coverage.window(x, end, W))


def replicate(claim: dict, snap: dict) -> float | None:
    """Return our value r under the claim's stated window, end date and definition, or None."""
    rule = claim["recompute"]
    if rule == "none":
        return None
    end = dt.date.fromisoformat(claim["window_end"])
    W = int(claim["window_days"])
    a = float(claim["annualise"]) if claim["annualise"] else 1.0
    b, f, v, rev, S, p = (snap[k] for k in ("b", "f", "v", "rev", "S", "p"))
    if rule == "sum_b":
        return window_sum(b, end, W) * a
    if rule == "sum_rev":
        return window_sum(rev, end, W) * a
    if rule == "sum_v":
        return window_sum(v, end, W) * a
    if rule == "kappa":
        return window_sum(b, end, W) / window_sum(f, end, W) * a
    if rule == "kappa_rev":
        return window_sum(rev, end, W) / window_sum(f, end, W) * a
    if rule == "rate":
        return coverage.rate(S, end) * a
    if rule == "coverage":
        return window_sum(b, end, W) * a / (coverage.issuance(S, end) * p[end])
    if rule == "multiple_param":
        return float(claim["param"]) * S[end] * p[end] / (window_sum(b, end, W) * a)
    raise ValueError(f"unknown recompute rule {rule}")


def canonical(x: float, claim: dict) -> float:
    """Return x in the metric's common unit (scale, and inversion of multiples)."""
    x = 1.0 / x if claim["invert"] == "1" else x
    return x * float(claim["scale"])


def primary_values(snap: dict) -> dict:
    """Return r0 per metric: our primary definitions at t0, in the common units."""
    b, f, v, S, p, t0 = (snap[k] for k in ("b", "f", "v", "S", "p", "t0"))
    return {
        "M1": coverage.annualised(b, t0, 90),
        "M2": coverage.capture(b, f, t0, 90),
        "M3": coverage.coverage(b, S, p, t0, 90),
        "M4": window_sum(v, t0, 30),
        "M5": coverage.rate(S, t0),
    }


def decompose(y: float, r: float, r0: float) -> dict:
    """Return e = ln(y/r), s = ln(r/r0) and ln(y/r0) = s + e."""
    e, s = math.log(y / r), math.log(r / r0)
    return {"e": e, "s": s, "total": s + e, "reproduced": abs(e) <= TOLERANCE}


def dispersion(values: list[float]) -> dict:
    """Return the interquartile range of ln values with n; the IQR only if n >= 5."""
    n = len(values)
    if n < 5:
        return {"n": n, "iqr_ln": None, "q25_ln": None, "q75_ln": None}
    lv = np.log(np.array(values))
    q25, q75 = np.percentile(lv, [25, 75])
    return {"n": n, "iqr_ln": float(q75 - q25), "q25_ln": float(q25), "q75_ln": float(q75)}


HEADER = ["thesis", "repo_url", "commit", "file", "line", "metric", "value", "unit",
          "window_start", "window_end", "recompute", "r", "y_common", "r_common", "r0",
          "e", "s", "ln_y_over_r0", "status", "note"]


def run(snap: dict, claims: list[dict]) -> tuple[list[list], dict]:
    """Return the audit rows and the summary (r0, counts, dispersion by metric)."""
    r0s = primary_values(snap)
    rows, by_metric = [], {}
    for c in claims:
        y = float(c["value"])
        yc = canonical(y, c)
        r = replicate(c, snap)
        r0 = r0s[c["metric"]]
        by_metric.setdefault(c["metric"], {})
        by_metric[c["metric"]].setdefault(c["thesis"], yc)
        if r is None:
            d, rc, status = None, None, "not recomputed"
        else:
            rc = canonical(r, c)
            d = decompose(yc, rc, r0)
            status = "reproduced" if d["reproduced"] else "not reproduced by us"
        rows.append([c["thesis"], c["repo_url"], c["commit"], c["file"], int(c["line"]),
                     c["metric"], c["value"], c["unit"], c["window_start"], c["window_end"],
                     c["recompute"], r, yc, rc, r0,
                     d["e"] if d else None, d["s"] if d else None,
                     d["total"] if d else math.log(yc / r0), status, c["note"]])
    summary = {
        "t0": snap["t0"].isoformat(), "tolerance_ln": TOLERANCE, "metrics": METRICS, "r0": r0s,
        "theses": len({c["thesis"] for c in claims}), "claims": len(claims),
        "status_counts": {s: sum(1 for r in rows if r[18] == s)
                          for s in ("reproduced", "not reproduced by us", "not recomputed")},
        "dispersion": {m: dispersion(list(v.values())) for m, v in sorted(by_metric.items())},
    }
    return rows, summary


def load_snapshot() -> dict:
    """Return the NEAR snapshot with the DefiLlama revenue series added."""
    snap = coverage.load()
    snap["rev"] = dict(series.llama_daily("intents_revenue"))
    return snap


def main() -> None:
    """Write results/audit.csv and results/audit.json."""
    rows, summary = run(load_snapshot(), load_claims())
    out.write_text(out.RESULTS / "audit.csv", out.csv_text(HEADER, rows))
    out.write_text(out.RESULTS / "audit.json", out.json_text(summary))
    print(f"{summary['theses']} theses, {summary['claims']} claims: {summary['status_counts']}")
    for m, d in summary["dispersion"].items():
        print(m, d)


if __name__ == "__main__":
    main()
