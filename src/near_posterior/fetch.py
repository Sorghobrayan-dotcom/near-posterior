"""Download the raw public series into data/raw/ and record them in a manifest.

Run once with network access: `python -m near_posterior.fetch`.
Everything downstream reads only the committed files, never the network.
"""

import datetime as dt
import hashlib
import json
import pathlib
import time
import urllib.error
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


RPC = "https://archival-rpc.mainnet.fastnear.com"
RPC_OUT = RAW.parent / "rpc" / "supply.json"
GENESIS_HEIGHT = 9820210


def rpc_call(method: str, params: dict) -> dict:
    """Return the `result` of one JSON-RPC call to the archival node ({} if there is none)."""
    body = json.dumps({"jsonrpc": "2.0", "id": "near-posterior", "method": method,
                       "params": params}).encode("ascii")
    req = urllib.request.Request(RPC, data=body, headers={
        "Content-Type": "application/json", "User-Agent": "near-posterior/0.1"})
    for attempt in range(6):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                res = json.loads(resp.read())
            return res.get("result", {})
        except urllib.error.HTTPError as exc:
            if exc.code != 429:
                raise
            time.sleep(10 * (attempt + 1))
    raise RuntimeError("RPC rate limit: 6 attempts failed")


def rpc_header(height: int | None = None) -> dict | None:
    """Return the block header at height (latest final block if None), or None if no block."""
    params = {"finality": "final"} if height is None else {"block_id": height}
    return rpc_call("block", params).get("header")


def existing_header(height: int) -> dict:
    """Return the header of the highest existing block at or below height (heights can skip)."""
    for h in range(height, height - 200, -1):
        header = rpc_header(h)
        if header:
            return header
    raise RuntimeError(f"no block between {height - 199} and {height}")


def last_block_before(ts_ns: int, top: dict) -> dict:
    """Return the header of the last block with a timestamp before ts_ns (binary search)."""
    lo, hi = GENESIS_HEIGHT, top["height"]
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if existing_header(mid)["timestamp"] < ts_ns:
            lo = mid
        else:
            hi = mid
    return existing_header(lo)


def rpc_supply(days: list[dt.date]) -> dict:
    """Return total_supply at the last block of each day and of the day before, from the RPC."""
    top = rpc_header()
    res = {"rpc": RPC, "fetched_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
           .isoformat(), "days": {}}
    for day in days:
        entry = {}
        for label, edge in (("start_of_day", day), ("end_of_day", day + dt.timedelta(days=1))):
            ts = int(dt.datetime(edge.year, edge.month, edge.day, tzinfo=dt.timezone.utc)
                     .timestamp()) * 10**9
            h = last_block_before(ts, top)
            entry[label] = {"height": h["height"], "timestamp_ns": h["timestamp"],
                            "total_supply": h["total_supply"]}
            print(f"{day} {label}: height {h['height']}", flush=True)
        res["days"][day.isoformat()] = entry
    return res


def rpc_main(days: list[str]) -> None:
    """Write data/rpc/supply.json: total supply at the edges of the given days, from the RPC."""
    res = rpc_supply([dt.date.fromisoformat(d) for d in days])
    RPC_OUT.parent.mkdir(parents=True, exist_ok=True)
    RPC_OUT.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n", encoding="ascii",
                       newline="\n")


WALLET = "buybacks.multisignature.near"
WALLET_OUT = RAW.parent / "rpc" / "buyback_wallet.json"
WALLET_WINDOW_DAYS = 90
REGISTERED = RAW.parents[1] / "results" / "registered_forecast.json"


def rpc_wallet(t0: dt.date) -> dict:
    """Return supply and buyback wallet balance at the end of t0 and of t0 - 90 days."""
    top = rpc_header()
    res = {"rpc": RPC, "account": WALLET, "edge": "end_of_day", "t0": t0.isoformat(),
           "window_days": WALLET_WINDOW_DAYS,
           "fetched_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
           "days": {}}
    for day in (t0 - dt.timedelta(days=WALLET_WINDOW_DAYS), t0):
        edge = day + dt.timedelta(days=1)
        ts = int(dt.datetime(edge.year, edge.month, edge.day, tzinfo=dt.timezone.utc)
                 .timestamp()) * 10**9
        h = last_block_before(ts, top)
        acc = rpc_call("query", {"request_type": "view_account", "block_id": h["height"],
                                 "account_id": WALLET})
        if "amount" not in acc:
            raise RuntimeError(f"view_account {WALLET} at {h['height']}: no amount")
        res["days"][day.isoformat()] = {"height": h["height"], "timestamp_ns": h["timestamp"],
                                        "total_supply": h["total_supply"],
                                        "amount": acc["amount"], "locked": acc["locked"]}
        print(f"{day} end_of_day: height {h['height']}", flush=True)
    return res


def wallet_main() -> None:
    """Write data/rpc/buyback_wallet.json, anchored at the registered t0."""
    t0 = json.loads(REGISTERED.read_text(encoding="ascii"))["t0"]
    res = rpc_wallet(dt.date.fromisoformat(t0))
    WALLET_OUT.parent.mkdir(parents=True, exist_ok=True)
    WALLET_OUT.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n", encoding="ascii",
                          newline="\n")


if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["--rpc-supply"]:
        rpc_main(sys.argv[2:])
    elif sys.argv[1:2] == ["--rpc-wallet"]:
        wallet_main()
    else:
        main()
