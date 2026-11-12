"""Lever table (PREREG_2 S6) and the governance issuance scenario read at a primary source (S10).

Secondary (specified after the primary results).
"""

import json

from near_posterior import forecast, out

GOVERNANCE = out.ROOT / "data" / "governance.json"
H = 24
CAPTURES = ("kappa_90", 0.34, 0.50, 0.75, 1.00)
ISSUANCE = (1.0, 0.75, 0.50, 0.25)
PRICES = (0.5, 1.0, 2.0)
HEADER = ["label", "capture", "kappa_target", "G_kappa", "issuance_factor", "G_I", "G_P",
          "k_star", "P", "P_lo", "P_hi", "entities"]


def cap(t: float, gov: dict) -> float:
    """Return the issuance cap in percent t months after activation (HSP-029 formula)."""
    p = gov["parameters"]
    m = p["ramp_months"]
    return p["cap_start_percent"] - (p["cap_start_percent"] - p["cap_target_percent"]) * \
        min(max(t, 0.0), m) / m


def governance_factor(gov: dict, activation_month: float, h: int = H, steps: int = 1200) -> float:
    """Return the trailing-year issuance at month h relative to the constant-rate path: the mean
    cap over months h-12..h after t0, divided by the starting cap (midpoint rule)."""
    width = 12.0 / steps
    mean = sum(cap(h - 12 + (i + 0.5) * width - activation_month, gov)
               for i in range(steps)) / steps
    return mean / gov["parameters"]["cap_start_percent"]


def cell(sample: dict, label: str, capture, kappa: float, factor: float, g_p: float, C: float,
         r: float) -> list:
    """Return one lever row: k* for the scenario and P_B0(k*) with its interval."""
    target = kappa if capture == "kappa_90" else capture
    g_kappa = target / kappa
    g_i = (1.0 + r) ** (H / 12) * factor
    k = g_i * g_p / g_kappa / C
    res = forecast.b0(sample["Y"], sample["e"], k)
    return [label, str(capture), target, g_kappa, factor, g_i, g_p, k, res["P"],
            res["interval"][0], res["interval"][1], res["entities"]]


def compute(sample: dict, cov: dict, gov: dict | None) -> list[list]:
    """Return the 60 registered cells and, if a governance source exists, its labelled rows."""
    w90 = next(w for w in cov["windows"] if w["window"] == "90")
    C, kappa, r = w90["C"], w90["kappa"], cov["r"]
    rows = [cell(sample, "lever grid", c, kappa, f, p, C, r)
            for c in CAPTURES for f in ISSUANCE for p in PRICES]
    if gov:
        for s in gov["scenarios"]:
            factor = governance_factor(gov, s["activation_month"])
            rows += [cell(sample, s["label"], c, kappa, factor, p, C, r)
                     for c in CAPTURES for p in PRICES]
    return rows


def load_governance() -> dict | None:
    """Return data/governance.json, or None if no primary source was recorded."""
    return json.loads(GOVERNANCE.read_text(encoding="ascii")) if GOVERNANCE.exists() else None
