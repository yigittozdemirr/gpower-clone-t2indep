"""CONTRACT 9 public vectors: 5 t2-indep vectors must match; the other 20 are UNSUPPORTED."""

from __future__ import annotations

import json

import pytest

from conftest import INT_OUTPUTS, close_enough, load_vectors, run_cli, to_argv
from gpower_clone import engine

VECTORS = load_vectors()
T2 = [v for v in VECTORS if v["input"]["test"] == "t2-indep"]
OTHER = [v for v in VECTORS if v["input"]["test"] != "t2-indep"]


def test_vector_file_shape():
    assert len(VECTORS) == 25
    assert len(T2) == 5
    assert len(OTHER) == 20


def _check(out: dict, expected: dict):
    for key, exp in expected.items():
        assert key in out, key
        if key in INT_OUTPUTS:
            assert type(out[key]) is int, (key, out[key])
            assert out[key] == exp, (key, out[key], exp)
        else:
            assert isinstance(out[key], float), (key, out[key])
            assert close_enough(out[key], exp), (key, out[key], exp)


@pytest.mark.parametrize("vec", T2, ids=[v["id"] for v in T2])
def test_t2_indep_vector_engine(vec):
    out, code = engine.run(vec["input"])
    assert code == 0, out
    _check(out, vec["expected"])


@pytest.mark.parametrize("vec", T2, ids=[v["id"] for v in T2])
def test_t2_indep_vector_cli(vec):
    stdout, _, code, _ = run_cli(to_argv(vec["input"]))
    assert code == 0
    _check(json.loads(stdout), vec["expected"])


@pytest.mark.parametrize("vec", OTHER, ids=[v["id"] for v in OTHER])
def test_other_families_unsupported(vec):
    out, code = engine.run(vec["input"])
    assert code == 2
    assert out["code"] == "UNSUPPORTED"
    assert out["field"] == "test"
    assert set(out) == {"error", "code", "field"}
    stdout, _, cli_code, _ = run_cli(to_argv(vec["input"]))
    assert cli_code == 2
    assert json.loads(stdout)["code"] == "UNSUPPORTED"
