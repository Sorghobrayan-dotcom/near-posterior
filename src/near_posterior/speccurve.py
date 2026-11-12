"""Specification curve (PREREG 7), headline probability and verdict (PREREG 6 and 8)."""

import math

import numpy as np

from near_posterior import backtest, coverage, forecast, refclass

PRIMARY = {"window": "90", "h": 24, "capture": "constant", "issuance": "constant", "G_P": 1.0}
HEADLINE_H = 24


def grid(snap: dict) -> list[dict]:
    """Return the 864 rows of PREREG 7: every class crossed with the 216 coverage scenarios."""
    return [dict(row, cls=cls) for cls in refclass.CLASSES for row in coverage.scenario_grid(snap)]


def class_sample(mom: dict, cls: str, F_near: float, panel: dict) -> tuple[np.ndarray, np.ndarray]:
    """Return (Y, entity) of the resolved moments of class cls."""
    mask = refclass.in_class(mom, cls, F_near, panel) & refclass.resolved(mom)
    return mom["Y"][mask], mom["e"][mask]


def is_primary(row: dict) -> bool:
    """Return True for the primary scenario row (any class)."""
    return all(row[k] == v for k, v in PRIMARY.items())


def run(panel: dict, snap: dict, F_near: float, moms: dict) -> list[dict]:
    """Return the 864 rows with P_B0(k*) and its bootstrap interval, computed with model B0."""
    samples = {(cls, h): class_sample(moms[h], cls, F_near, panel)
               for cls in refclass.CLASSES for h in coverage.HORIZONS}
    rows = []
    for row in grid(snap):
        Y, ent = samples[(row["cls"], row["h"])]
        res = forecast.b0(Y, ent, row["k_star"]) if Y.size else None
        rows.append(dict(row, P=res["P"] if res else None,
                         P_lo=res["interval"][0] if res else None,
                         P_hi=res["interval"][1] if res else None,
                         entities=res["entities"] if res else 0,
                         moments=res["moments"] if res else 0))
    return rows


def summarise(rows: list[dict], primary_class: str) -> dict:
    """Return median, min, max of P over the 864 rows, and the primary row."""
    P = np.array([r["P"] for r in rows if r["P"] is not None])
    primary = next(r for r in rows if r["cls"] == primary_class and is_primary(r))
    return {"rows": len(rows), "with_value": int(P.size), "median": float(np.median(P)),
            "min": float(P.min()), "max": float(P.max()), "primary": primary}


def verdict(P: float) -> str:
    """Return the verdict words of PREREG 8 for probability P."""
    if P < 0.10:
        return "buybacks are unlikely to cover issuance within 24 months"
    if P <= 0.50:
        return "conditional"
    return "supported"


def share_above(Y: np.ndarray, w: np.ndarray, k: float) -> float:
    """Return the forecast P(Y >= ln k) of a weighted sample."""
    return float(np.sum(w[Y >= math.log(k)]))


def break_even(Y: np.ndarray, w: np.ndarray) -> float:
    """Return k50: the forecast P(Y >= ln k) exceeds 0.50 exactly when k <= k50."""
    order = np.argsort(-Y, kind="stable")
    y, c = Y[order], np.cumsum(w[order])
    last = np.r_[y[1:] != y[:-1], True]
    above = c[last] > 0.5 + 1e-12
    return float(math.exp(y[last][np.argmax(above)]))


def what_would_change(Y: np.ndarray, w: np.ndarray, primary: dict, kappa: float,
                      curve: list[dict], cls: str) -> dict:
    """Return the capture, issuance and price factors that each move P across 0.50 alone.

    P is the headline model's forecast from its weighted sample (Y, w).
    """
    k = primary["k_star"]
    k50 = break_even(Y, w)
    P0 = share_above(Y, w, k)
    ratio = k50 / k
    singles = []
    for r in curve:
        if r["cls"] != cls or r["window"] != "90" or r["h"] != HEADLINE_H:
            continue
        diff = [key for key in ("capture", "issuance", "G_P") if r[key] != primary[key]]
        if len(diff) == 1:
            P = share_above(Y, w, r["k_star"])
            singles.append({"factor": diff[0], "value": r[diff[0]], "G_kappa": r["G_kappa"],
                            "G_I": r["G_I"], "G_P": r["G_P"], "k_star": r["k_star"], "P": P,
                            "crosses": (P > 0.5) != (P0 > 0.5)})
    return {
        "k50": k50, "k_star": k, "P": P0,
        "G_kappa_needed": 1.0 / ratio, "kappa_needed": kappa / ratio,
        "G_I_needed": primary["G_I"] * ratio, "G_I_cut_needed": 1.0 - ratio,
        "G_P_needed": ratio, "single_factor_grid_rows": singles,
        "any_grid_row_crosses": any(s["crosses"] for s in singles),
    }


def headline(panel: dict, cov: dict, choice: dict, moms: dict, counts: dict,
             curve: list[dict]) -> dict:
    """Return the headline probability, interval, model, verdict and what would change it."""
    stop = counts["classes"]["R"]["24"]["entities"] < 30
    cls = "R_all_ages" if stop else "R"
    F_near = cov["F_near"]
    w90 = next(w for w in cov["windows"] if w["window"] == "90")
    primary = next(r for r in curve if r["cls"] == cls and is_primary(r))
    k_star = primary["k_star"]
    mom = moms[HEADLINE_H]
    Y, ent = class_sample(mom, cls, F_near, panel)
    mask = refclass.in_class(mom, cls, F_near, panel) & refclass.resolved(mom)
    years = np.array([refclass.month_start(int(m)).year for m in mom["month"][mask]])
    b0 = forecast.b0(Y, ent, k_star, years)
    _, inv = np.unique(ent, return_inverse=True)
    b0_w = 1.0 / np.bincount(inv)[inv] / np.unique(ent).size
    ok = refclass.resolved(mom) & backtest.analog_mask(mom)
    idx = np.flatnonzero(ok)
    x0 = np.array([math.log(F_near), cov["momentum"], math.log(cov["age_t0"])])
    X = backtest.covariates(mom, idx)
    analog = {}
    for K in backtest.KS:
        pick = idx[forecast.analogs(x0, X, mom["e"][idx], K, mom["month"][idx])]
        analog[f"A_{K}"] = dict(forecast.analog_forecast(mom["Y"][pick], k_star), pick=pick)
    model = choice["model"]
    if model == "B0":
        P, interval, n_ent = b0["P"], b0["interval"], b0["entities"]
        sample = (Y, b0_w)
        interval_kind = "cluster bootstrap over entities, 90 percent"
    else:
        a = analog[model]
        P, interval, n_ent = a["P"], a["interval"], a["n"]
        Ya = mom["Y"][a["pick"]]
        sample = (Ya, np.full(Ya.size, 1.0 / Ya.size))
        interval_kind = "exact Clopper-Pearson, 90 percent"
    pick30 = analog["A_30"]["pick"]
    table = [{"entity": panel["ids"][mom["e"][i]], "name": panel["name"][mom["e"][i]],
              "category": panel["category"][mom["e"][i]],
              "origin": refclass.month_start(int(mom["month"][i])).isoformat(),
              "F": float(mom["F"][i]), "m": float(mom["m"][i]), "age": int(mom["age"][i]),
              "Y": float(mom["Y"][i])} for i in pick30]
    for a in analog.values():
        del a["pick"]
    return {
        "t0": cov["t0"], "fetched_at": cov["fetched_at"], "class": cls,
        "stop_rule_R_below_30": stop, "model": model, "choice": choice, "h": HEADLINE_H,
        "k_star": k_star, "C_90": w90["C"], "kappa_90": w90["kappa"], "P": P,
        "interval": list(interval), "interval_kind": interval_kind, "entities": n_ent,
        "verdict": verdict(P), "B0": b0, "analogs": analog, "analog_table": table,
        "what_would_change": what_would_change(*sample, primary, w90["kappa"], curve, cls),
        "class_Y": sorted(float(y) for y in Y),
    }
