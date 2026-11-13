"""Rebuild everything in memory and compare it with the committed files, offline.

Run: `python -m near_posterior.verify`. Prints one PASS or FAIL line per check and exits with
code 0 only if every check passes.
"""

import csv
import hashlib
import io
import json
import math
import pathlib
import re
import sys

from near_posterior import ask, build, coverage, onchain, out, readme, refclass, series

FIXTURE = out.ROOT / "tests" / "fixtures" / "near_20261112"
SPEC = out.ROOT / "docs" / "SPEC.md"
SCALARS = {
    "`S_t0`": "S_t0", "`S_{t0-365}`": "S_t0_minus_365", "`I(t0)`": "I_t0", "`r`": "r",
    "`p_t0`": "p_t0", "sum of `b` since 2026-02-23 (262 days)": "b_sum_since_start",
    "`F_NEAR = A_90(f, t0)`": "F_near", "`A_90(f)` for the window ending 2026-05-11": "F_6m",
    "momentum of NEAR Intents at t0": "momentum",
}
WINDOW_COLUMNS = ("A_b", "A_f", "kappa", "C", "inv_C", "k_star_h24")


def close(value: float, printed: str) -> bool:
    """True if value matches a printed control to rel 1e-9 or to its printed precision."""
    decimals = len(printed.split(".")[1]) if "." in printed else 0
    target = float(printed)
    return abs(value - target) <= max(1e-9 * abs(target), 0.5 * 10.0**-decimals)


def same(a, b) -> bool:
    """True if two parsed values are equal, numbers to rel 1e-9 (abs 1e-12)."""
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)
    return a == b


def cell(x: str):
    """Return a CSV cell as a float when it is a number, else the text."""
    try:
        return float(x)
    except ValueError:
        return x


def same_text(rel: str, expected: str, actual: str) -> bool:
    """Compare a generated file with the committed one: JSON and CSV numerically, else exactly."""
    if rel.endswith(".json"):
        return same(json.loads(expected), json.loads(actual))
    if rel.endswith(".csv"):
        def rows(t):
            return [[cell(c) for c in r] for r in csv.reader(io.StringIO(t))]
        return same(rows(expected), rows(actual))
    return expected == actual


def check_controls() -> list[tuple[bool, str]]:
    """Return the checks of the control values of docs/SPEC.md section 5 on the fixture."""
    s = coverage.summary(coverage.load(FIXTURE))
    text = SPEC.read_text(encoding="utf-8").split("## 5. Control values")[1].split("## 6")[0]
    rows = [[c.strip() for c in line.strip().strip("|").split("|")]
            for line in text.splitlines() if line.startswith("|") and "---" not in line]
    bad, n = [], 0
    for r in rows:
        if r[0] in SCALARS:
            n += 1
            if not close(s[SCALARS[r[0]]], r[1].split()[0]):
                bad.append(r[0])
        elif r[0].isdigit():
            w = next(x for x in s["windows"] if x["W"] == int(r[0]))
            for key, printed in zip(WINDOW_COLUMNS, r[1:]):
                n += 1
                if not close(w[key], printed):
                    bad.append(f"{key} W={r[0]}")
    first = [r for r in rows if r[0] == "first day with `f > 0`"][0][1]
    n += 1
    if first.split()[0] != s["first_fee_day"] or f"age {s['age_t0']} days" not in first:
        bad.append("first day / age")
    for printed, h in re.findall(r"([0-9.]+) \(h=(\d+)\)", text):
        n += 1
        if not close(s["G_I"][h], printed):
            bad.append(f"G_I h={h}")
    return [(not bad and n == 37,
             f"control values of docs/SPEC.md section 5 on the registered snapshot ({n} values)"
             + (f": {bad}" if bad else ""))]


def check_manifests() -> list[tuple[bool, str]]:
    """Return the sha256 checks of data/raw and data/refclass against their manifests."""
    res = []
    try:
        series.manifest()
        res.append((True, "data/raw files match data/raw/manifest.json"))
    except ValueError as exc:
        res.append((False, f"data/raw: {exc}"))
    ref = out.ROOT / "data" / "refclass"
    man = json.loads((ref / "manifest.json").read_text(encoding="ascii"))
    bad = [n for n, d in man["files"].items()
           if hashlib.sha256((ref / n).read_bytes()).hexdigest() != d]
    res.append((not bad, "data/refclass files match data/refclass/manifest.json"
                + (f": {bad}" if bad else "")))
    return res


def check_files(files: dict, root: pathlib.Path) -> list[tuple[bool, str]]:
    """Return one check per generated file: the committed copy under root equals the rebuild."""
    res = []
    for rel in sorted(files):
        if rel.startswith("_") or rel == "history.csv":
            continue
        path = root / rel
        ok = path.exists() and same_text(rel, files[rel], path.read_text(encoding="ascii"))
        res.append((ok, f"{rel} regenerates from data/raw and data/refclass"))
    return res


def check_history(files: dict, root: pathlib.Path) -> list[tuple[bool, str]]:
    """Return the check that history.csv holds the current snapshot's row as rebuilt."""
    committed = (root / "history.csv").read_text(encoding="ascii")
    rows = {r[0]: r for r in csv.reader(io.StringIO(committed))}
    rebuilt = {r[0]: r for r in csv.reader(io.StringIO(files["history.csv"]))}
    key = files["_fetched_at"]
    ok = key in rows and same([cell(c) for c in rows[key]], [cell(c) for c in rebuilt[key]])
    return [(ok, f"history.csv holds the row of snapshot {key}")]


def check_readme(files: dict, root: pathlib.Path) -> list[tuple[bool, str]]:
    """Return the checks of every README "see Y" value."""
    text = (root / "README.md").read_text(encoding="ascii")
    head = files["_headline"]
    return [
        (head in text, "README headline line equals the line printed by build"),
        (readme.fill(text, files["_readme_blocks"]) == text,
         "README generated blocks equal the rebuild"),
        (head in (root / "site" / "index.html").read_text(encoding="ascii").replace("&#x27;", "'"),
         "site/index.html shows the same headline line"),
    ]


def check_ask() -> list[tuple[bool, str]]:
    """Return the check that `ask` at the primary k* reproduces the registered headline."""
    head = json.loads((out.RESULTS / "headline.json").read_text(encoding="ascii"))
    panel = refclass.load_panel()
    a = ask.answer(panel, refclass.moments(panel, 24), coverage.summary(coverage.load())["F_near"],
                   ask.primary_k(24))
    ok = (head["model"] != "B0" or head["class"] != "R"
          or (math.isclose(a["P"], head["P"], rel_tol=1e-9) and a["entities"] == head["entities"]
              and all(math.isclose(x, y, rel_tol=1e-9)
                      for x, y in zip(a["interval"], head["interval"]))))
    return [(ok, "ask at the primary k* (h = 24) reproduces the registered headline")]


# README claims and the checks that cover them (VERIFICATION.md).
CLAIMS = [
    ("`uv run pytest -q`: all tests pass", "not a verify check: pytest itself (also run by CI)"),
    ("`verify`: every line starts with PASS", "all checks below"),
    ("`build` prints the headline line of the README", "README headline line equals the line "
     "printed by build"),
    ("`build` leaves `git status` unchanged", "every check ending in 'regenerates from data/raw "
     "and data/refclass', and the history.csv check"),
    ("`ask` prints the registered headline", "ask at the primary k* (h = 24) reproduces the "
     "registered headline"),
    ("`site/index.html` shows the headline number and line", "site/index.html shows the same "
     "headline line; site/index.html regenerates"),
    ("The README charts are current", "site/img/exceedance.svg, levers.svg and calibration.svg "
     "regenerate"),
    ("The finding sentence and limits of the README come from results/", "README generated "
     "blocks equal the rebuild"),
    ("`THESIS.md` reads every number from results/", "THESIS.md regenerates"),
    ("Control values of docs/SPEC.md section 5 are reproduced", "control values check"),
    ("The data are the committed snapshot and frozen panel", "data/raw and data/refclass "
     "manifest checks"),
    ("The registered forecasts are written on NEAR", "on-chain record checks (offline); "
     "`python -m near_posterior.onchain` reads them back from the chain"),
]


def verification_text(checks: list[tuple[bool, str]], t0: str) -> str:
    """Return VERIFICATION.md: every check with its status, and the README claims it covers."""
    L = ["# Verification", "",
         f"Generated by `uv run python -m near_posterior.verify --write` on the snapshot "
         f"t0 = {t0}. `verify` rebuilds every result in memory from `data/raw/` and "
         "`data/refclass/` and compares it with the committed files (JSON and CSV numerically "
         "to a relative 1e-9, text byte for byte).", "",
         f"{sum(ok for ok, _ in checks)} of {len(checks)} checks pass.", "",
         "| Status | Check |", "|---|---|"]
    L += [f"| {'PASS' if ok else 'FAIL'} | {text} |" for ok, text in checks]
    L += ["", "## README claims and the checks that cover them", "",
          "| README claim | Covered by |", "|---|---|"]
    L += [f"| {claim} | {cover} |" for claim, cover in CLAIMS]
    L += ["", "Not covered by `verify`: the result of the CI workflow on Linux, Windows and "
          "macOS (shown by the badge at the top of the README), and what a reader concludes "
          "from the numbers.", ""]
    return "\n".join(L)


def base_checks(root: pathlib.Path = out.ROOT) -> tuple[list[tuple[bool, str]], str]:
    """Return every check except the VERIFICATION.md one, and the snapshot t0."""
    history = root / "history.csv"
    files = build.compute(history.read_text(encoding="ascii") if history.exists() else "")
    checks = (check_controls() + check_manifests() + check_files(files, root)
              + check_history(files, root) + check_readme(files, root) + check_ask()
              + onchain.offline_checks())
    return checks, files["_t0"]


def report_check(checks: list[tuple[bool, str]], t0: str,
                 root: pathlib.Path = out.ROOT) -> tuple[bool, str]:
    """Return the check that VERIFICATION.md lists these checks with their current status."""
    path = root / "VERIFICATION.md"
    ok = path.exists() and path.read_text(encoding="ascii") == verification_text(checks, t0)
    return ok, "VERIFICATION.md lists these checks with their current status"


def run(root: pathlib.Path = out.ROOT) -> list[tuple[bool, str]]:
    """Return every check as (passed, description); the last one is VERIFICATION.md itself."""
    checks, t0 = base_checks(root)
    return checks + [report_check(checks, t0, root)]


def main(argv=None) -> int:
    """Print one PASS/FAIL line per check; with --write, rewrite VERIFICATION.md first."""
    argv = sys.argv[1:] if argv is None else argv
    checks, t0 = base_checks()
    if "--write" in argv:
        out.write_text(out.ROOT / "VERIFICATION.md", verification_text(checks, t0))
    checks = checks + [report_check(checks, t0)]
    for ok, text in checks:
        print(f"{'PASS' if ok else 'FAIL'} {text}")
    return 0 if all(ok for ok, _ in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
