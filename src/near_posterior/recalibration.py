"""Recalibration by past probability integral transforms (PREREG_3 T2).

Tertiary (specified after the secondary results). G is the empirical distribution function of
the training targets' mid-PIT values; the recalibrated event probability is
P_cal(Y >= y) = 1 - G(F(y)), with F the weighted (mid convention) distribution function of the
class sample.
"""

import math

import numpy as np

from near_posterior import backtest, forecast, recency, refclass, scoring, validation

EVENTS = (1.0, 2.0, 5.0)
TRAIN_LAST_YEAR = recency.CHOICE_LAST_YEAR


def fit(pits) -> np.ndarray:
    """Return the fitted map: the sorted training PIT values."""
    return np.sort(np.asarray(pits, dtype=float))


def G(u, fitted: np.ndarray):
    """Return the empirical distribution function of the training PITs at u."""
    return np.searchsorted(fitted, u, side="right") / fitted.size


def mid_cdf(z: np.ndarray, w: np.ndarray, y: float) -> float:
    """Return F(y) = P(Z < y) + 0.5 P(Z = y) of a weighted sample (weights summing to 1)."""
    return float(np.sum(w[z < y]) + 0.5 * np.sum(w[z == y]))


def target_rows(panel: dict, ov: dict, mom: dict, h: int, H=None) -> list[dict]:
    """Return, for each scored S1 target, its PIT, raw event probabilities and F at ln k."""
    ok = refclass.resolved(mom)
    zf = np.maximum(mom["Y"], refclass.FLOOR)
    rows = []
    for i in np.flatnonzero(validation.target_mask(mom, ov)):
        tau = int(mom["month"][i])
        cls = validation.class_mask(mom, ok, int(mom["e"][i]), tau, float(mom["F"][i]),
                                    float(mom["age"][i]), h)
        if np.unique(mom["e"][cls]).size < validation.MIN_CLASS_ENTITIES:
            continue
        idx = np.flatnonzero(cls)
        z = zf[idx]
        w = recency.weights(mom["e"][idx], mom["month"][idx], tau, H)
        Y = float(mom["Y"][i])
        rows.append({
            "entity": panel["ids"][int(mom["e"][i])], "year": refclass.month_start(tau).year,
            "Y": Y, "pit": scoring.pit_sample(z, w, max(Y, refclass.FLOOR)),
            "raw": {f"{k:g}": float(np.sum(w[z >= math.log(k)])) for k in EVENTS},
            "F": {f"{k:g}": mid_cdf(z, w, math.log(k)) for k in EVENTS},
        })
    return rows


def scores(rows: list[dict], fitted: np.ndarray | None) -> list[dict]:
    """Return per-target event probabilities, Brier scores and PIT, raw or recalibrated."""
    res = []
    for r in rows:
        if fitted is None:
            prob = r["raw"]
            pit = r["pit"]
        else:
            prob = {k: float(1.0 - G(f, fitted)) for k, f in r["F"].items()}
            pit = float(G(r["pit"], fitted))
        s = {"entity": r["entity"], "year": r["year"], "Y": r["Y"], "pit": pit}
        for k in EVENTS:
            key = f"{k:g}"
            s[f"prob_{key}"] = prob[key]
            s[f"brier_{key}"] = scoring.brier(prob[key], float(r["Y"] >= math.log(k)))
        s["cov_50"] = float(0.25 <= pit <= 0.75)
        s["cov_90"] = float(0.05 <= pit <= 0.95)
        res.append(s)
    return res


def describe(sc: list[dict]) -> dict:
    """Return mean Brier, PIT-based coverage, the KS distance and the reliability tables."""
    rel_rows = [{"entity": s["entity"], "Y": s["Y"], "m": s} for s in sc]
    res = {f"brier_{k:g}": float(np.mean([s[f"brier_{k:g}"] for s in sc])) for k in EVENTS}
    res.update(cov_50=float(np.mean([s["cov_50"] for s in sc])),
               cov_90=float(np.mean([s["cov_90"] for s in sc])),
               ks=scoring.pit([s["pit"] for s in sc])["ks"],
               reliability=validation.reliability(rel_rows, ("m",))["m"])
    return res


def compare(raw: list[dict], cal: list[dict]) -> dict:
    """Return differences (recalibrated - raw) with cluster-bootstrap intervals over entities."""
    groups = np.array([s["entity"] for s in raw])
    res = {}
    for k in EVENTS:
        d = np.array([c[f"brier_{k:g}"] - r[f"brier_{k:g}"] for c, r in zip(cal, raw)])
        res[f"brier_{k:g}"] = {"mean": float(d.mean()),
                               "interval": list(backtest.cluster_interval(d, groups))}
    ents, inv = np.unique(groups, return_inverse=True)
    rng = np.random.default_rng(forecast.SEED)
    pr, pc = np.array([s["pit"] for s in raw]), np.array([s["pit"] for s in cal])
    diffs = []
    for _ in range(forecast.RESAMPLES):
        pick = np.concatenate([np.flatnonzero(inv == j)
                               for j in rng.integers(0, ents.size, ents.size)])
        diffs.append(scoring.pit(pc[pick].tolist())["ks"] - scoring.pit(pr[pick].tolist())["ks"])
    res["ks"] = {"mean": float(scoring.pit(pc.tolist())["ks"] - scoring.pit(pr.tolist())["ks"]),
                 "interval": [float(np.percentile(diffs, 5)), float(np.percentile(diffs, 95))]}
    return res


def improves(diff: dict) -> bool:
    """Rule used by the thesis: recalibration improves the held-out scores if the mean Brier
    falls for k = 1, 2 and 5, no Brier interval is above 0, and at least one is below 0."""
    b = [diff[f"brier_{k:g}"] for k in EVENTS]
    return (all(x["mean"] < 0 for x in b) and not any(x["interval"][0] > 0 for x in b)
            and any(x["interval"][1] < 0 for x in b))


def near_p_cal(rows: list[dict], F_R: float) -> dict:
    """Return P_cal = 1 - G(F_R) with G from all rows, and its interval (targets' entities
    resampled, G refitted)."""
    pits = np.array([r["pit"] for r in rows])
    groups = np.array([r["entity"] for r in rows])
    ents, inv = np.unique(groups, return_inverse=True)
    rng = np.random.default_rng(forecast.SEED)
    boot = []
    for _ in range(forecast.RESAMPLES):
        pick = np.concatenate([np.flatnonzero(inv == j)
                               for j in rng.integers(0, ents.size, ents.size)])
        boot.append(1.0 - float(G(F_R, fit(pits[pick]))))
    return {"P_cal": 1.0 - float(G(F_R, fit(pits))), "F_R": F_R,
            "interval": [float(np.percentile(boot, 5)), float(np.percentile(boot, 95))],
            "targets": int(pits.size), "entities": int(ents.size)}


def class_r_cdf(panel: dict, mom: dict, F_near: float, k: float, H, t0_month: int) -> float:
    """Return F_R(ln k): the weighted mid distribution function of class R at ln k."""
    mask = refclass.in_class(mom, "R", F_near, panel) & refclass.resolved(mom)
    z = np.maximum(mom["Y"][mask], refclass.FLOOR)
    w = recency.weights(mom["e"][mask], mom["month"][mask], t0_month, H)
    return mid_cdf(z, w, math.log(k))


def compute(panel: dict, ov: dict, moms: dict, F_near: float, t0_month: int, k_star: dict,
            H_star: str) -> dict:
    """Return results/recalibration.json."""
    res = {"label": recency.TERTIARY,
           "convention": "PIT and F use the mid convention; coverage is PIT-based for raw and "
                         "recalibrated forecasts alike; raw event probabilities are the S1 ones",
           "models": {}}
    variants = [("C0", None)] + ([(f"C_{H_star}", int(H_star))] if H_star != "inf" else [])
    for name, H in variants:
        r12 = target_rows(panel, ov, moms[12], 12, H)
        r24 = target_rows(panel, ov, moms[24], 24, H)
        train = [r for r in r12 if r["year"] <= TRAIN_LAST_YEAR]
        test = [r for r in r12 if r["year"] > TRAIN_LAST_YEAR]
        g12 = fit([r["pit"] for r in train])
        raw_t, cal_t = scores(test, None), scores(test, g12)
        g24 = fit([r["pit"] for r in r24])
        raw24, cal24 = scores(r24, None), scores(r24, g24)
        diff = compare(raw_t, cal_t)
        m = {"held_out_12": {"fitted_on": f"origins up to {TRAIN_LAST_YEAR}",
                             "train_targets": len(train), "test_targets": len(test),
                             "test_entities": len({r["entity"] for r in test}),
                             "raw": describe(raw_t), "recalibrated": describe(cal_t),
                             "difference": diff, "improves": improves(diff)},
             "in_sample_24": {"note": "G fitted on all 24-month targets (origins "
                                      + ", ".join(sorted({str(r["year"]) for r in r24}))
                                      + "); no later origin to test it on",
                              "targets": len(r24), "raw": describe(raw24),
                              "recalibrated": describe(cal24)},
             "near": {}}
        for h, rows in (("12", r12), ("24", r24)):
            F_R = class_r_cdf(panel, moms[int(h)], F_near, k_star[h], H, t0_month)
            m["near"][h] = dict(near_p_cal(rows, F_R), k_star=k_star[h],
                                tested_out_of_sample=h == "12")
        res["models"][name] = m
    return res
