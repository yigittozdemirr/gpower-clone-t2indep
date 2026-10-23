"""Subprocess tests of the real console script (CONTRACT 2)."""

from __future__ import annotations

import json
import re

import pytest

from conftest import run_cli

T2 = "t2-indep"
LIMIT_S = 2.0

CASES = [
    (["--test", T2, "--mode", "a-priori", "--tails", "1", "--d", "0.5", "--alpha", "0.05",
      "--power", "0.95", "--ratio", "1"], 0),
    (["--test", T2, "--mode", "a-priori", "--tails", "2", "--d", "0.2", "--alpha", "0.01",
      "--power", "0.99", "--ratio", "3"], 0),
    (["--test", T2, "--mode", "a-priori", "--tails", "2", "--d", "0.1", "--alpha", "0.001",
      "--power", "0.99", "--ratio", "0.25"], 0),
    (["--test", T2, "--mode", "post-hoc", "--tails", "2", "--d", "0.3", "--alpha", "0.05",
      "--n1", "40", "--n2", "120"], 0),
    (["--test", T2, "--mode", "compromise", "--tails", "2", "--d", "0.5", "--beta_alpha_ratio", "4",
      "--n1", "30", "--n2", "45"], 0),
    (["--test", T2, "--mode", "criterion", "--tails", "2", "--d", "0.5", "--power", "0.8",
      "--n1", "30", "--n2", "45"], 0),
    (["--test", T2, "--mode", "sensitivity", "--tails", "2", "--alpha", "0.05", "--power", "0.8",
      "--n1", "2", "--n2", "2"], 0),
    (["--test", T2, "--mode", "sensitivity", "--tails", "2", "--alpha", "1e-12", "--power", "0.99",
      "--n1", "2", "--n2", "2"], 1),
    (["--test", T2, "--mode", "a-priori", "--tails", "2", "--d", "0.0005", "--alpha", "0.05",
      "--power", "0.8", "--ratio", "1"], 1),
    (["--test", T2, "--mode", "post-hoc", "--tails", "1", "--d", "0,5", "--alpha", "0.05",
      "--n1", "10", "--n2", "10"], 2),
    (["--test", "anova-oneway", "--mode", "a-priori"], 2),
]


@pytest.mark.parametrize("argv,exit_code", CASES)
def test_one_json_line_exit_code_and_time(argv, exit_code):
    stdout, stderr, code, wall = run_cli(argv)
    assert code == exit_code
    assert wall < LIMIT_S, wall
    text = stdout.decode("ascii")
    assert text.endswith("\n") and not text.endswith("\r\n")
    assert text.count("\n") == 1
    obj = json.loads(text)
    assert isinstance(obj, dict)
    if exit_code == 0:
        assert "error" not in obj
        for k in ("df", "n1", "n2", "n_total"):
            if k in obj:
                assert type(obj[k]) is int
                assert re.search(r'"%s": \d+[,}]' % k, text)
    else:
        assert list(obj) == ["error", "code", "field"]


def test_integers_are_json_integers():
    stdout, _, code, _ = run_cli(["--test", T2, "--mode", "a-priori", "--tails", "1", "--d", "0.5",
                                  "--alpha", "0.05", "--power", "0.95", "--ratio", "1"])
    text = stdout.decode()
    assert code == 0
    assert '"df": 174,' in text and '"n1": 88,' in text and '"n2": 88,' in text
    assert '"n_total": 176,' in text
    assert "88.0" not in text


def test_output_format_separators():
    stdout, _, _, _ = run_cli(["--test", T2, "--mode", "post-hoc", "--tails", "1", "--d", "0.5",
                               "--alpha", "0.05", "--n1", "88", "--n2", "88"])
    assert stdout == (b'{"ncp": 3.3166247903554, "critical_t": 1.6536580165162162, "df": 174, '
                      b'"power": 0.9514254482775331}\n')


def test_version():
    stdout, _, code, wall = run_cli(["--version"])
    assert code == 0 and wall < LIMIT_S
    obj = json.loads(stdout)
    assert list(obj) == ["contract_version", "name", "engine"]
    assert obj["contract_version"] == "1.0.0"
    assert obj["name"] == "gpower-clone-t2indep"
    assert obj["engine"].startswith("Python ") and obj["engine"].endswith("(stdlib)")


def test_error_text_is_ascii_escaped():
    stdout, _, code, _ = run_cli(["--test", T2, "--mode", "a-priori", "--tails", "1", "--d", "0.5",
                                  "--alpha", "0.05", "--power", "0.01", "--ratio", "1"])
    assert code == 2
    stdout.decode("ascii")
    assert json.loads(stdout)["error"] == "Power, alpha değerinden büyük olmalı"


def test_deterministic_bytes():
    argv = CASES[1][0]
    first = run_cli(argv)[0]
    assert run_cli(argv)[0] == first


def test_nothing_on_stdout_but_json_for_core_import():
    # the core must not import third-party packages (2 s budget, SPEC 1.1)
    import subprocess
    import sys

    code = ("import sys, gpower_clone.cli, gpower_clone.engine, gpower_clone.numerics;"
            "bad=[m for m in ('scipy','numpy','mcp','anthropic','pydantic') if m in sys.modules];"
            "print(bad)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    assert out.stdout.strip() == "[]"
