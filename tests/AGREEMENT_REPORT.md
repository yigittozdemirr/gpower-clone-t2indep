# Uyum raporu (diferansiyel test)

Üretildi: 2026-10-23 · `uv run python tools/differential_report.py`

Aynı girdiler hem kâhine hem motora verildi. Fark varsa ya bizim hatamızdır ya kaçırdığımız bir kuraldır ya da kâhinin kendi hatasıdır; her uyuşmazlık aşağıda sınıflandırılır.

- **G*Power:** `oracle/gpower_vectors.csv` (45 vektör, her satır `oracle/screenshots/` altında bir ekran görüntüsüne dayanır) ve `oracle/gpower_random_apriori.jsonl` (120 rastgele a-priori; arayüzden aynı araçla okundu). Ondalıklar G*Power'ın gösterdiği basamağa kadar, tam sayılar birebir karşılaştırılır.
- **statsmodels 0.15 (`TTestIndPower`):** bağımsız bir kütüphane. a-priori'de N'yi **kesirli** verir; G*Power ve motorumuz toplamı çift sayıya yukarı yuvarlayıp yarım yukarı böler (LEDGER R-06, R-07). Karşılaştırma: statsmodels'ın sürekli `N*`'ı bu kuralla yuvarlanır. post-hoc güç 1e-6 içinde.

## G*Power (kâhin, 165 vektör)

| Ölçüt | Sonuç |
|---|---|
| Tüm alanlar eşleşen vektör | 162/165 (%98.2) |
| a-priori N alanları tam eşleşen (kapı ≥ %90) | 147/149 (%98.7) |
| Açıklanmış uyuşmazlık | 3 |
| Açıklanmamış uyuşmazlık | 0 |

| Vektör | Mod | Girdi | Fark | Açıklama |
|---|---|---|---|---|
| V33 | post-hoc | tails=2, d=0.5, alpha=0.05, n1=1, n2=10 | motor hata verdi (OUT_OF_RANGE); G*Power sonuç üretti | sözleşme önceliği: CONTRACT §5 n1, n2 ≥ 2 der; G*Power n = 1'i kabul ediyor |
| V43 | a-priori | tails=2, d=0.0001, alpha=0.05, power=0.95, ratio=1.0 | ncp: motor 3.6048175, G*Power 3.6048180; df: motor 5197883638, G*Power 5197885006; n1: motor 2598941820, G*Power 2598942504; n2: motor 2598941820, G*Power 2598942504; n_total: motor 5197883640, G*Power 5197885008 | kâhin sayısal hatası: G*Power N = 5197885008, ama bir önceki çift toplam (5197885006) bağımsız normal yaklaşımla güç 0.9500000489 > hedef 0.95 veriyor (df 5.20e+09); G*Power'ın N'si minimal değil |
| V44 | a-priori | tails=2, d=1e-05, alpha=0.05, power=0.95, ratio=1.0 | ncp: motor 3.6048175, G*Power 3.6048996; df: motor 519788363788, G*Power 519812041144; n1: motor 259894181895, G*Power 259906020573; n2: motor 259894181895, G*Power 259906020573; n_total: motor 519788363790, G*Power 519812041146; actual_power: motor 0.9500000, G*Power 0.9500402 | kâhin sayısal hatası: G*Power kendi N'sinde (259906020573/259906020573) güç 0.9500402 gösteriyor, formül 0.9500085 veriyor (df 5.20e+11) |

## statsmodels (ölçek, 600 vektör)

| Ölçüt | Sonuç |
|---|---|
| Tüm alanlar eşleşen vektör | 599/600 (%99.8) |
| a-priori N alanları tam eşleşen (kapı ≥ %90) | 299/300 (%99.7) |
| Açıklanmış uyuşmazlık | 1 |
| Açıklanmamış uyuşmazlık | 0 |

| Vektör | Mod | Girdi | Fark | Açıklama |
|---|---|---|---|---|
| S257 | a-priori | tails=2, d=1.297, alpha=0.001, power=0.953, ratio=1.0 | n1/n2: motor 33/33, G*Power kuralıyla statsmodels 32/32 (statsmodels n1* = 31.558154) | kâhin hatası: statsmodels'ın kökünde (N* = 63.1163) güç 0.9485498, hedef 0.953 değil (SciPy nct NaN, kök bulucu saptı) |

## Bulgular

- **Kesirli N ile tam sayı N farkı:** statsmodels'ın verdiği kesirli `n1*`, kâhin hatası olan satırlar dışında her a-priori vektöründe G*Power kuralıyla (çift toplam, yarım yukarı bölme) yuvarlandığında motorun tam sayı sonucunu veriyor. Kütüphaneler "kaç denek" sorusunu yarım hastayla yanıtlıyor; G*Power ve motor yukarı yuvarlayıp gücü yeniden hesaplıyor (`actual_power`).
- **Kâhin de yanılabilir:** statsmodels'ın kök bulucusu, SciPy'nin merkezî olmayan t dağılımı NaN döndürdüğünde yanlış köke yakınsayabiliyor. Bu satırlarda statsmodels'ın önerdiği N hedef güce ulaşmıyor; motor doğru. Bunu kanıtlamak için önerilen N'yi post-hoc'a verip gücü ölçüyoruz.
