"""Short live forecast that resolves during judging (PREREG_4.md).

Specified after the primary results; it tests the machinery (commit, resolve, attest), not the
24-month thesis. `python -m near_posterior.live --register` freezes the forecast once into
`data/live/forecast.json` (refused once `data/onchain/commitments.json` has a `live` key);
`build` only reads that file and adds the current reading of the outcome.
"""

import datetime as dt
import json
import math
import sys

from near_posterior import coverage, out

FROZEN = out.ROOT / "data" / "live" / "forecast.json"
COMMITS = out.ROOT / "data" / "onchain" / "commitments.json"
EVENT_DAY = "2026-11-15"
DUE = "2026-11-17T00:00:00Z"
WINDOW = 90
LABEL = ("specified after the primary results (PREREG_4.md); it tests the machinery, not the "
         "24-month thesis")
RULE = ("outcome = 1 if C_90(e) >= C_90(a), both from daily[] of the first daily snapshot "
        "fetched on or after the due time, else 0; Brier = (P - outcome)^2")


def probability(series: list[list], start: str, anchor: str, event: str) -> dict:
    """Return k, the pairs (d, d + k) used, and the share with C_90(d + k) >= C_90(d), for d on
    or after start + 89 days and d + k on or before the anchor."""
    C = {dt.date.fromisoformat(d): c for d, c in series}
    a, e = dt.date.fromisoformat(anchor), dt.date.fromisoformat(event)
    k = (e - a).days
    first = dt.date.fromisoformat(start) + dt.timedelta(days=WINDOW - 1)
    pairs = [d for d in sorted(C) if d >= first and d + dt.timedelta(days=k) <= a
             and d + dt.timedelta(days=k) in C]
    hits = sum(C[d + dt.timedelta(days=k)] >= C[d] for d in pairs)
    return {"k": k, "first_day": first.isoformat(), "n": len(pairs), "hits": hits,
            "P": hits / len(pairs) if pairs else None}


def freeze(cov: dict) -> dict:
    """Return the frozen forecast from a coverage summary: anchor at its last daily day."""
    series = out.tidy([[r["date"], r["C_90"]] for r in cov["daily"]])
    anchor = series[-1][0]
    p = probability(series, cov["buyback_start"], anchor, EVENT_DAY)
    if p["k"] < 1 or not p["n"]:
        raise ValueError(f"cannot freeze: anchor {anchor}, event {EVENT_DAY}, n = {p['n']}")
    return {"label": LABEL, "question": f"C_90({EVENT_DAY}) >= C_90({anchor})",
            "anchor_day": anchor, "anchor_C_90": series[-1][1], "event_day": EVENT_DAY,
            "buyback_start": cov["buyback_start"], "first_day": p["first_day"], "k": p["k"],
            "n": p["n"], "hits": p["hits"], "P": p["P"], "resolution_due": DUE, "rule": RULE,
            "snapshot_fetched_at": cov["fetched_at"], "series": series}


def frozen_check(frozen: dict) -> tuple[bool, str]:
    """Return the check that P, n and k recompute from the series frozen with the forecast."""
    p = probability(frozen["series"], frozen["buyback_start"], frozen["anchor_day"],
                    frozen["event_day"])
    ok = (p["k"] == frozen["k"] and p["n"] == frozen["n"] and p["hits"] == frozen["hits"]
          and math.isclose(p["P"], frozen["P"], rel_tol=1e-9) and frozen["series"][-1][0] == frozen["anchor_day"])
    return ok, "data/live/forecast.json: P, n and k recompute from the series frozen with it"


def checks() -> list[tuple[bool, str]]:
    """Return the offline check of the frozen live forecast, or nothing if there is none."""
    if not FROZEN.exists():
        return []
    return [frozen_check(json.loads(FROZEN.read_text(encoding="ascii")))]


def reading(frozen: dict, cov: dict) -> dict:
    """Return the frozen forecast (without its series) and the current reading of the outcome
    on this snapshot; the reading is not the on-chain resolution and may move with revisions."""
    res = {k: v for k, v in frozen.items() if k != "series"}
    C = {r["date"]: r["C_90"] for r in cov["daily"]}
    now = {"label": "current reading on the latest daily snapshot, not the on-chain resolution; "
                    "recent days may still be revised",
           "snapshot_fetched_at": cov["fetched_at"], "snapshot_t0": cov["t0"]}
    if frozen["event_day"] in C and frozen["anchor_day"] in C:
        outcome = int(C[frozen["event_day"]] >= C[frozen["anchor_day"]])
        now.update({"status": "readable", "C_90_event": C[frozen["event_day"]],
                    "C_90_anchor": C[frozen["anchor_day"]], "outcome": outcome,
                    "brier": (frozen["P"] - outcome) ** 2,
                    "fetched_after_due": cov["fetched_at"] >= DUE.replace("Z", "+00:00")})
    else:
        now["status"] = "pending"
    res["current_reading"] = now
    return res


def register() -> int:
    """Freeze the forecast from the current snapshot, unless it is already on chain."""
    if COMMITS.exists() and "live" in json.loads(COMMITS.read_text(encoding="utf-8")):
        print("live: data/onchain/commitments.json has a `live` key; the forecast is on chain "
              "and cannot be re-registered")
        return 1
    res = freeze(coverage.summary(coverage.load()))
    out.write_text(FROZEN, out.json_text(res))
    print(f"live: anchor {res['anchor_day']} (C_90 = {res['anchor_C_90']}), event "
          f"{res['event_day']}, k = {res['k']}, P = {res['P']} ({res['hits']} of {res['n']})")
    return 0


if __name__ == "__main__":
    sys.exit(register() if sys.argv[1:2] == ["--register"] else 0)
