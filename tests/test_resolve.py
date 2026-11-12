import datetime as dt
import json

import pytest

from near_posterior import out, resolve


def later_snapshot(t0, daily_buyback):
    """A synthetic snapshot: supply grows 1000 NEAR a day, price 1, constant buybacks."""
    days = [t0 - dt.timedelta(days=i) for i in range(800)]
    return {"t0": t0, "b": {d: daily_buyback for d in days},
            "S": {d: 1e9 + 1000.0 * (d - days[-1]).days for d in days}, "p": {d: 1.0 for d in days}}


def test_resolves_after_the_date_and_stays_pending_before():
    reg = {"forecasts": {"24": {"P": 0.05, "resolution_date": "2028-11-11"}}}
    early = resolve.resolve(reg, later_snapshot(dt.date(2028, 11, 10), 5000.0))
    assert early["by_h"]["24"]["status"] == "pending"
    hit = resolve.resolve(reg, later_snapshot(dt.date(2029, 1, 1), 1001.0))["by_h"]["24"]
    assert hit["status"] == "resolved" and hit["outcome"] == 1
    assert hit["brier"] == pytest.approx(0.95 ** 2)
    miss = resolve.resolve(reg, later_snapshot(dt.date(2029, 1, 1), 999.0))["by_h"]["24"]
    assert miss["outcome"] == 0 and miss["brier"] == pytest.approx(0.05 ** 2)


def test_registered_forecast_matches_the_headline():
    reg = json.loads((out.RESULTS / "registered_forecast.json").read_text(encoding="ascii"))
    head = json.loads((out.RESULTS / "headline.json").read_text(encoding="ascii"))
    assert reg["t0"] == "2026-11-11" and reg["forecasts"]["24"]["resolution_date"] == "2028-11-11"
    if head["t0"] == reg["t0"] and head["model"] == "B0":
        assert reg["forecasts"]["24"]["P"] == pytest.approx(head["P"], rel=1e-9)
