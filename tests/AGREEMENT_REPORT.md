# Uyum raporu (diferansiyel test)

Üretildi: 2026-10-23 · `uv run python tools/differential_report.py`

Aynı girdiler hem kâhine hem motora verildi. Fark varsa ya bizim hatamızdır ya kaçırdığımız bir kuraldır ya da kâhinin kendi hatasıdır; her uyuşmazlık aşağıda sınıflandırılır.

- **G*Power:** `oracle/gpower_vectors.csv`, her satır `oracle/screenshots/` altında bir ekran görüntüsüne dayanır. Ondalıklar G*Power'ın gösterdiği basamağa kadar, tam sayılar birebir karşılaştırılır.
- **statsmodels 0.15 (`TTestIndPower`):** bağımsız bir kütüphane. a-priori'de N'yi **kesirli** verir; G*Power ve motorumuz yukarı yuvarlar. Karşılaştırma: `n1 = ⌈n1*⌉`, `n2 = ⌈ratio·n1*⌉`. post-hoc güç 1e-6 içinde.

## G*Power (kâhin)

_Henüz vektör yok._

## statsmodels (ölçek, 600 vektör)

| Ölçüt | Sonuç |
|---|---|
| Tüm alanlar eşleşen vektör | 599/600 (%99.8) |
| a-priori N alanları tam eşleşen (kapı ≥ %90) | 299/300 (%99.7) |
| Açıklanmış uyuşmazlık | 1 |
| Açıklanmamış uyuşmazlık | 0 |

| Vektör | Mod | Girdi | Fark | Açıklama |
|---|---|---|---|---|
| S257 | a-priori | tails=2, d=1.297, alpha=0.001, power=0.953, ratio=1.0 | n1/n2: motor 33/33, ⌈statsmodels⌉ 32/32 (statsmodels n1 = 31.558154) | kâhin hatası: ⌈statsmodels⌉ = 32/32 ile güç 0.9523969 < hedef 0.953 (SciPy nct NaN, kök bulucu saptı) |

## Bulgular

- **Kesirli N ile tam sayı N farkı:** statsmodels'ın verdiği kesirli `n1*`, kâhin hatası olan satırlar dışında her a-priori vektöründe G*Power kuralıyla (her grup ayrı yukarı) yuvarlandığında motorun tam sayı sonucunu veriyor. Kütüphaneler "kaç denek" sorusunu yarım hastayla yanıtlıyor; G*Power ve motor yukarı yuvarlayıp gücü yeniden hesaplıyor (`actual_power`).
- **Kâhin de yanılabilir:** statsmodels'ın kök bulucusu, SciPy'nin merkezî olmayan t dağılımı NaN döndürdüğünde yanlış köke yakınsayabiliyor. Bu satırlarda statsmodels'ın önerdiği N hedef güce ulaşmıyor; motor doğru. Bunu kanıtlamak için önerilen N'yi post-hoc'a verip gücü ölçüyoruz.
