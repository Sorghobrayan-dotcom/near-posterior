"""Second route for total supply: NEAR archival RPC block headers against NearBlocks (task T10).

`python -m near_posterior.fetch --rpc-supply <day> <day>` stores the RPC values once in
`data/rpc/supply.json`; this module compares them offline with the NearBlocks snapshot.
"""

import datetime as dt

from near_posterior import out

RPC_FILE = out.ROOT / "data" / "rpc" / "supply.json"


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
