import datetime as dt
import math

from near_posterior import refclass, within


def days(a, b):
    """Return the ISO dates from a to b inclusive."""
    return [(a + dt.timedelta(days=i)).isoformat() for i in range((b - a).days + 1)]


def test_crosses_at_month_10_and_falls_back_by_month_24():
    spike = set(days(dt.date(2021, 8, 1), dt.date(2021, 10, 31)))
    rows = [("x", d, 20000.0 if d in spike else 1000.0)
            for d in days(dt.date(2020, 1, 1), dt.date(2023, 1, 2))]
    panel = refclass.from_rows([{"entity_id": "x", "name": "x", "category": "Dexs"}], rows)
    ov = refclass.origin_values(panel)
    mom = refclass.moments(panel, 24, ov)
    i = [j for j in range(mom["e"].size)
         if refclass.month_start(int(mom["month"][j])) == dt.date(2021, 1, 1)][0]
    k = int(mom["k"][i])
    C = 1 / 15
    assert within.first_crossing(ov, 0, k, 24, C, 0.0) == 10
    assert mom["status"][i] == "ok" and mom["Y"][i] < math.log(15)
    assert within.first_crossing(ov, 0, k, 9, C, 0.0) is None
    assert within.first_crossing(ov, 0, k, 24, 1 / 25, 0.0) is None
