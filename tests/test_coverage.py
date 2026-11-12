import datetime as dt
import pathlib
import random

import pytest

from near_posterior import coverage

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "near_20261112"

# docs/SPEC.md section 5, copied as printed.
CONTROL = {
    "S_t0": "1311473431.762788",
    "S_t0_minus_365": "1279706922.253202",
    "I_t0": "31766509.509586",
    "r": "0.02482327",
    "p_t0": "3.58413601",
    "b_sum_since_start": "8059471.05",
    "F_near": "75897110.4444",
    "F_6m": "41486463.7222",
    "momentum": "0.60401141",
}
WINDOWS = {
    "30": ("21936451.3333", "70346462.1667", "0.31183446", "0.1926692442", "5.190242", "5.451118"),
    "90": ("20751795.1667", "75897110.4444", "0.27342010", "0.1822643339", "5.486537", "5.762305"),
    "180": ("13894744.9722", "55928720.8611", "0.24843667", "0.1220384269", "8.194140", "8.606000"),
    "since": ("11227889.0582", "51445125.6107", "0.21824981", "0.0986152622", "10.140418",
              "10.650103"),
}
G_I = {"12": "1.02482327", "24": "1.05026273", "36": "1.07633369"}


def close(value: float, printed: str) -> bool:
    """True if value matches the printed control to rel 1e-9 or to its printed precision."""
    decimals = len(printed.split(".")[1]) if "." in printed else 0
    target = float(printed)
    return abs(value - target) <= max(1e-9 * abs(target), 0.5 * 10.0**-decimals)


@pytest.fixture(scope="module")
def summary():
    return coverage.summary(coverage.load(FIXTURE))


def test_t0_and_age(summary):
    assert summary["t0"] == "2026-11-11"
    assert summary["first_fee_day"] == "2025-05-10"
    assert summary["age_t0"] == 550
    assert summary["buyback_days"] == 262
    assert summary["F_6m_end"] == "2026-05-11"


@pytest.mark.parametrize("key", sorted(CONTROL))
def test_control_scalars(summary, key):
    assert close(summary[key], CONTROL[key]), (key, summary[key])


@pytest.mark.parametrize("label", sorted(WINDOWS))
def test_control_windows(summary, label):
    row = next(w for w in summary["windows"] if w["window"] == label)
    got = (row["A_b"], row["A_f"], row["kappa"], row["C"], row["inv_C"], row["k_star_h24"])
    for value, printed in zip(got, WINDOWS[label]):
        assert close(value, printed), (label, value, printed)
    if label == "since":
        assert row["W"] == 262


def test_control_growth_of_issuance(summary):
    for h, printed in G_I.items():
        assert close(summary["G_I"][h], printed), (h, summary["G_I"][h])


def test_identity_on_random_inputs():
    rng = random.Random(7)
    start = dt.date(2020, 1, 1)
    for _ in range(50):
        n = 1200
        days = [start + dt.timedelta(days=i) for i in range(n)]
        f = {d: rng.uniform(1, 1e6) for d in days}
        b = {d: f[d] * rng.uniform(0, 0.5) for d in days}
        S = {d: 1e9 * (1 + 0.0001 * i + rng.uniform(0, 1e-5)) for i, d in enumerate(days)}
        p = {d: rng.uniform(0.5, 10) for d in days}
        t0, t1 = days[500], days[500 + rng.randrange(1, 600)]
        c0, c1 = coverage.coverage(b, S, p, t0, 90), coverage.coverage(b, S, p, t1, 90)
        g_F = coverage.annualised(f, t1, 90) / coverage.annualised(f, t0, 90)
        g_k = coverage.capture(b, f, t1, 90) / coverage.capture(b, f, t0, 90)
        g_I = coverage.issuance(S, t1) / coverage.issuance(S, t0)
        g_P = p[t1] / p[t0]
        assert c1 == pytest.approx(c0 * g_F * g_k / (g_I * g_P), rel=1e-12)
        k_star = coverage.required_multiple(c0, g_I, g_P, g_k)
        assert (c1 >= 1) == (g_F >= k_star) or abs(c1 - 1) < 1e-9


def test_scenario_grid_has_216_rows():
    rows = coverage.scenario_grid(coverage.load(FIXTURE))
    assert len(rows) == 4 * 3 * 3 * 2 * 3
    primary = [r for r in rows if r["window"] == "90" and r["h"] == 24 and r["capture"] == "constant"
               and r["issuance"] == "constant" and r["G_P"] == 1.0]
    assert len(primary) == 1 and close(primary[0]["k_star"], "5.762305")


def test_window_names_missing_days():
    x = {dt.date(2026, 1, 1): 1.0}
    with pytest.raises(ValueError, match="missing days"):
        coverage.annualised(x, dt.date(2026, 1, 2), 2)
