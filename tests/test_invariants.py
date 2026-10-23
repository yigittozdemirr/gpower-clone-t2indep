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


@pytest.mark.parametrize("c", GRID)
def test_apriori_posthoc_and_minimality(c):
    a = _apriori(c)
    assert a["n_total"] == a["n1"] + a["n2"]
    assert a["df"] == a["n_total"] - 2
    assert a["n1"] >= 2 and a["n2"] >= 2
    # post-hoc on the a-priori sample sizes reproduces actual_power, which reaches the target
    ph = _posthoc(c["tails"], c["d"], c["alpha"], a["n1"], a["n2"])
    assert ph == a["actual_power"]
    assert a["actual_power"] >= c["power"] - 1e-9
    # minimality: one step below n1 on the ratio-preserving continuous path misses the target
    n1_lo = max(2.0, 2.0 / c["ratio"])
    m = a["n1"] - 1
    if m >= n1_lo:
        assert engine.power_of(c["tails"], c["d"], c["alpha"], m, c["ratio"] * m) < c["power"]
    # per-group rounding: n2 never exceeds ceil(ratio * n1)
    assert a["n2"] <= math.ceil(c["ratio"] * a["n1"] - 1e-9)


@pytest.mark.parametrize("c", GRID[:40])
def test_criterion_alpha_gives_target_power(c):
    a = _apriori(c)
    cr = _ok({"test": T2, "mode": "criterion", "tails": c["tails"], "d": c["d"], "power": c["power"],
              "n1": a["n1"], "n2": a["n2"]})
    assert 0.0 < cr["alpha"] <= c["alpha"] * (1 + 1e-9)
    assert abs(_posthoc(c["tails"], c["d"], cr["alpha"], a["n1"], a["n2"]) - c["power"]) <= 1e-9


@pytest.mark.parametrize("c", GRID[:40])
def test_sensitivity_d_gives_target_power(c):
    a = _apriori(c)
    se = _ok({"test": T2, "mode": "sensitivity", "tails": c["tails"], "alpha": c["alpha"],
              "power": c["power"], "n1": a["n1"], "n2": a["n2"]})
    assert 0.0 < se["d"] <= c["d"] * (1 + 1e-9)
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


def test_ratio_three_rounds_each_group_separately():
    # SPEC 3.1: n2 = ceil(ratio * n1*), not ratio * ceil(n1*)
    found = False
    for d in [0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.7, 0.8]:
        a = _apriori({"tails": 2, "d": d, "alpha": 0.05, "power": 0.8, "ratio": 3})
        assert a["n2"] <= 3 * a["n1"]
        if a["n2"] != 3 * a["n1"]:
            found = True
    assert found
