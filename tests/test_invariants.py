"""SPEC 8 invariants on a seeded random grid.

Grid: tails {1, 2}, d 0.1..2, alpha 0.001..0.2, power 0.6..0.99, ratio 0.25..4.
"""

from __future__ import annotations

import math
import random

import pytest

from gpower_clone import engine

T2 = "t2-indep"


def _grid(seed: int, n: int):
    rng = random.Random(seed)
    cases = []
    for _ in range(n):
        cases.append({
            "tails": rng.choice([1, 2]),
            "d": rng.uniform(0.1, 2.0),
            "alpha": math.exp(rng.uniform(math.log(0.001), math.log(0.2))),
            "power": rng.uniform(0.6, 0.99),
            "ratio": math.exp(rng.uniform(math.log(0.25), math.log(4.0))),
        })
    return cases


GRID = _grid(20261023, 60)


def _ok(params: dict) -> dict:
    out, code = engine.run(params)
    assert code == 0, (params, out)
    return out


def _apriori(c: dict) -> dict:
    return _ok({"test": T2, "mode": "a-priori", "tails": c["tails"], "d": c["d"], "alpha": c["alpha"],
                "power": c["power"], "ratio": c["ratio"]})


def _posthoc(tails, d, alpha, n1, n2) -> float:
    return _ok({"test": T2, "mode": "post-hoc", "tails": tails, "d": d, "alpha": alpha,
                "n1": n1, "n2": n2})["power"]


def _cont_power(c: dict, n_tot: float) -> float:
    """Power on the continuous ratio-preserving path at total N (SPEC 3.1 step 1)."""
    r = c["ratio"]
    return engine.power_of(c["tails"], c["d"], c["alpha"], n_tot / (1 + r), r * n_tot / (1 + r))


@pytest.mark.parametrize("c", GRID)
def test_apriori_posthoc_and_minimality(c):
    a = _apriori(c)
    # SPEC 8: n_total even and >= 4, split rule, integer df
    assert a["n_total"] % 2 == 0 and a["n_total"] >= 4
    assert a["n_total"] == a["n1"] + a["n2"]
    assert a["df"] == a["n_total"] - 2
    assert a["n1"] == math.floor(a["n_total"] / (1 + c["ratio"]) + 0.5)
    if a["n1"] < 2 or a["n2"] < 2:
        assert "warning" in a
    else:
        assert "warning" not in a
        # post-hoc on the a-priori sample sizes reproduces actual_power byte for byte
        # (actual_power >= target is NOT an invariant: split rounding, SPEC 3.1 step 6)
        ph = _posthoc(c["tails"], c["d"], c["alpha"], a["n1"], a["n2"])
        assert ph == a["actual_power"]
    # the even total reaches the target on the continuous path ...
    assert _cont_power(c, a["n_total"]) >= c["power"] - 1e-12
    # ... and minimality: the previous even total does not (only when n_total > 4)
    if a["n_total"] > 4:
        assert _cont_power(c, a["n_total"] - 2) < c["power"]


@pytest.mark.parametrize("c", GRID[:40])
def test_criterion_alpha_gives_target_power(c):
    a = _apriori(c)
    cr = _ok({"test": T2, "mode": "criterion", "tails": c["tails"], "d": c["d"], "power": c["power"],
              "n1": a["n1"], "n2": a["n2"]})
    assert 0.0 < cr["alpha"] < 1.0
    # alpha <= input alpha exactly when the integer split reached the target
    if a["actual_power"] >= c["power"]:
        assert cr["alpha"] <= c["alpha"] * (1 + 1e-9)
    else:
        assert cr["alpha"] >= c["alpha"] * (1 - 1e-9)
    assert abs(_posthoc(c["tails"], c["d"], cr["alpha"], a["n1"], a["n2"]) - c["power"]) <= 1e-9


@pytest.mark.parametrize("c", GRID[:40])
def test_sensitivity_d_gives_target_power(c):
    a = _apriori(c)
    se = _ok({"test": T2, "mode": "sensitivity", "tails": c["tails"], "alpha": c["alpha"],
              "power": c["power"], "n1": a["n1"], "n2": a["n2"]})
    assert se["d"] > 0.0
    if a["actual_power"] >= c["power"]:
        assert se["d"] <= c["d"] * (1 + 1e-9)
    else:
        assert se["d"] >= c["d"] * (1 - 1e-9)
    assert abs(_posthoc(c["tails"], se["d"], c["alpha"], a["n1"], a["n2"]) - c["power"]) <= 1e-9


@pytest.mark.parametrize("c", GRID[:40])
def test_compromise_ratio(c):
    rng = random.Random(int(c["d"] * 1e6))
    q = math.exp(rng.uniform(math.log(0.25), math.log(4.0)))
    n1 = rng.randint(2, 300)
    n2 = rng.randint(2, 300)
    co = _ok({"test": T2, "mode": "compromise", "tails": c["tails"], "d": c["d"],
              "beta_alpha_ratio": q, "n1": n1, "n2": n2})
    assert abs(co["beta"] / co["alpha"] - q) <= 1e-9 * q
    assert co["power"] == 1.0 - co["beta"]
    assert abs(_posthoc(c["tails"], c["d"], co["alpha"], n1, n2) - co["power"]) <= 1e-9


@pytest.mark.parametrize("c", GRID[:30])
def test_power_monotonicity(c):
    t, d, al = c["tails"], c["d"], c["alpha"]
    n1, n2 = 20, max(2, int(20 * c["ratio"]))
    p = engine.power_of(t, d, al, n1, n2)
    saturated = p > 1 - 1e-12
    assert engine.power_of(t, d * 1.1, al, n1, n2) > p or saturated
    assert engine.power_of(t, d, al, n1 + 5, n2) > p or saturated
    assert engine.power_of(t, d, al, n1, n2 + 5) > p or saturated
    assert engine.power_of(t, d, min(0.99, al * 1.5), n1, n2) > p or saturated
    assert engine.power_of(1, d, al, n1, n2) >= engine.power_of(2, d, al, n1, n2)


@pytest.mark.parametrize("c", GRID[:10])
def test_determinism(c):
    params = {"test": T2, "mode": "a-priori", **c}
    first = engine.to_json(engine.run(params)[0])
    for _ in range(3):
        assert engine.to_json(engine.run(dict(params))[0]) == first


def test_ratio_three_split_is_half_up():
    # SPEC 3.1: N* = 232.24 -> N = 234, n1 = floor(234/4 + 0.5) = floor(59.0) = 59 (58.5 rounds UP)
    a = _apriori({"tails": 1, "d": 0.5, "alpha": 0.05, "power": 0.95, "ratio": 3})
    assert (a["n1"], a["n2"], a["n_total"]) == (59, 175, 234)


@pytest.mark.parametrize("c", GRID[:20])
def test_ratio_one_gives_equal_groups(c):
    a = _apriori({**c, "ratio": 1})
    assert a["n1"] == a["n2"] and a["n_total"] == 2 * a["n1"]


@pytest.mark.parametrize("c", GRID[:20])
def test_ratio_reciprocal_mirrors_groups(c):
    # power depends on n1*n2/(n1+n2) only, so ratio and 1/ratio share N*; the split mirrors
    # unless N/(1+ratio) sits exactly on .5 (half-up is not symmetric)
    a = _apriori(c)
    b = _apriori({**c, "ratio": 1 / c["ratio"]})
    assert a["n_total"] == b["n_total"]
    x = a["n_total"] / (1 + c["ratio"])
    if abs(x - math.floor(x) - 0.5) > 1e-6:
        assert (a["n1"], a["n2"]) == (b["n2"], b["n1"])


def test_actual_power_may_be_below_target():
    # SPEC 3.1 step 6 (G*Power V07): 404/282, actual power 0.8998856 < 0.90 is kept
    a = _apriori({"tails": 2, "d": 0.3, "alpha": 0.01, "power": 0.9, "ratio": 0.7})
    assert (a["n1"], a["n2"], a["n_total"]) == (404, 282, 686)
    assert a["actual_power"] < 0.9


def test_n_total_four_shortcut_and_power_equal_alpha():
    # power(N = 4) >= target -> N = 4 (power = alpha is valid input, SPEC 2.9)
    a = _apriori({"tails": 1, "d": 0.5, "alpha": 0.05, "power": 0.05, "ratio": 1})
    assert (a["n1"], a["n2"], a["n_total"], a["df"]) == (2, 2, 4, 2)
    assert "warning" not in a


@pytest.mark.parametrize("ratio,n1,n2", [(0.25, 3, 1), (0.1, 4, 0), (4, 1, 3), (10, 0, 4)])
def test_degenerate_groups_get_warning(ratio, n1, n2):
    a = _apriori({"tails": 2, "d": 10, "alpha": 0.05, "power": 0.8, "ratio": ratio})
    assert (a["n1"], a["n2"], a["n_total"], a["df"]) == (n1, n2, 4, 2)
    assert a["warning"] == engine.DEGENERATE_WARNING
    assert list(a) == ["ncp", "critical_t", "df", "n1", "n2", "n_total", "actual_power", "warning"]
    if 0 in (n1, n2):
        assert a["ncp"] == 0.0
        assert abs(a["actual_power"] - 0.05) <= 1e-12


def test_sensitivity_power_equal_alpha_gives_zero_effect():
    for tails in (1, 2):
        se = _ok({"test": T2, "mode": "sensitivity", "tails": tails, "alpha": 0.05, "power": 0.05,
                  "n1": 20, "n2": 20})
        assert se["d"] == 0.0 and se["ncp"] == 0.0 and se["df"] == 38
