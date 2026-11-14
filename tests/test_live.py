"""Tests of the short live forecast of PREREG_4.md (offline)."""

import datetime as dt
import json

import pytest

from near_posterior import live, onchain, thesis


def series(values, start="2026-01-01"):
    """Return [date, C_90] rows on consecutive days from start."""
    d0 = dt.date.fromisoformat(start)
    return [[(d0 + dt.timedelta(days=i)).isoformat(), v] for i, v in enumerate(values)]


def test_probability_counts_pairs_after_the_window_is_full_and_up_to_the_anchor():
    s = series([0.0] * 89 + [1.0, 2.0, 1.5, 1.5, 3.0])
    # first full day is day 89 (2026-03-31); anchor is the last day (day 93), k = 2
    res = live.probability(s, "2026-01-01", s[-1][0], "2026-04-06")
    assert res["k"] == 2 and res["first_day"] == "2026-03-31"
    # pairs: (89, 91) 1.0 -> 1.5 yes, (90, 92) 2.0 -> 1.5 no, (91, 93) 1.5 -> 3.0 yes
    assert res["n"] == 3 and res["hits"] == 2 and res["P"] == pytest.approx(2 / 3)


def test_freeze_anchors_at_the_last_daily_day_and_refuses_a_past_event():
    daily = [{"date": d, "C_90": c} for d, c in series([0.1] * 100 + [0.2], "2026-08-01")]
    cov = {"daily": daily, "buyback_start": "2026-08-01", "fetched_at": "x"}
    fz = live.freeze(cov)
    assert fz["anchor_day"] == daily[-1]["date"] and fz["anchor_C_90"] == 0.2
    assert fz["anchor_day"] == "2026-11-09" and fz["k"] == 6 and live.frozen_check(fz)[0]
    late = [{"date": d, "C_90": c} for d, c in series([0.1] * 120, "2026-08-01")]
    with pytest.raises(ValueError):
        live.freeze({"daily": late, "buyback_start": "2026-08-01", "fetched_at": "x"})


def test_reading_is_pending_until_the_event_day_then_uses_one_snapshot():
    fz = {"P": 0.6, "anchor_day": "2026-11-12", "event_day": "2026-11-15", "series": []}
    cov = {"fetched_at": "2026-11-17T06:40:00+00:00", "t0": "2026-11-16",
           "daily": [{"date": "2026-11-12", "C_90": 0.19}, {"date": "2026-11-15", "C_90": 0.18}]}
    res = live.reading(fz, cov)
    assert "series" not in res
    now = res["current_reading"]
    assert now["outcome"] == 0 and now["C_90_anchor"] == 0.19 and now["fetched_after_due"]
    assert now["brier"] == pytest.approx(0.36)
    cov["daily"] = cov["daily"][:1]
    assert live.reading(fz, cov)["current_reading"]["status"] == "pending"


def test_committed_frozen_forecast_recomputes():
    assert live.checks() and all(ok for ok, _ in live.checks())


def test_register_refuses_once_the_forecast_is_on_chain(tmp_path, monkeypatch):
    path = tmp_path / "commitments.json"
    path.write_text(json.dumps({"live": {}}), encoding="utf-8")
    monkeypatch.setattr(live, "COMMITS", path)
    monkeypatch.setattr(live, "FROZEN", tmp_path / "forecast.json")
    assert live.register() == 1 and not (tmp_path / "forecast.json").exists()


def test_live_checks_are_absent_without_a_live_key_and_check_the_record_with_one():
    assert onchain.live_offline({}) == [] and onchain.live_live({}) == []
    fz = json.loads(live.FROZEN.read_text(encoding="ascii"))
    rec = {k: fz[k] for k in ("anchor_day", "anchor_C_90", "event_day", "k", "n", "P",
                              "resolution_due")}
    rec.update(type="live", sha256={"PREREG_4.md": onchain.sha256("PREREG_4.md"),
                                    "data/live/forecast.json": onchain.sha256(
                                        "data/live/forecast.json")})
    com = {"live": {"contract": "c.testnet", "index": 0, "tx": "t", "record": json.dumps(rec),
                    "code_sha256": onchain.sha256("contract/posterior_registry.wasm")}}
    checks = onchain.live_offline(com)
    assert len(checks) == 2 and all(ok for ok, _ in checks)
    rec["P"] = 0.5
    com["live"]["record"] = json.dumps(rec)
    assert not onchain.live_offline(com)[1][0]


def test_live_window_says_the_window_had_started_only_when_it_had():
    """The sentence appears when the snapshot was fetched after the anchor day, not otherwise."""
    lv = {"anchor_day": "2026-11-12", "snapshot_fetched_at": "2026-11-13T14:47:40+00:00"}
    assert "2026-11-13, after 2026-11-12 had ended" in thesis.live_window(lv)
    assert thesis.live_window({**lv, "snapshot_fetched_at": "2026-11-12T23:00:00+00:00"}) == ""
