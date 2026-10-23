"""Differential comparison of the engine against its oracles.

Shared by tests/test_differential.py (assertions) and tools/differential_report.py (report).

Oracles:
- oracle/gpower_vectors.csv : values read from G*Power 3.1.9.7 screenshots (the real oracle)
- oracle/scale_vectors.csv  : statsmodels TTestIndPower (independent library, fractional N)
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from pathlib import Path

from gpower_clone import engine

ROOT = Path(__file__).resolve().parents[1]
GPOWER_CSV = ROOT / "oracle" / "gpower_vectors.csv"
SCALE_CSV = ROOT / "oracle" / "scale_vectors.csv"

INPUT_FIELDS = ["tails", "d", "alpha", "power", "ratio", "n1", "n2", "beta_alpha_ratio"]
INT_FIELDS = {"tails", "n1", "n2", "n_total", "df"}
OUTPUT_FIELDS = ["ncp", "critical_t", "df", "n1", "n2", "n_total", "actual_power", "power", "alpha", "beta", "d"]


@dataclass
class Result:
    id: str
    source: str
    mode: str
    inputs: dict
    ok: bool
    n_ok: bool | None = None          # a-priori N fields (gate)
    diffs: list[str] = field(default_factory=list)
    note: str = ""


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return [row for row in csv.DictReader(fh) if row.get("id")]


def _inputs(row: dict) -> dict:
    params = {"test": "t2-indep", "mode": row["mode"]}
    for key in INPUT_FIELDS:
        value = (row.get(key) or "").strip()
        if value:
            params[key] = int(value) if key in INT_FIELDS else float(value)
    return params


def _shown_tolerance(text: str) -> float:
    """G*Power shows a fixed number of decimals; accept anything that rounds to the shown value."""
    decimals = len(text.split(".")[1]) if "." in text else 0
    return 0.5 * 10.0 ** (-decimals) + 1e-12


def compare_gpower() -> list[Result]:
    results = []
    for row in _read(GPOWER_CSV):
        params = _inputs(row)
        out, code = engine.run(params)
        gp_error = (row.get("gp_error") or "").strip()
        res = Result(row["id"], "G*Power", row["mode"], params, ok=True, note=row.get("note", ""))
        if gp_error:
            res.ok = "error" in out
            if not res.ok:
                res.diffs.append(f"G*Power hata verdi ({gp_error}); motor sonuç üretti")
        elif "error" in out:
            res.ok = False
            res.diffs.append(f"motor hata verdi ({out['code']}); G*Power sonuç üretti")
        else:
            for key in OUTPUT_FIELDS:
                shown = (row.get(f"gp_{key}") or "").strip()
                if not shown or key not in out:
                    continue
                if key in INT_FIELDS:
                    if out[key] != int(shown):
                        res.diffs.append(f"{key}: motor {out[key]}, G*Power {shown}")
                elif abs(out[key] - float(shown)) > _shown_tolerance(shown):
                    res.diffs.append(f"{key}: motor {out[key]:.7f}, G*Power {shown}")
            res.ok = not res.diffs
        if row["mode"] == "a-priori" and not gp_error:
            res.n_ok = not any(d.split(":")[0] in ("n1", "n2", "n_total") for d in res.diffs) and "error" not in out
        results.append(res)
    return results


def _explain_scale_mismatch(params: dict, nobs1: float, exp_n1: int, exp_n2: int) -> str:
    """Classify an a-priori disagreement with statsmodels. Empty string = unexplained."""
    ratio = params["ratio"]
    # Right at an integer boundary the two solvers' tolerances decide the ceiling: not a rule difference.
    if min(abs(nobs1 - round(nobs1)), abs(ratio * nobs1 - round(ratio * nobs1))) < 1e-6:
        return "sınırda"
    # If statsmodels' rounded-up N does not even reach the target power, the oracle's root is wrong.
    check, _ = engine.run({"test": "t2-indep", "mode": "post-hoc", "tails": params["tails"], "d": params["d"],
                           "alpha": params["alpha"], "n1": exp_n1, "n2": exp_n2})
    if "power" in check and check["power"] < params["power"]:
        return (f"kâhin hatası: ⌈statsmodels⌉ = {exp_n1}/{exp_n2} ile güç {check['power']:.7f} "
                f"< hedef {params['power']} (SciPy nct NaN, kök bulucu saptı)")
    return ""


def compare_scale() -> list[Result]:
    results = []
    for row in _read(SCALE_CSV):
        params = _inputs(row)
        out, code = engine.run(params)
        res = Result(row["id"], "statsmodels", row["mode"], params, ok=True)
        if code != 0:
            res.ok = False
            res.diffs.append(f"motor hata verdi: {out}")
        elif row["mode"] == "a-priori":
            nobs1 = float(row["sm_nobs1"])
            ratio = params["ratio"]
            exp_n1 = math.ceil(nobs1 - 1e-9)
            exp_n2 = math.ceil(ratio * nobs1 - 1e-9)
            if (out["n1"], out["n2"]) != (exp_n1, exp_n2):
                res.diffs.append(f"n1/n2: motor {out['n1']}/{out['n2']}, ⌈statsmodels⌉ {exp_n1}/{exp_n2} "
                                 f"(statsmodels n1 = {nobs1:.6f})")
                res.note = _explain_scale_mismatch(params, nobs1, exp_n1, exp_n2)
            res.n_ok = not res.diffs
            res.ok = not res.diffs
        else:
            sm_power = float(row["sm_power"])
            if abs(out["power"] - sm_power) > 1e-6:
                res.diffs.append(f"power: motor {out['power']!r}, statsmodels {sm_power!r}")
            res.ok = not res.diffs
        results.append(res)
    return results
