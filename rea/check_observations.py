"""G*Power gözlemlerini (observations.jsonl) motorun CLI çıktısıyla ve hipotez tahminleriyle karşılaştırır.

Kullanım:  uv run python rea/check_observations.py

Hesap yapmaz: motoru CLI üzerinden çağırır, yalnızca JSON karşılaştırır.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INT_FIELDS = {"n1", "n2", "n_total", "df", "df1", "df2"}
TOL = 1e-6


def load(name):
    path = ROOT / name
    if not path.exists():
        return {}
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {row["id"]: row for row in rows}


def run_cli(inp):
    args = []
    for key, value in inp.items():
        args += [f"--{key}", str(value)]
    proc = subprocess.run(
        [sys.executable, "-c", "import sys; from gpower_clone.cli import main; sys.exit(main())", *args],
        capture_output=True, text=True, encoding="utf-8",
    )
    return json.loads(proc.stdout)


def matches(ours, observed):
    """observed'daki her alan ours'ta sözleşme toleransıyla tutuyor mu? (fark listesi döner)"""
    if "error" in observed:
        return [] if "error" in ours else ["G*Power hata verdi, biz sonuç ürettik"]
    if "error" in ours:
        return [f"biz hata verdik ({ours.get('code')}), G*Power sonuç üretti"]
    diffs = []
    for key, gp in observed.items():
        mine = ours.get(key)
        if mine is None:
            diffs.append(f"{key}: bizde yok")
        elif key in INT_FIELDS:
            if int(mine) != int(gp):
                diffs.append(f"{key}: biz {mine}, G*Power {gp}")
        else:
            delta = abs(mine - gp)
            if delta > TOL and delta > TOL * abs(gp):
                diffs.append(f"{key}: biz {mine:.7f}, G*Power {gp:.7f}")
    return diffs


def main():
    experiments = load("experiments.jsonl")
    observations = load("observations.jsonl")
    if not observations:
        print("observations.jsonl boş ya da yok. KANIT_DEFTERI.md'deki adımlarla G*Power gözlemlerini ekleyin.")
        return 1
    failed = 0
    for exp_id, obs in sorted(observations.items()):
        exp = experiments.get(exp_id)
        if exp is None:
            print(f"{exp_id}: experiments.jsonl'da yok, atlandı")
            continue
        ours = run_cli(exp["input"])
        diffs = matches(ours, obs["observed"])
        status = "TUTTU" if not diffs else "TUTMADI"
        failed += bool(diffs)
        print(f"{exp_id} ({exp['hypothesis']}): motor {status}")
        for diff in diffs:
            print(f"    {diff}")
        # Hangi hipotez tahmini gözlemle uyuşuyor?
        for name, pred in exp.get("predicted", {}).items():
            if "error" in pred or "error" in obs["observed"]:
                continue
            keys = [k for k in ("n1", "n2", "n_total") if k in pred and k in obs["observed"]]
            if keys and all(pred[k] == obs["observed"][k] for k in keys):
                print(f"    N alanları hipotez {name} ile uyuşuyor")
    print(f"\n{len(observations) - failed}/{len(observations)} gözlem motorla tutuyor")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
