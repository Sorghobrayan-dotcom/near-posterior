import math
import pathlib

import numpy as np

from near_posterior import coverage, speccurve

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "near_20261112"


def test_grid_has_864_rows_without_missing_values():
    rows = speccurve.grid(coverage.load(FIXTURE))
    assert len(rows) == 864
    assert all(v is not None for r in rows for v in r.values())
    keys = {(r["cls"], r["window"], r["h"], r["capture"], r["issuance"], r["G_P"]) for r in rows}
    assert len(keys) == 864
    assert sum(speccurve.is_primary(r) for r in rows) == 4


def test_verdict_bounds():
    assert speccurve.verdict(0.0999).startswith("buybacks are unlikely")
    assert speccurve.verdict(0.10) == "conditional"
    assert speccurve.verdict(0.50) == "conditional"
    assert speccurve.verdict(0.5001) == "supported"


def test_break_even():
    Y = np.log(np.array([1.0, 2.0, 3.0, 4.0]))
    w = np.full(4, 0.25)
    k50 = speccurve.break_even(Y, w)
    assert abs(k50 - 2.0) < 1e-12
    assert speccurve.share_above(Y, w, k50) > 0.5
    assert speccurve.share_above(Y, w, k50 * 1.0001) <= 0.5


def test_break_even_with_ties_and_weights():
    Y = np.array([0.0, 0.0, 1.0, 2.0])
    w = np.array([0.3, 0.3, 0.2, 0.2])
    assert speccurve.break_even(Y, w) == math.exp(0.0)
