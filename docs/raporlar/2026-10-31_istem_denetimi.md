# 31 Ekim 2026 · İstem denetimi (prompt-audit): ajan yapılandırması ve Beyin istemleri

Komut: `/claude-api prompt-audit .` (Claude Code oturumu, dal `claude/elegant-cray-bnb84u`, `main` `98a3dc7` üstünde). Denetim rehberi: Claude API skill'i › `shared/prompt-audit.md`. **Hiçbir dosya değiştirilmedi;** bu rapor ve yanındaki yama (`2026-10-31_istem_denetimi.patch`) öneridir. Uygulama ayrı bir BK iş emri ve Lokman'ın onayıyla.

## 1. Kapsam ve varsayımlar

- **Kapsam:** depo kökünün tamamı (`.`): ajan yapılandırma dosyaları (`CLAUDE.md`, `AGENTS.md`, `.claude/rules/`, `.claude/skills/`, `.claude/agents/`), Beyin'in LLM istemleri, araç tanımları ve istek kurucu kod. `.claude/settings.json` (hook tanımları; sır taşıyabilir) **okunmadı**, yalnız varlığı denetlendi; hook betiklerinden yalnız modele giden iletiler okundu. `CLAUDE.md`'nin depo dışına verdiği adresler (Mac klasörü, Claude Docs belgesi, kanvas bağlantısı) denetlenmedi.
- **Hedef model, yapılandırma dosyaları için:** bu oturumun yapılandırıldığı model (`claude-fable-5-1`). Hakem tanımları kendi modelini pimler (`geometri-hakemi` `model: opus` → Claude Opus 5.5; `kvkk-denetcisi` `model: sonnet` → Claude Sonnet 5.5) ve o modele karşı okundu. Bulguların hepsi ya deponun kendi kendini yalanladığı yerler ya da API düzeyinde belgelenmiş davranışlar; model ailesine göre değişmez.
- **Hedef model, uygulama (Beyin) için:** `claude-opus-5-5` — canlı ayarın modeli (`kanal/ayarlar.py:15,31,35,39`, `vps/kurulum.sh:543,557`; K10, Z-05) ve beş Beyin modülünün `VARSAYILAN_AYAR`'ı.
- **Anthropic dışı sağlayıcı izleri:** `beyin/llm.py` `openai_chat` ve `openai` arka uçlarını da taşır (`gpt-4o-mini`, `temperature: 0`); `docs/kanal/README_KANAL.txt:10` ve K10/Z-05 başlıkları eski gpt-4o-mini dönemini anlatır. Bu yollar **denetlenmedi ve Anthropic'e çevrilmedi**; yamada yalnız `prompt.md`'den taşınan çıktı cümlesi aynen bu dallara eklenir ki davranışları değişmesin.
- **Davranış denemesi yapılmadı.** Her LLM çağrısı ücretli denemedir (AGENTS.md › Ayrı onay gerekenler) ve bu ortamda anahtar yok. Bulgular depo kanıtıyla (yol var mı, komut tanımlı mı, iki dosya aynı şeyi farklı mı söylüyor, `git blame`) ve İE-19'un kayıtlı HTTP 400'üyle doğrulandı. `git blame` için sığ klon `git fetch --deepen` ile tam geçmişe açıldı (1.070 commit).

## 2. Özet

En etkili üç bulgu:

1. **`beyin/llm.py` yalnız tam olarak `"claude-opus-5-5"` yazan modelde doğru yolu seçiyor.** Başka her model adı (ör. `claude-sonnet-5-5`, ileride `claude-opus-5-6`) zorunlu araç seçimine (`tool_choice: tool`), 1.500 `max_tokens`'a ve `effort`'suz isteğe düşüyor; İE-19 bunun Sonnet 5.5'te HTTP 400 verdiğini kaydetti (`docs/is_emirleri/IE-19.md:183`). Üstelik ayar model vermezse varsayılan `claude-haiku-4-5-20251001` (tarihli, eski nesil). Öneri: modele göre dallanmayan tek yol, varsayılan `claude-opus-5-5`, araç açıklaması dolu (Y1, Y2, O1).
2. **Yapılandırma dosyaları depoyu yalanlıyor:** `hosting/` 9 Ekim'de silindi ama `AGENTS.md` tabloda; `kanal-vps.md` canlıyı `v2026.10.15` sayıyor, canlı 17 Ekim'den beri `v2026.10.16`; `motor-cizim.md` BK-09'un kapattığı G1'i "bilinen açık" diye tutuyor; `sahip-ozeti` K16'yı açık karar örneği sayıyor; `kapanis` hâlâ `DURUM.md` diyor (Y3–Y7, Y10).
3. **Komut dosyaları birbirine uymuyor:** `kapanis` tam doğrulamayı `kurallar/` değişince istemiyor, `test-politikasi.md` (daha yeni) istiyor; `geometri-hakemi`ne "salt okunur" denip izlenen `beyin/testler/` dosyalarını yazan `python -m beyin.harness` koşturuluyor (Y8, Y9).

Sayım: **Yüksek 10 · Orta 8 · İşaret (düşük ya da Lokman'ın kararı) 8.** Gruplara göre: Grup 1 (eski model kalıpları) 4 bulgu + 2 işaret; Grup 2 (kırılgan yapılandırma: bayat olgu, çelişki, tarih arkeolojisi) 11 bulgu + 3 işaret; Grup 3 (araç tanımları) 2 bulgu; Grup 4 (istek yapılandırması) 1 bulgu (+ Y1'in API tarafı). Vurgu dili (Grup 1a) yapılandırma dosyalarında yok denecek kadar az: büyük harfli zorlama sözcüğü 13 dosyada toplam 4 ve dördü de tanım cümlesi; bulgu değil.

## 3. Envanter (modele giden her şey)

| Yüzey | Dosyalar |
|---|---|
| Her oturumda yüklenen talimat | `CLAUDE.md` (48 satır; `@AGENTS.md`), `AGENTS.md` (81 satır) |
| Alan kuralları (yol dokununca yüklenir) | `.claude/rules/beyin.md`, `kanal-vps.md`, `motor-cizim.md`, `test-politikasi.md` |
| Komutlar | `.claude/skills/{atolye,is-emri,kapanis,sahip-ozeti}/SKILL.md` |
| Hakemler (alt ajan) | `.claude/agents/geometri-hakemi.md` (opus), `kvkk-denetcisi.md` (sonnet) |
| Frenler | `.claude/hooks/{sir_koruma,komut_koruma,hizli_kontrol}.py` — modele giden iletileri okundu; `settings.json` okunmadı |
| Uygulama sistem istemleri | `beyin/prompt.md` (+ `llm.py:111`'in eklediği araç cümlesi); `beyin/plan_program.py` `PROMPT`, `YENIDEN_PROMPT`; `beyin/plan_islem.py` `PROMPT`; `beyin/gorsel_okuma.py` `PROMPT`, `DUZELTME_PROMPT`; `beyin/degisiklik_okuyucu.py` `PROMPT`; kullanıcı mesajı kurucuları (`_metin`, `_yeniden_metin`, `tablo`, `tablo_metni`, `ornek_ozetleri`) |
| Araç tanımları | `llm.py:112` `talep_kaydet`; `ARAC_ACIKLAMA` × 6 (`plan_program`, `plan_islem`, `gorsel_okuma` × 2, `degisiklik_okuyucu`, `plan_sema`) + `YENIDEN_ACIKLAMA`; şemalar pydantic'ten (`sema.py`, `plan_sema.py`, modüllerin kendi modelleri) |
| İstek kurucu kod | `beyin/llm.py` (`cikar_detayli`, `cikar_guvenli`, `arac_cagir`); ayar varsayılanları `kanal/ayarlar.py`, `vps/kurulum.sh`, beş modülün `VARSAYILAN_AYAR`'ı |
| Few-shot | yok (`ornek_ozetleri` çalışma anında bankadan türetilen veridir, sabit örnek değil) |

## 4. Bulgular — Yüksek

Alanlar: **Yer · Kanıt · Kalıp · Neden bayat · Güven · İşlem.**

**Y1 · `beyin/llm.py:109-122`** — `opus55 = model == "claude-opus-5-5"`; değilse `"tool_choice": {"type": "tool", "name": "talep_kaydet"}`, `max_tokens` 1500, `output_config` yok, araç çağrısı denetimi yok. · Kalıp: Grup 1b/4, zorunlu araç seçimi ve modele göre dallanan istek. · Neden: zorunlu `tool_choice` Opus 5.5 ve Sonnet 5.5'te HTTP 400 (`IE-19.md:183`: "tool_choice: type tool and any are not supported for this model"); düşünmesi açık modellerde 1.500 token düşünme payıyla birlikte sayılır ve kesilir. Dal 29.09'da (commit `6292e29`) yalnız Opus geçişi için eklendi; o günden beri ad eşleşmeyen her model eski yola düşüyor. · Güven: **Yüksek.** · İşlem: **rewrite** — tek yol: `tool_choice auto + disable_parallel_tool_use`, sistem istemine "yalnız bu aracı bir kez çağır", `max_tokens 4096`, `effort` parametresi (varsayılan `low`, eski nesil model için `None`), çağrı denetimi her modelde (yama: `llm.py` @@ -68, -106).

**Y2 · `beyin/llm.py:18`** — `"anthropic": "claude-haiku-4-5-20251001"`. · Kalıp: Grup 4 API fosili / Grup 2 pimli model adı. · Neden: canlı ayar `claude-opus-5-5` (`kanal/ayarlar.py:15`, `vps/kurulum.sh:543`; K10); tarihli snapshot adı eski nesil; `kanal/worker.py:107` ayar model vermezse bu varsayılana düşer ve Y1'in 400 veren yoluna değil ama eski modele gider. Satır 22.09'dan (gpt-4o-mini dönemi) kalma. · Güven: **Yüksek.** · İşlem: **rewrite** → `claude-opus-5-5` (yama: `llm.py` @@ -15).

**Y3 · `AGENTS.md:62`** — `| hosting/ | Hosting'teki canlı dosyaların kayıt kopyası; pakete girmez |`. · Kalıp: Grup 2 bayat yol. · Neden: dizin 9 Ekim 2026'da silindi (commit `762c334`, İE-06 A5: "hosting/PHP kalıntıları kaldırıldı"); `.gitignore`'da değil; `kanal-vps.md:9` da "Hosting'te yalnız web sitesi" diyor. · Güven: **Yüksek.** · İşlem: **remove** (yama: `AGENTS.md` @@ -59).

**Y4 · `AGENTS.md:53`** — "Dondurulmuş referans girdiler (23 dosya)", yalnız dört dizin. · Kalıp: Grup 2 oynak sayı; iki dosya farklı söylüyor. · Neden: `testler/referans/dogrula.py:56-61` `GIRDI_KALIPLARI` ayrıca `kanal/ref_*`, `modeller/*.json`, `kurallar/…` ve `ref_prefabrik/**/*` (26 dosya) içerir; `motor-cizim.md:25` `ref_prefabrik/`'i BK-12 PR-R'den beri referans girdisi sayar; dört dizinde bugün 37 dosya var. · Güven: **Yüksek.** · İşlem: **rewrite** — dizin listesi kalıplarla aynı, sayı yerine kaynağa işaret (yama: `AGENTS.md` @@ -45).

**Y5 · `.claude/rules/kanal-vps.md:25`** — "Canlı: `v2026.10.15` (16.10), `plan_uretimi.acik = true`." · Kalıp: Grup 2 oynak olgu. · Neden: `DURUM.md:340` 17 Ekim'de `v2026.10.16`'nın canlıya alındığını, `DURUM.md:137` 27 Ekim tatbikatının yine `v2026.10.16`'da bittiğini yazar. Kural dosyası canlı durumu taşımamalı; durum eklerinin işi. · Güven: **Yüksek.** · İşlem: **rewrite** → "Canlı sürüm ve açık ayarlar durum eklerinde yazar" (yama: `kanal-vps.md` @@ -22).

**Y6 · `.claude/rules/motor-cizim.md:17`** — "**Bilinen açık (G1 …):** `ciz_genel.zincirler` … sabit 12,5 cm eşikle arar … Düzeltme ayrı küçük PR'da (Lokman, 13.10 16:35 …)". · Kalıp: Grup 2 aynı dosyanın yalanladığı olgu. · Neden: bir alt madde (satır 18, BK-09 / D-16, 14.10) eşiği `ciz_genel.zincir_esigi` ile tanımlar; fonksiyon `motor/genel/ciz_genel.py:90`'da; `test-politikasi.md:13` G1'i kapanmış test olarak sayar. · Güven: **Yüksek.** · İşlem: **remove** (G1 cümleleri; yama: `motor-cizim.md` @@ -14).

**Y7 · `.claude/skills/kapanis/SKILL.md:3`** — description: "… kanıt, DURUM.md, commit/push …". · Kalıp: Grup 2 bayat olgu (komut listesinde her oturum görünür). · Neden: aynı dosyanın 31. satırı ve `CLAUDE.md` › Oturum sonu "DURUM.md'ye ek yazılmaz" der (28 Ekim 2026); `DURUM.md`'nin son commit'i 28 Ekim (`ef00a4f`), `docs/durum/`'da 36 ek var. · Güven: **Yüksek.** · İşlem: **rewrite** → "durum eki (docs/durum/)" (yama: `kapanis` @@ -1).

**Y8 · `.claude/skills/kapanis/SKILL.md:17-18`** — tam doğrulama yalnız "`motor/`, `beyin/` ya da `kanal/` değiştiyse"; hızlı koşu "(~45 sn)". · Kalıp: Grup 2 çelişen talimat dosyaları + sürüklenen kopya. · Neden: `test-politikasi.md:5` (`git blame` 12.10, kapanis satırı 4.10'dan) `kurallar/` değişince de tam doğrulama ister; `kurallar/` değişikliği her iki şıkkın da dışında kalıyor. Süre `AGENTS.md:68`'de ~60 sn. · Güven: **Yüksek** (yön: yeni dosya test-politikasi). · İşlem: **rewrite** — `kurallar/` eklenir, süre AGENTS.md ile aynı (yama: `kapanis` @@ -14).

**Y9 · `.claude/agents/geometri-hakemi.md:20`** — "Gerekirse salt okunur komut koştur (`python -m beyin.harness`, …); dosya değiştirme". · Kalıp: Grup 2 talimat ile depo gerçeğinin çelişmesi. · Neden: `beyin/harness.py:54` `main(rapor_yaz=True)` varsayılanla izlenen `beyin/testler/` dosyalarını yazar; `test-politikasi.md:12` bu yüzden `harness.main(durum_dir=<geçici>, rapor_yaz=False)` ister. Hakem "dosya değiştirme" kuralını kendi komutuyla bozar. · Güven: **Yüksek.** · İşlem: **rewrite** — harness yazmayan çağrıyla (yama: `geometri-hakemi.md` @@ -17).

**Y10 · `.claude/skills/sahip-ozeti/SKILL.md:16`** — "açık kararlar (K16, K3/K4, Z-03/Z-06 vb.)". · Kalıp: Grup 2 oynak örnek listesi. · Neden: K16 11.10'da kapandı (D-08; `KARARLAR/README.md:160` üstü çizili); liste her kapanan kararda bayatlar. · Güven: **Yüksek.** · İşlem: **rewrite** → kaynağa işaret: `KARARLAR/README.md` › "Açık kararlar" (yama: `sahip-ozeti` @@ -13).

## 5. Bulgular — Orta

**O1 · `beyin/llm.py:112`** — araç açıklaması `"Yapılandırılmış talep"` (iki sözcük). · Kalıp: Grup 3 eksik tanım. · Neden: araç açıklaması modelin sözleşmesidir; ne zaman ve kaç kez çağrılır, boş alan ne olur, ne hesaplanmaz yazmıyor; bugün bu bilgi sistem istemine ve şema alan açıklamalarına dağılmış. · Güven: **Orta.** · İşlem: **add** — dört cümlelik sözleşme (yama: `llm.py` @@ -106, Y1 ile aynı parça).

**O2 · `beyin/prompt.md:29`** — "Çıktı yalnız şemaya uyan JSON'dur; başka metin yazma." · Kalıp: Grup 1b, API özelliğinin yerini aldığı JSON zorlama cümlesi. · Neden: satır 22.09'da gpt-4o-mini'nin JSON kipi için yazıldı (`git blame` `d3d18e5`); canlı yolda çıktı araç çağrısıdır ve `llm.py:111` zaten "yalnız talep_kaydet aracını bir kez çağır" ekler: model iki çıktı biçimi talimatını uzlaştırıyor. · Güven: **Orta.** · İşlem: **move** — cümle `prompt.md`'den çıkar, yalnız JSON kipli openai dallarına `JSON_NOTU` olarak eklenir (yama: `prompt.md` @@ -25, `llm.py` @@ -15, -85, -98). Not: `prompt.md` değişince kural gereği harness tam koşulur (`beyin.md`); harness kayıtlı çıkarımlarla koşar, fark beklenmez.

**O3 · `plan_program.py:26`, `plan_islem.py:30`, `gorsel_okuma.py:33,35`, `degisiklik_okuyucu.py:21`, `plan_sema.py:137`** — altı araç açıklaması "… Yalnız bu araçla cevap ver." ile bitiyor. · Kalıp: Grup 3 açıklamaya gömülü davranış yönlendirmesi; Grup 1c yineleme. · Neden: `llm.arac_cagir` (`llm.py:178`) aynı talimatı her çağrıda sistem istemine ekliyor; `YENIDEN_ACIKLAMA` (`plan_program.py:224`) bu cümleyi taşımıyor ve aynı yoldan çalışıyor. Açıklama sözleşme, yönlendirme sistem isteminin işi. · Güven: **Orta.** · İşlem: **remove** (altı küçük parça). Testlerde bu metni sabitleyen satır yok (`grep`).

**O4 · `beyin/llm.py:147`** — tekrar turunda bağlama eklenen "ÖNCEKİ ÇIKTIN ŞEMAYA UYMADI (…)". · Kalıp: Grup 1a baskı dili. · Neden: 22.09'da gpt-4o-mini için yazıldı; güncel modellerde büyük harfli ton gereksiz ve çıktının tonuna sızar. · Güven: **Orta.** · İşlem: **rewrite** — aynı içerik, normal ses (yama: `llm.py` @@ -144). Tekrar döngüsünün kendisi kalır (F4'e bakın).

**O5 · `beyin/llm.py:6,9`** — modül açıklaması: "zorunlu araç çağrısıyla şema" ve "Bu sürümde canlı anahtarla yalnız manuel yol test edildi; … öz-testinde denenecek". · Kalıp: Grup 2 zaman bağımlı anlatım. · Neden: `anthropic` yolu 29.09'dan beri canlı (K10, `KARARLAR/README.md:22`); "zorunlu araç" Y1 ile kalkıyor. · Güven: **Orta.** · İşlem: **rewrite** (yama: `llm.py` @@ -3).

**O6 · `AGENTS.md:48`** — "Canlı paket `DURUM.md`'de yazar". · Kalıp: Grup 2, `CLAUDE.md` ile çelişki. · Neden: `CLAUDE.md` 28 Ekim'den beri `DURUM.md`'ye yazılmayacağını söyler; canlı etiketi bugün yalnız donmuş `DURUM.md`'de (`v2026.10.16`), hiçbir durum eki canlı sürümü yazmıyor (`grep` sıfır). Sonraki canlı değişiklikte bu cümle yanlışa döner. · Güven: **Orta.** · İşlem: **rewrite** → canlı etiketi durum eklerinde, 28 Ekim öncesi `DURUM.md`'de (yama: `AGENTS.md` @@ -45). Açık boşluk: ilk canlı değişiklikte durum eki etiketi yazmalı.

**O7 · `AGENTS.md:72`** — "(12 Ekim 2026, İE-08'e kadar sır taraması … işaretliyordu ve '2 kontrolde fark' beklenirdi; o yanlış pozitif artık …)". · Kalıp: Grup 1d göç-göreli anlatım / Grup 2 tarih arkeolojisi. · Neden: cümle bugünkü kuralı değil eski bir beklentiyi anlatır; güncel olgu zaten `test-politikasi.md:15`'te. · Güven: **Orta.** · İşlem: **rewrite** — yalnız geçerli kural ve yanlış pozitifin bugünkü yeri (yama: `AGENTS.md` @@ -69).

**O8 · `.claude/rules/beyin.md:12`** (ve 17) — tek maddede ~3.000 karakter: "(geometri hakemi dördüncü tur)", "(beşinci tur)", "(altıncı tur)", "(yedinci tur)", "Hakem döngüsü yedinci turda kapandı", iki kez "`prompt.md` ve `sema.py` değişmedi (harness 22/22)" ve `test_celik_okuma.py` / `test_celik_revizyon_karar.py`'nin kilitlediği onlarca örnek cümle. · Kalıp: Grup 2 tarih anlatısı + yama birikimi + kodu yineleyen oynak ayrıntı. · Neden: kural dosyası `beyin/` dokununca her seferinde yüklenir; tur arkeolojisi davranış değiştirmez, örnekler testte zaten kilitli ve kod değiştiğinde ikisi birden güncellenmiyor. · Güven: **Orta.** · İşlem: **rewrite** — madde bütün yürürlükteki kuralları koruyarak kısaltıldı (sınıflar, aday sayısı davranışı, çatı seçimi, hesaplanan satırlar, Lokman'ın 13.10 kuralı, S1–S7 koşulu, soru bütçesi); tur işaretleri, geçmiş durum cümleleri ve test-kilitli örnekler çıktı; kod ve test adları eklendi (yama: `beyin.md` @@ -9). **Yalnız öneri:** metin cümle cümle aslıyla karşılaştırıldı, yine de Lokman onayı olmadan uygulanmaz.

## 6. İşaretler (düşük güven ya da Lokman'ın kararı; yamada yok)

- **F1 · `kvkk-denetcisi.md:3,8,22` ↔ `CLAUDE.md:25`, `kapanis:25`** — hakem tanımı kişisel veriyi de tarar ve "Kişisel veri bulguları" bölümü ister; iki çağıran "şimdilik yalnız sır taraması" der (Lokman, 16.10). Yeni kural bir denetimi daraltıyor; rehber gereği yeniden yazılmaz, karar Lokman'ın: ya hakem tanımına "varsayılan kapsam yalnız sır; kişisel veri yalnız istenirse" satırı eklenir ya da pilotta tam kapsam geri gelir.
- **F2 · `CLAUDE.md:25` "Kapanışta ikisi de koşturulur" ↔ `kapanis:24` (geometri-hakemi yalnız `motor/`, `is_emri/`, `beyin/varyant.py` değişince)** — iki cümle de aynı commit'ten (`8d9fb0f`, 4.10); geçmiş sıralayamıyor. Lokman seçer: koşullu (maliyet) ya da her kapanışta.
- **F3 · `beyin/prompt.md:22`** — "TAM yaz … 1'i düşürme": 22.09'da gpt-4o-mini'nin düşürdüğü bir rakam için yazılmış büyük harfli vurgu (Grup 1a/1d). Ücretli deneme olmadan yeniden ölçülemez; silinmesi önerilmez, pilot ölçümünde bakılır.
- **F4 · `beyin/llm.py:137-150`** — şema doğrulama hatasında tekrar döngüsü. Araçta `strict: true` (+ `sema.py`'de `additionalProperties: false`) şemayı sunucuda garanti eder ve döngüyü gereksiz kılar (Grup 1b, API özelliğiyle değiştir). `sema.py` harness'e bağlı dondurulmuş sözleşme olduğu ve pydantic şemasının strict kipe uygunluğu doğrulanmadığı için yalnız işaret.
- **F5 · `CLAUDE.md:14`, `atolye/SKILL.md:9`** — "iki cümleyle" sayısal anlatım sınırı (Grup 1f). Kod yazmayan sahibe yönelik biçim kararı; Fable 5.1 zaten az anlatır, sınır gerekli bilgiyi de kısabilir. İstenirse "her adımda ne yapıldığı kısa ve Türkçe söylenir" biçimine alınır.
- **F6 · Aynı birikim kalıbı, parça önerilmedi:** `beyin.md:17` (İE-14 maddesi: "Kapanış incelemesi (15.10, K1–K5)", "Canlı öncesi (16.10)", "canlı deneme G"), `kanal-vps.md:10,23,25`, `motor-cizim.md:17,26`. O8 kabul görürse aynı yöntemle kısaltılır.
- **F7 · Kapsam dışı belgeler:** `docs/kanal/README_KANAL.txt:10` Beyin'i gpt-4o-mini ile anlatır; talimat dosyası değil, bilgi için.
- **F8 · Hakem model pimleri** (`model: opus`, `model: sonnet`) takma addır, tarihli değil; yapılandırmadır, bulgu değil.

## 7. Bilerek bulgu sayılmayanlar

- Karar ve tarih referansları (K.., D.., "Lokman, 28 Ekim 2026"): kuralın dayanağı; D-02 ve `KARARLAR/` düzeni bunu ister. Bağlamdır, kalır.
- Onay kapılarının sabit cümleleri ("Plan hazır, onayını bekliyorum.", "main'e birleştirme senin onayınla."): tek güvenli sıranın olduğu kırılgan işlemler; kalır.
- Aynı kuralın birden çok dosyada **aynı** söylenişi ("LLM anlar, kod karar verir", sır kuralları, D-28 dört madde): çalışan yineleme, çelişmiyor.
- `kapanis`, `is-emri`, `atolye` adımlarının numaralı sırası: sıra gerçekten önemli.
- `gorsel_okuma.py` isteminin koordinat çerçevesi ve zincir kuralları: çıktı sözleşmesi, görsel okuma iskelesi değil.
- Hook'lar: kuralı kodla uygulayan yerler (`hizli_kontrol.py` 200 satır sınırı, `komut_koruma.py`) rehberin istediği yön.
- Yüzlerce yol adı denetlendi: `hosting/` dışında eksik yok; `genel_parmak_izleri.txt` her referans klasörünün içinde (`testler/referans/<tarih>/`), `test_aday_kabul.py` `testler/kalici/`de, `okuma_gorseli` `motor/genel/`de — kural metinleri yalnız dosya adı veriyor, çelişki yok. Komut bayrakları (`uret.py`, `dogrula.py`, `ortam_kur.sh --dogrula`, `atolye.py` alt komutları) argparse ile aynı.

## 8. Doğrulama

- Yama `git apply --check` ile depoya temiz uygulanıyor (23 parça, 14 dosya); altı Python dosyası `py_compile` geçti; yamada sır ve numara deseni yok.
- Davranış denemesi yok (ücretli; anahtar yok). Y1'in canlı etkisi: `claude-opus-5-5` için istek gövdesi araç açıklaması dışında aynı kalır (auto + aynı sistem cümlesi + 4096 + effort low); değişen yalnız ad eşleşmeyen modellerin yolu.
- Uygulandığında kapanış doğrulaması: `beyin/` değiştiği için `bash araclar/ortam_kur.sh --dogrula` (tam), harness 22/22, `dogrula.py` "fark yok"; `kanal/tests/e2e_vps_kanal.py` manuel arka uçla. `dogrula.py`'nin v1.1.1 `SHA256SUMS` farkı bilgi amaçlıdır, kırmızı değildir.

## 9. Önerilen yama

Dosya: `docs/raporlar/2026-10-31_istem_denetimi.patch`. Tamamı: `git apply docs/raporlar/2026-10-31_istem_denetimi.patch`; seçerek: `git apply --include='beyin/*' …` ya da parça parça elle. Parça dizini:

| Dosya · parça | Bulgu |
|---|---|
| `beyin/llm.py` @@ -3 | O5 |
| `beyin/llm.py` @@ -15 | Y2, O2 (`JSON_NOTU`) |
| `beyin/llm.py` @@ -68, -85, -98 | Y1 (`effort` parametresi), O2 |
| `beyin/llm.py` @@ -106 | Y1, O1 |
| `beyin/llm.py` @@ -144 | O4 |
| `beyin/prompt.md` @@ -25 | O2 |
| `plan_program.py`, `plan_islem.py`, `gorsel_okuma.py`, `degisiklik_okuyucu.py`, `plan_sema.py` | O3 |
| `AGENTS.md` @@ -45 | O6 (satır 48), Y4 (satır 53) |
| `AGENTS.md` @@ -59 · @@ -69 | Y3 · O7 |
| `.claude/skills/kapanis/SKILL.md` @@ -1 · @@ -14 | Y7 · Y8 |
| `.claude/skills/sahip-ozeti/SKILL.md` @@ -13 | Y10 |
| `.claude/agents/geometri-hakemi.md` @@ -17 | Y9 |
| `.claude/rules/kanal-vps.md` @@ -22 | Y5 |
| `.claude/rules/motor-cizim.md` @@ -14 | Y6 |
| `.claude/rules/beyin.md` @@ -9 | O8 (yalnız öneri) |

Kod parçaları aşağıda; kural dosyalarının uzun satırlı parçaları yalnız yama dosyasında.

```diff
--- a/beyin/llm.py
+++ b/beyin/llm.py
@@ -3,10 +3,11 @@
 Arka uçlar:
 - "openai_chat": Chat Completions + response_format json_schema (hosting'deki sohbet botunun kullandığı, kanıtlı API yolu).
 - "openai":      Responses API, json_schema çıktı.
-- "anthropic":   Messages API, zorunlu araç çağrısıyla şema.
+- "anthropic":   Messages API, araç çağrısıyla şema (tool_choice auto + istemde "yalnız bu aracı bir kez çağır"; zorunlu araç seçimi
+                 Opus 5.5 ve Sonnet 5.5'te HTTP 400 verir, İE-19).
 - "manuel":      hazır çıktı sözlüğü (test koşumu; LLM çağrısı yok).
 Anahtar: çağıranın verdiği `anahtar` → ortam değişkeni (OPENAI_API_KEY / ANTHROPIC_API_KEY) → PORTMAN_AYARLAR_JSON dosyası.
-Bu sürümde canlı anahtarla yalnız manuel yol test edildi; openai_chat/openai/anthropic yolları kurulum öz-testinde denenecek.
+Canlı arka uç `anthropic` (K10; Claude Opus 5.5); openai yolları yedektir ve bu dosyada eski biçimiyle durur.
 """
@@ -15,7 +16,8 @@
 PROMPT = (Path(__file__).resolve().parent / "prompt.md").read_text(encoding="utf-8")
-VARSAYILAN_MODEL = {"openai_chat": "gpt-4o-mini", "openai": "gpt-4o-mini", "anthropic": "claude-haiku-4-5-20251001"}
+JSON_NOTU = "\nÇıktı yalnız şemaya uyan JSON'dur; başka metin yazma."      # yalnız JSON kipli openai yolları; anthropic yolu araç çağırır
+VARSAYILAN_MODEL = {"openai_chat": "gpt-4o-mini", "openai": "gpt-4o-mini", "anthropic": "claude-opus-5-5"}   # ayar model vermezse (K10)
@@ -68,8 +70,10 @@
 def cikar_detayli(mesaj: str, baglam: str = "", backend: str = "manuel", model: str | None = None, hazir: dict | None = None,
-                  anahtar: str | None = None, ayarlar_json: str | None = None, timeout: int = 60) -> tuple[Talep, dict]:
-    """Bayi mesajını Talep'e çevirir; ikinci değer ölçüm: {backend, model, girdi_token, cikti_token, sure_ms}."""
+                  anahtar: str | None = None, ayarlar_json: str | None = None, timeout: int = 60,
+                  effort: str | None = "low") -> tuple[Talep, dict]:
+    """Bayi mesajını Talep'e çevirir; ikinci değer ölçüm: {backend, model, girdi_token, cikti_token, sure_ms}.
+    `effort` yalnız anthropic yolunda (`output_config.effort`); None verilirse gönderilmez."""
@@ -85,7 +89,7 @@
-                     "messages": [{"role": "system", "content": PROMPT}, {"role": "user", "content": kullanici}],
+                     "messages": [{"role": "system", "content": PROMPT + JSON_NOTU}, {"role": "user", "content": kullanici}],
@@ -98,7 +102,7 @@
-                    {"model": model, "instructions": PROMPT, "input": kullanici,
+                    {"model": model, "instructions": PROMPT + JSON_NOTU, "input": kullanici,
@@ -106,28 +110,27 @@
     elif backend == "anthropic":
         key = anahtar_bul(backend, anahtar, ayarlar_json)
-        opus55 = model == "claude-opus-5-5"
-        govde = {"model": model, "max_tokens": 4096 if opus55 else 1500,
-                 "system": PROMPT + ("\nTalebi yalnız talep_kaydet aracını bir kez çağırarak bildir." if opus55 else ""),
-                 "tools": [{"name": "talep_kaydet", "description": "Yapılandırılmış talep", "input_schema": schema}],
-                 "tool_choice": {"type": "auto", "disable_parallel_tool_use": True} if opus55 else {"type": "tool", "name": "talep_kaydet"},
+        # Tek yol, modele göre dallanma yok: zorunlu araç seçimi (tool_choice "tool") Opus 5.5 ve Sonnet 5.5'te 400 verir (İE-19);
+        # aracı istem adlandırır, çağrı sayısını kod denetler. max_tokens düşünme payını da kapsar (düşünme açık modellerde sayılır).
+        govde = {"model": model, "max_tokens": 4096,
+                 "system": PROMPT + "\nTalebi yalnız talep_kaydet aracını bir kez çağırarak bildir.",
+                 "tools": [{"name": "talep_kaydet",
+                            "description": "Bayinin mesajından okunan yapılandırılmış talebi kaydeder. Mesaj başına bir kez çağrılır. "
+                                           "Mesajda geçmeyen alanlar null kalır (listeler boş); yalnız şemadaki izinli değerler kullanılır; "
+                                           "ölçü, adet ve fiyat hesaplanmaz, karar verilmez. Kayıt kural katmanına gider, bayiye dönmez.",
+                            "input_schema": schema}],
+                 "tool_choice": {"type": "auto", "disable_parallel_tool_use": True},
                  "messages": [{"role": "user", "content": kullanici}]}
-        if opus55:
-            govde["output_config"] = {"effort": "low"}
+        if effort:
+            govde["output_config"] = {"effort": effort}
         out = _post("https://api.anthropic.com/v1/messages",
                     {"x-api-key": key, "anthropic-version": "2023-06-01"}, govde, timeout)
-        if opus55:
-            calls = [b for b in out.get("content", []) if b.get("type") == "tool_use"]
-            if out.get("stop_reason") != "tool_use" or len(calls) != 1 or calls[0].get("name") != "talep_kaydet":
-                raise LLMHatasi("Opus talep yanıtı tamamlanmadı veya beklenen araç çağrısı dönmedi")
+        calls = [b for b in out.get("content", []) if b.get("type") == "tool_use"]
+        if out.get("stop_reason") != "tool_use" or len(calls) != 1 or calls[0].get("name") != "talep_kaydet":
+            raise LLMHatasi(f"talep_kaydet çağrısı dönmedi (stop_reason {out.get('stop_reason')})")
         kullanim = out.get("usage") or {}
         meta.update(model=out.get("model") or model, girdi_token=kullanim.get("input_tokens"), cikti_token=kullanim.get("output_tokens"))
-        talep = None
-        for blok in out.get("content", []):
-            if blok.get("type") == "tool_use":
-                talep = Talep.model_validate(blok["input"]); break
-        if talep is None:
-            raise LLMHatasi("araç çağrısı dönmedi")
+        talep = Talep.model_validate(calls[0].get("input") or {})
@@ -144,7 +147,7 @@
-        ek = (baglam + " | " if baglam else "") + f"ÖNCEKİ ÇIKTIN ŞEMAYA UYMADI ({hata}); yalnız şemadaki izinli değerleri kullan, uymayanı null bırak ve belirsizliklere yaz"
+        ek = (baglam + " | " if baglam else "") + f"Önceki çıktı şemaya uymadı ({hata}); yalnız şemadaki izinli değerleri kullan, uymayan değeri null bırak ve belirsizliklere yaz."
--- a/beyin/prompt.md
+++ b/beyin/prompt.md
@@ -25,5 +25,3 @@
 10. `ozet`: bayiye geri okunacak tek cümle, Türkçe, örn. "P6001 modelinin aynalanmış hali için ön onay planı istiyorsunuz."
-
-Çıktı yalnız şemaya uyan JSON'dur; başka metin yazma.
--- a/beyin/plan_program.py
+++ b/beyin/plan_program.py
@@ -23,7 +23,7 @@
-ARAC_ACIKLAMA = "Tek kat çelik ev talebinin oda programını kaydet (koordinatsız). Yalnız bu araçla cevap ver."
+ARAC_ACIKLAMA = "Tek kat çelik ev talebinin oda programını kaydet (koordinatsız)."
--- a/beyin/plan_islem.py
+++ b/beyin/plan_islem.py
@@ -27,7 +27,7 @@
-ARAC_ACIKLAMA = "Bayinin yeni plan revizyon isteğini koordinatsız işlemlere çevir. Yalnız bu araçla cevap ver."
+ARAC_ACIKLAMA = "Bayinin yeni plan revizyon isteğini koordinatsız işlemlere çevir."
--- a/beyin/gorsel_okuma.py
+++ b/beyin/gorsel_okuma.py
@@ -30,9 +30,9 @@
-ARAC_ACIKLAMA = "Bayinin plan çiziminden okuduklarını kaydet. Yalnız bu araçla cevap ver."
+ARAC_ACIKLAMA = "Bayinin plan çiziminden okuduklarını kaydet."
-DUZELTME_ACIKLAMA = "Bayinin düzeltmesini ya da revizyon isteğini önceki okumaya işle. Yalnız bu araçla cevap ver."
+DUZELTME_ACIKLAMA = "Bayinin düzeltmesini ya da revizyon isteğini önceki okumaya işle."
--- a/beyin/degisiklik_okuyucu.py
+++ b/beyin/degisiklik_okuyucu.py
@@ -18,7 +18,7 @@
-ARAC_ACIKLAMA = "Bayinin revizyon isteğini planın tablosuna göre değişiklik işlemlerine çevir. Yalnız bu araçla cevap ver."
+ARAC_ACIKLAMA = "Bayinin revizyon isteğini planın tablosuna göre değişiklik işlemlerine çevir."
--- a/beyin/plan_sema.py
+++ b/beyin/plan_sema.py
@@ -134,7 +134,7 @@
-ARAC_ACIKLAMA = "Tek kat çelik plan taslağını kaydet (İE-14 plan şeması). Yalnız bu araçla cevap ver."
+ARAC_ACIKLAMA = "Tek kat çelik plan taslağını kaydet (İE-14 plan şeması)."
--- a/.claude/skills/kapanis/SKILL.md
+++ b/.claude/skills/kapanis/SKILL.md
@@ -1,6 +1,6 @@
-description: İş emrini kapatır — doğrulama, kanıt, DURUM.md, commit/push, bağımsız inceleme ve PR özeti. Merge etmez; main'e birleştirme Lokman'ın onayıyla.
+description: İş emrini kapatır — doğrulama, kanıt, durum eki (docs/durum/), commit/push, bağımsız inceleme ve PR özeti. Merge etmez; main'e birleştirme Lokman'ın onayıyla.
@@ -14,8 +14,8 @@
-- `motor/`, `beyin/` ya da `kanal/` değiştiyse **tam**: `bash araclar/ortam_kur.sh --dogrula` (~9 dk; arka planda koşturup bekleyebilirsin).
-- Yalnız belge/ayar/`.claude/` değiştiyse **hızlı**: `python3 testler/referans/dogrula.py --hizli` (~45 sn) ve `bash -n` / `py_compile` zaten hook'ta.
+- `motor/`, `beyin/`, `kanal/` ya da `kurallar/` değiştiyse **tam**: `bash araclar/ortam_kur.sh --dogrula` (~9 dk; arka planda koşturup bekleyebilirsin).
+- Yalnız belge/ayar/`.claude/` değiştiyse **hızlı**: `python3 testler/referans/dogrula.py --hizli` (~60 sn) ve `bash -n` / `py_compile` zaten hook'ta.
--- a/.claude/skills/sahip-ozeti/SKILL.md
+++ b/.claude/skills/sahip-ozeti/SKILL.md
@@ -13,7 +13,7 @@
-4. **Senin kararını bekleyenler** — açık kararlar (K16, K3/K4, Z-03/Z-06 vb.) ve her birinin neyi tıkadığı.
+4. **Senin kararını bekleyenler** — açık kararlar (`KARARLAR/README.md` › "Açık kararlar") ve her birinin neyi tıkadığı.
--- a/.claude/agents/geometri-hakemi.md
+++ b/.claude/agents/geometri-hakemi.md
@@ -17,7 +17,7 @@
-3. Gerekirse salt okunur komut koştur (`python -m beyin.harness`, `python3 testler/referans/dogrula.py --hizli`); dosya değiştirme, dondurma yapma, ağ kullanma.
+3. Gerekirse salt okunur komut koştur: `python3 testler/referans/dogrula.py --hizli`; harness'i `python3 -c "from beyin import harness; harness.main(durum_dir='/tmp/hakem_durum', rapor_yaz=False)"` ile (çıplak `python -m beyin.harness` izlenen `beyin/testler/` dosyalarını yazar). Dosya değiştirme, dondurma yapma, ağ kullanma.
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -45,12 +45,12 @@
-| `beyin/`, `motor/`, `kanal/`, `vps/` | Canlıdaki kod (v1.1.1 ağacı ve İE-02 eklemeleri). Canlı paket `DURUM.md`'de yazar |
+| `beyin/`, `motor/`, `kanal/`, `vps/` | Canlıdaki kod (v1.1.1 ağacı ve İE-02 eklemeleri). Canlı sürüm etiketi `docs/durum/` eklerinde yazar (28 Ekim 2026'dan öncesi `DURUM.md`'de) |
-| `is_emri/`, `ref_katalog/`, `ref_yan/`, `beyin/veri/` | Dondurulmuş referans girdiler (23 dosya); değiştirilmez, yeni dosya eklenebilir. İE-08'den beri `modeller/*.json` ve `kurallar/` (setler, cizim, secenekler, bayi) da referans girdisidir |
+| `is_emri/`, `ref_katalog/`, `ref_yan/`, `ref_prefabrik/`, `beyin/veri/`, `kanal/ref_*` | Dondurulmuş referans girdiler (kalıplar `testler/referans/dogrula.py` › `GIRDI_KALIPLARI`); var olan dosya değiştirilmez, yeni dosya eklenebilir. İE-08'den beri `modeller/*.json` ve `kurallar/` (setler, çizim, seçenekler, bayi örneği) da referans girdisidir |
@@ -59,7 +59,6 @@
-| `hosting/` | Hosting'teki canlı dosyaların kayıt kopyası; pakete girmez |
@@ -69,7 +68,7 @@
-- **Referans farkı beklenmez.** `dogrula.py` "SONUÇ: fark yok" demeli. (12 Ekim 2026, İE-08'e kadar sır taraması `vps/kapi_d_dogrula.sh:25`'i işaretliyordu ve "2 kontrolde fark" beklenirdi; o yanlış pozitif artık `denetim/kos.py`'de beklenen bulgu, telefon deseni ondalık sayıları numara sanmıyor.) Herhangi bir FARKLI satırı incelenir.
+- **Referans farkı beklenmez.** `dogrula.py` "SONUÇ: fark yok" demeli; herhangi bir FARKLI satırı incelenir. Sır taramasının `vps/kapi_d_dogrula.sh:25` parola deseni yanlış pozitifi `denetim/kos.py`'de beklenen bulgudur, telefon deseni ondalık sayıları numara saymaz (`testler/test_sir_taramasi.py`).
```

`kanal-vps.md` @@ -22: son cümle "Canlı: `v2026.10.15` (16.10), `plan_uretimi.acik = true`." → "Canlı sürüm ve açık ayarlar durum eklerinde (`docs/durum/`) yazar." · `motor-cizim.md` @@ -14: "**Bilinen açık (G1 …)** … (Lokman, 13.10 16:35 …, D-02)." cümleleri çıkar. · `beyin.md` @@ -9: 12. madde kısaltılmış biçim, 17. maddeden "`prompt.md` ve `sema.py` değişmedi (harness 22/22)." çıkar; tam metin yama dosyasında.

## 10. Sıradaki adım

Lokman'ın kararı: (a) yamanın hangi parçaları uygulanacak (önerilen sıra: Y1–Y10 ve O1–O7 birlikte; O8 ayrı okunup onaylanır), (b) F1 ve F2'de hangi kural geçerli. Uygulama bir BK iş emrinde (`/is-emri BK-NN İstem denetimi düzeltmeleri`): yama → tam doğrulama → `/kapanis`. Bu denetim her yeni model geçişinde yeniden koşulur.
