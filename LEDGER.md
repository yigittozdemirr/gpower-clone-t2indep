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

"GUI ✔" = G*Power 3.1.9.7 arayüzünden otomatik toplanan kâhin vektörleriyle (oracle/, ekran görüntüleriyle) diferansiyel olarak doğrulandı. Bu güçlü bir kanıttır ama **binary kanıtı değildir**; satır, Ghidra'da fonksiyon adresi ya da dize referansı bulunana kadar `[AJAN]` etiketinde kalır. **Güncel durum:** H-01…H-06 bölüm C'deki R-xx bulgularıyla `[REA]`'ya yükseldi; H-07 yalnızca GUI ile doğrulandı (`[AJAN]`).

| # | İddia (güncel) | Etiket | Kanıt | Gereken `[REA]` kanıtı |
|---|---|---|---|---|
| H-01 | a-priori dağıtım: sürekli toplam `N*` **çift sayıya** yukarı yuvarlanır (`N = 2⌈N*/2⌉`); `n1 = ⌊N/(1+ratio) + 0.5⌋` (yarım yukarı), `n2 = N − n1` | `[REA]` (R-06, R-07) + GUI ✔ | **140/140** a-priori vektör (oracle V01–V42 + `oracle/gpower_random_apriori.jsonl`'daki 120 rastgele). Bankacı yuvarlaması 139/140 (V04: 58.5 → 59). İlk hipotez ("her grup ayrı yukarı", Fisher örneğinden) 68/140 ile **çürütüldü** (HALLUCINATIONS H-7). | Çözücüde `2*ceil(x/2)` ya da eşdeğeri; bölmede `floor(x+0.5)` |
| H-01b | Gerçekleşen güç hedefin **altında** kalabilir; G*Power düzeltmez | `[REA]` (R-07) + GUI ✔ | V07: 404/282, 0.8998856 < 0.90; V10: 663/33, 0.7994111 < 0.80 | Bölmeden sonra güç kontrolünün olmaması |
| H-02 | Arama `N > 2`'den başlar; en küçük sonuç N = 4; bir grup **1 ya da 0** olabilir | `[REA]` (R-05, R-06) + GUI ✔ | V19 (d 10): 2/2; V34: 3/1; V35: 1/3; **V36 (ratio 0.1, d 10): 4/0, ncp 0, güç 0.05** (G*Power'ın dejenere sonucu) | Çözücünün başlangıç değeri |
| H-03 | Üst sınır yok (en azından 5·10⁷'ye kadar) | `[REA]` (R-05) + GUI ✔ | V16 (d 0.001): 25 989 420 / 25 989 420. Bizim 1e7 sınırımız yanlıştı (HALLUCINATIONS H-8). | İterasyon üst sınırı sabiti |
| H-04 | `power < alpha` reddedilir; `power = alpha` kabul edilir | `[REA]` (R-02) + GUI ✔ | V20, V41: "Power must be greater than or equal to alpha." V21 → 2/2; V29 (sensitivity) → d = 0 | Dizenin binary'deki adresi ve onu çağıran karşılaştırma (`<` mı `<=` mi) |
| H-05 | İterasyonun durma koşulu (tolerans / adım) | `[REA]` (R-04) | Doğrudan gözlenemiyor; 140/140 eşleşme toleransın N'yi değiştirecek kadar kaba olmadığını gösteriyor | Çözücü döngüsünün tolerans sabiti |
| H-06 | Oran kabul aralığı **[0.01, 100]** (uçlar dahil); post-hoc'ta n1 = 1 kabul | `[REA]` (R-01, R-08) + GUI ✔ | V32, V39, V40: "The allocation ratio falls outside the admissible range (0.01, 100)." V37 (0.01) ve V38 (100) hesaplanıyor. V33: n1 = 1 hesaplanıyor (biz CONTRACT §5 gereği reddediyoruz) | Dize adresi ve karşılaştırma sabitleri (0.01, 100) |
| H-07 | Çift kuyrukta criterion ve compromise α'yı iki kuyruğa bölerek çözer | `[AJAN]` GUI ✔ | V30, V31 7 basamakta eşleşiyor | Kritik değer çağrısında `α/2` |
| H-08 | **Çok büyük df'de (d ≤ 0.0001) G*Power'ın N'si minimal değil.** d = 0.0001: G*Power 2 598 942 504/grup, formül 2 598 941 820/grup yetiyor; d = 0.00001: G*Power kendi N'sinde güç 0.9500402 gösteriyor, formül 0.9500085 veriyor. | `[AJAN]` GUI ✔ + bağımsız sınama | V43, V44. Sınama motordan ve SciPy'den bağımsız: df > 10⁹'da t ≈ normal; yalnızca Python `statistics.NormalDist` ile G*Power'ın bir önceki çift toplamının hedefe ulaştığı gösteriliyor (`tests/differential.py`). Binary'de G*Power'ın büyük df'deki dağılım hesabı incelenmedi; motor bu hatayı **taklit etmez** (doğru hesabı korur). | — |
| D-02 | Çift kuyrukta güç iki kuyruğun toplamı | `[DOK]` + GUI ✔ | V24: 0.0551613 (yalnız üst kuyruk 0.0402359 olurdu) | — |

Eski deney listesi ([rea/experiments.jsonl](rea/experiments.jsonl)) tarihsel kayıt olarak duruyor: E-01…E-06'daki iki hipotez (A ve B) de G*Power tarafından çürütüldü.

## C. Binary bulguları (REA + Ghidra) `[REA]`

Araç: REA `rea-agents` 6.7.0, sağlayıcı Ghidra 12.1.4 (Evidence profili `3de5374f…`). Hedef: `GPowerNT.exe` SHA-256 `c63e6a13…c812`, x86 PE. Kanıt paketi (46 Evidence kaydı) repo dışında tutuluyor, çünkü decompile çıktısı içeriyor: `C:\Users\Casper\Tools\gpower-analysis\rea-evidence-bundle.json`. Aşağıda yalnızca adres, sabit ve kısa açıklama var.

| # | Bulgu | Kanıt (adres / dize / sabit) | Evidence ID | Diferansiyel sınama |
|---|---|---|---|---|
| R-01 | Oran kabul aralığı **[alt, 1/alt]**, uçlar dahil (`alt ≤ oran ≤ 1/alt`) | Doğrulayıcı `0x487300`; dize `0x5c679c` "The allocation ratio falls outside"; çağrı yerinde `alt = 0x3f847ae147ae147b` = **0.01** (`0x4ad72e`) → [0.01, 100] | `ev_6713205…`, `ev_baf0cbb…`, `ev_bed4d23…` | V32, V37–V40 |
| R-02 | **Güç ≥ α** kabul edilir, güç < α reddedilir (eşitlik geçerli) | `0x4880e0`: `if (alpha <= power) return 1;` aksi halde dize `0x5c6220` "Power must be greater than or equal to alpha." | `ev_a7e9b99…`, `ev_8abdb9a…` | V20, V21, V29, V41 |
| R-03 | t2-indep sınıfı: sanal tablo `0x5ca40c`, RTTI `0x5ef454`, ad `0x4d9a00` → "Means: Difference between two independent means (two groups)" (`0x5cb418`) | Sanal tablo baytları `0x5ca3e0–0x5ca540` | `ev_341c2a6…`, `ev_68976a7…`, `ev_ea7943d…` | — |
| R-04 | a-priori, toplam N'yi genel çözücüden alır (sanal `+0x48` = `0x496aa0`): kök bulucu **Brent** (`0x4f9bb0`), tolerans parametresi **1e-10**, en fazla **300 iterasyon**; ardından sınıfa özgü yuvarlama (`+0x74`) ve tam sayı N ile güç (`+0x30`) | `0x496aa0`: sabit `0x3ddb7cdfd9d7bdbb` (=1e-10), `300`; `0x4f9bb0` yakınsama `|b|·1.11e-16` | `ev_1562794…`, `ev_380ea12…` | 140/140 a-priori |
| R-05 | Arama aralığı **[3, 100]** ile başlar; güç 100'de yetmezse üst uç **×1.6** ile **sınırsız** büyütülür (üst sınır yok) | `0x4ac4c0` → `0x4962d0(3.0, 100.0)`; `0x4962d0`'da `hi *= 1.6` döngüsü | `ev_14ed4ff…`, `ev_19fde9c…` | V16, V43, V44 (N = 519 812 041 146) |
| R-06 | **Çift toplam:** `N = 2·f(N*/2)`, `f(x) = ceil( floor(x·10¹⁰ + 0.5) / 10¹⁰ )` | `0x4d64c0` (`x·0.5`, sonuç `+` kendisi), `0x496a20` (`1e10`, `floor`, `ceil`) | `ev_a9746fd…`, `ev_278014…` | 140/140 (hiçbir G*Power N'si tek değil) |
| R-07 | **Bölme:** `n1 = round(N/(oran+1), 0)` **yarım yukarı** (`floor(x·10^k + 0.5)/10^k`), `n2 = ceil(N − n1)`; `|oran − 1| < 1e-8` ve `n1 ≠ n2` ise küçük gruba +1 | a-priori kodu `0x4d9d23–0x4d9e01` (Ghidra bu bölgeyi fonksiyona bağlamadı; baytlar okunup yerelde disassemble edildi); sabitler `0x5c19a0` = 1.0, `0x5c4198` = 1e-8; yuvarlama `0x5727d0` | `ev_241b5b0…`, `ev_ee98cb7…`, `ev_baa8d10…`, `ev_3fa25c0…` | V04 (58.5 → 59), V07, V10 |
| R-08 | a-priori'de **|d| ≥ 0.00001** şartı (`1e-5 > |d|` ise hata) | `0x4d9260`: `comisd [0x5c7ed8], |d|`; sabit `0x5c7ed8` = `0x3ee4f8b588e368f1` (=1e-5); dize `0x5cb220` "effect size must be greater than 0.00001." | `ev_712e602…`, `ev_bcc9e9c…`, `ev_c151d3e…`, `ev_57f6c10…` | V44 (kabul), V45 (red) |

**Ne kanıtlandı, ne kanıtlanmadı:** R-01…R-08 statik analizdir; yürütme gözlenmedi. Yürütme tarafını G*Power arayüzünden toplanan 165 kâhin vektörü sınıyor (diferansiyel test). Merkezî olmayan t dağılımının G*Power'daki sayısal yöntemi incelenmedi; doğruluğu 7 basamaklı çıktılar üzerinden sınandı. R-07'deki kod bölgesi Ghidra'nın fonksiyon envanterinde yok (sanal tablodan çağrılan, sınırları tanınmamış kod); bu bir kapsama sınırıdır.

## D. Deneyler ve kâhin

- G*Power arayüzünden toplanan vektörler: [oracle/gpower_vectors.csv](oracle/gpower_vectors.csv) (42 vektör, her biri `oracle/screenshots/Vxx.png`), [oracle/gpower_random_apriori.jsonl](oracle/gpower_random_apriori.jsonl) (120 rastgele a-priori). Toplama aracı: [tools/gpower_gui_collect.py](tools/gpower_gui_collect.py) (Windows UI otomasyonu; G*Power'ın kendi alanlarını okur, fare kullanmaz).
- Karşılaştırma: `uv run pytest tests/test_differential.py`, rapor: [tests/AGREEMENT_REPORT.md](tests/AGREEMENT_REPORT.md).
