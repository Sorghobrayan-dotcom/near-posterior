"""Ask the base rate for any required fee multiple and horizon.

Run: `python -m near_posterior.ask [--k K] [--h 12|24|36]`. With no `--k`, k is the primary k*
of the horizon; at h = 24 that prints the registered headline. Offline.
"""

import argparse
import csv
import json
import math

import numpy as np

from near_posterior import coverage, exceedance, forecast, out, refclass, thesis


def answer(panel: dict, mom: dict, F_near: float, k: float) -> dict:
    """Return P_B0(k) of class R with its interval and the entities that reached k."""
    s = exceedance.class_sample(panel, mom, F_near)
    res = forecast.b0(s["Y"], s["e"], k)
    lk = math.log(k)
    reached = []
    for e in np.unique(s["e"][s["Y"] >= lk]):
        sel = s["e"] == e
        hits = sel & (s["Y"] >= lk)
        reached.append({"entity": panel["ids"][e], "name": panel["name"][e],
                        "category": panel["category"][e], "successes": int(hits.sum()),
                        "moments": int(sel.sum()),
                        "first_origin":
                            refclass.month_start(int(s["month"][hits].min())).isoformat()})
    return dict(res, k=k, reached=reached)


def primary_k(h: int) -> float:
    """Return the primary k* of horizon h from the committed results/speccurve.csv."""
    with open(out.RESULTS / "speccurve.csv", encoding="ascii", newline="") as fh:
        for r in csv.DictReader(fh):
            if (r["cls"] == "R" and r["window"] == "90" and int(r["h"]) == h
                    and r["capture"] == "constant" and r["issuance"] == "constant"
                    and float(r["G_P"]) == 1.0):
                return float(r["k_star"])
    raise ValueError(f"no primary row for h = {h}")


def main(argv=None) -> None:
    """Print the base rate, its interval, the entities and those that reached k."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--k", type=float, default=None, help="required fee multiple (default k*)")
    ap.add_argument("--h", type=int, default=24, choices=(12, 24, 36), help="horizon in months")
    args = ap.parse_args(argv)
    k = args.k if args.k is not None else primary_k(args.h)
    cov = coverage.summary(coverage.load())
    panel = refclass.load_panel()
    mom = refclass.moments(panel, args.h)
    a = answer(panel, mom, cov["F_near"], k)
    print(f"Class R, h = {args.h} months, k = {k:.3f}"
          + (" (primary k*)" if args.k is None else "") + ":")
    lo, hi = a["interval"]
    print(f"P({args.h}-month fee growth >= k) = {a['P']:.3f} (90% interval {lo:.3f} to "
          f"{hi:.3f}), {a['entities']} entities, {a['moments']} moments")
    print(f"Entities that reached it: {len(a['reached'])}")
    for r in a["reached"]:
        print(f"  {r['name']} ({r['category']}): {r['successes']} of {r['moments']} moments, "
              f"first from {r['first_origin']}")
    if args.k is None and args.h == 24:
        head = json.loads((out.RESULTS / "headline.json").read_text(encoding="ascii"))
        print("Registered headline: " + thesis.headline_line({"headline": head}))


if __name__ == "__main__":
    main()
