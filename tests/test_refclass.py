import datetime as dt
import math

import numpy as np
import pytest

from near_posterior import refclass, refclass_fetch

START = dt.date(2020, 1, 1)
LAST = dt.date(2023, 1, 2)  # fetch day: the panel end D is 2023-01-01
F_NEAR = 365.0 * 1000


def days(a, b):
    """Return the ISO dates from a to b inclusive."""
    return [(a + dt.timedelta(days=i)).isoformat() for i in range((b - a).days + 1)]


@pytest.fixture(scope="module")
def panel():
    entries = [
        {"slug": "normal", "name": "Normal", "totalAllTime": 9e6, "category": "Dexs"},
        {"slug": "dead", "name": "Dead", "totalAllTime": 9e6, "category": "Lending"},
        {"slug": "gappy", "name": "Gappy", "totalAllTime": 9e6, "category": "Dexs"},
        {"slug": "c1", "name": "C1", "totalAllTime": 8e6, "category": "Dexs", "parentProtocol": "parent#p"},
        {"slug": "c2", "name": "C2", "totalAllTime": 2e6, "category": "Yield", "parentProtocol": "parent#p"},
        {"slug": "big", "name": "Big", "totalAllTime": 9e9, "category": "Dexs"},
    ]
    gap = set(days(dt.date(2021, 12, 1), dt.date(2021, 12, 11)))
    raw = []
    raw += [["normal", d, "1000"] for d in days(START, LAST)]
    raw += [["dead", d, "1000"] for d in days(START, dt.date(2021, 6, 30))]
    raw += [["gappy", d, "1000"] for d in days(START, LAST) if d not in gap]
    raw += [["c1", d, "600"] for d in days(START, LAST)]
    raw += [["c2", d, "400"] for d in days(dt.date(2020, 6, 1), LAST)]
    raw += [["big", d, "1000000"] for d in days(START, LAST)]
    ents, rows = refclass_fetch.merge_entities(entries, raw)
    keys = ["entity_id", "name", "category", "slugs", "first_day", "last_day", "n_days"]
    return refclass.from_rows([dict(zip(keys, r)) for r in ents],
                              [(a, b, float(c)) for a, b, c in rows])


def moment(panel, h, entity, origin):
    """Return the moment of entity at origin as a dict, or None."""
    mom = refclass.moments(panel, h)
    e = panel["ids"].index(entity)
    m = refclass.month_index(origin)
    hit = np.flatnonzero((mom["e"] == e) & (mom["month"] == m))
    if not hit.size:
        return None
    return {k: (v[hit[0]] if isinstance(v, np.ndarray) else v) for k, v in mom.items()}


def test_panel_end_and_dead_fill(panel):
    assert panel["D"] == dt.date(2023, 1, 1)
    assert panel["dead"] == ["dead"]


def test_normal_entity(panel):
    m = moment(panel, 12, "normal", dt.date(2021, 1, 1))
    assert m["status"] == "ok" and m["Y"] == pytest.approx(0.0, abs=1e-12)
    assert m["F"] == pytest.approx(F_NEAR) and m["age"] == 366 and m["m"] == pytest.approx(0.0)


def test_dead_entity_gets_floor(panel):
    m = moment(panel, 12, "dead", dt.date(2021, 1, 1))
    assert m["status"] == "floor" and m["Y"] == pytest.approx(math.log(0.01))


def test_79_present_days_excluded_and_listed(panel):
    m = moment(panel, 12, "gappy", dt.date(2021, 1, 1))
    assert m["status"] == "excluded" and math.isnan(m["Y"])
    assert moment(panel, 12, "gappy", dt.date(2022, 1, 1)) is None
    _, excluded = refclass.counts(panel, F_NEAR)
    assert [12, "gappy", "2021-01-01", 79] in excluded


def test_80_present_days_is_valid(panel):
    e = panel["ids"].index("gappy")
    end = (dt.date(2021, 12, 11) - panel["base"]).days + 80
    assert refclass.window_value(panel, e, end)[0] == 80


def test_merged_parent(panel):
    m = moment(panel, 12, "parent#p", dt.date(2021, 1, 1))
    assert m["F"] == pytest.approx(F_NEAR) and m["status"] == "ok"
    e = panel["ids"].index("parent#p")
    assert panel["category"][e] == "Dexs"
    first = (dt.date(2020, 1, 1) - panel["base"]).days
    assert refclass.window_value(panel, e, first + 89) == (90, pytest.approx(365.0 * 600))


def test_unresolved_moment(panel):
    m = moment(panel, 12, "normal", dt.date(2022, 6, 1))
    assert m["status"] == "unresolved"
    assert moment(panel, 12, "normal", dt.date(2022, 1, 1))["status"] == "ok"


def test_scale_band(panel):
    mom = refclass.moments(panel, 12)
    ok = refclass.resolved(mom)
    names = {panel["ids"][e] for e in mom["e"][refclass.in_class(mom, "R", F_NEAR, panel) & ok]}
    assert "big" not in names and "normal" in names and "dead" in names
    trading = {panel["ids"][e]
               for e in mom["e"][refclass.in_class(mom, "R_trading", F_NEAR, panel) & ok]}
    assert "dead" not in trading and "normal" in trading


def test_age_band(panel):
    mom = refclass.moments(panel, 12)
    young = mom["age"] < 270
    assert young.any()
    assert not (refclass.in_class(mom, "R", F_NEAR, panel) & young).any()
    assert not (refclass.in_class(mom, "R_all_ages", F_NEAR, panel) & young).any()
