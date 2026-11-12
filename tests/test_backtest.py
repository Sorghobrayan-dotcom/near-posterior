import datetime as dt
import math

import numpy as np
import pytest

from near_posterior import backtest, refclass

F_NEAR = 365.0 * 1e5


@pytest.fixture(scope="module")
def panel():
    """A synthetic panel of 150 entities with monthly log random walks of daily fees."""
    rng = np.random.default_rng(11)
    start, end = dt.date(2017, 1, 1), dt.date(2023, 1, 2)
    n_days = (end - start).days + 1
    entities, rows = [], []
    for j in range(150):
        eid = f"e{j:03d}"
        entities.append({"entity_id": eid, "name": eid, "category": "Dexs"})
        first = int(rng.integers(0, 700))
        level = math.log(1e5) + rng.normal(0, 1)
        for i in range(first, n_days):
            if i % 30 == 0:
                level += rng.normal(0, 0.3)
            day = (start + dt.timedelta(days=i)).isoformat()
            rows.append((eid, day, math.exp(level)))
    return refclass.from_rows(entities, rows)


def test_pool_has_no_look_ahead_and_no_own_entity(panel):
    ov = refclass.origin_values(panel)
    for h in (12, 24):
        mom = refclass.moments(panel, h, ov)
        in_r = refclass.in_class(mom, "R", F_NEAR, panel)
        tg = backtest.targets(mom, ov, in_r)
        assert tg.size > 50
        for i in tg[:: max(1, tg.size // 40)]:
            b0_idx, an_idx = backtest.pools(mom, i, h, in_r)
            for idx in (b0_idx, an_idx):
                assert (mom["month"][idx] + h <= mom["month"][i]).all()
                assert (mom["e"][idx] != mom["e"][i]).all()
                assert refclass.resolved(mom)[idx].all()


def test_targets_need_valid_lags(panel):
    ov = refclass.origin_values(panel)
    mom = refclass.moments(panel, 12, ov)
    in_r = refclass.in_class(mom, "R", F_NEAR, panel)
    for i in backtest.targets(mom, ov, in_r):
        e, k = mom["e"][i], mom["k"][i]
        assert all(ov["valid"][e, k - lag] for lag in (3, 6, 9, 12))
        assert len(backtest.quarterly_changes(ov, e, k)) >= 4


def test_rolling_origin_scores_and_drops(panel, monkeypatch):
    with monkeypatch.context() as mp:
        mp.setattr(backtest, "MIN_ANALOG_ENTITIES", 1000)
        none = backtest.rolling_origin(panel, 12, F_NEAR)
    assert not none["rows"] and none["dropped"]
    run = backtest.rolling_origin(panel, 12, F_NEAR)
    assert run["rows"] and run["dropped"]
    assert run["candidates"] == len(run["rows"]) + len(run["dropped"]) == none["candidates"]
    for d in run["dropped"]:
        assert d["analog_entities"] < 120 or d["b0_entities"] < 20
    for r in run["rows"]:
        assert r["analog_entities"] >= 120 and r["b0_entities"] >= 20
        for m in backtest.MODELS:
            assert math.isfinite(r[m]["crps"]) and 0 <= r[m]["pit"] <= 1
    agg = backtest.aggregate(run)
    assert agg["scored"] == len(run["rows"])
    assert set(agg["models"]) == set(backtest.MODELS)


def fake(h24, h12):
    """Return aggregated scores with given (sufficient, crps by model, A interval) per horizon."""
    res = {}
    for h, (suff, crps, interval) in (("24", h24), ("12", h12)):
        models = {m: {"crps": crps.get(m, 1.0), "crps_minus_B0_interval": interval}
                  for m in backtest.CANDIDATES}
        res[h] = {"sufficient": suff, "models": models}
    return res


def test_select_model_rule():
    best = {"B0": 1.0, "A_60": 0.8}
    c = backtest.select_model(fake((True, best, (-0.3, -0.1)), (True, {}, (0, 0))))
    assert c["model"] == "A_60" and c["horizon"] == 24
    c = backtest.select_model(fake((True, best, (-0.3, 0.1)), (True, {}, (0, 0))))
    assert c["model"] == "B0" and c["lowest_crps"] == "A_60"
    c = backtest.select_model(fake((False, best, (-0.3, -0.1)), (True, {"A_30": 0.5}, (-1, -0.5))))
    assert c["model"] == "A_30" and c["horizon"] == 12
    c = backtest.select_model(fake((False, best, (-0.3, -0.1)), (False, best, (-0.3, -0.1))))
    assert c["model"] == "B0" and c["horizon"] is None
    c = backtest.select_model(fake((True, {"B0": 0.5}, (0, 0)), (True, {}, (0, 0))))
    assert c["model"] == "B0" and c["lowest_crps"] == "B0"
