# Kalıcı akış ve kanal testleri (İE-02, İE-04, İE-06)

Postgres üzerinde kalıcı konuşma ve iş akışının kabul testleri (İE-02) ile tek sunuculu kanalın (İE-06) birim ve betik testleri. İş emirleri: `docs/is_emirleri/IE-02.md`, `IE-06.md`. Kod: `kanal/depo.py`, `kanal/kalici.py`, `kanal/webhook.py`, `kanal/gonderici.py`, `kanal/panel.py`, `kanal/meta_api.py`, `kanal/goc/`, `vps/`.

## Koşum

Gerçek bir Postgres gerekir (16 ile sınandı). Adres ortam değişkeniyle verilir; yoksa testler atlanır. Her test kendi veritabanını açar ve siler.

```
PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python -m pytest testler/kalici -q
PORTMAN_TEST_PG="…" python testler/kalici/kabul_gosterimi.py --rapor kabul.md
```

## Neyin gerçek, neyin simülasyon olduğu

| Gerçek | Simülasyon |
|---|---|
| Postgres 16; göçler; işlemler; kilitler | Gelen WhatsApp mesajı: kuyruk satırı elle üretilir (`conftest.mesaj`; İE-06 testlerinde imzalı sahte Meta olayı, `test_webhook.py`) |
| Beyin kural katmanı (`karar_ver`), `worker.isle`; webhook, gönderici ve panel WSGI uygulamaları doğrudan | LLM çıkarımı kayıtlıdır (manuel arka uç) |
| Motor: `test_yeniden_baslatma.py`, `kabul_gosterimi.py` ve `kanal/tests/e2e_vps_kanal.py`'de gerçek; öteki testlerde hızlı sahte üretici | Gönderim sahte göndericiyle (`SahteWhatsApp`) ya da sahte Graph API ile (`sahte_meta.py`); betikler `PM_*` değişkenleriyle sahte dizin ve sahte komutlarla (systemctl, rclone, age, sshd) |
| Ayrı işleyici süreçleri; süreç öldürme (SIGKILL) ve yeniden başlatma (SIGTERM) | Zamanın geçmesi, konuşmadaki zamanlar geriye alınarak taklit edilir (D-01'in 2 saati) |

Gerçek WhatsApp ve gerçek LLM ile denenmedi. Bu testler canlı doğrulama değildir.

## Testler

| # | Test | Dosya |
|---|---|---|
| T1 | Aynı mesaj tekrar ya da eşzamanlı gelir (8 iş parçacığı): tek iş; D-01 sorusu askıdayken tekrar gelen mesaj sayacı artırmaz | `test_kalici.py` |
| T2 | D-01 sorusu ("yeni" ve "değişiklik"), B1 pencere sorusu, eksik bilgi sorusu: soru bir süreçte sorulur, cevap yeni bir süreçte doğru soruya ve projeye bağlanır | `test_kalici.py` |
| T3 | Yarım iş: süreç Motor sırasında öldürülür, yeniden başlayan işleyici bitirir; LLM yeniden çağrılmaz; üç denemede bitmeyen iş başarısız sayılır, bayiye ve Patron'a bildirim yazılır | `test_yeniden_baslatma.py` (gerçek süreç ve Motor), `test_kalici.py` |
| T4 | Eski sürümle yazma reddedilir; kirası devredilen işin geç sonucu atılır; üç işleyici eşzamanlı çalışırken art arda iki değişiklik sırayla işlenir ve ikisi de son revizyonda olur | `test_kalici.py` |
| T5 | Sonucu belirsiz gönderim yeniden gönderilmez; yarıda kalan gönderim belirsiz sayılır; kesin gönderilmeyen satır işaretlenir | `test_kalici.py` |
| T6 | Başka numaranın revizyonu ve çıktısı okunamaz; bir bayinin onayı ya da cevabı ötekinin kaydını değiştirmez | `test_kalici.py`, `test_inceleme.py` |
| T7 | Yeni revizyon iletilmeden yazılan onay, eski revizyonu alıntılayan onay ve iletimi belirsiz revizyona gelen onay kaydedilmez | `test_kalici.py` |
| T8 | `pg_dump` yedeği ayrı bir veritabanına `pg_restore` ile yüklenir; bütün tablolar aynı; askıdaki soru oradan doğru cevapla sürer; asıl veritabanı etkilenmez | `test_kalici.py` |
| T9 | Dosya düzeni (`durum/*.json`, `state.json`) → Postgres → dosya düzeni kayıpsız; askıdaki D-01 sorusu geçişten sonra cevaplanır; işlenmiş mesaj yeniden işlenmez | `test_kalici.py` |
| T10 | Kabul gösterimi (aşağıda) | `kabul_gosterimi.py`, `test_kabul.py` |
| İnceleme | Bağımsız incelemenin (28.09) bulguları ve yakalanmayan mutasyonlar. İşin bitişi yazılamazsa hiçbir sonuç kalmaz; mesaj ve iş birlikte yazılır (ikisi de tetikleyiciyle sınanır). İlk yazmada da sessiz ezme olmaz. Kirası devredilen işin eski sahibi yazamaz. Süresi dolan D-01 sorusundan sonra gelen onay da denetlenir. Soru kaydı cevaplandı, düştü ya da devredildi diye doğru kapanır. Aynı bayi kodlu iki numara birbirinin kaydını göremez ve aynı İş Emri numarası üretilse de dosya ezilmez. Değişmiş PDF gönderilmez. Geç gelen gönderim teyidi kaybolmaz. İşlenmekte olan mesaj varken geçiş yapılmaz. SIGTERM'de eldeki iş bitirilir. İkinci tur: PDF yolu kayıtta ve satırda yerinde, hazırlık klasörü temiz; çakışmada taşınan dosya silinir; kayıt yazıldıktan sonra bağlantı koparsa PDF yerinde kalır; hiçbir şey sorulmadıysa soru kaydı açılmaz. | `test_inceleme.py` |

## Tarihli kapı testleri (İE-02, İE-04)

- `test_lib_tara.py` (kapı B): `denetim/lib_tara.py` sahte sırları (anahtar, telefon, e-posta, sır adlı değer, kodda uzun sayı) bulur ve değerlerin hiçbirini ya da 8 karakterlik bir parçasını yazdırmaz; temiz kopya yalnız değerleri değiştirir; özgünün üzerine yazmaz.
- `test_kapi_c.py` (kapı C): `vps/kapi_c.py` sahte hosting, sahte OpenAI ve sahte systemctl ile uçtan uca: adım sırası zorunlu, eski anahtar iptal edilmeden bitmez; hiçbir çıktıda anahtar parçası yok.
- `test_kapi_m.py` (İE-04 kapı M): `vps/kapi_m_goc.sh` göç 003'ü yalnız ön koşullar tutunca uygular; fikstür 30.09'daki paket düzenini (göç 001–003) kopyalar.
- İE-06 ile kaldırılanlar (sınadıkları kod artık yok): `sahte_hosting.py`, `test_hosting_devri.py`, `test_baglanti.py`, `test_kapi_f.py`, `test_kapi_g.py`, `test_vps_betikleri.py`, `test_bagimliliklar.py`, `test_llm_opus.py`, `test_pg_kurulum.py` (`pg_kurulum.sh`'nin yerel bağlantı, sahiplik ve geçici küme denetimleri `test_kurulum.py`'ye taşındı). Git geçmişinde `bc2bdc0`'da dururlar.

## Tek sunuculu kanal (İE-06)

| Test | Ne sınar |
|---|---|
| `test_meta_api.py` | İmza (HMAC-SHA256, sabit zamanlı), hub doğrulaması, gelen olay çözümü (metin, buton, liste, medya, konum), dosya denetimi (yol, imza, boyut), yük kurucuları ve Cloud API sınırları (`feature.php` ile aynı sayılar), Graph istemcisi (gönderim, medya yükleme/indirme), anahtar maskeleme |
| `test_webhook.py` | `GET /webhook` hub, `POST /webhook` imza/413/400, yakalama kuralları (`enabled`, `enabled_at`, 15 dk, `phone_number_id`), tekilleştirme (`mesajlar.id`, `webhook_olaylar`), `mode` kararları, kayıtsız gönderen ve sabit cevap sıklığı, durum bildirimleri (`biz_opaque_callback_data`, sıra, failed), medya kaydı, `/saglik` (nabız yaşı, `nabiz.sh` sorunları → 503), işlenemeyen olayda 503 |
| `test_gonderici.py` | `pm_kanal_send` kuralları: metin/belge/görsel/etkileşim yükleri, medya yükleme ve yeniden deneme (`YenidenDene`), belirsiz cevap, `dry_run` ve kapalı kanal, PATRON bildirimi ve 24 saat penceresi, gelen medya indirme (`gelen_medya/`), nabız |
| `test_panel.py` | Giriş (scrypt, ön çerez + CSRF), 5 başarısız girişte 15 dk kilit (IP özeti başına; başka IP girer), imzalı oturum çerezi (sahte/süresi dolmuş ret), CSRF'siz POST 403, bayi ekle/düzenle (numara değişmez, aktif kapatılır, HTML kaçışı), gelen kutusu, konuşma sayfası, dosya indirme yalnız `gelen_medya` altından, güvenlik başlıkları, çıkış |
| `test_bayi.py` | Bayi kimlik kartı alanları, kod türetme (`PATRON`, `B` + son 4), `gelen_bayisi` (pasif → None), olay tekilleştirme, durum satırı eşleşmesi |
| `test_bayi_kaydi.py` | İE-22 WhatsApp'tan bayi kaydı (sahte Meta webhook gövdeleri, sahte Graph API): ayar kapalıyken bugünkü sabit cevap; ad → firma → Patron'a [Onayla] [Reddet] + şablon; geçersiz cevap, cevap sınırı, zaman aşımı, günlük tavan; kartı olan numara akışa girmez; Onayla (LLM'siz) → kart, karşılama; Reddet → 30 gün sabit cevap; yarış (`Cakisma`); yabancı düğme; gönderici penceresi; panel Onayla/Reddet/Reddi geri al |
| `test_goc_eklemeli.py` | Göçlerde DROP/RENAME/daraltma/varsayılansız NOT NULL yok; her göç tekrar koşulabilir; eski sürüm kodu yeni şemada çalışır |
| `test_kurulum.py` | `vps/kurulum.sh` sahte dizinlerde ve yerel Postgres'te: dizinler, dağıtım anahtarı (yalnız açık anahtar ekrana), `settings.json` varsayılanı `ayarlar.VARSAYILAN` ile aynı, `panel.env` oturum anahtarı (yazdırılmaz), gömülü systemd/nginx/sshd/fail2ban/logrotate dosyaları depodakilerle birebir, sshd drop-in yalnız `authorized_keys` doluyken ve bozuk sözdiziminde geri alınır, sertifika/DNS kararı, ikinci koşu korur; Postgres: yalnız yerel dinleme, sahiplik, yerel olmayan kümede durur ve hiçbir şey oluşturmaz |
| `test_surum.py` | `guncelle.sh` (yerel çıplak git deposu; açıklamalı etiket ve `origin/main` denetimi; `git archive`; içe aktarma denetimi; göçler; bağlantı değişimi; sağlık 503'te kendiliğinden geri dönüş), `geri_don.sh`, `surum_temizle.sh` (onaysız silmez), `sir_koy.py` (biçim, atomik 0600, parmak izi, doğrulama yerel sahte sunucuya), `panel_parola.py`, `yedek_kur.sh`, `yedek.sh` (sahte rclone/age/pg_dump; `nabiz/` ve `checks/` yedeğe girmez; yerelde 3), `yedek_geri_dene.sh` (işaretli deneme veritabanı), `nabiz.sh` + `uyari_gonder.py` (pencere, sıklık), `ayar.sh`, `oz_test.sh`, `kuru_kosu.sh` (imza), `arsiv_al.sh`, `durum.sh` (maskeli) |
| `test_e2e_vps_kanal.py` | `kanal/tests/e2e_vps_kanal.py`'yi koşturur: sahte Meta → webhook → Postgres → ajan (ayrı süreç, gerçek Motor) → gönderici → durum bildirimi → buton cevabı/onay zinciri; katman kapalı; kayıtsız numara; gelen görsel; panel; `/saglik` (42 vaka) + İE-07 bölüm 8 + İE-08 bölüm 9 (çelik: kabul kaydı → "Ç8801" → üç çatı seçeneği → düğme → r01 genel motordan, PDF antet, Meta çağrıları) + İE-22 bölüm 13 (WhatsApp'tan bayi kaydı: ad → firma → Patron'a düğmeli talep → Onayla → kart, karşılama şablonu → "Nasıl çalışır?" PDF'i; panel) |
| `test_celik_akisi.py` | İE-08 8a PR-2a çelik akışı A2–A3: K-A10 kapısı (kabul kaydı yokken sunulmaz), "Ç8801" → çatı seti (öncelik sorusu yok, 3 düğme + bileşik görsel), "88 m² 2+1 çelik" → alan seti (görselde Ç8801 üçlüsü), kat süzgeci ve uyan yoksa bugünkü davranış, dış ölçü → alan yolu (GRID yok); seçim → r01 (zarf `yapi.sistem celik`, tanım gömülü değil, sha; satırlar etkileşim + belge `Portman_<no>_rNN.pdf`; CTA yok; set `secildi`; konuşma sıfırlanmaz), varyant/KT kodu doğrudan r01 (KT adsız), D-09 (Patron ve kart dışı numara antete girmez, LLM müşteri telefonu kullanılmaz), çizim düşünce `dogrulanmadi` + maskeli Patron iletisi; gerçek genel motorla r01 (PDF 2 sayfa, TASLAK, ad + kart numarası, bayi görseli, IFC, liste) |
| `test_aday_kabul.py` | `araclar/aday_kabul.py` (K-A10): yalnız verilen kodlar `gecerli` + `muhendis_kabulu`; `kabul_edilmis_adaylar` yalnız onları döndürür; upsert; ad çıktıda yok; olmayan kod ve bozuk tarih DUR; `--kuru` yazmaz |

## Kabul gösterimi

`kabul_gosterimi.py` şu sırayı koşar ve her adımı veritabanından denetler:

1. Bayinin açık bir projesi var: r01 üretilmiş ve gönderilmiş.
2. WhatsApp talebi gelir ve kaydedilir.
3. Portman netleştirme sorusu sorar (D-01).
4. İşleyici süreci durdurulur ve yeniden başlatılır.
5. Cevap doğru soruya ve projeye bağlanır; r02 r01'den devam eder.
6. PDF gönderilir.
7. Aynı mesaj yeniden gelir; ikinci iş oluşmaz.
