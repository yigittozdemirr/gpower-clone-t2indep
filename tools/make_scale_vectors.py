"""Generate oracle/scale_vectors.csv: 600 statsmodels vectors for the t2-indep family.

statsmodels (TTestIndPower) is an independent implementation built on SciPy. It returns a
*fractional* nobs1 for a-priori; G*Power rounds up. Our engine must give
n1 = ceil(nobs1), n2 = ceil(ratio * nobs1) and the same post-hoc power.

    uv run python tools/make_scale_vectors.py
"""

from __future__ import annotations

import csv
import random
import warnings
from pathlib import Path

from statsmodels.stats.power import TTestIndPower

OUT = Path(__file__).resolve().parents[1] / "oracle" / "scale_vectors.csv"
N_A_PRIORI = 300
N_POST_HOC = 300
SEED = 20261023


def main() -> None:
    warnings.simplefilter("ignore")
    rng = random.Random(SEED)
    solver = TTestIndPower()
    rows = []
    while len(rows) < N_A_PRIORI:
        tails = rng.choice([1, 2])
        d = round(rng.uniform(0.1, 1.5), 3)
        alpha = rng.choice([0.001, 0.005, 0.01, 0.025, 0.05, 0.1])
        power = round(rng.uniform(0.5, 0.99), 3)
        ratio = rng.choice([0.25, 0.5, 0.7, 1, 1, 1, 1.5, 2, 2.5, 3, 4])
        alternative = "larger" if tails == 1 else "two-sided"
        try:
            nobs1 = float(solver.solve_power(effect_size=d, alpha=alpha, power=power,
                                             ratio=ratio, alternative=alternative))
        except Exception:
            continue
        if not 2 <= nobs1 < 1e6:
            continue
        rows.append(dict(id=f"S{len(rows) + 1:03d}", mode="a-priori", tails=tails, d=d, alpha=alpha,
                         power=power, ratio=ratio, n1="", n2="", sm_nobs1=repr(nobs1), sm_power=""))
    while len(rows) < N_A_PRIORI + N_POST_HOC:
        tails = rng.choice([1, 2])
        d = round(rng.uniform(0.05, 1.5), 3)
        alpha = rng.choice([0.001, 0.01, 0.05, 0.1])
        n1 = rng.randint(2, 400)
        n2 = rng.randint(2, 400)
        alternative = "larger" if tails == 1 else "two-sided"
        pw = float(solver.power(effect_size=d, nobs1=n1, alpha=alpha, ratio=n2 / n1,
                                alternative=alternative))
        rows.append(dict(id=f"S{len(rows) + 1:03d}", mode="post-hoc", tails=tails, d=d, alpha=alpha,
                         power="", ratio="", n1=n1, n2=n2, sm_nobs1="", sm_power=repr(pw)))
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} vectors -> {OUT.name}")


if __name__ == "__main__":
    main()
