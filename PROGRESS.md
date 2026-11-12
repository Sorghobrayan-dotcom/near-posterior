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
