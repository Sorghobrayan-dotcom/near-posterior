"""One interval for sampling and class definition (PREREG_3 T3), and a tail model as a
cross-check (PREREG_3 T4, optional).

Tertiary (specified after the secondary results).
"""

import math

import numpy as np

from near_posterior import exceedance, forecast, multiverse, recency, refclass

THRESHOLD_Q = 0.85
XI_RANGE = (-0.9, 2.0)


def pooled(values: list[np.ndarray]) -> dict:
    """Return the 5th, 50th and 95th percentiles of the pooled values and the share of the
    pooled variance that lies between groups (variance of group means over pooled variance)."""
    allv = np.concatenate(values)
    means = np.array([v.mean() for v in values])
    total = float(allv.var())
    return {"p5": float(np.percentile(allv, 5)), "p50": float(np.percentile(allv, 50)),
            "p95": float(np.percentile(allv, 95)), "values": int(allv.size),
            "groups": len(values), "between_share": float(means.var() / total) if total else 0.0}


def t3(panel: dict, mom: dict, F_near: float, k: float) -> dict:
    """Return T3: the pooled bootstrap values of the 72 class specifications at h = 24."""
    values = []
    for _, _, _, wt, Y, e in multiverse.specifications(panel, mom, F_near):
        if wt == "entity":
            values.append(forecast.bootstrap_means(forecast.entity_shares(Y, e, k)[1]))
        else:
            values.append(multiverse.moment_share_values(Y, e, k)[1])
    return dict(pooled(values), label=recency.TERTIARY, h=24, k_star=k,
                weighting="equal weight per specification; 2000 values each, same seed")


def gpd_loglik(xi, sigma, x: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Return the weighted GPD log-likelihood on a grid of (xi, sigma) (broadcast arrays)."""
    xi, sigma = np.asarray(xi)[..., None], np.asarray(sigma)[..., None]
    t = 1.0 + xi * x / sigma
    small = np.abs(xi) < 1e-9
    with np.errstate(divide="ignore", invalid="ignore"):
        logf = np.where(small, -np.log(sigma) - x / sigma,
                        -np.log(sigma) - (1.0 / np.where(small, 1.0, xi) + 1.0) * np.log(t))
        logf = np.where(t > 0, logf, -np.inf)
    return (w * logf).sum(axis=-1)


def gpd_fit(x: np.ndarray, w: np.ndarray, size: int = 41, rounds: int = 3):
    """Return (xi, sigma, converged) of the weighted GPD maximum likelihood fit, by a grid
    search refined `rounds` times inside fixed bounds; not converged if the final optimum lies
    on a bound of the parameter domain (within 0.01) or the likelihood is not finite."""
    if x.size < 5 or not np.all(np.isfinite(x)) or x.std() <= 0:
        return math.nan, math.nan, False
    s0 = float(np.average(x, weights=w))
    bounds = (XI_RANGE[0], XI_RANGE[1], math.log(s0 / 50), math.log(s0 * 50))
    xlo, xhi, llo, lhi = bounds
    for _ in range(rounds):
        xs, ls = np.linspace(xlo, xhi, size), np.linspace(llo, lhi, size)
        XI, LS = np.meshgrid(xs, ls, indexing="ij")
        ll = gpd_loglik(XI, np.exp(LS), x, w)
        if not np.isfinite(ll).any():
            return math.nan, math.nan, False
        i, j = np.unravel_index(np.argmax(np.where(np.isfinite(ll), ll, -np.inf)), ll.shape)
        dx, dl = (xhi - xlo) / (size - 1), (lhi - llo) / (size - 1)
        xi, lsig = xs[i], ls[j]
        xlo, xhi = max(bounds[0], xi - 2 * dx), min(bounds[1], xi + 2 * dx)
        llo, lhi = max(bounds[2], lsig - 2 * dl), min(bounds[3], lsig + 2 * dl)
    inside = (bounds[0] + 0.01 < xi < bounds[1] - 0.01
              and bounds[2] + 0.01 < lsig < bounds[3] - 0.01)
    return float(xi), float(math.exp(lsig)), bool(inside)


def gpd_survival(x: float, xi: float, sigma: float) -> float:
    """Return P(X > x) under a GPD(xi, sigma)."""
    if abs(xi) < 1e-9:
        return math.exp(-x / sigma)
    t = 1.0 + xi * x / sigma
    return 0.0 if t <= 0 else t ** (-1.0 / xi)


def tail_probability(Y: np.ndarray, e: np.ndarray, k: float) -> dict:
    """Return the T4 model probability of Y >= ln k: 0.15 * GPD survival above the
    entity-weighted 85th percentile, with the fitted parameters."""
    w = exceedance.entity_weights(e)
    u = exceedance.weighted_quantiles(Y, w, (THRESHOLD_Q,))[f"{THRESHOLD_Q:g}"]
    above = Y > u
    xi, sigma, ok = gpd_fit(Y[above] - u, w[above] / w[above].sum())
    p = (1 - THRESHOLD_Q) * gpd_survival(math.log(k) - u, xi, sigma) if ok else math.nan
    return {"P": p, "xi": xi, "sigma": sigma, "threshold": u, "excesses": int(above.sum()),
            "converged": ok}


def t4(panel: dict, mom: dict, F_near: float, k: float) -> dict:
    """Return T4 for class R at h = 24, with an entity bootstrap that refits each time."""
    mask = refclass.in_class(mom, "R", F_near, panel) & refclass.resolved(mom)
    Y, e = mom["Y"][mask], mom["e"][mask]
    fit = tail_probability(Y, e, k)
    ents, inv = np.unique(e, return_inverse=True)
    members = [np.flatnonzero(inv == j) for j in range(ents.size)]
    rng = np.random.default_rng(forecast.SEED)
    boot, failed = [], 0
    for _ in range(forecast.RESAMPLES):
        draw = rng.integers(0, ents.size, ents.size)
        pick = np.concatenate([members[j] for j in draw])
        ids = np.concatenate([np.full(members[j].size, n) for n, j in enumerate(draw)])
        r = tail_probability(Y[pick], ids, k)
        if r["converged"]:
            boot.append(r["P"])
        else:
            failed += 1
    share = failed / forecast.RESAMPLES
    res = {"label": recency.TERTIARY, "h": 24, "k_star": k, "fit": fit,
           "empirical_P": forecast.class_frequency(Y, e, k), "failed_resamples": failed,
           "failed_share": share}
    if share > 0.05 or not fit["converged"]:
        res["result"] = (f"the fit did not converge on {failed} of {forecast.RESAMPLES} "
                         f"resamples (more than 5 percent): no number is reported")
        res["P"], res["interval"] = None, None
    else:
        res["result"] = "converged"
        res["P"] = fit["P"]
        res["interval"] = [float(np.percentile(boot, 5)), float(np.percentile(boot, 95))]
    return res
