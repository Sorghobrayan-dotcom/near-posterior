import math

import numpy as np
import pytest

from near_posterior import forecast, scoring


@pytest.mark.parametrize("x, lo, hi", [
    (0, 0.0, 1 - 0.05 ** (1 / 10)),
    (10, 0.05 ** (1 / 10), 1.0),
    (3, 0.0872644, 0.6066242),
])
def test_clopper_pearson_exact(x, lo, hi):
    got = forecast.clopper_pearson(x, 10, 0.90)
    assert got[0] == pytest.approx(lo, abs=1e-6) and got[1] == pytest.approx(hi, abs=1e-6)


def test_clopper_pearson_defining_property():
    lo, hi = forecast.clopper_pearson(3, 10, 0.90)
    assert 1 - forecast.binom_cdf(2, 10, lo) == pytest.approx(0.05, abs=1e-12)
    assert forecast.binom_cdf(3, 10, hi) == pytest.approx(0.05, abs=1e-12)


def test_class_frequency_weights_entities_equally():
    Y = np.array([1.0, 1.0, 1.0, -1.0])
    ent = np.array([0, 0, 0, 1])
    assert forecast.class_frequency(Y, ent, 1.0) == pytest.approx(0.5)


def test_bootstrap_reproducible_with_seed():
    p = np.random.default_rng(1).uniform(size=50)
    assert forecast.cluster_bootstrap(p) == forecast.cluster_bootstrap(p)
    lo, hi = forecast.cluster_bootstrap(p)
    assert lo < p.mean() < hi


def test_b0_earliest_and_by_year():
    Y = np.array([2.0, -1.0, 3.0, 0.5])
    ent = np.array([0, 0, 1, 2])
    year = np.array([2021, 2020, 2022, 2021])
    res = forecast.b0(Y, ent, math.e, year)
    assert res["P"] == pytest.approx((0.5 + 1 + 0) / 3)
    assert res["earliest"]["n"] == 3 and res["earliest"]["x"] == 1
    assert res["by_year"]["2021"]["entities"] == 2


def test_analogs_keep_one_moment_per_entity():
    rng = np.random.default_rng(3)
    X = rng.normal(size=(300, 3))
    ent = np.repeat(np.arange(100), 3)
    idx = forecast.analogs(np.zeros(3), X, ent, 30, np.tile(np.arange(3), 100))
    assert idx.size == 30 and np.unique(ent[idx]).size == 30
    _, scale = forecast.robust_scale(X)
    d = np.sqrt((((X - 0) / scale) ** 2).sum(axis=1))
    for i in idx:
        assert d[i] == d[ent == ent[i]].min()
    rest = np.setdiff1d(np.arange(100), ent[idx])
    best_rest = min(d[ent == r].min() for r in rest)
    assert d[idx].max() <= best_rest


def test_robust_scale_fallbacks():
    X = np.array([[1.0, 5.0, 2.0], [1.0, 5.0, 4.0], [1.0, 5.0, 4.0], [1.0, 7.0, 4.0]])
    med, scale = forecast.robust_scale(X)
    assert scale[0] == 1.0 and scale[1] == pytest.approx(X[:, 1].std()) and scale[2] > 0


def test_crps_sample_matches_normal():
    rng = np.random.default_rng(5)
    z = rng.normal(0.3, 1.7, size=200_000)
    w = np.full(z.size, 1 / z.size)
    for y in (-2.0, 0.0, 1.0, 4.0):
        assert scoring.crps_sample(z, w, y) == pytest.approx(scoring.crps_normal(0.3, 1.7, y), abs=1e-2)


def test_crps_sample_small_case():
    z, w = np.array([0.0, 1.0]), np.array([0.5, 0.5])
    assert scoring.crps_sample(z, w, 0.0) == pytest.approx(0.5 * 1 - 0.5 * 0.5)


def test_brier_perfect_forecast_is_zero():
    assert scoring.brier(1.0, 1) == 0 and scoring.brier(0.0, 0) == 0


def test_pit_of_calibrated_forecast_is_uniform():
    rng = np.random.default_rng(9)
    y = rng.normal(size=4000)
    res = scoring.pit([scoring.pit_normal(0.0, 1.0, v) for v in y])
    assert res["ks"] < 1.36 / math.sqrt(4000)


def test_weighted_quantile_and_coverage():
    z, w = np.array([3.0, 1.0, 2.0, 4.0]), np.full(4, 0.25)
    assert scoring.weighted_quantile(z, w, 0.25) == 1.0
    assert scoring.weighted_quantile(z, w, 0.75) == 3.0
    assert scoring.interval_coverage(1.0, 3.0, 3.0) and not scoring.interval_coverage(1.0, 3.0, 3.5)
    assert scoring.normal_quantile(0.95) == pytest.approx(1.6448536, abs=1e-6)
