import datetime as dt

import pytest

from near_posterior import coverage, milestones, resolve


def test_path_starts_at_today_and_ends_at_one():
    t0 = dt.date(2026, 11, 11)
    assert milestones.path(0.25, t0, t0) == pytest.approx(0.25)
    assert milestones.path(0.25, t0, dt.date(2028, 11, 11)) == pytest.approx(1.0)
    assert milestones.path(0.25, t0, dt.date(2027, 11, 11)) == pytest.approx(0.5, abs=1e-3)


def test_milestones_on_the_registered_snapshot_are_pending_and_increasing():
    snap = coverage.load(resolve.FIXTURE)
    res = milestones.compute(snap, snap)
    needed = [r["C_needed"] for r in res["milestones"]]
    assert needed == sorted(needed) and needed[-1] == pytest.approx(1.0)
    assert all(r["status"] == "pending" for r in res["milestones"])
    assert res["today"]["C_90"] == pytest.approx(res["C0"])
    assert res["today"]["status"] == "ahead"
