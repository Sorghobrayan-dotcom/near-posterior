"""The registered forecasts on NEAR: the forecast registry contract and its commitments.

`contract/` holds a NEAR contract with no dependency; `contract/posterior_registry.wasm` is the
deployed build. `node onchain/near.mjs commit <account>` wrote one record per horizon on chain and
`data/onchain/commitments.json` keeps each record with its transaction.

Offline (`verify`): every committed record names the sha256 of the registered forecast and of the
three PREREG files, and these hashes and the forecast numbers equal the files in this repository.
Live (`python -m near_posterior.onchain`, network): the contract code on chain is the committed
wasm, each record read back from the chain is the committed record, and it was written before its
resolution date.
"""

import base64
import datetime as dt
import hashlib
import json
import sys
import urllib.request

from near_posterior import out

FILE = out.ROOT / "data" / "onchain" / "commitments.json"
WASM = out.ROOT / "contract" / "posterior_registry.wasm"
RPC = {"testnet": "https://rpc.testnet.fastnear.com", "mainnet": "https://rpc.mainnet.fastnear.com"}
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def sha256(rel: str) -> str:
    """Return the hex sha256 of a repository file."""
    return hashlib.sha256((out.ROOT / rel).read_bytes()).hexdigest()


def b58(data: bytes) -> str:
    """Return the base58 text of bytes (NEAR code hashes)."""
    n, s = int.from_bytes(data, "big"), ""
    while n:
        n, r = divmod(n, 58)
        s = B58[r] + s
    return "1" * (len(data) - len(data.lstrip(b"\0"))) + s


def offline_checks() -> list[tuple[bool, str]]:
    """Return the checks of the committed records against the files of this repository."""
    if not FILE.exists():
        return [(False, "data/onchain/commitments.json exists")]
    com = json.loads(FILE.read_text(encoding="utf-8"))
    reg = json.loads((out.ROOT / "results" / "registered_forecast.json").read_text(encoding="utf-8"))
    res = [(com["code_sha256"] == sha256("contract/posterior_registry.wasm"),
            "contract/posterior_registry.wasm is the build named in data/onchain/commitments.json")]
    hs = sorted(int(h) for h in reg["forecasts"])
    res.append((sorted(c["h_months"] for c in com["commitments"]) == hs,
                f"one on-chain record per registered horizon ({', '.join(map(str, hs))} months)"))
    for c in com["commitments"]:
        r, f = json.loads(c["record"]), reg["forecasts"][str(c["h_months"])]
        ok = (all(r["sha256"][k] == sha256(k) for k in r["sha256"])
              and r["P"] == f["P"] and r["interval"] == f["interval"]
              and r["k_star"] == f["k_star"] and r["resolution_date"] == f["resolution_date"])
        res.append((ok, f"on-chain record h = {c['h_months']} (index {c['index']}, tx {c['tx']}) "
                        "names the committed forecast and PREREG files"))
    return res


def rpc(network: str, method: str, params: dict) -> dict:
    """Call the NEAR JSON-RPC and return its result."""
    body = json.dumps({"jsonrpc": "2.0", "id": "np", "method": method, "params": params}).encode()
    req = urllib.request.Request(RPC[network], body, {"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.loads(r.read())
    if "error" in j:
        raise RuntimeError(j["error"])
    return j["result"]


def live_checks() -> list[tuple[bool, str]]:
    """Return the checks of the records read back from the chain (network)."""
    com = json.loads(FILE.read_text(encoding="utf-8"))
    net, acct = com["network"], com["contract"]
    acc = rpc(net, "query", {"request_type": "view_account", "finality": "final", "account_id": acct})
    res = [(acc["code_hash"] == b58(hashlib.sha256(WASM.read_bytes()).digest()),
            f"code deployed on {acct} ({net}) is contract/posterior_registry.wasm")]
    for c in com["commitments"]:
        q = rpc(net, "query", {"request_type": "call_function", "finality": "final", "account_id": acct,
                               "method_name": "get",
                               "args_base64": base64.b64encode(str(c["index"]).encode()).decode()})
        got = json.loads(bytes(q["result"]).decode("utf-8"))
        when = dt.datetime.fromtimestamp(got["block_timestamp_ns"] / 1e9, dt.timezone.utc)
        due = dt.date.fromisoformat(json.loads(c["record"])["resolution_date"])
        ok = got["record"] == json.loads(c["record"]) and when.date() < due
        res.append((ok, f"record h = {c['h_months']} read on chain equals the committed record, "
                        f"written at block {got['block_height']} on {when:%Y-%m-%d %H:%M} UTC, "
                        f"before its resolution date {due}"))
    return res


def main(argv=None) -> int:
    """Print one PASS/FAIL line per offline and live check."""
    checks = offline_checks() + live_checks()
    for ok, text in checks:
        print(f"{'PASS' if ok else 'FAIL'} {text}")
    return 0 if all(ok for ok, _ in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
