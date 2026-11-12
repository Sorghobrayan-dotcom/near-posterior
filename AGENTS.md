# Rules for coding agents

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
