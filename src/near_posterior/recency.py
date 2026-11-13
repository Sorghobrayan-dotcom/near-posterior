"""Recency-weighted class forecast (PREREG_3 T1).

Tertiary (specified after the secondary results). Weight of a class moment: (1 / n_j') *
0.5^(d / H), d = months from its origin to the target's origin, normalised to sum 1;
H = infinity is the class forecast C0 of PREREG_2 S1.
"""

import datetime as dt
import math

import numpy as np

from near_posterior import backtest, forecast, refclass, validation

TERTIARY = "tertiary (specified after the secondary results)"
HALF_LIVES = (12, 24, 48, None)
CHOICE_LAST_YEAR = 2024
METRICS = ("crps", "brier_1", "brier_2", "brier_5", "cov_50", "cov_90")


def label(H) -> str:
    """Return the text label of a half-life (None is infinity)."""
    return "inf" if H is None else str(H)


def weights(e: np.ndarray, months: np.ndarray, tau_month: int, H) -> np.ndarray:
    """Return normalised weights (1 / n_j) * 0.5^(d / H), d = tau_month - origin month."""
    _, inv, n = np.unique(e, return_inverse=True, return_counts=True)
    w = 1.0 / n[inv]
    if H is not None:
        w = w * 0.5 ** ((tau_month - months) / H)
    return w / w.sum()


def target_scores(z: np.ndarray, e: np.ndarray, months: np.ndarray, tau_month: int, Y: float,
                  H) -> dict:
    """Return the S1 scores of one target under the recency-weighted class sample."""
    return backtest.sample_scores(z, weights(e, months, tau_month, H), Y)


def score_horizon(panel: dict, ov: dict, mom: dict, h: int) -> list[dict]:
    """Return one row per scored S1 target with its scores under every half-life."""
    ok = refclass.resolved(mom)
    zf = np.maximum(mom["Y"], refclass.FLOOR)
    rows = []
    for i in np.flatnonzero(validation.target_mask(mom, ov)):
        tau = int(mom["month"][i])
        cls = validation.class_mask(mom, ok, int(mom["e"][i]), tau, float(mom["F"][i]),
                                    float(mom["age"][i]), h)
        if np.unique(mom["e"][cls]).size < validation.MIN_CLASS_ENTITIES:
            continue
        idx = np.flatnonzero(cls)
        Y = float(mom["Y"][i])
        row = {"entity": panel["ids"][int(mom["e"][i])], "year": refclass.month_start(tau).year,
               "Y": Y}
        for H in HALF_LIVES:
            row[label(H)] = target_scores(zf[idx], mom["e"][idx], mom["month"][idx], tau, Y, H)
        rows.append(row)
    return rows


def summary(rows: list[dict]) -> dict:
    """Return mean scores and reliability tables for every half-life over the rows."""
    res = {"targets": len(rows), "entities": len({r["entity"] for r in rows}), "by_H": {}}
    if not rows:
        return res
    for H in HALF_LIVES:
        lab = label(H)
        res["by_H"][lab] = {m: float(np.mean([r[lab][m] for r in rows])) for m in METRICS}
        res["by_H"][lab]["reliability"] = validation.reliability(rows, (lab,))[lab]
    return res


def choose(rows: list[dict]) -> dict:
    """Choose H* on origins up to 2024 and test it on origins 2025 (PREREG_3 T1)."""
    train = [r for r in rows if r["year"] <= CHOICE_LAST_YEAR]
    test = [r for r in rows if r["year"] > CHOICE_LAST_YEAR]
    means = {label(H): float(np.mean([r[label(H)]["crps"] for r in train])) for H in HALF_LIVES}
    order = [label(H) for H in reversed(HALF_LIVES)]
    best = min(order, key=lambda lab: (means[lab], order.index(lab)))
    res = {"choice_mean_crps": means, "best_on_choice_set": best, "H_star": "inf",
           "held_out_difference": None}
    if best == "inf":
        res["reason"] = ("H = infinity (C0) has the lowest mean CRPS on origins up to "
                         f"{CHOICE_LAST_YEAR}: recency weighting is not used")
        return res
    d = np.array([r[best]["crps"] - r["inf"]["crps"] for r in test])
    groups = np.array([r["entity"] for r in test])
    lo, hi = backtest.cluster_interval(d, groups)
    res["held_out_difference"] = {"mean": float(d.mean()), "interval": [lo, hi],
                                  "targets": len(test)}
    if hi < 0:
        res["H_star"] = best
        res["reason"] = (f"H = {best} has the lowest mean CRPS on origins up to "
                         f"{CHOICE_LAST_YEAR}, and on origins {CHOICE_LAST_YEAR + 1} the 90 "
                         f"percent interval of CRPS(C_{best}) - CRPS(C0) is below 0")
    else:
        res["reason"] = (f"H = {best} has the lowest mean CRPS on origins up to "
                         f"{CHOICE_LAST_YEAR}, but on origins {CHOICE_LAST_YEAR + 1} the 90 "
                         f"percent interval of CRPS(C_{best}) - CRPS(C0) is not below 0: "
                         f"recency weighting is not used")
    return res


def weighted_frequency(Y: np.ndarray, e: np.ndarray, months: np.ndarray, t0_month: int, H,
                       k: float) -> dict:
    """Return the recency-weighted P(Y >= ln k) of a class sample and its entity bootstrap."""
    _, inv, n = np.unique(e, return_inverse=True, return_counts=True)
    w = 1.0 / n[inv]
    if H is not None:
        w = w * 0.5 ** ((t0_month - months) / H)
    hit = (Y >= math.log(k)).astype(float)
    W = np.bincount(inv, weights=w)
    S = np.bincount(inv, weights=w * hit)
    rng = np.random.default_rng(forecast.SEED)
    idx = rng.integers(0, W.size, size=(forecast.RESAMPLES, W.size))
    boot = S[idx].sum(axis=1) / W[idx].sum(axis=1)
    return {"P": float(S.sum() / W.sum()),
            "interval": [float(np.percentile(boot, 5)), float(np.percentile(boot, 95))],
            "entities": int(W.size), "moments": int(Y.size)}


def compute(panel: dict, ov: dict, moms: dict, F_near: float, t0: str, k_star: dict) -> dict:
    """Return results/recency.json: scores by half-life, the choice of H*, P_recency for NEAR."""
    res = {"label": TERTIARY, "half_lives": [label(H) for H in HALF_LIVES], "by_h": {}}
    rows12 = score_horizon(panel, ov, moms[12], 12)
    rows24 = score_horizon(panel, ov, moms[24], 24)
    res["by_h"]["12"] = {
        "all": summary(rows12),
        "choice_set": summary([r for r in rows12 if r["year"] <= CHOICE_LAST_YEAR]),
        "held_out": summary([r for r in rows12 if r["year"] > CHOICE_LAST_YEAR]),
    }
    res["by_h"]["24"] = {"all": summary(rows24),
                         "note": "one origin year; all four half-lives reported, no choice"}
    res["choice"] = choose(rows12)
    H = None if res["choice"]["H_star"] == "inf" else int(res["choice"]["H_star"])
    t0_month = refclass.month_index(dt.date.fromisoformat(t0))
    res["near"] = {"H_star": res["choice"]["H_star"],
                   "d": "months from the moment's origin month to the month of t0",
                   "by_h": {}}
    for h in (12, 24, 36):
        mom = moms[h]
        mask = refclass.in_class(mom, "R", F_near, panel) & refclass.resolved(mom)
        r = weighted_frequency(mom["Y"][mask], mom["e"][mask], mom["month"][mask], t0_month,
                               H, k_star[str(h)])
        res["near"]["by_h"][str(h)] = dict(r, k_star=k_star[str(h)])
    return res
