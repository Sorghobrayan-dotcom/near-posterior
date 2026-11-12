"""Reference-class moments, classes and outcomes (PREREG sections 2.2, 4.1, 4.2).

Run: `python -m near_posterior.refclass` writes `results/refclass_counts.json` and
`data/refclass/excluded.csv`.
"""

import csv
import datetime as dt
import gzip
import io
import json
import math
import pathlib

import numpy as np

from near_posterior import coverage, out, series

REF = out.ROOT / "data" / "refclass"
LAG_DAYS = 90
MIN_PRESENT = 80
DEAD_GAP = 30
FLOOR = math.log(0.01)
HORIZONS = (12, 24, 36)
CLASSES = ("R", "R_strict", "R_all_ages", "R_trading")
TRADING = frozenset({
    "Dexs", "Derivatives", "Bridge", "Cross Chain Bridge", "Bridge Aggregator",
    "Canonical Bridge", "DEX Aggregator", "Perps Aggregator", "Trading App", "Interface",
    "Telegram Bot", "Prediction Market", "Options",
})
ANALOG_MIN_F = 365.0 / 90.0 * 1e6


def month_index(day: dt.date) -> int:
    """Return the month number of a date (year * 12 + month - 1)."""
    return day.year * 12 + day.month - 1


def month_start(m: int) -> dt.date:
    """Return the first day of month number m."""
    return dt.date(m // 12, m % 12 + 1, 1)


def from_rows(entities: list[dict], rows: list[tuple[str, str, float]]) -> dict:
    """Build the panel from entity records and (entity_id, ISO date, fee) rows; apply dead fill."""
    days = sorted({r[1] for r in rows})
    base = dt.date.fromisoformat(days[0])
    D = dt.date.fromisoformat(days[-1]) - dt.timedelta(days=1)
    n = (D - base).days + 1
    ids = sorted(e["entity_id"] for e in entities)
    pos = {eid: i for i, eid in enumerate(ids)}
    fees = np.zeros((len(ids), n))
    present = np.zeros((len(ids), n), dtype=bool)
    for eid, day, value in rows:
        i = (dt.date.fromisoformat(day) - base).days
        if i < n:
            fees[pos[eid], i] = value
            present[pos[eid], i] = True
    dead = []
    first_pos = []
    for e in range(len(ids)):
        idx = np.flatnonzero(present[e])
        last = int(idx[-1]) if idx.size else -1
        if idx.size and (n - 1) - last > DEAD_GAP:
            present[e, last + 1:] = True
            dead.append(ids[e])
        positive = np.flatnonzero(fees[e] > 0)
        first_pos.append(int(positive[0]) if positive.size else -1)
    meta = {e["entity_id"]: e for e in entities}
    return {
        "ids": ids, "base": base, "D": D, "fees": fees, "present": present, "dead": dead,
        "first_pos": np.array(first_pos), "category": [meta[i].get("category", "") for i in ids],
        "name": [meta[i].get("name", i) for i in ids],
    }


def load_panel(ref: pathlib.Path = REF) -> dict:
    """Load data/refclass/entities.csv and panel.csv.gz into a panel (see `from_rows`)."""
    with open(ref / "entities.csv", encoding="ascii", newline="") as fh:
        entities = list(csv.DictReader(fh))
    text = gzip.decompress((ref / "panel.csv.gz").read_bytes()).decode("ascii")
    rows = [(r[0], r[1], float(r[2])) for r in list(csv.reader(io.StringIO(text)))[1:]]
    return from_rows(entities, rows)


def window_value(panel: dict, e: int, end: int) -> tuple[int, float | None]:
    """Return (present days, 365 * mean of present fees) of the 90 days ending at day index end.

    The value is None when the window leaves the panel or has no present day.
    """
    start = end - LAG_DAYS + 1
    if start < 0 or end >= panel["fees"].shape[1]:
        return 0, None
    mask = panel["present"][e, start:end + 1]
    count = int(mask.sum())
    if count == 0:
        return 0, None
    return count, 365.0 * math.fsum(panel["fees"][e, start:end + 1][mask]) / count


def origin_values(panel: dict) -> dict:
    """Return F_j(t) and present counts for every entity and every month start t of the panel."""
    first_m = month_index(panel["base"]) + 1
    last_m = month_index(panel["D"] + dt.timedelta(days=1))
    months = list(range(first_m, last_m + 1))
    n_e = len(panel["ids"])
    F = np.full((n_e, len(months)), np.nan)
    count = np.zeros((n_e, len(months)), dtype=int)
    for k, m in enumerate(months):
        end = (month_start(m) - panel["base"]).days - 1
        for e in range(n_e):
            c, v = window_value(panel, e, end)
            count[e, k] = c
            if v is not None:
                F[e, k] = v
    valid = (count >= MIN_PRESENT) & (F > 0)
    return {"months": months, "F": F, "count": count, "valid": valid}


def outcome(F_t: float, count_u: int, F_u: float | None) -> tuple[str, float]:
    """Return (status, Y) of a moment from its value and its outcome window (PREREG 4.1)."""
    if count_u < MIN_PRESENT or F_u is None:
        return "excluded", math.nan
    if F_u <= 0:
        return "floor", FLOOR
    return "ok", math.log(F_u / F_t)


def moments(panel: dict, h: int, ov: dict | None = None) -> dict:
    """Return every valid moment at horizon h as columns (numpy arrays), PREREG 4.1."""
    ov = ov if ov is not None else origin_values(panel)
    months, F, count, valid = ov["months"], ov["F"], ov["count"], ov["valid"]
    col = {k: [] for k in ("e", "k", "month", "F", "age", "m", "status", "Y")}
    D = panel["D"]
    for e in range(len(panel["ids"])):
        for k, m in enumerate(months):
            if not valid[e, k]:
                continue
            t = month_start(m)
            age = (t - (panel["base"] + dt.timedelta(days=int(panel["first_pos"][e])))).days
            k6 = k - 6
            mom = math.log(F[e, k] / F[e, k6]) if k6 >= 0 and valid[e, k6] else math.nan
            u = series.add_months(t, h)
            if u - dt.timedelta(days=1) > D:
                status, Y = "unresolved", math.nan
            else:
                ku = k + h
                status, Y = outcome(F[e, k], int(count[e, ku]),
                                    None if math.isnan(F[e, ku]) else float(F[e, ku]))
            for key, val in (("e", e), ("k", k), ("month", m), ("F", F[e, k]), ("age", age),
                             ("m", mom), ("status", status), ("Y", Y)):
                col[key].append(val)
    ints = ("e", "k", "month", "age")
    res = {key: np.array(val, dtype=int if key in ints else float)
           for key, val in col.items() if key != "status"}
    res["status"] = np.array(col["status"], dtype="<U10")
    res["h"] = h
    return res


def in_class(mom: dict, spec: str, F_near: float, panel: dict) -> np.ndarray:
    """Return the mask of moments inside class `spec` (scale band and age only, PREREG 4.2)."""
    F, age = mom["F"], mom["age"]
    band = 2.0 if spec == "R_strict" else 3.0
    mask = (F >= F_near / band) & (F <= F_near * band) & (age >= 270)
    if spec != "R_all_ages":
        mask &= age <= 1095
    if spec == "R_trading":
        cats = np.array([panel["category"][e] in TRADING for e in range(len(panel["ids"]))])
        mask &= cats[mom["e"]]
    return mask


def resolved(mom: dict) -> np.ndarray:
    """Return the mask of moments with an outcome Y (status ok or floor)."""
    return (mom["status"] == "ok") | (mom["status"] == "floor")


def counts(panel: dict, F_near: float) -> tuple[dict, list[list]]:
    """Return the class counts by class and horizon, and the excluded-moment rows."""
    ov = origin_values(panel)
    res = {"D": panel["D"].isoformat(), "entities": len(panel["ids"]),
           "dead_filled": len(panel["dead"]), "F_near": F_near, "classes": {}, "moments": {}}
    excluded = []
    for h in HORIZONS:
        mom = moments(panel, h, ov)
        ok = resolved(mom)
        res["moments"][str(h)] = {s: int((mom["status"] == s).sum())
                                  for s in ("ok", "floor", "excluded", "unresolved")}
        res["moments"][str(h)]["valid"] = int(mom["status"].size)
        for spec in CLASSES:
            mask = in_class(mom, spec, F_near, panel) & ok
            res["classes"].setdefault(spec, {})[str(h)] = {
                "entities": int(np.unique(mom["e"][mask]).size), "moments": int(mask.sum())}
        for i in np.flatnonzero(mom["status"] == "excluded"):
            e, k = int(mom["e"][i]), int(mom["k"][i])
            excluded.append([h, panel["ids"][e], month_start(int(mom["month"][i])).isoformat(),
                             int(ov["count"][e, k + h])])
    return res, excluded


def panel_meta(ref: pathlib.Path = REF) -> dict:
    """Return the fetch facts of the frozen panel (universe, missing entries) from its manifest."""
    man = json.loads((ref / "manifest.json").read_text(encoding="ascii"))
    return {k: man[k] for k in ("fetched_at", "universe", "missing", "missing_share")}


def summary(panel: dict, F_near: float) -> tuple[dict, list[list]]:
    """Return the class counts with the panel facts and the stop-rule flag, and excluded rows."""
    res, excluded = counts(panel, F_near)
    res["panel"] = panel_meta()
    res["stop_rule_R_below_30_at_h24"] = res["classes"]["R"]["24"]["entities"] < 30
    return res, excluded


def main() -> None:
    """Write results/refclass_counts.json and data/refclass/excluded.csv; apply the stop rule."""
    panel = load_panel()
    F_near = coverage.summary(coverage.load())["F_near"]
    res, excluded = summary(panel, F_near)
    n_r = res["classes"]["R"]["24"]["entities"]
    out.write_text(out.RESULTS / "refclass_counts.json", out.json_text(res))
    out.write_text(REF / "excluded.csv", out.csv_text(
        ["h", "entity_id", "origin", "present_days_in_outcome_window"], excluded))
    for spec in CLASSES:
        print(spec, {h: res["classes"][spec][h] for h in ("12", "24", "36")})
    print(f"excluded moments: {len(excluded)}")
    if n_r < 30:
        print(f"STOP: class R has {n_r} entities at h = 24 (PREREG 9); R_all_ages becomes primary")


if __name__ == "__main__":
    main()
