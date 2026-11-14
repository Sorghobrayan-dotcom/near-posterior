"""Dated milestones between the registered t0 and the 24-month resolution (descriptive).

The path is the constant-growth line from C_90 at the registered t0 to 1 at t0 + 24 months:
C(m) = C0 ** (1 - m / 24). It is a yardstick to read the coverage before the resolution date,
not a forecast and not part of PREREG.md. `build` writes `results/milestones.json`.
"""

import datetime as dt

from near_posterior import coverage, series

H = 24
MONTHS = (3, 6, 9, 12, 15, 18, 21, 24)


def path(C0: float, t0: dt.date, t: dt.date) -> float:
    """Return the coverage on the constant-growth line from C0 at t0 to 1 at t0 + 24 months."""
    span = (series.add_months(t0, H) - t0).days
    return C0 ** (1 - (t - t0).days / span)


def compute(reg_snap: dict, snap: dict) -> dict:
    """Return the milestone dates, the coverage each needs, and where the snapshot stands."""
    t0 = reg_snap["t0"]
    C0 = coverage.coverage(reg_snap["b"], reg_snap["S"], reg_snap["p"], t0, 90)
    rows = []
    for m in MONTHS:
        due = series.add_months(t0, m)
        row = {"month": m, "date": due.isoformat(), "C_needed": path(C0, t0, due),
               "status": "pending"}
        if snap["t0"] >= due:
            C = coverage.coverage(snap["b"], snap["S"], snap["p"], due, 90)
            row.update(status="ahead" if C >= row["C_needed"] else "behind", C_90=C)
        rows.append(row)
    now = snap["t0"]
    C_now = coverage.coverage(snap["b"], snap["S"], snap["p"], now, 90)
    return {"t0": t0.isoformat(), "C0": C0, "h": H, "milestones": rows,
            "today": {"date": now.isoformat(), "C_90": C_now, "C_path": path(C0, t0, now),
                      "status": "ahead" if C_now >= path(C0, t0, now) else "behind"},
            "label": "descriptive yardstick, not a forecast, not pre-registered"}
