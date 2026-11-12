"""Method validation with target-centred classes (PREREG_2 S1) and the class R backtest without
the analog-pool condition (PREREG_2 S2).

Secondary (specified after the primary results).
"""

import numpy as np

from near_posterior import backtest, refclass

HORIZONS = (12, 24)
MIN_CLASS_ENTITIES = 20
AGE_LO, AGE_HI, AGE_REF = 270.0, 1095.0, 550.0
SCALE = 3.0
MODELS = ("C0", "B1", "B2")
BINS = {"2": (0.0, 0.05, 0.10, 0.20, 0.40, 1.0), "5": (0.0, 0.02, 0.05, 0.10, 1.0)}


def target_mask(mom: dict, ov: dict) -> np.ndarray:
    """Return the S1 targets: resolved, 90-day fees >= 1M USD, age >= 270, valid lags."""
    ok = refclass.resolved(mom) & (mom["F"] >= refclass.ANALOG_MIN_F) & (mom["age"] >= 270)
    for lag in backtest.TARGET_LAGS:
        k = mom["k"] - lag
        lagged = np.zeros(mom["k"].size, dtype=bool)
        inside = k >= 0
        lagged[inside] = ov["valid"][mom["e"][inside], k[inside]]
        ok &= lagged
    return ok


def class_mask(mom: dict, ok: np.ndarray, e: int, month: int, F: float, age: float,
               h: int) -> np.ndarray:
    """Return the class of a target: other entities, t' + h <= tau, resolved, scale and age
    bands centred on the target (S1)."""
    return (ok & (mom["e"] != e) & (mom["month"] + h <= month)
            & (mom["F"] >= F / SCALE) & (mom["F"] <= F * SCALE)
            & (mom["age"] >= age * AGE_LO / AGE_REF) & (mom["age"] <= age * AGE_HI / AGE_REF))


def class_weights(e: np.ndarray) -> np.ndarray:
    """Return weights 1 / n_j' normalised to sum to 1 (each entity has equal total weight)."""
    _, inv, n = np.unique(e, return_inverse=True, return_counts=True)
    return 1.0 / n[inv] / n.size


def score_target(mom: dict, ov: dict, zf: np.ndarray, i: int, cls: np.ndarray, h: int,
                 c_name: str) -> dict:
    """Return the scores of the class sample (named c_name), B1 and B2 for target i."""
    Y = float(mom["Y"][i])
    e, k = int(mom["e"][i]), int(mom["k"][i])
    idx = np.flatnonzero(cls)
    row = {c_name: backtest.sample_scores(zf[idx], class_weights(mom["e"][idx]), Y)}
    ch = backtest.quarterly_changes(ov, e, k)
    mu, s = float(np.mean(ch)), float(np.std(ch, ddof=1))
    s = s if s > 0 else 1e-6
    scale = np.sqrt(h / 3)
    row["B1"] = backtest.normal_scores(0.0, s * scale, Y)
    row["B2"] = backtest.normal_scores(mu * h / 3, s * scale, Y)
    row["n_quarters"] = len(ch)
    return row


def reliability(rows: list[dict], names: tuple) -> dict:
    """Return reliability tables: per model, event and forecast bin, the number of targets and
    entities, the mean forecast and the observed frequency."""
    res = {}
    for name in names:
        res[name] = {}
        for k, edges in BINS.items():
            table = []
            for lo, hi in zip(edges[:-1], edges[1:]):
                sel = [r for r in rows if lo <= r[name][f"prob_{k}"] < hi
                       or (hi == 1.0 and r[name][f"prob_{k}"] == 1.0)]
                table.append({
                    "bin": [lo, hi], "targets": len(sel),
                    "entities": len({r["entity"] for r in sel}),
                    "mean_forecast": float(np.mean([r[name][f"prob_{k}"] for r in sel]))
                    if sel else None,
                    "observed": float(np.mean([r["Y"] >= np.log(float(k)) for r in sel]))
                    if sel else None,
                })
            res[name][f"Y_ge_ln{k}"] = table
    return res


def run_s1(panel: dict, ov: dict, moms: dict) -> tuple[dict, list[list]]:
    """Return the S1 results by horizon and the per-target rows."""
    out_, csv_rows = {}, []
    for h in HORIZONS:
        mom = moms[h]
        ok = refclass.resolved(mom)
        zf = np.maximum(mom["Y"], refclass.FLOOR)
        rows, dropped = [], 0
        for i in np.flatnonzero(target_mask(mom, ov)):
            cls = class_mask(mom, ok, int(mom["e"][i]), int(mom["month"][i]), float(mom["F"][i]),
                             float(mom["age"][i]), h)
            n_ent = np.unique(mom["e"][cls]).size
            if n_ent < MIN_CLASS_ENTITIES:
                dropped += 1
                continue
            tau = refclass.month_start(int(mom["month"][i]))
            row = score_target(mom, ov, zf, i, cls, h, "C0")
            row.update({"entity": panel["ids"][int(mom["e"][i])], "tau": tau.isoformat(),
                        "year": tau.year, "Y": float(mom["Y"][i]), "class_entities": int(n_ent),
                        "class_moments": int(cls.sum())})
            rows.append(row)
            csv_rows.append([h, row["entity"], row["tau"], row["Y"], n_ent, int(cls.sum())]
                            + [row[m][s] for m in MODELS for s in CSV_SCORES])
        run = {"h": h, "rows": rows, "dropped": [None] * dropped, "candidates": len(rows) + dropped}
        agg = backtest.aggregate(run, MODELS, "C0")
        agg["origins_by_year"] = {str(y): sum(1 for r in rows if r["year"] == y)
                                  for y in sorted({r["year"] for r in rows})}
        agg["reliability"] = reliability(rows, MODELS)
        b2 = agg["models"]["B2"]["crps_minus_C0_interval"] if rows else None
        agg["C0_beats_B2"] = bool(b2 and b2[0] > 0)
        out_[str(h)] = agg
    return out_, csv_rows


CSV_SCORES = ("crps", "brier_2", "brier_5", "prob_2", "prob_5", "pit")
CSV_HEADER = (["h", "entity", "tau", "Y", "class_entities", "class_moments"]
              + [f"{m}_{s}" for m in MODELS for s in CSV_SCORES])


def run_s2(panel: dict, ov: dict, moms: dict, F_near: float, h: int = 24) -> dict:
    """Return the class R backtest of PREREG 6 with B0, B1, B2 and only the B0-pool condition."""
    mom = moms[h]
    in_r = refclass.in_class(mom, "R", F_near, panel)
    ok = refclass.resolved(mom)
    zf = np.maximum(mom["Y"], refclass.FLOOR)
    rows, dropped = [], 0
    for i in backtest.targets(mom, ov, in_r):
        b0 = ok & in_r & (mom["e"] != mom["e"][i]) & (mom["month"] + h <= mom["month"][i])
        if np.unique(mom["e"][b0]).size < backtest.MIN_B0_ENTITIES:
            dropped += 1
            continue
        tau = refclass.month_start(int(mom["month"][i]))
        row = score_target(mom, ov, zf, i, b0, h, "B0")
        row.update({"entity": panel["ids"][int(mom["e"][i])], "tau": tau.isoformat(),
                    "year": tau.year, "Y": float(mom["Y"][i])})
        rows.append(row)
    run = {"h": h, "rows": rows, "dropped": [None] * dropped, "candidates": len(rows) + dropped}
    agg = backtest.aggregate(run, ("B0", "B1", "B2"), "B0")
    agg["origins_by_year"] = {str(y): sum(1 for r in rows if r["year"] == y)
                              for y in sorted({r["year"] for r in rows})}
    return agg


def compute(panel: dict, ov: dict, moms: dict, F_near: float) -> tuple[dict, list[list]]:
    """Return validation.json content (S1 by horizon and S2) and the S1 per-target rows."""
    s1, rows = run_s1(panel, ov, moms)
    return {"label": "secondary (specified after the primary results)", "S1": s1,
            "S2": run_s2(panel, ov, moms, F_near)}, rows
