"""Ask the base rate for any required fee multiple and horizon.

Run: `python -m near_posterior.ask [--k K] [--h 12|24|36] [--slug ENTITY_ID]`. With no `--k`,
k is the primary k* of the horizon; at h = 24 that prints the registered headline. With
`--slug`, the class is centred on that entity's latest valid moment (PREREG_2 S1). Offline.
"""

import argparse
import csv
import datetime as dt
import json
import math

import numpy as np

from near_posterior import coverage, exceedance, forecast, out, refclass, thesis, validation


def answer(panel: dict, mom: dict, F_near: float, k: float) -> dict:
    """Return P_B0(k) of class R with its interval and the entities that reached k."""
    return answer_sample(panel, exceedance.class_sample(panel, mom, F_near), k)


def answer_sample(panel: dict, s: dict, k: float) -> dict:
    """Return P_B0(k) of a class sample with its interval and the entities that reached k."""
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


def centred_sample(panel: dict, mom: dict, ov: dict, entity: str, h: int) -> tuple[dict, dict]:
    """Return the S1 class sample centred on the entity's latest valid moment, and that moment."""
    e = panel["ids"].index(entity)
    k = int(np.flatnonzero(ov["valid"][e])[-1])
    month = ov["months"][k]
    t = refclass.month_start(month)
    first = panel["base"] + dt.timedelta(days=int(panel["first_pos"][e]))
    target = {"entity": entity, "origin": t.isoformat(), "F": float(ov["F"][e, k]),
              "age": (t - first).days}
    cls = validation.class_mask(mom, refclass.resolved(mom), e, month, target["F"],
                                float(target["age"]), h)
    return {"Y": mom["Y"][cls], "e": mom["e"][cls], "month": mom["month"][cls]}, target


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
    ap.add_argument("--slug", default=None, help="entity_id of the frozen panel (S1 class)")
    args = ap.parse_args(argv)
    k = args.k if args.k is not None else primary_k(args.h)
    cov = coverage.summary(coverage.load())
    panel = refclass.load_panel()
    ov = refclass.origin_values(panel)
    mom = refclass.moments(panel, args.h, ov)
    if args.slug:
        entity = next((x for x in (args.slug, f"parent#{args.slug}") if x in panel["ids"]), None)
        if entity is None:
            ap.error(f"{args.slug} is not an entity_id of data/refclass/entities.csv")
        sample, target = centred_sample(panel, mom, ov, entity, args.h)
        a = answer_sample(panel, sample, k)
        print(f"Class centred on {target['entity']} at {target['origin']} (F = "
              f"{target['F']:,.0f} USD per year, age {target['age']} days), h = {args.h} "
              f"months, k = {k:.3f}:")
        if a["entities"] < validation.MIN_CLASS_ENTITIES:
            print(f"(class below {validation.MIN_CLASS_ENTITIES} entities: S1 would not score it)")
    else:
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
    if args.k is None and args.h == 24 and not args.slug:
        head = json.loads((out.RESULTS / "headline.json").read_text(encoding="ascii"))
        print("Registered headline: " + thesis.headline_line({"headline": head}))


if __name__ == "__main__":
    main()
