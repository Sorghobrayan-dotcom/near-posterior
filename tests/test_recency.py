import json

import numpy as np
import pytest

from near_posterior import out, recency


def test_weights_sum_to_one_and_infinity_is_entity_equal():
    rng = np.random.default_rng(4)
    e = rng.integers(0, 7, 50)
    months = rng.integers(0, 60, 50)
    for H in recency.HALF_LIVES:
        assert recency.weights(e, months, 80, H).sum() == pytest.approx(1.0)
    w = recency.weights(e, months, 80, None)
    for j in np.unique(e):
        assert w[e == j].sum() == pytest.approx(1 / np.unique(e).size)


def test_infinity_reproduces_c0_exactly():
    rec = json.loads((out.RESULTS / "recency.json").read_text(encoding="ascii"))
    val = json.loads((out.RESULTS / "validation.json").read_text(encoding="ascii"))
    for h in ("12", "24"):
        inf = rec["by_h"][h]["all"]["by_H"]["inf"]
        c0 = val["S1"][h]["models"]["C0"]
        assert rec["by_h"][h]["all"]["targets"] == val["S1"][h]["scored"]
        for m in recency.METRICS:
            assert inf[m] == pytest.approx(c0[m], rel=1e-9, abs=1e-12), (h, m)


def test_recent_outcomes_lower_make_a_finite_half_life_win():
    rng = np.random.default_rng(8)
    months = np.repeat(np.arange(60), 20)
    e = np.arange(months.size) % 40
    z = np.where(months < 40, 1.0, -1.0) + rng.normal(0, 0.2, months.size)
    targets = rng.normal(-1.0, 0.2, 200)
    crps = {H: np.mean([recency.target_scores(z, e, months, 72, y, H)["crps"] for y in targets])
            for H in (12, None)}
    assert crps[12] < crps[None]


def row(entity, year, crps_by_h):
    """Return a fake scored target with the given CRPS per half-life label."""
    return {"entity": entity, "year": year, "Y": 0.0,
            **{lab: {"crps": c} for lab, c in crps_by_h.items()}}


def test_2025_targets_never_choose_h():
    train = [row(f"a{i}", 2024, {"12": 1.0, "24": 1.0, "48": 1.0, "inf": 0.9}) for i in range(5)]
    test = [row(f"b{i}", 2025, {"12": 0.1, "24": 0.5, "48": 0.5, "inf": 2.0}) for i in range(5)]
    c = recency.choose(train + test)
    assert c["best_on_choice_set"] == "inf" and c["H_star"] == "inf"
    assert c["choice_mean_crps"]["inf"] == pytest.approx(0.9)
    test[0]["12"]["crps"] = -50.0
    assert recency.choose(train + test)["choice_mean_crps"] == c["choice_mean_crps"]


def test_finite_h_kept_only_if_it_beats_c0_on_held_out_origins():
    train = [row(f"a{i}", 2023, {"12": 0.5, "24": 1.0, "48": 1.0, "inf": 1.0}) for i in range(8)]
    better = [row(f"b{i}", 2025, {"12": 0.5, "24": 1, "48": 1, "inf": 1.0}) for i in range(8)]
    worse = [row(f"b{i}", 2025, {"12": 1.5, "24": 1, "48": 1, "inf": 1.0}) for i in range(8)]
    assert recency.choose(train + better)["H_star"] == "12"
    assert recency.choose(train + worse)["H_star"] == "inf"
