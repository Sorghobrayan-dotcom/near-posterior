"""Class multiverse (PREREG_2 S7) and origin-year cohorts (S8).

Secondary (specified after the primary results).
"""

import math

import numpy as np

from near_posterior import forecast, refclass

H = 24
SCALES = (2.0, 3.0, 5.0)
AGES = ((270.0, 1095.0), (180.0, 730.0), (365.0, 1460.0), (270.0, math.inf))
WEIGHTINGS = ("entity", "moment")
YIELD = frozenset({
    "Liquid Staking", "Staking Pool", "Liquid Restaking", "Restaking", "Stablecoin Issuer", "RWA",
    "Lending", "CDP", "Yield", "Yield Aggregator", "Basis Trading", "Risk Curators",
    "Onchain Capital Allocator", "Uncollateralized Lending", "NFT Lending", "Restaked BTC",
    "Anchor BTC", "Decentralized BTC", "Leveraged Farming", "Farm",
})
CATEGORIES = ("all", "trading", "all except yield-type")
HEADER = ["scale_q", "age_lo", "age_hi", "weighting", "categories", "P", "P_lo", "P_hi",
          "entities", "moments", "flag_below_30_entities"]


def category_mask(panel: dict, mom: dict, which: str) -> np.ndarray:
    """Return the mask of moments whose entity category belongs to the category set."""
    if which == "all":
        return np.ones(mom["e"].size, dtype=bool)
    cats = panel["category"]
    if which == "trading":
        keep = np.array([c in refclass.TRADING for c in cats])
    else:
        keep = np.array([c not in YIELD for c in cats])
    return keep[mom["e"]]


def moment_share_values(Y: np.ndarray, e: np.ndarray, k: float) -> tuple[float, np.ndarray]:
    """Return the plain share of moments with Y >= ln k and its entity-resampled values."""
    ents, inv = np.unique(e, return_inverse=True)
    hits = np.bincount(inv, weights=(Y >= math.log(k)).astype(float), minlength=ents.size)
    n = np.bincount(inv, minlength=ents.size).astype(float)
    rng = np.random.default_rng(forecast.SEED)
    idx = rng.integers(0, ents.size, size=(forecast.RESAMPLES, ents.size))
    return float(hits.sum() / n.sum()), hits[idx].sum(axis=1) / n[idx].sum(axis=1)


def moment_share(Y: np.ndarray, e: np.ndarray, k: float) -> dict:
    """Return the plain share of moments with Y >= ln k and its cluster bootstrap interval."""
    P, shares = moment_share_values(Y, e, k)
    ents = np.unique(e)
    return {"P": P,
            "interval": (float(np.percentile(shares, 5)), float(np.percentile(shares, 95))),
            "entities": int(ents.size), "moments": int(Y.size)}


def specifications(panel: dict, mom: dict, F_near: float):
    """Yield (scale q, age band, categories, weighting, Y, entity) for the 72 specifications."""
    ok = refclass.resolved(mom)
    for q in SCALES:
        for lo, hi in AGES:
            for cats in CATEGORIES:
                mask = (ok & (mom["F"] >= F_near / q) & (mom["F"] <= F_near * q)
                        & (mom["age"] >= lo) & (mom["age"] <= hi)
                        & category_mask(panel, mom, cats))
                for wt in WEIGHTINGS:
                    yield q, (lo, hi), cats, wt, mom["Y"][mask], mom["e"][mask]


def run(panel: dict, mom: dict, F_near: float, k: float) -> list[list]:
    """Return the 72 specifications of S7 at h = 24 and the primary k*."""
    ok = refclass.resolved(mom)
    rows = []
    for q in SCALES:
        for lo, hi in AGES:
            for cats in CATEGORIES:
                mask = (ok & (mom["F"] >= F_near / q) & (mom["F"] <= F_near * q)
                        & (mom["age"] >= lo) & (mom["age"] <= hi)
                        & category_mask(panel, mom, cats))
                Y, e = mom["Y"][mask], mom["e"][mask]
                for wt in WEIGHTINGS:
                    res = forecast.b0(Y, e, k) if wt == "entity" else moment_share(Y, e, k)
                    rows.append([q, lo, "infinity" if math.isinf(hi) else hi, wt, cats,
                                 res["P"], res["interval"][0], res["interval"][1],
                                 res["entities"], res["moments"], int(res["entities"] < 30)])
    return rows


def summary(rows: list[list]) -> dict:
    """Return median, minimum and maximum of P over the specifications, and the flag count."""
    P = np.array([r[5] for r in rows])
    return {"specifications": len(rows), "median": float(np.median(P)), "min": float(P.min()),
            "max": float(P.max()), "below_30_entities": int(sum(r[10] for r in rows))}


def cohorts(Y: np.ndarray, e: np.ndarray, years: np.ndarray, k: float) -> dict:
    """Return leave-one-origin-year-out P_B0 and the two-stage (year, block) bootstrap."""
    loo = {}
    for y in sorted(set(years.tolist())):
        keep = years != y
        loo[str(y)] = ({"P": forecast.class_frequency(Y[keep], e[keep], k),
                        "entities": int(np.unique(e[keep]).size), "moments": int(keep.sum())}
                       if keep.any() else None)
    blocks = sorted({(int(a), int(b)) for a, b in zip(e, years)})
    share = np.array([float(np.mean(Y[(e == a) & (years == b)] >= math.log(k)))
                      for a, b in blocks])
    block_year = np.array([b for _, b in blocks])
    uniq = np.array(sorted(set(years.tolist())))
    rng = np.random.default_rng(forecast.SEED)
    means = []
    for _ in range(forecast.RESAMPLES):
        drawn = rng.choice(uniq, size=uniq.size, replace=True)
        pool = np.concatenate([np.flatnonzero(block_year == y) for y in drawn])
        pick = rng.choice(pool, size=pool.size, replace=True)
        means.append(share[pick].mean())
    return {"leave_one_year_out": loo, "blocks": len(blocks), "years": [int(y) for y in uniq],
            "two_stage_bootstrap": {"mean_block_share": float(share.mean()),
                                    "interval": [float(np.percentile(means, 5)),
                                                 float(np.percentile(means, 95))],
                                    "note": "indicative only (few cohorts)"}}
