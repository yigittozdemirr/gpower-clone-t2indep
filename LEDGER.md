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

"GUI ✔" = G*Power 3.1.9.7 arayüzünden otomatik toplanan kâhin vektörleriyle (oracle/, ekran görüntüleriyle) diferansiyel olarak doğrulandı. Bu güçlü bir kanıttır ama **binary kanıtı değildir**; satır, Ghidra'da fonksiyon adresi ya da dize referansı bulunana kadar `[AJAN]` etiketinde kalır.

| # | İddia (güncel) | Etiket | Kanıt | Gereken `[REA]` kanıtı |
|---|---|---|---|---|
| H-01 | a-priori dağıtım: sürekli toplam `N*` **çift sayıya** yukarı yuvarlanır (`N = 2⌈N*/2⌉`); `n1 = ⌊N/(1+ratio) + 0.5⌋` (yarım yukarı), `n2 = N − n1` | `[AJAN]` GUI ✔ | **140/140** a-priori vektör (oracle V01–V42 + `oracle/gpower_random_apriori.jsonl`'daki 120 rastgele). Bankacı yuvarlaması 139/140 (V04: 58.5 → 59). İlk hipotez ("her grup ayrı yukarı", Fisher örneğinden) 68/140 ile **çürütüldü** (HALLUCINATIONS H-7). | Çözücüde `2*ceil(x/2)` ya da eşdeğeri; bölmede `floor(x+0.5)` |
| H-01b | Gerçekleşen güç hedefin **altında** kalabilir; G*Power düzeltmez | `[AJAN]` GUI ✔ | V07: 404/282, 0.8998856 < 0.90; V10: 663/33, 0.7994111 < 0.80 | Bölmeden sonra güç kontrolünün olmaması |
| H-02 | Arama `N > 2`'den başlar; en küçük sonuç N = 4; bir grup **1 ya da 0** olabilir | `[AJAN]` GUI ✔ | V19 (d 10): 2/2; V34: 3/1; V35: 1/3; **V36 (ratio 0.1, d 10): 4/0, ncp 0, güç 0.05** (G*Power'ın dejenere sonucu) | Çözücünün başlangıç değeri |
| H-03 | Üst sınır yok (en azından 5·10⁷'ye kadar) | `[AJAN]` GUI ✔ | V16 (d 0.001): 25 989 420 / 25 989 420. Bizim 1e7 sınırımız yanlıştı (HALLUCINATIONS H-8). | İterasyon üst sınırı sabiti |
| H-04 | `power < alpha` reddedilir; `power = alpha` kabul edilir | `[AJAN]` GUI ✔ | V20, V41: "Power must be greater than or equal to alpha." V21 → 2/2; V29 (sensitivity) → d = 0 | Dizenin binary'deki adresi ve onu çağıran karşılaştırma (`<` mı `<=` mi) |
| H-05 | İterasyonun durma koşulu (tolerans / adım) | `[AJAN]` | Doğrudan gözlenemiyor; 140/140 eşleşme toleransın N'yi değiştirecek kadar kaba olmadığını gösteriyor | Çözücü döngüsünün tolerans sabiti |
| H-06 | Oran kabul aralığı **[0.01, 100]** (uçlar dahil); post-hoc'ta n1 = 1 kabul | `[AJAN]` GUI ✔ | V32, V39, V40: "The allocation ratio falls outside the admissible range (0.01, 100)." V37 (0.01) ve V38 (100) hesaplanıyor. V33: n1 = 1 hesaplanıyor (biz CONTRACT §5 gereği reddediyoruz) | Dize adresi ve karşılaştırma sabitleri (0.01, 100) |
| H-07 | Çift kuyrukta criterion ve compromise α'yı iki kuyruğa bölerek çözer | `[AJAN]` GUI ✔ | V30, V31 7 basamakta eşleşiyor | Kritik değer çağrısında `α/2` |
| D-02 | Çift kuyrukta güç iki kuyruğun toplamı | `[DOK]` + GUI ✔ | V24: 0.0551613 (yalnız üst kuyruk 0.0402359 olurdu) | — |

Eski deney listesi ([rea/experiments.jsonl](rea/experiments.jsonl)) tarihsel kayıt olarak duruyor: E-01…E-06'daki iki hipotez (A ve B) de G*Power tarafından çürütüldü.

## C. Binary bulguları (REA + Ghidra)

_REA oturumu yeniden başlatıldıktan sonra doldurulacak. Her satır şu biçimde:_

```
[REA] R-xx · <iddia>
  Dize   : "<kısa dize>" @ 0x...........
  İşlev  : FUN_xxxxxxxx @ 0x........ (rolü: ...)
  Alıntı : <en fazla 1-2 satır, kısa>
  Sınama : <hangi deney/test bunu doğruluyor>
```

## D. Deneyler ve kâhin

- G*Power arayüzünden toplanan vektörler: [oracle/gpower_vectors.csv](oracle/gpower_vectors.csv) (42 vektör, her biri `oracle/screenshots/Vxx.png`), [oracle/gpower_random_apriori.jsonl](oracle/gpower_random_apriori.jsonl) (120 rastgele a-priori). Toplama aracı: [tools/gpower_gui_collect.py](tools/gpower_gui_collect.py) (Windows UI otomasyonu; G*Power'ın kendi alanlarını okur, fare kullanmaz).
- Karşılaştırma: `uv run pytest tests/test_differential.py`, rapor: [tests/AGREEMENT_REPORT.md](tests/AGREEMENT_REPORT.md).
