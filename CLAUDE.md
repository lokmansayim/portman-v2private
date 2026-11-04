@AGENTS.md

# Claude Code · oturum akışı

Ortak kurallar yukarıdaki `AGENTS.md`'den gelir; burada yalnız Claude'a özgü akış var. Hook, izin, skill ve hakem yüklenmeyen oturumlarda (project thread'i) aynı frenler `.claude/rules/frenler.md`'de metin olarak durur; o dosya her oturumda yüklenir.

## Oturum başında

1. **Güncel durumu ve aktif işi oku.** `docs/durum/`'daki en yeni ekler (dosya adı tarih-saatle başlar, en yenisi en sonda) nerede kalındığını, aktif işi ve dalı söyler; o dala geç. `main`'e girmemiş ekler açık iş dallarındadır (`git fetch` sonrası `git ls-tree --name-only origin/<dal> docs/durum/`). 28 Ekim 2026'dan önceki durum `DURUM.md`'dedir. `docs/devir/`'in en yeni notu 16 Ekim 2026 tarihlidir ve güncel değildir; devir notu yalnız pencere değişirken yazılır.
2. **Ortamı kur:** `bash araclar/ortam_kur.sh` (gerileme için `--dogrula`).
3. **Yeni işe Plan modunda başla.** Plan Lokman'ın onayından sonra uygulanır; iş emri belgesi `/is-emri` ile açılır. Diff'i tek cümleyle anlatılabilen küçük düzeltmelerde plan atlanabilir. Project thread'inde plan modu yoktur: plan CIO'ya gider, CIO kurallarla kıyaslayıp başlatır; Lokman'a sonuç, birleştirme, canlı, ücretli deneme, silme ve gerçek karar gider (Lokman, 27 Ekim 2026 18:12, CIO'nun önerisine: "Evet öyle yapalım").
4. **Üretim kuralı (D-28, `AGENTS.md`).** Bayiye, mühendise ya da Lokman'a gidecek bir çıktıyı (çizim, liste, rehber, teklif) yalnız `main`'e girmiş kodla üret. Oturumun kendi betiğiyle, proje dosyalarındaki bir araçla ya da elle düzeltilmiş çıktı teslim edilmez; eksik varsa önce kod düzeltilir. Hedef örnek ve kıyas testi yoksa o çıktı için "çalışıyor" yazılmaz.
5. **Lokman'a anlatım.** Her adımda ne yapıldığı iki cümleyle Türkçe söylenir; onayı gereken yerde tek soru sorulur; beklemeye düşülmez, kendi başına devam edilir.

## Lokman'la çalışma düzeni

Notion › "Claude ile Çalışma Düzeni · Devir Notu ve Tarama Kaydı" (30 Ekim 2026), çalışma kuralları, birebir:

> Motto: Bir oturum, bir iş. Kural dosyada, kanıt gözümün önünde, karar bende.
>
> 1. Her oturum işe başlamadan önce dosyadaki kuralları ve durumu okur. Ezberden yazmaz.
> 2. Tek seferde tek iş, tek proje.
> 3. Sonucu gösterir: çizim, sayılar, gerçek listeyle farklar. "Geçti" demez; kararı Lokman verir.
> 4. Kural yoksa ya da çelişki varsa uydurmaz, tek cümleyle sorar.
> 5. Lokman'ın verdiği örnekler kural değildir. Kural gerçek proje verisinden çıkar.
> 6. Bir konu açılınca önce dünya taraması yapar: kim yapmış, hazırda ne var, bize ne kalır. Lokman'ın bilmediği seçenekleri kendisi getirir; yalnızca onun söylediği eksende dönmez. Bu sayfada kayıtlı bir tarama tekrar yapılmaz.
> 7. Konu dışına çıkmaz, yan konu açmaz.
> 8. Projelere kodla değil gerçek adla hitap eder.
> 9. Bağlam ağırlaşınca bunu kendisi söyler. Bir sohbet = bir konu. Önemli olan her şey dosyada durur.

Aynı sayfa, soru 15: "AP-01…AP-28 = Mac'teki Desktop/AIPrefabrik klasörünün alfabetik sırası … Konuşurken gerçek ad kullanılır." Adlı eşleme depoya ve paylaşılan klasöre girmez (`docs/notlar/2026-10-18_AIPrefabrik_muhur.md`, `docs/notlar/2026-10-25_AICelik_muhur.md`).

## Komutlar (skill)

| Komut | Ne yapar |
|---|---|
| `/is-emri <KOD> <başlık>` | Dal + iş emri belgesi + plan; onay için durur |
| `/kapanis` | Doğrulama → kanıt → DURUM → commit/push → `/code-review` → PR özeti |
| `/sahip-ozeti` | Lokman için 10 satırlık durum: canlıda ne var, bekleyen onaylar, açık riskler |
| `/atolye <KOD> <istek>` | Model atölyesi (İE-09): kart, tanım, çizim, kontrol sayfası, düzeltme, kabul, gün sonu |

Komut yüklenmiyorsa (project thread'i) `.claude/skills/<ad>/SKILL.md` okunur ve adımları sırayla uygulanır.

Hakem (`.claude/agents/`): `geometri-hakemi` (Motor/İş Emri değişikliklerini kurallara karşı inceler); kapanışta Motor, İş Emri ya da `beyin/varyant.py` değiştiyse koşturulur. Ajan yüklenmiyorsa dosyanın metni diff'le birlikte `general-purpose` ajana verilir. `kvkk-denetcisi` ve KVKK denetimi 28 Ekim 2026'da Patron kararıyla kaldırıldı (D-13, BK-17): kapanışta kişisel veri denetimi yok. Sır taraması `dogrula.py`'dedir (CI'da da koşar); yerel Claude Code'da ayrıca `sir_koruma.py` hook'u. `AGENTS.md`'deki maskeleme maddesi D-33'le durur.

## Frenler

Hook'lar (`.claude/settings.json`) yalnız o dosyayı okuyan yerel Claude Code'da çalışır; project thread'inde yüklenmez (4 Kasım 2026 denetimi). Orada aynı kurallar `.claude/rules/frenler.md`'dedir ve commit'ten önce `python3 araclar/fren.py` koşulur. Son kapı CI'dır: `Doğrulama sonucu` (mühür kilit testi dahil) ve `Korunan dosya onayı` (korunan dosya değişiyorsa Lokman'ın `patron-onayi` etiketi; oturum bu etiketi eklemez).

- `sir_koruma.py` — sır ve canlı durum dosyaları ile dondurulmuş kayıtlar düzenlenemez; sır içeren yazım engellenir; telefon numarasına benzeyen içerik sorar.
- `komut_koruma.py` — `ssh/scp/sftp/rsync`, `vps_komut`, `main`'e push ve zorla push engellenir; `main`'deyken birleştirme engellenir; silme, ağ ve veritabanı komutları sorar.
- `hizli_kontrol.py` — her `.py/.sh/.json` düzenlemesinden sonra sözdizimi denetimi; hata varsa düzeltmeden devam edilmez.
- `muhur_koruma.py` — mühürlü konular (`AGENTS.md` › Mühürlü konular, `KARARLAR/muhurlu.json`): oturum başında listeyi okutur; mühürlü bir kilidi değiştiren düzenleme ve komut "Patron onayı gerekir" diye engellenir; komuttan sonra kilitler denetlenir; mühür açma (`ac`) Lokman'a sorar.

Hook'lar talimat değil koddur: kuralı yorumlayarak aşılamaz. Bir hook'u, `araclar/fren.py`'yi ya da CI iş akışını değiştirmek ya da kapatmak Lokman'ın onayını gerektirir.

## Commit ve dal

- **Commit kimliği:** `git -c user.name="Claude" -c user.email="noreply@anthropic.com" commit`. Mesajın sonuna oturumun verdiği Co-Authored-By ve Claude-Session satırları eklenir.
- **Push.** Oturum sonunda izlenmeyen dosyalar da commit'lenip iş dalına push edilir.
- **Dallar.** Her iş emrinin kendi dalı olur. `main`'e birleştirme yalnız Lokman'ın açık onayıyla yapılır.
- **Onaylı PR (D-43).** Lokman bir PR'a birleştirme onayı verdiyse o PR'ın sohbeti, `Doğrulama sonucu` ve `Korunan dosya onayı` yeşil olunca beklemeden birleştirir (merge commit) ve sonucu tek satırla bildirir; kırmızıda kendisi düzeltir, toplu gönderir, yeniden koşturur. Onay PR'a özgüdür; onaysız PR'da birleştirme Lokman'a açıkça sorulur. Canlı, ücretli deneme, silme ve mühürlü konular bu kararın dışındadır.
- **Oturum sonu.** Her oturumun son adımı `docs/durum/`'a tarihli bir ek dosyası yazmaktır (`/kapanis` bunu yapar); `DURUM.md`'ye ek yazılmaz (her PR aynı satırları değiştirdiği için çakışıyordu). Pencere değişecekse `docs/devir/`'e bir not yazılır.

## Yerler

- **Mac çalışma klasörü:** `~/Desktop/Claude Portman Çalışması/`, numaralı klasörler.
  - Kapı çıktıları, yedekler, aday paketleri ve Astra'nın çizimleri (`24_Astra_Cizimler/`) orada durur.
  - Kökteki `DURUM.md` 23.09 tarihlidir ve güncel değildir; güncel durum depodadır.
- **Zemin (Claude Docs):** belge `65844cef-e6c5-4a5d-b714-ee003c57fe5b`. "Güncel durum" sekmesi durumlarla birlikte güncellenir.
- **Hedef WhatsApp Akışı (Design kanvası):** https://claude.ai/artifact/478avu6uRTg3tP7q8A3qoL.
