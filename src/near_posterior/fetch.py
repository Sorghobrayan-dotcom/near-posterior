"""Download the raw public series into data/raw/ and record them in a manifest.

Run once with network access: `python -m near_posterior.fetch`.
Everything downstream reads only the committed files, never the network.
"""

import datetime as dt
import hashlib
import json
import pathlib
import urllib.request

RAW = pathlib.Path(__file__).resolve().parents[2] / "data" / "raw"

SOURCES = {
    "intents_volume": "https://api.llama.fi/summary/dexs/near-intents?dataType=dailyVolume",
    "intents_fees": "https://api.llama.fi/summary/fees/near-intents?dataType=dailyFees",
    "intents_revenue": "https://api.llama.fi/summary/fees/near-intents?dataType=dailyRevenue",
    "intents_holders_revenue": "https://api.llama.fi/summary/fees/near-intents?dataType=dailyHoldersRevenue",
    "nearblocks_charts": "https://api.nearblocks.io/v1/charts",
}


def download(url: str) -> bytes:
    """Return the body of a GET request to url."""
    req = urllib.request.Request(url, headers={"User-Agent": "near-posterior/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def main() -> None:
    """Fetch every source, write it to data/raw/, and write manifest.json."""
    RAW.mkdir(parents=True, exist_ok=True)
    fetched_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    manifest = {"fetched_at": fetched_at, "files": {}}
    for name, url in SOURCES.items():
        body = download(url)
        json.loads(body)
        (RAW / f"{name}.json").write_bytes(body)
        manifest["files"][name] = {
            "url": url,
            "sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body),
        }
        print(f"{name}: {len(body)} bytes")
    (RAW / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="ascii", newline="\n")
    print(f"manifest written, fetched_at={fetched_at}")


if __name__ == "__main__":
    main()
