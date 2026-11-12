"""Download the reference panel once, under PREREG section 2.2, into data/refclass/.

Run once with network access: `python -m near_posterior.refclass_fetch`.
The panel is frozen afterwards; `python -m near_posterior.refclass_fetch --merge` rebuilds the
merged files offline from the stored raw entries.
"""

import csv
import datetime as dt
import gzip
import hashlib
import http.client
import io
import json
import math
import sys
import time
import urllib.request

from near_posterior import out

REF = out.ROOT / "data" / "refclass"
OVERVIEW_URL = ("https://api.llama.fi/overview/fees?excludeTotalDataChart=true"
                "&excludeTotalDataChartBreakdown=true&dataType=dailyFees")
HISTORY_URL = ("https://api.llama.fi/summary/fees/{slug}?dataType=dailyFees"
               "&excludeTotalDataChartBreakdown=true")
TARGET = "near-intents"
MIN_TOTAL = 1_000_000
MAX_MISSING = 0.05


def get(url: str, tries: int = 3) -> bytes:
    """Return the body of a GET request, retrying `tries` times with a growing pause."""
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "near-posterior/0.1"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except (OSError, http.client.HTTPException) as exc:
            last = exc
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"{tries} attempts failed: {last}")


def fetch_overview() -> bytes:
    """Return the raw body of the DefiLlama fees overview."""
    body = get(OVERVIEW_URL)
    json.loads(body)
    return body


def universe(overview: dict) -> list[dict]:
    """Return the universe entries of PREREG 2.2, sorted by slug, without the target."""
    keep = [p for p in overview["protocols"]
            if p.get("protocolType") == "protocol" and (p.get("totalAllTime") or 0) >= MIN_TOTAL
            and p.get("slug") != TARGET]
    return sorted(keep, key=lambda p: p["slug"])


def parse_history(body: bytes) -> list[tuple[str, str]]:
    """Return the (ISO date, value text) pairs of a summary body; fail if there are none."""
    chart = json.loads(body).get("totalDataChart") or []
    rows = []
    for ts, value in chart:
        if value is None:
            continue
        day = dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date().isoformat()
        rows.append((day, str(value) if isinstance(value, int) else repr(float(value))))
    if not rows:
        raise ValueError("empty totalDataChart")
    return rows


def fetch_history(slug: str) -> list[tuple[str, str]]:
    """Return the daily fee history of one slug as (ISO date, value text)."""
    return parse_history(get(HISTORY_URL.format(slug=slug)))


def gz_csv(header: list[str], rows) -> bytes:
    """Return gzip bytes (mtime 0, no file name) of a CSV with LF line ends."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    raw = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
        gz.write(buf.getvalue().encode("ascii"))
    return raw.getvalue()


def read_gz_csv(data: bytes) -> list[list[str]]:
    """Return the rows (header excluded) of a gzip CSV."""
    text = gzip.decompress(data).decode("ascii")
    return list(csv.reader(io.StringIO(text)))[1:]


def merge_entities(entries: list[dict], raw_rows: list[list[str]]) -> tuple[list, list]:
    """Merge entries by parentProtocol (PREREG 2.2); return (entity rows, panel rows)."""
    by_slug = {e["slug"]: e for e in entries}
    groups: dict[str, list[dict]] = {}
    for e in entries:
        groups.setdefault(e.get("parentProtocol") or e["slug"], []).append(e)
    daily: dict[str, dict[str, list[float]]] = {}
    for slug, day, value in raw_rows:
        eid = by_slug[slug].get("parentProtocol") or slug
        daily.setdefault(eid, {}).setdefault(day, []).append(float(value))
    entity_rows, panel_rows = [], []
    for eid in sorted(daily):
        members = groups[eid]
        top = max(members, key=lambda e: (e.get("totalAllTime") or 0, e["slug"]))
        name = eid.split("#", 1)[1] if eid.startswith("parent#") else top["name"]
        days = sorted(daily[eid])
        entity_rows.append([eid, name.encode("ascii", "replace").decode("ascii"),
                            top.get("category") or "", ";".join(sorted(e["slug"] for e in members)),
                            days[0], days[-1], len(days)])
        for d in days:
            panel_rows.append([eid, d, repr(math.fsum(daily[eid][d]))])
    return entity_rows, panel_rows


def write_merged(entries: list[dict], raw_rows: list[list[str]]) -> dict:
    """Write entities.csv and panel.csv.gz; return their file names and bytes."""
    entity_rows, panel_rows = merge_entities(entries, raw_rows)
    files = {
        "entities.csv": out.csv_text(
            ["entity_id", "name", "category", "slugs", "first_day", "last_day", "n_days"],
            entity_rows).encode("ascii"),
        "panel.csv.gz": gz_csv(["entity_id", "date", "fees"], panel_rows),
    }
    for name, data in files.items():
        path = REF / name
        if path.exists() and same_content(name, path.read_bytes(), data):
            continue
        path.write_bytes(data)
    return files


def same_content(name: str, old: bytes, new: bytes) -> bool:
    """True if two versions of a file hold the same content; gzip files are compared after
    decompression, because compressed bytes depend on the platform's zlib build."""
    if name.endswith(".gz"):
        return gzip.decompress(old) == gzip.decompress(new)
    return old == new


def sha256(data: bytes) -> str:
    """Return the hex sha256 of data."""
    return hashlib.sha256(data).hexdigest()


def write_manifest(meta: dict) -> None:
    """Write manifest.json with the sha256 of every data file in data/refclass/."""
    names = sorted(p.name for p in REF.iterdir() if p.name not in ("manifest.json", "excluded.csv"))
    meta["files"] = {n: sha256((REF / n).read_bytes()) for n in names}
    out.write_text(REF / "manifest.json", out.json_text(meta))


def main() -> int:
    """Fetch the overview and every universe history once; write the frozen panel."""
    REF.mkdir(parents=True, exist_ok=True)
    fetched_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    body = fetch_overview()
    (REF / "overview.json.gz").write_bytes(gzip.compress(body, mtime=0))
    entries = universe(json.loads(body))
    print(f"universe: {len(entries)} entries", flush=True)
    raw_rows, missing = [], {}
    for i, e in enumerate(entries, 1):
        try:
            raw_rows.extend([e["slug"], d, v] for d, v in fetch_history(e["slug"]))
        except Exception as exc:  # any failure names the slug in missing.txt
            missing[e["slug"]] = str(exc)[:200]
            print(f"missing {e['slug']}: {missing[e['slug']]}", flush=True)
        if i % 50 == 0:
            print(f"{i}/{len(entries)} fetched, {len(missing)} missing", flush=True)
        time.sleep(0.2)
    (REF / "raw_entries.csv.gz").write_bytes(gz_csv(["slug", "date", "fees"], raw_rows))
    out.write_text(REF / "missing.txt", "".join(f"{s}\n" for s in sorted(missing)))
    out.write_text(REF / "universe.csv", out.csv_text(
        ["slug", "name", "parent", "category", "total_all_time", "fetched"],
        [[e["slug"], e["name"].encode("ascii", "replace").decode("ascii"),
          e.get("parentProtocol") or "", e.get("category") or "", e.get("totalAllTime"),
          0 if e["slug"] in missing else 1] for e in entries]))
    fetched = [e for e in entries if e["slug"] not in missing]
    write_merged(fetched, raw_rows)
    share = len(missing) / len(entries)
    write_manifest({
        "fetched_at": fetched_at, "overview_url": OVERVIEW_URL, "history_url": HISTORY_URL,
        "universe": len(entries), "missing": len(missing), "missing_share": share,
        "missing_reasons": missing, "stop_rule_max_missing": MAX_MISSING,
    })
    print(f"missing: {len(missing)}/{len(entries)} = {share:.4f}")
    if share > MAX_MISSING:
        print("STOP: more than 5 percent of the universe is missing (PREREG 9)")
        return 1
    return 0


def remerge() -> None:
    """Rebuild entities.csv and panel.csv.gz offline from overview and raw entries."""
    overview = json.loads(gzip.decompress((REF / "overview.json.gz").read_bytes()))
    missing = set((REF / "missing.txt").read_text(encoding="ascii").split())
    entries = [e for e in universe(overview) if e["slug"] not in missing]
    write_merged(entries, read_gz_csv((REF / "raw_entries.csv.gz").read_bytes()))
    meta = json.loads((REF / "manifest.json").read_text(encoding="ascii"))
    write_manifest(meta)


if __name__ == "__main__":
    if "--merge" in sys.argv:
        remerge()
    else:
        sys.exit(main())
