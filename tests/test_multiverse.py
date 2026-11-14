import csv
import json
import math

import numpy as np
import pytest

from near_posterior import multiverse, out


def test_72_specifications_and_the_primary_one():
    with open(out.RESULTS / "class_multiverse.csv", encoding="ascii", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 72
    assert len({(r["scale_q"], r["age_lo"], r["age_hi"], r["weighting"], r["categories"])
                for r in rows}) == 72
    head = json.loads((out.RESULTS / "headline.json").read_text(encoding="ascii"))
    prim = [r for r in rows if r["scale_q"] == "3.0" and r["age_lo"] == "270.0"
            and r["age_hi"] == "1095.0" and r["weighting"] == "entity" and r["categories"] == "all"]
    assert len(prim) == 1 and float(prim[0]["P"]) == pytest.approx(head["P"], rel=1e-9)
    assert int(prim[0]["entities"]) == head["entities"]


def test_moment_share_counts_moments():
    Y = np.array([1.0, 1.0, 1.0, -1.0])
    e = np.array([0, 0, 0, 1])
    assert multiverse.moment_share(Y, e, math.e)["P"] == pytest.approx(0.75)


def test_cohorts_leave_one_year_out():
    Y = np.array([2.0, 2.0, -1.0, -1.0])
    e = np.array([0, 1, 2, 3])
    years = np.array([2021, 2021, 2022, 2022])
    res = multiverse.cohorts(Y, e, years, math.e)
    assert res["leave_one_year_out"]["2021"]["P"] == 0.0
    assert res["leave_one_year_out"]["2022"]["P"] == 1.0
    assert res["blocks"] == 4 and res["two_stage_bootstrap"]["mean_block_share"] == 0.5


def test_without_entities_drops_the_named_protocols_only():
    panel = {"ids": ["a", "tether", "b"]}
    sample = {"Y": np.log(np.array([10.0, 1.0, 10.0, 10.0, 1.0])),
              "e": np.array([0, 0, 1, 2, 2])}
    res = multiverse.without_entities(panel, sample, 5.0)
    assert res["excluded_present"] == ["tether"]
    assert res["entities"] == 2 and res["moments"] == 4 and res["P"] == 0.5
    assert "post hoc" in res["label"]
