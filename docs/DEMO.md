# 60 saniyelik CLI demosu — çekim senaryosu

Terminal: proje klasöründe PowerShell. Yazı tipini büyüt (Ctrl + fare tekerleği). Kayıt: `Win + Alt + R` (Xbox Game Bar) ya da OBS.

| Süre | Komut | Ne gösterir |
|---|---|---|
| 0–8 s | `uv run gpower-clone --version` | Sözleşme sürümü, tek satır JSON |
| 8–20 s | `uv run gpower-clone --test t2-indep --mode a-priori --tails 2 --d 0.5 --alpha 0.05 --power 0.95 --ratio 1` | 105 / 105: G*Power ile birebir |
| 20–32 s | `uv run gpower-clone --test t2-indep --mode a-priori --tails 2 --d 0.3 --alpha 0.01 --power 0.9 --ratio 0.7` | 404 / 282: binary'den bulunan "çift toplam" kuralı, güç hedefin biraz altında (G*Power da aynısını veriyor) |
| 32–40 s | `uv run gpower-clone --test t2-indep --mode post-hoc --tails 2 --d 0,5 --alpha 0.05 --n1 88 --n2 88` | Virgüllü sayı → hata JSON'u, `INVALID_VALUE` |
| 40–60 s | `uv run pytest -q` | 1304 test geçiyor (G*Power diferansiyel testi dahil) |

Konuşma (isteğe bağlı): "G*Power'ın iki bağımsız ortalama hesabını Ghidra ile söktük, kanıtladık, temiz odada yeniden yazdık. Ajanlar artık ekran görüntüsü yerine tek satırlık bir komutla aynı sonucu alıyor."

Videoyu YouTube'a "Liste dışı" ya da Google Drive'a "Bağlantıya sahip herkes görüntüleyebilir" ayarıyla yükle ve bağlantıyı README'deki "Demo" satırına ekle.
