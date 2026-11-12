# Engineering specification

`PREREG.md` is the source of truth for every statistical rule. This file says how to build it.
If the two disagree, `PREREG.md` wins and the disagreement is reported in `PROGRESS.md`.

## 1. What the organisers expect (track `thesis`)

From `nearai/near-hackathon-prompt-examples`, `tracks/02-thesis.md` and `HACKATHON.md`:

1. One command that rebuilds every chart from raw data.
2. A static dashboard page: each chart, the query behind it, one plain sentence on what it shows.
3. `THESIS.md`: the claim, the evidence for it, the evidence against it, what result would
   change our mind.
4. Never invent numbers. If a metric cannot be computed, say so in `THESIS.md`.
5. README written for a machine reader: "do X, see Y" steps. Claude Code and Codex screen
   every project first: they check that it runs and does what the README says.

## 2. Hard constraints

- Python >= 3.11, dependency: `numpy` only (dev: `pytest`). No pandas, scipy, matplotlib.
- Works on Windows, macOS and Linux. No `make`, no shell scripts. Entry points are
  `uv run python -m near_posterior.<module>`.
- Network only in `fetch.py` and `refclass_fetch.py`. The build, the verification and the
  tests never touch the network.
- Deterministic: fixed seeds, sorted iteration, no wall-clock values in results except the
  snapshot's `fetched_at`.
- Every file that is served or hashed is pure ASCII with LF line endings
  (`.gitattributes` enforces LF; data files are `-text`).
- A loop that skips an item names it in an output file. Nothing is dropped silently.
- Full offline build in under 5 minutes on a laptop.

## 3. Layout

    PREREG.md  DEVIATIONS.md  THESIS.md (generated)  README.md  LICENSE  PROGRESS.md
    data/raw/                 live NEAR snapshot (refreshed daily) + manifest.json
    data/refclass/            panel.csv.gz, entities.csv, manifest.json, missing.txt, excluded.csv
    data/claims.csv           figures read from other public theses
    results/                  everything computed (json/csv), committed
    site/index.html           static page, inline SVG, no JavaScript dependency
    history.csv               one row per snapshot: headline probability over time
    src/near_posterior/       code
    tests/                    tests; tests/fixtures/near_20261112/ is the registered snapshot

## 4. Modules

| Module | Functions | Rules |
|---|---|---|
| `fetch.py` (exists) | `main()` | NEAR snapshot + sha256 manifest |
| `series.py` (exists) | `manifest`, `llama_daily`, `window_sum` | add a NearBlocks reader (`supply`, `price`) |
| `coverage.py` | `annualised(x, t, W)`, `issuance(S, t)`, `capture(b, f, t, W)`, `coverage(b, S, p, t, W)`, `required_multiple(C, g_I, g_P, g_kappa)`, `scenario_grid(...)` | PREREG 3 |
| `refclass_fetch.py` | `fetch_overview()`, `fetch_history(slug)`, `merge_entities(...)`, `main()` | PREREG 2.2; polite: 1 request at a time, retry 3 times, then name the slug in `missing.txt` |
| `refclass.py` | `load_panel()`, `window_value(...)`, `moments(panel, h)`, `in_class(moment, spec, F_near)`, `outcome(...)` | PREREG 4.1, 4.2 |
| `forecast.py` | `class_frequency(...)`, `cluster_bootstrap(...)`, `clopper_pearson(x, n, level)`, `analogs(target, pool, K)` | PREREG 4.3, 5 |
| `scoring.py` | `brier`, `crps_sample(z, w, y)`, `crps_normal(mu, s, y)`, `interval_coverage`, `pit` | PREREG 6 |
| `backtest.py` | `rolling_origin(panel, h)`, `select_model(scores)` | PREREG 6 |
| `audit.py` | `replicate(claim)`, `decompose(y, r, r0)`, `dispersion(values)` | PREREG 10 |
| `speccurve.py` | `grid()`, `run()` | PREREG 7 (864 rows) |
| `thesis.py` | `render()` | fills `THESIS.md` from `results/` only |
| `site.py` | `render()` | writes `site/index.html` from `results/` only |
| `build.py` | `main()` | runs everything offline in order, appends `history.csv` |
| `verify.py` | `main()` | rebuilds in memory, compares with committed `results/`, checks every README "see Y" value, prints one `PASS`/`FAIL` line per check, exit code 0 only if all pass |

`clopper_pearson` is exact: invert the binomial CDF by bisection (no scipy).
`Phi` is computed with `math.erf`.

`panel.csv.gz` columns: `entity_id,date,fees` (one row per present day, dead fill not stored).
`entities.csv` columns: `entity_id,name,category,slugs,first_day,last_day,n_days`.
gzip is written with `mtime=0` so that the file hash is reproducible.

## 5. Control values (registered snapshot, `t0 = 2026-11-11`)

Computed independently of this repository. `coverage.py` must reproduce them on
`tests/fixtures/near_20261112` to a relative tolerance of 1e-9. If it does not: stop.

| Quantity | Value |
|---|---|
| `S_t0` | 1311473431.762788 |
| `S_{t0-365}` | 1279706922.253202 |
| `I(t0)` | 31766509.509586 |
| `r` | 0.02482327 (8 decimals) |
| `p_t0` | 3.58413601 |
| sum of `b` since 2026-02-23 (262 days) | 8059471.05 |
| first day with `f > 0` | 2025-05-10 (age 550 days at t0) |
| `F_NEAR = A_90(f, t0)` | 75897110.4444 |
| `A_90(f)` for the window ending 2026-05-11 | 41486463.7222 |
| momentum of NEAR Intents at t0 | 0.60401141 |

| W | `A_W(b)` | `A_W(f)` | `kappa_W` | `C_W` | `1 / C_W` | `k*` (h=24, all constant) |
|---|---|---|---|---|---|---|
| 30 | 21936451.3333 | 70346462.1667 | 0.31183446 | 0.1926692442 | 5.190242 | 5.451118 |
| 90 | 20751795.1667 | 75897110.4444 | 0.27342010 | 0.1822643339 | 5.486537 | 5.762305 |
| 180 | 13894744.9722 | 55928720.8611 | 0.24843667 | 0.1220384269 | 8.194140 | 8.606000 |
| 262 | 11227889.0582 | 51445125.6107 | 0.21824981 | 0.0986152622 | 10.140418 | 10.650103 |

`G_I`: 1.02482327 (h=12), 1.05026273 (h=24), 1.07633369 (h=36).
Values with fewer printed digits are checked to the printed precision.

The reference-class results have no control values: nobody has seen them. Their tests use
synthetic panels with known answers (section 6).

## 6. Tests that must exist

- `coverage`: the control table; the identity of PREREG 3 to 1e-12 on random inputs.
- `refclass`: a hand-built panel of 6 entities covering: a normal entity, a dead entity
  (dead fill, floor outcome), a window with 79 present days (excluded and listed), a merged
  parent with two children, an unresolved moment, an entity outside the scale band.
- `forecast`: `clopper_pearson` against exact values (0/10, 3/10, 10/10 at 90 percent);
  bootstrap reproducible with the seed; analogs keep one moment per entity.
- `scoring`: `crps_sample` of a large Normal sample matches `crps_normal` within 1e-2;
  Brier of a perfect forecast is 0; PIT of a calibrated forecast is uniform (KS-style bound).
- `backtest`: no pool moment with `t' + h > tau`; the target's own entity never in its pool.
- `speccurve`: exactly 864 rows, none with a missing value.
- `thesis`/`site`: regenerating produces byte-identical files; ASCII only.
- `verify`: fails when one committed result is altered.

## 7. THESIS.md (generated) - sections in this order

1. The claim, in one sentence, with the headline probability, its interval, n entities,
   the model used and the snapshot date.
2. Evidence for.
3. Evidence against.
4. What would change our mind (PREREG 8).
5. How other theses measure the same thing (audit, PREREG 10).
6. Backtest: scores of B0, B1, B2, A_K, with intervals, by year. Stated plainly if the
   outside view does not beat trend extrapolation.
7. Specification curve: median, min, max, primary row.
8. What this cannot tell you: no price forecast; frequencies are not mechanisms; DefiLlama
   lists what it lists; "fees" differ across protocols; few independent market cycles;
   capture and issuance are governance decisions; aggregator data, not an on-chain rebuild.
9. Deviations from the pre-registration (or "none").

Every number in `THESIS.md` and `site/index.html` is read from `results/`. No number is typed.

## 8. Static page

One file, inline SVG drawn by Python, no external request. For each chart: title, the chart,
"Query:" the exact command or function that produced it, and one plain sentence.
Charts: coverage over time since 2026-02-23; required multiple by window; distribution of
24-month fee growth in class R with `k*` marked; specification curve; backtest scores by
model; table of the nearest analogs; dispersion of other theses' figures.

## 9. README

- First screen: what it is, the headline number with its date, and the "do X, see Y" table.
- "Do X, see Y": clone, `uv sync`, `uv run python -m near_posterior.verify`
  (see: all lines `PASS`), `uv run python -m near_posterior.build` (see: the headline line
  printed, equal to the one in the README), open `site/index.html`.
- Data sources and why DefiLlama and NearBlocks were used instead of BigQuery or the Intents
  Explorer (no key, no cost, re-runnable by anyone).
- Hackathon disclosure: code written in the window; AI coding assistance was used;
  libraries; no other project submitted by the author.
- Limits (same list as THESIS section 8). No marketing.

## 10. CI

- `check.yml`: on push, `ubuntu-latest` and `windows-latest`: `uv sync`, `pytest -q`,
  `python -m near_posterior.verify`.
- `refresh.yml`: daily cron: `fetch`, `build`, commit `data/raw`, `results/`, `THESIS.md`,
  `site/`, `history.csv`. The reference panel is not refetched.
