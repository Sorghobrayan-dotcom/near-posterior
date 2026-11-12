import csv
import re

from near_posterior import forward, out


def test_at_least_eight_forward_claims_with_provenance():
    claims = forward.load()
    assert len(claims) >= 8
    for c in claims:
        assert re.fullmatch(r"[0-9a-f]{40}", c["commit"]) and int(c["line"]) >= 1
        assert float(c["k"]) > 0 and c["quote"] and c["condition"]


def test_horizon_mapping():
    assert forward.horizons("") == (12, 24, 36)
    assert forward.horizons("18") == (12,) and forward.horizons("30") == (24,)
    assert forward.horizons("60") == (36,)


def test_results_follow_the_exceedance_ordering():
    with open(out.RESULTS / "forward_claims.csv", encoding="ascii", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == sum(len(forward.horizons(c["horizon_months"])) for c in forward.load())
    for h in ("12", "24", "36"):
        pairs = sorted((float(r["k"]), float(r["P"])) for r in rows if r["h"] == h)
        assert all(a[1] >= b[1] - 1e-12 for a, b in zip(pairs, pairs[1:]))
