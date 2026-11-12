"""Proper scores and calibration checks for the backtest (PREREG section 6)."""

import math

import numpy as np


def Phi(z: float) -> float:
    """Return the standard Normal CDF, computed with math.erf."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def phi(z: float) -> float:
    """Return the standard Normal density."""
    return math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)


def normal_quantile(q: float) -> float:
    """Return the standard Normal quantile of q by bisection on Phi."""
    lo, hi = -40.0, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if Phi(mid) < q:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def brier(p: float, o: float) -> float:
    """Return the Brier score (p - o)^2 of probability p for outcome o in {0, 1}."""
    return (p - o) ** 2


def crps_sample(z: np.ndarray, w: np.ndarray, y: float) -> float:
    """Return the CRPS of a weighted sample (weights summing to 1) at observation y."""
    order = np.argsort(z, kind="stable")
    z, w = z[order], w[order]
    c = np.cumsum(w)
    below, above = c - w, c[-1] - c
    spread = 2.0 * float(np.sum(w * z * (below - above)))
    return float(np.sum(w * np.abs(z - y))) - 0.5 * spread


def crps_normal(mu: float, s: float, y: float) -> float:
    """Return the CRPS of Normal(mu, s^2) at observation y."""
    z = (y - mu) / s
    return s * (z * (2.0 * Phi(z) - 1.0) + 2.0 * phi(z) - 1.0 / math.sqrt(math.pi))


def weighted_quantile(z: np.ndarray, w: np.ndarray, q: float) -> float:
    """Return the smallest sample value whose cumulative weight reaches q."""
    order = np.argsort(z, kind="stable")
    c = np.cumsum(w[order])
    i = int(np.searchsorted(c, q * c[-1] - 1e-12))
    return float(z[order][min(i, z.size - 1)])


def interval_coverage(lo: float, hi: float, y: float) -> bool:
    """Return True if y lies in the closed interval [lo, hi]."""
    return lo <= y <= hi


def pit_sample(z: np.ndarray, w: np.ndarray, y: float) -> float:
    """Return the mid-PIT P(Z < y) + 0.5 P(Z = y) of a weighted sample."""
    return float(np.sum(w[z < y]) + 0.5 * np.sum(w[z == y])) / float(np.sum(w))


def pit_normal(mu: float, s: float, y: float) -> float:
    """Return the PIT of Normal(mu, s^2) at y."""
    return Phi((y - mu) / s)


def pit(values: list[float], bins: int = 10) -> dict:
    """Return the PIT histogram (counts per equal bin) and the KS distance to uniform."""
    v = np.sort(np.asarray(values, dtype=float))
    hist = np.histogram(v, bins=bins, range=(0.0, 1.0))[0]
    n = v.size
    ks = float(max(np.max(np.arange(1, n + 1) / n - v), np.max(v - np.arange(n) / n))) if n else None
    return {"histogram": [int(x) for x in hist], "ks": ks, "n": int(n)}
