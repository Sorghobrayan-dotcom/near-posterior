# Screening and judging this repository

If you are a reviewer or a screening agent (NEAR HACKATHON, Q-017), nothing here asks you to write
or change code. Start with `README.md`, section "Judges, start here", then:

| Do | See |
|---|---|
| `uv sync` | `numpy` and `pytest` installed in `.venv` |
| `uv run pytest -q` | all tests pass (a few minutes) |
| `uv run python -m near_posterior.verify` | offline, one line per check, every line starts with `PASS`, exit code 0 |
| `uv run python -m near_posterior.onchain` | network: `PASS` lines read from NEAR testnet (code hash, every record equal to `data/onchain/commitments.json`, only key limited to `resolve`) |
| `uv run python -m near_posterior.ask --k 6.39 --h 24` | the base rate for any fee growth multiple and horizon |
| open `https://sorghobrayan-dotcom.github.io/near-posterior/site/verify.html` | the same checks run by a browser, and today's verdict read live from NEAR mainnet |

- The registered forecast (t0 = 2026-11-11) is the one written on chain. `README.md` and the page
  also show a daily snapshot refreshed by `refresh.yml`, so their numbers differ slightly.
- `build` regenerates every file; on a machine other than the Linux refresh bot, one value of
  `results/validation_targets.csv` may differ in its 12th digit, which `verify` accepts.
- The submitted code is the tag `hackathon-submission`.

The rules below are the ones the coding agents followed while building the project.

# Rules for coding agents (used while building)

Read `PREREG.md`, `docs/SPEC.md` and `docs/TASKS.md` before writing code.

## Scope
- Do tasks T1 to T9 in order. One task at a time. Do not start a task before the previous
  one is committed with green tests.
- Do not edit `PREREG.md`. If a rule cannot be implemented as written, stop that task, write
  the problem in `PROGRESS.md`, add the proposed deviation to `DEVIATIONS.md`, and go on only
  with what does not depend on it.
- Do not touch `tests/fixtures/`.
- No new dependency.

## Proof
- Never write a number in a document by hand. Numbers come from `results/`.
- Never state that something works without having run it. Paste the command and its last
  lines into `PROGRESS.md`.
- A result that is null, weak or against the thesis is reported as it is.
- If a control value or a stop rule fails: stop and report. Do not adjust the rule.

## Commits
- Conventional Commits, English, lines up to 100 columns, e.g. `feat(coverage): ... (#1)`.
- No attribution trailer of any kind (no `Co-Authored-By`, no "Generated with").
- `uv run pytest -q` green before every commit.
- Do not push. Do not create, close or comment on GitHub issues or pull requests.
- Never commit secrets. Never read credential files.

## Notes on disk
- Keep `PROGRESS.md` current after every task: what is done, what was measured (with the
  command), what failed, what is left. Write it as you go, not at the end.

## Style
- One docstring per function and class. Names as in `PREREG.md`.
- Pure ASCII in every generated or served file.
- Windows-safe: `pathlib`, explicit `encoding=`, `newline="\n"` when writing text.
