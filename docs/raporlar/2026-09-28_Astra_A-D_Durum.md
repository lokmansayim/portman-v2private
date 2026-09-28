# İE-02 · Kapı A–D durum raporu (Astra için) · 28 Eylül 2026, 23:00

Hazırlayan: Claude. Okur: Astra (ChatGPT). Dal: `lokmansayim/portman-v2private` → `ie-02` (bu rapor eklenmeden önceki uç `84092ca`). Ayrıntılı plan ve kanıt: `docs/is_emirleri/IE-02-canli.md`; özet: `DURUM.md`.

Bu raporda anahtar değeri, telefon numarası, kişi adı ya da mesaj metni yok. Anahtarlar yalnız SHA-256'nın ilk 12 hanesiyle (parmak izi) geçer.

Kanıtın kaynağı:
- Canlı sunuculardaki komutları Lokman kendi Mac Terminal'inden çalıştırdı. Asistanın VPS'in 22. portuna ağ yolu yok: Mac'teki yalıtılmış ortamda "Network is unreachable", bulut ortamında zaman aşımı.
- Değerlendirmeler, çıktı dosyalarının kendisinden yapıldı. Dosyalar Lokman'ın Mac'inde, `Claude Portman Çalışması/14_Kapi_A … 17_Kapi_D` klasörlerinde.

## 1. Kısa durum

| Kapı | Durum | Tek cümle |
|---|---|---|
| A · canlı sürüm (salt okunur) | Tamam | Canlıda v1.1.1 çalışıyor; denetlenen her şey tam hash'le beklenenle aynı. |
| B · gerçek `lib.php` ile PHP testleri | Tamam (sınırlı) | Dört takım PHP 8.2.30 ve 8.4'te tam geçti; ağsız ortamda koştu. |
| C · anahtar yenileme | Tamam | Eşleşme ve OpenAI anahtarları yenilendi; eskileri 401 veriyor, yenileri çalışıyor. |
| D · VPS'e Postgres | Tamam (kurulum kapsamı) | PostgreSQL 16.15 yalnız yerel; yedek ve geri yükleme denemesi geçti; ajan dosya modunda. |
| E · hosting PHP + paket | Onay bekliyor | Maliyet, sınır ve 12 hata notu hazırlandı. Yükleme ve ücretli deneme yapılmadı. |
| F, G, H | Onay bekliyor | Dokunulmadı. |

## 2. Kapı A · canlı sürüm (salt okunur)

VPS'te `vps/kapi_a_salt_okunur.sh` çalıştı (sha256 `56960c3c…`). Lokman ayrıca hosting'ten `feature.php` ile `api.php`'yi indirip SHA-256'yı kendi hesapladı.

| Denetlenen | Sonuç |
|---|---|
| VPS'teki uygulama ↔ paket | 48/48 dosya aynı; `agent.py`, `worker.py`, `karar.py`, `dxf_out.py` ve `cikarici.py` beklenen hash'lerle aynı |
| Paket | `bd1ca27c22d7b5c06722d0ddab855a5c2d821c96e78cc1049afe0c6e78b7a408`, 639.306 B. Hosting'in dağıttığı baytların hash'i VPS'te tam olarak hesaplandı; `current.sha256` ve `vps-health.json` ile aynı |
| `api.php` | `455f8c74…a0867`, 16.675 B = git `a3050c3`, v1.1 zip'i |
| `feature.php` | `91c954a6…5d0e`, 24.111 B = git `d3d18e5`, v1.0 zip'leri |
| Ayarlar | açık, `worker` vps, Patron, `dry_run` kapalı, `vps_komut` kapalı; saat farkı 0 sn |

`health.json`'daki `kanal-v1.0` etiketi bir fark değil. Dosyayı `feature.php` yazıyor ve kendi sabitini koyuyor (satır 13 ve 248); `feature.php` v1.0'dan beri değişmedi. Paketin, `api.php`'nin ve ajanın ayrı sürüm etiketleri var.

Sızan anahtar A'da "büyük olasılıkla etkin, kanıtlanmadı" diye kaydedildi. C bu soruyu kapattı (4. bölüm).

## 3. Kapı B · gerçek `lib.php` ile PHP testleri

**Dosyanın hazırlanması:**
- `public_html/portman/lib.php` (28.004 B) Lokman'ın Mac'inde tarandı; değer yazdırılmadı (`denetim/lib_tara.py`).
- Anahtar, parola ya da e-posta yok. 7. satırda iki telefon numarası var (`PM_RECIPIENTS`); yalnız görünen adı seçmek için kullanılıyor.
- `lib.clean.php` yalnız bu iki numarayı aynı uzunlukta sahte rakamlarla değiştirdi. Yeniden tarama temiz; kod iskeleti aynı; değişen tek satır 7.
- Asistanın ortamına yalnız `lib.clean.php` gitti; testten sonra silindi. Orijinal Mac'ten çıkmadı.

**Test kancaları:**
- `pm_remote`: `PM_OFFLINE_TEST` + `pm_test_remote`.
- `pm_stream_media`: `PM_OFFLINE_TEST` + `pm_test_stream`.
- Bütün `curl` çağrıları bu iki işlevde.

**Test ortamı:**
- PHP 8.2.30, php-src'nin resmî `php-8.2.30` etiketinden derlendi (commit `b233e9d0`). Hosting de 8.2.30 kullanıyor.
- Testler yalnız loopback olan ayrı bir ağ ad alanında koştu; dış bağlantı denemesi başarısız oldu.
- Ayrıca PHP'nin ağ işlevleri (`curl_init`, `curl_exec`, `fsockopen` …) kapatılarak yinelendi; sonuç aynı.

| Takım | PHP 8.2.30 | PHP 8.4.21 |
|---|---|---|
| `offline_test.php` | 30/30 | 30/30 |
| `baglanti_test.php` | 16/16 | 16/16 |
| `e2e_vps.py` | 19/19 | 19/19 |
| `e2e_kalici.py` | 18/18 | 18/18 |

Uyarı ya da kullanımdan kalkma bildirimi çıkmadı.

**Lokman'ın kayıtta tuttuğu sınırlamalar:**
1. Medya indirme yolu (`pm_download` → `pm_stream_media`) sınanmadı; testler oraya girmiyor. Bu yol İE-02'de değişmedi.
2. Temiz kopyada bir kişinin ön adı kaldı. Tarayıcı kişi adı aramıyordu. Kural: bundan sonra dışarı aktarımda kişi adları da maskelenir; tarayıcıya ad denetimi eklenmeden yeni bir aktarım yapılmaz.

## 4. Kapı C · anahtar yenileme

Adımları `vps/kapi_c.py` sıraladı: hazirla → yenile → ara → yeniden_baslat → bitir. Betik, önceki adım geçmeden sonrakini çalıştırmıyor. Sahte hosting, sahte OpenAI ve sahte systemctl ile uçtan uca sınandı (`test_kapi_c.py`).

Denetimlerin hepsi ücretsiz: hosting'e `op=settings`, OpenAI'ye `GET /v1/models`. OpenAI'nin hata mesajı anahtarın bir parçasını içerdiği için yalnız hata kodu yazıldı.

| Anahtar | Eski → yeni parmak izi | Eskisi | Yenisi |
|---|---|---|---|
| Eşleşme (VPS ↔ hosting) | `3173020445c2` → `9238aa8aadce` | hosting 401 (22:03 ve 22:23) | hosting 200; çalışan süreç ve dosya aynı |
| OpenAI | `0acef17e0f05` → `4cf00ec74492` | OpenAI 401 `invalid_api_key` (Lokman iptal etti) | OpenAI 200; hosting'in verdiği anahtar bu |

- Eski iki anahtar iptal denetimi için geçici, root'a özel bir klasörde tutuldu ve son adımda silindi. `agent.env` yedeğinde anahtar satırı yok. Geri dönüş yolu yeni bir anahtar daha üretmek; eskiler yeniden kullanılmaz.
- Sohbet botu (`ai.php`) OpenAI anahtarını kendi içinde tutmuyor. `ayarlarOku()` → `developer/veri/ayarlar.json` yolunu izliyor; Portman da `settings.json` → `ayarlar_json` ile aynı dosyayı okuyor. Bu yüzden bot yeni anahtara kendiliğinden geçti. Bu koddan gösterildi; **gerçek bir mesajla denenmedi** (ücretli; ayrı onay).
- Yan bulgu (C'nin kapsamı dışında): `developer/config.php`'de WhatsApp erişim anahtarı, doğrulama belirteci ve panel parolası kodun içinde yazılı. Değerleri görülmedi, yalnız türleri ve satırları.

## 5. Kapı D · VPS'e Postgres (kurulum kapsamı)

`vps/pg_kurulum.sh` kurdu, `vps/kapi_d_dogrula.sh` salt okunur doğruladı. Çıktılar `17_Kapi_D/1_kurulum.txt` ve `2_dogrula.txt`.

- **Sürüm:** PostgreSQL 16.15 (`16.15-0ubuntu0.24.04.1`). Küme `16/main` çevrimiçi; servis açık ve açılışta başlıyor.
- **Yalnız yerel bağlantı:** `listen_addresses` localhost; 5432'yi yalnız `127.0.0.1` dinliyor; `pg_hba`'daki TCP kuralları yalnız `127.0.0.1` ve `::1`; güvenlik duvarı açık, 5432 kuralı yok. Bu koşullar sağlanmasaydı betik dururdu; bu davranış test edildi.
- **Rol ve veritabanı:** `portman` rolü parolasız (peer), süper kullanıcı değil, veritabanı ya da rol açamıyor. `portman` veritabanının sahibi `portman`; 0 tablo. Ajanın ortamında psycopg 3.3.6 (saf Python, libpq 16.15) bağlanıyor.
- **Yedek:**
  - cron 03:17'de; otomatik silme kapalı (açmak ayrı tercih);
  - deneme yedeği, kendi açıp işaretlediği ayrı veritabanına geri yüklendi, sonra silindi; kalıntı 0;
  - deneme yedeği `pg_restore --list` ile okunuyor.
- **Portman servisi:** PID 86646 kurulumdan önce ve sonra aynı; kurulum sırasında Ubuntu'nun servisleri kendiliğinden yeniden başlatması askıya alındı. Dosya modunda: `PORTMAN_PG_DSN` yok, `pg.env` yok, ek yapılandırma yok. Bekleyen sonuç 0; hosting ajanın anahtarını kabul ediyor.
- **12 `api:` hatası** (`gunluk_api_hatalari.sh`, salt okunur):
  - hepsi HTTP 401 `unauthorized` (11 `settings`, 1 `claim`);
  - hepsi 22:00:54–22:03:51 arasında, 16 sn aralıkla;
  - C'de hosting'e yeni anahtar yazıldıktan sonra, 22:03:53'teki yeniden başlatmadan önce; sonrasında 0.
  - Not kapandı.
- **Sınırlar:**
  - Veritabanı boş olduğu için geri yükleme denemesi yedekten geri yüklemeye giden zinciri kanıtlıyor, veriyle doğruluğu değil. Veriyle doğruluk yerelde sınandı (T8); canlı veriyle ilk yedek F'de alınacak.
  - İlk otomatik gece yedeği henüz görülmedi (29.09 03:17).
  - Yedekler yalnız VPS diskinde; sunucu dışı yedek yok.

## 6. Kapı E hazırlığı (onay bekliyor)

**Maliyet** (resmî kaynaklar, 28.09):
- **OpenAI `gpt-4o-mini`:** 1M giriş 0,15 $, 1M çıkış 0,60 $. Kullanımdan kaldırılanlar listesinde yok.
  - Planlı çağrı: 2 (paket öz-testi + 1 Patron mesajı). Tekrarlarla en çok 4; sınır 6.
  - Bol payla (çağrı başına 5.000 giriş, 500 çıkış) 6 çağrı en çok ~0,006 $.
- **WhatsApp:** Meta'nın "Non-template message pricing" sayfasına göre servis mesajları 1 Ekim 2026'ya dek ücretsiz. Sonra mesaj başına, pazarın utility oranıyla ücretlendirilir; hacim kademesi yok.
  - Türkiye, 1 Ekim oran değişikliği listesinde yok; 1 Temmuz 2026 fiyat dosyasındaki oran geçerli.
  - Bu oran dosyadan okunamadı: bağlantılar sayfa metninde yok. E 29 ya da 30 Eylül'de yapılırsa WhatsApp payı 0'dır. Sonra yapılırsa Lokman USD fiyat dosyasını indirir, asistan Türkiye satırını okur.

**Aşılmayacak sınır:**
- En çok 2 Patron deneme mesajı: biri planlı; ikincisi yalnız ilki kod dışı bir nedenle cevapsız kalırsa.
- En çok 6 OpenAI çağrısı, en çok 6 giden WhatsApp mesajı.
- Beklenenden fazla cevap ya da tekrar eden çağrı görülürse `worker: off` ile durdurulur, E.5 ile geri alınır.

**Korunan koşullar:**
- Önce `feature.php`, `api.php` ve paket yedeklenir.
- Üzerine yazmadan önce iki PHP dosyası A'daki tam hash'le karşılaştırılır; farklıysa E durur.
- Ajan dosya modunda kalır; F'ye geçilmez.
- G'nin denemeleri E'nin onayına dahil değildir.

E'de ajan, yeni paketle kendini günceller (`vps-agent-v1.2`) ve yeniden başlar. Paket öz-testi bir kez gerçek LLM çağrısı yapar; WhatsApp'a göndermez.

## 7. Açık noktalar (hiçbiri E'yi engellemiyor)

- Sohbet botunun yeni OpenAI anahtarıyla gerçek cevabı denenmedi (ücretli; ayrı onay).
- Medya indirme yolu B'de sınanmadı.
- İlk gece yedeği henüz görülmedi; sunucu dışı yedek yok.
- Mac'teki hassas yerel kopyalar silinmedi; silme ayrı onay bekliyor. Bunlar `16_Kapi_C/config.php`, `ai.php`, `settings.json` ve `15_Kapi_B/lib.php`, `lib.clean.php`.
- `config.php`'de kodun içinde duran WhatsApp anahtarı ve panel parolası İE-02'nin kapsamı dışında; ayrı bir iş olarak ele alınabilir.

## 8. Depoda bakılacak yerler

- Plan ve her kapının sonucu: `docs/is_emirleri/IE-02-canli.md` (bölüm 0 kısa özet; bölüm 4 kapılar; bölüm 5 kalan riskler).
- Betikler:
  - `vps/kapi_a_salt_okunur.sh`, `vps/kapi_c.py`, `vps/pg_kurulum.sh`, `vps/kapi_d_dogrula.sh`, `vps/gunluk_api_hatalari.sh`;
  - `denetim/lib_tara.py`.
- Testler (`testler/kalici/`, 185/185): `test_lib_tara.py`, `test_kapi_c.py`, `test_pg_kurulum.py`.
- Bu turun commit'leri: `48329ec` (A), `15d32a2` (B), `cf26239` · `377d126` · `f8bd57c` (C), `055fad9` · `fbec86a` (D), `cdd7e23` · `84092ca` (E hazırlığı ve 12 hata notu).
