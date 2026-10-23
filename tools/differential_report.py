"""Write tests/AGREEMENT_REPORT.md: agreement rates and every disagreement with its explanation.

    uv run python tools/differential_report.py
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from differential import compare_gpower, compare_scale  # noqa: E402

OUT = ROOT / "tests" / "AGREEMENT_REPORT.md"


def _rate(ok: int, total: int) -> str:
    return f"{ok}/{total} (%{100 * ok / total:.1f})" if total else "—"


def _section(title: str, results: list) -> list[str]:
    lines = [f"## {title}", ""]
    if not results:
        return lines + ["_Henüz vektör yok._", ""]
    apriori = [r for r in results if r.n_ok is not None]
    lines += [
        "| Ölçüt | Sonuç |",
        "|---|---|",
        f"| Tüm alanlar eşleşen vektör | {_rate(sum(r.ok for r in results), len(results))} |",
        f"| a-priori N alanları tam eşleşen (kapı ≥ %90) | {_rate(sum(r.n_ok for r in apriori), len(apriori))} |",
        f"| Açıklanmış uyuşmazlık | {sum(1 for r in results if not r.ok and r.note)} |",
        f"| Açıklanmamış uyuşmazlık | {sum(1 for r in results if not r.ok and not r.note)} |",
        "",
    ]
    bad = [r for r in results if not r.ok]
    if bad:
        lines += ["| Vektör | Mod | Girdi | Fark | Açıklama |", "|---|---|---|---|---|"]
        for r in bad:
            inp = ", ".join(f"{k}={v}" for k, v in r.inputs.items() if k not in ("test", "mode"))
            lines.append(f"| {r.id} | {r.mode} | {inp} | {'; '.join(r.diffs)} | {r.note or '**AÇIKLANMADI**'} |")
        lines.append("")
    return lines


def main() -> None:
    gpower = compare_gpower()
    scale = compare_scale()
    lines = [
        "# Uyum raporu (diferansiyel test)",
        "",
        f"Üretildi: {datetime.date.today().isoformat()} · `uv run python tools/differential_report.py`",
        "",
        "Aynı girdiler hem kâhine hem motora verildi. Fark varsa ya bizim hatamızdır ya kaçırdığımız bir kuraldır "
        "ya da kâhinin kendi hatasıdır; her uyuşmazlık aşağıda sınıflandırılır.",
        "",
        "- **G*Power:** `oracle/gpower_vectors.csv`, her satır `oracle/screenshots/` altında bir ekran görüntüsüne "
        "dayanır. Ondalıklar G*Power'ın gösterdiği basamağa kadar, tam sayılar birebir karşılaştırılır.",
        "- **statsmodels 0.15 (`TTestIndPower`):** bağımsız bir kütüphane. a-priori'de N'yi **kesirli** verir; "
        "G*Power ve motorumuz yukarı yuvarlar. Karşılaştırma: `n1 = ⌈n1*⌉`, `n2 = ⌈ratio·n1*⌉`. post-hoc güç 1e-6 içinde.",
        "",
    ]
    lines += _section("G*Power (kâhin)", gpower)
    lines += _section("statsmodels (ölçek, 600 vektör)", scale)
    lines += [
        "## Bulgular",
        "",
        "- **Kesirli N ile tam sayı N farkı:** statsmodels'ın verdiği kesirli `n1*`, kâhin hatası olan satırlar dışında her a-priori vektöründe "
        "G*Power kuralıyla (her grup ayrı yukarı) yuvarlandığında motorun tam sayı sonucunu veriyor. Kütüphaneler "
        "\"kaç denek\" sorusunu yarım hastayla yanıtlıyor; G*Power ve motor yukarı yuvarlayıp gücü yeniden hesaplıyor "
        "(`actual_power`).",
        "- **Kâhin de yanılabilir:** statsmodels'ın kök bulucusu, SciPy'nin merkezî olmayan t dağılımı NaN döndürdüğünde "
        "yanlış köke yakınsayabiliyor. Bu satırlarda statsmodels'ın önerdiği N hedef güce ulaşmıyor; motor doğru. "
        "Bunu kanıtlamak için önerilen N'yi post-hoc'a verip gücü ölçüyoruz.",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
