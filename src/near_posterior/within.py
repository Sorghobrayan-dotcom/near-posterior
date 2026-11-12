"""Coverage reached at any point within the horizon (PREREG_2 S4).

Secondary (specified after the primary results).
"""

import math

import numpy as np

from near_posterior import forecast, refclass

HORIZONS = (12, 24, 36)


def first_crossing(ov: dict, e: int, k: int, h: int, C: float, r: float, g_p: float = 1.0,
                   g_kappa: float = 1.0) -> int | None:
    """Return the first month u in 1..h with a valid window and
    F(t + u) / F(t) >= (1 + r)^(u/12) * G_P / G_kappa / C, or None."""
    F0 = ov["F"][e, k]
    for u in range(1, h + 1):
        ku = k + u
        if ku >= ov["valid"].shape[1] or not ov["valid"][e, ku]:
            continue
        if ov["F"][e, ku] / F0 >= (1.0 + r) ** (u / 12) * g_p / g_kappa / C:
            return u
    return None


def compute(panel: dict, cov: dict, moms: dict, ov: dict, primary: dict) -> dict:
    """Return P_within(h) with its interval next to the registered 'at month h' value."""
    C = next(w for w in cov["windows"] if w["window"] == "90")["C"]
    res = {"class": "R", "scenario": "primary (W = 90, G_P = 1, G_kappa = 1)", "C_90_t0": C,
           "r": cov["r"], "by_h": {}}
    for h in HORIZONS:
        mom = moms[h]
        mask = refclass.in_class(mom, "R", cov["F_near"], panel) & refclass.resolved(mom)
        idx = np.flatnonzero(mask)
        hit = np.array([first_crossing(ov, int(mom["e"][i]), int(mom["k"][i]), h, C, cov["r"])
                        is not None for i in idx], dtype=float)
        ents, p = forecast.entity_shares(hit, mom["e"][idx], math.e)
        at = primary[h]
        res["by_h"][str(h)] = {
            "P_within": float(p.mean()), "interval_within": list(forecast.cluster_bootstrap(p)),
            "P_at_month_h": at["P"], "interval_at_month_h": [at["P_lo"], at["P_hi"]],
            "k_star": at["k_star"], "entities": int(ents.size), "moments": int(idx.size),
            "moments_crossing": int(hit.sum()),
        }
    return res
