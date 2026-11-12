import shutil

import pytest

from near_posterior import build, out, verify


@pytest.fixture(scope="module")
def files():
    history = (out.ROOT / "history.csv").read_text(encoding="ascii")
    return build.compute(history)


def copy_committed(files, root):
    """Copy every committed generated file under root."""
    for rel in list(files) + ["history.csv"]:
        if rel.startswith("_"):
            continue
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out.ROOT / rel, dst)


def test_committed_files_pass(files, tmp_path):
    copy_committed(files, tmp_path)
    checks = (verify.check_files(files, tmp_path) + verify.check_history(files, tmp_path)
              + verify.check_readme(files, tmp_path))
    assert all(ok for ok, _ in checks), [t for ok, t in checks if not ok]


def test_altered_result_fails(files, tmp_path):
    copy_committed(files, tmp_path)
    path = tmp_path / "results" / "headline.json"
    text = path.read_text(encoding="ascii")
    path.write_text(text.replace('"entities": 75', '"entities": 74', 1), encoding="ascii",
                    newline="\n")
    if text == path.read_text(encoding="ascii"):
        path.write_text(text.replace('"model": "', '"model": "X', 1), encoding="ascii",
                        newline="\n")
    checks = dict((t, ok) for ok, t in verify.check_files(files, tmp_path))
    assert not checks["results/headline.json regenerates from data/raw and data/refclass"]
    assert sum(not ok for ok in checks.values()) == 1


def test_altered_number_in_csv_fails(files, tmp_path):
    copy_committed(files, tmp_path)
    path = tmp_path / "results" / "speccurve.csv"
    lines = path.read_text(encoding="ascii").split("\n")
    cells = lines[1].split(",")
    cells[-5] = str(float(cells[-5]) + 0.001)
    lines[1] = ",".join(cells)
    path.write_text("\n".join(lines), encoding="ascii", newline="\n")
    checks = dict((t, ok) for ok, t in verify.check_files(files, tmp_path))
    assert not checks["results/speccurve.csv regenerates from data/raw and data/refclass"]


def test_controls_and_manifests_pass():
    assert all(ok for ok, _ in verify.check_controls() + verify.check_manifests())
