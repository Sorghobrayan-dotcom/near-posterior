"""Resolution of the registered forecasts (PREREG_2 S11).

Run: `python -m near_posterior.resolve`. Prints, for h = 12, 24, 36, the registered forecast,
its resolution date, and the outcome and Brier contribution once the snapshot reaches that date.
The registered forecasts are computed from the registered snapshot
(`tests/fixtures/near_20261112`) and the frozen panel, never from a later snapshot.
"""

import datetime as dt
import json

from near_posterior import coverage, exceedance, forecast, out, refclass, series, thesis

FIXTURE = out.ROOT / "tests" / "fixtures" / "near_20261112"
HORIZONS = (12, 24, 36)


def registered(panel: dict) -> dict:
    """Return the registered forecasts P_B0(k*) of class R, primary scenario, registered snapshot."""
    snap = coverage.load(FIXTURE)
    cov = coverage.summary(snap)
    rows = coverage.scenario_grid(snap)
    ov = refclass.origin_values(panel)
    res = {"t0": cov["t0"], "snapshot_fetched_at": cov["fetched_at"], "class": "R",
           "scenario": "primary (W = 90, capture, price and issuance rate constant)",
           "rule": "outcome = 1 if C_90 at t0 + h months >= 1, else 0; Brier = (P - outcome)^2",
           "forecasts": {}}
    for h in HORIZONS:
        k = next(r["k_star"] for r in rows if r["window"] == "90" and r["h"] == h
                 and r["capture"] == "constant" and r["issuance"] == "constant"
                 and r["G_P"] == 1.0)
        s = exceedance.class_sample(panel, refclass.moments(panel, h, ov), cov["F_near"])
        b0 = forecast.b0(s["Y"], s["e"], k)
        due = series.add_months(dt.date.fromisoformat(cov["t0"]), h)
        res["forecasts"][str(h)] = {"k_star": k, "P": b0["P"], "interval": list(b0["interval"]),
                                    "entities": b0["entities"], "resolution_date": due.isoformat()}
    return res


def resolve(reg: dict, snap: dict) -> dict:
    """Return, per horizon, pending or the outcome and Brier contribution on this snapshot."""
    res = {"snapshot_t0": snap["t0"].isoformat(), "by_h": {}}
    for h, f in reg["forecasts"].items():
        due = dt.date.fromisoformat(f["resolution_date"])
        if snap["t0"] < due:
            res["by_h"][h] = {"status": "pending", "resolution_date": f["resolution_date"]}
            continue
        C = coverage.coverage(snap["b"], snap["S"], snap["p"], due, 90)
        outcome = 1 if C >= 1 else 0
        res["by_h"][h] = {"status": "resolved", "resolution_date": f["resolution_date"],
                          "C_90": C, "outcome": outcome, "brier": (f["P"] - outcome) ** 2}
    return res


def markdown(reg: dict, res: dict) -> str:
    """Return the text of RESOLUTION.md (dates, rule, command, status)."""
    L = ["# Resolution of the registered forecasts", "",
         f"Rule (`PREREG_2.md` S11): {reg['rule']}. The forecasts were computed once from the "
         f"registered snapshot (t0 = {reg['t0']}, fetched {reg['snapshot_fetched_at']}) and the "
         f"frozen reference panel; they are never recomputed from a later snapshot "
         f"(`results/registered_forecast.json`).", "",
         "Command: `uv run python -m near_posterior.resolve` (offline, on the current "
         "`data/raw/` snapshot; the daily refresh keeps that snapshot current).", "",
         "| Horizon | Resolution date | k* | Registered P (90% interval) | Status on the current "
         "snapshot |", "|---|---|---|---|---|"]
    for h, f in reg["forecasts"].items():
        r = res["by_h"][h]
        status = (f"pending (snapshot t0 = {res['snapshot_t0']})" if r["status"] == "pending"
                  else f"resolved: C_90 = {r['C_90']:.3f}, outcome {r['outcome']}, "
                       f"Brier {r['brier']:.4f}")
        L.append(f"| {h} months | {f['resolution_date']} | {f['k_star']:.3f} | "
                 f"{thesis.f(f['P'])} ({thesis.interval(f['interval'])}) | {status} |")
    return "\n".join(L) + "\n"


def main() -> None:
    """Print the status of every registered forecast on the current snapshot."""
    reg = json.loads((out.RESULTS / "registered_forecast.json").read_text(encoding="ascii"))
    res = resolve(reg, coverage.load())
    for h, r in res["by_h"].items():
        f = reg["forecasts"][h]
        tail = ("pending" if r["status"] == "pending"
                else f"outcome {r['outcome']} (C_90 = {r['C_90']:.3f}), Brier {r['brier']:.4f}")
        print(f"h = {h}: P = {f['P']:.3f}, resolves on {f['resolution_date']}: {tail}")


if __name__ == "__main__":
    main()
