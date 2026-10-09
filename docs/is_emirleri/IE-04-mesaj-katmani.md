# İE-04 · WhatsApp mesaj katmanı (kanal v1.3) · tasarım kaydı, 30.09.2026

Onay: Lokman 30.09 07:54, yalnız yerel geliştirme ve test. Canlıya alınması (hosting PHP, paket, göç 003, 3D barınağı) ayrı onay.

Amaç: kanvasın 1–4. adımlarını bugünkü kanal üzerinde taşımak. Taşıyıcı değişmez (WhatsApp → hosting → VPS → Beyin/Motor → hosting → WhatsApp); üstüne dört giden mesaj türü ve gelen cevapların kimlikle bağlanması gelir.

## Giden satır türleri (ajan → `api.php` → `feature.php`)

Bugün: `text`, `document` (PDF). Eklenenler:

| kind | Alanlar | Meta payload |
|---|---|---|
| `image` | `file` (PNG/JPEG, ≤5 MB), `filename`, `mime`, `sha256`, `body` (altyazı ≤1024) | `type: image` |
| `interactive` | `body` (panel ve yedek metin), `interactive` = {`type`: `button` \| `list` \| `cta_url`, `header`?, `body`, `footer`?, `action`}; başlık görseli için `file`/`mime`/`sha256` üst düzeyde | `type: interactive` |

Sınırlar (WhatsApp Cloud API): buton ≤3, başlık ≤20; liste düğmesi ≤20, toplam satır ≤10, satır başlığı ≤24, açıklama ≤72, kimlik ≤200; gövde ≤1024; `cta_url` `display_text` ≤20. PHP gönderimden önce yeniden doğrular; sınırı aşan satır gönderilmez (`upload_failed`, hata metniyle).

Dosyası olan her satırda (`document`, `image`, başlık görselli `interactive`) `file` üst düzeydedir: `api.php` dosyayı `projects/<no>/rNN/` altına alır (PDF `%PDF-`, PNG `\x89PNG`, JPEG `\xFF\xD8` başlığı; boyut sınırı), `feature.php` medya olarak yükler.

## Gelen cevap kimlikleri

`feature.php::pm_kanal_capture` kuyruk satırına ekler: `reply_id` (`interactive.button_reply.id` ya da `list_reply.id`; şablon butonunda `button.payload`), `reply_kind`. `context_id` zaten var (İE-02): cevabın hangi giden mesaja verildiği (wamid → `giden.dis_id`).

**Kimlik dilbilgisi** (ajan üretir, kendini anlatır; veritabanı sırası gerekmez):

| Kimlik | Anlamı | Güncellik koşulu |
|---|---|---|
| `s:<set>:<kod>` | seçenek setinden aday seçimi (`set` = `ss_` + sha256(kaynak mesaj id)[:16]) | set konuşmadaki açık set ve `durum = acik` |
| `o:<is_emri_no>:<rev>` | planı onayla | `son_is_emri` aynı numara ve revizyon, aşama `onay_bekliyor` |
| `r:<is_emri_no>:<rev>` | revizyon iste | aynı |
| `q:<alan>:<deger>` | bekleyen sorunun kısa cevabı (`pencere_islem:degistir`, `yeni_mi_degisiklik:yeni`, `oncelik:butce` …) | `son_soru_alani = alan` |

Kural: **görünen başlık metni tek başına seçim kimliği sayılmaz.** Kimlik çözülür, `context_id` ile geldiği giden satır bulunur ve kimliğin o mesajın butonları arasında olduğu doğrulanır; sonra güncellik koşulu denetlenir. Koşul sağlanmıyorsa hiçbir durum değişmez; bayiye "bu buton eski (…); güncel durum …" denir. Geçerli kimlik LLM çağrılmadan kural katmanına deterministik bir Talep olarak girer (`meta.backend = "etkilesim"`). Serbest metin bugünkü gibi LLM'den geçer; "P9401 olsun" gibi metinle seçim de açık seti kapatır.

## Akış (kanvas 1–4)

1. **Tarif.** Bugünkü çıkarım ve kural katmanı. Eksik bilgi soruları, cevap uzayı küçükse buton taşır (`q:` kimlikleri). Öncelik sorusu (`oncelik`: bütçe / yaşam alanı / montaj) yalnız aday kaydında ≥2 aday varsa sorulur; ağırlıklar geçici (karar bekliyor).
2. **Seçenek + puan.** Talepte oda programı ve alan (ya da dış ölçü) varsa aday kaydından uygun adaylar süzülür (K-A1 bekleyen: geçici olarak katalog m² ±%10), sabit ağırlıkla puanlanır, hesabı yazılır. Giden: en çok üç planın bileşik görseli + 3 seçim butonu (`s:`) ve tam liste (`list`, ≤10). Üç geçerli aday yoksa sayı tamamlanmaz, mesaj durumu söyler; hiç aday yoksa bugünkü davranış (katalog kodları metin olarak, `sor`).
3. **Seçim + revizyon.** Seçim → adayın İş Emri'nden r01 (Motor). Giden: bayi plan görseli (İş Emri'nden üretilir) + butonlar `o:` Onayla, `r:` Revize et, (`cta_url` 3D). Ölçülü PDF belge olarak. Revizyon isteği serbest metinle: bugünkü pencere/ayna yolu; r02 aynı projede.
4. **3D.** Aynı İş Emri'nden IFC ve statik görüntüleyici. Bağlantı butonu yalnız `ucb_taban_url` ayarı varsa; yoksa metin "3D bağlantısı henüz yayınlanmadı". Barınak canlı karardır.

## Kayıt (göç 003, yalnız ekler)

- `giden.kind`: `image`, `interactive` eklenir.
- `revizyonlar.ekler jsonb`: türetilmiş dosyalar (`gorsel`, `ifc`, `ucb`) yol ve özetleriyle.
- `secenek_setleri`: set kimliği, gönderen, proje, kaynak mesaj, adaylar (kod, puan, gerekçe), durum (`acik`, `secildi`, `eskidi`, `dustu`), seçilen kod, seçim mesajı.
- `adaylar`: aday kaydı (kod, durum `test`/`kosullu`/`gecerli`, kaynak, denetim sonucu, mühendis kabulü). Şablonlar pakette (`is_emri/adaylar/`), kabul kaydı burada; kalıcı modda `gecerli` aday ancak kabul kaydı varsa sunulur. `test` adaylar yalnız `settings.test_adaylari = true` iken (yerel).

## Değişen dosyalar

`kanal/feature.php`, `kanal/api.php` (v1.3); `kanal/worker.py`, `kanal/kalici.py`, `kanal/depo.py`, `kanal/goc/003_mesaj_katmani.sql`; `beyin/karar.py`, `beyin/sema.py` (Karar'a isteğe bağlı alanlar), `beyin/katalog.py` (aday kaydı), `beyin/secenek.py` (süzme ve puan), `motor/bayi_gorseli.py`, `motor/ifc_uret.py` (23.09 kodundan modül), `vps/agent.py` (dosyalı satır genel). Testler: `kanal/tests/offline_test.php` (genişletme), `testler/kalici/test_etkilesim.py`, harness değişmez.

## Gerileme

Harness 22/22; `testler/` tümü; `testler/referans/dogrula.py` parmak izleri (Motor PDF'i değişmez; bayi görseli ayrı dosya); P6001 G senaryosu butonlarla ve metinle aynı sonucu verir.
