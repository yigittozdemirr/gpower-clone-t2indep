# LEDGER.md — Kanıt defteri (`t2-indep`)

**İncelenen:** G*Power 3.1.9.7 (Windows), `GPowerNT.exe`, SHA-256 `c63e6a133eb6372932f810c08cc33dc35a06d1ddb658f897bd6c34a754efc812`
**Aile:** t tests – Means: Difference between two independent means (two groups)
**Araçlar:** REA (`rea-agents` 6.7.0) + Ghidra 12.1.4 (JDK 21.0.11). G*Power yalnızca resmi sayfadan indirildi; exe repoda yok.

## Etiketler (ödev yönergesi)

| Etiket | Anlamı | Puan |
|---|---|---|
| `[DOK]` | Kılavuzda, makalede ya da eğitmenin yayımladığı belgelerde yazıyor | — |
| `[REA]` | Binary'den kanıtlandı: fonksiyon adresi ya da dize referansıyla | ✔ |
| `[AJAN]` | Ajanın çıkarımı; binary kanıtı yok. Diferansiyel testle sınanmalı | — |

Her satır: **iddia → kanıt → nasıl sınandı**. `[AJAN]` satırı binary kanıtı bulunduğunda `[REA]`'ya yükselir, çürütülürse SPEC düzeltilir ve HALLUCINATIONS.md'ye yazılır. Decompile çıktısı buraya kopyalanmaz; yalnızca kısa alıntı ve adres.

---

## A. Formül ve temel davranış

| # | İddia | Etiket | Kanıt | Sınama |
|---|---|---|---|---|
| D-01 | `df = n1 + n2 − 2`, `δ = d·√(n1n2/(n1+n2))`, `tc = t⁻¹(1 − α/tails; df)`, güç = merkezî olmayan t'nin `tc` ötesindeki kütlesi | `[DOK]` | Faul ve ark. (2007); G*Power 3.1 kılavuzu, iki bağımsız ortalama bölümü | CONTRACT §9'daki 5 vektör 5e-8 içinde (`tests/test_public_vectors.py`) |
| D-02 | Çift kuyrukta güç **iki kuyruğun toplamıdır** (`1 − F(tc) + F(−tc)`) | `[DOK]` + `[AJAN]` | Ödev ek dokümanı örneği: 2 kuyruk, d 0.5, güç .95 → 105/105, güç 0.9501, critical 1.9714, ncp 3.6228; motorumuz birebir üretiyor. Yalnız üst kuyruk sayılsa fark 4. basamakta görünmez, bu yüzden ayırt edici deney E-09 tanımlı. | E-09 (d 0.1, n 10/10: iki kuyruk 0.0551613, tek kuyruk 0.0402359) |
| D-03 | a-priori'de N **yukarı yuvarlanır**, `actual_power` tam sayı N ile yeniden hesaplanır | `[DOK]` | Kılavuz: "Actual power" alanı; ödev ek dokümanı c) notu | `tests/test_differential.py` (statsmodels kesirli N → ⌈N⌉) |

## B. Kılavuzda OLMAYAN davranış (asıl hedef)

| # | İddia | Etiket | Bugünkü kanıt | Gereken `[REA]` kanıtı | Ayırt edici deney |
|---|---|---|---|---|---|
| H-01 | Eşit olmayan oranda **her grup ayrı yuvarlanır**: sürekli `n1*` için `n1 = ⌈n1*⌉`, `n2 = ⌈ratio·n1*⌉` (n2, n1'in tam katı olmayabilir) | `[AJAN]` | Kılavuzda başka bir testin (Fisher exact) örneği: ratio 2 → N = 443 (148 ve 295); 2·148 = 296 ≠ 295 `[DOK]`. t testi için doğrudan kanıt yok. | a-priori çözücü fonksiyonunda n1 ve n2'nin ayrı tavan (ceil) çağrısı; `Allocation ratio N2/N1` dizesine referans veren kod | E-01…E-06, oracle V04–V12 |
| H-02 | Arama alt sınırı: her grup en az 2 (`n1 ≥ max(2, 2/ratio)`) | `[AJAN]` | Yok | Çözücünün başlangıç değeri / alt sınır sabiti | E-07, E-08, V18, V19 |
| H-03 | Çok küçük etkide üst sınır: `n1* > 1e7` → çözüm yok | `[AJAN]` | Yok (sınır değeri tamamen tahmin) | İterasyon üst sınırı sabiti ve hata dizesi | E-11, V16 |
| H-04 | `power ≤ alpha` reddedilir | `[AJAN]` | CONTRACT §2.4 hata örneği aynı mesajı gösteriyor `[DOK]`; G*Power'ın tepkisi bilinmiyor | Hata/uyarı dizesi ve onu üreten karşılaştırma | E-12, E-13, V20, V21, V29 |
| H-05 | İterasyonun durma koşulu (tolerans / adım) | `[AJAN]` | Motorumuz Brent, xtol 1e-10 | Çözücü döngüsünün tolerans sabiti | Yuvarlama sınırına çok yakın `n1*` olan vektörler |
| H-06 | Geçersiz girdiye tepki (ratio 0, n1 = 1, α ≥ 1) | `[AJAN]` | CONTRACT §5 aralıkları `[DOK]` | Girdi doğrulama dizeleri | V32, V33 |
| H-07 | Çift kuyrukta criterion ve compromise α'yı iki kuyruğa bölerek çözer | `[AJAN]` | Açık vektörler yalnızca tek kuyruk | Kritik değer çağrısında `α/2` | E-15, E-16, V30, V31 |

## C. Binary bulguları (REA + Ghidra)

_REA oturumu yeniden başlatıldıktan sonra doldurulacak. Her satır şu biçimde:_

```
[REA] R-xx · <iddia>
  Dize   : "<kısa dize>" @ 0x...........
  İşlev  : FUN_xxxxxxxx @ 0x........ (rolü: ...)
  Alıntı : <en fazla 1-2 satır, kısa>
  Sınama : <hangi deney/test bunu doğruluyor>
```

## D. Deneyler

Girdiler ve iki rakip hipotezin tahminleri: [rea/experiments.jsonl](rea/experiments.jsonl). G*Power arayüzünden toplanan sonuçlar: [oracle/](oracle/). Karşılaştırma: `uv run python rea/check_observations.py` ve `uv run pytest tests/test_differential.py`.

| Deney | Girdi | Hipotez B (SPEC) | Rakip hipotez A |
|---|---|---|---|
| E-01 | 1 kuyruk, d 0.5, α .05, güç .95, ratio 3 | 59 / 175 | 59 / 177 |
| E-02 | 2 kuyruk, d 0.5, α .05, güç .80, ratio 1.5 | 54 / 80 | 53 / 80 |
| E-03 | 2 kuyruk, d 0.8, α .05, güç .80, ratio 0.25 | 63 / 16 | 61 / 16 |
| E-04 | 2 kuyruk, d 0.3, α .01, güç .90, ratio 0.7 | 404 / 283 | 403 / 283 |
| E-05 | 2 kuyruk, d 0.5, α .05, güç .80, ratio 2 | 48 / 96 | 48 / 96 |
| E-06 | 1 kuyruk, d 0.5, α .05, güç .95, ratio 0.5 | 131 / 66 | 131 / 66 |
| E-14 | 2 kuyruk, d 0.5, α .05, güç .80, ratio 0.05 | 662 / 34 | 661 / 34 |

Hipotez A: en küçük tam sayı `n1` aranır, `n2 = ⌈ratio·n1⌉`.
