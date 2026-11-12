import csv

from near_posterior import build, out, thesis

SECTIONS = ["## 1. The claim", "## 2. Evidence for", "## 3. Evidence against",
            "## 4. What would change our mind", "## 5. How other theses measure the same thing",
            "## 6. Backtest", "## 7. Specification curve", "## 8. What this cannot tell you",
            "## 9. Deviations from the pre-registration"]


def test_thesis_regenerates_byte_identically_from_results():
    text = (out.ROOT / "THESIS.md").read_text(encoding="ascii")
    assert thesis.render(thesis.load_results()) == text
    assert "\r" not in text


def test_thesis_has_the_nine_sections_in_order():
    text = (out.ROOT / "THESIS.md").read_text(encoding="ascii")
    positions = [text.index(s) for s in SECTIONS]
    assert positions == sorted(positions)


def test_speccurve_csv_has_864_complete_rows():
    with open(out.RESULTS / "speccurve.csv", encoding="ascii", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 864
    assert all(v != "" for r in rows for v in r.values())


def test_history_holds_the_current_snapshot_once():
    res = thesis.load_results()
    text = (out.ROOT / "history.csv").read_text(encoding="ascii")
    assert build.history_text(text, res["headline"]) == text
    rows = list(csv.DictReader(text.splitlines()))
    assert [r["fetched_at"] for r in rows].count(res["headline"]["fetched_at"]) == 1
