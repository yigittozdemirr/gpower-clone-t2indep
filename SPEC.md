# SPEC.md — `t2-indep` temiz oda belirtimi

**Aile:** `t2-indep` · K1 · t tests – Means: Difference between two independent means (two groups)
**Klinik örnek:** İlaç ve plasebo grubu
**Sözleşme:** [CONTRACT.md](CONTRACT.md) sürüm 1.0.0
**Bu belgeyi yazan:** İnceleme (REA) oturumu. **Bu belgeyi okuyan:** Yazım oturumu (yalnızca SPEC.md + CONTRACT.md görür).

Bu belge yayımlanmış yöntemlerden (Cohen 1988; Faul, Erdfelder, Lang & Buchner 2007), G*Power kılavuzundan, G*Power'ın gözlenen davranışından ve binary incelemesinin bulgularından (yalnızca soyut kural olarak, kod olarak değil) üretilmiştir. Her kuralın yanında kanıt etiketi vardır; ayrıntısı [LEDGER.md](LEDGER.md)'de:

- `[DOK]` — kılavuz, makale, CONTRACT.md ya da eğitmen belgesi
- `[REA]` — binary'den fonksiyon adresi ya da dize referansıyla kanıtlandı
- `[AJAN]` — kanıtı henüz olmayan çıkarım; ayırt edici deneyi LEDGER'da tanımlı

Kabul kriterleri Gherkin biçiminde Bölüm 9'dadır.

---

## 1. Matematik `[DOK]`

Girdi: kuyruk sayısı `tails` ∈ {1, 2}, etki büyüklüğü `d` (Cohen d), `alpha`, grup büyüklükleri `n1`, `n2`.

```
df   = n1 + n2 − 2
ncp  = d · sqrt(n1 · n2 / (n1 + n2))          (δ, merkezî olmama parametresi)
tc   = t⁻¹(1 − alpha / tails ; df)              (merkezî t dağılımının üst kantili; Critical t)

tails = 1:  power = 1 − F_nct(tc ; df, ncp)
tails = 2:  power = 1 − F_nct(tc ; df, ncp) + F_nct(−tc ; df, ncp)
```

`F_nct` merkezî olmayan t dağılımının birikimli dağılım fonksiyonudur. Çift kuyrukta **iki kuyruğun katkısı da** güce eklenir.

Bu formüller açık vektörlerin beşini de 1e-9'dan küçük farkla tutturuyor (bkz. kanıt defteri R-01).

### 1.1 Sayısal gereksinimler

- **Çalışma zamanında yalnızca standart kütüphane** kullanılır. Gerekçe bir G*Power davranışı değil, ölçümdür: bu makinede `import scipy.stats` tek başına ~2.1 s sürüyor, sözleşme her çağrı için 2 s sınırı koyuyor (CONTRACT §2.1). Python'un kendi açılışı ~0.09 s.
- Gerekli sayısal yapı taşları (motorun içinde yazılır):
  1. `log Γ` (`math.lgamma` kullanılabilir).
  2. Düzenlenmiş tamamlanmamış beta fonksiyonu `I_x(a, b)` — sürekli kesir (Lentz yöntemi) ile; `x > (a+1)/(a+b+2)` ise simetri `I_x(a,b) = 1 − I_{1−x}(b,a)` kullanılır.
  3. Merkezî t CDF: `F_t(t; ν) = 1 − ½ I_{ν/(ν+t²)}(ν/2, ½)` (t ≥ 0), simetri ile t < 0.
  4. Merkezî t ters CDF: Newton + ikiye bölme güvenceli kök bulma; göreli hata ≤ 1e-13.
  5. Merkezî olmayan t CDF: Lenth (1989) AS 243 algoritması (Poisson ağırlıklı beta serisi, hem ileri hem geri yönde toplanır), hata eşiği ≤ 1e-13. Çok büyük `ncp` (≈ 37'nin üstü) veya seri yakınsamadığında sağlam bir geri dönüş gerekir (ör. `ncp` çok büyükse güç 1'e, gücün küçük tarafındaki kuyruk 0'a sıkıştırılır; normal yaklaşım yalnızca 1e-12'den küçük olasılıklar için kabul edilir).
- **Doğruluk hedefi:** Her çıktı ondalığı bağımsız bir kâhine (SciPy `stats.t`, `stats.nct`; yalnızca test bağımlılığı) karşı mutlak ≤ 1e-9. Sözleşme toleransı 1e-6; 1000 kat pay bırakıyoruz.
- Sürekli `df` (tam sayı olmayan) desteklenmelidir; a-priori çözümü sürekli toplam `N` üzerinde çalışır (Bölüm 3.1).

---

## 2. Doğrulama (girdi kontrolü)

Kontrol sırası sabittir; ilk hatada durulur `[DOK: CONTRACT]` + takım kararı:

1. `--version` tek başına verilirse sürüm JSON'u.
2. `test` ya da `mode` eksik → `MISSING_PARAM` (field: `test`/`mode`).
3. `test` ≠ `t2-indep` ya da `mode` bilinmiyor → `UNSUPPORTED` (field: `test`/`mode`). Diğer aileler bu takımın kapsamında değildir.
4. Aynı alan iki kez verilmiş → `INVALID_VALUE`.
5. Moda ait olmayan alan (tanınmayan ya da ilgisiz) → `UNKNOWN_PARAM` (alan sırasıyla ilk bulunan).
6. Modun gerektirdiği alan eksik → `MISSING_PARAM` (Bölüm 4 tablosundaki sırayla ilk eksik).
7. Tür: ondalık alanlar sonlu bir sayı olmalı (`nan`, `inf`, `0,05`, boş metin → `INVALID_VALUE`). Tam sayı alanları (`tails`, `n1`, `n2`) yalnızca tam sayı yazımı kabul eder: `88` evet; `88.5`, `88.0`, `1e2` → `INVALID_VALUE`. MCP'den gelen JSON değerinde `88` (int) kabul, `88.5` (float) → `INVALID_VALUE`; `true/false` → `INVALID_VALUE`.
8. Aralık (CONTRACT §5) → `OUT_OF_RANGE`: `tails` ∈ {1,2}; `0 < alpha < 1`; `0 < power < 1`; `beta_alpha_ratio > 0`; `d > 0`; `ratio > 0`; `n1, n2 ≥ 2`.
   - Ek olarak `ratio` **0.01 ≤ ratio ≤ 100** olmalı (uçlar dahil); dışındaysa `OUT_OF_RANGE`, field `ratio`, mesaj "Allocation ratio kabul edilebilir aralığın (0.01, 100) dışında". `[AJAN, G*Power arayüzüyle doğrulandı: oracle V32, V37–V40 — 0.01 ve 100 kabul, 0, 0.009 ve 100.5 için G*Power "The allocation ratio falls outside the admissible range (0.01, 100)." diyor]`
   - Not: G*Power post-hoc'ta `n1 = 1`'i kabul ediyor (oracle V33), ama CONTRACT §5 `n1, n2 ≥ 2` diyor; **sözleşme önceliklidir**, `OUT_OF_RANGE`.
   - Yalnızca `a-priori` modunda: `d < 0.00001` ise `OUT_OF_RANGE`, field `d`, mesaj "A-priori analizde etki büyüklüğü 0.00001'den küçük olamaz". `d = 0.00001` **kabul edilir**. `[REA: 0x4d9260'ta `1e-5 > |d|` karşılaştırması, sabit 0x5c7ed8 = 1e-5, dize 0x5cb220 "…effect size must be greater than 0.00001."; GUI: d 1e-10 reddedildi, d 1e-5 hesaplandı]`
9. Tutarlılık → `INCONSISTENT`:
   - `a-priori` ve `sensitivity`: `power < alpha` (**kesin küçük**) ise hata, field `power`, mesaj "Power, alpha değerinden büyük olmalı". `power = alpha` hata **değildir**. `[AJAN, G*Power arayüzüyle doğrulandı: oracle V20, V41 → "Power must be greater than or equal to alpha."; V21, V29 → eşitlikte sonuç üretiyor]`
10. Hesap çözüm üretemezse → `NO_SOLUTION` (Bölüm 3'teki sınırlar).

Çıkış kodları `[DOK: CONTRACT]`: başarı `0`; adım 2–9 hataları `2`; `NO_SOLUTION` ve beklenmeyen istisnalar `1` (beklenmeyen istisna `code: "INTERNAL"`).

Hata JSON'u: `{"error": "<insan için açıklama>", "code": "<KOD>", "field": "<alan ya da null>"}`.

---

## 3. Modlar

Her modun girdi/çıktı alanları CONTRACT §4.1'deki tablodadır. Aşağıda yalnızca **davranış** var. Tüm çıktılarda `df` tam sayıdır; `critical_t` her zaman pozitif üst kritik değerdir (çift kuyrukta `t⁻¹(1 − alpha/2)`).

### 3.1 `a-priori` — gerekli örneklem

Girdi: `tails, d, alpha, power, ratio` (`ratio` = N2/N1).

**Dağıtım kuralı — "çift toplam, yuvarlanarak bölünür"** `[REA: LEDGER R-03…R-07]` `[GUI: 140/140 a-priori vektör (oracle V01–V42 + 120 rastgele)]`:

1. Toplam `N` **sürekli** bir değişken kabul edilir; gruplar sürekli olarak `n1 = N/(1+ratio)`, `n2 = ratio·N/(1+ratio)`, `df = N − 2`.
2. `power(N) = hedef power` denkleminin kökü `N*` bulunur (güç N'de monoton artan). G*Power arama aralığını [3, 100] ile başlatır, gerekirse üst ucu 1.6 ile çarparak sınırsız genişletir, sonra Brent yöntemiyle (makine hassasiyetine kadar, en fazla 300 iterasyon) kökü bulur. `[REA: 0x4ac4c0 → 0x4962d0, 0x4f9bb0]`
3. Toplam **çift sayıya** yukarı yuvarlanır, önce 10 basamağa yuvarlanarak: `x = N*/2`, `N = 2·⌈⌊x·10¹⁰ + 0.5⌋ / 10¹⁰⌉`. `[REA: 0x4d64c0 = 2·f(N*/2), f = 0x496a20]` Kök 3'ün altındaysa (güç zaten N = 3'te hedefe ulaşıyorsa) `N = 4`. Sonuç hiçbir zaman 4'ten küçük olmaz.
4. Bölme: `n1 = ⌊N/(1+ratio) + 0.5⌋` (**yarım yukarı** yuvarlama; bankacı yuvarlaması DEĞİL: ratio = 3, N = 234 → 58.5 → **59**), `n2 = ⌈N − n1⌉ = N − n1`. `[REA: 0x4d9d53 → 0x5727d0 (floor(x·10^k + 0.5)/10^k, k = 0); 0x4d9d86 ceil]`
4b. `|ratio − 1| < 1e-8` iken `n1 ≠ n2` ise küçük gruba 1 eklenir `[REA: 0x4d9dc5–0x4d9e01, sabit 0x5c4198 = 1e-8]`. N çift olduğu için bu adım pratikte hiçbir şeyi değiştirmez; yine de uygulanır.
5. `ncp`, `critical_t`, `df` ve `actual_power` bu **tam sayı** `n1, n2` ile yeniden hesaplanır. `n_total = N`.
6. **Sonuç hedefin altında kalabilir.** Bölme yuvarlaması yüzünden `actual_power < power` olabilir; G*Power bunu düzeltmez ve biz de düzeltmeyiz (oracle V07: 404/282, 0.8998856 < 0.90; V10: 663/33, 0.7994111 < 0.80).
7. **Dejenere sonuç.** Çok büyük etki ve küçük oranda bir grup 1 ya da 0 olabilir (oracle V34: 3/1; V35: 1/3; V36: ratio 0.1, d 10 → **4/0**, ncp 0, df 2, güç = alpha). G*Power bunu üretiyor; biz de aynısını üretiriz. `n1` ya da `n2` 2'den küçükse çıktıya fazladan bir `warning` alanı (metin) eklenir: "Gruplardan biri 2'den küçük; sonuç G*Power ile uyum için üretildi, klinik olarak kullanılamaz." `n2 = 0` iken `ncp = 0` (formüldeki `n1·n2/(n1+n2)` sıfır), `df = n1 − 2`.

Örnekler (G*Power arayüzünden, oracle/gpower_vectors.csv):

| Girdi | N* | N | n1 / n2 |
|---|---|---|---|
| 1 kuyruk, d .5, α .05, güç .95, ratio 1 | 174.53 | 176 | 88 / 88 |
| 1 kuyruk, d .5, α .05, güç .95, ratio 3 | 232.24 | 234 | 59 / 175 |
| 2 kuyruk, d .8, α .05, güç .80, ratio 0.25 | 78.62 | 80 | 64 / 16 |
| 2 kuyruk, d .3, α .01, güç .90, ratio 0.7 | 685.89 | 686 | 404 / 282 |
| 2 kuyruk, d .5, α .05, güç .80, ratio 0.05 | 694.20 | 696 | 663 / 33 |

**Kök arama (bizim uygulamamız; sonuç G*Power'ınkiyle aynı):**
- `power(N = 4) ≥ hedef` ise `N = 4` (kök ≤ 4 ise çift yuvarlama da 4 verir). Böylece df → 0 bölgesindeki sayısal sorunlardan kaçınılır.
- Aksi halde `N = 4`'ten başlayıp katlayarak `power ≥ hedef` olan ilk üst uç; sonra Brent, mutlak tolerans 1e-12 ve göreli 1e-15 (G*Power makine hassasiyetine kadar iniyor; adım 3'teki 10 basamak yuvarlaması için kökün en az bu kadar hassas olması gerekir).
- **Üst sınır yok** `[REA: 0x4962d0 aralığı 1.6 çarpanıyla sınırsız genişletir]`. G*Power d = 0.001 için 25 989 420 / 25 989 420, d = 0.0001 için 2 598 942 504 / 2 598 942 504, d = 0.00001 için 259 906 020 573 / 259 906 020 573 hesaplıyor (oracle V16, V43, V44). a-priori'de `NO_SOLUTION` yalnızca sayısal taşma (sonsuz/NaN) olursa döner.

### 3.2 `post-hoc` — ulaşılan güç

Girdi: `tails, d, alpha, n1, n2`. Bölüm 1 formülleri doğrudan uygulanır. Çıktı: `ncp, critical_t, df, power`.

### 3.3 `compromise` — α ve gücü β/α oranına göre bul

Girdi: `tails, d, beta_alpha_ratio (q), n1, n2`.
`β(α) = 1 − power(α)` olmak üzere `β(α) = q · α` denkleminin `α ∈ (0, 1)` kökü bulunur (`β(α) − qα` α'da kesin azalan, tek kök). Çıktı: `ncp, critical_t (bu α ile), df, alpha, beta, power`. Kök toleransı: α'da mutlak 1e-14, göreli 1e-12.

Açık vektör: `q=1, d=0.5, n1=n2=88, tails=1` → `alpha = beta = 0.0492887`, `critical_t = 1.6606859`, `power = 0.9507113`.

### 3.4 `criterion` — gerekli α

Girdi: `tails, d, power, n1, n2`. `power(α) = hedef` denkleminin `α ∈ (0, 1)` kökü (güç α'da monoton artan). Çıktı: `ncp, critical_t, df, alpha`. Kök α → 0'da ya da α → 1'de sınır dışı kalırsa `NO_SOLUTION`.

Açık vektör: `power=0.95, d=0.5, n1=n2=88, tails=1` → `alpha = 0.0485965`, `critical_t = 1.6676050`.

### 3.5 `sensitivity` — saptanabilir en küçük etki

Girdi: `tails, alpha, power, n1, n2`. `power(d) = hedef` denkleminin **d ≥ 0** kökü `[DOK: CONTRACT]` (G*Power yalnızca pozitif yönü hesaplar). Arama aralığı `d ∈ [0, 1000]`; bulunamazsa `NO_SOLUTION`. Çıktı: `ncp` (bulunan d ile), `critical_t`, `df`, `d`.
`power = alpha` iken (çift kuyrukta d = 0'da güç tam alpha'dır) sonuç `d = 0`, `ncp = 0` `[AJAN, G*Power arayüzüyle doğrulandı: oracle V29]`. `power < alpha` → `INCONSISTENT` (Bölüm 2).

Açık vektör: `alpha=0.05, power=0.95, n1=n2=88, tails=1` → `d = 0.4978840`, `ncp = 3.3025887`.

---

## 4. Alan sırası (eksik/ilgisiz alan raporlaması için)

| Mod | Zorunlu alanlar (bu sırayla) |
|---|---|
| `a-priori` | `tails, d, alpha, power, ratio` |
| `post-hoc` | `tails, d, alpha, n1, n2` |
| `compromise` | `tails, d, beta_alpha_ratio, n1, n2` |
| `criterion` | `tails, d, power, n1, n2` |
| `sensitivity` | `tails, alpha, power, n1, n2` |

Çıktı alanları (fazladan alan yazılmaz; düzenek yok sayar ama ajan okurken sade kalsın):

| Mod | Çıktı (bu sırayla) |
|---|---|
| `a-priori` | `ncp, critical_t, df, n1, n2, n_total, actual_power` |
| `post-hoc` | `ncp, critical_t, df, power` |
| `compromise` | `ncp, critical_t, df, alpha, beta, power` |
| `criterion` | `ncp, critical_t, df, alpha` |
| `sensitivity` | `ncp, critical_t, df, d` |

---

## 5. Mimari `[DOK: CONTRACT §7, ödev kuralı 3]`

```
gpower_clone/
  numerics.py   # özel fonksiyonlar (beta, t, nct, kök bulma) — saf stdlib
  engine.py     # TEK hesap motoru: doğrulama + 5 mod. run(params: dict) -> (dict, exit_code)
  cli.py        # argv -> dict -> engine.run -> stdout JSON
  mcp_server.py # power_analysis aracı -> engine.run -> aynı JSON metni
  agent.py      # doğal dil -> Claude -> MCP aracı (hesap yapmaz)
```

- `engine.run` hem CLI'nin metin değerlerini (`"0.05"`) hem MCP'nin JSON değerlerini (`0.05`) kabul eder; doğrulama tek yerdedir.
- JSON çıktısı: `json.dumps(obj, ensure_ascii=True, separators=(", ", ": "))`, tek satır. Ondalıklar Python `float` `repr`'i ile (tam double, yuvarlama yok); tam sayılar `int`. `ensure_ascii=True` Windows konsol kodlamasından bağımsızlık için.
- `--version` → `{"contract_version": "1.0.0", "name": "<takım-adı>", "engine": "Python <sürüm> (stdlib)"}`.
- Ondalık ayrıştırma `float()` ile yapılır (yerel ayardan bağımsız); `,` içeren değer hata.
- stdout'a JSON dışında hiçbir şey yazılmaz.

## 6. MCP `[DOK: CONTRACT §7]`

- Tek araç `power_analysis`; girdi şeması CLI alan adlarıyla aynı (`test`, `mode` zorunlu; diğerleri isteğe bağlı olarak tanımlı, zorunluluğu motor denetler). Şema türleri gevşek tutulur (sayı ya da metin) ki hata davranışı CLI ile aynı kalsın.
- Çıktı: CLI'nin stdout satırıyla **bayt bayt aynı** metin (`TextContent`). Hata da aynı JSON.
- Eşdeğerlik testi: CONTRACT §9'daki 25 vektörün her biri için CLI (alt süreç) çıktısı == MCP (gerçek stdio istemcisi) çıktısı.

## 7. Ajan `[DOK: CONTRACT §8, §10]`

- Claude modeli + MCP istemcisi (stdio) ile `power_analysis` aracını çağırır; **sayıyı asla kendisi hesaplamaz**, yalnızca aracın döndürdüğünü aktarır.
- Her araç çağrısı `logs/agent_calls.jsonl`'a bir satır: `ts` (yerel saat, ofsetli ISO 8601), `question`, `tool_input`, `tool_output` (ayrıştırılmış JSON), `tokens_in`, `tokens_out` (o araç çağrısını üreten model yanıtının `usage` değerleri).
- Sistem istemi kuralları: "küçük/orta/büyük etki" bir kategoridir; ajan değeri (0.2/0.5/0.8) seçerse bunu **açıkça söyler**. Yön iddiası yoksa çift kuyruk, "daha iyi/daha az" gibi yön varsa tek kuyruk önerir ve bunu söyler. Eksik bilgi varsa önce sorar. Yalnızca kurgusal senaryolar.

## 8. Değişmezler (özellik testleri için)

- `post-hoc(a-priori sonucu n1,n2)` gücü = a-priori `actual_power` (bayt bayt aynı). **`actual_power ≥ hedef` bir değişmez DEĞİLDİR** (bölme yuvarlaması; §3.1 madde 6).
- `a-priori`: `n_total` her zaman çift ve ≥ 4; `n1 = ⌊n_total/(1+ratio) + 0.5⌋`, `n2 = n_total − n1`.
- `a-priori` minimallik: sürekli yolda `power(N = n_total − 2) < hedef` (n_total > 4 iken); yani bir önceki çift toplam, sürekli bölmeyle hedefe ulaşmaz. (İlk iki sürüm yanlıştı; bkz. HALLUCINATIONS.md H-3, H-7.)
- `ratio = 1` iken `n1 = n2`.
- `criterion` çıktısındaki α ile `post-hoc` → hedef güç (≤ 1e-9).
- `sensitivity` çıktısındaki d ile `post-hoc` → hedef güç.
- `compromise`: `beta / alpha = q` (göreli ≤ 1e-9) ve `power = 1 − beta`.
- Güç: d'de, n'de ve α'da monoton artan; tek kuyruk gücü ≥ çift kuyruk gücü (d > 0).
- Aynı girdi → aynı bayt dizisi (deterministik).

---

## 9. Kabul kriterleri (Gherkin)

Aşağıdaki `gherkin` bloklarındaki **Örnekler** tabloları `tests/test_spec_gherkin.py` tarafından doğrudan okunup CLI üzerinden çalıştırılır. Belge ile test ayrışamaz: bir satır değişirse test de değişir. `beklenen` sütunu, çıktıda bulunması gereken alanların JSON alt kümesidir; ondalıklar G*Power'ın 7 basamağına göre karşılaştırılır (|fark| ≤ 1e-6), tam sayılar birebir.

```gherkin
# language: tr
Özellik: G*Power ile aynı hesap (açık vektörler)  [DOK]
  Senaryo taslağı: Beş mod, tek kuyruk, d = 0.5
    Diyelim ki motor "t2-indep" testi için çağrılıyor
    Eğer ki "<argümanlar>" ile çalıştırırsam
    O zaman çıkış kodu 0 olmalı
    Ve çıktı "<beklenen>" alanlarını içermeli

    Örnekler:
      | argümanlar | beklenen |
      | --mode a-priori --tails 1 --d 0.5 --alpha 0.05 --power 0.95 --ratio 1 | {"ncp": 3.3166248, "critical_t": 1.6536580, "df": 174, "n1": 88, "n2": 88, "n_total": 176, "actual_power": 0.9514254} |
      | --mode post-hoc --tails 1 --d 0.5 --alpha 0.05 --n1 88 --n2 88 | {"ncp": 3.3166248, "critical_t": 1.6536580, "df": 174, "power": 0.9514254} |
      | --mode compromise --tails 1 --d 0.5 --beta_alpha_ratio 1 --n1 88 --n2 88 | {"critical_t": 1.6606859, "alpha": 0.0492887, "beta": 0.0492887, "power": 0.9507113} |
      | --mode criterion --tails 1 --d 0.5 --power 0.95 --n1 88 --n2 88 | {"critical_t": 1.6676050, "alpha": 0.0485965} |
      | --mode sensitivity --tails 1 --alpha 0.05 --power 0.95 --n1 88 --n2 88 | {"ncp": 3.3025887, "d": 0.4978840} |
      | --mode a-priori --tails 2 --d 0.5 --alpha 0.05 --power 0.95 --ratio 1 | {"ncp": 3.6228442, "critical_t": 1.9714347, "df": 208, "n1": 105, "n2": 105, "n_total": 210, "actual_power": 0.9501287} |
```

```gherkin
# language: tr
Özellik: Eşit olmayan oranda grup büyüklükleri  [AJAN, G*Power arayüzüyle doğrulandı 140/140: LEDGER H-01]
  Klinik bağlam: plaseboya daha az hasta ayırmak (ratio = N2/N1).
  Kural: sürekli toplam N* çift sayıya yukarı yuvarlanır (N = 2·⌈N*/2⌉),
         n1 = ⌊N/(1+ratio) + 0.5⌋, n2 = N − n1. Gerçekleşen güç hedefin altında kalabilir.

  Senaryo taslağı: Çift toplam, yarım yukarı yuvarlanarak bölünür (beklenenler G*Power ekranından)
    Eğer ki "<argümanlar>" ile a-priori hesaplarsam
    O zaman çıktı "<beklenen>" alanlarını içermeli

    Örnekler:
      | argümanlar | beklenen |
      | --mode a-priori --tails 1 --d 0.5 --alpha 0.05 --power 0.95 --ratio 3 | {"n1": 59, "n2": 175, "n_total": 234, "actual_power": 0.9522160} |
      | --mode a-priori --tails 2 --d 0.5 --alpha 0.05 --power 0.8 --ratio 1.5 | {"n1": 54, "n2": 80, "n_total": 134, "actual_power": 0.8046333} |
      | --mode a-priori --tails 2 --d 0.8 --alpha 0.05 --power 0.8 --ratio 0.25 | {"n1": 64, "n2": 16, "n_total": 80, "actual_power": 0.8069741} |
      | --mode a-priori --tails 2 --d 0.3 --alpha 0.01 --power 0.9 --ratio 0.7 | {"n1": 404, "n2": 282, "n_total": 686, "actual_power": 0.8998856} |
      | --mode a-priori --tails 2 --d 0.5 --alpha 0.05 --power 0.8 --ratio 2 | {"n1": 48, "n2": 96, "n_total": 144, "actual_power": 0.8021395} |
      | --mode a-priori --tails 1 --d 0.5 --alpha 0.05 --power 0.95 --ratio 0.5 | {"n1": 132, "n2": 66, "n_total": 198, "actual_power": 0.9515720} |
      | --mode a-priori --tails 2 --d 0.5 --alpha 0.05 --power 0.8 --ratio 0.05 | {"n1": 663, "n2": 33, "n_total": 696, "actual_power": 0.7994111} |
      | --mode a-priori --tails 2 --d 0.5 --alpha 0.05 --power 0.8 --ratio 0.01 | {"n1": 3174, "n2": 32, "n_total": 3206} |
      | --mode a-priori --tails 2 --d 0.5 --alpha 0.05 --power 0.8 --ratio 100 | {"n1": 32, "n2": 3174, "n_total": 3206} |
```

```gherkin
# language: tr
Özellik: Sınır değerler  [AJAN, G*Power arayüzüyle doğrulandı: LEDGER H-02, H-03, H-04, D-02]
  Senaryo taslağı: Çok büyük ve çok küçük etki, güç = alfa, çift kuyruk (beklenenler G*Power ekranından)
    Eğer ki "<argümanlar>" ile çalıştırırsam
    O zaman çıktı "<beklenen>" alanlarını içermeli

    Örnekler:
      | argümanlar | beklenen |
      | --mode a-priori --tails 2 --d 5 --alpha 0.05 --power 0.8 --ratio 1 | {"n1": 3, "n2": 3, "df": 4} |
      | --mode a-priori --tails 2 --d 10 --alpha 0.05 --power 0.8 --ratio 1 | {"n1": 2, "n2": 2, "df": 2} |
      | --mode a-priori --tails 2 --d 10 --alpha 0.05 --power 0.8 --ratio 0.25 | {"n1": 3, "n2": 1, "df": 2, "actual_power": 0.9754623} |
      | --mode a-priori --tails 2 --d 10 --alpha 0.05 --power 0.8 --ratio 0.1 | {"n1": 4, "n2": 0, "df": 2, "ncp": 0, "actual_power": 0.05} |
      | --mode a-priori --tails 2 --d 0.001 --alpha 0.05 --power 0.95 --ratio 1 | {"n1": 25989420, "n2": 25989420, "n_total": 51978840} |
      | --mode a-priori --tails 2 --d 0.00001 --alpha 0.05 --power 0.95 --ratio 1 | {} |
      | --mode a-priori --tails 1 --d 0.5 --alpha 0.05 --power 0.05 --ratio 1 | {"n1": 2, "n2": 2, "actual_power": 0.0994117} |
      | --mode sensitivity --tails 2 --alpha 0.05 --power 0.05 --n1 20 --n2 20 | {"d": 0, "ncp": 0, "df": 38} |
      | --mode post-hoc --tails 2 --d 0.1 --alpha 0.05 --n1 10 --n2 10 | {"power": 0.0551613} |
      | --mode sensitivity --tails 2 --alpha 0.05 --power 0.8 --n1 20 --n2 30 | {"d": 0.8253839, "df": 48} |
      | --mode criterion --tails 2 --d 0.5 --power 0.8 --n1 30 --n2 45 | {"alpha": 0.2043565, "critical_t": 1.2806903} |
      | --mode compromise --tails 2 --d 0.5 --beta_alpha_ratio 4 --n1 30 --n2 45 | {"alpha": 0.0871225, "beta": 0.3484899} |
```

```gherkin
# language: tr
Özellik: Geçersiz girdiler reddedilir  [DOK: CONTRACT §2.4, §5] [AJAN, G*Power arayüzüyle doğrulandı: oracle V20, V32, V39–V41]
  Senaryo taslağı: Hata JSON'u ve çıkış kodu
    Eğer ki "<argümanlar>" ile çalıştırırsam
    O zaman stdout tek satır "error" içeren JSON olmalı
    Ve çıktı "<beklenen>" alanlarını içermeli
    Ve çıkış kodu <çıkış> olmalı

    Örnekler:
      | argümanlar | beklenen | çıkış |
      | --mode a-priori --tails 2 --d 0.5 --alpha 0.05 --power 0.95 | {"code": "MISSING_PARAM", "field": "ratio"} | 2 |
      | --mode post-hoc --tails 2 --d 0.5 --alpha 0.05 --n1 88 --n2 88 --power 0.8 | {"code": "UNKNOWN_PARAM", "field": "power"} | 2 |
      | --mode post-hoc --tails 2 --d 0.5 --alpha 0.05 --n1 88.5 --n2 88 | {"code": "INVALID_VALUE", "field": "n1"} | 2 |
      | --mode post-hoc --tails 2 --d 0,5 --alpha 0.05 --n1 88 --n2 88 | {"code": "INVALID_VALUE", "field": "d"} | 2 |
      | --mode post-hoc --tails 3 --d 0.5 --alpha 0.05 --n1 88 --n2 88 | {"code": "OUT_OF_RANGE", "field": "tails"} | 2 |
      | --mode post-hoc --tails 2 --d 0.5 --alpha 0.05 --n1 1 --n2 88 | {"code": "OUT_OF_RANGE", "field": "n1"} | 2 |
      | --mode post-hoc --tails 2 --d 0.5 --alpha 1 --n1 20 --n2 20 | {"code": "OUT_OF_RANGE", "field": "alpha"} | 2 |
      | --mode a-priori --tails 2 --d 0.5 --alpha 0.05 --power 0.8 --ratio 0 | {"code": "OUT_OF_RANGE", "field": "ratio"} | 2 |
      | --mode a-priori --tails 1 --d 0.5 --alpha 0.05 --power 0.04 --ratio 1 | {"code": "INCONSISTENT", "field": "power"} | 2 |
      | --mode sensitivity --tails 2 --alpha 0.05 --power 0.04 --n1 20 --n2 20 | {"code": "INCONSISTENT", "field": "power"} | 2 |
      | --mode a-priori --tails 2 --d 0.5 --alpha 0.05 --power 0.8 --ratio 0.009 | {"code": "OUT_OF_RANGE", "field": "ratio"} | 2 |
      | --mode a-priori --tails 2 --d 0.5 --alpha 0.05 --power 0.8 --ratio 100.5 | {"code": "OUT_OF_RANGE", "field": "ratio"} | 2 |
      | --mode a-priori --tails 2 --d 0.0000000001 --alpha 0.05 --power 0.95 --ratio 1 | {"code": "OUT_OF_RANGE", "field": "d"} | 2 |
      | --mode post-hoc --tails 2 --d 0.0000000001 --alpha 0.05 --n1 20 --n2 20 | {"df": 38} | 0 |
      | --mode bogus | {"code": "UNSUPPORTED", "field": "mode"} | 2 |
```

```gherkin
# language: tr
Özellik: Ajan çağı arayüzü  [DOK: CONTRACT §2, §7]
  Senaryo: CLI çıktısı makine tarafından okunabilir
    Eğer ki herhangi bir geçerli girdiyle çalıştırırsam
    O zaman stdout'ta tam olarak bir satır JSON olmalı
    Ve n1, n2, n_total, df JSON tam sayısı olmalı
    Ve çağrı 2 saniyeden kısa sürmeli
    # test: tests/test_cli.py

  Senaryo: MCP ile CLI aynı cevabı verir
    Diyelim ki CONTRACT §9'daki 25 vektör
    Eğer ki her birini hem CLI'ye hem "power_analysis" MCP aracına verirsem
    O zaman iki çıktı bayt bayt aynı olmalı
    # test: tests/test_mcp_equivalence.py

  Senaryo: Ajan hesap yapmaz
    Eğer ki ajan klinik bir soruyu yanıtlarsa
    O zaman yanıttaki her sayı logs/agent_calls.jsonl'daki bir araç çıktısından gelmeli
    Ve "orta etki" gibi bir kategori kullanıldıysa varsayılan değeri açıkça söylemeli
    # test: tests/test_agent.py, eval/run_eval.py
```
