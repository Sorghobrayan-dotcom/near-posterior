# Pre-registration addendum 3: time-aware forecast, recalibration, total uncertainty

Written on 2026-11-13, after the results of `PREREG.md` and `PREREG_2.md` were computed and
before any analysis below was run. Nothing here replaces a registered result: the headline
stays the one of `PREREG.md`. Everything below is reported whatever its outcome, under the
label "tertiary (specified after the secondary results)".

Notation, data, seeds, the floor `ln 0.01`, the bootstrap (2000 resamples,
`numpy.random.default_rng(20261112)`, percentiles 5 and 95) and all definitions are those of
`PREREG.md` and `PREREG_2.md` unless stated.

## 0. Why, and what was known when this was written

Known: every result of the first two documents, in particular that the class forecast C0 beat
trend extrapolation at 12 and 24 months but forecast more growth than happened (S1 reliability
tables: doubling forecast at 0.28 and observed at 0.11 at 12 months, 0.25 against 0.03 at 24
months), that the probability differs by origin year (0.000 to 0.118 for years with at least
ten entities), and that the 72 class definitions give 0.009 to 0.063.

Purpose: a forecast that is known to be too optimistic should be corrected by a rule fixed in
advance and tested on data the rule did not see. Two candidate causes are addressed:
older outcomes may describe a faster-growing period (T1), and the class forecast may be
miscalibrated as a whole (T2). T3 puts sampling and specification uncertainty in one interval.

No result of T1, T2, T3 or T4 has been computed.

## T1. Recency-weighted class forecast

- For a target at month `tau` and a pool moment `(j', t')` of its class (S1 construction):
  weight `w = (1 / n_j') * 0.5^(d / H)`, `d` = months from `t'` to `tau`, weights normalised
  to sum 1. `H in {12, 24, 48}` months; `H = infinity` is C0.
- Scored on exactly the S1 targets, at h = 12 and h = 24, with the S1 scores.
- Choice of H, at h = 12 only: `H*` is the H with the lowest mean CRPS over targets whose
  origin year is 2024 or earlier. `H*` is then scored on targets with origin year 2025, which
  played no part in the choice. If the 90 percent interval of CRPS(C_H*) - CRPS(C0) on the
  2025 targets contains 0 or is above 0, then `H* = infinity`: recency weighting is not used.
- At h = 24 all four H are reported; no choice is made there (one origin year).
- Applied to NEAR Intents at t0 with `H*`: `P_recency(k*)` for class R at h = 12, 24, 36,
  with `d` = months from the moment's origin to t0, and the registered bootstrap.

## T2. Recalibration by past probability integral transforms

- PIT of a scored target under a class forecast: the mid-PIT of `PREREG.md` 6.
- Map: `G(u)` = empirical distribution function of the PIT values of the training targets.
  Recalibrated distribution function: `F_cal(y) = G(F(y))`, with `F` the weighted distribution
  function of the class sample (mid convention). Recalibrated event probability:
  `P_cal(Y >= y) = 1 - G(F(y))`.
- Test at h = 12: G fitted on targets with origin year 2024 or earlier, evaluated on targets
  with origin year 2025. Reported for raw and recalibrated forecasts: Brier score for
  k = 1, 2, 5, the reliability tables of S1, coverage of the central 50 and 90 percent
  intervals, and the KS distance of the PIT values to the uniform distribution. Difference
  intervals by the cluster bootstrap over target entities.
- At h = 24: G is fitted on all 24-month targets (origins 2024 only). There is no later origin
  to test it on; this is stated wherever the number appears.
- Applied to NEAR Intents: `P_cal(k*) = 1 - G_h(F_R(ln k*))` at h = 12 (G from all 12-month
  targets) and h = 24 (G from all 24-month targets), with `F_R` the class R distribution
  function at that horizon. Interval: resample the validation targets' entities, refit G,
  recompute; percentiles 5 and 95. The class forecast used is C0, or C_H* if T1 selected a
  finite `H*` (then both are reported).
- Reading rule, fixed now: the thesis reports the registered P first, then P_cal as "how
  often outcomes at this forecast level happened in the past", and says which of the two is
  tested out of sample at which horizon.

## T3. One interval for sampling and class definition

For the primary scenario at h = 24: pool the 2000 bootstrap values of each of the 72 class
specifications of S7 (equal weight per specification; same seed for each). Report the 5th,
50th and 95th percentiles of the pooled 144000 values, and the share of the pooled variance
that is between specifications (variance of the 72 means over the pooled variance).

## T4. Optional: tail model as a cross-check

Class R, h = 24: fit a generalised Pareto distribution by maximum likelihood to the excesses
of `Y` over its entity-weighted 85th percentile (moments weighted `1 / n_j`); the model
probability of `Y >= ln k*` is `0.15 * (1 - GPD(ln k* - threshold))`. Interval by the cluster
bootstrap over entities (refit each time). Reported next to the empirical frequency. If the
fit fails to converge on more than 5 percent of resamples, report that instead of a number.

## What does not change

The registered headline, its verdict, the specification curve and the resolution rule (S11:
the forecast that will be scored is the registered P). The tertiary numbers are additional
readings of the same evidence.
