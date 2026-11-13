import json

import numpy as np
import pytest

from near_posterior import out, total


def test_pooled_interval_and_between_share():
    same = [np.array([0.0, 1.0, 2.0])] * 4
    r = total.pooled(same)
    assert r["between_share"] == pytest.approx(0.0) and r["values"] == 12
    apart = [np.full(10, 0.0), np.full(10, 1.0)]
    assert total.pooled(apart)["between_share"] == pytest.approx(1.0)


def test_t3_pools_72_specifications_of_2000_values():
    r = json.loads((out.RESULTS / "total_uncertainty.json").read_text(encoding="ascii"))
    assert r["groups"] == 72 and r["values"] == 72 * 2000
    assert r["p5"] <= r["p50"] <= r["p95"] and 0 <= r["between_share"] <= 1


def test_gpd_fit_recovers_known_parameters():
    rng = np.random.default_rng(2)
    xi, sigma = 0.3, 1.0
    u = rng.uniform(size=5000)
    x = sigma / xi * ((1 - u) ** (-xi) - 1)
    fxi, fsigma, ok = total.gpd_fit(x, np.full(x.size, 1 / x.size))
    assert ok and fxi == pytest.approx(xi, abs=0.08) and fsigma == pytest.approx(sigma, rel=0.1)
    assert total.gpd_survival(0.0, fxi, fsigma) == 1.0
