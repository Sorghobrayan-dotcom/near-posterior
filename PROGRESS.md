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

## Clean-clone check (T1 to T9)

Fresh `git clone` of commit 454d8a2 into a new directory, with `UV_OFFLINE=1`:

```
> uv sync                       (offline, from the uv cache)
 + pytest==9.2.0
> uv run pytest -q
82 passed in 14.69s
> uv run python -m near_posterior.verify
20 lines, all PASS, exit=0
> uv run python -m near_posterior.build
P(buybacks cover NEAR net issuance within 24 months) = 0.053 (90% interval 0.022 to 0.091), model B0, class R, 75 entities, snapshot t0 = 2026-11-11: buybacks are unlikely to cover issuance within 24 months
> git status --short
(empty)
> sha256sum THESIS.md site/index.html history.csv README.md results/* | sha256sum
ccc02b89...  (identical in the clone and in the working repository)
```

Only `fetch.py` and `refclass_fetch.py` import a network module. Not verified: the CI
workflows (never run, nothing pushed); macOS (no machine here).

## Left

- T10 (optional, supply from the NEAR RPC), T11 (optional, governance scenario): see below.
- T12 is for the author (submission, video, public repository, form).

## T10 - Second route for total supply from the NEAR RPC (done, optional)

- `fetch.py --rpc-supply <day> <day>`: binary search on block height for the last block before
  the start and before the end of each UTC day on `https://archival-rpc.mainnet.fastnear.com`
  (0.5 s between requests, retries on HTTP 429: the first attempt hit the rate limit), stores
  heights, timestamps and header `total_supply` in `data/rpc/supply.json`. Run once.
- `rpc_check.py` compares offline with NearBlocks; `build` writes `results/rpc_supply.json`
  and one sentence in THESIS section 9; `verify` checks the file like the others.
- Result: NearBlocks `total_supply` for day D equals the header `total_supply` of the last
  block of D (UTC) exactly, on 2025-11-11 (height 172244004) and 2026-11-11 (height 224135609).
  So `I(t0)` and `r` are reproduced exactly by the RPC. The start-of-day blocks (end of the
  previous day) give r = 0.02480474838807113, the value several other theses publish.

```
> uv run python -m near_posterior.fetch --rpc-supply 2026-11-11 2025-11-11
2026-11-11 start_of_day: height 223988377
2026-11-11 end_of_day: height 224135609
2025-11-11 start_of_day: height 172104797
2025-11-11 end_of_day: height 172244004
> uv run python -m near_posterior.verify
21 lines, all PASS
> uv run pytest -q
83 passed
```

## T11 - Governance issuance scenario (not done)

Not done: it needs the proposal text read at its primary source and a model of when and how a
new issuance parameter would apply, which I did not do. What the registered results already
say: P is non-increasing in k*, and k* is proportional to G_I, so any issuance cut smaller than
the registered "half" row gives a P at most that row's P (`results/speccurve.csv`), below 0.50;
the break-even issuance cut is in `results/headline.json` (`what_would_change.G_I_cut_needed`).

# Second pass (PREREG_2.md, docs/TASKS_V2.md)

## U1 - Wording, limits and unverified claims (done)

- Event wording: "within 24 months" replaced by "at the 24-month mark" in the headline line,
  verdict words (history.csv included), THESIS, README and page. Recorded in `DEVIATIONS.md`
  (wording only; event, thresholds and numbers unchanged).
- Audit status "not reproduced" is now "not reproduced by us", with the sentence that the
  status compares their figure with our recomputation under our reading of their definition.
- Limits added (THESIS, README, page): age in DefiLlama's data; class R mixes fee types, with
  the R_trading primary probability shown next to R (read from `results/speccurve.csv`); dead
  fill uses `D`; regression to the mean in a class selected at a high point.
- README: "Windows: run locally. Linux and macOS: not yet run". `check.yml` adds macos-latest.

```
> uv run python -m near_posterior.build
P(buybacks cover NEAR net issuance at the 24-month mark) = 0.053 (90% interval 0.022 to 0.091), model B0, class R, 75 entities, snapshot t0 = 2026-11-11: buybacks are unlikely to cover issuance at the 24-month mark
> uv run python -m near_posterior.verify
21 lines, all PASS
> uv run pytest -q
83 passed
```

## U2 - Exceedance curve, coverage distribution, ask (S3, S5) (done)

Secondary (specified after the primary results).
- `exceedance.py`: `P_B0(k, h)` of class R on the grid `k = 10^(-2 + i/20)`, i = 0..80,
  h = 12, 24, 36, each with the registered bootstrap (`results/exceedance.csv`, 243 rows);
  entity-weighted lower quantiles of `exp(Y)` and the entity-weighted share of floor outcomes
  (`results/growth_quantiles.json`); per entity and horizon: category, moments, successes at
  the primary k* of that horizon, largest growth and its origin (`results/entities_R.csv`);
  entity-weighted quantiles of `C(h) = C_90(t0) exp(Y) / (1 + r)^(h/12)`
  (`results/coverage_quantiles.json`). `build` writes them, so `verify` checks them.
- `ask.py`: `python -m near_posterior.ask [--k K] [--h H]`; default k = primary k* of h.
- Tests: `ask` at the primary k* returns the registered P, interval and entity count; P, P_lo
  and P_hi non-increasing in k; weighted quantiles.
- Build time rose from about 6 s to about 14 s (243 bootstraps).

```
> uv run python -m near_posterior.ask
Class R, h = 24 months, k = 5.762 (primary k*):
P(24-month fee growth >= k) = 0.053 (90% interval 0.022 to 0.091), 75 entities, 525 moments
Entities that reached it: 9
  ... (9 lines)
Registered headline: P(buybacks cover NEAR net issuance at the 24-month mark) = 0.053 (90% interval 0.022 to 0.091), model B0, class R, 75 entities, snapshot t0 = 2026-11-11: buybacks are unlikely to cover issuance at the 24-month mark
```

## U3 - At any point within the horizon (S4) (done)

Secondary (specified after the primary results).
- `within.py`: `first_crossing` (first month u in 1..h with a valid window and
  `F(t+u)/F(t) >= (1+r)^(u/12) G_P / G_kappa / C_90(t0)`), `compute` on the registered class R
  moments of each horizon, entity-weighted with the registered bootstrap.
- `results/within.json` (primary scenario):
  h = 12: within 0.069 (0.039 to 0.102) vs at month 12 0.054 (0.026 to 0.083);
  h = 24: within 0.138 (0.084 to 0.199) vs at month 24 0.053 (0.022 to 0.091);
  h = 36: within 0.167 (0.081 to 0.259) vs at month 36 0.061 (0.014 to 0.120).
- Test: a synthetic entity crosses the threshold at month 10 and falls back by month 24.

## U4 - Method validation (S1, S2): STOPPED, not committed

Counts computed without reading outcomes, against the expected counts of `docs/TASKS_V2.md`:
- candidates match: h = 12: 2730, h = 24: 1390. S2 matches: 92 targets from 31 entities.
- scored differ: h = 12: 1659 targets, 188 entities, origins 2023 102 / 2024 494 / 2025 1063
  (expected 1636, 187, 97 / 488 / 1051); h = 24: 201 targets, 51 entities, all 2024
  (expected 194, 50).
- My class: pool moments with an outcome (status ok or floor), other entity, `t' + h <= tau`
  (months), `F/3 <= F' <= 3F`, `a*270/550 <= a' <= a*1095/550`; scored if >= 20 entities.
- Variants tried, none reproduces both counts: "> 20" entities; strict band edges; excluded
  moments in the pool; `t' + h < tau`; pool status ok only; pool momentum defined; pool age
  >= 270; pool F >= 1M; and the 32 combinations of the last four with ">= 20" and "> 20".
- Question sent to the session that computed the expected counts; U4 waits for its answer.
  U5 to U7 do not depend on S1 and go on.

## U5 - Lever table and governance scenario (S6, S10) (done)

Secondary (specified after the primary results).
- S10 primary source: the HSP-029 proposal text, first post of its thread on the NEAR
  governance forum (`data/governance.json`: URL, raw URL, date read 2026-11-12, sha256 of the
  raw text, quoted lines). Quoted parameter: `cap(t) = 2.5% - 0.9% x min(t, 24)/24`, t in
  months from activation; "Activation occurs one full quarter after ratification"; frontmatter
  "Status: Succeeded". The ratification date is not in the source, so the scenario rows state
  their assumed activation month: at t0 (earliest bound) and at t0 + 3 months.
- Scenario factor on the constant-rate path: trailing-year issuance at month 24 = mean cap over
  months 12..24 after t0, divided by 2.5 percent: 0.73 (activation at t0), 0.775 (t0 + 3).
- `levers.py`, `results/levers.csv`: 60 registered cells (capture kappa_90, 0.34, 0.50, 0.75,
  1.00 x issuance factor 1, 0.75, 0.50, 0.25 x G_P 0.5, 1, 2) + 2 x 15 labelled HSP-029 rows.
  Highest P of the table: 0.492 (0.401 to 0.580) at capture 1.00, issuance x 0.25, G_P 0.5;
  no cell has P > 0.50. Primary cell = registered headline (test).

## U6 - Class multiverse and cohorts (S7, S8) (done)

Secondary (specified after the primary results).
- `multiverse.py`: 72 specifications at h = 24 and the primary k* (scale q 2, 3, 5 x age band
  [270, 1095], [180, 730], [365, 1460], [270, inf) x entity-equal or moment-equal weighting x
  all / trading / all except the yield-type list). Moment-equal: plain share with a cluster
  bootstrap over entities. `results/class_multiverse.csv` and `.json`: median 0.032, minimum
  0.009, maximum 0.063; 8 specifications have fewer than 30 entities (flagged, kept). The
  primary specification reproduces the headline (test).
- Cohorts (`results/cohorts.json`): leave-one-origin-year-out P: without 2020 0.040, 2021
  0.057, 2022 0.049, 2023 0.039, 2024 0.101. Two-stage bootstrap over (entity, origin year)
  blocks, indicative only: mean block share 0.048, interval 0.014 to 0.118.

## U7 - Forward requirements of other theses (S9) and a wider audit (done)

- `data/claims.csv` now holds 43 values from 17 theses (added, from files already pinned in T6:
  Apihpih96 `FINDINGS.md`, tobadaniel `THESIS.md`, EmekaManuel `THESIS.md`, Alberto
  `THESIS.md`, bomanaps `THESIS.md`, soldanoandrea `thesis/NUMBERS.md`). The first 32 rows are
  byte-identical to T6. Markdown lines are found by an exact substring; quotes are transliterated
  to ASCII (x for the multiplication sign, - for dashes, ~ for "approximately") and cut around
  the value when longer than 300 characters. New recompute rule `coverage_param`
  (buybacks / (parameter x supply x price)). `uv run python -m near_posterior.audit`:
  17 theses, 43 claims: 26 reproduced, 8 not reproduced by us, 9 not recomputed.
- `data/forward_claims.csv`: 12 forward requirements from 9 theses (break-even and net-zero
  multiples of volume, revenue or buybacks, a yield target), each with commit, file, line,
  condition and quote. None states a horizon, so all three horizons are reported.
- `forward.py`, `results/forward_claims.csv` (36 rows): P_B0(k, h) of class R with its
  interval. At h = 24 the requirements of 3.1x to 7.2x map to P between 0.034 and 0.076; the
  1.6x requirement (conditional on a 5 bps contract take) maps to 0.147 (0.092 to 0.209).

## U11 - Resolution (S11) (done; taken before U8 to U10 because U4 waits for an answer)

- `resolve.py`: `registered` computes P_B0(k*) of class R, primary scenario, for h = 12, 24,
  36 from the registered snapshot (`tests/fixtures/near_20261112`) and the frozen panel, so it
  never changes with the daily refresh (`results/registered_forecast.json`); `resolve` gives
  pending, or the outcome (C_90 at t0 + h months >= 1) and the Brier contribution, on the
  current snapshot (`results/resolution.json`); `RESOLUTION.md` (dates, rule, command, status)
  is generated by `build`. Resolution dates: 2027-11-11, 2028-11-11, 2029-11-11.
- Tests: a synthetic later snapshot resolves to 1 (C_90 = 1.001) and to 0 (0.999) with the
  right Brier; before the date it stays pending.

```
> uv run python -m near_posterior.resolve
h = 12: P = 0.054, resolves on 2027-11-11: pending
h = 24: P = 0.053, resolves on 2028-11-11: pending
h = 36: P = 0.061, resolves on 2029-11-11: pending
```

## U4 - still stopped (further checks, counts only)

More variants tried for the S1 class, none gives 1636 / 194: pool restricted to moments with
F valid at t' - 3..12 (1574 / 48), at t' - 12 (1582 / 48), at t' - 3, 6 (1653 / 192), at
t' - 3 (1658 / 201); age-band bounds floored, ceiled, rounded or truncated (1657 to 1662 /
199 to 205); target F from the window ending on tau itself, as for NEAR at t0 (1658 / 199);
F as 365 x (90-day sum) / 90 instead of 365 x mean of present days (1658 / 200).
The S1 and S2 code (`src/near_posterior/validation.py`, and the `backtest.aggregate` change it
needs) is in the working tree, not committed. Waiting for the definition used for the
expected counts. Done meanwhile: U5, U6, U7, U11. Left: U4, then U8, U9, U10, U12, U13.

## U4 - Method validation (S1, S2) (done)

Secondary (specified after the primary results). Unblocked by the reviewer: the expected counts
had been computed with an age band of [a/2, 2a]; under the registered S1 rule the reviewer
recounted 1659 / 188 and 201 / 51, equal to mine. Recorded as an erratum in `DEVIATIONS.md`;
`docs/TASKS_V2.md` U4 counts corrected. `PREREG_2.md` unchanged.
- `validation.py`: S1 targets (outcome, 90-day fees >= 1M USD, age >= 270, valid lags), class
  centred on each target (other entities, `t' + h <= tau`, scale x/3..3x, age
  a*270/550..a*1095/550, >= 20 entities), models C0 (class sample, weight 1/n_j'), B1, B2;
  scores, intervals, by year, reliability tables; S2 = class R with B0, B1, B2 and only the
  B0-pool condition. `backtest.aggregate` takes the model list and the base model;
  `sample_scores` / `normal_scores` also return the event probabilities.
- `results/validation.json`, `results/validation_targets.csv`:
  - S1 h = 12: 2730 candidates, 1659 scored, 188 entities (origins 2023 102, 2024 494,
    2025 1063), sufficient. Mean CRPS: C0 0.995 (0.916 to 1.079), B1 1.117, B2 1.774;
    B1 - C0: 0.086 to 0.160, B2 - C0: 0.654 to 0.909 (C0 beats both).
  - S1 h = 24: 1390 candidates, 201 scored, 51 entities (origins 2024 only), sufficient.
    C0 1.410 (1.200 to 1.640), B1 1.898, B2 4.528; B1 - C0: 0.381 to 0.596,
    B2 - C0: 2.384 to 3.858.
  - Calibration: C0 forecasts more growth than happened. Event "fees at least doubled", bin
    [0.20, 0.40): mean forecast 0.279, observed 0.108 at h = 12 (1328 targets); 0.253 vs
    0.031 at h = 24 (127 targets). Event "at least 5x", bin [0.10, 1]: 0.158 vs 0.022 at
    h = 12; 0.168 vs 0.019 at h = 24.
  - S2 (h = 24): 335 candidates, 92 scored from 31 entities, not sufficient (as expected).
- Tests: no pool moment with `t' + h > tau`, never the target's entity, a target with NEAR's
  scale and age gets exactly class R, the registered counts.
- Build time is now about 21 s.
- `ask --slug <entity_id>` (U2, after U4): the class is centred on that entity's latest valid
  moment with the S1 construction; `parent#` may be omitted; a class below 20 entities is
  flagged. Example: `uv run python -m near_posterior.ask --slug aave --h 24` (8 entities,
  flagged).

## U8 - The thesis as an essay (done)

- `thesis.py` rewritten: twelve sections in the order of TASKS_V2 U8, five-sentence summary,
  every number read from `results/` (generic loader `parse` / `load_results` for every
  results file), sentences chosen from the numbers (direction, even odds, calibration),
  secondary analyses labelled "[secondary (specified after the primary results)]".
  `exceedance` adds P at k = 1, 2, 5, 10 to `results/growth_quantiles.json` for section 3.
- `uv run python -m near_posterior.verify`: 36 PASS, 0 FAIL. `uv run pytest -q`: 102 passed.

## U9 - The page (done)

- `svg.py` rewritten: a `Frame` with linear or log axes, one accent colour and a neutral scale,
  labels on the charts (no colour legend), standalone SVG output.
- `site.py` rewritten: top block (question, headline number large, interval, snapshot date,
  one line on the method, links to `THESIS.md`, `PREREG.md`, `PREREG_2.md`, the headline line);
  explorer (exceedance curve with interval band, k* ticks by window, triangles for the other
  theses' requirements, a cursor; slider over the 81 grid values of k and a 12/24/36 switch,
  data embedded from `results/exceedance.csv` and `results/entities_R.csv`; the static text
  shows the primary k* result, so the page is complete without JavaScript; the only script is
  inline, with no request); charts: coverage since 2026-02-23, coverage distribution at 12/24/36
  months, lever heat map (with the HSP-029 column), calibration of C0 against B2, backtest
  scores (registered and S1), robustness (specification curve, class multiverse, leave one year
  out), cohorts; tables: who reached k*, nearest analogs, other theses (measurements and
  forward requirements); limits. Every block has its "Query:" line and one sentence; sentences
  that state a direction are computed from the results.
- `site/img/exceedance.svg`, `levers.svg`, `calibration.svg`: standalone copies written by
  `build`, so `verify` checks them.
- Checked in the built-in browser at desktop width and at 380 px (no horizontal scroll;
  document width 380). Explorer checked by script: k = 1 at 24 months shows P = 0.205, equal
  to `results/growth_quantiles.json`.
- Screenshots of the first screen: `docs/img/page_1200.png` and `docs/img/page_380.png`, taken
  with Edge headless (`--window-size`; the 380 px one through a 380 px iframe because headless
  Edge enforces a wider minimum window).

```
> uv run python -m near_posterior.verify
39 lines, all PASS
> uv run pytest -q
103 passed
```

## U10 - README, verification report (done)

- README first screen: the generated finding sentence (number and snapshot date), the
  exceedance chart (`site/img/exceedance.svg`), the "do X, see Y" table (now with `ask`,
  `ask --k --h`, `ask --slug`, `resolve`, and `verify --write`), the generated headline line,
  the lever chart (`site/img/levers.svg`). Layout updated (PREREG_2, VERIFICATION, RESOLUTION,
  forward claims, governance, RPC data, images).
- `verify`: new check that `ask` at the primary k* reproduces the registered headline; new
  `--write` option that rewrites `VERIFICATION.md` (every check with its status, and for each
  README claim the check that covers it); a last check that `VERIFICATION.md` is current. The
  three README images and every new result file are generated by `build` and therefore checked.

```
> uv run python -m near_posterior.verify --write
... 41 lines, all PASS, exit=0
> uv run pytest -q
103 passed
```

## U12 - CI, pages, material for the author (done)

- `.github/workflows/pages.yml`: on push to main, publishes the repository with GitHub Pages
  (page at `/near-posterior/site/`, so the relative links to `THESIS.md` and the
  pre-registrations resolve). Works once the repository is public and Pages uses GitHub
  Actions. Not run: nothing is pushed.
- `material.py`, generated by `build` (so checked by `verify`): `docs/DEMO_SCRIPT.md` (75 seconds,
  seven shots: verify, ask, explorer, who reached k*, lever heat map, calibration,
  pre-registration and resolution date) and `docs/X_POST.md` (three-post draft: the problem and
  one complete number, how it was made from NEAR's public data with the links, a question). The
  author edits and posts; nothing is sent.

```
> uv run python -m near_posterior.verify --write
43 lines, all PASS, exit=0
> uv run pytest -q
103 passed
```

## U13 - Second route for buybacks (S12): not done

Optional, cut first by the task order. Not attempted: reading the buyback accounts from the
DefiLlama adapter source and their on-chain NEAR balance changes needs more than the time left.

## Clean-clone check of the second pass

Fresh `git clone` of commit 7b1c112 into a new directory, with `UV_OFFLINE=1`:

```
> uv sync && uv run pytest -q
103 passed in 29.46s
> uv run python -m near_posterior.verify
43 lines, all PASS, exit=0
> uv run python -m near_posterior.build
P(buybacks cover NEAR net issuance at the 24-month mark) = 0.053 (90% interval 0.022 to 0.091), model B0, class R, 75 entities, snapshot t0 = 2026-11-11: buybacks are unlikely to cover issuance at the 24-month mark
> git status --short
(empty)
> uv run python -m near_posterior.ask
... Registered headline: P(buybacks cover NEAR net issuance at the 24-month mark) = 0.053 ...
> uv run python -m near_posterior.resolve
... h = 36: P = 0.061, resolves on 2029-11-11: pending
```

Second pass status: U1 to U12 committed; U13 (optional) not done. Not verified: CI on Linux
and macOS, GitHub Pages (nothing pushed), the page in browsers other than Edge and the built-in
browser.

## U14 - Form fixes after review (done)

The reviewer recomputed the second pass independently and found no calculation error. Five form
fixes, no number, rule or result file changed (`git diff -- results/ history.csv` is empty):
1. `docs/X_POST.md`: post 1 now starts with "Built at NEAR HACKATHON", keeps `@NEARProtocol` and
   `#NEARHackathon`, 270 characters (test: <= 280).
2. Page top and README finding show the headline as a percentage (5.3%, interval 2.2% to 9.1%;
   coverage 18.2%); the exact headline line with 0.053 is unchanged below it (verify and ask
   compare that line).
3. Page: the long bracket label is replaced by a short tag "secondary" (or "partly secondary"
   for the backtest and robustness blocks) next to the heading, explained once near the top with
   a link to `PREREG_2.md`. `THESIS.md` keeps the full label.
4. Generated root `index.html` (meta refresh to `site/` plus a plain link), written by `build`
   and checked by `verify`.
5. `THESIS.md` summary: two sentences on what the result means for an investor, chosen from the
   verdict and the lever table (no advice wording, no price view); section 7 calibration as
   tables (model, event, forecast bin, targets, mean forecast, observed).

```
> uv run python -m near_posterior.build
P(buybacks cover NEAR net issuance at the 24-month mark) = 0.053 (90% interval 0.022 to 0.091), ...
> uv run python -m near_posterior.verify --write
44 lines, all PASS, exit=0
> uv run pytest -q
108 passed
```

## U15 - CI fixes after the first CI run (done)

The reviewer pushed a3ffaad: CI passed on Linux and Windows; on macOS one test failed
(`tests/test_refclass_fetch.py::test_panel_matches_entities_and_raw_entries`, 1 failed,
107 passed), because it compared freshly gzip-compressed bytes with the committed ones and
compressed bytes depend on the platform's zlib build.
1. The test now compares the decompressed content. `refclass_fetch.write_merged` (used by
   `refclass_fetch --merge`) keeps a committed file when its content is unchanged
   (`same_content`: gzip files compared after decompression), so a re-merge on another
   platform does not rewrite `panel.csv.gz` or its manifest hash. The sha256 manifest check of
   the committed files is unchanged; no other place re-hashes freshly compressed bytes (`build`
   and `verify` write or compare no gzip file). Checked here: `uv run python -m
   near_posterior.refclass_fetch --merge` leaves `data/` unchanged (`git status` empty).
   Not checked: the macOS run itself (I cannot see CI).
2. `pages.yml`: the deploy job runs only `if: ${{ vars.PAGES_ENABLED == 'true' }}`. The author
   sets the repository variable `PAGES_ENABLED` to `true` (Settings > Secrets and variables >
   Actions > Variables) after enabling GitHub Pages with source "GitHub Actions".
3. README: `check` workflow badge at the top; the OS line says "Linux, Windows and macOS: run by
   CI on every push", with the result left to the badge. `VERIFICATION.md` says the CI result is
   not a verify check.

```
> uv run python -m near_posterior.verify --write
44 lines, all PASS, exit=0
> uv run pytest -q
108 passed
```

## U16 - Daily refresh that lands a consistent tree (done)

CI on 45e793a was green on Linux, Windows and macOS (reviewer's report). The reviewer found that
the daily refresh would fail, or push an inconsistent tree, after a new snapshot.
- Reproduced here on a copy with a changed snapshot (last 12 values of
  `intents_holders_revenue.json` and `intents_revenue.json` x 1.2, manifest and `fetched_at`
  updated), with the old workflow steps: `build` then `verify` -> 1 FAIL ("VERIFICATION.md lists
  these checks with their current status"); the old `git add` list leaves `docs/DEMO_SCRIPT.md`
  and `docs/X_POST.md` modified; `verify` on the tree it would push -> 3 FAIL (DEMO_SCRIPT,
  X_POST, VERIFICATION).
- Fix: `near_posterior.refresh` (`python -m near_posterior.refresh [--commit]`): build,
  `verify --write` (must exit 0), with `--commit` `git add -A` and commit if anything changed,
  then a plain `verify` on the committed tree and `git status --porcelain` empty; exit 0 only if
  all hold. It first checks that the package it runs is the one of the target folder.
  `refresh.yml`: fetch, then `refresh --commit`, then `git push` in a later step (so no push
  if the refresh step fails). Bot identity kept; the reference panel is still not refetched.
- `verify --write` now computes the checks once (it ran them twice before).
- Everything `build` or `verify --write` writes (`RESOLUTION.md`, root `index.html`,
  `site/img/*`, `docs/*`, `VERIFICATION.md`, README) is now committed by `git add -A`; the
  regression test asserts an empty `git status` after the refresh.
- `tests/test_refresh.py`: copies the repository to a temporary git repo, applies the same
  snapshot change, runs `refresh.main(["--commit"])`, and asserts exit 0, an empty
  `git status`, a refresh commit that includes `VERIFICATION.md`, `docs/DEMO_SCRIPT.md` and
  `history.csv`, and that it changed files outside the old `git add` list; a second test checks
  the workflow order (fetch, refresh --commit, push) and that no hand-written `git add` list or
  bare `build` step remains. On the old logic the first test cannot pass (no refresh step, and
  the old list misses those files).
- README: the refresh line now says `fetch`, then `refresh`.

```
> uv run python -m near_posterior.verify --write
44 lines, all PASS, exit=0
> uv run python -m near_posterior.refresh
refresh: verify on the committed tree: 0 FAIL; uncommitted changes: none
> uv run pytest -q
110 passed in 77.91s
```
Not verified: the scheduled workflow itself on GitHub (it runs once pushed).

# Third pass (PREREG_3.md, docs/TASKS_V3.md)

Pull before starting: `git pull --ff-only origin main` at 2026-11-13 06:22 UTC and again at
06:31 UTC: already up to date at 7ecd678 (the branch has no upstream configured, so the remote
is named explicitly). No bot commit "chore(data): daily NEAR snapshot refresh" had arrived yet
(the schedule is 06:30 UTC). Work starts on the snapshot fetched 2026-11-12T10:17:09Z
(t0 = 2026-11-11). A later bot commit only touches files that W1 to W3 do not modify, so these
commits can be rebased onto it and rebuilt.

## W1 - Recency-weighted class forecast (T1) (done)

Tertiary (specified after the secondary results).
- `recency.py`: weights `(1/n_j') 0.5^(d/H)`, d = months from the moment's origin to the
  target's origin, normalised; H in {12, 24, 48, infinity}; scored on exactly the S1 targets
  with the S1 scores; `choose` picks H* on 12-month targets with origins up to 2024 and keeps it
  only if the 90 percent interval of CRPS(C_H*) - CRPS(C0) on origins 2025 is below 0;
  `weighted_frequency` gives P_recency for class R at t0 (d to the month of t0) with the
  registered entity bootstrap. `results/recency.json`.
- Result: mean CRPS on origins up to 2024 (596 targets): H = 12: 1.0055, 24: 1.0061,
  48: 1.0118, infinity: 1.0244, so H = 12 is best on the choice set. On origins 2025
  (1063 targets), CRPS(C_12) - CRPS(C0) = -0.0061, interval -0.0146 to 0.0028: it contains 0,
  so H* = infinity and recency weighting is not used. P_recency therefore equals the class
  frequency: 12 months 0.054 (0.026 to 0.083), 24 months 0.053 (0.022 to 0.091), 36 months
  0.061 (0.014 to 0.120). At 24 months (one origin year, no choice): mean CRPS H = 12: 1.277,
  24: 1.325, 48: 1.362, infinity: 1.410.
- Tests: H = infinity reproduces C0 exactly (all six S1 scores, both horizons); weights sum to
  1; a synthetic pool whose recent outcomes are lower makes H = 12 beat infinity; changing a
  2025 target does not change the choice statistics; a finite H is kept only if it beats C0 on
  2025 origins.

```
> uv run python -m near_posterior.verify --write
45 lines, all PASS
> uv run python -m near_posterior.refresh
refresh: verify on the committed tree: 0 FAIL; uncommitted changes: none
> uv run pytest -q
115 passed in 90.97s
```

## W2 - Recalibration (T2) (done)

Tertiary (specified after the secondary results).
- `recalibration.py`: G = empirical distribution function of training mid-PIT values;
  recalibrated event probability `1 - G(F(ln k))` (F: weighted class distribution function, mid
  convention); recalibrated PIT `G(PIT)`. Coverage of the central 50 and 90 percent intervals is
  PIT-based for raw and recalibrated forecasts alike; raw event probabilities are the S1 ones.
  Brier differences with the cluster bootstrap over target entities; KS difference by the same
  entity resampling. Rule used later by the thesis (`improves`): recalibration improves the
  held-out scores if the mean Brier falls for k = 1, 2, 5, no interval is above 0 and at least
  one is below 0. `results/recalibration.json`. W1 kept H* = infinity, so only C0 is reported.
- Held-out test at 12 months: G fitted on 596 targets with origins up to 2024, tested on 1063
  targets with origins 2025 (164 protocols). Raw against recalibrated: Brier (fees maintained)
  0.1941 vs 0.1705, difference -0.0236 (-0.0285 to -0.0184); Brier (doubled) 0.0943 vs 0.0700,
  -0.0242 (-0.0284 to -0.0195); Brier (5x) 0.0227 vs 0.0115, -0.0112 (-0.0131 to -0.0086); KS
  of PIT 0.238 vs 0.206, -0.032 (-0.050 to -0.008); coverage 50 percent 0.604 vs 0.556, 90
  percent 0.902 vs 0.938. Recalibration improves the held-out scores by the rule. The 2025
  reliability is closer but still above the diagonal (largest recalibrated bin: forecast 0.254,
  observed 0.105).
- 24 months, G fitted on all 201 targets (origins 2024 only, in sample): Brier (doubled) 0.0768
  vs 0.0434; KS 0.321 vs 0.010 (in sample, so not a test).
- NEAR Intents: P_cal at 12 months 0.0054 (0.0011 to 0.0109), F_R(ln k*) = 0.946, G from all
  1659 12-month targets (map tested out of sample at this horizon); at 24 months P_cal 0.000
  (0.000 to 0.000), F_R(ln k*) = 0.947: none of the 201 past 24-month targets (51 protocols,
  origins 2024) had a PIT above that level, in sample.
- Tests: uniform PITs leave G close to the identity; a forecast that doubles a Normal tail
  probability is corrected to within four standard errors; changing a 2025 target does not
  change the fitted map; the map is applied to event probabilities and PITs as specified; the
  `improves` rule.

```
> uv run python -m near_posterior.verify --write
46 lines, all PASS
> uv run python -m near_posterior.refresh
refresh: verify on the committed tree: 0 FAIL; uncommitted changes: none
> uv run pytest -q
120 passed in 111.57s
```

## W3 - Total interval (T3); tail model (T4) not reported (done)

Tertiary (specified after the secondary results).
- `total.py`: `t3` pools the 2000 bootstrap values of each of the 72 class specifications of S7
  (equal weight per specification, same seed), primary scenario, h = 24. To get those values
  without changing any result, `forecast.bootstrap_means` and
  `multiverse.moment_share_values` / `multiverse.specifications` expose what
  `cluster_bootstrap` and `moment_share` already computed (no existing result file changed).
  `results/total_uncertainty.json`: 144000 values; 5th percentile 0.0042, median 0.0321, 95th
  percentile 0.0824; 29.5 percent of the pooled variance lies between class specifications.
- T4 (optional, generalised Pareto tail): implemented (`total.gpd_fit`, `total.t4`, weighted
  maximum likelihood by a grid search refined inside fixed bounds) but not reported and not
  part of `build`. "Did not converge" was not defined by PREREG_3; I defined it as an optimum on
  a bound of the parameter domain. With the code as committed (41-point grid, 3 refinements)
  116 of 2000 resamples (5.8 percent) did not converge, above the 5 percent rule, so no number
  is reported. Exploratory runs before settling the code showed the share depends on the
  numerical definition: 2.5 and 4.3 percent with an "edge of the initial grid" criterion
  (41 and 21 points), 4.7 percent with the bound criterion on a 21-point grid. The point fit
  on the full class (xi -0.118, sigma 1.21, threshold 0.441 = entity-weighted 85th percentile
  of Y, 95 excesses) would give 0.047 against the empirical 0.053; it is not a reported result.
  Reproduce: `uv run python -c "import json; from near_posterior import coverage, refclass,
  total; c = coverage.summary(coverage.load()); p = refclass.load_panel();
  print(total.t4(p, refclass.moments(p, 24), c['F_near'],
  json.load(open('results/headline.json'))['k_star'])['result'])"`.
- Tests: pooled percentiles and between-group share on constructed groups; the T3 file holds
  72 x 2000 values; the GPD fit recovers xi = 0.3, sigma = 1 on 5000 simulated excesses.

```
> uv run python -m near_posterior.verify --write
47 lines, all PASS
> uv run python -m near_posterior.refresh
refresh: verify on the committed tree: 0 FAIL; uncommitted changes: none
> uv run pytest -q
123 passed in 113.91s
```

## W4 - Thesis, page, README (done)

- `THESIS.md`: new section 8 "Correcting for past over-forecasting" (sections renumbered to 13):
  what T1 chose and why (recency weighting not used: it did not beat C0 on 2025 origins), the
  held-out test of T2 as a table (Brier for three events, KS, coverage, with difference
  intervals) and the 2025 reliability table before and after, the 24-month in-sample note, the
  numbers for NEAR Intents in the order fixed by PREREG_3 (registered P, recency-weighted P
  "not used", P_cal with interval and whether it was tested out of sample), the T3 interval,
  and T4 "not reported" with the reason. Summary: one added sentence giving the registered P and
  how often outcomes at that forecast level happened in the past, at 24 months (in sample) and
  12 months (tested out of sample). Rule for quoting P_cal as a correction
  (`recalibration.improves`): mean Brier lower for k = 1, 2, 5, no interval above 0, at least
  one below 0; it holds on the 2025 targets, so the sentence is shown; otherwise the section
  says recalibration did not improve the held-out scores and the summary does not quote P_cal.
- Page: one block tagged "tertiary" (reliability before and after recalibration on the 2025
  origins, and a table with the registered P, the recency-weighted P and P_cal side by side for
  12 and 24 months); the top note now explains the "tertiary" tag with a link to `PREREG_3.md`.
  Explorer unchanged. Checked in the built-in browser.
- README finding: headline unchanged; one added sentence with P_cal under the same rule.
- `VERIFICATION.md`, `docs/DEMO_SCRIPT.md`, `docs/X_POST.md` regenerate (unchanged by this task).

```
> uv run python -m near_posterior.verify --write
47 lines, all PASS
> uv run python -m near_posterior.refresh
refresh: verify on the committed tree: 0 FAIL; uncommitted changes: none
> uv run pytest -q
124 passed in 199.47s
```
