# Deviations from the pre-registration

## 2026-11-12: wording of the event and of the verdict

`PREREG.md` section 1 says "within 24 months", while the registered event of section 3 is
`C_90(t0 + 24 months) >= 1`, i.e. at the 24-month mark (`PREREG_2.md` section 0). The verdict
words of `PREREG.md` section 8 ("buybacks are unlikely to cover issuance within 24 months")
are therefore printed as "... at the 24-month mark". The event, the thresholds and every number
are unchanged. "Within" is used only for the secondary analysis S4 of `PREREG_2.md`.

## 2026-11-12: erratum on the expected S1 counts (not a deviation of method)

The counts quoted in `PREREG_2.md` section 0 and in `docs/TASKS_V2.md` U4 (1636 targets from 187
entities at h = 12; 194 from 50 at h = 24) were computed by the reviewer with an age band of
[a/2, 2a]. Under the rule registered in S1 the counts are 1659 from 188 and 201 from 51. Both
counts were made without reading outcomes. The registered rule was applied.

## 2026-11-13: judgement calls of the third pass (not changes of method)

(a) "Improve the held-out scores". `PREREG_3.md` T2 and `docs/TASKS_V3.md` W4 do not define
when recalibration improves the held-out scores. The rule used (`recalibration.improves`, fixed
before the thesis text was written and stated in `THESIS.md` section 8): the mean Brier score is
lower for the three events (fees maintained, doubled, at least 5x), no 90 percent interval of the
difference is above 0, and at least one is below 0. On the 2025 origins all three intervals are
below 0, so P_cal is quoted, always after the registered probability.

(b) T4 not reported. `PREREG_3.md` T4 says to report the failure instead of a number if the fit
fails to converge on more than 5 percent of resamples, but does not define convergence. With the
definition kept in the code (the maximum-likelihood optimum lies on a bound of the parameter
domain) 116 of 2000 resamples (5.8 percent) did not converge; across the definitions tried
(an optimum on the edge of the initial grid, or on a bound, with 21- or 41-point grids) the
share ranged from 2.5 to 5.8 percent, around the stop line. Because the definition was not
registered and the outcome depends on it, no T4 number is reported. The point fit seen during
these runs (0.047 against the empirical 0.053) is recorded in `PROGRESS.md` only and is stated as
unreported in `THESIS.md`.

(c) Exact upper bound for P_cal. At 24 months no past forecast reached the level of k* (0 of 201
forecasts from 51 protocols, origins 2024), so the registered bootstrap interval is 0 to 0 and
cannot express the uncertainty. Added after the results: the count of past forecasts above the
level and an exact one-sided 95 percent upper bound by Clopper-Pearson with the protocols as the
independent units (0 of 51 at 24 months; the same bound is shown at 12 months, 4 of 188
protocols). The bootstrap interval stays reported next to them, as registered.


## 2026-11-14: post hoc class without interest-income protocols (not a change of method)

Specified after the primary results, in answer to the objection that the reference class mixes
fee businesses with protocols whose fees are interest income. The 24-month probability is
recomputed with the registered estimator (`forecast.b0`, entity-weighted, cluster bootstrap) on
the same class sample and the same k*, leaving out `tether`, `parent#maker`, `parent#aave` and
`binance-staked-eth` (ids as in `results/entities_R.csv`). This list is named and hand-picked
after seeing which protocols reached k*; it is not a rule written in advance, and other lists
would give other numbers. The result is in `results/posthoc_class.json`, shown as a "post hoc"
row in the robustness block of the page and in section 9 of `THESIS.md`. The registered headline
does not change.
