import datetime as dt
import math
import re

import pytest

from near_posterior import audit, out

REQUIRED = ["thesis", "repo_url", "commit", "file", "line", "metric", "value", "unit", "source",
            "definition", "recompute"]
JUDGEMENT = re.compile(r"\b(wrong|bad|poor|sloppy|mistaken?|incorrect|flawed|careless|misleading|"
                       r"naive|fake|invalid)\b", re.I)


def test_claims_cover_ten_theses_with_provenance():
    claims = audit.load_claims()
    assert len({c["thesis"] for c in claims}) >= 10
    for c in claims:
        for key in REQUIRED:
            assert c[key], (c["thesis"], key)
        assert re.fullmatch(r"[0-9a-f]{40}", c["commit"])
        assert c["repo_url"] == "https://github.com/" + c["thesis"]
        assert int(c["line"]) >= 1 and c["metric"] in audit.METRICS
        float(c["value"])
        if c["recompute"] != "none":
            assert int(c["window_days"]) > 0
            dt.date.fromisoformat(c["window_end"])
            dt.date.fromisoformat(c["window_start"])
        else:
            assert c["note"], "a value not recomputed says why"


def test_no_judgement_words():
    for path in (audit.CLAIMS, out.RESULTS / "audit.csv", out.RESULTS / "audit.json"):
        assert not JUDGEMENT.search(path.read_text(encoding="ascii")), path


def test_decompose_identity():
    d = audit.decompose(3.0, 2.0, 1.5)
    assert d["total"] == pytest.approx(math.log(3.0 / 1.5))
    assert d["e"] == pytest.approx(math.log(1.5)) and not d["reproduced"]
    assert audit.decompose(1.0199, 1.0, 1.0)["reproduced"]


def test_dispersion_needs_five():
    assert audit.dispersion([1.0, 2.0, 3.0, 4.0])["iqr_ln"] is None
    d = audit.dispersion([1.0, 2.0, 3.0, 4.0, 5.0])
    assert d["n"] == 5 and d["iqr_ln"] == pytest.approx(math.log(4.0) - math.log(2.0))


def snapshot():
    """A synthetic snapshot with constant daily series."""
    days = [dt.date(2025, 1, 1) + dt.timedelta(days=i) for i in range(400)]
    return {"b": {d: 10.0 for d in days}, "f": {d: 40.0 for d in days},
            "v": {d: 1000.0 for d in days}, "rev": {d: 12.0 for d in days},
            "S": {d: 1000.0 + i for i, d in enumerate(days)}, "p": {d: 2.0 for d in days},
            "t0": days[-1]}


@pytest.mark.parametrize("rule, ann, param, expected", [
    ("sum_b", "1", "", 300.0),
    ("sum_rev", "12", "", 12 * 360.0),
    ("sum_v", str(1 / 30), "", 1000.0),
    ("kappa", "100", "", 25.0),
    ("kappa_rev", "1", "", 0.3),
    ("coverage", str(365 / 30), "", 300 * 365 / 30 / (365 * 2.0)),
    ("multiple_param", "12", "0.025", 0.025 * 1399.0 * 2.0 / (300 * 12)),
])
def test_replicate_rules(rule, ann, param, expected):
    end = dt.date(2025, 1, 1) + dt.timedelta(days=399)
    claim = {"recompute": rule, "window_end": end.isoformat(), "window_days": "30",
             "annualise": ann, "param": param}
    assert audit.replicate(claim, snapshot()) == pytest.approx(expected)


def test_rate_and_none():
    end = dt.date(2025, 1, 1) + dt.timedelta(days=399)
    claim = {"recompute": "rate", "window_end": end.isoformat(), "window_days": "365",
             "annualise": "100", "param": ""}
    assert audit.replicate(claim, snapshot()) == pytest.approx(100 * 365 / 1034.0)
    assert audit.replicate({"recompute": "none"}, snapshot()) is None


def test_canonical_inverts_multiples():
    assert audit.canonical(4.0, {"invert": "1", "scale": "1.0"}) == 0.25
    assert audit.canonical(2.5, {"invert": "0", "scale": "0.01"}) == pytest.approx(0.025)
