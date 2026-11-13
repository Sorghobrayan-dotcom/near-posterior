import csv

from near_posterior import build, out, thesis

SECTIONS = ["## 1. Summary", "## 2. The question", "## 3. The outside view",
            "## 4. Does NEAR Intents' own momentum change this?",
            "## 5. At month 24, and at any point within 24 months", "## 6. What NEAR controls",
            "## 7. How we know the method works", "## 8. Correcting for past over-forecasting",
            "## 9. Robustness",
            "## 10. How other theses measure the same thing, and what they need to be true",
            "## 11. What would change our mind", "## 12. What this cannot tell you",
            "## 13. Pre-registration, addenda, deviations, resolution"]


def test_thesis_regenerates_byte_identically_from_results():
    text = (out.ROOT / "THESIS.md").read_text(encoding="ascii")
    assert thesis.render(thesis.load_results()) == text
    assert "\r" not in text


def test_thesis_has_the_thirteen_sections_in_order():
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
