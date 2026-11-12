# Resolution of the registered forecasts

Rule (`PREREG_2.md` S11): outcome = 1 if C_90 at t0 + h months >= 1, else 0; Brier = (P - outcome)^2. The forecasts were computed once from the registered snapshot (t0 = 2026-11-11, fetched 2026-11-12T10:17:09+00:00) and the frozen reference panel; they are never recomputed from a later snapshot (`results/registered_forecast.json`).

Command: `uv run python -m near_posterior.resolve` (offline, on the current `data/raw/` snapshot; the daily refresh keeps that snapshot current).

| Horizon | Resolution date | k* | Registered P (90% interval) | Status on the current snapshot |
|---|---|---|---|---|
| 12 months | 2027-11-11 | 5.623 | 0.054 (0.026 to 0.083) | pending (snapshot t0 = 2026-11-11) |
| 24 months | 2028-11-11 | 5.762 | 0.053 (0.022 to 0.091) | pending (snapshot t0 = 2026-11-11) |
| 36 months | 2029-11-11 | 5.905 | 0.061 (0.014 to 0.120) | pending (snapshot t0 = 2026-11-11) |
