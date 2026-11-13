import json
import math

import numpy as np
import pytest

from near_posterior import out, recalibration as rc, scoring


def test_calibrated_forecast_is_left_unchanged():
    rng = np.random.default_rng(3)
    fitted = rc.fit(rng.uniform(size=5000))
    u = np.linspace(0, 1, 101)
    assert np.max(np.abs(rc.G(u, fitted) - u)) < 1.63 / math.sqrt(5000) * 1.5


def test_forecast_doubling_the_tail_is_corrected():
    rng = np.random.default_rng(5)
    a = 1.5
    true_tail = 1 - scoring.Phi(a)
    mu = a - scoring.normal_quantile(1 - 2 * true_tail)
    assert 1 - scoring.Phi(a - mu) == pytest.approx(2 * true_tail, rel=1e-6)
    y_train = rng.normal(size=5000)
    fitted = rc.fit([scoring.Phi(y - mu) for y in y_train])
    p_cal = 1 - float(rc.G(scoring.Phi(a - mu), fitted))
    se = math.sqrt(true_tail * (1 - true_tail) / 5000)
    assert abs(p_cal - true_tail) < 4 * se


def fake_row(entity, year, pit, f2):
    """Return a fake S1 target row for the recalibration functions."""
    return {"entity": entity, "year": year, "Y": 0.0, "pit": pit,
            "raw": {"1": 0.5, "2": 0.2, "5": 0.05}, "F": {"1": 0.5, "2": f2, "5": 0.95}}


def test_2025_targets_never_fit_the_map_tested_on_them():
    res = json.loads((out.RESULTS / "recalibration.json").read_text(encoding="ascii"))
    h = res["models"]["C0"]["held_out_12"]
    assert h["fitted_on"] == "origins up to 2024"
    train = [fake_row(f"a{i}", 2024, p, 0.8) for i, p in enumerate((0.1, 0.2, 0.3))]
    test = [fake_row(f"b{i}", 2025, p, 0.8) for i, p in enumerate((0.9, 0.95))]
    g1 = rc.fit([r["pit"] for r in train + test if r["year"] <= rc.TRAIN_LAST_YEAR])
    test[0]["pit"] = 0.0
    g2 = rc.fit([r["pit"] for r in train + test if r["year"] <= rc.TRAIN_LAST_YEAR])
    assert np.array_equal(g1, g2)


def test_scores_apply_the_map_to_event_probabilities_and_pits():
    rows = [fake_row("a", 2025, 0.3, 0.8)]
    fitted = rc.fit([0.1, 0.2, 0.9, 0.95])
    s = rc.scores(rows, fitted)[0]
    assert s["prob_2"] == pytest.approx(1 - 0.5) and s["pit"] == pytest.approx(0.5)
    assert rc.scores(rows, None)[0]["prob_2"] == 0.2


def test_improves_rule():
    good = {f"brier_{k}": {"mean": -0.01, "interval": [-0.02, -0.001]} for k in ("1", "2", "5")}
    assert rc.improves(good)
    mixed = dict(good, brier_5={"mean": 0.001, "interval": [-0.01, 0.01]})
    assert not rc.improves(mixed)
