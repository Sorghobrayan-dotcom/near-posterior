# Pre-registration 4: a short forecast that resolves during judging

Specified after the primary results. It changes nothing in `PREREG.md`, `PREREG_2.md` or
`PREREG_3.md`, and it says nothing about the 24-month question. It tests the machinery (commit on
chain, resolve, attest), not the thesis: nothing else in this project resolves before 2027.

Written before the forecast below was computed.

## Event

C_90(e) >= C_90(a), where

- C_90(d) is the coverage of `PREREG.md` (buybacks over the dollar value of net issuance, both
  summed over the 90 days ending on day d), as given in `daily[]` of `results/coverage.json`;
- e = 2026-11-15 (the event day);
- a = the anchor day: the last day of `daily[]` in `results/coverage.json` at the moment the
  forecast is frozen.

Why the anchor is not the registered t0 (2026-11-11): at the time of writing, C_90 for 2026-11-12
is already in the daily series and already above the value at t0. A comparison with t0 would
be partly decided at commit time. Anchoring at the last known day means that no information
past the anchor is used.

## Probability

With k = e - a in days, P is the share of past pairs (d, d + k) with C_90(d + k) >= C_90(d),
where

- d runs over the days on or after the first day the 90-day window is full, that is
  `buyback_start` + 89 days (before that day C_90 rises mechanically while the window fills);
- d + k is on or before a (only data up to the anchor are used).

The number of pairs n and the number of pairs where the event held are reported with P.

Limits, stated with the number wherever it is shown:

- overlapping windows are not independent: consecutive pairs share most of their days, so n
  overstates the amount of information;
- the sample is small (a few months of full windows);
- the two 90-day windows compared share 90 - k days, so C_90 moves slowly and the event depends
  mostly on the k days that enter and the k days that leave the window.

## Freezing

`python -m near_posterior.live --register` computes the forecast from the current snapshot and
writes it to `data/live/forecast.json`, with the anchor day, C_90 at the anchor, e, k, P, n,
the `fetched_at` of the snapshot and the daily series used. `build` and the daily refresh never
rewrite this file. It may be rewritten only while `data/onchain/commitments.json` has no `live`
key, that is before the forecast is written on chain.

## Resolution

- Due: 2026-11-17 00:00 UTC.
- Outcome = 1 if C_90(e) >= C_90(a), else 0, both values read from `daily[]` of the same
  snapshot: the first daily snapshot fetched on or after the due time. Aggregators revise recent
  days; reading both values from one snapshot avoids mixing vintages. The anchor value frozen
  in `data/live/forecast.json` is not used for the outcome.
- Brier = (P - outcome)^2.

## On chain

- Network: NEAR testnet.
- Contract: the same `contract/posterior_registry.wasm`, on the account
  `brayan-posterior-live.testnet`.
- Right after the commit, the account is locked to a single key that can only call `resolve`.
