"""Second route for total supply: NEAR archival RPC block headers against NearBlocks (task T10).

`python -m near_posterior.fetch --rpc-supply <day> <day>` stores the RPC values once in
`data/rpc/supply.json`; this module compares them offline with the NearBlocks snapshot.
"""

import datetime as dt

from near_posterior import out

RPC_FILE = out.ROOT / "data" / "rpc" / "supply.json"
WALLET_FILE = out.ROOT / "data" / "rpc" / "buyback_wallet.json"


def compare(snap: dict, rpc: dict) -> dict:
    """Return NearBlocks against RPC total supply at each stored day, and the implied issuance."""
    S = snap["S"]
    rows, edge_supply = [], {}
    for day, entry in sorted(rpc["days"].items()):
        d = dt.date.fromisoformat(day)
        for edge in ("start_of_day", "end_of_day"):
            s_rpc = int(entry[edge]["total_supply"]) / 10**24
            edge_supply[(day, edge)] = s_rpc
            rows.append({"day": day, "edge": edge, "height": entry[edge]["height"],
                         "S_rpc": s_rpc, "S_nearblocks": S[d], "diff": S[d] - s_rpc,
                         "rel_diff": (S[d] - s_rpc) / s_rpc})
    d0, d1 = sorted(rpc["days"])
    issuance = {}
    for edge in ("start_of_day", "end_of_day"):
        i_rpc = edge_supply[(d1, edge)] - edge_supply[(d0, edge)]
        i_nb = S[dt.date.fromisoformat(d1)] - S[dt.date.fromisoformat(d0)]
        issuance[edge] = {"I_rpc": i_rpc, "I_nearblocks": i_nb,
                          "rel_diff": (i_nb - i_rpc) / i_rpc,
                          "r_rpc": i_rpc / edge_supply[(d0, edge)],
                          "r_nearblocks": i_nb / S[dt.date.fromisoformat(d0)]}
    closest = min(("start_of_day", "end_of_day"),
                  key=lambda e: sum(abs(r["rel_diff"]) for r in rows if r["edge"] == e))
    return {"rpc": rpc["rpc"], "rpc_fetched_at": rpc["fetched_at"], "days": [d0, d1],
            "supply": rows, "issuance": issuance, "closest_edge": closest}


def onchain_coverage(wallet: dict, cov: dict) -> dict:
    """Return the coverage read from the chain alone, (B(t0) - B(t0 - W)) / (S(t0) - S(t0 - W)),
    next to the model's C_90 on the same date."""
    d0, d1 = sorted(wallet["days"])
    e0, e1 = wallet["days"][d0], wallet["days"][d1]
    S0, S1 = int(e0["total_supply"]) / 10**24, int(e1["total_supply"]) / 10**24
    B0 = (int(e0["amount"]) + int(e0["locked"])) / 10**24
    B1 = (int(e1["amount"]) + int(e1["locked"])) / 10**24
    c = (B1 - B0) / (S1 - S0)
    model = next(d["C_90"] for d in cov["daily"] if d["date"] == wallet["t0"])
    return {"rpc": wallet["rpc"], "rpc_fetched_at": wallet["fetched_at"],
            "account": wallet["account"], "edge": wallet["edge"], "t0": wallet["t0"],
            "window_days": wallet["window_days"], "days": [d0, d1],
            "heights": [e0["height"], e1["height"]], "S": [S0, S1], "B": [B0, B1],
            "dS": S1 - S0, "dB": B1 - B0, "coverage_onchain": c, "C_90_model": model,
            "gap": c - model}
