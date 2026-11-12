"""Coverage of net issuance by buybacks, and the fee growth it requires (PREREG section 3).

Run: `python -m near_posterior.coverage` writes `results/coverage.json` from `data/raw/`.
"""

import datetime as dt
import math
import pathlib

from near_posterior import out, series

BUYBACK_START = dt.date(2026, 2, 23)
HORIZONS = (12, 24, 36)
CAPTURES = ("constant", 0.34, 0.50)
ISSUANCES = ("constant", "half")
PRICES = (0.5, 1.0, 2.0)


def load(raw: pathlib.Path = series.RAW) -> dict:
    """Return the NEAR snapshot: daily dicts f, b, v, S, p, the snapshot time and `t0`."""
    snap = {
        "f": dict(series.llama_daily("intents_fees", raw)),
        "b": dict(series.llama_daily("intents_holders_revenue", raw)),
        "v": dict(series.llama_daily("intents_volume", raw)),
        "S": dict(series.supply(raw)),
        "p": dict(series.price(raw)),
        "fetched_at": series.manifest(raw)["fetched_at"],
    }
    snap["t0"] = min(max(snap[k]) for k in ("f", "b", "S", "p"))
    return snap


def window(x: dict, t: dt.date, W: int) -> list[float]:
    """Return the W daily values of x ending on t, and fail if a day is missing."""
    days = [t - dt.timedelta(days=i) for i in range(W)]
    missing = [d for d in days if d not in x]
    if missing:
        raise ValueError(f"{len(missing)} missing days in the {W}-day window ending {t}")
    return [x[d] for d in days]


def annualised(x: dict, t: dt.date, W: int) -> float:
    """Return A_W(x, t) = 365 * mean of x over the W days ending on t."""
    return 365.0 * math.fsum(window(x, t, W)) / W


def issuance(S: dict, t: dt.date) -> float:
    """Return net issuance I(t) = S_t - S_{t-365} in NEAR per year."""
    return S[t] - S[t - dt.timedelta(days=365)]


def rate(S: dict, t: dt.date) -> float:
    """Return the net issuance rate r = I(t) / S_{t-365}."""
    return issuance(S, t) / S[t - dt.timedelta(days=365)]


def capture(b: dict, f: dict, t: dt.date, W: int) -> float:
    """Return kappa_W(t) = sum(b) / sum(f) over the W days ending on t."""
    return math.fsum(window(b, t, W)) / math.fsum(window(f, t, W))


def coverage(b: dict, S: dict, p: dict, t: dt.date, W: int) -> float:
    """Return C_W(t) = A_W(b, t) / (I(t) * p_t)."""
    return annualised(b, t, W) / (issuance(S, t) * p[t])


def required_multiple(C: float, g_I: float, g_P: float, g_kappa: float) -> float:
    """Return k* = (G_I * G_P / G_kappa) / C, the fee growth G_F needed for coverage >= 1."""
    return (g_I * g_P / g_kappa) / C


def windows(t0: dt.date) -> list[tuple[str, int]]:
    """Return the registered windows (label, W): 30, 90, 180 days and days since BUYBACK_START."""
    return [("30", 30), ("90", 90), ("180", 180), ("since", (t0 - BUYBACK_START).days + 1)]


def first_positive(x: dict) -> dt.date:
    """Return the first day with a value > 0."""
    return min(d for d, v in x.items() if v > 0)


def scenario_grid(snap: dict) -> list[dict]:
    """Return the 216 (W, h, capture, issuance, price) scenarios of PREREG 7 with their k*."""
    b, f, S, p, t0 = snap["b"], snap["f"], snap["S"], snap["p"], snap["t0"]
    r = rate(S, t0)
    rows = []
    for label, W in windows(t0):
        C = coverage(b, S, p, t0, W)
        kappa = capture(b, f, t0, W)
        for h in HORIZONS:
            for cap in CAPTURES:
                g_kappa = 1.0 if cap == "constant" else cap / kappa
                for iss in ISSUANCES:
                    g_I = (1.0 + r) ** (h / 12) * (1.0 if iss == "constant" else 0.5)
                    for g_P in PRICES:
                        rows.append({
                            "window": label, "W": W, "h": h, "capture": str(cap),
                            "issuance": iss, "G_P": g_P, "G_kappa": g_kappa, "G_I": g_I,
                            "C_W": C, "kappa_W": kappa,
                            "k_star": required_multiple(C, g_I, g_P, g_kappa),
                        })
    return rows


def summary(snap: dict) -> dict:
    """Return every coverage quantity of the snapshot at t0, plus daily coverage since buybacks."""
    b, f, S, p, t0 = snap["b"], snap["f"], snap["S"], snap["p"], snap["t0"]
    t365 = t0 - dt.timedelta(days=365)
    r = rate(S, t0)
    g_I = {str(h): (1.0 + r) ** (h / 12) for h in HORIZONS}
    rows = []
    for label, W in windows(t0):
        C = coverage(b, S, p, t0, W)
        rows.append({
            "window": label, "W": W,
            "A_b": annualised(b, t0, W), "A_f": annualised(f, t0, W),
            "kappa": capture(b, f, t0, W), "C": C, "inv_C": 1.0 / C,
            "k_star_h24": required_multiple(C, g_I["24"], 1.0, 1.0),
        })
    first = first_positive(f)
    end6 = series.add_months(t0, -6)
    F_near = annualised(f, t0, 90)
    F_6m = annualised(f, end6, 90)
    daily = []
    d = BUYBACK_START
    while d <= t0:
        daily.append({"date": d.isoformat(), "C_30": coverage(b, S, p, d, 30),
                      "C_90": coverage(b, S, p, d, 90)})
        d += dt.timedelta(days=1)
    return {
        "t0": t0.isoformat(), "fetched_at": snap["fetched_at"],
        "S_t0": S[t0], "S_t0_minus_365": S[t365], "I_t0": issuance(S, t0), "r": r,
        "p_t0": p[t0], "G_I": g_I,
        "buyback_start": BUYBACK_START.isoformat(),
        "buyback_days": (t0 - BUYBACK_START).days + 1,
        "b_sum_since_start": math.fsum(window(b, t0, (t0 - BUYBACK_START).days + 1)),
        "first_fee_day": first.isoformat(), "age_t0": (t0 - first).days,
        "F_near": F_near, "F_6m_end": end6.isoformat(), "F_6m": F_6m,
        "momentum": math.log(F_near / F_6m),
        "windows": rows, "daily": daily,
    }


def main() -> None:
    """Write results/coverage.json from data/raw/ and print the primary coverage."""
    s = summary(load())
    out.write_text(out.RESULTS / "coverage.json", out.json_text(s))
    w90 = next(w for w in s["windows"] if w["window"] == "90")
    print(f"t0={s['t0']} C_90={w90['C']:.6f} k*_24={w90['k_star_h24']:.6f}")


if __name__ == "__main__":
    main()
