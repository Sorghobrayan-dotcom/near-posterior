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
