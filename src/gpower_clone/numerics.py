"""Special functions for the t2-indep power engine (pure standard library).

Contents
--------
* ``lbeta``            log B(a, b), accurate also when one argument is huge
* ``betainc``          regularized incomplete beta I_x(a, b) and its complement
                       (modified Lentz continued fraction, NR-style symmetry)
* ``norm_cdf`` / ``norm_sf`` / ``norm_ppf``
* ``t_cdf`` / ``t_sf`` / ``t_isf``      central Student t
* ``nct_cdf`` / ``nct_sf``              noncentral t (Poisson mixture of incomplete
                       beta functions, Lenth 1989 / AS 243 representation, summed
                       outwards from the Poisson mode in both directions; very large
                       |ncp| -> quadrature over Z with the incomplete gamma function;
                       negligible tails (normal-approximation |z| > 40) clamped to 0 / 1;
                       df >= 1e5 with small t^2/df -> O(1/df^2) asymptotic expansion)
* ``brentq``           safeguarded Brent root finder

Every function is total on its documented domain: nothing returns NaN.
"""

from __future__ import annotations

import math

EPS = 2.220446049250313e-16
TINY = 1e-300
_LOG_SQRT_2PI = 0.5 * math.log(2.0 * math.pi)
_SQRT2 = math.sqrt(2.0)

# --------------------------------------------------------------------------
# log-gamma helpers
# --------------------------------------------------------------------------


def _stirling_corr(x: float) -> float:
    """lgamma(x) - [(x-1/2)log x - x + log sqrt(2 pi)]  for x >= 10."""
    z = 1.0 / (x * x)
    return (
        1.0 / 12.0
        - z * (1.0 / 360.0 - z * (1.0 / 1260.0 - z * (1.0 / 1680.0 - z * (1.0 / 1188.0 - z * (691.0 / 360360.0)))))
    ) / x


def lgamma_diff(x: float, h: float) -> float:
    """lgamma(x + h) - lgamma(x) without cancellation when x is large (x > 0, h >= 0)."""
    if x < 10.0:
        return math.lgamma(x + h) - math.lgamma(x)
    # (x+h-1/2) log(x+h) - (x-1/2) log x - h  rewritten with log1p
    r = h / x
    main = h * math.log(x) + (x + h - 0.5) * math.log1p(r) - h
    return main + _stirling_corr(x + h) - _stirling_corr(x)


def log_poisson_like(m: float, lam: float) -> float:
    """log( e^-lam lam^m / Gamma(m+1) ) for real m >= 0, lam > 0, accurate for huge m ~ lam.

    Saddle-point form (Loader): -bd0(m, lam) - 1/2 log(2 pi m) - stirling_corr(m), with
    bd0 = m log(m/lam) + lam - m = lam [(1+v) log1p(v) - v], v = (m - lam)/lam.
    """
    if m < 10.0:
        return -lam + m * math.log(lam) - math.lgamma(m + 1.0)
    v = (m - lam) / lam
    bd0 = lam * ((1.0 + v) * math.log1p(v) - v)
    return -bd0 - 0.5 * math.log(2.0 * math.pi * m) - _stirling_corr(m)


def lbeta(a: float, b: float) -> float:
    """log B(a, b) = lgamma(a) + lgamma(b) - lgamma(a + b), a, b > 0."""
    big, small = (a, b) if a >= b else (b, a)
    if big < 10.0:
        return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    return math.lgamma(small) - lgamma_diff(big, small)


# --------------------------------------------------------------------------
# regularized incomplete beta
# --------------------------------------------------------------------------


def _betacf(a: float, b: float, x: float, y: float, maxiter: int = 100000) -> float:
    """Continued fraction for I_x(a,b) (modified Lentz), converges for x < (a+1)/(a+b+2).

    ``y`` = 1 - x; the first denominator 1 - (a+b)x/(a+1) is formed from it when x is
    close to 1 (avoids cancellation when a is huge, e.g. t with very large df).
    """
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    if x > 0.5:
        d = (1.0 - b + qab * y) / qap
    else:
        d = 1.0 - qab * x / qap
    if abs(d) < TINY:
        d = TINY
    d = 1.0 / d
    h = d
    for m in range(1, maxiter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < TINY:
            d = TINY
        c = 1.0 + aa / c
        if abs(c) < TINY:
            c = TINY
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < TINY:
            d = TINY
        c = 1.0 + aa / c
        if abs(c) < TINY:
            c = TINY
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-16:
            break
    return h


def _logs(x: float, y: float) -> tuple[float, float]:
    lx = math.log(x) if x < 0.5 else math.log1p(-y)
    ly = math.log(y) if y < 0.5 else math.log1p(-x)
    return lx, ly


def betainc(a: float, b: float, x: float, y: float | None = None,
            lx: float | None = None, ly: float | None = None) -> tuple[float, float]:
    """Return (I_x(a,b), 1 - I_x(a,b)), both with full relative accuracy.

    ``y`` may be given as an accurately computed ``1 - x``; ``lx``/``ly`` as
    accurately computed log x / log y (needed when x or y underflows).
    """
    if y is None:
        y = 1.0 - x
    if lx is None or ly is None:
        if x <= 0.0:
            return 0.0, 1.0
        if y <= 0.0:
            return 1.0, 0.0
        lx, ly = _logs(x, y)
    log_front = a * lx + b * ly - lbeta(a, b)
    if x < (a + 1.0) / (a + b + 2.0):
        v = math.exp(log_front - math.log(a)) * _betacf(a, b, x, y)
        v = min(max(v, 0.0), 1.0)
        return v, 1.0 - v
    w = math.exp(log_front - math.log(b)) * _betacf(b, a, y, x)
    w = min(max(w, 0.0), 1.0)
    return 1.0 - w, w


# --------------------------------------------------------------------------
# normal distribution
# --------------------------------------------------------------------------


def norm_cdf(z: float) -> float:
    return 0.5 * math.erfc(-z / _SQRT2)


def norm_sf(z: float) -> float:
    return 0.5 * math.erfc(z / _SQRT2)


def norm_ppf(p: float) -> float:
    """Acklam's rational approximation (rel. err ~1e-9) plus one Halley step."""
    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf
    a = (-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02,
         1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00)
    b = (-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02,
         6.680131188771972e01, -1.328068155288572e01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00,
         -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00,
         3.754408661907416e00)
    plow = 0.02425
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    elif p <= 1.0 - plow:
        q = p - 0.5
        r = q * q
        x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
            (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    else:
        q = math.sqrt(-2.0 * math.log1p(-p))
        x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    # one Halley refinement
    e = norm_cdf(x) - p
    if math.isfinite(x) and abs(x) < 37.0:
        u = e * math.sqrt(2.0 * math.pi) * math.exp(x * x / 2.0)
        x = x - u / (1.0 + x * u / 2.0)
    return x


# --------------------------------------------------------------------------
# central t distribution
# --------------------------------------------------------------------------


def _t_xy(t: float, df: float) -> tuple[float, float, float, float]:
    """x = t^2/(t^2+df), y = df/(t^2+df) and their logs, without overflow/cancellation."""
    at = abs(t)
    if at == 0.0:
        return 0.0, 1.0, -math.inf, 0.0
    if at > 1e100:
        r = (df / at) / at  # df / t^2, may underflow
        lr = math.log(df) - 2.0 * math.log(at)
        l1 = math.log1p(r)
        return 1.0 / (1.0 + r), r / (1.0 + r), -l1, lr - l1
    t2 = at * at
    s = t2 + df
    x, y = t2 / s, df / s
    if x < 1e-300:
        lx = 2.0 * math.log(at) - math.log(df) - math.log1p(t2 / df)
        return x, y, lx, math.log1p(-x)
    lx, ly = _logs(x, y)
    return x, y, lx, ly


_ASYM_DF = 1e7      # df at/above which the 1/df expansion replaces the beta series
_ASYM_T2DF = 1e-3   # ... provided t^2/df is at most this (expansion error ~ (t^2/df)^3)


def _use_asym(t: float, df: float) -> bool:
    if df >= _ASYM_DF:
        return t * t <= _ASYM_T2DF * df
    if df >= 1e5:
        return t * t <= 1e-4 * df
    return False


def _asym_cdf_sf(t: float, df: float, delta: float) -> tuple[float, float]:
    """Large-df expansion of P(T <= t), T = (Z + delta)/sqrt(chi2_df/df).

    F = E[Phi(t sqrt(W) - delta)],  W = chi2_df/df; Taylor expansion of
    g(w) = Phi(t sqrt(w) - delta) around w = 1 with the central moments of W
    (2/df, 8/df^2, 12/df^2 + ...), kept to O(1/df^2).  Error O((t^2/df)^3).
    Returns (cdf, sf) with relative accuracy in both tails.
    """
    u = t - delta
    h1, h2, h3, h4 = t / 2.0, -t / 4.0, 3.0 * t / 8.0, -15.0 * t / 16.0
    c2 = -u * h1 * h1 + h2
    c3 = (u * u - 1.0) * h1 ** 3 - 3.0 * u * h1 * h2 + h3
    c4 = ((-u ** 3 + 3.0 * u) * h1 ** 4 + 6.0 * (u * u - 1.0) * h1 * h1 * h2
          - u * (3.0 * h2 * h2 + 4.0 * h1 * h3) + h4)
    phi = math.exp(-0.5 * u * u - _LOG_SQRT_2PI)
    corr = phi * (c2 / df + (4.0 / 3.0) * c3 / (df * df) + 0.5 * c4 / (df * df))
    cdf = norm_cdf(u) + corr
    sf = norm_sf(u) - corr
    return min(max(cdf, 0.0), 1.0), min(max(sf, 0.0), 1.0)


def t_sf(t: float, df: float) -> float:
    """P(T > t) for central t with df > 0 degrees of freedom."""
    if math.isinf(t):
        return 0.0 if t > 0 else 1.0
    if t == 0.0:
        return 0.5
    if _use_asym(t, df):
        return _asym_cdf_sf(t, df, 0.0)[1]
    x, y, lx, ly = _t_xy(t, df)
    # P(|T| > |t|) = I_y(df/2, 1/2) = 1 - I_x(1/2, df/2)
    i_x, i_x_c = betainc(0.5, 0.5 * df, x, y, lx, ly)
    tail = 0.5 * i_x_c
    return tail if t > 0 else 1.0 - tail


def t_cdf(t: float, df: float) -> float:
    return t_sf(-t, df)


def t_logpdf(t: float, df: float) -> float:
    at = abs(t)
    if at > 1e100:
        l1p = 2.0 * math.log(at) - math.log(df) + math.log1p((df / at) / at)
    else:
        l1p = math.log1p(at * at / df)
    return lgamma_diff(0.5 * df, 0.5) - 0.5 * math.log(df * math.pi) - 0.5 * (df + 1.0) * l1p


def t_isf(q: float, df: float) -> float:
    """Upper quantile: t such that P(T > t) = q, 0 < q < 1. Relative error <= 1e-13."""
    if not 0.0 < q < 1.0:
        if q <= 0.0:
            return math.inf
        return -math.inf
    if q == 0.5:
        return 0.0
    if q > 0.5:
        return -t_isf(1.0 - q, df)
    # q < 0.5 -> t > 0. Bracket [lo, hi] with sf(lo) > q > sf(hi).
    z = -norm_ppf(q)
    if not math.isfinite(z) or z <= 0.0:
        z = 1e-3
    guess = z + (z ** 3 + z) / (4.0 * df)
    if not math.isfinite(guess) or guess <= 0.0:
        guess = z
    lo, hi = 0.0, None
    t = guess
    logq = math.log(q)
    for _ in range(4000):
        s = t_sf(t, df)
        if s > q:
            lo = t
            t *= 4.0
        else:
            hi = t
            break
        if math.isinf(t):
            return math.inf
    # Safeguarded Newton on log sf(t) - log q inside the bracket.
    t = hi if lo == 0.0 else 0.5 * (lo + hi)
    if lo < guess < hi:
        t = guess
    for _ in range(100):
        s = t_sf(t, df)
        if s <= 0.0:
            hi = t
            newt = _mid(lo, hi)
        else:
            f = math.log(s) - logq
            if f == 0.0:
                return t
            if f > 0.0:
                lo = t
            else:
                hi = t
            dlog = -math.exp(t_logpdf(t, df) - math.log(s))  # d/dt log sf
            newt = t - f / dlog if dlog != 0.0 else math.nan
            if not (lo < newt < hi) or not math.isfinite(newt):
                newt = _mid(lo, hi)
        if abs(newt - t) <= 1e-15 * abs(newt) or hi - lo <= 1e-15 * hi:
            return newt
        t = newt
    return t


def _mid(lo: float, hi: float) -> float:
    if lo > 0.0:
        return math.sqrt(lo) * math.sqrt(hi)
    return 0.5 * hi


# --------------------------------------------------------------------------
# noncentral t distribution
# --------------------------------------------------------------------------

_CLAMP_Z = 40.0   # normal-approximation z beyond which F is < 1e-300 away from 0 / 1


def _nct_cdf_pos(t: float, df: float, delta: float) -> float:
    """F(t; df, delta) for t >= 0 (any sign of delta).

    F = Phi(-delta) + 1/2 * sum_i [ P_i I_x(i+1/2, df/2) + sgn(delta) R_i I_x(i+1, df/2) ]
    P_i = e^-lam lam^i / i!,  R_i = e^-lam lam^(i+1/2) / Gamma(i+3/2),  lam = delta^2/2,
    x = t^2/(t^2+df).  Summed from the Poisson mode outwards in both directions.
    """
    base = norm_cdf(-delta)
    if t == 0.0:
        return base
    if abs(delta) > _SERIES_DELTA_MAX:
        return _nct_cdf_pos_integral(t, df, delta)
    x, y, lx, ly = _t_xy(t, df)
    b = 0.5 * df
    if delta == 0.0:
        ix, _ = betainc(0.5, b, x, y, lx, ly)
        return min(1.0, base + 0.5 * ix)
    lam = 0.5 * delta * delta
    sgn = 1.0 if delta > 0 else -1.0
    k = int(lam)
    # starting values at the mode
    a1 = k + 0.5
    a2 = k + 1.0
    p_k = math.exp(log_poisson_like(float(k), lam))
    r_k = math.exp(log_poisson_like(k + 0.5, lam))
    i1_k, _ = betainc(a1, b, x, y, lx, ly)
    i2_k, _ = betainc(a2, b, x, y, lx, ly)
    # log of g(a) = x^a y^b / (a B(a,b)),  I(a+1) = I(a) - g(a)
    lg1_k = a1 * lx + b * ly - math.log(a1) - lbeta(a1, b)
    lg2_k = a2 * lx + b * ly - math.log(a2) - lbeta(a2, b)

    total = p_k * i1_k + sgn * r_k * i2_k
    maxsteps = int(40.0 * math.sqrt(lam)) + 2000

    # forward: i = k+1, k+2, ...
    p, r, i1, i2, lg1, lg2 = p_k, r_k, i1_k, i2_k, lg1_k, lg2_k
    i = k
    for _ in range(maxsteps):
        a_1 = i + 0.5
        a_2 = i + 1.0
        i1 -= math.exp(lg1)
        i2 -= math.exp(lg2)
        lg1 += lx + math.log((a_1 + b) / (a_1 + 1.0))
        lg2 += lx + math.log((a_2 + b) / (a_2 + 1.0))
        i += 1
        p *= lam / i
        r *= lam / (i + 0.5)
        if i1 < 0.0:
            i1 = 0.0
        if i2 < 0.0:
            i2 = 0.0
        term = p * i1 + sgn * r * i2
        total += term
        if i + 1 > lam:
            ratio = lam / (i + 1.0)
            bound = (p * i1 + r * i2) * ratio / (1.0 - ratio)
            if bound < 1e-17 or (i1 == 0.0 and i2 == 0.0) or (p == 0.0 and r == 0.0):
                break

    # backward: i = k-1, ..., 0
    p, r, i1, i2, lg1, lg2 = p_k, r_k, i1_k, i2_k, lg1_k, lg2_k
    i = k
    for _ in range(maxsteps):
        if i == 0:
            break
        a_1 = i + 0.5
        a_2 = i + 1.0
        # g(a-1) = g(a) * a / (x (a+b-1))
        lg1 += math.log(a_1 / (a_1 + b - 1.0)) - lx
        lg2 += math.log(a_2 / (a_2 + b - 1.0)) - lx
        i1 += math.exp(lg1) if lg1 < 700 else math.inf
        i2 += math.exp(lg2) if lg2 < 700 else math.inf
        if i1 > 1.0:
            i1 = 1.0
        if i2 > 1.0:
            i2 = 1.0
        p *= i / lam
        r *= (i + 0.5) / lam
        i -= 1
        total += p * i1 + sgn * r * i2
        if i < lam:
            ratio = i / lam
            bound = (p + r) * ratio / (1.0 - ratio)
            if bound < 1e-17:
                break

    f = base + 0.5 * total
    return min(max(f, 0.0), 1.0)


_SERIES_DELTA_MAX = 1000.0   # beyond |delta| = 1000 the Poisson series gets long; integrate instead


def gammaincc(a: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(a, x) (series / Lentz continued fraction)."""
    if x <= 0.0:
        return 1.0
    if math.isinf(x):
        return 0.0
    log_front = -x + a * math.log(x) - math.lgamma(a)
    if x < a + 1.0:
        ap = a
        term = 1.0 / a
        total = term
        for _ in range(100000):
            ap += 1.0
            term *= x / ap
            total += term
            if abs(term) < abs(total) * 1e-17:
                break
        p = total * math.exp(log_front)
        return min(max(1.0 - p, 0.0), 1.0)
    b = x + 1.0 - a
    c = 1.0 / TINY
    d = 1.0 / b
    h = d
    for i in range(1, 100000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < TINY:
            d = TINY
        c = b + an / c
        if abs(c) < TINY:
            c = TINY
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-16:
            break
    return min(max(math.exp(log_front) * h, 0.0), 1.0)


_GL_CACHE: dict[int, list[tuple[float, float]]] = {}


def _gauss_legendre(n: int) -> list[tuple[float, float]]:
    """Nodes/weights on [-1, 1] (Newton on P_n)."""
    if n in _GL_CACHE:
        return _GL_CACHE[n]
    out = []
    for i in range(1, n + 1):
        x = math.cos(math.pi * (i - 0.25) / (n + 0.5))
        for _ in range(100):
            p0, p1 = 1.0, x
            for k in range(2, n + 1):
                p0, p1 = p1, ((2 * k - 1) * x * p1 - (k - 1) * p0) / k
            dp = n * (x * p1 - p0) / (x * x - 1.0)
            dx = p1 / dp
            x -= dx
            if abs(dx) < 1e-16:
                break
        p0, p1 = 1.0, x
        for k in range(2, n + 1):
            p0, p1 = p1, ((2 * k - 1) * x * p1 - (k - 1) * p0) / k
        dp = n * (x * p1 - p0) / (x * x - 1.0)
        out.append((x, 2.0 / ((1.0 - x * x) * dp * dp)))
    _GL_CACHE[n] = out
    return out


def _nct_cdf_pos_integral(t: float, df: float, delta: float) -> float:
    """F(t; df, delta), t > 0, by quadrature over Z (used for very large |delta|).

    F = Phi(-delta) + int_{z > -delta} phi(z) Q(df/2, df (z+delta)^2 / (2 t^2)) dz,
    since T <= t  <=>  Z + delta <= t S  and  P(S >= s) = Q(df/2, df s^2 / 2).
    The z-range is truncated to [-12, 12] (phi mass outside < 1e-32).
    """
    lo = max(-delta, -12.0)
    hi = 12.0
    base = norm_cdf(-delta)
    if lo >= hi:
        return min(max(base, 0.0), 1.0)
    a = 0.5 * df
    nodes = _gauss_legendre(20)
    # the Q factor varies on the z-scale t / sqrt(2 df): keep panels narrower than that
    pw = min(1.0, 0.5 * t / math.sqrt(2.0 * df))
    panels = min(4000, max(1, int(math.ceil((hi - lo) / pw))))
    width = (hi - lo) / panels
    total = 0.0
    for j in range(panels):
        c = lo + (j + 0.5) * width
        half = 0.5 * width
        for xg, wg in nodes:
            z = c + half * xg
            s = (z + delta) / t
            q = gammaincc(a, a * s * s)
            total += wg * half * math.exp(-0.5 * z * z - _LOG_SQRT_2PI) * q
    return min(max(base + total, 0.0), 1.0)


def _nct_normal_z(t: float, df: float, delta: float) -> float:
    """Normal approximation z for P(T <= t) (used only to detect negligible tails)."""
    num = t * (1.0 - 1.0 / (4.0 * df)) - delta
    den = math.hypot(1.0, t / math.sqrt(2.0 * df))
    return num / den


def nct_cdf(t: float, df: float, delta: float) -> float:
    """P(T <= t) for the noncentral t distribution (df > 0, any real delta)."""
    if math.isinf(t):
        return 1.0 if t > 0 else 0.0
    if delta == 0.0:
        return t_cdf(t, df)
    if _use_asym(t, df):
        return _asym_cdf_sf(t, df, delta)[0]
    if abs(delta) > 37.0:
        z = _nct_normal_z(t, df, delta)
        if z < -_CLAMP_Z:
            return 0.0
        if z > _CLAMP_Z:
            return 1.0
    if t >= 0.0:
        return _nct_cdf_pos(t, df, delta)
    return 1.0 - _nct_cdf_pos(-t, df, -delta)


def nct_sf(t: float, df: float, delta: float) -> float:
    """P(T > t)."""
    return 1.0 - nct_cdf(t, df, delta)


# --------------------------------------------------------------------------
# root finding
# --------------------------------------------------------------------------


class RootError(ValueError):
    pass


def brentq(f, xa: float, xb: float, xtol: float = 1e-12, rtol: float = 4 * EPS,
           maxiter: int = 500, fa: float | None = None, fb: float | None = None,
           tol_mode: str = "sum") -> float:
    """Brent's method (as in SciPy's brentq).  Requires f(xa) and f(xb) of opposite sign.

    Stopping half-width:  tol_mode "sum": (xtol + rtol*|x|)/2 ;  "min": min(xtol, rtol*|x|)/2.
    """
    xpre, xcur = float(xa), float(xb)
    fpre = f(xpre) if fa is None else fa
    fcur = f(xcur) if fb is None else fb
    if fpre == 0.0:
        return xpre
    if fcur == 0.0:
        return xcur
    if (fpre > 0) == (fcur > 0):
        raise RootError("root not bracketed")
    xblk = fblk = spre = scur = 0.0
    for _ in range(maxiter):
        if fpre != 0.0 and fcur != 0.0 and ((fpre > 0) != (fcur > 0)):
            xblk = xpre
            fblk = fpre
            spre = scur = xcur - xpre
        if abs(fblk) < abs(fcur):
            xpre, xcur, xblk = xcur, xblk, xcur
            fpre, fcur, fblk = fcur, fblk, fcur
        if tol_mode == "min":
            delta = 0.5 * max(min(xtol, rtol * abs(xcur)), 4 * EPS * abs(xcur), 1e-320)
        else:
            delta = 0.5 * (xtol + rtol * abs(xcur))
        sbis = 0.5 * (xblk - xcur)
        if fcur == 0.0 or abs(sbis) < delta:
            return xcur
        if abs(spre) > delta and abs(fcur) < abs(fpre):
            if xpre == xblk:
                stry = -fcur * (xcur - xpre) / (fcur - fpre)
            else:
                dpre = (fpre - fcur) / (xpre - xcur)
                dblk = (fblk - fcur) / (xblk - xcur)
                stry = -fcur * (fblk * dblk - fpre * dpre) / (dblk * dpre * (fblk - fpre))
            if 2.0 * abs(stry) < min(abs(spre), 3.0 * abs(sbis) - delta):
                spre = scur
                scur = stry
            else:
                spre = sbis
                scur = sbis
        else:
            spre = sbis
            scur = sbis
        xpre = xcur
        fpre = fcur
        if abs(scur) > delta:
            xcur += scur
        else:
            xcur += delta if sbis > 0 else -delta
        fcur = f(xcur)
    return xcur
