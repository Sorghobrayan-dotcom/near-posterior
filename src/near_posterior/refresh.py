"""Daily refresh after a new NEAR snapshot: build, verify --write, commit, verify again.

Run: `python -m near_posterior.refresh [--commit]` after `python -m near_posterior.fetch`.
The reference panel is never refetched. With `--commit`, every changed file is committed
(`git add -A`), then a plain `verify` runs on the committed tree and `git status --porcelain`
must be empty; the exit code is 0 only if all of this holds, so the workflow pushes only then.
"""

import os
import pathlib
import subprocess
import sys

from near_posterior import out

MESSAGE = "chore(data): daily NEAR snapshot refresh"


def python(args: list[str], root: pathlib.Path) -> subprocess.CompletedProcess:
    """Run `python -m ...` on the package of `root`, offline, capturing its output."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root / "src") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, *args], cwd=root, env=env, capture_output=True,
                          text=True)


def git(args: list[str], root: pathlib.Path) -> subprocess.CompletedProcess:
    """Run a git command in `root`, capturing its output."""
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def failures(output: str) -> list[str]:
    """Return the FAIL lines of a verify run."""
    return [line for line in output.splitlines() if line.startswith("FAIL")]


def main(argv=None, root: pathlib.Path = out.ROOT) -> int:
    """Build, rewrite VERIFICATION.md, optionally commit everything, verify the result."""
    argv = sys.argv[1:] if argv is None else argv
    where = python(["-c", "from near_posterior import out; print(out.ROOT)"], root).stdout.strip()
    if not where or pathlib.Path(where).resolve() != pathlib.Path(root).resolve():
        print(f"refresh: the package imported from {root} resolves to {where!r}; stopping")
        return 1
    for step in (["-m", "near_posterior.build"], ["-m", "near_posterior.verify", "--write"]):
        r = python(step, root)
        print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "", flush=True)
        if r.returncode:
            print(f"refresh: {' '.join(step[1:])} failed", *failures(r.stdout), r.stderr[-2000:],
                  sep="\n")
            return 1
    if "--commit" in argv:
        git(["add", "-A"], root)
        if git(["diff", "--cached", "--quiet"], root).returncode:
            c = git(["commit", "-q", "-m", MESSAGE], root)
            if c.returncode:
                print("refresh: git commit failed", c.stderr, sep="\n")
                return 1
    r = python(["-m", "near_posterior.verify"], root)
    bad = failures(r.stdout)
    status = git(["status", "--porcelain"], root).stdout.strip() if "--commit" in argv else ""
    print(f"refresh: verify on the committed tree: {len(bad)} FAIL; "
          f"uncommitted changes: {'none' if not status else status}")
    return 0 if r.returncode == 0 and not bad and not status else 1


if __name__ == "__main__":
    sys.exit(main())
