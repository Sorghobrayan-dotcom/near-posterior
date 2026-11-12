import datetime as dt

import pytest

from near_posterior import rpc_check


def test_compare_finds_the_matching_edge():
    d0, d1 = dt.date(2025, 1, 2), dt.date(2026, 1, 2)
    snap = {"S": {d0: 1000.0, d1: 1030.0}}
    rpc = {"rpc": "x", "fetched_at": "t", "days": {
        d0.isoformat(): {"start_of_day": {"height": 1, "total_supply": str(999 * 10**24)},
                         "end_of_day": {"height": 2, "total_supply": str(1000 * 10**24)}},
        d1.isoformat(): {"start_of_day": {"height": 3, "total_supply": str(1029 * 10**24)},
                         "end_of_day": {"height": 4, "total_supply": str(1030 * 10**24)}},
    }}
    res = rpc_check.compare(snap, rpc)
    assert res["closest_edge"] == "end_of_day"
    assert res["issuance"]["end_of_day"]["rel_diff"] == 0.0
    assert res["issuance"]["end_of_day"]["r_rpc"] == pytest.approx(0.03)
    assert res["issuance"]["start_of_day"]["I_rpc"] == pytest.approx(30.0)
