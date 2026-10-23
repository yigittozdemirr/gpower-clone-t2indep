"""SPEC.md section 9: every Gherkin "Örnekler" row is executed through the real CLI.

The spec and the tests cannot drift apart: editing a table row in SPEC.md changes this test.
"""

from __future__ import annotations

import json
import re
import shlex

import pytest

from conftest import INT_OUTPUTS, ROOT, close_enough, run_cli

SPEC = (ROOT / "SPEC.md").read_text(encoding="utf-8")


def gherkin_rows() -> list[tuple[str, dict]]:
    rows = []
    for block in re.findall(r"```gherkin\n(.*?)```", SPEC, flags=re.S):
        feature = re.search(r"Özellik:\s*(.+)", block).group(1).strip()
        header = None
        for line in block.splitlines():
            line = line.strip()
            if not line.startswith("|"):
                header = None if not line.startswith("Örnekler") else header
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if header is None:
                header = cells
                continue
            rows.append((feature, dict(zip(header, cells))))
    return rows


ROWS = gherkin_rows()


def test_spec_has_examples():
    assert len(ROWS) >= 30


@pytest.mark.parametrize("feature,row", ROWS, ids=[f"{i:02d}" for i in range(len(ROWS))])
def test_gherkin_example(feature, row):
    argv = ["--test", "t2-indep", *shlex.split(row["argümanlar"])]
    stdout, _, code, _ = run_cli(argv)
    lines = stdout.decode("utf-8").splitlines()
    assert len(lines) == 1, stdout
    out = json.loads(lines[0])
    expected = json.loads(row["beklenen"])
    assert code == int(row.get("çıkış", "0")), (feature, out)
    if "çıkış" in row:
        assert "error" in out, out
    for key, exp in expected.items():
        assert key in out, (feature, key, out)
        if isinstance(exp, str) or exp is None:
            assert out[key] == exp, (feature, key, out[key], exp)
        elif key in INT_OUTPUTS:
            assert type(out[key]) is int and out[key] == exp, (feature, key, out[key], exp)
        else:
            assert close_enough(out[key], exp), (feature, key, out[key], exp)
