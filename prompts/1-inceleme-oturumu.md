# Oturum 1 — İnceleme (REA) oturumunun ilk prompt'u

**Ajan:** Claude Code (masaüstü uygulaması), model Claude Opus 5.5
**Rol:** G*Power'ı inceler; yalnızca `SPEC.md`, `LEDGER.md` (kanıt defteri), deney listesi ve oracle vektör listesi üretir. Motor kodunu bu oturum yazmadı.

İlk prompt (kullanıcının yazdığı, birebir; hocanın ödev duyurusu alıntısı dahil):

---

> Yazılım gerçekleme ve Test dersimizde hocamız bir ödev verdi. Hocanın ödev hakkındaki yazdıklarını atıyorum.
>
> G*Power, klinik araştırmacıların "kaç denek gerekir?" sorusunu yanıtladığı ücretsiz bir araç. Ama yalnızca grafik arayüzü var; ne CLI'si ne API'si var. Bir AI ajanı onu ancak ekran görüntüsü alıp tıklayarak kullanabiliyor ve bu her çağrıda çok token demek.
>
> Bu sprintte G*Power'ın bir hesabını REA ile tersine mühendislikle inceleyecek, kanıtlarıyla belgeleyecek, temiz odada yeniden yazacak ve ajan çağına taşıyacaksınız: önce CLI, isterseniz MCP ve AI ajanı.
>
> Soru: "Ajanın söktüğü şeyin DOĞRU olduğunu nasıl kanıtlarsın?"
>
> TAKIM: En fazla 4 kişi; bireysel çalışma da serbest. Her takım tek bir test ailesi üzerinde çalışır.
>
> PUANLAMA
> Temel (CLI): 85 puan
> Kapı: Gizli vektörlerde N en az %90 oranında tam eşleşmeli. Tutmazsa bonus açılmaz.
> +15 MCP sunucusu: 100 puan
> +10 AI ajanı (MCP üzerinden, doğal dilde): 110 puan
>
> TEMEL KURALLAR
> 1. Puan yalnızca [REA] etiketli kanıtlara verilir. Kılavuzda yazanı değil, kılavuzda OLMAYAN davranışı bulun.
> 2. İki ayrı ajan oturumu: biri inceler, diğeri yalnızca SPEC.md ile yazar.
> 3. Hesap mantığı tek motordadır. CLI, MCP ve ajan bu motoru çağıran ince katmanlardır.
> 4. Teslim edilen kodda decompile çıktısı olmaz. GPower.exe repoya konmaz.
>
> TESLİM: GitHub repo linki
>
> Ayrıntılı yönerge, CLI sözleşmesi ve etik kurallar ekteki dosyada. Ders slaytları ders klasöründe.
>
> \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_
> Ödevin belirli konuları var. Konum şu: t testi, iki bağımsız ortalama (ilaç ve pasebo)
>
> Ayrıca proje dosyamızda CONTRACT.md dosyası var. Bu yazdıklarıma vs bak analiz et ve ödevi yap benim yapmam gereken bir şey varsa söyle ödevi yapmam lazım bitmesi lazım

---

## Oturum içindeki sonraki önemli yönlendirmeler

- Ayrıntılı yönerge (`2026-10-16-odev-supp`) oturumun ortasında eklendi. Bu oturum ilk başta [REA]'yı "G*Power arayüzünde gözlenen davranış" diye yanlış yorumlamıştı (bkz. [HALLUCINATIONS.md](../HALLUCINATIONS.md) H-1).
- Kullanıcı Node.js güncellemesi, Ghidra 12.1.4 ve REA (`rea-agents` 6.7.0) kurulumunu onayladı. Binary incelemesi REA + Ghidra ile bu oturumda yapılır.
- Yazım oturumu ayrı ve sıfır bağlamla başlatıldı; prompt'u [2-yazim-oturumu.md](2-yazim-oturumu.md).
