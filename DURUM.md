# Portman · DURUM

**Son güncelleme: 11 Ekim 2026 (İE-07 eki aşağıda; kanal 10 Ekim'den beri VPS'te canlı) · eski başlık: 30 Eylül 2026 22:05 (tek aktif teslim: Aşama 2 kabul vakası, İE-04; mesaj katmanı kanal v1.3 CANLIDA ve açık — Kapı M 30.09 akşamı geçti; kritik yol Astra'nın üç 3+1 adayı + Ubeydullah kabulü + K-A kararları; 3D bağlantısı M3 ayrı iş).** Her oturumun son adımı bu dosyayı güncellemektir. Aktif dal `ie-04`.

**Oturum devri:** `docs/devir/2026-09-30_Aksam_Devri.md` (30.09 akşamı, Kapı M sonrası; sıra ve bakım listesi) ve `docs/devir/2026-09-30_Oturum_Devri.md` (30.09 01:10; kurallar, K-A kararları, Astra ölçütleri). 28–30 Eylül penceresi kapandı. Yeni pencere bu ikisiyle başlar: kurallar, yapılanlar, bekleyen kararlar, sıradaki işler, Astra'ya çizim işi için ölçütler.

Yeni pencere için hazırlıklar:
- `CLAUDE.md` (oturum kuralları) ve `bash araclar/ortam_kur.sh` (tek komutla yerel ortam). İkisi 30.09 01:15'te Lokman'ın onayıyla `main`'e birleştirildi (`e8014e7`).
- Dış çizim denetimi: `deneme/2026-09-30_asama2/kos.py --dxf`.
- Mac'te `24_Astra_Cizimler/`.

**11 Ekim 2026 eki (dal `ie-07-pilot-hazirligi`, İE-07 Pilot hazırlığı; `docs/is_emirleri/IE-07.md`; kararlar `KARARLAR/D-06.md`, `D-07.md`):**
- **Canlı durum (10 Ekim, Notion kaydından depoya işlendi):** kanal 10 Ekim 13:54'ten beri VPS'te canlı, sürüm `v2026.10.10` (= `main` `6f889af`), mod `patron`, dry_run kapalı, teknik not kapalı. Kapı 4 (2. deneme 11:53), 5 (13:18), 7 (13:27), 8 (13:43–13:54; webhook v26.0) tamam; Kapı 6 kısmen (Patron kartı; 12 bayi bekliyor); Kapı 9 kısmen (13:56–57 "P6001 aynalı" → plan + PDF, r02; kayıtsız numara ve düğme denemesi kaldı); Natro işlemci "host" (14:00); ilk yedek 14:13 (Drive). İE-06 B3, B4, B6 Canlıda çalışıyor; B5, B7, B8 Kısmen; B9–B11 Çalışmıyor (Kapı 10–13 bekliyor). Ayrıntı `IE-06.md › Kanıt`.
- **İE-07 yerel kod (11 Ekim; Lokman'ın plan onayı ve altı kararı):** katalog kaydının yeni sürümü `beyin/veri/katalog_37_proje_v2.json` (kat, kaynak, doğrulama; 13 çift katlı "çift kat"; Ç8201, Ç1031 (103 m² 2+1), Ç1151 çizimden; dondurulmuş dosya değişmedi, D-07), yakın model önerisinde kat süzgeci (söylenmediyse süzgeç yok, etiket doğru); göç 005 (giden kind `template`, `giden.kaynak`, rol `test`); Meta şablon mesajı (`kanal/sablonlar.py`, `meta_api.sablon_yuku`; adlar ayarda `sablon_patron_bildirim`, `sablon_bayi_dosyalar_hazir`); Patron bildirimi metin + şablon (pencere kapalıysa şablon gider, açıksa gereksiz; talep kimliği boş gitmez); panelden bayiye metin + PDF (10 MiB; nginx `/panel/` 12m) ve "dosyalar hazır" şablonu; bayinin "Dosyaları gönder" cevabı LLM'siz sabit metin + Patron'a çift bildirim; kuru koşu `rol=test` kartıyla (Patron konuşmasında iz yok) ve rapor sorgusu düzeltildi. BK-04 ve BK-06 PR'ları kapatıldı, BK-05 Mac maddelerine daraltıldı. Meta şablon başvuru notu: `docs/kanal/2026-10-11_Meta_sablon_basvurusu.md`.
- **Kullanıcı adımları:** P1 Yerelde çalışıyor (kayıt eşitlendi; kuru koşu düzeltmesi yerelde); P2 Yerelde çalışıyor (LLM'in "tek kat"ı kat=1'e çevirmesi canlıda ücretli denemeyle kanıtlanacak); P3, P4, P5 Yerelde çalışıyor (sahte Meta); P6 bkz. gerileme. Canlıya alma, şablonların Meta onayı ve ayar girişi, Kapı 9–13: ayrı kapılar (rehber planı sıra 2).
- **Gerileme (11 Ekim):** `IE-07.md › Kanıt` (harness 22/22, referans girdiler ve DXF/PDF parmak izleri AYNI, yalnız bilinen sır farkı, pytest 352 geçti, e2e 60/60). Hakemler: KVKK temiz; bağımsız kod incelemesinin 15 bulgusundan 13'ü düzeltildi.
- **Sınırlar:** Canlıya, sunucuya, LLM'e ve WhatsApp'a dokunulmadı; ücretli çağrı yok; silme yok (harness artığı 4 dosya scratchpad'e taşındı, Lokman'ın onayıyla silinir). **Bekleyen onay:** PR (`ie-07-pilot-hazirligi` → `main`) ve etiket; Meta'ya şablon başvurusu (Lokman, WhatsApp Manager). Bu ek `main`'e birleşirken korunur.

**9 Ekim 2026 eki (dal `ie-06-kanal-vps`, İE-06 Aşama A; `docs/is_emirleri/IE-06.md`, karar `KARARLAR/D-05.md`):**
- **Kanal tek sunucuya taşınıyor.** Yerel kod bitti: Meta webhook (`kanal/webhook.py`), gönderici (`kanal/gonderici.py`), Meta istemcisi (`kanal/meta_api.py`), panel (`kanal/panel.py`), göç 004 (bayi kimlik kartı, gelen dosyalar, webhook olayları), ajan yerel kuyrukta (`vps/agent.py` v2.0), VPS betikleri (`vps/kurulum.sh`, `guncelle.sh`, `geri_don.sh`, `sir_koy.py`, `panel_parola.py`, `yedek*.sh`, `nabiz.sh`, `durum.sh`, `kuru_kosu.sh` …) ve systemd/nginx/sshd/fail2ban dosyaları. Eski mimari depodan çıktı: `kanal/feature.php`, `api.php`, `install/`, PHP testleri ve `e2e_*.py`, `vps/paketle.py`, `bootstrap_template.sh`, `hosting/` (29.09 kayıt kopyası git geçmişinde: `bc2bdc0`). Kullanıcı adımı B1 **Yerelde çalışıyor**; B2–B11 Çalışmıyor (canlı kapılar). BK-04 İE-06 içinde kapandı (`docs/is_emirleri/BK-04.md`).
- **Gerileme (9 Ekim 19:32–19:42, inceleme düzeltmelerinden sonra):** `bash araclar/ortam_kur.sh --dogrula` çıkış 0: harness 22/22, DXF ve PDF parmak izleri 18/18 AYNI, yalnız bilinen sır taraması farkı; pytest 307 geçti; `kanal/tests/e2e_vps_kanal.py` 42/42 (ayrıntı `IE-06.md › Kanıt`). Oturum devri: `docs/devir/2026-10-09_IE-06_Devri.md`.
- **İnceleme:** KVKK denetimi temiz (gerçek sır/kişisel veri yok; yer tutucu numaralar düzeltildi). Bağımsız kod incelemesinin 8 bulgusu düzeltildi (nginx 1.24 `http2`, nabız uyarısı portman kullanıcısıyla, pg_restore stdin, sürüm kapısı sağlık JSON'una bağlı, uyarı sıklık anahtarı, panel URL'leri günlüğe yazılmaz, bayi kartı ezilmez, kayıtsız medya sınırı); ayrıntı `IE-06.md › Kanıt › İnceleme`. Bekleyen: hook korunan listesine `deploy_key`/`rclone.conf` (Lokman onayı).
- **Sınırlar:** Canlıya, veriye, sunucuya, LLM'e ve WhatsApp'a dokunulmadı; ücretli çağrı yok; silme yalnız depodan (PR'da görünür). Canlı akış hâlâ eski yol (hosting PHP + eski VPS, v1.3); Kapı 1–13 Lokman'ın onayı ve eliyle.
- **Bekleyen onay:** Kapı M — birinci PR (`ie-06-kanal-vps` → `main`, İE-04 kodu içinde) ve `main`'de açıklamalı etiket. Bu dosya `main`'de geride; `ie-06` birleşirken bu ek elle taşınır.
- **9 Ekim akşamı, Kapı M öncesi düzeltmeler (Lokman'ın kararları 1–8; `IE-06.md › Kanıt`):** hook korunan listesine VPS sırları; `/saglik` dışarıya yalnız durum kodu ve kısa durum, ayrıntı 127.0.0.1'den; panelde hesap geneli kilit kalktı (IP başına kilit, nginx hız sınırı, fail2ban, ≥12 karakter parola kalır); Kapı 0 yapılmayacak; `.gitattributes` ile sürüm ağacına `testler/` ve `deneme/` girmez (`beyin/testler/` öz-test için kalır); `motor/ifc_uret.py` varsayılan bina adı nötr; `kanal/settings.example.json` kaldırıldı; kurumsal hat kişisel veri değil. **Gerileme (20:04–20:13):** `ortam_kur.sh --dogrula` çıkış 0, harness 22/22, parmak izleri 18/18 AYNI, yalnız bilinen sır farkı, pytest 308; e2e 42/42. Hakemler: KVKK sır yok (test profil adı sahteyle değiştirildi; belgelerdeki mühendis adı ve "Lokman Bey" hitabı Lokman'ın kararına bırakıldı), geometri kurallara uygun. PR açıldı; birleştirme ve etiket Lokman'ın onayıyla.
- **10 Ekim · canlı kapılar başladı; Kapı 4 numpy'da güvenle durdu (K19).** Kapı 0 yapılmadı. Kapı 1 (10:45–11:07) Natro'da düz Ubuntu 24.04; Kapı 3 DNS A kaydı eşleşti; Kapı 2 (11:10–11:12) 9 adım temiz, sertifika 8 Ocak 2027'ye kadar, parolalı SSH kapalı, ufw 22/80/443 → **B2 Canlıda çalışıyor**. Kapı 4 1. deneme (11:19): `v2026.10.09` doğrulandı, 256 dosya açıldı, içe aktarma denetiminde numpy 2.4.6 `X86_V2` hatası → sürüm etkinleşmedi (B3 Çalışmıyor). Natro vCPU x86-64-v2 sunmuyor; **K19 geçerli** (K19 › Uygulanış). Düzeltme: `vps/gereksinimler.txt` (tam sabit; numpy 1.26.4), `guncelle.sh` yalnız onu kurar ve numpy hesabı yapar; `araclar/gereksinimler.txt` yerel kalır. **Doğrulama (bulut, Python 3.12.3 + sunucu listesi, 08:33–08:44):** harness 22/22, DXF/PDF parmak izleri 18/18 AYNI, pytest 308, e2e 42/42. Belge düzeltmeleri: Riskler'deki "canlıda 2.5.3" satırı yanlıştı; SSH anahtarı `portman_natro_ed25519`; Mac'te `gh repo clone` ile klon; Kapı 1 Natro notu. Sıradaki: PR birleşince Lokman Mac'ten `v2026.10.10` etiketini iter (komut devir notunda), Kapı 4 yeniden.
- **Kapı M tamamlandı (9 Ekim 23:24):** PR #7 (`ie-06-kanal-vps` → `main`) Lokman tarafından birleştirildi, birleşme commit'i `1ff69d1`; İE-06 Aşama A ve İE-04 kodu artık `main`'de. Etiket adı **`v2026.10.09`** (açıklamalı; `1ff69d1`'i gösterir); bulut oturumunda yerelde açıldı, ama bu ortamın git vekili etiket push'unu reddediyor (dal push'u çalışıyor, `refs/tags` 403) → **etiketi Lokman Mac'ten iter** (komut `docs/devir/2026-10-09_IE-06_Devri.md › Etiket`). Kapı 4 bu etiketi bekler. KVKK soruları kapandı: tarihli belgelerdeki mühendis adı kalır (şirket içi belge, ekip üyesi), ürün metnindeki "Lokman Bey" hitabı bilerek, kalır (Lokman, 9.10). Harness artığı 4 dosya Lokman'ın onayıyla silindi. Bu ek `main`'in üstünden yeniden başlatılan `ie-06-kanal-vps` dalında; ikinci PR (kanıt ve DURUM) Lokman'ın onayıyla.

**4 Ekim 2026 eki (dal `claude/dreamy-ride-pz40kq`, BK-03 kayıt bakımı; `docs/is_emirleri/BK-03.md`):**
- **BK-01 ve BK-02 `main`'de.** BK-01 (PR #1) 15:35'te `0ed6b96` ile, BK-02 (PR #2) 15:37'de `c816b6f` ile birleşti. Alttaki iki ekte geçen "`main`'e birleştirme Lokman'ın onayını bekliyor" satırları bu tarihle kapandı. Ekler tarihli kayıt olduğu için değiştirilmedi.
- **K17 kapandı olarak işaretlendi.** Sızan eşleşme anahtarı 28.09'da kapı C'de yenilenmişti (aşağıda "Kapananlar"), ama `KARARLAR/README.md` K17'yi hâlâ açık karar gösteriyordu. README'ye ve `KARARLAR/K17.md`'ye uygulanış notu eklendi; 22.09 karar metni değişmedi. Claude anahtarının 29.10 son kullanma tarihi ayrı bir risktir ve açık kalıyor.
- **Bu dosya hâlâ geride.** Güncel durum `ie-05` dalındaki DURUM'dadır. `ie-04` ya da `ie-05` birleşirken bu ek ve alttaki iki ek elle taşınır.
- **Sınırlar:** Yalnız belge değişti. Canlıya, veriye ve sunucuya dokunulmadı; ücretli çağrı ve silme yok. Gerileme sonucu `BK-03.md` › Kanıt'ta.

**4 Ekim 2026 13:45 eki (dal `bk-02-depo-iskeleti`, BK-02; BK-01'in üstüne):**
- **Depo iskeleti kuruldu** (`docs/is_emirleri/BK-02.md`): `AGENTS.md` (Claude ve Codex için ortak değişmez kurallar), kısaltılmış `CLAUDE.md` (`@AGENTS.md` içe alır), `.claude/rules/` (test politikası her oturumda; motor, beyin, kanal kuralları ilgili dosya açılınca), komutlar `/is-emri` `/kapanis` `/sahip-ozeti`, hakemler `geometri-hakemi` ve `kvkk-denetcisi`, üç hook (sır/dondurulmuş dosya koruması, komut freni, sözdizimi denetimi) ve izin listesi (`.claude/settings.json`).
- **Gerileme** (`dogrula.py --hizli`, 13:41–13:43): harness 22/22, parmak izleri AYNI, yalnız bilinen sır taraması farkı (BK-01 ile aynı sayılar); ürün koduna dokunulmadı.
- **Sınırlar:** Canlıya, veriye ve sunucuya dokunulmadı. Hook'lar gerçek Code oturumunda henüz görülmedi (B1–B8 Lokman'ın ilk oturumunda). `main`'e birleştirme Lokman'ın onayını bekliyor; BK-01 önce birleşmeli.

**3 Ekim 2026 23:05 eki (dal `claude/lucid-ritchie-66j34y`, BK-01):**
- **Bu dosya geride.** Güncel durum `ie-05` dalındaki DURUM'dadır; aktif iş İE-04, taslak iş İE-05.
- **Yapılan bakım** (`docs/is_emirleri/BK-01.md`):
  - `araclar/ortam_kur.sh` artık `main`'de olmayan `deneme/2026-09-30_asama2/kos.py`'yi önermiyor; dosya varsa (`ie-04`, `ie-05`) öneri görünüyor.
  - `README.md` harness için "15 mesaj" yerine "22 vaka" diyor.
- **Gerileme** (`ortam_kur.sh --dogrula`, 22:50–23:00): harness 22/22; DXF ve PDF parmak izleri AYNI (18/18); yalnız bilinen sır taraması farkı; testler 328 geçti.
- **Sınırlar:** Canlıya, veriye ve sunucuya dokunulmadı. `main`'e birleştirme Lokman'ın onayını bekliyor. `ie-04` birleşirken bu paragraf onun DURUM'una elle taşınır.

Canlıda çalışan akış şu: WhatsApp → hosting kanalı → VPS ajanı → Beyin ve Motor → plan PDF'i. Akış yalnız Patron modunda açık. Son gerçek mesaj doğrulaması 29.09 21:16–21:32 (kapı G yeniden denemesi, 6 Patron mesajı). 28–29 Eylülde canlıya v1.2 kuruldu (dosya modu) ve LLM Claude Opus 5.5'e geçti; 29.09 01:16'da gerçek bir Patron mesajıyla denendi (r01 PDF'i telefona geldi). 29.09 18:59'dan beri ajan kalıcı modda: konuşma ve iş durumu Postgres'te (kapı F); 29.09 19:27–19:56'da kalıcı modda 5 gerçek Patron mesajı işlendi (kapı G). 29.09 21:09'dan beri canlıda düzeltilmiş paket `9c76af59…` var; 21:16–21:32 arasında 6 gerçek Patron mesajıyla G'nin kabul adımları geçti. Depo, v1.1.1'in (`ec4e9a3`) devridir. Hedefteki "90 m² 3+1, üç seçenek" akışı henüz taslak.

Durumlar: **Taslak** yalnız belgede · **Kodlandı** kod var, testi yok ya da dar · **Test edildi** tekrarlanabilir testten geçti · **Canlıda doğrulandı** gerçek kullanımda (gerçek mesaj ya da planlı koşu) görüldü ve tarihli.

## Tek aktif teslim: Aşama 2 kabul vakası · yaklaşık 90 m² 3+1 (İE-04)

Onay: Lokman 29.09 23:49. İş emri: `docs/is_emirleri/IE-04.md` (dal `ie-04`). Yerel geliştirme ve testler onaylı; yeni harcama, veri paylaşımı, silme ve canlı değişiklik ayrıca onaylanır. P6001 referans ve gerileme testi olarak kalır.

**Bitiş koşulu:** Aşağıdaki altı kullanıcı adımının hepsi Patron modunda canlıda, aynı yeni projede çalışır. Seçenekler, kaynak uygunluk denetiminden ve Ubeydullah kabulünden geçmiş üç geçerli adaydan gelir. P6001 akışı, harness, altın testler ve `yeniden_kos.py` çıktıları değişmez. İlerleme test sayısıyla değil, bu tablodaki adım durumlarıyla bildirilir.

| # | Kullanıcı adımı | Durum (30.09 22:00, Kapı M sonrası) |
|---|---|---|
| A1 | "3+1, 90 m² civarı" → yalnız gerekli sorular | Kısmen. Kod canlıda (öncelik sorusu butonlu); aday kaydı yokken canlı v1.2 gibi (yakın model listesi) |
| A2 | Teknik olarak uygun üç alternatif | Çalışmıyor — 0 geçerli aday. Kod ve tablolar canlıda; Astra'nın üç adayı + kaynak uygunluk denetimi + Ubeydullah kabulü + paket gerekir |
| A3 | Seçim → o adaydan r01 | Yerelde TEST adaylarıyla çalışıyor; canlıda P6001 doğrudan plan (buton/görsel/PDF, 30.09 T1). Adaylarla canlı test bekliyor |
| A4 | Bir değişiklik → aynı projede r02 | **Canlıda çalışıyor** (30.09 T2–T3, T6): Revize butonu → soru → metin → aynı projede r02/r03; gerçek geometri değişikliği (120x120 → 120x180) görselde ve PDF'te |
| A5 | Aynı revizyondan PDF ve 3D bağlantısı | Kısmen canlıda: görsel + PDF aynı İş Emri'nden gidiyor; IFC ve 3D sayfası üretilip VPS'te duruyor; **bağlantı yok** (M3: hosting'te statik sayfa, karar 30.09) |
| A6 | Eski revizyon onayı reddi, güncel onay kabulü | **Canlıda çalışıyor** (30.09 T4–T5): eski Onayla reddedildi ve durum değişmedi; güncel Onayla → onaylandi |

**Beklenen kararlar** (aday paketi `docs/raporlar/2026-09-30_Asama2_3arti1_Aday_Karsilastirmasi.md`, K-A1–K-A10):
- alan tanımı ve tolerans;
- katalog PDF'i ile DXF'in önceliği;
- kutu dışı veranda;
- açık plan sınırı;
- açıklık konumu, kapı genişlikleri, iç duvar ekseni;
- K16 (üçüncü aday);
- kaynak uygunluk denetimi;
- insan kabulü.

İE-03'ten bu teslime alınanlar: kaynaklı aday bilgisi, ilgili değişikliği doğru anlayan konuşma davranışı, düzeltme adaylarının kaydı. Geniş hafıza depoları ve ölçüm çalışması bu teslimin ön koşulu değil.

**Hedef akış (30.09 07:14, Lokman):** Hedef WhatsApp Akışı kanvası (sürüm 13) hedef akıştır. Aşama 2 kanvasın 1–4. adımlarını kapsar; seçenekler görsel + buton + liste ile gider. Bugünkü kanal yalnız metin ve PDF gönderiyor; görsel, buton, liste ve bağlantı butonu hosting PHP ve ajan değişikliğidir (yerelde geliştirilir, canlıya alınması ayrı onay). Kanvasın 5–6. adımları Aşama 3–4'te.

**Mesaj katmanı (kanal v1.3), 30.09 07:54 onayı, yalnız yerel:** `docs/is_emirleri/IE-04-mesaj-katmani.md`. Ajan/Beyin, hosting PHP (`feature.php`, `api.php` v1.3), göç 003 (yalnız ekler), `motor/bayi_gorseli.py`, `motor/ifc_uret.py`, `motor/ucb_sayfa.py`. Ayar `mesaj_katmani` kapalıyken davranış v1.2 ile aynı. Testler: 343 Python + harness 22/22 + PHP çevrimdışı 44/44 + gerçek PHP hattı uçtan uca (katman kapalı 18/18, açık 21/21); referans DXF/PDF parmak izleri AYNI. Canlıya alınması (hosting PHP, paket, göç 003, 3D barınağı) ayrı onay.

**Canlıya alma (Kapı M), 30.09 19:59–21:56 — GEÇTİ:** `docs/is_emirleri/IE-04-canli.md` §4 (saatler, çıktılar), Mac `27_Kapi_M/` (`cikti/`, `yedek/`). Canlı: hosting `feature.php`/`api.php` v1.3, paket `kanal-v1.3-20260930-1948` `34ae192c…` (60/60 birebir; öz-test geçti), göç 003, `mesaj_katmani: true`, `ucb_taban_url` yok. Ajan venv'ine matplotlib/pillow/ifcopenshell kuruldu (numpy 2.5.3'e yükseldi; öz-test sonra geçti). Gerçek hatta T1–T6: görsel başlıklı buton mesajı + PDF + teknik not; Revize butonu; aynı projede r02 ve r03 (gerçek pencere değişikliği); eski Onayla reddi; güncel Onayla kabulü; 9 Patron mesajı (işler 26–34), 21 giden, okunan kanıtta hepsi teslim; 5 LLM çağrısı ≈0,14 $. Kozmetik kusurlar (buton işlerinde "LLM None…", sayaçların bunları LLM sayması, "birkaç dakika içinde PDF" kalıbı, "vps-agent-v1.2" etiketi) sonraki pakete. Ürün soruları: onaylanmış planın Revize butonu; sıfır fark revizyonu. **1 Ekim'den itibaren WhatsApp servis mesajları ücretli:** her plan 3 mesaj (teknik not kapatılırsa 2); tutar Meta tarifesinden okunacak.

**Günlük canlı kontrol:****Günlük canlı kontrol:** `vps/canli_kontrol.sh` (salt okunur; Lokman `ssh portman-vps 'bash -s' < canli_kontrol.sh` ile koşar): servis, paket, hosting, öz-test, disk, yedekler, Postgres sayıları, günlükteki hatalar. 30.09 19:59'da canlıda ilk kez koşuldu (temiz); beklenen paket varsayılanı v1.3 (`34ae192c…`).

## Bu depoda ne var

| Yol | İçerik |
|---|---|
| Kökteki v1.1.1 ağacı | `lokmansayim/portman` deposunun geçmişiyle birlikte, değiştirilmeden (`ec4e9a3`, 22.09 20:12). Özetleri `SHA256SUMS`'ta. |
| `testler/referans/` | Dondurulmuş referanslar (`2026-09-28/`, `2026-09-28b/`) ve `dogrula.py` |
| `testler/kalici/` | İE-02 kalıcı akış testleri (gerçek Postgres; T1–T10) ve kabul gösterimi |
| `docs/is_emirleri/` | İE-02 (kapandı 29.09); İE-03 planı ve Aşama 0 envanteri; İE-04 Aşama 2 kabul vakası (aktif) |
| `testler/bilinen_hatalar/` | B1 ve B2 testleri; G ve Astra (A1/A2) testleri. Düzeltmeler canlıda: B1 ve B2 28.09 23:31'den, B1'in Opus'la kısa cevap yolu 29.09 21:09'dan beri |
| `deneme/2026-09-23/` | 23 Eylül denemeleri ve `yeniden_kos.py` |
| `deneme/2026-09-30_asama2/` | Aşama 2 aday karşılaştırmasını yeniden üreten `kos.py` (dış çizim için `--dxf`), kaynak sayımları, pafta ayırıcı ve küçük çıktılar |
| `docs/devir/` | Oturum devir notları (en yenisi en günceli) |
| `CLAUDE.md` | Her oturumun kendiliğinden okuduğu kurallar ve okuma sırası |
| `araclar/` | `ortam_kur.sh` (tek komutla yerel ortam; `--dogrula` ile gerileme) ve `gereksinimler.txt` |
| `KARARLAR/` | K01–K25 ve Z-01–Z-10, her karar ayrı dosyada |

## Bileşenler

| Bileşen | Durum | Kanıt (tarih) | Kapsam sınırı |
|---|---|---|---|
| Kanal v1.1.1: WhatsApp → hosting webhook → kuyruk → gönderim | Canlıda doğrulandı | 21.09 (v1.0): 3 mesaj, 1'i bekletildi, 2 PDF okundu · 22.09 22:31: v1.1.1 paketi (`bd1ca27c…`), öz-test geçti · 22.09 22:33–38: 3 Patron mesajı yanıtlandı · 28.09 (kapı A, salt okunur): VPS'teki uygulama (48/48 dosya), hosting'in dağıttığı paket ve hosting'teki `feature.php` ile `api.php` v1.1.1 ile birebir (tam hash); servis 25.09'dan beri kesintisiz · 28.09 23:31 (kapı E): hosting `feature.php` ve `api.php` v1.2, paket v1.2; 29.09 00:47: Opus paketi `f2bff20a…`, öz-test geçti · 29.09 01:16: 1 Patron mesajı → iş emri r01, 25,9 sn, metin + PDF telefona ulaştı · 29.09 21:09: paket `9c76af59…` (G düzeltmesi), öz-test geçti · 29.09 G ve yeniden denemesi: 11 Patron mesajı, 15 giden, hepsi Meta'ya teslim | Yalnız Patron modu; gelen kuyruk hosting'te bir JSON dosyası (`state.json`); konuşma ve iş durumu 29.09 18:59'dan beri VPS'te Postgres'te |
| VPS ajanı (Natro, portman-agent; 28.09'dan beri v1.2) | Canlıda doğrulandı | 22.09 19:06: ilk gerçek İş Emri, 27 sn · 22.09 22:14: v1.1.1, `vps-health.json` · 29.09 00:57: v1.2, dosya modunda, 50/50 dosya paketle aynı · 29.09 18:59: kalıcı mod (Postgres), 19:09'da sağlıklı · 29.09 21:09: paket `9c76af59…`, kalıcı modda, 50/50 dosya paketle aynı | ufw etkin ama kuralları okunmadı; root parolayla SSH'ye girebiliyor (22.09 23:59) |
| Beyin: LLM çıkarımı (29.09'dan beri Claude Opus 5.5; önce gpt-4o-mini), kural katmanı, varyant | Canlıda doğrulandı | Harness 22/22 (sabit girdiler; 28.09 ve 29.09'da yeniden) · 22.09 22:33–38 canlı davranış testi 2/3 (B1) · 29.09 G yeniden denemesi (Opus): belirsiz pencere sözünde soru, olumsuz cevapta soru yinelemesi, "değiştir" ile aynı soruya bağlanma ve aynı projede r02 gerçek mesajla geçti | Yalnız P6001 şablonu ve pencere senaryosu canlıda görüldü; B2 (D-01) canlıda gerçek mesajla tetiklenmedi; olumsuz ya da soru biçimli kısa cevaba "Anlayamadım" (pilot sınırlaması, İE-03 gereksinimi) |
| Motor v1.1.1: İş Emri → DXF → doğrulama → PDF | Test edildi | Altın testler 6×8 (41 pano, 0 cm²) ve Yan Verandalı 6×8,5 (BOM 26 kod); P6001 katalog testi (773 × 763) · 28.09: üç temiz koşuda içerik parmak izi aynı | Plan PDF'i üretir, ön onay paftası değil; canlı PDF içeriği insan gözüyle doğrulanmadı |
| Çıkarıcı: katalog DXF → İş Emri | Kodlandı | 30.09: 90 m² civarı 3+1 adaylarında kaynakla karşılaştırıldı: P9401 ve P9201 bütün açıklıklarla, P9501 ve P1051 oda yerleşimi yanlış; Motor doğrulaması yanlış çizimi de geçiriyor (kaynak uygunluk denetimi önerildi) · 16 planın 15'i Motor doğrulamasından geçti (22.09 ve 28.09) | P1051'de kapılar, P8501, P9501 ve P1081'de bazı açıklıklar düşüyor; P9901 desteklenmiyor; insan kabulü yok |
| Serbest aks (Motor yaması) | Kodlandı | 23.09: Tatar 80 m²'de denendi · 28.09: `yeniden_kos.py` ile yeniden koşuldu, sonuçlar aynı | Test dar: tek plan. `deneme/` altında ayrı yama; ana kodda ve canlıda değil; K16'ya bağlı |
| Vektör PDF plan okuyucu | Kodlandı | 23.09 Tatar 80: ölçek iki yöntemle %0,05 tutarlı · 28.09: `yeniden_kos.py` ile aynı | Test dar: tek plan. Deneme sürümü; el çizimi okumuyor |
| IFC4 üretimi (IfcOpenShell) | Kodlandı | 30.09: P9401 ve P9201 İş Emri'nden IFC4 (7/5 ve 6/5 açıklık, şema hatası 0) · 28.09 yeniden koşum (`yeniden_kos.py`): şema 0 hata, çift sayım 35/35, hacim farkı %0,0 · Yan Verandalı: Astra modeliyle 65/67 eleman, açıklık 13/13 | Tekrarlanabilir test var ama dar: iki plan. Şema doğrulaması üretim doğruluğu değildir |
| Blender modeli | Kodlandı | 28.09: `yeniden_kos.py` ile bpy 5.0.1'de yeniden kuruldu, 65 pano, BOM aynı | Test dar: tek plan; sunum içindir, hesap burada yapılmaz |
| Depo | Kodlandı | 28.09: `portman-v2private` açıldı; v1.1.1 geçmişiyle alındı; İE-01, Lokman'ın onayıyla `main`'e birleştirildi · 29.09: İE-02 Lokman'ın onayıyla `main`'e birleştirildi · 30.09 01:15: altyapı (`CLAUDE.md`, `araclar/`) Lokman'ın onayıyla `main`'e birleştirildi (`e8014e7`) | Eski depo `lokmansayim/portman` yalnız okunuyor |
| Yapı Tanımı şeması | Taslak | Zemin, 27.09; temeli İş Emri şeması v0.1 (21.09) | Ölçü anlamları ve ürün ailesi ayrımı eksik |
| Veritabanı: kalıcı konuşma ve iş akışı (Postgres) | Canlıda doğrulandı | 29.09 G (19:25–19:59) ve yeniden denemesi (21:05–21:34): 11 gerçek Patron mesajı; soru kaydı yeniden başlatmadan sonra korundu, onay zinciri eski revizyonu reddetti, tekrar gelen mesaj ikinci iş açmadı · 29.09 kapı F: canlı VPS'te göçler 1–2; hosting'ten 1 konuşma, 14 mesaj/iş aktarıldı, kaynak ↔ Postgres 15/15 aynı; ajan 18:59'dan beri kalıcı modda, `worker` vps. 28.09: `testler/kalici/`, gerçek Postgres 16'da 185 test geçti. Kabul gösterimi 10/10 (simülasyon: WhatsApp ve LLM sahte). Ajanın kalıcı modu sahte hosting ile sınandı (600 sn süpürme ve hata enjeksiyonu dahil). | Geçişten önceki planlar `projeler`/`revizyonlar`'da yok (tasarım gereği; onayları eski yoldan). Canlı verinin yedekleri elle alındı (G öncesi/sonrası, yeniden deneme öncesi/sonrası; Mac'te); günlük cron'un canlı veriyle ilk koşusu 30.09 03:17. Yer: mevcut VPS (D-04). Canlıya bağlama planı ve onay kapıları: `docs/is_emirleri/IE-02-canli.md`. pgvector yok (İE-03 planında zorunlu değil, ölçüme bağlı). |
| Kaynaklı hafıza ve getirme (İE-03) | Taslak | Araştırma notu, 21.09 · İE-03 planı 29.09 (`docs/is_emirleri/IE-03.md`, `ie-03` dalı) | Uygulama, veri paylaşımı, ücretli deneme ve canlı değişiklik ayrı onayla |
| Model geçidi | Canlıda doğrulandı | `llm.py`'de OpenAI ve Anthropic yolları var; 29.09'dan beri canlıda `claude-opus-5-5` (K10), öz-test geçti (5.309 + 488 token, ~0,031 $; 29.09 21:09'da yeni paketle 5.309 + 458) · 23.09 kıyas: gpt-4o-mini 6/7, gpt-6-sol 4/7 | 29.09 01:16'da tek gerçek Patron mesajında 5.280 + 337 token, ~0,028 $; 29.09 G yeniden denemesinde (B1 vakası dahil) çağrı başına 5.280–5.382 giriş + 135–623 çıkış token (~0,024–0,034 $), tekrar yok. Claude anahtarı VPS `agent.env`'de ve hosting `claude_api.json`'da; bilinen son kullanma 29.10. Hosting ayarı VPS'e yalnız arka uç, model ve zaman aşımını geçiriyor (B4) |
| PortmanBench | Taslak | Tohum: `testler/referans/` (28.09) | Uçtan uca ölçüm ve kritik hata türleri yok |
| Ön onay paketi | Taslak | Hedef format notu, 21.09 | Motor PDF'inde çalışma ön görünüşü ve basit özellik tablosu var; yan görünüş, Güncel Şablon 2024 düzeni, fiyat ve onay durumları yok |
| BOM'dan fiyat | Taslak | Fiyat MVP Excel'i · CTKBF V1.1 27.09'da incelendi, 19 bulgu | Canlı akışta fiyat yok |
| Çift doğrulama | Taslak | Tasarım, 27.09 (Z-10) | Prefabrikte ikinci motor yok |
| Kişisel veri: takma ad | Taslak | Günlüklerde numara maskeli; mesaj metni LLM'e olduğu gibi gidiyor (`llm.py`); Patron modunda yalnız Patron'un mesajları işleniyor | Takma ad ve saklama süresi yok |
| Aylık alan taraması | Canlıda doğrulandı | 27.09: ilk koşu başarılı, rapor üretildi | Sonraki koşu 1 Ekim |

## Açık riskler

- **Olumsuz ya da soru biçimli kısa cevap (pilot sınırlaması, 29.09).** Bekleyen pencere sorusuna "değiştirmeyin" gibi cevapta sistem "Anlayamadım." deyip soruyu yineler. Güvenlidir (pencere ve revizyon değişmez) ama nihai konuşma başarısı sayılmaz; LLM'in talimatı anlaması İE-03'ün açık gereksinimi.
- **Claude anahtarının son kullanma tarihi 29.10.2026.** Bitmeden VPS `agent.env` ve hosting `claude_api.json` birlikte yenilenmeli; yoksa hem Portman hem bayi botu durur.
- **Kişisel veri içeren geçici kopyalar.** VPS, hosting ve Mac'te duruyor; silinmeleri ayrı onayla (liste: `docs/is_emirleri/IE-02-canli.md` §7).
- **Sunucu erişimi.** root parolayla SSH girişi açık; ufw kuralları okunmadı. Anahtarla girişe geçmek canlı değişikliktir, onayla yapılır.
- **İmzasız paket kanalı.** Hostinge dosya yazabilen biri VPS'te kod çalıştırabilir (K14, K25).
- **Test verisinde olası kişisel veri.** `beyin/testler/mesajlar.json` vaka 1 (bkz. `testler/referans/README.md`).

Kapananlar (tarihli):
- **Sızan eşleşme anahtarı** — 22.09'da ekran görüntüsüyle sohbete girmişti; 28.09'da kapı C'de eşleşme ve OpenAI anahtarları yenilendi, eskileri 401 dönüyor.
- **B1** (belirsiz pencere isteğinde soru yerine İş Emri) — düzeltme 28.09 23:31'den beri canlıda; Opus'la kısa cevap yolu 29.09 21:09'da düzeltildi ve G yeniden denemesinde canlıda doğrulandı.
- **B2** (eski taslağın sessizce devralınması; D-01) — düzeltme 28.09 23:31'den beri canlıda, testleri geçiyor; canlıda gerçek mesajla henüz tetiklenmedi.

## İE-02 · Kalıcı akış (kapandı 29.09 22:30)

Dal: `ie-02`, 29.09'da `main`'e birleştirildi. İş emri: `docs/is_emirleri/IE-02.md`; canlı kayıt ve kapanış: `docs/is_emirleri/IE-02-canli.md` (§6 kapanış kaydı, §7 temizlik listesi).

Yapıldı:
- B2 düzeltmesi (D-01) ve B1 düzeltmesi;
- referansın PDF içeriğini izlemesi (D-02, `2026-09-28b`);
- Postgres üzerinde kalıcı akış (D-03, D-04);
- ajanın kalıcı modu, hosting bağlantısı (`api.php` v1.2, `feature.php` `context_id`), göç 002 (kabul ve teslim ayrı, onay zinciri), VPS kurulum betiği;
- dördüncü bağımsız incelemenin düzeltmeleri: Postgres kesintisinde mesaj kaybı yok, sonuç claim'den önce verilir, D-03 hosting'in 600 sn'sine sığar, hosting hata sınıfları, `worker=off` ile boşaltma, eşitleme ve onay sınırı, yeniden girişte boş veritabanı (`test_hosting_devri.py`);
- beşinci bağımsız incelemenin düzeltmeleri: bir işin devir hatası ötekini bekletmez, geçici hatada cevap atılmaz (uyarı), Postgres'e yazılamayan mesaj kuyruğu tıkamaz, açık iş varken yeni mesaj alınmaz, Meta'nın iletemediği metin uyarıya düşer, WhatsApp kimliği (numarayı içerir) günlüğe ve kanıt çıktısına yalnız özetiyle yazılır.
- altıncı tur (aynı inceleyicinin yeniden denetimi): devir hatasında hosting'e ulaşılabiliyor mu diye sorulur; işe özgü hatada aralıklı yeniden deneme (öteki işler beklemez), süpürme sınırına yaklaşan sonuç claim'den önce denenir, süpürme ancak hosting'e sorularak kabul edilir; yeniden kuyruğa konan mesajın süresi yeniden başlar.
- kapı D'nin ön koşulları (28.09 akşam, Lokman): yedeklerin otomatik silinmesi ayrı tercih, varsayılanı kapalı; geri yükleme denemesi yalnız kendi açıp işaretlediği veritabanını siler; yerel bağlantı şartı sağlanmıyorsa kurulum durur (`test_pg_kurulum.py`, 27 test);
- kapı A (28.09, salt okunur): canlı sürüm v1.1.1, beklenenle fark yok (VPS'teki uygulama, hosting paketi, hosting `feature.php` ve `api.php` tam hash'le); eşleşme anahtarı iki tarafta aynı; sızan anahtar büyük olasılıkla hâlâ etkin, kanıtlanmadı.
- kapı B (28.09): gerçek `lib.php`'nin temiz kopyasıyla (7. satırdaki iki numara sahte rakamlarla değiştirildi; orijinal Mac'ten çıkmadı) dört PHP takımı PHP 8.2.30'da ve 8.4'te 30/30, 16/16, 19/19, 18/18; ağsız ortamda, PHP ağ işlevleri kapalıyken de aynı.
- kuralı (Lokman, 28.09): dışarı aktarımda kişi adları da maskelenir; B'nin sınırlamaları kayıtta: medya indirme yolu sınanmadı, temiz kopyada bir ön ad kaldı.
- kapı C (28.09): eşleşme anahtarı (`3173020445c2` → `9238aa8aadce`) ve OpenAI anahtarı (`0acef17e0f05` → `4cf00ec74492`) yenilendi; eskileri hosting'te ve OpenAI'de 401; eski anahtarların kopyası kalmadı (`vps/kapi_c.py`, adımları Lokman yürüttü).
- kapı D (28.09): VPS'e PostgreSQL 16.15, yalnız yerel bağlantı; `portman` rolü ve veritabanı (parolasız peer); psycopg 3.3.6; günlük yedek 03:17, otomatik silme kapalı; yedek ve geri yükleme denemesi geçti; ajan yeniden başlamadı, dosya modunda.
- kapı E (28–29.09, kapandı):
  - `feature.php` ve `api.php` v1.2 ile paket yüklendi; ajan `vps-agent-v1.2`, dosya modunda.
  - Öz-test OpenAI'de kredi bitince (429) geçmedi. Lokman Claude'a geçişi istedi ve Opus 5.5'i seçti.
  - Geçişi başka bir ajan (Codex) yaptı; Portman çıkarımı ve bayi botu Opus 5.5'te. Asistan dosyalardan doğruladı; canlı `llm.py`, `ai.php` ve `claude_api.php` depoda (`hosting/`).
  - Öz-test Opus'la geçti. Opus maliyeti bildirildikten sonra Lokman'ın gönderdiği tek Patron mesajı ("Yeni talep: P6001 aynalı olsun") iş emri r01 üretti; metin + PDF telefona ulaştı. Sayaç: LLM 5/6, WhatsApp 2/6; Claude toplamı ~0,090 $.
- kapı F (29.09 18:14–19:10, kapandı):
  - `worker` off → boşalma → hosting ve VPS yedekleri (Mac kopyaları aynı özette) → göç ve içe aktarma (1 konuşma, 14 mesaj/iş) → kaynak ↔ Postgres 15/15 aynı → kalıcı mod (18:59) → kuyruk boş → `worker` vps.
  - E projesinin r01'i konuşma durumunda, iş sonucunda ve PDF'te korundu. Hosting yedeğinde E'nin iki mesajının Meta durumu `read`.
  - Model, anahtar ve paket değişmedi; LLM ya da WhatsApp çağrısı yapılmadı.
  - İki betik sorunu (sudo'nun girdiyi yutması; karşılaştırmanın PDF'i taşınmayan klasörde araması) veriye dokunmadı; düzeltildi, testlendi.
  - Kişisel veri içeren geçici kopyalar VPS'te, hosting'te ve Mac'te duruyor; silinmeleri ayrı onayla.

Kapı G ve yeniden denemesi (`docs/is_emirleri/IE-02-canli.md`):
- G (29.09 19:25–19:59; açık maddeleri yeniden denemede kapandı): 5 Patron mesajı; 5 LLM çağrısı, 26.731 + 1.381 token, 0,1345 $; 7 giden mesaj, hepsi okundu. Kabul: yeniden başlatmadan sonra soru kayıtlı, eski revizyon onayı reddedildi, güncel onay kabul edildi, tekrar gelen mesaj ikinci iş açmadı. Açık: G-1 kısa "değiştir" cevabı soruya bağlanmadı (`dustu`), G-2 r02 yerine r03, G-3 gerekçede yinelenen not. Pencere değişikliği çizimde doğru (Lokman). Yedekler öncesi ve sonrası Mac'te.

- G yeniden denemesi (onay 20:45; 29.09 21:05–21:34, **G KAPANDI**): düzeltme `ie-02`'ye alındı (`e726432`; `main` değil). Canlı paket `9c76af59…`, öncekinden (`f2bff20a…`) yalnız `beyin/karar.py` ve sürüm etiketiyle farklı; öz-test geçti, kalıcı mod, Patron modu, model ve anahtarlar korundu.
  - Yeni proje 2: r01; belirsiz pencere sözü soru açtı; "değiştirmeyin" soruyu yineledi (pencere ve revizyon değişmedi); yeniden başlatmadan sonra soru açık; "değiştir" soruyu `cevaplandi` kapattı ve aynı projede r02 üretti (YATAK ODASI 1 120x180, not bir kez).
  - r01 onayı reddedildi, r02 onayı kabul edildi; tekrar gelen mesaj ikinci iş açmadı.
  - Sayaçlar: 6/7 Patron mesajı, 7/9 LLM çağrısı (öz-test dahil), 37.356 + 2.522 token ≈ 0,1999 $ / 0,30 $, 8/12 giden; WhatsApp ücreti yok (1 Ekim öncesi).
  - Yedekler (öncesi ve sonrası, hosting paketi) Mac'te, özetler aynı.
  - "Değiştirmeyin"e "Anlayamadım" cevabı güvenli pilot sınırlaması; nihai konuşma başarısı sayılmaz.

İE-02, 29.09 22:30'da Lokman'ın onayıyla tanımlı kapsamıyla kapandı ve `main`'e birleştirildi (`a043d1a`). Canlı paket `9c76af59…` `e726432`'deki kaynaktan üretildi; pakete giren kaynaklar `main`'de aynı, fark yalnız sürüm etiketi (§6). Kişisel veri içeren geçici kopyaların silinmesi ayrı onay bekliyor (§7).

Canlı dışı kalan: `kos.py` sır taramasındaki telefon kalıbı; test verisinde takma ad.

## İE-03 · Kaynaklı hafıza (plan; ertelendi, silinmedi)

29.09 23:49: İE-03 planı duruyor. Üç parçası (kaynaklı aday bilgisi, kapsamlı olumsuzluk davranışı, düzeltme adayı kaydı) İE-04'e alındı. Geniş hafıza depoları ve ölçüm çalışması Aşama 2'den sonraya kaldı.


Plan: `docs/is_emirleri/IE-03.md` (`ie-03` dalı). 29.09 23:04: ana yön onaylandı (üç ayrı depo, mevcut altyapı); Aşama 0 envanteri yapıldı (`IE-03-envanter.md`: yalnız depo ve İE-02'nin maskelenmiş örnekleri; yeni veri alınmadı, ihtiyaç ve izin listesi §7) ve plan netleştirildi (kod/paket değişmeden kullanım, taslağı sistem hazırlar, kapsamlı olumsuzluk, aynı karar koduyla ve başlangıca göre ölçüm, üç iz, getirme sırası, Patron modunda bayi ayrımı testi). Uygulama, yeni veri paylaşımı, ücretli ölçüm ve canlı değişiklik ayrı onayla. Açık gereksinim (29.09): LLM'in bayinin talimatını anlaması ve doğrulanmış bayi düzeltmelerinden yararlanması; faydası ölçülerek kabul edilir.

Lokman'ın açık kararları: K16 (a/b), K3 ve K4, Z-03 ve Z-06 eşikleri. Ayrıntı: `KARARLAR/README.md`.

## Kaynaklar

- Zemin belgesi (sekmeler: Zemin, Güncel durum, Düzeltme kaydı, İlk iş emri, CTKBF): https://claude.ai/code/artifact/65844cef-e6c5-4a5d-b714-ee003c57fe5b
- Masaüstündeki "Claude Portman Çalışması" klasörü: DURUM.md (23.09 00:35), `07_Denetim/` (22.09 20:30), `08_VPS/hosting_paket/`, 10–13 numaralı klasörler (23.09), 14–22 numaralı klasörler (İE-02 kapıları A–G, 28–29.09).
