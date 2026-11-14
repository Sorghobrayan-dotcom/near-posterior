"""Tests of the on-chain commitments (offline)."""

import json

from near_posterior import onchain


def test_offline_checks_pass():
    """Every committed record names the files and numbers of this repository."""
    checks = onchain.offline_checks()
    assert len(checks) == 7 and all(ok for ok, _ in checks)


def test_record_names_registered_forecast():
    """The 24-month record carries the registered probability and the resolution date."""
    com = json.loads(onchain.FILE.read_text(encoding="utf-8"))
    rec = json.loads(next(c["record"] for c in com["commitments"] if c["h_months"] == 24))
    reg = json.loads((onchain.out.ROOT / "results" / "registered_forecast.json")
                     .read_text(encoding="utf-8"))
    assert rec["P"] == reg["forecasts"]["24"]["P"]
    assert rec["resolution_date"] == "2028-11-11"


def test_b58_matches_near_encoding():
    """base58 keeps leading zero bytes as '1' characters."""
    assert onchain.b58(b"\0\0\x01") == "112"
