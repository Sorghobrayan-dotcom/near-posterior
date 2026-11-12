# Tasks

One task = one commit (or a few small ones), tests green before each commit.
Order matters: T1 to T9 are the product; T10 to T12 are optional or human.
Each task maps to the GitHub issue of the same number.

## T1 - Coverage and required multiple
Scope: `coverage.py`, NearBlocks readers in `series.py`, tests.
Done when: the control table of `docs/SPEC.md` section 5 is reproduced on
`tests/fixtures/near_20261112`; the identity test passes; `results/coverage.json` is written.
If the control values are not reproduced: stop and write why in `PROGRESS.md`.

## T2 - Reference panel fetch
Scope: `refclass_fetch.py`, `data/refclass/*`.
Done when: the panel is fetched once under PREREG 2.2, merged by parent, written with a
sha256 manifest; `missing.txt` names every failed slug; the share missing is printed;
a test checks the manifest against the files. Stop rule: more than 5 percent missing.

## T3 - Moments, classes, outcomes
Scope: `refclass.py`, synthetic-panel tests of SPEC section 6.
Done when: all six synthetic cases pass; on the real panel the number of entities and
moments in R, R_strict, R_all_ages, R_trading at h = 12, 24, 36 is written to
`results/refclass_counts.json`; `excluded.csv` is written. Stop rule: R below 30 entities
at h = 24.

## T4 - Forecast and scoring
Scope: `forecast.py`, `scoring.py`, tests.
Done when: class frequency with cluster bootstrap and Clopper-Pearson, analogs, Brier,
CRPS (sample and Normal), coverage and PIT are implemented and tested as in SPEC section 6.

## T5 - Backtest and model choice
Scope: `backtest.py`, tests, `results/backtest.json`.
Done when: rolling-origin scores for B0, B1, B2, A_30, A_60, A_120 at h = 12 and 24 are
written with intervals and by year; dropped targets are counted; `select_model` applies
PREREG 6 exactly; the no-look-ahead tests pass.

## T6 - Many-analysts audit
Scope: `data/claims.csv`, `audit.py`, `results/audit.csv`.
Done when: at least 10 public NEAR theses are recorded, each row with repository URL,
commit SHA (`git ls-remote`), file, line, value, unit, window, end date and stated source;
replication, decomposition and dispersion follow PREREG 10; a value that cannot be
recomputed is marked "not recomputed". No judgement words about other teams anywhere.
Candidate list: `docs/THESES.md`.

## T7 - Specification curve, headline, thesis
Scope: `speccurve.py`, `thesis.py`, `build.py`, `results/*`, `THESIS.md`, `history.csv`.
Done when: 864 rows are written; the headline follows PREREG 6 to 8; `THESIS.md` has the
nine sections of SPEC section 7 and regenerates byte-identically.

## T8 - Static page
Scope: `site.py`, `site/index.html`.
Done when: the page has the seven charts of SPEC section 8, each with its query and one
sentence; ASCII only; no external request; regenerates byte-identically.

## T9 - Verify command, README, CI
Scope: `verify.py`, `README.md`, `.github/workflows/check.yml`, `refresh.yml`.
Done when: `verify` prints only `PASS` on a fresh clone in a new directory; the README
follows SPEC section 9 and every "see Y" value is checked by `verify`; workflows exist.

## T10 - Optional: second route for total supply from the NEAR RPC
Read `total_supply` from the block header at `t0` and `t0 - 365` on an archival RPC and
compare with NearBlocks. Report the difference. Skip if it takes more than one hour.

## T11 - Optional: a governance issuance scenario from a primary source
Only if the proposal text is read at its primary source. Add it as an extra, labelled row,
never replacing a registered row, and record it in `DEVIATIONS.md`.

## T12 - Human: submission
Mainnet NEAR account; demo video; X post tagged @NEARProtocol #NEARHackathon; make the
repository public; tags `pre-hackathon` (none needed here) and `hackathon-submission`;
tracks `thesis` and `open`; form sent by the author before 2026-11-14 23:59 UTC.
