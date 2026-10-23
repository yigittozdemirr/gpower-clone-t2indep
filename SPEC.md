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
- Sürekli `df` (tam sayı olmayan) desteklenmelidir; a-priori çözümü sürekli `n1` üzerinde çalışır (Bölüm 3.1).

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
9. Tutarlılık → `INCONSISTENT`:
   - `a-priori` ve `sensitivity`: `power ≤ alpha` ise hata, field `power`, mesaj "Power, alpha değerinden büyük olmalı". `[AJAN: LEDGER H-04]` (sözleşmedeki hata örneği de aynı mesajı gösteriyor.)
10. Hesap çözüm üretemezse → `NO_SOLUTION` (Bölüm 3'teki sınırlar).

Çıkış kodları `[DOK: CONTRACT]`: başarı `0`; adım 2–9 hataları `2`; `NO_SOLUTION` ve beklenmeyen istisnalar `1` (beklenmeyen istisna `code: "INTERNAL"`).

Hata JSON'u: `{"error": "<insan için açıklama>", "code": "<KOD>", "field": "<alan ya da null>"}`.

---

## 3. Modlar

Her modun girdi/çıktı alanları CONTRACT §4.1'deki tablodadır. Aşağıda yalnızca **davranış** var. Tüm çıktılarda `df` tam sayıdır; `critical_t` her zaman pozitif üst kritik değerdir (çift kuyrukta `t⁻¹(1 − alpha/2)`).

### 3.1 `a-priori` — gerekli örneklem

Girdi: `tails, d, alpha, power, ratio` (`ratio` = N2/N1).

**Dağıtım kuralı `[AJAN: LEDGER H-01]`:**

1. `n1` **sürekli** bir değişken kabul edilir; `n2 = ratio · n1` (sürekli), `df = n1 + n2 − 2` (sürekli).
2. `power(n1) = hedef power` denkleminin kökü `n1*` bulunur (güç `n1`'de monoton artan).
3. Sonuç: `n1 = ⌈n1*⌉`, `n2 = ⌈ratio · n1*⌉` — **her grup ayrı ayrı yukarı yuvarlanır**. Dolayısıyla `n2 / n1` tam olarak `ratio` olmayabilir (örn. ratio = 3 için `n1 = 59, n2 = 175` beklenir; `n2 = 3·59 = 177` **değil**).
4. `ncp`, `critical_t`, `df` ve `actual_power` bu **tam sayı** `n1, n2` ile yeniden hesaplanır. `n_total = n1 + n2`.
5. Tavan almadan önce kayan nokta gürültüsünü bastırmak için `⌈x − 1e-9⌉` kullanılır.

Kanıt zinciri: G*Power kılavuzunun iki grup örneğinde ratio = 2 iken N = 443 (148 ve 295) raporlanıyor; 2 × 148 = 296 ≠ 295. Yani G*Power `n2`'yi `n1`'in tam sayı katı olarak değil, sürekli çözümden ayrı yuvarlayarak buluyor. Bu örnek başka bir testten (Fisher exact); t testinde aynı kuralın geçerli olduğu deney E-01…E-06 ile doğrulanacak. Alternatif hipotez (A: tam sayı `n1` için `n2 = ⌈ratio·n1⌉` ile en küçük `n1`) bazı oranlarda farklı sonuç verir; deneyler bu iki hipotezi ayırt edecek şekilde seçildi.

**Kök arama:**
- Alt sınır `n1_lo = max(2, 2/ratio)` — her iki grubun da en az 2 olmasını sağlar `[AJAN: LEDGER H-02]`. `power(n1_lo) ≥ hedef` ise `n1* = n1_lo` alınır.
- Üst sınır: `n1_lo`'dan başlayıp ikiye katlayarak `power ≥ hedef` olan ilk nokta (bu sayede `ncp` hiçbir zaman gereksiz büyümez ve sayısal taşma olmaz).
- `n1*` 1e7'yi aşarsa → `NO_SOLUTION` `[AJAN: LEDGER H-03]`.
- Kök: Brent ya da güvenceli ikiye bölme, mutlak tolerans 1e-10.

Örnek (açık vektör): `tails=1, d=0.5, alpha=0.05, power=0.95, ratio=1` → `n1* ≈ 87.26` → `n1 = n2 = 88`, `df = 174`, `ncp = 3.3166248`, `critical_t = 1.6536580`, `actual_power = 0.9514254`.

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

- `post-hoc(a-priori sonucu n1,n2)` gücü = a-priori `actual_power` ≥ hedef güç.
- `a-priori` minimallik: oranı koruyan **sürekli** yolda bir alt nokta, `power(n1 − 1, ratio·(n1 − 1))`, hedef güce ulaşmaz. (Tam sayı çifti `(n1 − 1, n2)` ulaşabilir, çünkü n2 ayrı yuvarlanır: 88/88 örneğinde (87, 88) hedefi geçer. Bu değişmezin ilk sürümü yanlıştı; bkz. HALLUCINATIONS.md H-3.)
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
Özellik: Eşit olmayan oranda grup büyüklükleri  [AJAN: LEDGER H-01]
  Klinik bağlam: plaseboya daha az hasta ayırmak (ratio = N2/N1).
  Kural: sürekli çözüm n1* için n1 = ⌈n1*⌉ ve n2 = ⌈ratio·n1*⌉; n2, n1'in tam katı olmak zorunda değil.

  Senaryo taslağı: Her grup ayrı yukarı yuvarlanır
    Eğer ki "<argümanlar>" ile a-priori hesaplarsam
    O zaman çıktı "<beklenen>" alanlarını içermeli

    Örnekler:
      | argümanlar | beklenen |
      | --mode a-priori --tails 1 --d 0.5 --alpha 0.05 --power 0.95 --ratio 3 | {"n1": 59, "n2": 175, "n_total": 234} |
      | --mode a-priori --tails 2 --d 0.5 --alpha 0.05 --power 0.8 --ratio 1.5 | {"n1": 54, "n2": 80, "n_total": 134} |
      | --mode a-priori --tails 2 --d 0.8 --alpha 0.05 --power 0.8 --ratio 0.25 | {"n1": 63, "n2": 16, "n_total": 79} |
      | --mode a-priori --tails 2 --d 0.3 --alpha 0.01 --power 0.9 --ratio 0.7 | {"n1": 404, "n2": 283, "n_total": 687} |
      | --mode a-priori --tails 2 --d 0.5 --alpha 0.05 --power 0.8 --ratio 2 | {"n1": 48, "n2": 96, "n_total": 144} |
      | --mode a-priori --tails 1 --d 0.5 --alpha 0.05 --power 0.95 --ratio 0.5 | {"n1": 131, "n2": 66, "n_total": 197} |
```

```gherkin
# language: tr
Özellik: Sınır değerler  [AJAN: LEDGER H-02, H-03, D-02]
  Senaryo taslağı: Çok büyük ve çok küçük etki, çift kuyruk
    Eğer ki "<argümanlar>" ile çalıştırırsam
    O zaman çıktı "<beklenen>" alanlarını içermeli

    Örnekler:
      | argümanlar | beklenen |
      | --mode a-priori --tails 2 --d 5 --alpha 0.05 --power 0.8 --ratio 1 | {"n1": 3, "n2": 3, "df": 4} |
      | --mode a-priori --tails 2 --d 10 --alpha 0.05 --power 0.8 --ratio 1 | {"n1": 2, "n2": 2, "df": 2} |
      | --mode post-hoc --tails 2 --d 0.1 --alpha 0.05 --n1 10 --n2 10 | {"power": 0.0551613} |
      | --mode sensitivity --tails 2 --alpha 0.05 --power 0.8 --n1 20 --n2 30 | {"d": 0.8253839, "df": 48} |
      | --mode criterion --tails 2 --d 0.5 --power 0.8 --n1 30 --n2 45 | {"alpha": 0.2043565, "critical_t": 1.2806903} |
      | --mode compromise --tails 2 --d 0.5 --beta_alpha_ratio 4 --n1 30 --n2 45 | {"alpha": 0.0871225, "beta": 0.3484899} |
```

```gherkin
# language: tr
Özellik: Geçersiz girdiler reddedilir  [DOK: CONTRACT §2.4, §5] [AJAN: LEDGER H-03, H-04]
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
      | --mode sensitivity --tails 2 --alpha 0.05 --power 0.05 --n1 20 --n2 20 | {"code": "INCONSISTENT", "field": "power"} | 2 |
      | --mode a-priori --tails 2 --d 0.001 --alpha 0.05 --power 0.95 --ratio 1 | {"code": "NO_SOLUTION"} | 1 |
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
