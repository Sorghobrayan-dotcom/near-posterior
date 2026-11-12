"""Read the committed raw files into clean daily series.

The fetch day is always dropped: DefiLlama reports it while it is still filling up.
"""

import datetime as dt
import hashlib
import json
import pathlib

RAW = pathlib.Path(__file__).resolve().parents[2] / "data" / "raw"


def manifest(raw: pathlib.Path = RAW) -> dict:
    """Return the manifest and fail if a raw file no longer matches its recorded sha256."""
    man = json.loads((raw / "manifest.json").read_text(encoding="ascii"))
    for name, meta in man["files"].items():
        digest = hashlib.sha256((raw / f"{name}.json").read_bytes()).hexdigest()
        if digest != meta["sha256"]:
            raise ValueError(f"{name}.json does not match the manifest")
    return man


def llama_daily(name: str, raw: pathlib.Path = RAW) -> list[tuple[dt.date, float]]:
    """Return complete days of a DefiLlama series as (date, value), oldest first."""
    cutoff = dt.datetime.fromisoformat(manifest(raw)["fetched_at"]).date()
    data = json.loads((raw / f"{name}.json").read_text(encoding="utf-8"))
    out = []
    for ts, value in data["totalDataChart"]:
        day = dt.datetime.fromtimestamp(ts, dt.timezone.utc).date()
        if day < cutoff:
            out.append((day, float(value)))
    return out


def nearblocks(field: str, raw: pathlib.Path = RAW) -> list[tuple[dt.date, str]]:
    """Return complete days of one NearBlocks chart field as (date, raw string), oldest first."""
    cutoff = dt.datetime.fromisoformat(manifest(raw)["fetched_at"]).date()
    data = json.loads((raw / "nearblocks_charts.json").read_text(encoding="utf-8"))
    out = []
    for row in data["charts"]:
        day = dt.date.fromisoformat(row["date"][:10])
        if day < cutoff:
            out.append((day, row[field]))
    return sorted(out)


def supply(raw: pathlib.Path = RAW) -> list[tuple[dt.date, float]]:
    """Return NEAR total supply in NEAR (yoctoNEAR / 1e24) as (date, value), oldest first."""
    return [(d, int(v) / 10**24) for d, v in nearblocks("total_supply", raw)]


def price(raw: pathlib.Path = RAW) -> list[tuple[dt.date, float]]:
    """Return the NEAR price in USD as (date, value), oldest first."""
    return [(d, float(v)) for d, v in nearblocks("near_price", raw)]


def add_months(day: dt.date, months: int) -> dt.date:
    """Return `day` moved by `months` calendar months, the day clamped to the month's length."""
    y, m = divmod(day.month - 1 + months, 12)
    year, month = day.year + y, m + 1
    nxt = dt.date(year + month // 12, month % 12 + 1, 1)
    return dt.date(year, month, min(day.day, (nxt - dt.timedelta(days=1)).day))


def window_sum(series: list[tuple[dt.date, float]], end: dt.date, days: int) -> float:
    """Sum the values of the `days` days ending on `end`, and fail if one is missing."""
    start = end - dt.timedelta(days=days - 1)
    picked = {d: v for d, v in series if start <= d <= end}
    if len(picked) != days:
        raise ValueError(f"{days - len(picked)} missing days between {start} and {end}")
    return sum(picked.values())
