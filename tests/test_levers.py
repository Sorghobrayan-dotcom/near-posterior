import csv
import json

import pytest

from near_posterior import levers, out


def test_governance_factor_matches_the_quoted_ramp():
    gov = levers.load_governance()
    assert gov["url"].startswith("https://gov.near.org/")
    assert levers.cap(0, gov) == pytest.approx(2.5) and levers.cap(24, gov) == pytest.approx(1.6)
    assert levers.cap(-5, gov) == pytest.approx(2.5) and levers.cap(40, gov) == pytest.approx(1.6)
    # trailing year at month 24: mean cap over months 12..24 after activation = 1.825 percent
    assert levers.governance_factor(gov, 0) == pytest.approx(1.825 / 2.5, abs=1e-9)
    assert levers.governance_factor(gov, 3) == pytest.approx((2.5 - 0.9 * 15 / 24) / 2.5,
                                                             abs=1e-9)


def test_lever_table_cells_and_primary_cell():
    with open(out.RESULTS / "levers.csv", encoding="ascii", newline="") as fh:
        rows = list(csv.DictReader(fh))
    grid = [r for r in rows if r["label"] == "lever grid"]
    assert len(grid) == 60 and len(rows) == 60 + 30
    head = json.loads((out.RESULTS / "headline.json").read_text(encoding="ascii"))
    prim = [r for r in grid if r["capture"] == "kappa_90" and float(r["issuance_factor"]) == 1.0
            and float(r["G_P"]) == 1.0]
    assert len(prim) == 1 and float(prim[0]["P"]) == pytest.approx(head["P"], rel=1e-9)
    pairs = sorted((float(r["k_star"]), float(r["P"])) for r in rows)
    assert all(a[1] >= b[1] - 1e-12 for a, b in zip(pairs, pairs[1:]))
