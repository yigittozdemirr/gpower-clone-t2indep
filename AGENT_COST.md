# AGENT_COST.md — Ajan maliyeti ve süreç günlüğü

## Kullanılan ajanlar

| Oturum | Ajan / model | Görev |
|---|---|---|
| 1 · İnceleme | Claude Code (masaüstü), Claude Opus 5.5 | Ödev analizi, hipotez betikleri, SPEC.md, LEDGER.md, deney listesi, kurulumlar (Node, Ghidra, REA), oracle listesi, diferansiyel test, belgeler; binary incelemesi (REA + Ghidra) |
| 2 · Yazım (temiz oda) | Claude Code alt ajanı, sıfır bağlam, Claude Opus 5.5 | Yalnızca SPEC.md + CONTRACT.md ile motor, CLI, MCP, ajan katmanı ve 419 test |
| Ürün ajanı | `gpower-clone-agent`, varsayılan `claude-sonnet-5-5` | Hekimin Türkçe sorusunu MCP aracıyla yanıtlar. **Canlı çalıştırılmadı:** API ücretli, anahtar alınmadı. |

## Ölçülen tüketim

| Oturum | Token | Araç çağrısı | Süre | Kaynak |
|---|---|---|---|---|
| 2 · Yazım | 284 752 | 61 | 29 dk 53 s | Alt ajan bitiş bildirimi (`subagent_tokens`, `tool_uses`, `duration_ms`) |
| 2b · Yazım, SPEC revizyonu 1 | 152 545 | 28 | 8 dk 41 s | Alt ajan bitiş bildirimi |
| 2b · Yazım, SPEC revizyonu 2 | 186 733 | 40 | 13 dk 54 s | Alt ajan bitiş bildirimi (aynı oturum, kümülatif) |
| 1 · İnceleme (tamamı) | ~679 000 bağlam penceresi (mesajlar ~592 k) | yüzlerce | ~4,5 saat (iki gün içinde, bir kullanım limiti kesintisiyle) | Uygulamanın bağlam ölçümü (teslim anı) |

- Abonelik: Claude **Pro**. Çalışma sırasında 5 saatlik kullanım sınırı bir kez doldu ve iş yarıda kesildi; haftalık sınırın ~%25'i kullanıldı. Ajanlı geliştirmede asıl darboğaz kullanım sınırı oluyor.
- Maliyet: Pro abonelik sabit ücretli olduğu için bu çalışmanın ek bir para maliyeti yok. API ile yapılsaydı maliyeti token sayısı × güncel liste fiyatı ile hesaplanmalı. Fiyatı ezberden yazmıyoruz.
- Ürün ajanının soru başına token ve süre ölçümü ücretli API gerektirdiği için yapılmadı; düzenek `eval/run_eval.py`'de hazır.

## İterasyonlar

1. İnceleme: CONTRACT okundu → formüller SciPy ile açık 5 vektöre karşı doğrulandı (1e-9) → eşit olmayan oran için iki rakip hipotez çıkarıldı (A/B), ayırt edici deneyler seçildi → SPEC.md.
2. Ölçüm: `import scipy.stats` = 2.1 s > 2 s sınırı → SPEC "saf stdlib" kararını içerdi.
3. Yazım: 1 tur, 61 araç çağrısı, 24 SPEC belirsizliği raporlandı (docs/IMPLEMENTATION_NOTES.md §4).
4. Doğrulama: 419 test; inceleme oturumunun 16 deney tahmini motorla birebir; ek yönergedeki örnek (105/105) birebir.
5. Yönerge güncellemesi: `[REA]` yeniden yorumlandı (HALLUCINATIONS H-1) → teslim yapısı yeniden düzenlendi, Gherkin, 600 statsmodels vektörü, S257 kâhin hatası bulundu.
6. G*Power arayüzü otomasyonu (pywinauto): 45 + 120 vektör ~4 dakikada toplandı → "her grup ayrı yukarı" kuralı çürütüldü (68/140), "çift toplam" kuralı bulundu (140/140).
7. REA + Ghidra: 8 [REA] bulgusu (LEDGER R-01…R-08), ~35 araç çağrısı; kural binary'de birebir doğrulandı ve iki yeni kural bulundu (10 basamaklı yuvarlama, a-priori d ≥ 1e-5).
8. Yazım oturumu SPEC farkıyla iki kez yeniden çalıştırıldı; sonuç 1304 test, G*Power ile açıklanmamış fark 0.

## Neyi farklı yapardık

- **Önce bütün yönergeyi okumak.** Ayrıntılı yönerge geç fark edildi; H-1 yüzünden kanıt defterinin yapısı bir kez baştan yazıldı. Ajan "eksik belge var mı?" diye sormalıydı: ilk prompt "ekteki dosya" diyordu ve dosya klasörde yoktu.
- **Binary incelemesini erken başlatmak.** Kurulum (Node güncellemesi, Ghidra, JDK, REA) yaklaşık 15 dakika sürdü ve uygulamanın yeniden başlatılmasını gerektirdi. İlk iş bu olmalıydı (yönergede de "KURULUM (ilk iş)" yazıyor).
- **SPEC'e değişmez yazarken onu hemen sınamak.** H-3'teki yanlış değişmez tek satırlık bir kontrolle yakalanabilirdi; temiz odaya taşınmasaydı yazım oturumu zaman kaybetmezdi.
- **Kâhine körü körüne güvenmemek.** SciPy ve statsmodels da yanılıyor (H-4). Her kâhin uyuşmazlığına bir "kim haklı?" testi eklemek baştan plana girmeli.
