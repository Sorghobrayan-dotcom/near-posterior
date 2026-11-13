# Tasks, third pass

Rules: `PREREG_3.md` (sections T1 to T4). `PREREG.md`, `PREREG_2.md` and `PREREG_3.md` are not
edited. The registered headline stays the headline. Everything here is labelled
"tertiary (specified after the secondary results)" and reported whatever it shows.
Same working rules as `AGENTS.md`: one task = one commit, tests, `build`, `verify` and
`refresh` green, every new result covered by `verify`, `PROGRESS.md` updated, no trailer,
no push. Order W1 to W4. Cut order: T4 (inside W3), then nothing else.

## W1 - Recency-weighted class forecast (T1)

- `results/recency.json`: for h = 12 and 24, mean CRPS, Brier (k = 1, 2, 5), coverage and
  reliability tables for H = 12, 24, 48 and infinity on the S1 targets; at h = 12 the choice
  set (origins up to 2024) and the held-out set (origins 2025) reported separately; `H*` and
  the reason; `P_recency(k*)` for NEAR Intents at h = 12, 24, 36 with intervals.
- Tests: H = infinity reproduces C0 exactly; weights sum to 1; a synthetic panel where recent
  outcomes are lower makes a finite H win; the 2025 targets are never used to choose H.

## W2 - Recalibration (T2)

- `results/recalibration.json`: the held-out test at h = 12 (raw against recalibrated: Brier,
  reliability, coverage, KS of the PIT values, difference intervals); the 24-month map with
  its in-sample note; `P_cal(k*)` for NEAR Intents at h = 12 and 24 with intervals; the same
  for C_H* if W1 selected a finite `H*`.
- Tests: a forecast that is already calibrated is left unchanged (G close to the identity);
  a synthetic forecast that doubles the true tail probability is corrected to within the
  sampling error; the 2025 targets are never used to fit the map that is tested on them.

## W3 - Total interval (T3) and optional tail model (T4)

- `results/total_uncertainty.json`: the pooled 5th, 50th and 95th percentiles and the
  between-specification share of variance.
- Optional `results/tail_model.json` (T4). Time limit two hours; if skipped, say so in
  `PROGRESS.md` and in the thesis.

## W4 - Thesis, page, README

- `THESIS.md`: a new section "Correcting for past over-forecasting" after "How we know the
  method works": what T1 chose and why, the held-out test of T2 in a table, the numbers for
  NEAR Intents (registered P first, then P_recency if any, then P_cal), and the T3 interval.
  The summary gets one sentence: the registered P, then how often outcomes at that forecast
  level happened in the past, with the horizon at which this was tested out of sample.
  Sentences are chosen from the numbers: if recalibration does not improve the held-out
  scores, the section says so and the summary does not quote P_cal as a correction.
- Page: one chart (reliability before and after recalibration on the held-out year) and the
  three numbers side by side; the explorer is unchanged.
- README finding: unchanged headline; one added sentence with P_cal under the same condition.
- `VERIFICATION.md`, `docs/DEMO_SCRIPT.md`, `docs/X_POST.md` regenerate; `verify` covers the
  new files.
