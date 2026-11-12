"""Exceedance curve, growth and coverage quantiles, entities of class R (PREREG_2 S3, S5).

Secondary (specified after the primary results).
"""

import math

import numpy as np

from near_posterior import forecast, refclass

K_GRID = [10 ** (-2 + i / 20) for i in range(81)]
QUANTILES = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)


def class_sample(panel: dict, mom: dict, F_near: float, cls: str = "R") -> dict:
    """Return the resolved class moments: Y, entity index, origin month and status."""
    mask = refclass.in_class(mom, cls, F_near, panel) & refclass.resolved(mom)
    return {"Y": mom["Y"][mask], "e": mom["e"][mask], "month": mom["month"][mask],
            "status": mom["status"][mask]}


def entity_weights(e: np.ndarray) -> np.ndarray:
    """Return moment weights 1 / n_j, normalised to sum to 1."""
    _, inv, n = np.unique(e, return_inverse=True, return_counts=True)
    w = 1.0 / n[inv]
    return w / w.sum()


def weighted_quantiles(x: np.ndarray, w: np.ndarray, qs=QUANTILES) -> dict:
    """Return the lower weighted quantiles: the smallest x whose cumulative weight reaches q."""
    order = np.argsort(x, kind="stable")
    xs, c = x[order], np.cumsum(w[order])
    return {f"{q:g}": float(xs[min(int(np.searchsorted(c, q - 1e-12)), xs.size - 1)])
            for q in qs}


def curve(sample: dict, h: int) -> list[list]:
    """Return the rows (h, k, P, P_lo, P_hi) of P_B0(k, h) on the fixed grid of k."""
    rows = []
    for k in K_GRID:
        res = forecast.b0(sample["Y"], sample["e"], k)
        rows.append([h, k, res["P"], res["interval"][0], res["interval"][1]])
    return rows


def growth_quantiles(sample: dict) -> dict:
    """Return entity-weighted quantiles of exp(Y) and the entity-weighted share ending at zero."""
    w = entity_weights(sample["e"])
    floor = sample["status"] == "floor"
    return {"quantiles_exp_Y": weighted_quantiles(np.exp(sample["Y"]), w),
            "share_floor_entity_weighted": float(np.sum(w[floor])),
            "moments_floor": int(floor.sum()), "moments": int(sample["Y"].size),
            "entities": int(np.unique(sample["e"]).size)}


def coverage_quantiles(sample: dict, C0: float, r: float, h: int) -> dict:
    """Return entity-weighted quantiles of C(h) = C_90(t0) exp(Y) / (1 + r)^(h/12) (S5)."""
    C = C0 * np.exp(sample["Y"]) / (1.0 + r) ** (h / 12)
    return weighted_quantiles(C, entity_weights(sample["e"]))


def entity_rows(panel: dict, sample: dict, k_star: float, h: int) -> list[list]:
    """Return per entity: category, moments, successes at k*, largest growth and its origin."""
    rows = []
    lk = math.log(k_star)
    for e in np.unique(sample["e"]):
        sel = sample["e"] == e
        Y = sample["Y"][sel]
        best = int(np.argmax(Y))
        rows.append([h, panel["ids"][e], panel["name"][e], panel["category"][e], int(sel.sum()),
                     int((Y >= lk).sum()), float(math.exp(Y[best])),
                     refclass.month_start(int(sample["month"][sel][best])).isoformat()])
    return rows


ENTITY_HEADER = ["h", "entity_id", "name", "category", "moments", "successes_at_k_star",
                 "largest_growth", "largest_growth_origin"]


def compute(panel: dict, cov: dict, moms: dict, curve_rows: list[dict], cls: str = "R") -> dict:
    """Return the S3 and S5 results: exceedance rows, growth and coverage quantiles, entities."""
    C0 = next(w for w in cov["windows"] if w["window"] == "90")["C"]
    exc, ent, growth, covq, kstar = [], [], {}, {}, {}
    for h in (12, 24, 36):
        sample = class_sample(panel, moms[h], cov["F_near"], cls)
        k = next(r["k_star"] for r in curve_rows if r["cls"] == cls and r["h"] == h
                 and r["window"] == "90" and r["capture"] == "constant"
                 and r["issuance"] == "constant" and r["G_P"] == 1.0)
        kstar[str(h)] = k
        exc += curve(sample, h)
        ent += entity_rows(panel, sample, k, h)
        growth[str(h)] = growth_quantiles(sample)
        covq[str(h)] = coverage_quantiles(sample, C0, cov["r"], h)
    return {"exceedance": exc, "entities": ent,
            "growth": {"class": cls, "k_star": kstar, "by_h": growth},
            "coverage": {"class": cls, "C_90_t0": C0, "r": cov["r"], "by_h": covq}}
