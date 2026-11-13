import datetime as dt
import json

import numpy as np

from near_posterior import coverage, out, refclass, validation, verify


def setup(h):
    panel = refclass.load_panel()
    ov = refclass.origin_values(panel)
    return panel, ov, refclass.moments(panel, h, ov)


def test_class_has_no_look_ahead_and_never_the_target_entity():
    panel, ov, mom = setup(24)
    ok = refclass.resolved(mom)
    targets = np.flatnonzero(validation.target_mask(mom, ov))
    for i in targets[:: max(1, targets.size // 60)]:
        cls = validation.class_mask(mom, ok, int(mom["e"][i]), int(mom["month"][i]),
                                    float(mom["F"][i]), float(mom["age"][i]), 24)
        assert (mom["month"][cls] + 24 <= mom["month"][i]).all()
        assert (mom["e"][cls] != mom["e"][i]).all()
        assert ok[cls].all()


def test_target_with_near_scale_and_age_gets_class_r():
    panel, ov, mom = setup(24)
    F_near = coverage.summary(coverage.load())["F_near"]
    ok = refclass.resolved(mom)
    month = refclass.month_index(dt.date(2027, 1, 1))
    cls = validation.class_mask(mom, ok, -1, month, F_near, 550.0, 24)
    assert np.array_equal(cls, refclass.in_class(mom, "R", F_near, panel) & ok)


def test_counts_of_the_registered_rule():
    v = json.loads((out.RESULTS / "validation.json").read_text(encoding="ascii"))
    s12, s24 = v["S1"]["12"], v["S1"]["24"]
    assert (s12["candidates"], s12["scored"], s12["entities"]) == (2730, 1659, 188)
    assert s12["origins_by_year"] == {"2023": 102, "2024": 494, "2025": 1063}
    assert (s24["candidates"], s24["scored"], s24["entities"]) == (1390, 201, 51)


def test_s2_counts_on_the_registered_snapshot():
    # S2 uses class R, whose scale band follows F_NEAR: its counts move with the daily snapshot,
    # so they are pinned on the registered one.
    panel, ov, mom = setup(24)
    F_registered = coverage.summary(coverage.load(verify.FIXTURE))["F_near"]
    s2 = validation.run_s2(panel, ov, {24: mom}, F_registered)
    assert (s2["scored"], s2["entities"]) == (92, 31)
