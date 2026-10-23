# SPEC.md — `t2-indep` temiz oda belirtimi

**Aile:** `t2-indep` · K1 · t tests – Means: Difference between two independent means (two groups)
**Klinik örnek:** İlaç ve plasebo grubu
**Sözleşme:** [CONTRACT.md](CONTRACT.md) sürüm 1.0.0
**Bu belgeyi yazan:** İnceleme (REA) oturumu. **Bu belgeyi okuyan:** Yazım oturumu (yalnızca SPEC.md + CONTRACT.md görür).

Bu belge G*Power'ın kaynak kodundan değil; yayımlanmış yöntemlerden (Cohen 1988; Faul, Erdfelder, Lang & Buchner 2007), G*Power kılavuzundan ve G*Power'ın **gözlenen** davranışından üretilmiştir. Her davranış kuralının yanında kaynağı yazar:

- `[YAYIN]` — yayımlanmış istatistik yöntemi
- `[SÖZLEŞME]` — CONTRACT.md'de yazan
- `[REA]` — G*Power'da gözlenmiş ve kanıt defterinde ([rea/KANIT_DEFTERI.md](rea/KANIT_DEFTERI.md)) kanıtı olan davranış
- `[REA-HİPOTEZ]` — kanıta dayalı çıkarım, G*Power'da doğrulama deneyi tanımlı ama sonucu henüz deftere işlenmemiş

---

## 1. Matematik `[YAYIN]`

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

- **Çalışma zamanında yalnızca standart kütüphane** kullanılır. Gerekçe `[REA]` değil ölçümdür: bu makinede `import scipy.stats` tek başına ~2.1 s sürüyor, sözleşme her çağrı için 2 s sınırı koyuyor (CONTRACT §2.1). Python'un kendi açılışı ~0.09 s.
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

Kontrol sırası sabittir; ilk hatada durulur `[SÖZLEŞME]` + takım kararı:

1. `--version` tek başına verilirse sürüm JSON'u.
2. `test` ya da `mode` eksik → `MISSING_PARAM` (field: `test`/`mode`).
3. `test` ≠ `t2-indep` ya da `mode` bilinmiyor → `UNSUPPORTED` (field: `test`/`mode`). Diğer aileler bu takımın kapsamında değildir.
4. Aynı alan iki kez verilmiş → `INVALID_VALUE`.
5. Moda ait olmayan alan (tanınmayan ya da ilgisiz) → `UNKNOWN_PARAM` (alan sırasıyla ilk bulunan).
6. Modun gerektirdiği alan eksik → `MISSING_PARAM` (Bölüm 4 tablosundaki sırayla ilk eksik).
7. Tür: ondalık alanlar sonlu bir sayı olmalı (`nan`, `inf`, `0,05`, boş metin → `INVALID_VALUE`). Tam sayı alanları (`tails`, `n1`, `n2`) yalnızca tam sayı yazımı kabul eder: `88` evet; `88.5`, `88.0`, `1e2` → `INVALID_VALUE`. MCP'den gelen JSON değerinde `88` (int) kabul, `88.5` (float) → `INVALID_VALUE`; `true/false` → `INVALID_VALUE`.
8. Aralık (CONTRACT §5) → `OUT_OF_RANGE`: `tails` ∈ {1,2}; `0 < alpha < 1`; `0 < power < 1`; `beta_alpha_ratio > 0`; `d > 0`; `ratio > 0`; `n1, n2 ≥ 2`.
9. Tutarlılık → `INCONSISTENT`:
   - `a-priori` ve `sensitivity`: `power ≤ alpha` ise hata, field `power`, mesaj "Power, alpha değerinden büyük olmalı". `[REA-HİPOTEZ: H-05]` (sözleşmedeki hata örneği de aynı mesajı gösteriyor.)
10. Hesap çözüm üretemezse → `NO_SOLUTION` (Bölüm 3'teki sınırlar).

Çıkış kodları `[SÖZLEŞME]`: başarı `0`; adım 2–9 hataları `2`; `NO_SOLUTION` ve beklenmeyen istisnalar `1` (beklenmeyen istisna `code: "INTERNAL"`).

Hata JSON'u: `{"error": "<insan için açıklama>", "code": "<KOD>", "field": "<alan ya da null>"}`.

---

## 3. Modlar

Her modun girdi/çıktı alanları CONTRACT §4.1'deki tablodadır. Aşağıda yalnızca **davranış** var. Tüm çıktılarda `df` tam sayıdır; `critical_t` her zaman pozitif üst kritik değerdir (çift kuyrukta `t⁻¹(1 − alpha/2)`).

### 3.1 `a-priori` — gerekli örneklem

Girdi: `tails, d, alpha, power, ratio` (`ratio` = N2/N1).

**Dağıtım kuralı `[REA-HİPOTEZ: H-01]`:**

1. `n1` **sürekli** bir değişken kabul edilir; `n2 = ratio · n1` (sürekli), `df = n1 + n2 − 2` (sürekli).
2. `power(n1) = hedef power` denkleminin kökü `n1*` bulunur (güç `n1`'de monoton artan).
3. Sonuç: `n1 = ⌈n1*⌉`, `n2 = ⌈ratio · n1*⌉` — **her grup ayrı ayrı yukarı yuvarlanır**. Dolayısıyla `n2 / n1` tam olarak `ratio` olmayabilir (örn. ratio = 3 için `n1 = 59, n2 = 175` beklenir; `n2 = 3·59 = 177` **değil**).
4. `ncp`, `critical_t`, `df` ve `actual_power` bu **tam sayı** `n1, n2` ile yeniden hesaplanır. `n_total = n1 + n2`.
5. Tavan almadan önce kayan nokta gürültüsünü bastırmak için `⌈x − 1e-9⌉` kullanılır.

Kanıt zinciri: G*Power kılavuzunun iki grup örneğinde ratio = 2 iken N = 443 (148 ve 295) raporlanıyor; 2 × 148 = 296 ≠ 295. Yani G*Power `n2`'yi `n1`'in tam sayı katı olarak değil, sürekli çözümden ayrı yuvarlayarak buluyor. Bu örnek başka bir testten (Fisher exact); t testinde aynı kuralın geçerli olduğu deney E-01…E-06 ile doğrulanacak. Alternatif hipotez (A: tam sayı `n1` için `n2 = ⌈ratio·n1⌉` ile en küçük `n1`) bazı oranlarda farklı sonuç verir; deneyler bu iki hipotezi ayırt edecek şekilde seçildi.

**Kök arama:**
- Alt sınır `n1_lo = max(2, 2/ratio)` — her iki grubun da en az 2 olmasını sağlar `[REA-HİPOTEZ: H-02]`. `power(n1_lo) ≥ hedef` ise `n1* = n1_lo` alınır.
- Üst sınır: `n1_lo`'dan başlayıp ikiye katlayarak `power ≥ hedef` olan ilk nokta (bu sayede `ncp` hiçbir zaman gereksiz büyümez ve sayısal taşma olmaz).
- `n1*` 1e7'yi aşarsa → `NO_SOLUTION` `[REA-HİPOTEZ: H-04]`.
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

Girdi: `tails, alpha, power, n1, n2`. `power(d) = hedef` denkleminin **d ≥ 0** kökü `[SÖZLEŞME]` (G*Power yalnızca pozitif yönü hesaplar). Arama aralığı `d ∈ [0, 1000]`; bulunamazsa `NO_SOLUTION`. Çıktı: `ncp` (bulunan d ile), `critical_t`, `df`, `d`.

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

## 5. Mimari `[SÖZLEŞME §7, kural 3]`

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

## 6. MCP `[SÖZLEŞME §7]`

- Tek araç `power_analysis`; girdi şeması CLI alan adlarıyla aynı (`test`, `mode` zorunlu; diğerleri isteğe bağlı olarak tanımlı, zorunluluğu motor denetler). Şema türleri gevşek tutulur (sayı ya da metin) ki hata davranışı CLI ile aynı kalsın.
- Çıktı: CLI'nin stdout satırıyla **bayt bayt aynı** metin (`TextContent`). Hata da aynı JSON.
- Eşdeğerlik testi: CONTRACT §9'daki 25 vektörün her biri için CLI (alt süreç) çıktısı == MCP (gerçek stdio istemcisi) çıktısı.

## 7. Ajan `[SÖZLEŞME §8, §10]`

- Claude modeli + MCP istemcisi (stdio) ile `power_analysis` aracını çağırır; **sayıyı asla kendisi hesaplamaz**, yalnızca aracın döndürdüğünü aktarır.
- Her araç çağrısı `logs/agent_calls.jsonl`'a bir satır: `ts` (yerel saat, ofsetli ISO 8601), `question`, `tool_input`, `tool_output` (ayrıştırılmış JSON), `tokens_in`, `tokens_out` (o araç çağrısını üreten model yanıtının `usage` değerleri).
- Sistem istemi kuralları: "küçük/orta/büyük etki" bir kategoridir; ajan değeri (0.2/0.5/0.8) seçerse bunu **açıkça söyler**. Yön iddiası yoksa çift kuyruk, "daha iyi/daha az" gibi yön varsa tek kuyruk önerir ve bunu söyler. Eksik bilgi varsa önce sorar. Yalnızca kurgusal senaryolar.

## 8. Değişmezler (özellik testleri için)

- `post-hoc(a-priori sonucu n1,n2)` gücü = a-priori `actual_power` ≥ hedef güç.
- `a-priori`: `n1 − 1` (ve oran korunarak bir alt nokta) hedef güce ulaşmaz (minimallik).
- `criterion` çıktısındaki α ile `post-hoc` → hedef güç (≤ 1e-9).
- `sensitivity` çıktısındaki d ile `post-hoc` → hedef güç.
- `compromise`: `beta / alpha = q` (göreli ≤ 1e-9) ve `power = 1 − beta`.
- Güç: d'de, n'de ve α'da monoton artan; tek kuyruk gücü ≥ çift kuyruk gücü (d > 0).
- Aynı girdi → aynı bayt dizisi (deterministik).
