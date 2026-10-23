"""Differential test: engine vs G*Power screenshots and vs statsmodels (600 vectors).

The full agreement report is written by `uv run python tools/differential_report.py`.
"""

from __future__ import annotations

import pytest

from differential import compare_gpower, compare_scale

SCALE = compare_scale()
GPOWER = compare_gpower()


def test_scale_vector_count():
    assert len(SCALE) >= 500


@pytest.mark.parametrize("res", SCALE, ids=[r.id for r in SCALE])
def test_scale_vector(res):
    # Every disagreement must be explained (integer boundary, or a provable oracle error).
    assert res.ok or res.note, res.diffs


@pytest.mark.skipif(not GPOWER, reason="oracle/gpower_vectors.csv henüz doldurulmadı")
def test_gpower_gate():
    """Ödev kapısı: a-priori N alanları en az %90 tam eşleşmeli (hedefimiz %100)."""
    gated = [r for r in GPOWER if r.n_ok is not None]
    rate = sum(r.n_ok for r in gated) / len(gated)
    assert rate >= 0.9, [(r.id, r.diffs) for r in gated if not r.n_ok]


@pytest.mark.parametrize("res", GPOWER, ids=[r.id for r in GPOWER])
def test_gpower_vector(res):
    # Accepted disagreements: a documented contract-over-G*Power decision (V33), or G*Power's displayed power
    # contradicting the formula at its own N (huge df, V43/V44) — measured, not assumed.
    assert res.ok or res.note.startswith(("sözleşme önceliği", "kâhin sayısal hatası")), res.diffs
