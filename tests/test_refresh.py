import hashlib
import json
import re
import shutil
import subprocess

from near_posterior import out, refresh

# What the old workflow committed by hand; a refresh that changes files outside this list
# would have left the pushed tree inconsistent.
OLD_ADD = ("data/raw", "results", "THESIS.md", "README.md", "site", "history.csv",
           "data/refclass/excluded.csv")


def git(root, *args):
    """Run git in root and return stdout; fail on error."""
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True,
                          text=True).stdout


def new_day(root):
    """Change the NEAR snapshot as a new day would: last 12 buyback and revenue values x 1.2."""
    raw = root / "data" / "raw"
    man = json.loads((raw / "manifest.json").read_text(encoding="ascii"))
    for name in ("intents_holders_revenue", "intents_revenue"):
        d = json.loads((raw / f"{name}.json").read_text(encoding="utf-8"))
        for row in d["totalDataChart"][-12:]:
            row[1] = round(row[1] * 1.2)
        body = json.dumps(d, separators=(",", ":")).encode("utf-8")
        (raw / f"{name}.json").write_bytes(body)
        man["files"][name].update(sha256=hashlib.sha256(body).hexdigest(), bytes=len(body))
    man["fetched_at"] = "2026-11-13T06:30:00+00:00"
    (raw / "manifest.json").write_text(json.dumps(man, indent=2) + "\n", encoding="ascii",
                                       newline="\n")


def test_refresh_after_a_new_snapshot_commits_a_consistent_tree(tmp_path):
    root = tmp_path / "repo"
    shutil.copytree(out.ROOT, root, ignore=shutil.ignore_patterns(
        ".git", ".venv", "__pycache__", ".pytest_cache", "*.pyc"))
    git(root, "init", "-q")
    git(root, "config", "user.name", "test")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "core.autocrlf", "false")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    new_day(root)

    assert refresh.main(["--commit"], root=root) == 0
    assert git(root, "status", "--porcelain").strip() == ""
    changed = git(root, "show", "--name-only", "--format=", "HEAD").split()
    assert git(root, "log", "-1", "--format=%s").strip() == refresh.MESSAGE
    assert "history.csv" in changed and "VERIFICATION.md" in changed
    missed = [p for p in changed if not p.startswith(OLD_ADD)]
    assert missed, "the refresh changed only files the old workflow committed"
    assert {"VERIFICATION.md", "docs/DEMO_SCRIPT.md"} <= set(missed)


def test_workflow_runs_the_refresh_module_before_pushing():
    text = (out.ROOT / ".github" / "workflows" / "refresh.yml").read_text(encoding="ascii")
    steps = text.split("steps:", 1)[1]
    assert steps.index("near_posterior.fetch") < steps.index("near_posterior.refresh --commit") \
        < steps.index("git push")
    assert not re.search(r"git add (?!-A)", steps)
    assert "near_posterior.build" not in steps
