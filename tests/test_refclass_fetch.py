import csv
import hashlib
import json

from near_posterior import refclass_fetch as rf

REF = rf.REF


def read_csv(name):
    with open(REF / name, encoding="ascii", newline="") as fh:
        return list(csv.DictReader(fh))


def test_manifest_matches_files():
    man = json.loads((REF / "manifest.json").read_text(encoding="ascii"))
    derived = {"manifest.json", "excluded.csv"}  # excluded.csv is written by refclass.py (T3)
    names = sorted(p.name for p in REF.iterdir() if p.name not in derived)
    assert sorted(man["files"]) == names
    for name, digest in man["files"].items():
        assert hashlib.sha256((REF / name).read_bytes()).hexdigest() == digest, name


def test_every_universe_slug_is_fetched_or_named_missing():
    man = json.loads((REF / "manifest.json").read_text(encoding="ascii"))
    universe = {r["slug"]: r for r in read_csv("universe.csv")}
    missing = set((REF / "missing.txt").read_text(encoding="ascii").split())
    in_entities = {s for r in read_csv("entities.csv") for s in r["slugs"].split(";")}
    assert missing == {s for s, r in universe.items() if r["fetched"] == "0"}
    assert missing == set(man["missing_reasons"])
    assert in_entities | missing == set(universe)
    assert not in_entities & missing
    assert rf.TARGET not in universe
    assert man["universe"] == len(universe) and man["missing"] == len(missing)
    assert abs(man["missing_share"] - len(missing) / len(universe)) < 1e-12


def test_panel_matches_entities_and_raw_entries():
    panel = rf.read_gz_csv((REF / "panel.csv.gz").read_bytes())
    counts = {}
    for eid, _, _ in panel:
        counts[eid] = counts.get(eid, 0) + 1
    ents = read_csv("entities.csv")
    assert {r["entity_id"]: int(r["n_days"]) for r in ents} == counts
    overview = json.loads(rf.gzip.decompress((REF / "overview.json.gz").read_bytes()))
    missing = set((REF / "missing.txt").read_text(encoding="ascii").split())
    entries = [e for e in rf.universe(overview) if e["slug"] not in missing]
    raw = rf.read_gz_csv((REF / "raw_entries.csv.gz").read_bytes())
    entity_rows, panel_rows = rf.merge_entities(entries, raw)
    rebuilt = rf.gz_csv(["entity_id", "date", "fees"], panel_rows)
    # compressed bytes depend on the platform's zlib build; the content must be identical
    assert rf.gzip.decompress(rebuilt) == rf.gzip.decompress((REF / "panel.csv.gz").read_bytes())
    assert rf.same_content("panel.csv.gz", (REF / "panel.csv.gz").read_bytes(), rebuilt)
    assert [r[0] for r in entity_rows] == [r["entity_id"] for r in ents]


def test_merge_by_parent():
    entries = [
        {"slug": "a", "name": "A", "totalAllTime": 5, "category": "Dexs", "parentProtocol": "parent#x"},
        {"slug": "b", "name": "B", "totalAllTime": 9, "category": "Lending", "parentProtocol": "parent#x"},
        {"slug": "c", "name": "C", "totalAllTime": 2, "category": "Yield"},
    ]
    raw = [["a", "2024-01-01", "1"], ["b", "2024-01-01", "2.5"], ["b", "2024-01-02", "3"],
           ["c", "2024-01-05", "0"]]
    ents, panel = rf.merge_entities(entries, raw)
    assert ents == [["c", "C", "Yield", "c", "2024-01-05", "2024-01-05", 1],
                    ["parent#x", "x", "Lending", "a;b", "2024-01-01", "2024-01-02", 2]]
    assert panel == [["c", "2024-01-05", "0.0"], ["parent#x", "2024-01-01", "3.5"],
                     ["parent#x", "2024-01-02", "3.0"]]


def test_gzip_content_is_reproducible():
    a, b = rf.gz_csv(["x"], [[1]]), rf.gz_csv(["x"], [[1]])
    assert rf.gzip.decompress(a) == rf.gzip.decompress(b) == b"x\n1\n"
    assert rf.same_content("t.gz", a, b) and not rf.same_content("t.gz", a, rf.gz_csv(["x"], [[2]]))
