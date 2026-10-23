# Kanıt defteri — `t2-indep` (REA)

**Referans:** G*Power 3.1.9.7 (Windows) · t tests – Means: Difference between two independent means (two groups)
**Yöntem:** Kara kutu gözlemi. G*Power'a kontrollü girdiler verilir, "Protocol of power analyses" sekmesindeki çıktı kopyalanır ve ekran görüntüsü `rea/kanit/` altına konur. Kaynak koda bakılmaz, decompile yapılmaz, GPower.exe repoya konmaz.

Etiketler:
- `[REA]` — G*Power'da **bizim gözlediğimiz**, kılavuzda yazmayan davranış. Her girdide: deney kimliği, G*Power girdileri, protokol çıktısı (7 basamak), ekran görüntüsü yolu.
- `[REA-HİPOTEZ]` — dolaylı kanıta dayanan çıkarım; ayırt edici deney tanımlı, gözlem bekleniyor.
- `[SÖZLEŞME-KANIT]` — eğitmenin G*Power protokol kayıtlarından alınan açık vektörler.

Deneylerin girdileri ve iki hipoteze göre beklenen sonuçlar: [experiments.jsonl](experiments.jsonl). Gözlemler `observations.jsonl`'a işlenir ve `python rea/check_observations.py` motoru bunlarla karşılaştırır.

---

## R-01 · Temel formüller açık vektörleri tutturuyor `[SÖZLEŞME-KANIT]`

- **Kanıt:** CONTRACT §9'daki 5 `t2-indep` vektörü (tek kuyruk, d = 0.5, n1 = n2 = 88).
- **Gözlem:** `ncp = d·√(n1n2/(n1+n2))`, `df = n1+n2−2`, `tc = t⁻¹(1−α/tails)`, güç = merkezî olmayan t'nin `tc` üstündeki kütlesi. Beş moddaki bütün ondalıklar 1e-9'dan küçük farkla tutuyor (`tests/test_public_vectors.py`).
- **Sonuç:** Hesap çekirdeği doğru. Tek kuyrukta belirsizlik yok. Çift kuyruk, eşit olmayan oran ve sınırlar bu vektörlerle **sınanmıyor**; aşağıdaki deneyler onlar için.

## H-01 · Eşit olmayan oranda n1/n2 her grup ayrı yuvarlanır `[REA-HİPOTEZ]` → deney E-01…E-06

- **Neden önemli:** Kapı (%90 N tam eşleşme) doğrudan buna bağlı. Kılavuz yuvarlama kuralını yazmıyor.
- **Dolaylı kanıt:** G*Power kılavuzunun iki grup örneğinde (Fisher exact) ratio = 2 iken "N = 443 (148 and 295)". 2 × 148 = 296 ≠ 295. Demek ki n2, n1'in tam sayı katı değil; sürekli çözüm `n1*` için `n1 = ⌈n1*⌉`, `n2 = ⌈ratio·n1*⌉`.
- **Rakip hipotez A:** En küçük tam sayı n1 aranır, `n2 = ⌈ratio·n1⌉`.
- **Ayırt edici deneyler:**

| Deney | Girdi | Hipotez B (seçilen) | Hipotez A |
|---|---|---|---|
| E-01 | 1 kuyruk, d 0.5, α .05, güç .95, ratio 3 | 59 / 175 (N 234) | 59 / 177 (N 236) |
| E-02 | 2 kuyruk, d 0.5, α .05, güç .80, ratio 1.5 | 54 / 80 (N 134) | 53 / 80 (N 133) |
| E-03 | 2 kuyruk, d 0.8, α .05, güç .80, ratio 0.25 | 63 / 16 (N 79) | 61 / 16 (N 77) |
| E-04 | 2 kuyruk, d 0.3, α .01, güç .90, ratio 0.7 | 404 / 283 (N 687) | 403 / 283 (N 686) |
| E-05 | 2 kuyruk, d 0.5, α .05, güç .80, ratio 2 | 48 / 96 (N 144) | 48 / 96 |
| E-06 | 1 kuyruk, d 0.5, α .05, güç .95, ratio 0.5 | 131 / 66 (N 197) | 131 / 66 |

- **Gözlem:** _(G*Power'da çalıştırıp buraya ve observations.jsonl'a yazın)_
- **Karar:** _(B tutarsa H-01 → `[REA]`. A tutarsa SPEC §3.1 güncellenir ve yazım oturumu yeniden çalıştırılır.)_

## H-02 · Çok büyük etkide alt sınır `[REA-HİPOTEZ]` → E-07, E-08

- Kılavuz, G*Power'ın en küçük grup büyüklüğünü yazmıyor.
- Hipotez: arama `n1 ≥ max(2, 2/ratio)` noktasından başlar; her grup en az 2.
- E-07: 2 kuyruk, d 5, α .05, güç .80, ratio 1 → beklenen 3 / 3.
- E-08: 2 kuyruk, d 10, α .05, güç .80, ratio 1 → beklenen 2 / 2.
- **Gözlem:** _(bekleniyor)_

## H-03 · Çift kuyrukta güce iki kuyruk da eklenir `[REA-HİPOTEZ]` → E-09, E-10

- Bazı araçlar çift kuyrukta yalnızca üst kuyruğu sayar. Fark küçük d ve küçük n'de görünür.
- E-09: post-hoc, 2 kuyruk, d 0.1, α .05, n1 10, n2 10 → iki kuyruk sayılırsa güç 0.0551613; yalnız üst kuyruk sayılırsa 0.0402359.
- E-10: sensitivity, 2 kuyruk, α .05, güç .80, n1 20, n2 30.
- **Gözlem:** _(bekleniyor)_

## H-04 · Çok küçük etkide üst sınır `[REA-HİPOTEZ]` → E-11

- E-11: a-priori, 2 kuyruk, d 0.001, α .05, güç .95, ratio 1 → yaklaşık n1 = n2 ≈ 26 milyon. G*Power sonuç mu veriyor, hata mı?
- Biz `n1* > 1e7` durumunda `NO_SOLUTION` döndürüyoruz. **Gözlem bu sınırı değiştirebilir.**

## H-05 · Güç ≤ α reddedilir `[REA-HİPOTEZ]` → E-12, E-13

- E-12: a-priori, 1 kuyruk, d 0.5, α .05, **güç .04**, ratio 1. Beklenen: G*Power hata verir / hesaplamaz.
- E-13: sensitivity, 2 kuyruk, α .05, güç .05, n1 20, n2 20.
- Bizim davranış: `INCONSISTENT`, field `power`.

## H-06 · Uç oran `[REA-HİPOTEZ]` → E-14

- E-14: a-priori, 2 kuyruk, d 0.5, α .05, güç .80, **ratio 0.05**. Hipotez B'ye göre n2 küçük ama ≥ 2 olmalı.

## H-07 · Çift kuyrukta criterion ve compromise `[REA-HİPOTEZ]` → E-15, E-16

- E-15: criterion, 2 kuyruk, d 0.5, güç .80, n1 30, n2 45.
- E-16: compromise, 2 kuyruk, d 0.5, β/α 4, n1 30, n2 45.

---

## Gözlem nasıl kaydedilir

1. G*Power → Test family **t tests** → Statistical test **Means: Difference between two independent means (two groups)** → Type of power analysis.
2. Girdileri `experiments.jsonl`'daki gibi gir, **Calculate**.
3. `rea/kanit/E-xx.png` adıyla ekran görüntüsü al (Windows: `Win+Shift+S`).
4. "Protocol of power analyses" sekmesindeki metni kopyala ve `observations.jsonl`'a şöyle bir satır ekle:

```json
{"id": "E-01", "observed": {"ncp": 3.3, "critical_t": 1.65, "df": 232, "n1": 59, "n2": 175, "n_total": 234, "actual_power": 0.95}, "screenshot": "rea/kanit/E-01.png", "note": ""}
```

G*Power hata verirse: `{"id": "E-12", "observed": {"error": "<G*Power'ın mesajı>"}, "screenshot": "..."}`.

5. `python rea/check_observations.py` → hangi hipotezin tuttuğunu yazdırır.
