# Temiz oda süreci ve doğruluk kanıtı

## İki oturum

| | İnceleme (REA) oturumu | Yazım oturumu |
|---|---|---|
| Gördüğü | G*Power davranışı (kara kutu), kılavuz, yayınlar, CONTRACT.md | **Yalnızca** `SPEC.md` + `CONTRACT.md` |
| Ürettiği | `SPEC.md`, `LEDGER.md`, `rea/experiments.jsonl`, `oracle/`, `tests/differential.py`, `tests/test_spec_gherkin.py` | `src/`, `tests/`, `pyproject.toml`, `docs/IMPLEMENTATION_NOTES.md` |
| Görmediği | — | G*Power, `rea/`, inceleme betikleri |

- Yazım oturumu sıfır bağlamla başlatıldı; verilen istem birebir [prompts/2-yazim-oturumu.md](../prompts/2-yazim-oturumu.md)'de.
- Git geçmişi sırayı gösterir: önce inceleme commit'i (SPEC + kanıt defteri), sonra uygulama commit'i.
- Teslim edilen kodda decompile çıktısı yok, GPower.exe yok (`.gitignore` `*.exe`'yi de dışlar).
- REA bulgusu SPEC'i değiştirirse (örn. H-01 yanlış çıkarsa): inceleme oturumu SPEC'i günceller, yazım oturumu yalnızca SPEC farkıyla yeniden çalışır.

## "Söktüğümüz şeyin doğru olduğunu nasıl kanıtlarız?"

Tek bir test yetmez; birbirinden bağımsız beş katman var. Her biri farklı türde bir hatayı yakalar.

1. **Kâhin karşılaştırması (G*Power'ın kendisi).** Açık 25 vektör + bizim `rea/observations.jsonl`'a işlediğimiz G*Power gözlemleri. Tamsayılar birebir, ondalıklar 1e-6 içinde. Bu, "G*Power ne yapıyorsa onu yapıyor muyuz?" sorusunun tek doğrudan kanıtı. Gözlemler regresyon testine dönüşür.
2. **Ayırt edici deneyler.** Rastgele girdi değil, rakip hipotezlerin **farklı** sonuç verdiği girdiler seçildi (örn. ratio = 3'te hipotez B 59/175, hipotez A 59/177 der). Böylece bir gözlem bir hipotezi kesin olarak eler. Sadece "tutuyor" demek yetmez; neyin tutmadığını da göstermek gerekir.
3. **Bağımsız sayısal kâhin.** Motor saf Python ile yazıldı (2 s sınırı). Aynı fonksiyonlar bağımsız bir kütüphaneye (SciPy/Boost) karşı geniş bir ızgarada 1e-9 içinde test edilir. Bu, "formül doğru ama sayısal yöntem bazı bölgelerde bozuk" hatasını yakalar (SciPy'nin kendisinin bile bazı noktalarda NaN döndüğünü bu sırada gördük).
4. **Değişmezler (özellik testleri).** Modlar birbirinin tersidir: a-priori'nin N'si post-hoc'a verilince güç ≥ hedef; bir eksik N hedefe ulaşmaz (minimallik); criterion'ın α'sı ve sensitivity'nin d'si post-hoc'tan hedef gücü geri verir; güç d, n ve α'da monoton. Bu testler G*Power'a hiç bakmadan iç tutarsızlığı yakalar.
5. **Katman eşdeğerliği.** CLI ve MCP aynı motoru çağırır ve 25 vektörde bayt bayt aynı çıktıyı verir; ajan hesabı asla kendisi yapmaz, her araç çağrısı `logs/agent_calls.jsonl`'da girdisi ve çıktısıyla kayıtlıdır. Böylece ajanın söylediği her sayı, loglanmış bir motor çağrısına geri izlenebilir.
