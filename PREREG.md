# Pre-registration

Written on 2026-11-12, before any fee history of a reference-class protocol was downloaded.
This file fixes the question, the data rules, the estimators, the backtest and the decision
rules. Results computed later are reported under these rules. Any deviation goes to
`DEVIATIONS.md` with its date and reason, and the registered result is still reported when it
can be computed.

All logarithms are natural. Days are UTC calendar days.

## 1. Question

Will NEAR buybacks funded by NEAR Intents revenue cover NEAR's net issuance within 24 months?

## 2. Data

### 2.1 NEAR series (snapshot `tests/fixtures/near_20261112`, fetched 2026-11-12T10:17:09Z)

- `f_d`: daily gross NEAR Intents fees in USD (DefiLlama `dailyFees`, slug `near-intents`).
- `b_d`: daily buybacks in USD (DefiLlama `dailyHoldersRevenue`, same slug). Zero before
  2026-02-23.
- `S_d`: NEAR total supply in NEAR (NearBlocks `/v1/charts`, `total_supply` / 1e24).
- `p_d`: NEAR price in USD (NearBlocks `/v1/charts`, `near_price`).
- `t0`: last complete day of the snapshot. For the registered snapshot, `t0 = 2026-11-11`.

NearBlocks `circulating_supply` is not used: it does not move in the snapshot.

### 2.2 Reference panel (DefiLlama fees, fetched once after this file is committed)

- Universe: entries of `https://api.llama.fi/overview/fees` (`dataType=dailyFees`) with
  `protocolType == "protocol"` and `totalAllTime >= 1,000,000` USD at fetch time.
  The slug `near-intents` is excluded: it is the target.
- Entity: entries sharing the same `parentProtocol` are merged into one entity; an entry
  without `parentProtocol` is its own entity. The entity's daily fee is the sum of its
  entries' daily fees. A day is present for an entity if at least one of its entries has a
  value that day.
- Entity category: the `category` of its entry with the largest `totalAllTime`.
- Panel end `D`: the latest day present in the panel, minus one day (the fetch day is partial).
- Dead fill: if an entity's last present day is more than 30 days before `D`, every later day
  up to `D` is present with value 0.
- The panel is frozen after the fetch. The daily refresh updates the NEAR series only.
- Every universe entry whose history could not be fetched is listed by slug in
  `data/refclass/missing.txt`. If more than 5 percent are missing, stop (section 9).

## 3. Definitions

- Annualised window: `A_W(x, t) = 365 * mean(x_d for d in t-W+1 .. t)`.
- Net issuance: `I(t) = S_t - S_{t-365}` (NEAR per year). Rate: `r = I(t0) / S_{t0-365}`.
- Capture rate: `kappa_W(t) = sum(b) / sum(f)` over the same W days.
- Coverage: `C_W(t) = A_W(b, t) / (I(t) * p_t)`.

Event: `E_h = { C_90(t0 + h months) >= 1 }`. Primary horizon `h = 24`; also 12 and 36.

Identity (exact, because `A_90(b) = A_90(f) * kappa_90`):

    C_90(t0+h) = C_90(t0) * G_F * G_kappa / (G_I * G_P)

with `G_X = X(t0+h) / X(t0)` and `F = A_90(f)`. Therefore

    E_h  <=>  G_F >= k*,   k* = (G_I * G_P / G_kappa) / C_W(t0)

Only `G_F` is forecast. `G_kappa`, `G_I` and `G_P` are scenarios (section 7).
No price model is used.

Primary scenario: `W = 90`, `G_kappa = 1`, `G_P = 1`, `G_I = (1 + r)^(h/12)`.

## 4. Reference class

### 4.1 Moments

- Origins `t`: the first day of each calendar month.
- `F_j(t)`: `365 * mean` of entity j's present daily fees over the 90 days `t-90 .. t-1`.
  Valid only if at least 80 of the 90 days are present (after dead fill) and `F_j(t) > 0`.
- Age `a_j(t)`: days between entity j's first day with fee > 0 and `t`.
- Momentum `m_j(t) = ln( F_j(t) / F_j(t - 6 months) )`, defined when both are valid.
- Outcome at horizon h: `u = t + h months`. The moment is resolved if `u - 1 <= D`.
  - `Y = ln( F_j(u) / F_j(t) )` if the 90-day window ending `u-1` has at least 80 present
    days and a positive mean;
  - `Y = ln(0.01)` (floor) if that window has at least 80 present days and a mean <= 0;
  - otherwise the moment is excluded and written to `data/refclass/excluded.csv`.
  For scoring, `Y` is replaced by `max(Y, ln 0.01)`.

For NEAR Intents the same formulas are applied at `t0` (window ending `t0`), with
`F_NEAR = A_90(f, t0)`.

### 4.2 Classes

Primary class R: valid, resolved moments with
`F_NEAR / 3 <= F_j(t) <= 3 * F_NEAR` and `270 <= a_j(t) <= 1095`.

Declared variants:
- `R_strict`: scale band `F_NEAR / 2 .. 2 * F_NEAR`, same ages.
- `R_all_ages`: scale band of R, `a_j(t) >= 270`.
- `R_trading`: R restricted to entity categories Dexs, Derivatives, Bridge,
  Cross Chain Bridge, Bridge Aggregator, Canonical Bridge, DEX Aggregator, Perps Aggregator,
  Trading App, Interface, Telegram Bot, Prediction Market, Options.

Fees are nominal USD. No adjustment for market size across years.

### 4.3 Class frequency (model B0)

For a threshold k:

    p_j = mean over entity j's class moments of 1{ Y >= ln k }
    P_B0(k) = mean over entities of p_j

- 90 percent interval: cluster bootstrap over entities, 2000 resamples,
  `numpy.random.default_rng(20261112)`, percentiles 5 and 95.
- Secondary estimate: one moment per entity (its earliest class moment), exact
  Clopper-Pearson 90 percent interval.
- Also reported: `P_B0(k)` by calendar year of the origin, with the number of entities.

If class R has fewer than 30 entities at h = 24, stop (section 9).

## 5. Analog model (A_K)

- Pool: valid, resolved moments with a 90-day fee sum >= 1,000,000 USD
  (`F_j(t) >= 365/90 * 1e6`), `a_j(t) >= 270`, momentum defined.
- Covariates: `x = ( ln F_j(t), m_j(t), ln a_j(t) )`.
- Scaling: per covariate, subtract the pool median and divide by `1.4826 * MAD` of the pool
  (if the MAD is 0, divide by the pool standard deviation; if that is 0, by 1).
- Distance: Euclidean in the scaled space. For each entity keep its single nearest moment.
  Take the K nearest entities, `K in {30, 60, 120}`.
- Predictive sample: the K outcomes, equal weights. `P_A(k)` = share with `Y >= ln k`,
  exact Clopper-Pearson 90 percent interval.

## 6. Backtest and model choice

Rolling origin, no look-ahead, for h in {12, 24}.

- Targets at month `tau`: class R moments `(j, tau)` for which `F_j` is valid and positive
  at `tau`, `tau-3`, `tau-6`, `tau-9` and `tau-12` months, and the outcome is resolved.
- Pool for target `(j, tau)`: moments `(j', t')` with `j' != j` and `t' + h months <= tau`.
- Models:
  - B0: weighted empirical sample of the pool moments that are in class R, weight
    `1 / n_j'` (each entity has total weight 1).
  - B1: `Y ~ Normal(0, s^2 * h/3)`.
  - B2: `Y ~ Normal(mu * h/3, s^2 * h/3)`.
    `mu` and `s` are the mean and the sample standard deviation (ddof = 1) of the entity's
    own consecutive non-overlapping quarterly log changes of `F` before `tau`
    (the most recent 4 to 8). If `s = 0`, use `s = 1e-6`.
  - A_K: section 5 applied to the pool, K in {30, 60, 120}.
- A target is scored only if its B0 pool holds at least 20 entities and its analog pool at
  least 120 entities. Dropped targets are counted and reported.
- Scores, all on the same scored targets:
  - Brier score for the events `Y >= ln k`, `k in {1, 2, 5}`;
  - CRPS on `max(Y, ln 0.01)`:
    weighted sample `sum_i w_i |z_i - y| - 0.5 * sum_i sum_j w_i w_j |z_i - z_j|`;
    Normal `s * ( z * (2*Phi(z) - 1) + 2*phi(z) - 1/sqrt(pi) )`, `z = (y - mu) / s`;
  - coverage of the central 50 and 90 percent predictive intervals; PIT values.
- Aggregation: plain mean over scored targets. Uncertainty of a score difference:
  cluster bootstrap over target entities, 2000 resamples, same seed, percentiles 5 and 95.
  Scores are also reported by calendar year of `tau`.

Sufficiency: a backtest at horizon h is sufficient if it has at least 100 scored targets
from at least 30 entities.

Model choice for the headline:
1. Use the h = 24 backtest if sufficient, else the h = 12 backtest if sufficient,
   else the headline model is B0 and the thesis states that no backtest supports it.
2. Among {B0, A_30, A_60, A_120} take the lowest mean CRPS.
3. If the 90 percent interval of (CRPS of that model - CRPS of B0) contains 0,
   the headline model is B0.

B1 and B2 are comparison baselines only. Their scores are reported whatever they are.

## 7. Specification curve

Grid, every combination computed with model B0:

- window W for `C_W(t0)`: 30, 90, 180, days since 2026-02-23 inclusive;
- class: R, R_strict, R_all_ages, R_trading;
- horizon h: 12, 24, 36 months;
- capture at the horizon: `kappa_W(t0)` (constant), 0.34, 0.50
  (`G_kappa = kappa_target / kappa_W(t0)`);
- issuance: `G_I = (1+r)^(h/12)` (constant rate) and half of it (illustrative halving;
  not a statement about any governance proposal);
- price: `G_P` = 0.5, 1, 2.

That is 4 * 4 * 3 * 3 * 2 * 3 = 864 rows. Reported: every row, the median, the minimum,
the maximum, and the primary row.

## 8. Verdict

On the primary scenario, with the headline model's point estimate `P`:

- `P < 0.10`: "buybacks are unlikely to cover issuance within 24 months";
- `0.10 <= P <= 0.50`: "conditional";
- `P > 0.50`: "supported".

The thesis also reports what would change this verdict: the smallest `G_kappa`, the largest
`G_I` cut and the price factor that each move `P` across 0.50 on their own, or the statement
that none in the grid does.

## 9. Stop rules

- More than 5 percent of the universe missing from the panel: stop and report.
- Class R with fewer than 30 entities at h = 24: stop, report the count, then use
  `R_all_ages` as primary and say so at the top of the thesis.
- Control values of `docs/SPEC.md` not reproduced on the registered snapshot: stop.

## 10. Many-analysts audit

Descriptive only. For each public NEAR thesis read, and each metric it publishes among
M1 annualised buybacks or captured revenue, M2 capture rate, M3 required multiple or
coverage, M4 30-day NEAR Intents volume, M5 net inflation rate:

- `y`: the published value, with repository, commit, file, line, window, end date, source;
- `r`: our value under their stated window, end date and definition;
- `r0`: our value under our primary definition at `t0`;
- replication error `e = ln(y / r)`; reproduced if `|e| <= ln(1.02)`;
- specification effect `s = ln(r / r0)`; identity `ln(y / r0) = s + e`;
- dispersion: interquartile range of `ln y` across theses, reported with n, only if n >= 5.

A value we cannot recompute is reported as "not recomputed", never as wrong.
DefiLlama can revise its history; a replication error can come from a revision.

## 11. What was seen before this file was written

- All NEAR series of section 2.1.
- From the DefiLlama fees overview: counts of entries by type, by category, by cumulative-fee
  threshold, by `parentProtocol`; the totals of NEAR Intents.
- The first date, last date and number of points of five fee series (ethereum, tether,
  fantom, camelot-v3, opensea-v1). No values.
- The READMEs of 30 public NEAR theses.

No fee value or growth outcome of any reference-class protocol was examined. The author
has ordinary prior knowledge of the industry; the rules above were not tuned on the panel.
