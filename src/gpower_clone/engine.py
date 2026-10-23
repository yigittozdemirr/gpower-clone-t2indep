"""The single calculation + validation engine for the ``t2-indep`` family (SPEC.md).

Public API
----------
* ``run(params)``      params: dict (CLI strings or MCP JSON values) or a sequence of
                       (name, value) pairs (keeps duplicates).  Returns (obj, exit_code).
* ``run_argv(argv)``   CLI token list -> (obj, exit_code); syntax errors handled here too.
* ``to_json(obj)``     the one-line JSON text written to stdout / returned by MCP.
* ``version_info()``   the ``--version`` object.
"""

from __future__ import annotations

import json
import math
import platform
import re
from typing import Any, Iterable, Mapping

from . import numerics as nm

CONTRACT_VERSION = "1.0.0"
TEAM_NAME = "gpower-clone-t2indep"
TEST_ID = "t2-indep"

MODES: dict[str, tuple[str, ...]] = {
    "a-priori": ("tails", "d", "alpha", "power", "ratio"),
    "post-hoc": ("tails", "d", "alpha", "n1", "n2"),
    "compromise": ("tails", "d", "beta_alpha_ratio", "n1", "n2"),
    "criterion": ("tails", "d", "power", "n1", "n2"),
    "sensitivity": ("tails", "alpha", "power", "n1", "n2"),
}
INT_FIELDS = frozenset({"tails", "n1", "n2"})

N1_MAX = 1e7          # a-priori: n1* above this -> NO_SOLUTION   [SPEC 3.1, H-04]
D_MAX = 1000.0        # sensitivity search interval upper end      [SPEC 3.5]
ALPHA_MIN = 1e-300    # lower end of the alpha search (criterion / compromise)
ALPHA_MAX = 1.0 - 2.0 ** -53   # largest double below 1

_DEC_RE = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
_INT_RE = re.compile(r"[+-]?[0-9]+")


# ---------------------------------------------------------------------------
# output helpers
# ---------------------------------------------------------------------------


def to_json(obj: Mapping[str, Any]) -> str:
    """One-line JSON exactly as SPEC 5 prescribes (float repr, ints as ints)."""
    return json.dumps(obj, ensure_ascii=True, separators=(", ", ": "), allow_nan=False)


def version_info() -> dict:
    return {
        "contract_version": CONTRACT_VERSION,
        "name": TEAM_NAME,
        "engine": f"Python {platform.python_version()} (stdlib)",
    }


class EngineError(Exception):
    def __init__(self, code: str, message: str, field: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field

    def to_obj(self) -> dict:
        return {"error": self.message, "code": self.code, "field": self.field}

    @property
    def exit_code(self) -> int:
        return 1 if self.code in ("NO_SOLUTION", "INTERNAL") else 2


# ---------------------------------------------------------------------------
# statistics (SPEC 1)
# ---------------------------------------------------------------------------


def ncp_of(d: float, n1: float, n2: float) -> float:
    return d * math.sqrt(n1 * n2 / (n1 + n2))


def critical_t(alpha: float, tails: int, df: float) -> float:
    return nm.t_isf(alpha / tails, df)


def power_of(tails: int, d: float, alpha: float, n1: float, n2: float) -> float:
    df = n1 + n2 - 2.0
    delta = ncp_of(d, n1, n2)
    tc = critical_t(alpha, tails, df)
    p = 1.0 - nm.nct_cdf(tc, df, delta)
    if tails == 2:
        p += nm.nct_cdf(-tc, df, delta)
    return min(max(p, 0.0), 1.0)


def beta_of(tails: int, d: float, alpha: float, n1: float, n2: float) -> float:
    """beta = 1 - power, formed directly from the lower tail (keeps precision)."""
    df = n1 + n2 - 2.0
    delta = ncp_of(d, n1, n2)
    tc = critical_t(alpha, tails, df)
    b = nm.nct_cdf(tc, df, delta)
    if tails == 2:
        b -= nm.nct_cdf(-tc, df, delta)
    return min(max(b, 0.0), 1.0)


def _int_df(n1: int, n2: int) -> int:
    return n1 + n2 - 2


def _common_out(d: float, alpha: float, tails: int, n1: int, n2: int) -> dict:
    df = _int_df(n1, n2)
    return {
        "ncp": ncp_of(d, float(n1), float(n2)),
        "critical_t": critical_t(alpha, tails, float(df)),
        "df": df,
    }


def _ceil(x: float) -> int:
    return int(math.ceil(x - 1e-9))


# ---------------------------------------------------------------------------
# modes (SPEC 3)
# ---------------------------------------------------------------------------


def _a_priori(tails: int, d: float, alpha: float, power: float, ratio: float) -> dict:
    def f(n1: float) -> float:
        return power_of(tails, d, alpha, n1, ratio * n1) - power

    n1_lo = max(2.0, 2.0 / ratio)
    f_lo = f(n1_lo)
    if f_lo >= 0.0:
        n1_star = n1_lo
    else:
        lo, flo = n1_lo, f_lo
        hi = 2.0 * lo
        fhi = f(hi)
        while fhi < 0.0:
            if lo > N1_MAX:
                raise EngineError("NO_SOLUTION",
                                  "Gerekli örneklem büyüklüğü çok büyük (n1 > 1e7); çözüm üretilemedi",
                                  None)
            lo, flo = hi, fhi
            hi = 2.0 * hi
            fhi = f(hi)
        n1_star = nm.brentq(f, lo, hi, xtol=1e-10, rtol=4 * nm.EPS, fa=flo, fb=fhi)
    if n1_star > N1_MAX:
        raise EngineError("NO_SOLUTION",
                          "Gerekli örneklem büyüklüğü çok büyük (n1 > 1e7); çözüm üretilemedi", None)
    n1 = max(2, _ceil(n1_star))
    n2 = max(2, _ceil(ratio * n1_star))
    out = _common_out(d, alpha, tails, n1, n2)
    out["n1"] = n1
    out["n2"] = n2
    out["n_total"] = n1 + n2
    out["actual_power"] = power_of(tails, d, alpha, float(n1), float(n2))
    return out


def _post_hoc(tails: int, d: float, alpha: float, n1: int, n2: int) -> dict:
    out = _common_out(d, alpha, tails, n1, n2)
    out["power"] = power_of(tails, d, alpha, float(n1), float(n2))
    return out


def _alpha_root(g, what: str) -> float:
    """Root of a decreasing-or-increasing g on alpha in (0, 1) via bracketing + Brent.

    Tolerance: |delta alpha| <= min(1e-14, 1e-12 * alpha)  (SPEC 3.3).
    """
    hi = ALPHA_MAX
    g_hi = g(hi)
    if g_hi == 0.0:
        return hi
    lo = 1e-3
    g_lo = g(lo)
    if (g_lo > 0) == (g_hi > 0) and g_lo != 0.0:
        # move lo towards 0 until the sign changes
        while (g_lo > 0) == (g_hi > 0):
            if lo <= ALPHA_MIN:
                raise EngineError("NO_SOLUTION", f"{what}: α (0, 1) aralığında çözüm bulunamadı", None)
            hi, g_hi = lo, g_lo
            lo = max(lo * 1e-3, ALPHA_MIN)
            g_lo = g(lo)
    return nm.brentq(g, lo, hi, xtol=1e-14, rtol=1e-12, fa=g_lo, fb=g_hi, tol_mode="min")


def _compromise(tails: int, d: float, q: float, n1: int, n2: int) -> dict:
    fn1, fn2 = float(n1), float(n2)

    def g(a: float) -> float:
        return beta_of(tails, d, a, fn1, fn2) - q * a

    if g(ALPHA_MAX) > 0.0:
        raise EngineError("NO_SOLUTION", "compromise: α (0, 1) aralığında çözüm bulunamadı", None)
    alpha = _alpha_root(g, "compromise")
    out = _common_out(d, alpha, tails, n1, n2)
    beta = beta_of(tails, d, alpha, fn1, fn2)
    out["alpha"] = alpha
    out["beta"] = beta
    out["power"] = 1.0 - beta
    return out


def _criterion(tails: int, d: float, power: float, n1: int, n2: int) -> dict:
    fn1, fn2 = float(n1), float(n2)

    def g(a: float) -> float:
        return power_of(tails, d, a, fn1, fn2) - power

    if g(ALPHA_MAX) < 0.0 or g(ALPHA_MIN) > 0.0:
        raise EngineError("NO_SOLUTION", "criterion: α (0, 1) aralığında çözüm bulunamadı", None)
    alpha = _alpha_root(g, "criterion")
    out = _common_out(d, alpha, tails, n1, n2)
    out["alpha"] = alpha
    return out


def _sensitivity(tails: int, alpha: float, power: float, n1: int, n2: int) -> dict:
    fn1, fn2 = float(n1), float(n2)

    def g(d: float) -> float:
        return power_of(tails, d, alpha, fn1, fn2) - power

    no_sol = EngineError("NO_SOLUTION",
                         "sensitivity: d ∈ [0, 1000] aralığında hedef güce ulaşılamıyor", None)
    lo, g_lo = 0.0, g(0.0)
    if g_lo >= 0.0:  # cannot happen after the power > alpha check, kept for safety
        d = 0.0
    else:
        # expand the upper end geometrically inside [0, D_MAX] (keeps the ncp modest)
        hi = min(D_MAX, 4.0 / math.sqrt(fn1 * fn2 / (fn1 + fn2)))
        g_hi = g(hi)
        while g_hi < 0.0:
            if hi >= D_MAX:
                raise no_sol
            lo, g_lo = hi, g_hi
            hi = min(D_MAX, 2.0 * hi)
            g_hi = g(hi)
        d = nm.brentq(g, lo, hi, xtol=1e-14, rtol=1e-13, fa=g_lo, fb=g_hi)
    out = _common_out(d, alpha, tails, n1, n2)
    out["d"] = d
    return out


# ---------------------------------------------------------------------------
# validation (SPEC 2)
# ---------------------------------------------------------------------------


def _parse_decimal(field: str, v: Any) -> float:
    bad = EngineError("INVALID_VALUE", f"Geçersiz değer: '{field}' sonlu bir ondalık sayı olmalı "
                                       f"(ondalık ayırıcı nokta)", field)
    if isinstance(v, bool):
        raise bad
    if isinstance(v, int):
        try:
            x = float(v)
        except OverflowError:
            raise bad from None
    elif isinstance(v, float):
        x = v
    elif isinstance(v, str):
        if not _DEC_RE.fullmatch(v):
            raise bad
        x = float(v)
    else:
        raise bad
    if not math.isfinite(x):
        raise bad
    return x


def _parse_int(field: str, v: Any) -> int:
    bad = EngineError("INVALID_VALUE", f"Geçersiz değer: '{field}' bir tam sayı olmalı", field)
    if isinstance(v, bool):
        raise bad
    if isinstance(v, int):
        n = v
    elif isinstance(v, str):
        if not _INT_RE.fullmatch(v):
            raise bad
        n = int(v)
    else:
        raise bad
    try:
        float(n)
    except OverflowError:
        raise bad from None
    return n


_RANGE_MSG = {
    "tails": "'tails' 1 ya da 2 olmalı",
    "alpha": "'alpha' 0 ile 1 arasında olmalı (0 < alpha < 1)",
    "power": "'power' 0 ile 1 arasında olmalı (0 < power < 1)",
    "beta_alpha_ratio": "'beta_alpha_ratio' 0'dan büyük olmalı",
    "d": "'d' 0'dan büyük olmalı",
    "ratio": "'ratio' 0'dan büyük olmalı",
    "n1": "'n1' en az 2 olmalı",
    "n2": "'n2' en az 2 olmalı",
}


def _in_range(field: str, v: float | int) -> bool:
    if field == "tails":
        return v in (1, 2)
    if field in ("alpha", "power"):
        return 0.0 < v < 1.0
    if field in ("beta_alpha_ratio", "d", "ratio"):
        return v > 0.0
    if field in ("n1", "n2"):
        return v >= 2
    return True


def _validate_and_compute(pairs: list[tuple[str, Any]]) -> dict:
    # Values of None are treated as "not given" (MCP clients may send null).
    pairs = [(k, v) for k, v in pairs if v is not None]
    first: dict[str, Any] = {}
    for k, v in pairs:
        first.setdefault(k, v)

    # 2. test / mode present
    for f in ("test", "mode"):
        if f not in first:
            raise EngineError("MISSING_PARAM", f"Gerekli alan eksik: '{f}'", f)
    # 3. supported test / mode
    test, mode = first["test"], first["mode"]
    if not (isinstance(test, str) and test == TEST_ID):
        raise EngineError("UNSUPPORTED",
                          f"Desteklenmeyen test: {test!s}. Bu uygulama yalnızca 't2-indep' testini destekler",
                          "test")
    if not (isinstance(mode, str) and mode in MODES):
        raise EngineError("UNSUPPORTED",
                          f"Bilinmeyen mod: {mode!s}. Geçerli modlar: " + ", ".join(MODES), "mode")
    # 4. duplicate fields
    seen: set[str] = set()
    for k, _ in pairs:
        if k in seen:
            raise EngineError("INVALID_VALUE", f"Alan birden fazla kez verildi: '{k}'", k)
        seen.add(k)
    # 5. unknown / irrelevant fields (input order)
    fields = MODES[mode]
    for k, _ in pairs:
        if k in ("test", "mode"):
            continue
        if k not in fields:
            raise EngineError("UNKNOWN_PARAM",
                              f"'{mode}' modunda tanınmayan ya da ilgisiz alan: '{k}'", k)
    # 6. missing fields (table order)
    for f in fields:
        if f not in first:
            raise EngineError("MISSING_PARAM", f"Gerekli alan eksik: '{f}' ('{mode}' modu)", f)
    # 7. types (table order)
    vals: dict[str, Any] = {}
    for f in fields:
        vals[f] = _parse_int(f, first[f]) if f in INT_FIELDS else _parse_decimal(f, first[f])
    # 8. ranges (table order)
    for f in fields:
        if not _in_range(f, vals[f]):
            raise EngineError("OUT_OF_RANGE", "Aralık dışı değer: " + _RANGE_MSG[f], f)
    # 9. consistency
    if mode in ("a-priori", "sensitivity") and vals["power"] <= vals["alpha"]:
        raise EngineError("INCONSISTENT", "Power, alpha değerinden büyük olmalı", "power")
    # 10. compute
    if mode == "a-priori":
        out = _a_priori(vals["tails"], vals["d"], vals["alpha"], vals["power"], vals["ratio"])
    elif mode == "post-hoc":
        out = _post_hoc(vals["tails"], vals["d"], vals["alpha"], vals["n1"], vals["n2"])
    elif mode == "compromise":
        out = _compromise(vals["tails"], vals["d"], vals["beta_alpha_ratio"], vals["n1"], vals["n2"])
    elif mode == "criterion":
        out = _criterion(vals["tails"], vals["d"], vals["power"], vals["n1"], vals["n2"])
    else:
        out = _sensitivity(vals["tails"], vals["alpha"], vals["power"], vals["n1"], vals["n2"])
    for k, v in out.items():
        if isinstance(v, float) and not math.isfinite(v):
            raise EngineError("INTERNAL", f"Hesap sonlu olmayan bir değer üretti: '{k}'", None)
    return out


def run(params: Mapping[str, Any] | Iterable[tuple[str, Any]]) -> tuple[dict, int]:
    """Validate + compute.  Returns (output-or-error object, exit code)."""
    try:
        if isinstance(params, Mapping):
            pairs = list(params.items())
        else:
            pairs = [(str(k), v) for k, v in params]
        return _validate_and_compute(pairs), 0
    except EngineError as e:
        return e.to_obj(), e.exit_code
    except Exception as e:  # pragma: no cover - defensive
        err = EngineError("INTERNAL", f"Beklenmeyen iç hata: {type(e).__name__}: {e}", None)
        return err.to_obj(), 1


def run_argv(argv: list[str]) -> tuple[dict, int]:
    """CLI entry: ``--name value`` tokens -> run().

    * ``--version`` as the only token -> version object.
    * a token not starting with ``--`` where a flag is expected -> UNKNOWN_PARAM
    * a flag that is the last token or is followed by another ``--`` token -> INVALID_VALUE
    These syntax errors are reported first, in token order.
    """
    if list(argv) == ["--version"]:
        return version_info(), 0
    pairs: list[tuple[str, str]] = []
    i = 0
    n = len(argv)
    while i < n:
        tok = argv[i]
        if not tok.startswith("--"):
            err = EngineError("UNKNOWN_PARAM", f"Beklenmeyen konumsal argüman: '{tok}'", tok)
            return err.to_obj(), err.exit_code
        name = tok[2:]
        if i + 1 >= n or argv[i + 1].startswith("--"):
            err = EngineError("INVALID_VALUE", f"'--{name}' için değer verilmedi", name)
            return err.to_obj(), err.exit_code
        pairs.append((name, argv[i + 1]))
        i += 2
    return run(pairs)
