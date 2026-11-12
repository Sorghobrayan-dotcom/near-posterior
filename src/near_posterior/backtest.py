"""Rolling-origin backtest of B0, B1, B2 and A_K, and the headline model choice (PREREG 6).

Run: `python -m near_posterior.backtest` writes `results/backtest.json` and
`results/backtest_targets.csv`.
"""

import math

import numpy as np

from near_posterior import coverage, forecast, out, refclass, scoring

HORIZONS = (12, 24)
KS = (30, 60, 120)
EVENTS = (1.0, 2.0, 5.0)
TARGET_LAGS = (3, 6, 9, 12)
MIN_B0_ENTITIES = 20
MIN_ANALOG_ENTITIES = 120
MODELS = ("B0", "B1", "B2") + tuple(f"A_{K}" for K in KS)
CANDIDATES = ("B0",) + tuple(f"A_{K}" for K in KS)


def targets(mom: dict, ov: dict, in_r: np.ndarray) -> np.ndarray:
    """Return the indices of class R moments with an outcome and valid F at the target lags."""
    ok = in_r & refclass.resolved(mom)
    for lag in TARGET_LAGS:
        k = mom["k"] - lag
        lagged = np.zeros(mom["k"].size, dtype=bool)
        inside = k >= 0
        lagged[inside] = ov["valid"][mom["e"][inside], k[inside]]
        ok &= lagged
    return np.flatnonzero(ok)


def analog_mask(mom: dict) -> np.ndarray:
    """Return the mask of moments eligible for the analog pool (PREREG 5), outcome aside."""
    return (mom["F"] >= refclass.ANALOG_MIN_F) & (mom["age"] >= 270) & ~np.isnan(mom["m"])


def covariates(mom: dict, idx) -> np.ndarray:
    """Return the analog covariates (ln F, m, ln a) of the moments idx."""
    return np.column_stack([np.log(mom["F"][idx]), mom["m"][idx], np.log(mom["age"][idx])])


def pools(mom: dict, i: int, h: int, in_r: np.ndarray, ok: np.ndarray | None = None,
          an: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Return (B0 pool, analog pool) indices for target moment i: other entities, t' + h <= tau."""
    ok = refclass.resolved(mom) if ok is None else ok
    an = analog_mask(mom) if an is None else an
    base = ok & (mom["e"] != mom["e"][i]) & (mom["month"] + h <= mom["month"][i])
    return np.flatnonzero(base & in_r), np.flatnonzero(base & an)


def quarterly_changes(ov: dict, e: int, k: int) -> list[float]:
    """Return the entity's most recent consecutive quarterly log changes of F before tau (max 8)."""
    out_ = []
    for q in range(8):
        a, b = k - 3 * q, k - 3 * (q + 1)
        if b < 0 or not (ov["valid"][e, a] and ov["valid"][e, b]):
            break
        out_.append(math.log(ov["F"][e, a] / ov["F"][e, b]))
    return out_


def sample_scores(z: np.ndarray, w: np.ndarray, Y: float) -> dict:
    """Return Brier, CRPS, interval coverage and PIT of a weighted sample forecast."""
    y = max(Y, refclass.FLOOR)
    res = {f"prob_{k:g}": float(np.sum(w[z >= math.log(k)])) for k in EVENTS}
    res.update({f"brier_{k:g}": scoring.brier(res[f"prob_{k:g}"], float(Y >= math.log(k)))
                for k in EVENTS})
    res["crps"] = scoring.crps_sample(z, w, y)
    for level, (a, b) in (("50", (0.25, 0.75)), ("90", (0.05, 0.95))):
        res[f"cov_{level}"] = float(scoring.interval_coverage(
            scoring.weighted_quantile(z, w, a), scoring.weighted_quantile(z, w, b), y))
    res["pit"] = scoring.pit_sample(z, w, y)
    return res


def normal_scores(mu: float, s: float, Y: float) -> dict:
    """Return Brier, CRPS, interval coverage and PIT of a Normal(mu, s^2) forecast."""
    y = max(Y, refclass.FLOOR)
    res = {f"prob_{k:g}": 1.0 - scoring.Phi((math.log(k) - mu) / s) for k in EVENTS}
    res.update({f"brier_{k:g}": scoring.brier(res[f"prob_{k:g}"], float(Y >= math.log(k)))
                for k in EVENTS})
    res["crps"] = scoring.crps_normal(mu, s, y)
    for level, q in (("50", 0.75), ("90", 0.95)):
        half = scoring.normal_quantile(q) * s
        res[f"cov_{level}"] = float(scoring.interval_coverage(mu - half, mu + half, y))
    res["pit"] = scoring.pit_normal(mu, s, y)
    return res


def cluster_interval(values: np.ndarray, groups: np.ndarray) -> tuple[float, float]:
    """Return the 5-95 percentile interval of the plain mean over targets, entities resampled."""
    ents, inv = np.unique(groups, return_inverse=True)
    sums = np.bincount(inv, weights=values, minlength=ents.size)
    n = np.bincount(inv, minlength=ents.size).astype(float)
    rng = np.random.default_rng(forecast.SEED)
    idx = rng.integers(0, ents.size, size=(forecast.RESAMPLES, ents.size))
    means = sums[idx].sum(axis=1) / n[idx].sum(axis=1)
    return float(np.percentile(means, 5)), float(np.percentile(means, 95))


def rolling_origin(panel: dict, h: int, F_near: float, ov: dict | None = None) -> dict:
    """Return per-target scores of every model at horizon h, and the dropped targets."""
    ov = ov if ov is not None else refclass.origin_values(panel)
    mom = refclass.moments(panel, h, ov)
    in_r = refclass.in_class(mom, "R", F_near, panel)
    zf = np.maximum(mom["Y"], refclass.FLOOR)
    ok, an = refclass.resolved(mom), analog_mask(mom)
    rows, dropped = [], []
    for i in targets(mom, ov, in_r):
        e, k = int(mom["e"][i]), int(mom["k"][i])
        tau = refclass.month_start(int(mom["month"][i])).isoformat()
        b0_idx, an_idx = pools(mom, i, h, in_r, ok, an)
        n_b0, n_an = np.unique(mom["e"][b0_idx]).size, np.unique(mom["e"][an_idx]).size
        if n_b0 < MIN_B0_ENTITIES or n_an < MIN_ANALOG_ENTITIES:
            dropped.append({"entity": panel["ids"][e], "tau": tau, "b0_entities": int(n_b0),
                            "analog_entities": int(n_an)})
            continue
        Y = float(mom["Y"][i])
        row = {"entity": panel["ids"][e], "tau": tau, "year": int(tau[:4]), "Y": Y,
               "b0_entities": int(n_b0), "analog_entities": int(n_an)}
        ents, inv = np.unique(mom["e"][b0_idx], return_inverse=True)
        w = 1.0 / np.bincount(inv)[inv] / ents.size
        row["B0"] = sample_scores(zf[b0_idx], w, Y)
        ch = quarterly_changes(ov, e, k)
        mu, s = float(np.mean(ch)), float(np.std(ch, ddof=1))
        s = s if s > 0 else 1e-6
        scale = math.sqrt(h / 3)
        row["n_quarters"] = len(ch)
        row["B1"] = normal_scores(0.0, s * scale, Y)
        row["B2"] = normal_scores(mu * h / 3, s * scale, Y)
        X = covariates(mom, an_idx)
        x0 = covariates(mom, [i])[0]
        for K in KS:
            pick = an_idx[forecast.analogs(x0, X, mom["e"][an_idx], K, mom["month"][an_idx])]
            row[f"A_{K}"] = sample_scores(zf[pick], np.full(K, 1.0 / K), Y)
        rows.append(row)
    return {"h": h, "rows": rows, "dropped": dropped, "candidates": int(len(rows) + len(dropped))}


def aggregate(run: dict, names: tuple = MODELS, base: str = "B0") -> dict:
    """Return mean scores, intervals, differences to the base model, coverage, PIT and scores
    by year, for the models `names`."""
    rows = run["rows"]
    res = {"h": run["h"], "scored": len(rows), "dropped": len(run["dropped"]),
           "candidates": run["candidates"],
           "entities": len({r["entity"] for r in rows})}
    res["sufficient"] = res["scored"] >= 100 and res["entities"] >= 30
    if not rows:
        res["models"] = {}
        return res
    groups = np.array([r["entity"] for r in rows])
    metrics = [f"brier_{k:g}" for k in EVENTS] + ["crps", "cov_50", "cov_90"]
    models = {}
    for name in names:
        m = {}
        for metric in metrics:
            v = np.array([r[name][metric] for r in rows])
            m[metric] = float(v.mean())
            if metric.startswith(("brier", "crps")):
                m[f"{metric}_interval"] = cluster_interval(v, groups)
                if name != base:
                    d = v - np.array([r[base][metric] for r in rows])
                    m[f"{metric}_minus_{base}"] = float(d.mean())
                    m[f"{metric}_minus_{base}_interval"] = cluster_interval(d, groups)
        m["pit"] = scoring.pit([r[name]["pit"] for r in rows])
        years = sorted({r["year"] for r in rows})
        m["by_year"] = {str(y): {"n": sum(1 for r in rows if r["year"] == y),
                                 "crps": float(np.mean([r[name]["crps"] for r in rows if r["year"] == y])),
                                 "brier_2": float(np.mean([r[name]["brier_2"] for r in rows
                                                           if r["year"] == y]))}
                        for y in years}
        models[name] = m
    res["models"] = models
    return res


def select_model(scores: dict) -> dict:
    """Apply the model-choice rule of PREREG 6 to aggregated scores keyed by horizon."""
    for h in ("24", "12"):
        agg = scores[h]
        if agg["sufficient"]:
            means = {m: agg["models"][m]["crps"] for m in CANDIDATES}
            best = min(CANDIDATES, key=lambda m: (means[m], CANDIDATES.index(m)))
            if best == "B0":
                return {"horizon": int(h), "lowest_crps": best, "model": "B0",
                        "difference_interval": [0.0, 0.0],
                        "reason": "B0 has the lowest mean CRPS"}
            lo, hi = agg["models"][best]["crps_minus_B0_interval"]
            model = "B0" if lo <= 0.0 <= hi else best
            reason = (f"{best} has the lowest mean CRPS but the 90 percent interval of its CRPS "
                      "minus B0 contains 0" if model == "B0" else
                      f"{best} has the lowest mean CRPS and the 90 percent interval of its CRPS "
                      "minus B0 excludes 0")
            return {"horizon": int(h), "lowest_crps": best, "model": model,
                    "difference_interval": [lo, hi], "reason": reason}
    return {"horizon": None, "lowest_crps": None, "model": "B0", "difference_interval": None,
            "reason": "no backtest is sufficient; no backtest supports the headline model"}


def run_all(panel: dict, F_near: float) -> tuple[dict, list[list]]:
    """Return the backtest results (both horizons and the choice) and the per-target CSV rows."""
    ov = refclass.origin_values(panel)
    scores, csv_rows, dropped = {}, [], {}
    for h in HORIZONS:
        run = rolling_origin(panel, h, F_near, ov)
        scores[str(h)] = aggregate(run)
        dropped[str(h)] = run["dropped"]
        for r in run["rows"]:
            csv_rows.append([h, r["entity"], r["tau"], r["Y"], r["n_quarters"], r["b0_entities"],
                             r["analog_entities"]] + [r[m][s] for m in MODELS
                                                       for s in ("crps", "brier_2", "pit")])
    res = {"scores": scores, "choice": select_model(scores), "dropped_targets": dropped,
           "F_near": F_near}
    return res, csv_rows


CSV_HEADER = (["h", "entity", "tau", "Y", "n_quarters", "b0_entities", "analog_entities"]
              + [f"{m}_{s}" for m in MODELS for s in ("crps", "brier_2", "pit")])


def main() -> None:
    """Write results/backtest.json and results/backtest_targets.csv; print the choice."""
    panel = refclass.load_panel()
    F_near = coverage.summary(coverage.load())["F_near"]
    res, rows = run_all(panel, F_near)
    out.write_text(out.RESULTS / "backtest.json", out.json_text(res))
    out.write_text(out.RESULTS / "backtest_targets.csv", out.csv_text(CSV_HEADER, rows))
    for h, agg in res["scores"].items():
        crps = {m: round(v["crps"], 4) for m, v in agg.get("models", {}).items()}
        print(f"h={h}: scored={agg['scored']} entities={agg['entities']} dropped={agg['dropped']} "
              f"sufficient={agg['sufficient']} crps={crps}")
    print(f"choice: {res['choice']}")


if __name__ == "__main__":
    main()
