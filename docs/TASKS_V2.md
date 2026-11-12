# Tasks, second pass

The first pass (T1 to T10) is verified: an independent recomputation reproduced the headline,
the class counts, the 12-month backtest and the 32 audited values. This pass makes the project
stronger in substance and in form. `PREREG.md` stays untouched and its headline stays the
headline. The rules of every new analysis are in `PREREG_2.md` (sections S1 to S12): implement
them as written, report them whatever the outcome, and label them "secondary (specified after
the primary results)" wherever they appear.

Same rules as `AGENTS.md`. One task = one commit, tests green, `build` and `verify` green,
`PROGRESS.md` updated. Every new result file is covered by `verify`. Do not push.

Order: U1 to U12. Cut order if time runs out: U13, U11, the two-stage bootstrap of U6, forward
claims beyond the first eight in U7. Never cut U1, U2, U4, U5, U8, U9, U10.

## U1 - Wording, limits and unverified claims

- The registered event is "at month 24", not "within 24 months". Fix the headline line, the
  README, `THESIS.md`, the page and `history.csv` verdict text: "at the 24-month mark".
  "Within" is used only for S4.
- Audit status label: "not reproduced by us"; add one sentence: the status compares their
  figure with our recomputation under our reading of their definition, to 2 percent; it does
  not say their figure is wrong.
- Limits to add (THESIS, README, page): age is the age in DefiLlama's data, not since launch;
  class R mixes fee types (trading fees, interest, staking yield) and `R_trading` is shown
  next to R; the dead fill uses the panel end `D` (note of T5); class R selects protocols at a
  high point of their fees, so part of the typical decline is regression to the mean.
- README: state only what was run. "Windows: run locally. Linux and macOS: run by CI" once CI
  has run; until then say "not yet run".
- `check.yml`: add `macos-latest`.

## U2 - Exceedance curve, coverage distribution, `ask` (S3, S5)

- `results/exceedance.csv` (h, k, P, P_lo, P_hi), `results/growth_quantiles.json`,
  `results/entities_R.csv` (per entity and horizon: category, moments, successes at k*, largest
  growth and its origin), `results/coverage_quantiles.json`.
- `python -m near_posterior.ask --k 5.76 --h 24` prints the base rate, its interval, the number
  of entities and the entities that reached it; `--k` defaults to the primary k* of the horizon.
  `--slug <entity_id>` (after U4) answers the same question for any entity of the frozen panel
  with a class centred on that entity's latest valid moment (S1 construction).
- Tests: `ask` at the primary k* returns the registered headline; P is non-increasing in k.

## U3 - At any point within the horizon (S4)

`results/within.json`: P_within and interval at h = 12, 24, 36, next to the registered values.
Test on a synthetic entity that crosses the threshold at month 10 and falls back by month 24.

## U4 - Method validation (S1, S2)

- `results/validation.json`, `results/validation_targets.csv`, reliability tables included.
- Tests: no pool moment with `t' + h > tau`; the target's entity never in its class; for a
  synthetic target with the scale and age of NEAR Intents the class equals class R.
- Expected counts (computed without reading outcomes, corrected 2026-11-12, see the erratum in
  `DEVIATIONS.md`): h = 12: 2730 candidates, 1659 scored, 188 entities, origins 2023 (102),
  2024 (494), 2025 (1063); h = 24: 1390 candidates, 201 scored, 51 entities, origins 2024.
  If your counts differ, stop and say why before going on.

## U5 - Lever table and governance scenario (S6, S10)

- `results/levers.csv` (60 cells + labelled governance rows if S10 succeeds).
- S10: find the text of the issuance proposal that other theses call HSP-029 at a primary
  source. Record URL, date read and the quoted parameter in `data/governance.json`. If no
  primary source is reachable, write that in `PROGRESS.md` and in the thesis; do not use a
  secondary source.

## U6 - Class multiverse and cohorts (S7, S8)

`results/class_multiverse.csv` (72 rows), `results/cohorts.json`.

## U7 - Forward requirements of other theses (S9) and a wider audit

- Extend `data/claims.csv` to at least 15 theses. Read in priority: soldanoandrea/near-thesis,
  EmekaManuel/nearquery, bomanaps/-near-intents-thesis, Apihpih96/near-intents-thesis,
  Alberto-Campos-de-la-Torre/near-settlement-thesis, tobadaniel/NEAR-Thesis.
- New `data/forward_claims.csv` and `results/forward_claims.csv`: at least eight forward
  requirements or assumptions (for example "revenue must grow N times to offset issuance",
  "volume must grow N times for a 2 percent yield", a growth rate in a valuation model).

## U8 - The thesis as an essay

`THESIS.md` stays generated (every number from `results/`), but it reads as an argument, in
plain sentences, for an investor who has ten minutes. Sections, in this order:

1. Summary: five sentences. The question; coverage today and the required growth; the base
   rate and its interval; what governance can and cannot change (from U5); how the method was
   checked (from U4), with its weakest point named.
2. The question: buybacks against net issuance; coverage today by window; the required multiple
   and how much it moves with the window alone.
3. The outside view: how class R is built and why; the exceedance curve in words; the typical
   path (median growth, share ending at zero); a table of the entities that reached k*, with
   category and origin year, and one sentence on what kind of fees they earn.
4. Does NEAR Intents' own momentum change this? The analog results.
5. At month 24, and at any point within 24 months (U3).
6. What NEAR controls: the lever table read in sentences: growth alone; capture alone;
   issuance alone; the combination needed for even odds, or the statement that none in the
   table reaches it.
7. How we know the method works: the registered 12-month backtest, then S1 and S2, with the
   calibration tables; where the evidence is thin, say it first.
8. Robustness: specification curve, class multiverse, cohorts.
9. How other theses measure the same thing, and what they need to be true (U7).
10. What would change our mind.
11. What this cannot tell you.
12. Pre-registration, addendum, deviations, resolution dates.

Sentences adapt to the numbers (direction and verdict computed, as now). No adjectives of
praise, no certainty the data does not give.

## U9 - The page

One file, still offline and deterministic, ASCII. Inline JavaScript without any dependency is
allowed for one thing: the explorer. The page must be complete without JavaScript.

- Top: the question, the headline number large, its interval, the snapshot date, one line on
  the method, links to `THESIS.md`, `PREREG.md`, `PREREG_2.md`.
- Explorer: a slider for the required multiple k and a horizon switch (12, 24, 36); it shows
  the base rate with its interval and the entities that reached it, from data embedded in the
  page (S3). Default position: the primary k*. Markers on the curve for k* by window and for the
  forward requirements of other theses (U7).
- Charts: coverage since 2026-02-23; exceedance curve with interval band; coverage
  distribution at 12, 24, 36 months; lever table as a heat map; calibration (reliability) of
  C0 against B2; backtest scores; class multiverse and specification curve; cohorts.
- Tables: who reached k*; nearest analogs; other theses (measurements and forward requirements).
- Each chart keeps its "Query:" line and one plain sentence.
- Readable at 380 px width. One accent colour, one neutral scale, labels on the charts, no legend
  that needs colour matching.
- Standalone SVG files of three charts in `site/img/` (exceedance, levers, calibration) for the
  README.

## U10 - README, verification report

- First screen: one-sentence finding with the number and date; the exceedance chart; the
  "do X, see Y" table including `ask`; the lever chart.
- `VERIFICATION.md` (generated by `verify --write`): every check with its status, and for each
  claim made in the README the check that covers it.
- `verify` covers every new result file and the three README images.

## U11 - Resolution (S11)

`results/registered_forecast.json`, `python -m near_posterior.resolve`, `RESOLUTION.md`
(dates, rule, command). Test with a synthetic later snapshot.

## U12 - CI, pages, material for the author

- `pages.yml`: deploy `site/` to GitHub Pages on push to `main` (it will work once the
  repository is public).
- `docs/DEMO_SCRIPT.md`: a 75-second demo, shot by shot (command, headline, explorer, who
  reached it, lever table, calibration, pre-registration).
- `docs/X_POST.md`: a draft post following the advice of `HACKATHON.md` (lead with the problem,
  one complete moment, what NEAR's data made possible, link, a real question). The author posts.

## U13 - Optional: second route for buybacks (S12)
