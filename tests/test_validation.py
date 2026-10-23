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


@pytest.mark.parametrize("field,value", [("power", "0"), ("power", "1"), ("ratio", "0"), ("ratio", "-2")])
def test_out_of_range_a_priori(field, value):
    err(with_(APRI, **{field: value}), "OUT_OF_RANGE", field)


def test_out_of_range_beta_alpha_ratio():
    p = {"test": T2, "mode": "compromise", "tails": "2", "d": "0.5", "beta_alpha_ratio": "0",
         "n1": "10", "n2": "10"}
    err(p, "OUT_OF_RANGE", "beta_alpha_ratio")


def test_range_reported_in_table_order():
    err(with_(POST, n1="1", tails="5"), "OUT_OF_RANGE", "tails")


# --- INCONSISTENT (step 9) ------------------------------------------------------------------

@pytest.mark.parametrize("power,alpha", [("0.05", "0.05"), ("0.04", "0.05"), ("0.1", "0.5")])
def test_power_not_above_alpha_a_priori(power, alpha):
    out = err(with_(APRI, power=power, alpha=alpha), "INCONSISTENT", "power")
    assert out["error"] == "Power, alpha değerinden büyük olmalı"


def test_power_not_above_alpha_sensitivity():
    p = {"test": T2, "mode": "sensitivity", "tails": "2", "alpha": "0.2", "power": "0.1",
         "n1": "10", "n2": "10"}
    err(p, "INCONSISTENT", "power")


def test_range_before_inconsistent():
    err(with_(APRI, power="0", alpha="0.05"), "OUT_OF_RANGE", "power")


# --- NO_SOLUTION (step 10, exit 1) ----------------------------------------------------------

def test_no_solution_a_priori_too_large():
    err(with_(APRI, d="0.0005"), "NO_SOLUTION", None, exit_code=1)


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
