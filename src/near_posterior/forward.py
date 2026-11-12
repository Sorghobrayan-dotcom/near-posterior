"""Forward requirements stated by other theses, placed on the base-rate curve (PREREG_2 S9).

Secondary (specified after the primary results). The base rate is about fee growth in class R;
applying it to revenue or volume assumes a constant take rate.
"""

import csv

from near_posterior import forecast, out

CLAIMS = out.ROOT / "data" / "forward_claims.csv"
HORIZONS = (12, 24, 36)
HEADER = ["thesis", "file", "line", "k", "quantity", "horizon_stated", "h", "P", "P_lo", "P_hi",
          "entities", "condition"]
NOTE = ("The base rate is about fee growth in class R; applying it to revenue or volume assumes "
        "a constant take rate. A stated horizon is mapped to the nearest of 12, 24, 36 months "
        "(ties to the shorter); without a stated horizon all three are reported.")


def load() -> list[dict]:
    """Return the rows of data/forward_claims.csv."""
    with open(CLAIMS, encoding="ascii", newline="") as fh:
        return list(csv.DictReader(fh))


def horizons(stated: str) -> tuple:
    """Return the horizons to report: the nearest of 12, 24, 36 to a stated one, else all."""
    if not stated:
        return HORIZONS
    m = float(stated)
    return (min(HORIZONS, key=lambda h: (abs(h - m), h)),)


def run(claims: list[dict], samples: dict) -> list[list]:
    """Return P_B0(k, h) with its interval for every claim and reported horizon."""
    rows = []
    for c in claims:
        k = float(c["k"])
        for h in horizons(c["horizon_months"]):
            s = samples[h]
            res = forecast.b0(s["Y"], s["e"], k)
            rows.append([c["thesis"], c["file"], int(c["line"]), k, c["quantity"],
                         c["horizon_months"], h, res["P"], res["interval"][0],
                         res["interval"][1], res["entities"], c["condition"]])
    return rows
