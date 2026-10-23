"""Differential comparison of the engine against its oracles.

Shared by tests/test_differential.py (assertions) and tools/differential_report.py (report).

Oracles:
- oracle/gpower_vectors.csv : values read from G*Power 3.1.9.7 screenshots (the real oracle)
- oracle/scale_vectors.csv  : statsmodels TTestIndPower (independent library, fractional N)
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from statistics import NormalDist

from gpower_clone import engine

ROOT = Path(__file__).resolve().parents[1]
GPOWER_CSV = ROOT / "oracle" / "gpower_vectors.csv"
GPOWER_RANDOM = ROOT / "oracle" / "gpower_random_apriori.jsonl"
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


def _oracle_self_inconsistency(row: dict, params: dict) -> str:
    """Does G*Power's displayed power disagree with the textbook formula at G*Power's OWN sample sizes?

    If so, G*Power's power function is numerically off for this input, and its N (found with that
    function) cannot be reproduced by a correct engine. Empty string = no such evidence.
    """
    if row["mode"] != "a-priori" or not row.get("gp_n1") or not row.get("gp_actual_power"):
        return ""
    check, code = engine.run({"test": "t2-indep", "mode": "post-hoc", "tails": params["tails"], "d": params["d"],
                              "alpha": params["alpha"], "n1": int(row["gp_n1"]), "n2": int(row["gp_n2"])})
    shown = float(row["gp_actual_power"])
    if code == 0 and abs(check["power"] - shown) > _shown_tolerance(row["gp_actual_power"]):
        return (f"kâhin sayısal hatası: G*Power kendi N'sinde ({row['gp_n1']}/{row['gp_n2']}) güç {shown} gösteriyor, "
                f"formül {check['power']:.7f} veriyor (df {int(row['gp_n1']) + int(row['gp_n2']) - 2:.2e})")
    # Huge df: the noncentral t equals the normal to ~1e-10, so an engine-independent (stdlib-only) check is
    # possible. If the previous even total already reaches the target, G*Power's N is not minimal.
    total = int(row["gp_n1"]) + int(row["gp_n2"])
    if total - 2 > 1e9:
        prev = total - 2
        ratio = params["ratio"]
        n1, n2 = prev / (1 + ratio), ratio * prev / (1 + ratio)
        delta = params["d"] * math.sqrt(n1 * n2 / (n1 + n2))
        z = NormalDist().inv_cdf(1 - params["alpha"] / params["tails"])
        phi = NormalDist().cdf
        normal_power = phi(delta - z) + (phi(-delta - z) if params["tails"] == 2 else 0.0)
        if normal_power > params["power"] + 1e-8:
            return (f"kâhin sayısal hatası: G*Power N = {total}, ama bir önceki çift toplam ({prev}) bağımsız normal "
                    f"yaklaşımla güç {normal_power:.10f} > hedef {params['power']} veriyor (df {prev:.2e}); "
                    f"G*Power'ın N'si minimal değil")
    return ""


def _random_rows() -> list[dict]:
    """oracle/gpower_random_apriori.jsonl (120 random a-priori readings) in the CSV row shape."""
    if not GPOWER_RANDOM.exists():
        return []
    rows = []
    for line in GPOWER_RANDOM.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        row = dict(rec["input"])
        row.update({f"gp_{k}": v for k, v in rec["outputs"].items() if v not in ("", "?")})
        row["gp_error"] = rec["dialog"]
        rows.append(row)
    return rows


def compare_gpower() -> list[Result]:
    results = []
    for row in _read(GPOWER_CSV) + _random_rows():
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
            if out.get("code") == "OUT_OF_RANGE" and out.get("field") in ("n1", "n2"):
                res.note = "sözleşme önceliği: CONTRACT §5 n1, n2 ≥ 2 der; G*Power n = 1'i kabul ediyor"
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
            if not res.ok:
                res.note = _oracle_self_inconsistency(row, params)
        if row["mode"] == "a-priori" and not gp_error:
            res.n_ok = not any(d.split(":")[0] in ("n1", "n2", "n_total") for d in res.diffs) and "error" not in out
        results.append(res)
    return results


def gpower_split(total_star: float, ratio: float) -> tuple[int, int]:
    """G*Power's a-priori rounding (LEDGER R-03..R-07): even total, half-up split."""
    x = total_star / 2
    total = max(4, 2 * math.ceil(math.floor(x * 1e10 + 0.5) / 1e10))
    n1 = math.floor(total / (1 + ratio) + 0.5)
    return n1, total - n1


def _explain_scale_mismatch(params: dict, nobs1: float) -> str:
    """Classify an a-priori disagreement with statsmodels. Empty string = unexplained."""
    ratio = params["ratio"]
    total_star = nobs1 * (1 + ratio)
    # Right at an even-total boundary the two solvers' tolerances decide the ceiling: not a rule difference.
    if abs(total_star / 2 - round(total_star / 2)) < 1e-6:
        return "sınırda"
    # Is statsmodels' continuous root really a root? Evaluate the continuous power there.
    at_root = engine.power_of(params["tails"], params["d"], params["alpha"],
                              total_star / (1 + ratio), ratio * total_star / (1 + ratio))
    if abs(at_root - params["power"]) > 1e-6:
        return (f"kâhin hatası: statsmodels'ın kökünde (N* = {total_star:.4f}) güç {at_root:.7f}, "
                f"hedef {params['power']} değil (SciPy nct NaN, kök bulucu saptı)")
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
            exp_n1, exp_n2 = gpower_split(nobs1 * (1 + params["ratio"]), params["ratio"])
            if (out["n1"], out["n2"]) != (exp_n1, exp_n2):
                res.diffs.append(f"n1/n2: motor {out['n1']}/{out['n2']}, G*Power kuralıyla statsmodels "
                                 f"{exp_n1}/{exp_n2} (statsmodels n1* = {nobs1:.6f})")
                res.note = _explain_scale_mismatch(params, nobs1)
            res.n_ok = not res.diffs
            res.ok = not res.diffs
        else:
            sm_power = float(row["sm_power"])
            if abs(out["power"] - sm_power) > 1e-6:
                res.diffs.append(f"power: motor {out['power']!r}, statsmodels {sm_power!r}")
            res.ok = not res.diffs
        results.append(res)
    return results
