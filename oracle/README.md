# oracle/ — G*Power kâhin vektörleri

Kâhin G*Power'ın kendisidir. Buradaki her vektör G*Power 3.1.9.7 (Windows) arayüzünden elle toplanır ve ekran görüntüsüyle belgelenir.

| Dosya | İçerik |
|---|---|
| `vectors_todo.csv` | Toplanacak 33 vektörün girdileri ve amacı (sınır değerler, eşit olmayan oran, geçersiz girdi) |
| `screenshots/Vxx.png` | Her vektörün G*Power ekran görüntüsü |
| `gpower_vectors.csv` | Ekran görüntülerinden aktarılan G*Power çıktıları (7 basamak) |
| `scale_vectors.csv` | statsmodels ile üretilen 500+ ölçek vektörü (kesirli N; yuvarlama farkı bir bulgudur) |

## Bir vektör nasıl toplanır

1. `GPowerNT.exe`'yi aç.
2. **Test family:** `t tests` · **Statistical test:** `Means: Difference between two independent means (two groups)`.
3. **Type of power analysis:** satırdaki `mode` değerine göre seç:
   - `a-priori` → *A priori: Compute required sample size – given α, power, and effect size*
   - `post-hoc` → *Post hoc: Compute achieved power – given α, sample size, and effect size*
   - `sensitivity` → *Sensitivity: Compute required effect size – given α, power, and sample size*
   - `criterion` → *Criterion: Compute required α – given power, effect size, and sample size*
   - `compromise` → *Compromise: Compute implied α & power – given β/α ratio, sample size, and effect size*
4. Girdileri yaz: `Tail(s)` = One/Two, `Effect size d`, `α err prob`, `Power (1-β err prob)`, `Allocation ratio N2/N1`, `Sample size group 1/2`, `β/α ratio`. **Ondalık ayırıcı nokta olmalı** (G*Power virgülü farklı yorumlayabilir; ekranda girdinin doğru göründüğünü kontrol et).
5. **Calculate**.
6. Pencerenin tamamının ekran görüntüsünü al (`Win+Shift+S`) ve `oracle/screenshots/V01.png` gibi kaydet.
7. G*Power hata ya da uyarı verirse, o pencerenin de ekran görüntüsünü al (`V32.png` gibi).

Sayıları elle yazmana gerek yok: ekran görüntülerinden `gpower_vectors.csv`'yi ajan oluşturur, sen yalnızca kontrol edersin.
