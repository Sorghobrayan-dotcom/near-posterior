import csv
import json

import numpy as np
import pytest

from near_posterior import ask, coverage, exceedance, out, refclass


def test_ask_at_primary_k_returns_the_registered_headline():
    head = json.loads((out.RESULTS / "headline.json").read_text(encoding="ascii"))
    panel = refclass.load_panel()
    cov = coverage.summary(coverage.load())
    k = ask.primary_k(24)
    assert k == pytest.approx(head["k_star"], rel=1e-9)
    a = ask.answer(panel, refclass.moments(panel, 24), cov["F_near"], k)
    assert a["P"] == pytest.approx(head["P"], rel=1e-9)
    assert a["interval"][0] == pytest.approx(head["interval"][0], rel=1e-9)
    assert a["interval"][1] == pytest.approx(head["interval"][1], rel=1e-9)
    assert a["entities"] == head["entities"]


def test_exceedance_is_non_increasing_in_k():
    with open(out.RESULTS / "exceedance.csv", encoding="ascii", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 3 * 81
    for h in ("12", "24", "36"):
        sub = [r for r in rows if r["h"] == h]
        for key in ("P", "P_lo", "P_hi"):
            v = [float(r[key]) for r in sub]
            assert all(a >= b - 1e-12 for a, b in zip(v, v[1:])), (h, key)


def test_weighted_quantiles_lower_and_entity_weights():
    x = np.array([1.0, 2.0, 3.0, 4.0])
    e = np.array([0, 0, 0, 1])
    w = exceedance.entity_weights(e)
    assert w.sum() == pytest.approx(1.0) and w[3] == pytest.approx(0.5)
    q = exceedance.weighted_quantiles(x, w, (0.1, 0.5, 0.51))
    assert q == {"0.1": 1.0, "0.5": 3.0, "0.51": 4.0}


def test_ask_slug_class_excludes_the_entity_itself():
    panel = refclass.load_panel()
    ov = refclass.origin_values(panel)
    mom = refclass.moments(panel, 12, ov)
    entity = panel["ids"][0]
    sample, target = ask.centred_sample(panel, mom, ov, entity, 12)
    assert target["entity"] == entity and target["F"] > 0
    assert panel["ids"].index(entity) not in set(sample["e"].tolist())
