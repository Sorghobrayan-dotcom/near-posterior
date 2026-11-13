"""Class frequency (model B0) and analog model (A_K), PREREG sections 4.3 and 5."""

import math

import numpy as np

SEED = 20261112
RESAMPLES = 2000


def entity_shares(Y: np.ndarray, entity: np.ndarray, k: float) -> tuple[np.ndarray, np.ndarray]:
    """Return (entities, p_j): per entity, the share of its moments with Y >= ln k."""
    ents, inv = np.unique(entity, return_inverse=True)
    hits = np.bincount(inv, weights=(Y >= math.log(k)).astype(float), minlength=ents.size)
    n = np.bincount(inv, minlength=ents.size)
    return ents, hits / n


def class_frequency(Y: np.ndarray, entity: np.ndarray, k: float) -> float:
    """Return P_B0(k) = mean over entities of p_j."""
    return float(entity_shares(Y, entity, k)[1].mean())


def bootstrap_means(p: np.ndarray, resamples: int = RESAMPLES, seed: int = SEED) -> np.ndarray:
    """Return the mean of p over each entity resample (the registered cluster bootstrap)."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, p.size, size=(resamples, p.size))
    return p[idx].mean(axis=1)


def cluster_bootstrap(p: np.ndarray, resamples: int = RESAMPLES, seed: int = SEED) -> tuple:
    """Return the 5th and 95th percentiles of the mean of p over entity resamples."""
    means = bootstrap_means(p, resamples, seed)
    return float(np.percentile(means, 5)), float(np.percentile(means, 95))


def binom_cdf(x: int, n: int, p: float) -> float:
    """Return P(X <= x) for X ~ Binomial(n, p), summed in log space."""
    if p <= 0:
        return 1.0
    if p >= 1:
        return 1.0 if x >= n else 0.0
    lp, lq = math.log(p), math.log1p(-p)
    terms = [math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lp + (n - i) * lq
             for i in range(x + 1)]
    top = max(terms)
    return min(1.0, math.exp(top) * math.fsum(math.exp(t - top) for t in terms))


def bisect(fn, lo: float = 0.0, hi: float = 1.0, steps: int = 200) -> float:
    """Return the root of a decreasing function fn on [lo, hi] by bisection."""
    for _ in range(steps):
        mid = 0.5 * (lo + hi)
        if fn(mid) > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def clopper_pearson(x: int, n: int, level: float = 0.90) -> tuple[float, float]:
    """Return the exact Clopper-Pearson interval for x successes in n trials."""
    a = (1.0 - level) / 2.0
    lower = 0.0 if x == 0 else bisect(lambda p: a - (1.0 - binom_cdf(x - 1, n, p)))
    upper = 1.0 if x == n else bisect(lambda p: binom_cdf(x, n, p) - a)
    return lower, upper


def b0(Y: np.ndarray, entity: np.ndarray, k: float, origin_year: np.ndarray | None = None) -> dict:
    """Return P_B0(k) with its cluster-bootstrap interval, the one-moment-per-entity estimate
    with its Clopper-Pearson interval, and the estimate by calendar year of the origin."""
    ents, p = entity_shares(Y, entity, k)
    res = {"P": float(p.mean()), "interval": cluster_bootstrap(p), "entities": int(ents.size),
           "moments": int(Y.size)}
    if origin_year is not None:
        order = np.lexsort((origin_year, entity))
        first = order[np.r_[True, entity[order][1:] != entity[order][:-1]]]
        x = int((Y[first] >= math.log(k)).sum())
        res["earliest"] = {"x": x, "n": int(first.size), "P": x / first.size,
                           "interval": clopper_pearson(x, int(first.size))}
        res["by_year"] = {}
        for year in sorted(set(origin_year.tolist())):
            sel = origin_year == year
            e_y, p_y = entity_shares(Y[sel], entity[sel], k)
            res["by_year"][str(year)] = {"P": float(p_y.mean()), "entities": int(e_y.size),
                                         "moments": int(sel.sum())}
    return res


def robust_scale(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return per-column (median, scale) with scale = 1.4826 * MAD, else std, else 1."""
    med = np.median(X, axis=0)
    scale = 1.4826 * np.median(np.abs(X - med), axis=0)
    std = X.std(axis=0)
    scale = np.where(scale > 0, scale, np.where(std > 0, std, 1.0))
    return med, scale


def analogs(target: np.ndarray, X: np.ndarray, entity: np.ndarray, K: int,
            order_key: np.ndarray | None = None) -> np.ndarray:
    """Return the indices of the pool moments of the K nearest entities (PREREG 5).

    Each entity contributes its single nearest moment; ties break on `order_key` (e.g. the
    origin month), then on the entity id.
    """
    _, scale = robust_scale(X)
    d = np.sqrt((((X - target) / scale) ** 2).sum(axis=1))
    key = order_key if order_key is not None else np.zeros(d.size)
    order = np.lexsort((key, d, entity))
    first = order[np.r_[True, entity[order][1:] != entity[order][:-1]]]
    best = first[np.lexsort((entity[first], key[first], d[first]))]
    return best[:K]


def analog_forecast(Y: np.ndarray, k: float) -> dict:
    """Return P_A(k) = share of the analog outcomes with Y >= ln k, with its exact interval."""
    x = int((Y >= math.log(k)).sum())
    return {"P": x / Y.size, "x": x, "n": int(Y.size), "interval": clopper_pearson(x, int(Y.size))}
