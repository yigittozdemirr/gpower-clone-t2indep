"""numerics vs. an independent oracle (SciPy, test-only dependency): |error| <= 1e-9."""

from __future__ import annotations

import math
import random

import pytest

stats = pytest.importorskip("scipy.stats")

from gpower_clone import engine
from gpower_clone import numerics as nm

TOL = 1e-9
DFS = [1, 1.5, 2, 2.5, 3, 4.7, 7, 10, 17.3, 30, 58.6, 100, 174, 500.5, 1000, 3206, 10000]
T_VALUES = [-60, -35, -20, -8, -3, -1.6536, -0.4, -1e-3, 0.0, 1e-3, 0.4, 1.6536, 2.5, 3, 5,
            8, 12, 20, 35, 60]
NCPS = [0.0, 1e-4, 0.05, 0.3, 1, 2, 3.3166, 5, 8, 12, 17, 25, 33, 36.9, 37.1, 40]


@pytest.mark.parametrize("df", DFS)
def test_t_cdf_sf(df):
    for t in T_VALUES:
        assert abs(nm.t_cdf(t, df) - stats.t.cdf(t, df)) <= TOL, t
        assert abs(nm.t_sf(t, df) - stats.t.sf(t, df)) <= TOL, t


@pytest.mark.parametrize("df", DFS)
def test_t_isf(df):
    for q in [0.499, 0.4, 0.25, 0.1, 0.05, 0.025, 0.01, 0.005, 1e-3, 1e-4, 1e-6, 1e-9, 0.6, 0.9, 0.99]:
        ours = nm.t_isf(q, df)
        ref = stats.t.isf(q, df)
        assert abs(ours - ref) <= TOL * max(1.0, abs(ref)), (q, ours, ref)


@pytest.mark.parametrize("df", [1, 2, 2.7, 3, 10, 174, 1e4, 1e6, 1e9, 1e13])
def test_t_isf_roundtrip_extreme(df):
    # SciPy's own isf is not reliable this far out; check self-consistency instead.
    for q in [1e-12, 1e-30, 1e-100, 1e-200, 1e-300]:
        t = nm.t_isf(q, df)
        assert math.isfinite(t) and t > 0
        assert abs(nm.t_sf(t, df) - q) <= 1e-12 * q, (q, t)


@pytest.mark.parametrize("df", DFS)
def test_nct_cdf_both_tails(df):
    skipped = 0
    for ncp in NCPS:
        for t in T_VALUES:
            ours_cdf = nm.nct_cdf(t, df, ncp)
            ours_sf = nm.nct_sf(t, df, ncp)
            assert 0.0 <= ours_cdf <= 1.0 and not math.isnan(ours_cdf)
            if ncp == 0.0:
                ref_cdf, ref_sf = stats.t.cdf(t, df), stats.t.sf(t, df)
            else:
                ref_cdf, ref_sf = stats.nct.cdf(t, df, ncp), stats.nct.sf(t, df, ncp)
            if math.isnan(ref_cdf) or not 0.0 <= ref_cdf <= 1.0:
                skipped += 1
                assert ours_cdf < 1e-12, (t, ncp, ours_cdf)
            else:
                assert abs(ours_cdf - ref_cdf) <= TOL, (t, ncp, ours_cdf, ref_cdf)
            if not (math.isnan(ref_sf) or not 0.0 <= ref_sf <= 1.0):
                assert abs(ours_sf - ref_sf) <= TOL, (t, ncp, ours_sf, ref_sf)


def test_nct_negative_ncp():
    for df in [2, 10, 174, 5000]:
        for ncp in [-0.5, -3, -12]:
            for t in [-15, -3, -0.5, 0.5, 3]:
                ref = stats.nct.cdf(t, df, ncp)
                if math.isnan(ref):
                    continue
                assert abs(nm.nct_cdf(t, df, ncp) - ref) <= TOL


def test_nct_never_nan_for_huge_ncp():
    for df in [2, 10, 174, 1e5, 1e9]:
        for ncp in [50, 100, 500, 1e4, 1e8]:
            for t in [-10, 0.0, 1.65, 40, 1e3]:
                v = nm.nct_cdf(t, df, ncp)
                assert 0.0 <= v <= 1.0


@pytest.mark.parametrize("df", [1e5, 1e6, 1e7, 1e8])
def test_large_df_branch_consistency(df):
    # The 1/df expansion used for very large df must agree with the series
    # (beyond ~1e9 the series itself loses accuracy, which is why the expansion exists).
    for t in [-3, -1, 0.5, 2, 3]:
        for ncp in [0, 1, 3, 5]:
            asym = nm._asym_cdf_sf(t, df, ncp)[0]
            series = (nm._nct_cdf_pos(t, df, ncp) if t >= 0
                      else 1.0 - nm._nct_cdf_pos(-t, df, -ncp))
            assert abs(asym - series) <= TOL


def test_power_formula_against_scipy():
    rng = random.Random(20261023)
    for _ in range(150):
        tails = rng.choice([1, 2])
        d = rng.uniform(0.05, 2.5)
        alpha = math.exp(rng.uniform(math.log(1e-4), math.log(0.3)))
        n1 = rng.randint(2, 400)
        n2 = rng.randint(2, 400)
        df = n1 + n2 - 2
        ncp = d * math.sqrt(n1 * n2 / (n1 + n2))
        tc = stats.t.isf(alpha / tails, df)
        ref = stats.nct.sf(tc, df, ncp)
        if tails == 2:
            lower = stats.nct.cdf(-tc, df, ncp)
            ours_lower = nm.nct_cdf(-engine.critical_t(alpha, tails, df), df, ncp)
            if math.isnan(lower):          # SciPy fails far in the lower tail
                assert ours_lower < 1e-12
                lower = ours_lower
            ref += lower
        ours = engine.power_of(tails, d, alpha, n1, n2)
        assert abs(ours - ref) <= TOL, (tails, d, alpha, n1, n2, ours, ref)
        assert abs(engine.critical_t(alpha, tails, df) - tc) <= TOL * max(1, tc)


def test_brentq_simple():
    r = nm.brentq(lambda x: x * x - 2.0, 0.0, 2.0, xtol=1e-15)
    assert abs(r - math.sqrt(2.0)) < 1e-14
    with pytest.raises(nm.RootError):
        nm.brentq(lambda x: x * x + 1.0, 0.0, 2.0)


def test_betainc_against_scipy():
    special = pytest.importorskip("scipy.special")
    for a in [0.5, 1, 2.5, 10, 100.5, 5e3]:
        for b in [0.5, 1, 3, 87, 1e4]:
            for x in [1e-6, 0.01, 0.2, 0.5, 0.8, 0.99, 1 - 1e-9]:
                i, ic = nm.betainc(a, b, x)
                assert abs(i - special.betainc(a, b, x)) <= TOL
                assert abs(ic - special.betaincc(a, b, x)) <= TOL


def test_huge_ncp_quadrature_matches_series():
    # |ncp| > 1000 switches to quadrature; on the overlap both methods must agree.
    for df in [1, 3, 10, 100, 1000]:
        for ncp in [150.0, 600.0, 950.0]:
            for f in [0.7, 1.0, 1.1, 1.5, 10.0]:
                t = ncp * f
                assert abs(nm._nct_cdf_pos_integral(t, df, ncp) - nm._nct_cdf_pos(t, df, ncp)) <= TOL


def test_gammaincc_against_scipy():
    special = pytest.importorskip("scipy.special")
    for a in [0.5, 1, 1.5, 5, 50, 500.5, 5000]:
        for x in [1e-6, 0.1, 1, 4, 45, 60, 480, 5100, 1e4]:
            assert abs(nm.gammaincc(a, x) - special.gammaincc(a, x)) <= TOL
