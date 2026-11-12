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
