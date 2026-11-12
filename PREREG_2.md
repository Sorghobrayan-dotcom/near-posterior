# Pre-registration addendum: secondary analyses

Written on 2026-11-12, after the primary results of `PREREG.md` were computed and before any
analysis below was run. Nothing here replaces a registered result: the headline stays the one
of `PREREG.md` sections 4 to 8. Every analysis below is reported whatever its outcome, under
the heading "secondary (specified after the primary results)".

Notation, data, seeds, the floor `ln 0.01`, the bootstrap (2000 resamples,
`numpy.random.default_rng(20261112)`, percentiles 5 and 95) and all definitions are those of
`PREREG.md` unless stated.

## 0. What was known when this was written

- All primary results: the headline probability and interval, the class counts, the results by
  origin year, the 12-month backtest scores, the specification curve summary.
- The nine entities of class R with at least one 24-month success, and the moment-weighted
  quantiles of 24-month growth in class R.
- Counts only (no outcome) for S1: 1636 scorable targets from 187 entities at h = 12
  (origins 2023 to 2025), 194 from 50 entities at h = 24 (origins 2024); and for S2: 92 targets
  from 31 entities.
- A wording error: `PREREG.md` section 1 says "within 24 months" while the registered event of
  section 3 is "at month 24". The registered event is the one of section 3. S4 adds the
  "at any point within" event.

## S1. Method validation with target-centred classes

Purpose: test the construction "build a reference class around the target" on every eligible
entity of the panel, not only on class R.

- Horizons 12 and 24.
- Targets: valid, resolved moments `(j, tau)` with a 90-day fee sum >= 1,000,000 USD,
  `a_j(tau) >= 270`, and `F_j` valid and positive at `tau-3`, `tau-6`, `tau-9`, `tau-12` months.
- Class of a target: pool moments `(j', t')` with `j' != j`, `t' + h months <= tau`, resolved,
  `F_j(tau) / 3 <= F_j'(t') <= 3 * F_j(tau)` and
  `a_j(tau) * 270/550 <= a_j'(t') <= a_j(tau) * 1095/550`.
  (For NEAR Intents at t0, age 550, this is exactly class R.)
- A target is scored only if its class holds at least 20 entities. Dropped targets are counted.
- Models: C0 (the class sample, weight `1 / n_j'`), B1 and B2 exactly as in `PREREG.md` 6.
- Scores, aggregation, intervals and the by-year table exactly as in `PREREG.md` 6.
- Reliability tables for C0, B1 and B2:
  event `Y >= ln 2`, forecast bins [0, 0.05), [0.05, 0.10), [0.10, 0.20), [0.20, 0.40), [0.40, 1];
  event `Y >= ln 5`, forecast bins [0, 0.02), [0.02, 0.05), [0.05, 0.10), [0.10, 1].
  Per bin: number of targets, number of entities, mean forecast, observed frequency.
- Sufficiency: at least 100 scored targets from at least 30 entities, as in `PREREG.md` 6.
- If C0 does not beat B2 (the interval of CRPS(B2) - CRPS(C0) contains 0 or is below 0), the
  thesis says so in its summary.

## S2. Class R backtest without the analog-pool condition

`PREREG.md` 6 with models B0, B1, B2 only and the single scoring condition "B0 pool of at
least 20 entities", at h = 24. Reported with its sufficiency flag (expected: not sufficient).

## S3. Exceedance curve and growth quantiles

- `P_B0(k, h)` of `PREREG.md` 4.3 for class R, `h in {12, 24, 36}`, on the fixed grid
  `k = 10^(-2 + i/20)`, `i = 0 .. 80`, each with its bootstrap interval.
- Entity-weighted quantiles (5, 10, 25, 50, 75, 90, 95 percent) of `exp(Y)`: moment weight
  `1 / n_j`, normalised; lower weighted quantile.
- For each entity and horizon: the number of class moments, the number with `Y >= ln k*`
  (primary `k*` of that horizon), the largest `exp(Y)` and its origin month.

## S4. At any point within the horizon

For a class R moment `(j, t)` at horizon h (the same moments as the registered class), success
"within h" at scenario factors `(G_P, G_kappa)` and window W means: there is a month
`u in 1 .. h` whose 90-day window ending `t + u months - 1` is valid and such that

    F_j(t + u months) / F_j(t) >= (1 + r)^(u/12) * G_P / G_kappa / C_W(t0)

`P_within(h)` is the entity-weighted share of such moments, with the registered bootstrap.
Reported for the primary scenario at h = 12, 24, 36, next to the registered "at month h" value.

## S5. Distribution of coverage at the horizon

Primary scenario: `C(h) = C_90(t0) * exp(Y) / (1 + r)^(h/12)`. Entity-weighted quantiles
(5, 10, 25, 50, 75, 90, 95 percent) for h = 12, 24, 36.

## S6. Lever table

`P_B0(k*)` at h = 24, class R, W = 90, for every combination of
- capture at the horizon: `kappa_90(t0)`, 0.34, 0.50, 0.75, 1.00;
- issuance factor on the constant-rate path: 1, 0.75, 0.50, 0.25;
- price factor `G_P`: 0.5, 1, 2.

60 cells, each with its bootstrap interval. A governance scenario read at a primary source
(S10) is added as extra, labelled rows.

## S7. Class multiverse

Primary scenario, h = 24. Every combination of
- scale band: `F_NEAR / q .. q * F_NEAR`, `q in {2, 3, 5}`;
- age band: [270, 1095], [180, 730], [365, 1460], [270, infinity);
- weighting: entity-equal (`PREREG.md` 4.3), moment-equal (plain share of moments, cluster
  bootstrap over entities);
- categories: all; the trading list of `PREREG.md` 4.2; all except the yield-type list
  (Liquid Staking, Staking Pool, Liquid Restaking, Restaking, Stablecoin Issuer, RWA, Lending,
  CDP, Yield, Yield Aggregator, Basis Trading, Risk Curators, Onchain Capital Allocator,
  Uncollateralized Lending, NFT Lending, Restaked BTC, Anchor BTC, Decentralized BTC,
  Leveraged Farming, Farm).

72 specifications. Reported: P, interval, entities and moments of each; median, minimum and
maximum of P; specifications with fewer than 30 entities are flagged, not dropped.

## S8. Origin-year cohorts

- Leave-one-origin-year-out `P_B0` (class R, primary scenario, h = 24), one value per year.
- Two-stage bootstrap, indicative only (few cohorts): a block is an (entity, origin year) pair
  with its share of successes; draw origin years with replacement (as many as there are),
  collect the blocks of the drawn years (a year drawn twice contributes twice), draw as many
  blocks with replacement, take the mean share. 2000 resamples, percentiles 5 and 95.

## S9. Forward requirements stated by other theses

For each explicit forward requirement or assumption in a public NEAR thesis (a growth multiple
of fees, revenue or volume, with or without a horizon): record it as in `PREREG.md` 10
(repository, commit, file, line, quote), plus `k` and the horizon in months.
Report `P_B0(k, h)` from S3 at the stated horizon mapped to the nearest of 12, 24, 36 (the
mapping is stated; without a stated horizon, all three are reported).
The base rate is about fee growth in class R; applying it to revenue or volume assumes a
constant take rate, and this is written next to the table. No judgement about any thesis.

## S10. Governance issuance scenario

Only if the proposal text is read at a primary source (governance forum, on-chain proposal or
the protocol's documentation). Recorded: URL, date read, the quoted parameter. The scenario is
a factor on the constant-rate issuance path from t0. It adds labelled rows; it replaces none.

## S11. Resolution

For h = 12, 24, 36, the registered forecast is `P_B0(k*)` of class R, primary scenario, on the
registered snapshot. On the first snapshot whose `t0` is at or after the registered
`t0 + h months`, the outcome is 1 if `C_90` at the registered `t0 + h months` is >= 1, else 0,
and the Brier contribution is `(P - outcome)^2`. The registered forecasts are frozen in
`results/registered_forecast.json` and never recomputed from a later snapshot.

## S12. Optional: second route for buybacks

If the buyback or revenue accounts can be read from the public DefiLlama adapter source, compare
their on-chain NEAR balance change between 2026-02-23 and t0 with the NEAR implied by daily
buybacks and prices. Report the ratio. Time limit: two hours; if not done, say so.
