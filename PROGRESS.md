# Progress

- 2026-11-12: repository scaffold, NEAR snapshot, fixture, PREREG, SPEC, TASKS written. No model code yet.

## T1 - Coverage and required multiple (done)

- `series.py`: NearBlocks readers `supply` (total_supply / 1e24, exact integer division) and
  `price`, fetch day dropped as for DefiLlama; `add_months` (day clamped to month length).
- `coverage.py`: `annualised`, `issuance`, `rate`, `capture`, `coverage`, `required_multiple`,
  `scenario_grid` (216 scenarios = PREREG 7 grid without the class axis), `summary`, `main`.
  `t0` = the last day present in all four series f, b, S, p.
- `out.py`: deterministic JSON/CSV writers (sorted keys, floats rounded to 12 significant
  digits, ASCII, LF).
- Control table of `docs/SPEC.md` section 5: reproduced on `tests/fixtures/near_20261112`, every
  value to rel 1e-9 or to its printed precision (`tests/test_coverage.py`). Identity of PREREG 3
  holds to rel 1e-12 on 50 random inputs.
- Note: NEAR age at t0 is taken as `t0 - first day with f > 0` = 550 days, as in the control
  table. (For panel origins the age is `t - first day`, with the window ending `t - 1`.)

```
> uv run pytest -q
......................                                                   [100%]
22 passed in 0.53s
> uv run python -m near_posterior.coverage
t0=2026-11-11 C_90=0.182264 k*_24=5.762305
```

## T2 - Reference panel fetch (done)

- `refclass_fetch.py`: overview `https://api.llama.fi/overview/fees` (dailyFees), universe =
  `protocolType == "protocol"` and `totalAllTime >= 1e6`, `near-intents` excluded; one history
  request per slug (`/summary/fees/<slug>?dataType=dailyFees&excludeTotalDataChartBreakdown=true`;
  the breakdown flag only drops the per-chain breakdown, `totalDataChart` checked identical on
  `wbtc` before the run), sequential, 0.2 s pause, 3 tries per request.
- Run once, 2026-11-12T10:36:46Z. Universe 981 entries, 797 entities after parent merge,
  772925 raw (slug, day) rows, no duplicate (slug, day). Missing: 0 (`missing.txt` is empty).
  Stop rule (> 5 percent missing): not triggered.
- Stored: `overview.json.gz` (the overview as fetched), `raw_entries.csv.gz` (per slug),
  `universe.csv`, `entities.csv`, `panel.csv.gz` (merged), `manifest.json` (sha256 of each
  file). gzip written with mtime 0. `python -m near_posterior.refclass_fetch --merge` rebuilds
  the merged files offline; the test checks they rebuild byte-identically.
- No reference-class fee value or outcome was looked at during or after the fetch; only counts.

```
> uv run python -m near_posterior.refclass_fetch
universe: 981 entries
...
950/981 fetched, 0 missing
missing: 0/981 = 0.0000
> uv run pytest -q tests/test_refclass_fetch.py tests/test_series.py tests/test_coverage.py
27 passed in 8.43s
```

## T3 - Moments, classes, outcomes (done)

- `refclass.py`: `from_rows`/`load_panel` (day grid from the first panel day to `D`, dead fill
  when the last present day is more than 30 days before `D`), `window_value` (exact `fsum` of the
  present days of the 90-day window), `origin_values` (F and present counts at every month start),
  `outcome`, `moments`, `in_class`, `resolved`, `counts`, `main`.
- Synthetic panel tests (`tests/test_refclass.py`): normal entity, dead entity (dead fill, floor
  outcome), 79 present days (excluded and listed in the excluded rows), 80 days valid, merged
  parent with two children, unresolved moment, entity outside the scale band, age band.
- Real panel: `D = 2026-11-11`, 797 entities, 65 dead-filled, 18707 valid moments.
  Class counts are in `results/refclass_counts.json`; R at h = 24: 75 entities, 525 moments.
  Stop rule (R below 30 entities at h = 24): not triggered. 467 excluded moments listed in
  `data/refclass/excluded.csv` (one row per horizon and moment).
- `data/refclass/excluded.csv` is derived, so the fetch manifest does not list it.

```
> uv run python -m near_posterior.refclass
R {'12': {'entities': 136, 'moments': 980}, '24': {'entities': 75, 'moments': 525}, '36': {'entities': 38, 'moments': 306}}
R_strict {'12': {'entities': 102, 'moments': 599}, '24': {'entities': 57, 'moments': 342}, '36': {'entities': 32, 'moments': 193}}
R_all_ages {'12': {'entities': 139, 'moments': 1213}, '24': {'entities': 76, 'moments': 628}, '36': {'entities': 39, 'moments': 340}}
R_trading {'12': {'entities': 58, 'moments': 431}, '24': {'entities': 38, 'moments': 267}, '36': {'entities': 20, 'moments': 161}}
excluded moments: 467
> uv run pytest -q
58 passed in 13.35s
```

## T4 - Forecast and scoring (done)

- `forecast.py`: `entity_shares`, `class_frequency` (P_B0 = mean over entities of p_j),
  `cluster_bootstrap` (2000 resamples of entities, `default_rng(20261112)`, percentiles 5/95),
  exact `clopper_pearson` (binomial CDF in log space, bisection, no scipy), `b0` (with the
  one-moment-per-entity estimate and the estimate by origin year), `robust_scale`
  (1.4826 * MAD, else std, else 1), `analogs` (one nearest moment per entity, K nearest
  entities, ties on origin month then entity id), `analog_forecast`.
- `scoring.py`: `brier`, `crps_sample` (sorted closed form of the weighted formula),
  `crps_normal`, `Phi` via `math.erf`, `normal_quantile`, `weighted_quantile`,
  `interval_coverage`, `pit_sample` (mid-PIT), `pit_normal`, `pit` (histogram + KS distance).
- Tests: Clopper-Pearson 0/10, 3/10, 10/10 at 90 percent (3/10 gives 0.0872644, 0.6066242) and
  the defining tail equations to 1e-12; bootstrap reproducible; analogs keep one moment per
  entity and the K nearest; CRPS of a 200000-draw Normal sample within 1e-2 of the closed form;
  Brier of a perfect forecast 0; PIT of a calibrated forecast passes a KS bound.

```
> uv run pytest -q tests/test_forecast_scoring.py
14 passed
```

## T5 - Backtest and model choice (done)

- `backtest.py`: `targets` (class R moments with an outcome and valid F at tau - 3, 6, 9, 12
  months), `pools` (other entities only, `t' + h <= tau`, outcome known), B0 (pool moments in
  R, weight 1/n_j'), B1 and B2 (Normal from the entity's own consecutive quarterly log changes
  of F before tau, 4 to 8 of them), A_30/A_60/A_120 (analog pool of PREREG 5 within the
  backtest pool); Brier (k = 1, 2, 5), CRPS on max(Y, ln 0.01) (pool samples floored too),
  coverage of central 50/90 percent intervals, mid-PIT; plain means, cluster bootstrap over
  target entities for each mean and each difference to B0; scores by year of tau;
  `select_model` as PREREG 6. Per-target scores in `results/backtest_targets.csv`.
- Tests (`tests/test_backtest.py`, synthetic 150-entity panel): no pool moment with
  `t' + h > tau`, never the target's own entity, every pool moment resolved; targets have valid
  lags; dropped targets are counted and are exactly the ones below 20 B0 / 120 analog entities;
  the model-choice rule on constructed score tables.
- Result on the real panel (`results/backtest.json`):
  - h = 24: 335 candidate targets, 0 scored, 335 dropped. The largest analog pool any h = 24
    target sees has 39 entities (the rule needs 120). Not sufficient.
  - h = 12: 606 candidates, 158 scored from 40 entities, 448 dropped (all 448 have fewer than
    120 analog entities; 149 also fewer than 20 B0 entities). Sufficient (>= 100 targets,
    >= 30 entities). Every scored target has tau in 2025 (the analog pool reaches 120 entities
    only then), so "by year" has one year.
  - Model choice: h = 12 backtest used; lowest mean CRPS among {B0, A_30, A_60, A_120} is
    A_60; the 90 percent interval of CRPS(A_60) - CRPS(B0) contains 0, so the headline model
    is B0. B1 and B2 (trend extrapolation) score worse than B0 and their difference intervals
    exclude 0.
- Known limit, not a deviation: dead fill is defined on the whole panel (PREREG 2.2), so a pool
  outcome window that ends within 30 days after an entity's last report is filled with zeros
  using knowledge of `D`, not of tau.

```
> uv run python -m near_posterior.backtest
h=12: scored=158 entities=40 dropped=448 sufficient=True crps={'B0': 0.7693, 'B1': 1.0291, 'B2': 1.8874, 'A_30': 0.7837, 'A_60': 0.7666, 'A_120': 0.7749}
h=24: scored=0 entities=0 dropped=335 sufficient=False crps={}
choice: {'horizon': 12, 'lowest_crps': 'A_60', 'model': 'B0', 'difference_interval': [-0.02291261865088892, 0.019007761152790126], 'reason': 'A_60 has the lowest mean CRPS but the 90 percent interval of its CRPS minus B0 contains 0'}
```

## T6 - Many-analysts audit (done)

- Commits pinned with `git ls-remote <url> HEAD` for the 20 candidates of `docs/THESES.md`
  (2026-11-12). File lists read from a blobless shallow clone at that commit (tree only);
  every cited file downloaded from `https://raw.githubusercontent.com/<owner>/<repo>/<sha>/<path>`
  (all HTTP 200). Line numbers and the quoted line in `data/claims.csv` come from those bytes.
- `data/claims.csv`: 32 values from 11 theses (0xrard, AbdeldjalilChougui, ErfanMoheb,
  Lvalentine16, Raindess69, Topeseun, rajeshmullippa-collab, ervhint, semilla1lab, tenxagent,
  HATWHY4041), each with URL, commit, file, line, value, unit, window, end date, stated source,
  definition, the recompute rule, the conversion to a common unit, and the quoted line.
  Not recorded (9 candidates): Alamutu1 and daniels-martins (no result file in the tree);
  minorCoder and Apihpih96 (the result file read has no M1-M5 key); soldanoandrea (the end date
  of its capture share is not in the file read); tobadaniel, bomanaps, EmekaManuel and Alberto
  (not read in detail: 11 theses already met the >= 10 requirement). Their absence says nothing
  about their content.
- `audit.py`: `replicate` (our value under their window, end date and definition), `canonical`
  (common unit; required multiples inverted to coverage), `decompose` (e, s, ln(y/r0) = s + e),
  `dispersion` (IQR of ln y, only if n >= 5), `run`, `main`. Values whose definition needs data
  we do not have (gross minted NEAR, burns, a protocol parameter) or whose window is not stated
  are "not recomputed", with the reason in `note`.
- Since 2026-02-23 DefiLlama revenue equals holders revenue on every day of our snapshot
  (checked: 0 differing days), so revenue- and buyback-based rules agree on those windows.

```
> uv run python -m near_posterior.audit
11 theses, 32 claims: {'reproduced': 20, 'not reproduced': 6, 'not recomputed': 6}
M1 {'n': 7, 'iqr_ln': 0.10343941977268045, 'q25_ln': 16.844291018835538, 'q75_ln': 16.947730438608218}
M2 {'n': 5, 'iqr_ln': 0.2034195718865235, 'q25_ln': -1.2967458561253957, 'q75_ln': -1.0933262842388722}
M3 {'n': 6, 'iqr_ln': 0.1208895487457089, 'q25_ln': -1.7425849160730262, 'q75_ln': -1.6216953673273173}
M4 {'n': 8, 'iqr_ln': 0.026773592723714046, 'q25_ln': 22.03907107650529, 'q75_ln': 22.065844669229005}
M5 {'n': 6, 'iqr_ln': 0.005880542072888684, 'q25_ln': -3.696720176877785, 'q75_ln': -3.690839634804896}
> uv run pytest -q tests/test_audit.py
13 passed
```

## T7 - Specification curve, headline, thesis (done)

- `speccurve.py`: `grid` (864 rows = 4 classes x the 216 scenarios of `coverage.scenario_grid`),
  `run` (P_B0(k*) and its bootstrap interval per row), `summarise`, `verdict` (PREREG 8),
  `break_even`, `what_would_change`, `headline`.
- `thesis.py`: `render` builds the nine sections of SPEC 7 from `results/` and `DEVIATIONS.md`
  only. Facts are sorted into "for" and "against" by their direction relative to the verdict,
  computed from the data, so the text follows the numbers when the snapshot changes.
- `build.py`: `compute` (every generated file in memory, in order), `history_text` (one row per
  snapshot, keyed by `fetched_at`, replaced on rebuild), `main` (writes and prints the headline).
- `refclass.summary` adds the panel fetch facts (universe, missing) and the stop-rule flag to
  `results/refclass_counts.json`.
- Reading of PREREG 8 used (not a deviation): P of the headline model is a step function of k;
  `k50` is the largest k with P > 0.50. The capture, issuance and price factors that move P
  across 0.50 on their own are the ones that bring k* to `k50`; the single-factor rows of the
  registered grid are also listed with their P and whether they cross.
- Result (`results/headline.json`): model B0 (rule of PREREG 6 on the h = 12 backtest), class R,
  75 entities. Primary k* = 5.762. P = 0.053, 90 percent interval 0.022 to 0.091 (cluster
  bootstrap). Verdict: "buybacks are unlikely to cover issuance within 24 months". `k50` = 0.187:
  capture alone would need a capture rate of 8.44 (above 1), issuance a cut of 96.8 percent, or
  the price a factor of 0.032. No single-factor grid row crosses 0.50. Specification curve:
  median 0.074, min 0.000, max 0.294.
- Rebuild twice: `THESIS.md` and every `results/` file byte-identical (`cmp`). ASCII checked.

```
> uv run python -m near_posterior.build
P(buybacks cover NEAR net issuance within 24 months) = 0.053 (90% interval 0.022 to 0.091), model B0, class R, 75 entities, snapshot t0 = 2026-11-11: buybacks are unlikely to cover issuance within 24 months
> uv run pytest -q
75 passed in 8.72s
```

## T8 - Static page (done)

- `svg.py`: inline SVG line, bar (with error bars and per-bar colours), dot and strip charts drawn
  in Python. `site.py`: `render` writes the seven blocks of SPEC 8 from `results/` only
  (coverage over time, k* by window, 24-month growth distribution in class R with k* marked,
  specification curve, backtest scores, table of the 30 nearest analogs, other theses against
  ours), each with its title, the chart, "Query:" and one sentence. `build.py` writes the page.
- Checked in the built-in browser (file URL): seven blocks render. No script, no external
  request (only a relative link to `../THESIS.md`). ASCII. Rebuild is byte-identical (`cmp`).

```
> uv run python -m near_posterior.build
P(buybacks cover NEAR net issuance within 24 months) = 0.053 (90% interval 0.022 to 0.091), model B0, class R, 75 entities, snapshot t0 = 2026-11-11: buybacks are unlikely to cover issuance within 24 months
> uv run pytest -q
78 passed in 8.62s
```

## T9 - Verify command, README, CI (done)

- `verify.py`: rebuilds everything in memory (`build.compute`) and prints one PASS/FAIL line per
  check: the 37 control values of `docs/SPEC.md` section 5 parsed from SPEC itself and checked
  on the registered fixture; sha256 manifests of `data/raw/` and `data/refclass/`; every
  generated file (JSON and CSV compared numerically to rel 1e-9, Markdown and HTML byte for
  byte); the current row of `history.csv`; the README "see Y" values (headline line equal to
  the line printed by `build`, generated README blocks, same headline on the page). Exit code
  0 only if all pass.
- `readme.py`: the README headline and limits blocks are generated by `build` (no number typed
  in the README; rule constants are referred to by PREREG section).
- `.github/workflows/check.yml` (push and PR; ubuntu-latest and windows-latest: `uv sync`,
  `pytest -q`, `verify`) and `refresh.yml` (daily cron: `fetch`, `build`, `verify`, commit the
  NEAR snapshot and generated files; the reference panel is not refetched). Neither was run:
  nothing is pushed.
- First run of `verify` printed one FAIL on the control line: my check required at least 40
  values while SPEC section 5 holds 37; no value was off. Fixed the expected count to 37.
- Tests: `tests/test_verify.py` (committed files pass; altering one number in
  `results/headline.json` or in `results/speccurve.csv` makes exactly that check fail).
- To confirm by the author before submission: the README line "Author's declaration: no other
  project is submitted by the author" (I cannot verify it).

```
> uv run python -m near_posterior.verify
PASS control values of docs/SPEC.md section 5 on the registered snapshot (37 values)
PASS data/raw files match data/raw/manifest.json
PASS data/refclass files match data/refclass/manifest.json
... (16 more PASS lines, one per generated file, history, README)
PASS site/index.html shows the same headline line
exit=0
> uv run pytest -q
82 passed in 14.03s
```
