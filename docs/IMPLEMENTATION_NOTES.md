# IMPLEMENTATION_NOTES — `t2-indep` temiz oda uygulaması

Bu notları yazım (implementation) oturumu yazdı. Bu oturum yalnızca `SPEC.md` ve `CONTRACT.md`'yi okudu; `rea/`, G*Power ya da inceleme betikleri görülmedi, G*Power çalıştırılmadı.

## 1. Ne yapıldı

```
pyproject.toml                 hatchling, requires-python >=3.10, çekirdek bağımlılık: yok
public_vectors.jsonl           CONTRACT §9'daki 25 vektör (birebir kopya)
src/gpower_clone/
  __init__.py
  numerics.py                  özel fonksiyonlar (saf stdlib)
  engine.py                    TEK hesap + doğrulama motoru: run(), run_argv(), to_json(), version_info()
  cli.py                       argv -> engine.run_argv -> stdout'a tek JSON satırı, çıkış kodu
  mcp_server.py                MCP stdio sunucusu, tek araç: power_analysis
  agent.py                     doğal dil ajanı (Claude + MCP stdio istemcisi)
tests/
  conftest.py, test_public_vectors.py, test_numerics_oracle.py, test_invariants.py,
  test_validation.py, test_cli.py, test_mcp_equivalence.py, test_agent.py
```

Konsol komutları: `gpower-clone`, `gpower-clone-mcp`, `gpower-clone-agent`.
Ekstralar: `mcp = ["mcp>=1.2"]`, `agent = ["mcp>=1.2", "anthropic>=0.40"]`; geliştirme grubu: `pytest`, `scipy`, `mcp`.
Kurulum ve test: `uv sync --all-extras --group dev` ve `uv run pytest -q`.

Çekirdek (`cli`, `engine`, `numerics`) yalnızca `json`, `math`, `re`, `platform` kullanır; bir test, bu modüller yüklenince `scipy/numpy/mcp/anthropic/pydantic` modüllerinin içe aktarılmadığını doğrular.

## 2. Sayısal yöntemler (`numerics.py`)

| Yapı taşı | Yöntem |
|---|---|
| `log Γ` farkları | `math.lgamma`; büyük argümanlarda `lgamma(x+h) − lgamma(x)` Stirling düzeltme serisi + `log1p` ile (çok büyük df'de iptal hatasını önler). `lbeta` bunun üzerine kurulu. |
| Poisson ağırlıkları | `e^{-λ} λ^m / Γ(m+1)` eyer noktası (Loader) biçimi: `−bd0(m,λ) − ½log(2πm) − stirlerr(m)`, `bd0 = λ[(1+v)log1p(v) − v]`. Doğrudan `−λ + m log λ − lgamma(m+1)` büyük λ'da ~λ·1e-16 göreli hata veriyordu (δ = 600'de 2e-10); düzeltildi. |
| `I_x(a,b)` | Lentz sürekli kesri; `x > (a+1)/(a+b+2)` ise simetri `1 − I_{1−x}(b,a)`. `x` ve `1−x` (ve logları) ayrı ayrı ve kesin olarak taşınır; ilk payda `1 − (a+b)x/(a+1)`, `x` 1'e yakınken `1−x`'ten kurulur. Fonksiyon `(I, 1−I)` çiftini döndürür (iki kuyruk da göreli hassas). |
| Merkezî t CDF / SF | `P(|T|>t) = 1 − I_{t²/(t²+ν)}(½, ν/2)`; `t > 1e100` için `x, y` log uzayında (taşma yok; ν=1, q=1e-300 bile çalışır). |
| Merkezî t ters (üst kantil) | Acklam normal kantili + Cornish–Fisher başlangıcı, 4'er katlanarak köşeleme, sonra `log sf(t) − log q` üzerinde köşeli (bracket) Newton; köşe dışına çıkarsa geometrik ikiye bölme. Gidiş-dönüş testi: `|sf(t_isf(q)) − q| ≤ 1e-12·q`, q = 1e-300'e kadar, df 1…1e13. |
| Merkezî olmayan t CDF | Lenth (1989) AS 243 gösterimi (Benton & Krishnamoorthy 2003 biçimi): `F = Φ(−δ) + ½Σ[P_i I_x(i+½, ν/2) + sgn(δ) R_i I_x(i+1, ν/2)]`. Toplam Poisson modundan (`k = ⌊δ²/2⌋`) başlar, **ileri ve geri** yönde yürür; `I_x` değerleri log uzayındaki `g(a)` terimleriyle özyinelemeli güncellenir; durdurma, kalan Poisson kütlesinin geometrik üst sınırı `< 1e-17`. `t < 0` için `F(t;δ) = 1 − F(−t;−δ)`. |
| Büyük `|δ|` geri dönüşü | (1) `|δ| > 37` ve normal yaklaşım `z = (t(1−1/4ν) − δ)/√(1+t²/2ν)` için `|z| > 40` ise 0/1'e sıkıştırma (Φ(−40) ≈ 1e-350; yani yalnızca 1e-12'den çok küçük olasılıklar yaklaşımla verilir). (2) `|δ| > 1000` ise seri yerine Z üzerinden kareleme: `F = Φ(−δ) + ∫ φ(z) Q(ν/2, ν(z+δ)²/(2t²)) dz`, `z ∈ [−12, 12]`, 20 noktalı Gauss–Legendre panelleri (panel genişliği `min(1, ½·t/√(2ν))`), `Q` düzenlenmiş üst eksik gama (seri / Lentz). Örtüşme bölgesinde (δ = 150…950) seri ile kareleme farkı ≤ 6e-13. Hiçbir yol NaN döndürmez (testte δ = 1e8, t = 1e3, df = 1e9 dahil). |
| Çok büyük df | `ν ≥ 1e7` ve `t²/ν ≤ 1e-3` (ya da `ν ≥ 1e5` ve `t²/ν ≤ 1e-4`) ise `E[Φ(t√W − δ)]`'nin `W = χ²_ν/ν` etrafında `O(1/ν²)`'ye kadar açılımı (hata ≈ `(t²/ν)³`). Gerekçe: Lentz kesri ν ≈ 1e9'da ~1e-10 hassasiyet kaybediyor (her tek adımda `1 + aa·d` iptali); açılım ile seri 1e5…1e8'de ≤ 1e-11 tutarlı. |
| Kök bulma | SciPy `brentq` ile aynı Brent algoritması (saf Python); durdurma yarı genişliği `(xtol + rtol|x|)/2` ya da `min(xtol, rtol|x|)/2`. |

Doğruluk: SciPy kâhinine karşı df ∈ {1, 1.5, 2, 2.5, …, 10000} (tam sayı olmayanlar dahil), ncp 0…40, t ∈ [−60, 60], CDF ve SF için en büyük mutlak hata **≈ 4e-13** (hedef 1e-9). Açık vektörlerin beşi de G*Power'ın 7 basamaklı değerine 5e-8 içinde (yuvarlama payı).

## 3. Motor davranışı (SPEC §2–§4 uygulaması)

- `power(n1, n2, d, α, tails)` SPEC §1 formülleri; `tc = t_isf(α/tails, df)`; çift kuyrukta iki kuyruk da eklenir.
- **a-priori:** sürekli `n1`, `n2 = ratio·n1`; `n1_lo = max(2, 2/ratio)`; `power(n1_lo) ≥ hedef` ise `n1* = n1_lo`; değilse 2'şer katlayarak köşeleme, Brent (xtol 1e-10). `n1 = ⌈n1* − 1e-9⌉`, `n2 = ⌈ratio·n1* − 1e-9⌉` (her grup ayrı yuvarlanır). `ncp, critical_t, df, actual_power` tam sayı n'lerle yeniden hesaplanır. `n1* > 1e7` → `NO_SOLUTION`. SPEC'teki "ratio = 3 → n1 = 59, n2 = 175" örneği `tails=1, d=0.5, α=0.05, power=0.95, ratio=3` ile birebir üretiliyor.
- **post-hoc:** doğrudan.
- **compromise:** `g(α) = β(α) − qα` (β alt kuyruktan doğrudan hesaplanır), α ∈ [1e-300, 1−2⁻⁵³]; α = 1e-3'ten başlayıp gerekirse 1e-3 çarpanıyla aşağı köşeleme; Brent. Çıktı `power = 1 − beta`.
- **criterion:** `power(α) − hedef`, aynı köşeleme ve tolerans; `power(1−2⁻⁵³) < hedef` ya da `power(1e-300) > hedef` → `NO_SOLUTION`.
- **sensitivity:** d ∈ [0, 1000]; üst uç `δ = 4`'e karşılık gelen d'den başlayıp 1000'e kadar ikiye katlanır (ncp gereksiz büyümez); 1000'de hedefe ulaşılmazsa `NO_SOLUTION`.
- Çıktı biçimi: `json.dumps(obj, ensure_ascii=True, separators=(", ", ": "), allow_nan=False)`; ondalıklar `float.__repr__`, tam sayılar `int`. CLI satırı `sys.stdout.buffer`'a `\n` ile yazılır (Windows'ta `\r\n` olmaz). Sonlu olmayan bir çıktı oluşursa `INTERNAL` (çıkış 1).
- `--version` → `{"contract_version": "1.0.0", "name": "gpower-clone-t2indep", "engine": "Python 3.12.15 (stdlib)"}`.

## 4. SPEC belirsizlikleri ve verilen kararlar

1. **CLI sözdizimi hatalarının sırası.** SPEC §2 sırası alan sözlüğü üzerinden tanımlı; argv sözdizimi hataları orada yok. Karar: argv soldan sağa taranırken (SPEC §2 adımlarından **önce**) `--` ile başlamayan konumsal belirteç → `UNKNOWN_PARAM` (field = belirtecin kendisi), değersiz bayrak → `INVALID_VALUE` (field = bayrak adı). Örn. `gpower-clone foo` → `UNKNOWN_PARAM foo` (`MISSING_PARAM test` değil).
2. **"Değersiz bayrak" tanımı.** Son belirteç olan ya da ardından `--` ile başlayan bir belirteç gelen bayrak. `-0.5` gibi tek tireli değerler değerdir (→ `OUT_OF_RANGE`). `--d=0.5` biçimi desteklenmez: bayrak adı `d=0.5` sayılır (ardından değer gelmezse `INVALID_VALUE`, gelirse adım 5'te `UNKNOWN_PARAM`).
3. **`--version` başka argümanlarla.** Yalnızca argv tam olarak `["--version"]` ise sürüm JSON'u. Aksi halde sıradan bayrak: değersizse `INVALID_VALUE version`, değerliyse `UNKNOWN_PARAM version`.
4. **Adım 2–3 iç sırası.** Önce `test` eksik mi, sonra `mode` eksik mi; ardından `test` desteklenmiyor mu, sonra `mode` bilinmiyor mu. Örn. `{"test": "t-paired"}` → `MISSING_PARAM mode`.
5. **Yinelenen alan.** Adım 2–3 için `test`/`mode`'un ilk değeri kullanılır. Adım 4, ikinci geçişi en önce görülen alanı raporlar (tanınmayan alan yinelenmişse de adım 4 adım 5'ten önce gelir). MCP'de JSON nesnesi yineleme taşıyamaz.
6. **Adım 7 ve 8'deki alan sırası.** SPEC adım 5 için "alan sırasıyla", adım 6 için tablo sırasını söylüyor; 7–8 için söylemiyor. Karar: tablo (Bölüm 4) sırası; önce tüm tür denetimleri, sonra tüm aralık denetimleri.
7. **Ondalık yazımı.** `float()` çok şey kabul ediyor (`" 0.05"`, `"1_0"`, `"infinity"`, Unicode rakamlar). Karar: katı düzenli ifade `[+-]?(rakam[.rakam*] | .rakam)([eE][+-]?rakam)`, yalnızca ASCII rakam; boşluk, alt çizgi, onaltılık, `%` → `INVALID_VALUE`. `1e400` (taşma → inf) → `INVALID_VALUE`.
8. **Tam sayı yazımı.** `[+-]?[0-9]+` (baştaki sıfırlar kabul). Double'a sığmayan (≈1.8e308'den büyük) tam sayılar → `INVALID_VALUE`.
9. **MCP JSON türleri.** SPEC yalnızca `88.5` (float) için hata diyor. Karar: tam sayı alanında **her** JSON float'ı (`88.0` dahil) `INVALID_VALUE` (CLI'deki `"88.0"` kuralıyla tutarlı). Ondalık alanlarda JSON int kabul. Metin değerler CLI kurallarıyla ayrıştırılır. `bool`, liste, nesne → `INVALID_VALUE`. Metin olmayan `test`/`mode` → `UNSUPPORTED`.
10. **`null` değerler.** MCP istemcileri (ve LLM'ler) kullanılmayan alanlara `null` gönderebiliyor. Karar: `null` = alan verilmemiş. Bu yüzden `{"n2": null}` → `MISSING_PARAM n2`; `post-hoc`'ta `"ratio": null` hata değil.
11. **MCP hata bayrağı.** Hata JSON'u döndüğünde `CallToolResult.isError = true`; metin CLI satırıyla bayt bayt aynı.
12. **a-priori `n1*` sınırı yalnızca `n1`'e uygulanır.** `ratio` çok büyükse `n2` 1e7'yi aşabilir (örn. ratio = 1e6 → n1 = 32, n2 = 31 395 476 geçerli çıktı). `ratio < 2e-7` iken `n1_lo = 2/ratio > 1e7` olduğundan doğrudan `NO_SOLUTION`.
13. **Köşeleme sırasında NO_SOLUTION.** İkiye katlama, alt uç 1e7'yi geçtiği anda durur (kökün 1e7'den büyük olduğu kesinleşmiştir).
14. **compromise toleransı "mutlak 1e-14, göreli 1e-12".** Toplam mı, ikisi birden mi belirsiz. Karar: ikisi birden — durdurma yarı genişliği `min(1e-14, 1e-12·α)/2`. Böylece küçük α'da da `β/α = q` göreli 1e-9 içinde (q = 1000 → α ≈ 1.3e-22 testi).
15. **criterion toleransı belirtilmemiş.** compromise ile aynı alındı. Arama aralığı α ∈ [1e-300, 1 − 2⁻⁵³]; kök 1e-300'ün altındaysa `NO_SOLUTION`.
16. **sensitivity toleransı belirtilmemiş.** `xtol = 1e-14`, `rtol = 1e-13` (toplam biçim).
17. **"Gerekli alanı olmayan mod" ve iç tutarlılık.** SPEC `INCONSISTENT`'i yalnızca a-priori ve sensitivity için tanımlıyor (`power ≤ alpha`, eşitlik dahil); başka tutarlılık kuralı eklenmedi.
18. **Minimallik değişmezi (SPEC §8).** Tam sayı çifti `(n1−1, n2)` hedefe ulaşabilir (çünkü `n2` ayrı yukarı yuvarlanıyor; ratio = 1, n = 88/88 örneğinde `(87, 88)` hedefi geçer). Karar: değişmez, oranı koruyan sürekli yol üzerinde sınanır: `power(n1−1, ratio·(n1−1)) < hedef` (`n1−1 ≥ n1_lo` iken).
19. **`actual_power ≥ hedef`.** `⌈x − 1e-9⌉` kuralı yüzünden `n1`, `n1*`'dan en fazla 1e-9 küçük olabilir; değişmez testi `actual_power ≥ hedef − 1e-9` olarak yazıldı.
20. **"≈ 37'nin üstü" ncp eşiği.** Bu eşik AS 243'ün ileri yönlü toplamındaki `exp(−δ²/2)` taşmasından geliyor; çift yönlü toplamda gerek yok. Seri `|δ| ≤ 1000`'e kadar kullanılıyor, üstünde kareleme. Normal yaklaşım yalnızca `|δ| > 37` ve `|z| > 40` (olasılık < 1e-300) iken sıkıştırma kararı için kullanılıyor.
21. **Ajan logu.** Etkileşimli çok turlu oturumda `question` alanı, o araç çağrısını tetikleyen turdaki kullanıcı mesajıdır. Tek model yanıtı birden çok araç çağrısı isterse her satıra aynı `usage` değerleri yazılır. `ts` yerel saat, saniye hassasiyetinde, ofsetli ISO 8601. Log dosyası çalışma dizinine göre `logs/agent_calls.jsonl`.
22. **Ajanın MCP sunucusunu başlatması.** `PATH`'te `gpower-clone-mcp` varsa o, yoksa `python -m gpower_clone.mcp_server`.
23. **MCP SDK sürümü.** `mcp>=1.2` isteniyor; kurulan sürüm 2.3.0 ve düşük seviye `Server` API'si 2.x'te değişti (`on_list_tools` / `on_call_tool` kurucu argümanları). Sunucu her ikisini destekler: önce 2.x biçimi, `TypeError` olursa 1.x dekoratörleri (`call_tool(validate_input=False)`). İkisi de sınandı: mcp 2.3.0 (proje ortamı) ve mcp 1.30.0 (geçici ortam) ile eşdeğerlik + ajan testleri geçti. Girdi şemasında sayısal alanların türü `["number", "string"]`; 2.x düşük seviye sunucu argümanları şemaya göre doğrulamıyor, 1.x'te doğrulama kapatıldı.
24. **Kâhinin kendi hataları.** SciPy `t.isf` küçük df ve q = 1e-200'de (df = 2.7'de 2 kat) ve `nct.cdf` df ≥ 1e9'da (≈1e-10) hatalı; `nct.cdf` uzak alt kuyrukta NaN veriyor. Bu yüzden kâhin testleri brifteki aralıkla (df ≤ 10000) sınırlı; uç kuyruklar ve çok büyük df için öz-tutarlılık testleri (gidiş-dönüş, açılım ↔ seri, kareleme ↔ seri) kullanıldı; SciPy NaN verdiğinde bizim değerimizin < 1e-12 olduğu doğrulanıyor.

## 5. Test sonuçları

`uv run pytest -q` → **419 passed** (≈ 25–37 s; çoğu süre alt süreç ve MCP testlerinde).

| Dosya | Test | İçerik |
|---|---|---|
| `test_public_vectors.py` | 31 | 5 `t2-indep` vektörü motor ve CLI üzerinden (tam sayılar birebir, ondalıklar CONTRACT §6); diğer 20 vektör `UNSUPPORTED`, çıkış 2; dosya biçimi |
| `test_numerics_oracle.py` | 72 | t CDF/SF, t ters, nct CDF/SF (iki kuyruk, negatif ncp), güç formülü, beta ve gama fonksiyonları SciPy'ye karşı ≤ 1e-9; uç kuyruk gidiş-dönüşü; büyük ncp NaN vermez; büyük df ve kareleme tutarlılığı; Brent |
| `test_invariants.py` | 221 | Tohumlu rastgele ızgara (60 nokta): a-priori → post-hoc, minimallik, criterion, sensitivity, compromise (`β/α = q` göreli ≤ 1e-9, `power = 1 − β`), monotonluk, tek ≥ çift kuyruk, determinizm, ayrı yuvarlama |
| `test_validation.py` | 73 | Her hata kodu alan ve çıkış koduyla; `0,05`, `nan`, `88.0`, yinelenen alan, ilgisiz alan, bilinmeyen test/mod, eksik alan, `power ≤ alpha`; denetim sırası; CLI sözdizimi |
| `test_cli.py` | 17 | Alt süreç: tek satır JSON, `\n` (CRLF değil), JSON tam sayıları, çıkış kodları, `--version`, ASCII kaçışlı Türkçe hata, belirlenimcilik, her çağrı < 2 s, çekirdekte üçüncü taraf modül yok |
| `test_mcp_equivalence.py` | 2 | Gerçek stdio MCP sunucusu: 25 açık vektör + 12 hata/ek girdi için MCP metni == CLI stdout satırı (bayt bayt); gevşek şema |
| `test_agent.py` | 3 | API anahtarı yokken Türkçe stderr + çıkış 1; sahte model istemcisi + gerçek MCP oturumuyla araç döngüsü ve CONTRACT §8 log satırı; sistem istemi kuralları |

Ajan gerçek Anthropic API'siyle çalıştırılmadı (anahtar kullanılmadı); araç döngüsü ve log biçimi sahte istemciyle sınandı.

## 6. Zamanlamalar (bu makine, Windows 11, Python 3.12.15)

Komut: `gpower-clone --test t2-indep --mode a-priori --tails 2 --d 0.2 --alpha 0.01 --power 0.99 --ratio 3`
Çıktı: `{"ncp": 4.905099387372289, "critical_t": 2.577363709187354, "df": 3206, "n1": 802, "n2": 2406, "n_total": 3208, "actual_power": 0.9900102201099491}`

| Çağrı biçimi | Duvar saati (5 çalıştırma) |
|---|---|
| `uv run gpower-clone ...` | 400, 508, 509, 738, 901 ms (uv'nin ortam denetimi dahil) |
| `.venv\Scripts\gpower-clone.exe ...` | 256, 257, 263, 290, 299 ms |
| Yalnızca `engine.run` (süreç içi) | ≈ 6.7 ms/çağrı |

Zor girdiler (süreç içi): `δ = 70000, df = 2` post-hoc 2 ms; `d = 1e6, α = 1e-300` post-hoc 1 ms; `sensitivity α = 1e-15, n = 4/4` 56 ms; `criterion d = 1000, n = 2/2` 150 ms; `a-priori d = 100, α = 1e-300` 100 ms. Hepsi 2 s sınırının çok altında.

## Revizyon 1 — SPEC farkı (`git diff f72c2ec -- SPEC.md`) uygulandı

Bu bölüm, sıfır bağlamla başlatılan yeni bir yazım oturumunda yalnızca SPEC.md farkı okunarak yazıldı. Yukarıdaki §3'teki a-priori maddesi ve §4'teki 12, 13, 17, 18, 19 numaralı kararlar **bu bölümle geçersizdir**.

### Ne değişti

- **a-priori dağıtım kuralı (SPEC §3.1).** Artık sürekli değişken toplam `N`: `n1 = N/(1+ratio)`, `n2 = ratio·N/(1+ratio)`, `df = N − 2`. Önce `power(N = 4) ≥ hedef` mi bakılır; öyleyse `N = 4` (kısayol). Değilse `[4, 8]`'den başlayıp üst ucu ikiye katlayarak köşeleme, ardından Brent (`xtol = 1e-9`, `rtol = 1e-14`, toplam biçim). `N = max(4, 2·⌈N*/2 − 1e-9⌉)`; `n1 = ⌊N/(1+ratio) + 0.5⌋` (yarım yukarı; `math.floor(x + 0.5)`, Python `round` DEĞİL), `n2 = N − n1`. `ncp, critical_t, df, actual_power` tam sayılarla yeniden hesaplanır; `actual_power` hedefin altında kalabilir ve düzeltilmez.
- **Dejenere gruplar.** `n1 < 2` ya da `n2 < 2` ise çıktının sonuna (alan sırası: `ncp, critical_t, df, n1, n2, n_total, actual_power, warning`) SPEC'teki metinle `warning` eklenir. Bir grup 0 iken `ncp_of` doğal olarak 0 verir (`n1·n2/(n1+n2) = 0`), `df = n1 + n2 − 2`; güç tam alpha'ya eşit çıkar (ör. 4/0 → 0.05).
- **NO_SOLUTION.** 1e7 sınırı kaldırıldı. Yalnızca `N* > 1e13`: köşeleme sırasında üst uç ≥ 1e13 iken hâlâ hedefe ulaşılmıyorsa (kök kesin olarak > 1e13) ya da Brent kökü > 1e13 ise. Mesaj: "Gerekli örneklem büyüklüğü çok büyük (N > 1e13); çözüm üretilemedi".
- **ratio aralığı (SPEC §2.8).** `0.01 ≤ ratio ≤ 100` (uçlar dahil); dışında `OUT_OF_RANGE`, field `ratio`, mesaj "Aralık dışı değer: Allocation ratio kabul edilebilir aralığın (0.01, 100) dışında" (`ratio ≤ 0` de aynı mesajı alır).
- **INCONSISTENT (SPEC §2.9).** Yalnızca `power < alpha` (kesin). `power = alpha` geçerli: a-priori'de kısayol `N = 4` verir; sensitivity'de `d = 0`, `ncp = 0` (SPEC §3.5) — eşitlik varsa `g(0)` hesaplanmadan doğrudan `d = 0` (çift kuyrukta `power(0)` yuvarlama yüzünden alpha'nın 1 ulp altında çıkabiliyor).
- **MCP aracı açıklaması.** `ratio` alanının açıklaması `0.01 <= ratio <= 100` oldu; a-priori çıktısında `warning` olabileceği yazıldı (şema türleri değişmedi).

### Belirsizlikler ve kararlar

R1. **`N` kısayolu ve "N > 2" arama alanı.** SPEC hem "arama alanı N > 2" hem "power(4) ≥ hedef ise N = 4" diyor. Karar: güç hiçbir zaman (2, 4) aralığında hesaplanmaz; kök yalnızca `[4, ∞)` aralığında aranır. Bu, kökün (2, 4] aralığında olduğu her durumda 4 vermesi bakımından eşdeğerdir.
R2. **Bölmede kayan nokta.** `N/(1+ratio)` doğrudan bölmeyle hesaplanır (önceden hesaplanmış `1/(1+ratio)` ile çarpma değil), çünkü tam .5 durumları (ratio = 3, N = 234 → 58.5) böyle kesin kalıyor. `ratio` ondalık yazımından gelen gürültüyle `x.4999999…` çıkan bir durum için ek düzeltme yapılmadı (SPEC'te `1e-9` payı yalnızca çift yuvarlama için tanımlı).
R3. **`n1` sınırlaması.** `n1 = min(max(⌊N/(1+ratio)+0.5⌋, 0), N)`; ratio aralığı [0.01, 100] olduğundan bu kırpma pratikte hiç devreye girmez.
R4. **Dejenere çıktıda post-hoc.** `n1` ya da `n2` < 2 olan a-priori sonucu post-hoc'a verilemez (CONTRACT §5 `n ≥ 2`, SPEC §2 notu). Bu yüzden değişmez testi "post-hoc(a-priori n1,n2) = actual_power" yalnızca dejenere olmayan sonuçlarda sınanır; dejenere sonuçta `warning` alanının varlığı sınanır.
R5. **`warning` yalnızca a-priori'de.** SPEC yalnızca §3.1'de tanımlıyor; diğer modlarda dejenere giriş zaten `OUT_OF_RANGE`.
R6. **Minimallik değişmezi.** SPEC §8'deki gibi sürekli yolda `power(N = n_total − 2) < hedef` (n_total > 4 iken); ek olarak `power(N = n_total) ≥ hedef − 1e-12` sınanıyor.
R7. **criterion/sensitivity değişmezleri.** Eski testler `alpha_criterion ≤ alpha` ve `d_sensitivity ≤ d` varsayıyordu (actual_power ≥ hedef'e dayanıyordu). Artık yön, a-priori `actual_power`'ın hedefin üstünde mi altında mı kaldığına göre sınanıyor; gidiş-dönüş (≤ 1e-9) aynen kaldı.
R8. **SPEC §1.1'deki "a-priori çözümü sürekli n1 üzerinde" cümlesi** farkta güncellenmemiş; §3.1 önceliklidir (sürekli toplam N). Sürekli df desteği yine gerekli ve var.
R9. **Çok büyük df.** `d = 1e-5` (ratio 1) artık geçerli: `N ≈ 5.2e11`, `df ≈ 5.2e11`; numerics'teki büyük-df açılımı (`df ≥ 1e7`) kullanılıyor. Bu bölge için G*Power vektörü yok; yalnızca `d = 0.001` (25 989 420 / 25 989 420) Gherkin'de doğrulanıyor.

### Diferansiyel test (dokunulmadı, açılmadı)

`tests/test_differential.py` (ve içe aktardığı `tests/differential.py`) temiz oda kuralı gereği açılmadı/düzenlenmedi. Bu revizyondan sonra:
- `test_gpower_gate` artık **geçiyor** (revizyondan önce kalıyordu); G*Power vektörlerinden V06, V07, V09, V10, V12, V16, V21, V29, V34–V40, V42 revizyonla düzeldi.
- **Kalanlar:** `test_gpower_vector[V33]` — G*Power post-hoc'ta `n1 = 1` kabul ediyor, SPEC §2.8 notu "sözleşme önceliklidir, OUT_OF_RANGE" diyor; SPEC'e uyum bilerek korundu. `test_gpower_vector[V01]`, `[V03]` — mesaj "G*Power hata verdi (sonuç yok); motor sonuç üretti"; revizyondan **önce de** kalıyordu ve SPEC'te bu girdilerin neden hata olduğunu açıklayan bir kural yok (kâhin verisine bakılmadı).
- `test_scale_vector[S…]` — 121 vektör. Mesajlar `n1/n2: motor a/b, ⌈statsmodels⌉ c/d` biçiminde: karşılaştırıcı statsmodels'in sürekli `n1`'ini **eski "her grup ayrı yukarı yuvarlanır" kuralıyla** tam sayıya çeviriyor. Yeni SPEC §3.1 kuralıyla (çift toplam + yarım yukarı bölme) bu karşılaştırma uyuşamaz; motoru SPEC'e aykırı hale getirmeden düzeltilemez. Karşılaştırıcının (inceleme oturumunun aracı) yeni kurala güncellenmesi gerekiyor.

### Test sayıları (`uv run pytest -q`)

Toplam **1044 geçti, 124 kaldı** (hepsi `test_differential.py`: 121 `test_scale_vector` + V01, V03, V33). Uygulama oturumunun kendi testleri ve Gherkin tamamen yeşil:

| Dosya | Sonuç |
|---|---|
| `test_spec_gherkin.py` | 41 geçti |
| `test_invariants.py` | 268 geçti (yeni: çift/≥ 4 toplam, bölme kuralı, sürekli yolda minimallik, ratio = 1 ⇒ n1 = n2, ratio ↔ 1/ratio ayna, yarım yukarı 59/175, actual_power < hedef (404/282), N = 4 kısayolu, dejenere uyarı 4 durum, sensitivity power = alpha) |
| `test_validation.py` | 87 geçti (ratio 0.009 / 100.5 / 1e9 vb. → OUT_OF_RANGE + mesaj; 0.01 ve 100 dahil; power = alpha geçerli; d = 1e-10 → NO_SOLUTION; d = 0.001 → 25 989 420) |
| `test_cli.py` | 20 geçti (yeni: `--d 0.001` ratio 1 ve 0.01, `--d 0.0000000001` → çıkış 1, `--d 10 --ratio 0.1` dejenere) |
| `test_mcp_equivalence.py` | 2 geçti (ek girdiler: d = 1e-10, d = 0.001, 4/0 dejenere, ratio 100.5, sensitivity power = alpha) |
| `test_numerics_oracle.py` | 72 geçti |
| `test_public_vectors.py` | 31 geçti |
| `test_agent.py` | 3 geçti |
| `test_differential.py` | 520 geçti, 124 kaldı (yukarıya bakınız) |

### Zamanlamalar (bu makine, 5 çalıştırma, `--tails 2 --alpha 0.05 --power 0.95 --ratio 1`)

| Girdi | `.venv\Scripts\gpower-clone.exe` | `uv run --no-sync gpower-clone` | süreç içi `engine.run` |
|---|---|---|---|
| `--d 0.001` (→ 25 989 420 / 25 989 420) | 97–112 ms | 132–142 ms | 3.6 ms |
| `--d 0.0000000001` (→ NO_SOLUTION, çıkış 1) | 98–103 ms | 156–179 ms | 3.5 ms |
| `--d 0.5` (karşılaştırma) | 103–108 ms | 126–137 ms | — |

`--d 0.00001` (N ≈ 5.2e11) süreç içi 3.4 ms. 2 s sınırının çok altında; köşeleme en fazla ~42 ikiye katlama + Brent.

## Revizyon 2 — SPEC'in ikinci farkı (`git diff -- SPEC.md`, binary kanıtı eklendi)

Revizyon 1'deki `N > 1e13 → NO_SOLUTION` ve `⌈x − 1e-9⌉` kararları **bu bölümle geçersizdir**.

### Ne değişti

- **Çift toplam yuvarlaması (SPEC §3.1 adım 3).** `x = N*/2`, `N = max(4, 2·⌈⌊x·10¹⁰ + 0.5⌋ / 10¹⁰⌉)`. Yardımcı `_round_digits(x, k) = ⌊x·10^k + 0.5⌋ / 10^k`; aynı fonksiyon `k = 0` ile bölmede de kullanılıyor (adım 4).
- **Bölme (adım 4, 4b).** `n1 = ⌊N/(1+ratio) + 0.5⌋`, `n2 = ⌈N − n1⌉`; `|ratio − 1| < 1e-8` ve `n1 ≠ n2` ise küçük gruba 1 eklenir (çift N'de etkisiz, SPEC gereği uygulandı); `n_total = n1 + n2`.
- **Üst sınır yok.** `N_MAX` kaldırıldı. Üst uç taşma olana kadar ikiye katlanır; `NO_SOLUTION` yalnızca üst uç sonsuz olursa, güç NaN olursa ya da yuvarlanan kök sonlu değilse. Brent toleransı `xtol = 1e-12`, `rtol = 1e-15`. Mesaj: "a-priori: sayısal taşma; gerekli örneklem büyüklüğü hesaplanamadı".
- **Yeni doğrulama (SPEC §2.8, yalnızca a-priori).** `d < 0.00001` → `OUT_OF_RANGE`, field `d`, mesaj "Aralık dışı değer: A-priori analizde etki büyüklüğü 0.00001'den küçük olamaz". `d = 0.00001` geçerli. Denetim tablo sırasında `d`'nin yerinde yapılır (ör. `d = 1e-10, ratio = 0` → `d` raporlanır). `d ≤ 0` eski mesajı alır. post-hoc/compromise vb. küçük d'yi kabul etmeye devam eder.
- **Testler.** `test_validation.py`: d = 1e-10, 9.9999e-6, 9e-6, 1e-300 → `OUT_OF_RANGE d`; tablo sırası; d = 1e-5 (metin, `1e-5`, JSON float) geçerli; post-hoc ve compromise'da d = 1e-10 geçerli; a-priori `NO_SOLUTION` testi kaldırıldı (d ≥ 1e-5 iken taşmaya ulaşan geçerli girdi bulunamadı; en uç: d = 1e-5, α = 1e-300, güç 0.999999, ratio 0.01 → N = 1 782 403 921 929 216, 3.6 ms). `test_cli.py`: `--d 0.0000000001` artık çıkış 2; `--d 0.00001` ve yukarıdaki en uç girdi eklendi.

### Belirsizlik / çelişki: d = 0.00001 (ve d = 0.0001) G*Power değeri

SPEC §9 "Sınır değerler" tablosunda `--d 0.00001 --tails 2 --alpha 0.05 --power 0.95 --ratio 1 → n_total 519812041146` bekleniyor. Motor **519 788 363 790** veriyor; bu Gherkin satırı (ve diferansiyel testte V43, V44) kalıyor. Bunu yalnızca SPEC'ten giderebilecek bir kural bulamadım:

- SPEC §1 formülleriyle `N = 519 812 041 146`'da güç 0.9500085, `N = 519 788 363 790`'da 0.9500000000002. Bağımsız denetim: df ≈ 5e11'de merkezî olmayan t, N(δ, 1)'e 1/df ≈ 2e-12 içinde yakınsar; normal yaklaşımla (`Φ(δ − z) + Φ(−δ − z)`) motorun N'sindeki güç 0.95000000000085, `critical_t` ile `z₀.₉₇₅` farkı 4.6e-12 (beklenen `z(1+z²)/(4df)`). Yani motorun kökü SPEC §1 matematiğine ~1e-12 içinde uyuyor.
- Diferansiyel testin mesajına göre G*Power kendi N'sinde gücü 0.9500402 raporluyor; §1 formülleri aynı N'de 0.9500085 veriyor. G*Power'ın kendi kökünde güç ≈ 0.95 olması gerekirken bir tam sayı ötede 4e-5 fark etmesi, G*Power'ın güç fonksiyonunun df ≈ 5e11'de **sayısal olarak gürültülü** olduğunu gösteriyor (bağıl hata d = 0.001'de görünmez, d = 0.0001'de ~1.3e-7, d = 0.00001'de ~4.6e-5; yani hata kabaca df ile büyüyor, `x = df/(df+t²)` gibi 1'e yakın bir büyüklükte iptal kaybına benziyor — bu yalnızca bir tahmin).
- Bu değeri 12 basamak tutturmak için G*Power'ın büyük-df sayısal yolunun (kritik t ve nct CDF'yi hangi ara büyüklükle, hangi toleransla hesapladığı) birebir bilinmesi gerekir; SPEC bunu tanımlamıyor ve §1.1 "her çıktı ondalığı bağımsız kâhine karşı ≤ 1e-9" diyor. Bu iki gereksinim bu girdide birbirleriyle çelişiyor. Karar: SPEC §1/§1.1 matematiği korundu; tek bir veri noktasına özel düzeltme eklenmedi. İnceleme oturumunun bu satırı ya kaldırması/işaretlemesi ya da G*Power'ın büyük-df hesabını soyut bir kural olarak SPEC'e eklemesi gerekiyor.
- Aynı nedenle SPEC §3.1 metnindeki d = 0.0001 değeri (2 598 942 504 / grup) da tutmuyor; motor 2 598 941 820 / grup veriyor (Gherkin'de yok, diferansiyelde V43).

### Test sayıları (`uv run pytest -q`)

Toplam **1301 geçti, 3 kaldı**: `test_spec_gherkin.py::test_gherkin_example[20]` (d = 0.00001 satırı) ve `test_differential.py::test_gpower_vector[V43]`, `[V44]` (d = 0.0001 / 0.00001). Revizyon 1'de kalan statsmodels ölçek vektörleri ve V01, V03, V33 artık geçiyor (karşılaştırıcı inceleme tarafında güncellenmiş).

| Dosya | Sonuç |
|---|---|
| `test_spec_gherkin.py` | 42 geçti, 1 kaldı (yukarıda) |
| `test_invariants.py` | 268 geçti |
| `test_validation.py` | 96 geçti |
| `test_cli.py` | 22 geçti |
| `test_mcp_equivalence.py` | 2 geçti |
| `test_numerics_oracle.py` | 72 geçti |
| `test_public_vectors.py` | 31 geçti |
| `test_agent.py` | 3 geçti |
| `test_differential.py` | 765 geçti, 2 kaldı (V43, V44) |

### Zamanlamalar (5 çalıştırma, `--tails 2 --alpha 0.05 --power 0.95 --ratio 1`)

| Girdi | `.venv\Scripts\gpower-clone.exe` | `uv run --no-sync gpower-clone` | süreç içi |
|---|---|---|---|
| `--d 0.001` | 99–104 ms | 134–143 ms | 3.2 ms |
| `--d 0.00001` | 98–105 ms | 131–146 ms | 3.2 ms |
| `--d 0.0000000001` (OUT_OF_RANGE, çıkış 2) | 96–102 ms | 127–132 ms | 0.01 ms |
