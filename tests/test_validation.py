"""SPEC 2: every error code with field and exit code, plus the check order."""

from __future__ import annotations

import json

import pytest

from conftest import run_cli
from gpower_clone import engine

T2 = "t2-indep"
POST = {"test": T2, "mode": "post-hoc", "tails": "1", "d": "0.5", "alpha": "0.05", "n1": "88", "n2": "88"}
APRI = {"test": T2, "mode": "a-priori", "tails": "1", "d": "0.5", "alpha": "0.05", "power": "0.95",
        "ratio": "1"}


def err(params, code, field, exit_code=2):
    out, ec = engine.run(params)
    assert list(out) == ["error", "code", "field"], out
    assert out["code"] == code, out
    assert out["field"] == field, out
    assert ec == exit_code
    assert isinstance(out["error"], str) and out["error"]
    return out


def with_(base, **kw):
    p = dict(base)
    for k, v in kw.items():
        if v is ...:
            p.pop(k, None)
        else:
            p[k] = v
    return p


# --- MISSING_PARAM / UNSUPPORTED (steps 2-3) ----------------------------------------

def test_missing_test():
    err(with_(POST, test=...), "MISSING_PARAM", "test")


def test_missing_mode():
    err(with_(POST, mode=...), "MISSING_PARAM", "mode")


def test_missing_both_reports_test():
    err({}, "MISSING_PARAM", "test")


def test_missing_mode_before_unsupported_test():
    err({"test": "t-paired"}, "MISSING_PARAM", "mode")


def test_unknown_test():
    err(with_(POST, test="t-paired"), "UNSUPPORTED", "test")


def test_unknown_mode():
    err(with_(POST, mode="post_hoc"), "UNSUPPORTED", "mode")


def test_unsupported_before_unknown_param():
    err(with_(POST, test="anova-oneway", foo="1"), "UNSUPPORTED", "test")


# --- duplicates / unknown / irrelevant (steps 4-5) ------------------------------------

def test_duplicate_field():
    pairs = list(POST.items()) + [("d", "0.6")]
    err(pairs, "INVALID_VALUE", "d")


def test_duplicate_before_unknown():
    pairs = [("test", T2), ("mode", "post-hoc"), ("foo", "1"), ("d", "1"), ("d", "2")]
    err(pairs, "INVALID_VALUE", "d")


def test_irrelevant_field_power_in_post_hoc():
    err(with_(POST, power="0.8"), "UNKNOWN_PARAM", "power")


def test_irrelevant_field_ratio_in_sensitivity():
    p = {"test": T2, "mode": "sensitivity", "tails": "1", "alpha": "0.05", "power": "0.9", "n1": "10",
         "n2": "10", "ratio": "1"}
    err(p, "UNKNOWN_PARAM", "ratio")


def test_unknown_field():
    err(with_(POST, foo="1"), "UNKNOWN_PARAM", "foo")


def test_unknown_first_in_input_order():
    pairs = [("test", T2), ("mode", "post-hoc"), ("zeta", "1"), ("alpha2", "1")]
    err(pairs, "UNKNOWN_PARAM", "zeta")


def test_unknown_before_missing():
    err({"test": T2, "mode": "post-hoc", "power": "0.8"}, "UNKNOWN_PARAM", "power")


# --- MISSING_PARAM for mode fields (step 6) ---------------------------------------------

def test_missing_field():
    err(with_(POST, n2=...), "MISSING_PARAM", "n2")


def test_missing_reports_first_in_table_order():
    err(with_(APRI, alpha=..., ratio=..., tails=...), "MISSING_PARAM", "tails")
    err(with_(APRI, ratio=..., alpha=...), "MISSING_PARAM", "alpha")


# --- INVALID_VALUE (step 7) ---------------------------------------------------------------

@pytest.mark.parametrize("bad", ["0,05", "nan", "NaN", "inf", "-inf", "", " ", "abc", "1e400", "0x1",
                                 "1_0", "5%", " 0.05"])
def test_invalid_decimal(bad):
    err(with_(POST, alpha=bad), "INVALID_VALUE", "alpha")


@pytest.mark.parametrize("bad", ["88.0", "88.5", "1e2", "", "abc", "8 8", "0,5"])
def test_invalid_integer_text(bad):
    err(with_(POST, n1=bad), "INVALID_VALUE", "n1")


def test_integer_json_values():
    assert engine.run(with_(POST, n1=88, n2=88))[1] == 0
    err(with_(POST, n1=88.5), "INVALID_VALUE", "n1")
    err(with_(POST, n1=88.0), "INVALID_VALUE", "n1")
    err(with_(POST, n1=True), "INVALID_VALUE", "n1")
    err(with_(POST, tails=False), "INVALID_VALUE", "tails")


def test_decimal_json_values():
    assert engine.run(with_(POST, d=1, alpha=0.05))[1] == 0
    err(with_(POST, d=True), "INVALID_VALUE", "d")
    err(with_(POST, d=float("nan")), "INVALID_VALUE", "d")
    err(with_(POST, d=[0.5]), "INVALID_VALUE", "d")


def test_none_means_absent():
    err(with_(POST, n2=None), "MISSING_PARAM", "n2")
    assert engine.run(with_(POST, ratio=None))[1] == 0


def test_type_checked_before_range_and_in_table_order():
    err(with_(POST, tails="3", n2="x"), "INVALID_VALUE", "n2")
    err(with_(POST, d="x", alpha="y"), "INVALID_VALUE", "d")


# --- OUT_OF_RANGE (step 8) ------------------------------------------------------------------

@pytest.mark.parametrize("field,value", [
    ("tails", "0"), ("tails", "3"), ("tails", "-1"),
    ("alpha", "0"), ("alpha", "1"), ("alpha", "-0.1"), ("alpha", "1.5"),
    ("d", "0"), ("d", "-0.5"),
    ("n1", "1"), ("n1", "0"), ("n1", "-5"), ("n2", "1"),
])
def test_out_of_range_post_hoc(field, value):
    err(with_(POST, **{field: value}), "OUT_OF_RANGE", field)


@pytest.mark.parametrize("field,value", [("power", "0"), ("power", "1"), ("ratio", "0"), ("ratio", "-2"),
                                         ("ratio", "0.009"), ("ratio", "0.00999999"), ("ratio", "100.5"),
                                         ("ratio", "100.0000001"), ("ratio", "1e9")])
def test_out_of_range_a_priori(field, value):
    out = err(with_(APRI, **{field: value}), "OUT_OF_RANGE", field)
    if field == "ratio":
        assert out["error"].endswith("Allocation ratio kabul edilebilir aralığın (0.01, 100) dışında")


@pytest.mark.parametrize("ratio", ["0.01", "100", "1e-2", "1e2", 0.01, 100])
def test_ratio_bounds_are_inclusive(ratio):
    out, code = engine.run(with_(APRI, ratio=ratio))
    assert code == 0, out


def test_out_of_range_beta_alpha_ratio():
    p = {"test": T2, "mode": "compromise", "tails": "2", "d": "0.5", "beta_alpha_ratio": "0",
         "n1": "10", "n2": "10"}
    err(p, "OUT_OF_RANGE", "beta_alpha_ratio")


def test_range_reported_in_table_order():
    err(with_(POST, n1="1", tails="5"), "OUT_OF_RANGE", "tails")


# --- INCONSISTENT (step 9) ------------------------------------------------------------------

@pytest.mark.parametrize("power,alpha", [("0.04", "0.05"), ("0.1", "0.5"), ("0.0499999", "0.05")])
def test_power_below_alpha_a_priori(power, alpha):
    out = err(with_(APRI, power=power, alpha=alpha), "INCONSISTENT", "power")
    assert out["error"] == "Power, alpha değerinden büyük olmalı"


@pytest.mark.parametrize("tails", ["1", "2"])
def test_power_equal_alpha_is_valid(tails):
    # SPEC 2.9: only power < alpha (strict) is INCONSISTENT
    out, code = engine.run(with_(APRI, power="0.05", alpha="0.05", tails=tails))
    assert code == 0 and out["n_total"] == 4, out
    p = {"test": T2, "mode": "sensitivity", "tails": tails, "alpha": "0.05", "power": "0.05",
         "n1": "20", "n2": "20"}
    out, code = engine.run(p)
    assert code == 0 and out["d"] == 0.0 and out["ncp"] == 0.0, out


def test_power_not_above_alpha_sensitivity():
    p = {"test": T2, "mode": "sensitivity", "tails": "2", "alpha": "0.2", "power": "0.1",
         "n1": "10", "n2": "10"}
    err(p, "INCONSISTENT", "power")


def test_range_before_inconsistent():
    err(with_(APRI, power="0", alpha="0.05"), "OUT_OF_RANGE", "power")


# --- NO_SOLUTION (step 10, exit 1) ----------------------------------------------------------

@pytest.mark.parametrize("d", ["0.0000000001", "0.0000099999", "9e-6", "1e-300"])
def test_a_priori_d_below_minimum_is_out_of_range(d):
    # SPEC 2.8 (a-priori only): d < 0.00001 -> OUT_OF_RANGE, field d, exit 2
    out = err(with_(APRI, d=d), "OUT_OF_RANGE", "d")
    assert out["error"].endswith("A-priori analizde etki büyüklüğü 0.00001'den küçük olamaz")


def test_a_priori_d_minimum_reported_in_table_order():
    # d precedes ratio in the field table, so d is reported first
    err(with_(APRI, d="0.0000000001", ratio="0"), "OUT_OF_RANGE", "d")
    err(with_(APRI, d="0"), "OUT_OF_RANGE", "d")


@pytest.mark.parametrize("d", ["0.00001", "1e-5", 0.00001])
def test_a_priori_d_minimum_is_inclusive(d):
    out, code = engine.run(with_(APRI, d=d, tails="2", ratio="0.01"))
    assert code == 0 and out["n_total"] > 1e12, out


@pytest.mark.parametrize("mode_params", [
    {"mode": "post-hoc", "tails": "2", "d": "0.0000000001", "alpha": "0.05", "n1": "20", "n2": "20"},
    {"mode": "compromise", "tails": "2", "d": "0.0000000001", "beta_alpha_ratio": "1", "n1": "20",
     "n2": "20"},
])
def test_tiny_d_still_valid_outside_a_priori(mode_params):
    out, code = engine.run({"test": T2, **mode_params})
    assert code == 0 and out["df"] == 38, out


def test_huge_but_finite_a_priori_is_solved():
    # SPEC 3.1: no upper limit (G*Power: d = 0.001 -> 25 989 420 per group)
    out, code = engine.run(with_(APRI, tails="2", d="0.001", power="0.95"))
    assert code == 0 and (out["n1"], out["n2"]) == (25989420, 25989420), out
    out, code = engine.run(with_(APRI, d="0.0005"))
    assert code == 0 and out["n_total"] > 1e8, out


def test_no_solution_sensitivity():
    p = {"test": T2, "mode": "sensitivity", "tails": "2", "alpha": "1e-12", "power": "0.99",
         "n1": "2", "n2": "2"}
    err(p, "NO_SOLUTION", None, exit_code=1)


# --- CLI syntax --------------------------------------------------------------------------------

def _cli_err(argv, code, field, exit_code=2):
    stdout, _, ec, _ = run_cli(argv)
    out = json.loads(stdout)
    assert (out["code"], out["field"], ec) == (code, field, exit_code), out
    return out


def test_cli_flag_without_value_at_end():
    _cli_err(["--test", T2, "--mode", "post-hoc", "--d"], "INVALID_VALUE", "d")


def test_cli_flag_followed_by_flag():
    _cli_err(["--test", T2, "--mode", "post-hoc", "--d", "--alpha", "0.05"], "INVALID_VALUE", "d")


def test_cli_positional_token():
    _cli_err(["--test", T2, "--mode", "post-hoc", "extra"], "UNKNOWN_PARAM", "extra")
    _cli_err(["post-hoc"], "UNKNOWN_PARAM", "post-hoc")


def test_cli_duplicate():
    argv = ["--test", T2, "--mode", "post-hoc", "--tails", "1", "--d", "0.5", "--d", "0.6",
            "--alpha", "0.05", "--n1", "10", "--n2", "10"]
    _cli_err(argv, "INVALID_VALUE", "d")


def test_cli_negative_value_is_a_value():
    _cli_err(["--test", T2, "--mode", "post-hoc", "--tails", "1", "--d", "-0.5", "--alpha", "0.05",
              "--n1", "10", "--n2", "10"], "OUT_OF_RANGE", "d")


def test_cli_version_with_other_args():
    _cli_err(["--version", "--test", T2], "INVALID_VALUE", "version")
    _cli_err(["--test", T2, "--mode", "post-hoc", "--version", "1"], "UNKNOWN_PARAM", "version")


def test_cli_no_args():
    _cli_err([], "MISSING_PARAM", "test")
