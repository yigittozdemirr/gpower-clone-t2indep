"""Shared helpers for the test-suite."""

from __future__ import annotations

import json
import math
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VECTORS_PATH = ROOT / "public_vectors.jsonl"


def load_vectors() -> list[dict]:
    with open(VECTORS_PATH, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def cli_command() -> list[str]:
    """The installed console script if present, else ``python -m gpower_clone.cli``."""
    scripts = Path(sys.executable).parent
    for name in ("gpower-clone.exe", "gpower-clone"):
        exe = scripts / name
        if exe.exists():
            return [str(exe)]
    return [sys.executable, "-m", "gpower_clone.cli"]


def cli_value(v) -> str:
    if isinstance(v, bool):
        raise TypeError("booleans have no CLI form")
    if isinstance(v, float):
        return repr(v)
    return str(v)


def to_argv(params: dict) -> list[str]:
    argv: list[str] = []
    for k, v in params.items():
        argv += ["--" + k, cli_value(v)]
    return argv


def run_cli(argv: list[str], timeout: float = 30.0):
    """Returns (stdout bytes, stderr bytes, exit code, wall seconds)."""
    t0 = time.perf_counter()
    proc = subprocess.run(cli_command() + list(argv), capture_output=True, timeout=timeout)
    return proc.stdout, proc.stderr, proc.returncode, time.perf_counter() - t0


def close_enough(ours: float, expected: float, tol: float = 1e-6) -> bool:
    """CONTRACT 6: |diff| <= 1e-6 or relative diff <= 1e-6."""
    diff = abs(ours - expected)
    return diff <= tol or (expected != 0 and diff / abs(expected) <= tol)


INT_OUTPUTS = {"n1", "n2", "n_total", "df", "df1", "df2"}


@pytest.fixture(scope="session")
def vectors() -> list[dict]:
    return load_vectors()


def isclose_abs(a: float, b: float, tol: float) -> bool:
    return math.isfinite(a) and abs(a - b) <= tol
