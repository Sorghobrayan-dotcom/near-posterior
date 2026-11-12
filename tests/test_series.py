import datetime as dt
import json

import pytest

from near_posterior import series


def test_committed_snapshot_matches_manifest():
    man = series.manifest()
    assert set(man["files"]) == {
        "intents_volume",
        "intents_fees",
        "intents_revenue",
        "intents_holders_revenue",
        "nearblocks_charts",
    }


def test_fetch_day_is_dropped():
    cutoff = dt.datetime.fromisoformat(series.manifest()["fetched_at"]).date()
    for name in ("intents_volume", "intents_fees", "intents_revenue"):
        days = series.llama_daily(name)
        assert days, name
        assert days[-1][0] < cutoff


def test_window_sum_names_missing_days():
    s = [(dt.date(2026, 11, 1), 1.0), (dt.date(2026, 11, 3), 2.0)]
    with pytest.raises(ValueError, match="1 missing days"):
        series.window_sum(s, dt.date(2026, 11, 3), 3)


def test_tampered_file_is_refused(tmp_path):
    (tmp_path / "x.json").write_text('{"totalDataChart": []}')
    (tmp_path / "manifest.json").write_text(
        json.dumps({"fetched_at": "2026-11-12T00:00:00+00:00", "files": {"x": {"sha256": "0" * 64}}})
    )
    with pytest.raises(ValueError, match="does not match"):
        series.manifest(tmp_path)
