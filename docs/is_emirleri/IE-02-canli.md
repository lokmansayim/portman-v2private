# İE-02 · Canlıya bağlama planı (Patron numarası)

Dal: `ie-02`. Dayanak: Astra'nın 28 Eylül ikinci değerlendirmesi, D-03 ve D-04. Bu plan onaya sunulur. Her kapı (A–H) ayrı açık onayla açılır; onaylanmayan kapıdan sonrası yapılmaz. Sunucu komutlarını Lokman kendi terminalinden çalıştırır. Hiçbir komut anahtar değeri yazdırmaz; anahtarlar yalnız 12 haneli özet parmak iziyle karşılaştırılır.

## 0. Kısa özet

**Kapılar.** A (salt okunur) 28.09'da onaylandı ve yapıldı: canlı sürüm v1.1.1; VPS'te ve hosting'te denetlenen her şey beklenenle aynı (hosting PHP dosyaları tam hash'le); eşleşme anahtarı iki tarafta aynı; sızan anahtar büyük olasılıkla hâlâ etkin, kanıtlanmadı (ayrıntı A'da). B de 28.09'da onaylandı ve geçti: gerçek `lib.php`'nin temiz kopyasıyla dört takım PHP 8.2.30'da ve 8.4'te tam geçti, ağsız ortamda. C 28.09'da onaylandı ve tamamlandı: eşleşme ve OpenAI anahtarları yenilendi, eski ikisi geçersiz (hosting ve OpenAI 401), yenileri çalışıyor; yalnız anahtar yenilendi, başka bir şey değişmedi. D–H her biri ayrı onay bekler. Anahtar yenileme (C), kurulum (D), canlı değişiklik (E, F, H), veri silme ve ücretli deneme (E, G) ayrı ayrı onaylanır.

**Cevapsız kalabilecek işler.** Hepsi uyarıda ve kanıt sorgusu 6'da görünür; hiçbiri sessiz değildir.
- Hosting'in `claim` cevabı ajana ulaşmazsa, ya da ajan cevabı alıp diske ve Postgres'e yazamadan ölürse (milisaniyeler): satır hosting'te 600 sn sonra "takılı" sayılır. Bu v1.1.1'de de böyledir.
- Postgres'e yazılamayan mesaj (veri hatası): `kalici_bekleyen/hatali/`'ye ayrılır. NUL karakteri bilinen tek nedendi, yazmadan önce temizleniyor.
- Hosting sonucu kesin reddederse (yol, boyut, PDF biçimi, 413), ya da mesaj artık onda işlenmekte değilse ve satırlar orada yoksa: `gonderilmedi`. Mesaj yeniden kuyruğa konursa cevap o zaman verilir.
- WhatsApp tarafı:
  - hosting göndermezse (`held`: 24 saat penceresi kapalı ya da `dry_run`): `gonderilmedi`;
  - sonuç belirsizse (`uncertain`): `belirsiz`, yeniden gönderilmez;
  - Meta "failed" derse: uyarı.
- D-03: üç denemede bitmeyen iş sonuçsuz kalır. Bayiye "işleyemedim" ve Patron'a bildirim gider.
- Geçiş ya da geri dönüş 24 saati aşarsa, bekleyen mesajların cevabı `held` olur.

**Uyarılar nereden izlenir.** Panelde ayrı bir uyarı yok, WhatsApp'a bildirim gitmez. Uyarılar şuralarda görünür:
- hosting'te `kanal/vps-health.json` → `errors` alanı: "gönderilmedi", "belirsiz", "Meta iletemedi", "hosting'e verilemiyor", "Postgres'e yazılamadı";
- `kanal/vps.log` (hosting) ve `/opt/portman/logs/agent.log` (VPS);
- kanıt sorgusu 6 (`kanit_sorgulari.sql`).

**Geri dönüşte yarım işlerin korunması (H).**
1. `worker=off` yapılır. Ajan yeni mesaj almaz; Postgres'te açık kalan işleri bitirir ve sonuçlarını hosting'e verir.
2. Açık iş 0 olunca ve diskte bekleyen mesaj kalmayınca devam edilir.
3. Hosting'e verilemeyen sonuçlar Postgres'te `bekliyor`/`gonderilmedi` olarak kalır. Hosting'te o mesajların satırı `processing` kalır; H.6'da hosting onları "takılı" sayar.
4. Veritabanı silinmez: `pg_dump` alınır, Mac'e kopyalanır ve veritabanının adı `portman_pilot_<tarih>` yapılır.
5. Diskte kalan mesaj dosyaları yedeğin yanına taşınır.
6. Yeniden giriş yalnız boş bir veritabanına yapılır.

## 1. Durum: hazır olan ve olmayan

| Parça | Durum | Kanıt ya da eksik |
|---|---|---|
| Postgres kalıcı akış (depo, işleyici, göç 001–002) | Test edildi, izole | `testler/kalici`: gerçek Postgres 16 |
| Ajanın kalıcı modu (`vps/agent.py`) | Test edildi, **sahte hosting ile** | `test_baglanti.py`, `test_hosting_devri.py`. Sahte hosting `api.php`'nin bir kısmını taklit eder (600 sn süpürme, hata enjeksiyonu dahil; taklit etmediği yerler dosyasının başında yazılı). PHP'yi sınamaz |
| `feature.php` (`context_id`), `api.php` v1.2 (`giden_durum`) | Test edildi, **gerçek `lib.php` ile yerelde** (B, 28.09); canlıda değil | Hosting'teki `lib.php`'nin temiz kopyası; PHP 8.2.30 (hosting sürümü) ve 8.4'te 30/30, 16/16, 19/19, 18/18; ağsız ortam. `lib.php` depoya girmez |
| Canlı sürüm | Doğrulandı (A, 28.09) | VPS'teki uygulama (48/48 dosya), hosting'in dağıttığı paket ve hosting'teki `feature.php` ile `api.php` v1.1.1 ile birebir (tam hash) |
| VPS Postgres kurulumu | Betik hazır; VPS'te koşulmadı (A: Postgres kurulu değil) | `vps/pg_kurulum.sh`: parolasız peer bağlantısı, saf psycopg ve göçler ayrı bir deneme kümesinde sınandı. Durdurma koşulları, sahiplik denetimi, işaretli deneme veritabanı ve yedek silme tercihi ayrı geçici kümelerde uçtan uca sınandı (`test_pg_kurulum.py`). apt, systemd ve cron adımları VPS'te görülecek |
| Gerçek WhatsApp, gerçek LLM | Denenmedi | Kapı G (kabul gösterimi) |

## 2. Dar değişiklikler (depoda, `ie-02`)

| Dosya | Değişiklik |
|---|---|
| `kanal/feature.php` | Gelen satıra `context_id` (bayinin alıntıladığı mesajın kimliği; yalnız `wamid.` ile başlıyorsa). Sürüm `kanal-v1.2` (`health.json`'da görünür). Başka davranış değişmedi. |
| `kanal/api.php` | Yeni işlem `giden_durum`: verilen giden satırların durumu, WhatsApp kimliği, API kabul anı (hosting saati), Meta'nın ilk "sent" ve ilk "delivered/read" anları (Meta saati); en çok 200 satır. Gerçekten salt okunur: `state.json` paylaşımlı kilitle okunur, yazılmaz. Sürüm `kanal-api-v1.2`. Öteki işlemler değişmedi. |
| `vps/agent.py` | `PORTMAN_PG_DSN` varsa kalıcı mod. Bir tur: (1) Postgres'e bağlanılamıyorsa hosting'ten mesaj alınmaz; (2) önceki turda alınıp Postgres'e yazılamayan mesaj diskten yazılır; (3) bitmiş işlerin sonuçları hosting'e **claim'den önce** verilir (claim, 600 sn'yi aşan satırı "takılı" sayar); (4) `worker=vps` ise ve Postgres'te açık iş yoksa bir mesaj alınır (alınan mesaj hosting'in 600 sn'si içinde işlensin; alınmayan kuyrukta güvenle bekler); (5) gönderim durumu eşitlenir, bir iş işlenir; (6) sonuç hosting'e verilir. `worker=off` iken yeni mesaj almaz, açık işleri bitirir (boşaltma); `worker=hosting` iken hiçbir şey yapmaz. Hosting hatası: satırı yalnız hosting'in kararı "gönderilmedi" yapar: bilinen kesin ret ya da mutabakat (hosting mesajı artık işlenmekte saymıyor ve satırlar `giden_durum`'da yok; ajan mesajı aldıktan 660 sn sonra başarılı bir claim olduysa hosting satırı süpürmüştür, bu da `giden_durum` ile sorulur). Başka her hatada hosting'e küçük bir istekle (`settings`) ulaşılabiliyor mu diye bakılır: ulaşılamıyorsa sonraki turda yeniden denenir; ulaşılabiliyorsa hata o işe özgüdür (ör. büyük gövdenin erken reddi bağlantı kopması olarak gelir), iş 30–300 sn aralıkla yeniden denenir ve öteki işler beklemez. Mesaj alınalı 480 sn olduysa aralık yok sayılır: hosting'in süpürebileceği her sonuç claim'den önce denenir. Ajan geçici hatada vazgeçmez; 5 dakikayı aşan devir uyarıya düşer. Postgres'e yazılamayan mesaj (veri hatası) `data/kalici_bekleyen/hatali/`'ye alınır, kuyruğu tıkamaz; NUL karakteri yazmadan önce atılır. Kira 120 sn (D-03: üç deneme hosting'in 600 sn'sine sığar). Tekrar gelen kanal mesajı ikinci iş açmaz; ilk işin hosting'e verilemeyen cevabını bu alımla verir. Gönderilemeyen, sonucu belirsiz, Meta'nın iletemedi dediği ve hosting'e verilmesi uzayan satırlar sağlık bildirimine (`vps-health.json` → `errors`) uyarı olarak yazılır. Günlüğe WhatsApp mesaj kimliği yerine kısa özeti (`iz`) yazılır, çünkü kimlik karşı tarafın numarasını içerir. `PORTMAN_PG_DSN` yoksa v1.1.1 dosya modu aynen çalışır. |
| `vps/paketle.py` | Pakete `depo.py`, `kalici.py`, `depo_aktar.py`, `goc/*.sql`, `kanit_sorgulari.sql`, `tekrar_dene.py` eklenir. |
| `kanal/goc/002_…sql` | API kabulü (`kabul_edildi`, `kabul_zamani`) ile Meta bildirimleri (`gonderildi_zamani`, `teslim_durumu`, `teslim_zamani`) ayrı; `hostingte` durumu; `onay_zinciri` ve `cevap_baglari` görünümleri. |
| `kanal/depo_aktar.py` | Komut satırı yalnız boş veritabanına aktarır (geri dönüşten sonra eski durum sessizce kullanılmasın). |
| `vps/pg_kurulum.sh`, `vps/kanit_sorgulari.sql`, `vps/tekrar_dene.py` | Kurulum (kapı D), salt okunur kanıt sorguları ve tekrar gelen mesaj denemesi (kapı G). |
| `vps/kapi_a_salt_okunur.sh`, `vps/anahtar_yenile.py`, `vps/api_denetim.py` | Salt okunur canlı denetim (kapı A), anahtar yenileme (kapı C.1) ve salt okunur API denetimi (kapı E.4); üçü de anahtar değeri yazdırmaz. Pakete girmez, Mac'ten `ssh` ile çalıştırılır. |

Dokunulmayanlar: `webhook.php`, `worker.php`, panel dosyaları, `portman/lib.php`, `store.json`, Görev 2/3 ve hosting'teki `worker.py`.

## 3. Gerçek PHP hattı nasıl doğrulanır

Sahte gönderici ve sahte hosting testleri PHP'yi doğrulamaz; bunları tamamlanmış saymıyorum. Doğrulama iki adımda yapılır.

1. **Yerel, gerçek PHP kodu ile (kapı B).** `portman/lib.php`'nin bir kopyası gerekir. Kopya gelince şunlar koşulur:
   - `php kanal/tests/offline_test.php lib.php`: v1.1.1'in 30 testi, gerileme denetimi;
   - `php kanal/tests/baglanti_test.php lib.php`: `context_id`, `giden_durum` ve onun `state.json`'a yazmadığı, 16 test;
   - `python3 kanal/tests/e2e_vps.py lib.php`: dosya modu, gerçek `api.php` ile ajan (`php -S`), 19 test;
   - `python3 kanal/tests/e2e_kalici.py lib.php`: kalıcı mod, gerçek `api.php` + ajan + Postgres; tekrar gelen mesaj, onay zinciri ve süpürmeyi yalnız `claim`'in yaptığı (ajanın tur sırasının dayandığı özellik) dahil, 18 test.

   Meta'ya ve OpenAI'ye bağlanılmaz. Hosting PHP 8.2.30 kullanıyor (A, `health.json`); testler bu sürümle koşulur (B.5). **28.09'da gerçek `lib.php` ile geçti (B, aşağıda).** Bu testler 28.09'da elle yazılmış taslak bir `lib` ile, PHP 8.4'te ön denemeden geçti (30/30, 16/16, 19/19, 18/18). Bu ön deneme **sayılmaz**; yalnız benim kodumdaki hataları erken yakalamak içindi.
2. **Canlıda (kapı E, F ve G).** PHP yüklendikten sonra önce dosya modunda bir Patron mesajı gönderilir (gerileme denetimi). Kalıcı mod bu testten sonra açılır ve kabul gösterimi gerçek Meta ile yapılır.

## 4. Onay kapıları

Yollar: hosting `/home/portatifevcom/portman_app/kanal` (aşağıda `KANAL`), VPS `/opt/portman`, servis `portman-agent`. Mac'teki yedek klasörü `~/PortmanYedek/` (aşağıda `YEDEK`).

### A · Güncel sürümün salt okunur doğrulanması (değişiklik yok; 28.09 onaylandı ve yapıldı)
**VPS** (asistanın ağ yolu yok; Lokman Mac'ten çalıştırır, root parolasını kendisi girer, sonucu asistan klasörden okur):
```
ssh root@<VPS> 'bash -s' < ~/Desktop/"Claude Portman Çalışması"/14_Kapi_A/kapi_a_salt_okunur.sh > ~/Desktop/"Claude Portman Çalışması"/14_Kapi_A/kapi_a_vps_sonuc.txt 2>&1
```
`vps/kapi_a_salt_okunur.sh` hiçbir şeyi değiştirmez ve anahtar, numara, mesaj kimliği ya da metin yazdırmaz (sahte düzende sınandı: çıktıda değer yok, dosyalar aynı kaldı). Topladıkları:
- sürüm, paket ve dosya hash'leri; uygulamanın kurulu paketle birebir aynı olup olmadığı;
- servis durumu;
- `agent.env`'in tarihi ve izni;
- anahtarın parmak izi, hem dosyadaki hem çalışan süreçteki;
- hosting'e ajanın her birkaç saniyede zaten attığı iki okuma isteği (`settings`, `package`). Bunlar hosting'in bu anahtarı şu an kabul edip etmediğini, API sürümünü, ayarları ve dağıttığı paketi gösterir; cevaptaki OpenAI anahtarı okunmadan atılır, yalnız "veriliyor mu" yazılır;
- hosting ve VPS saatleri arasındaki fark.

**Hosting dosyaları** (`feature.php`, `api.php`): asistanın DirectAdmin'e tarayıcıdan erişimi bu ortamın izin denetiminde engellendi (28.09). Lokman 28.09 akşamı Safari'deki kendi DirectAdmin oturumundan yalnız bu iki dosyayı indirdi ve SHA-256'yı kendi Mac'inde hesapladı. Canlıda hiçbir dosya ya da ayar değişmedi; anahtar ve müşteri verisi dosyaları açılmadı. Ayrıca `package/SURUM.txt`, `package/current.sha256`, `health.json` ve `vps-health.json`'u okudu. Dosyalar klasöre konmadı; asistan verilen tam hash ve boyutları referanslarla karşılaştırdı. `api_token.txt` açılmaz, indirilmez; eşleşme, hosting'in anahtarı kabul edip etmediğiyle gösterilir.

Karşılaştırma (v1.1.1; 22.09 dağıtım zip'lerinden doğrulandı): `feature.php` `91c954a62537606e` (v1.0'dan beri aynı), `api.php` `455f8c7414442183`, `worker.py` `3687f3763c9a759a`, `agent.py` `72acb4238c1bfb1d`, paket `bd1ca27c22d7b5c0` (`kanal-v1.1.1-20260922-2011`). Farklı bir değer git geçmişindeki ve zip'lerdeki sürümlerle eşlenir.

**Sızan anahtar için kanıt düzeyi.** Parmak izi eşitliği ve dosya tarihi tek başına "sızan anahtar kesin hâlâ etkin" demek değildir. Gösterilebilenler:
- hosting'in çalışan ajanın anahtarını şu an kabul ettiği (canlı istek);
- dosyadaki ve süreçteki anahtarın aynı olduğu;
- anahtarın hangi tarihten beri değişmediği (bootstrap var olan `agent.env`'e dokunmaz; tarihi anahtarın üretildiği andır).

Kaydedilen sızıntı 22.09 18:15'te bir ekran görüntüsüyle oldu. Görüntüdeki anahtarın bugünkü anahtar olduğunu kesinleştirmek için o değerle karşılaştırmak gerekir; asistan değeri görmemek için görüntüyü açmaz. Bu yüzden sonuç en çok "büyük olasılıkla etkin, kanıtlanmadı" olabilir. C bu soruyu her durumda kapatır.

**Sonuç.** VPS betiğini Lokman 28.09 20:06'da koştu; değerlendirme çıktı dosyasından yapıldı. Çalıştırılan betik `2026-09-28b` (sha256 `56960c3c87bb3b87`); çıktı `14_Kapi_A/kapi_a_vps_sonuc.txt`, içinde anahtar, numara ya da mesaj kimliği yok. Depodaki sürüm yalnız bir görüntü satırında farklıdır (Postgres servis durumu tek satır).

| Denetlenen | Beklenen (v1.1.1) | Canlı | Sonuç |
|---|---|---|---|
| Paket | `kanal-v1.1.1-20260922-2011`; `bd1ca27c22d7b5c06722d0ddab855a5c2d821c96e78cc1049afe0c6e78b7a408`, 639.306 B (`hosting_guncelleme_2011.zip` içindeki `current.zip`'ten hesaplandı) | VPS: aynı. Hosting: `SURUM.txt`, `current.sha256` ve `vps-health.json` → `package_sha256` aynı (tam 64 hane) | ✓ |
| `agent.py` | `72acb4238c1bfb1d` | aynı (22.09 22:14'te kuruldu) | ✓ |
| `worker.py`, `karar.py`, `dxf_out.py`, `cikarici.py` | `3687f376…`, `9f01d064…`, `b2c96ce9…`, `acab9e16…` | aynı | ✓ |
| Kurulu uygulama ↔ paket | birebir | 48 dosya aynı; farklı, eksik ya da fazla 0 | ✓ |
| Hosting'in dağıttığı paket | `bd1ca27c…` | VPS betiği `op=package` ile gelen baytların SHA-256'sını hesapladı ve tam olarak karşılaştırdı (çıktıda ilk 16 hane): ayarlardaki ve VPS'teki kopyayla aynı; 639.306 B, 22.09 20:12 | ✓ |
| Hosting `api.php` | `455f8c7414442183f6c5fbf779605fea343ff9cdff0b71ee26975db4e11a0867`, 16.675 B (git `a3050c3`; `portman_kanal_v1.1_20260922.zip`; `KAYNAK_KODU.zip` = `ec4e9a3`) | aynı hash ve boyut (panel tarihi 22.09). API cevabı da uyumlu: `kanal-api-v1.1`, `vps_komut` alanı var | ✓ |
| Hosting `feature.php` | `91c954a62537606e6cf77cc2beed5d0fd71325b8b8fb820966eb37fbd5955d0e`, 24.111 B (git `d3d18e5`; `portman_kanal_v1.0_20260921.zip`, `v1.0.1`; `KAYNAK_KODU.zip`) | aynı hash ve boyut (panel tarihi 21.09) | ✓ |
| Hosting sağlık kayıtları | hata yok | `vps-health.json`: `vps-agent-v1.1.1`, öz-test `passed`, `errors` boş. `health.json`: PHP 8.2.30, `enabled` true, `dry_run` false, `error` null, sürüm `kanal-v1.0` (aşağıda) | ✓ |
| Ayarlar | açık, `worker` vps, Patron, `dry_run` kapalı, `vps_komut` kapalı | aynı; LLM `gpt-4o-mini` | ✓ |
| Servis | çalışıyor | 25.09 06:46'dan beri çalışıyor; 0 yeniden başlatma; kullanıcı `portman`; ek yapılandırma yok | ✓ |
| Saat farkı (hosting − VPS) | küçük | 0 sn | ✓ |

**Beklenenden fark: yok.** Denetlenen her şey tam hash ya da birebir değerle beklenenle aynı.

`health.json`'daki `kanal-v1.0` etiketi fark değildir. `health.json`'u `feature.php` yazar ve içine kendi sabitini koyar (`PM_KANAL_SURUM = 'kanal-v1.0'`, satır 13 ve 248). `feature.php` v1.0'dan beri değişmedi; hash'i 21.09 v1.0 zip'iyle aynı. v1.1 ve v1.1.1'de sürüm etiketi değişen parçalar başkaydı:
- paketi (VPS'te çalışan Python kodu; sürümü `package/SURUM.txt`'te);
- `api.php`'yi (`kanal-api-v1.1`);
- ajanı (`vps-agent-v1.1.1`, `vps-health.json`'da).

Yani ayrı parçaların ayrı etiketleri var; eski bir kurulumun işareti değil. E'de `feature.php` `kanal-v1.2` olunca `health.json` da `kanal-v1.2` gösterir (E.4).

**Anahtarlar iki tarafta eşleşiyor.**
- VPS: `agent.env`'deki ve çalışan süreçteki anahtarın parmak izi aynı (`3173020445c2`, 64 hane).
- Hosting: bu anahtarı 28.09 17:06 UTC'de kabul etti (`settings` ve `package` HTTP 200). Hosting yalnız `api_token.txt`'teki anahtarı kabul eder; demek ki o dosyada da aynı anahtar var. `api_token.txt` açılmadı.
- Hosting bu anahtarı taşıyana OpenAI anahtarını veriyor: evet (değer okunmadı).
- `agent.env` 22.09 18:19:43'ten beri değişmedi; sahibi root:portman, izni 0640.

**Sızan anahtar: büyük olasılıkla hâlâ etkin; kanıtlanmadı.**
- Bootstrap anahtarı yalnız `agent.env`'i oluştururken üretir ve ekrana bir kez yazar; var olan dosyaya dokunmaz. Dosya 18:19:43'ten beri değişmedi.
- Oturum günlüğü sızıntıdan sonra anahtarın yenilenmediğini yazıyor (22:09'da yenileme ertelendi).
- Ama günlükteki sızıntı saati (18:15) dosya tarihinden 4,5 dakika önce. Saat yaklaşık yazılmış olabilir. Yazılmamışsa görüntüdeki anahtar, ondan önce oluşturulup silinmiş bir dosyaya ait olabilir; günlükte böyle bir silme geçmiyor.
- Kesin kanıt ancak görüntüdeki değerle karşılaştırmadır; yapılmadı. C yapılırsa bu soru kalmaz.

**Öteki bulgular:**
- Hosting PHP 8.2.30 (B'deki testler bu sürümle koşulur).
- Postgres kurulu değil (D'nin başlangıç durumu).
- Disk: 195 GB'ın 178 GB'ı boş. Kullanılabilir bellek: 7,3 GB. Ubuntu 24.04.4, Python 3.12.3.
- Gönderilemeyip bekleyen sonuç: 0.
- Öz-test geçti (22.09 22:32, 27,2 sn).
- Son 24 saatte günlük satırı yok; hata da yok, iş de yok.

### B · `lib.php` kopyası ile yerel PHP testleri (değişiklik yok; 28.09 onaylandı ve geçti)
Teknik denetimi asistan yapar; Lokman yalnız dosyayı sağlar ve paylaşımı onaylar.
1. Lokman DirectAdmin'den `public_html/portman/lib.php`'yi indirip `Claude Portman Çalışması/15_Kapi_B/` içine koyar. Hosting'te hiçbir şey değişmez.
2. **Sır denetimi Lokman'ın bilgisayarında** (bağlı klasörün yerel yalıtılmış ortamı). Asistan dosyayı değer yazdırmayan bir betikle tarar. Çıktıda yalnız satır numarası, bulgunun türü ve tanımlayıcı adı görünür:
   - anahtar biçimli dizgeler (`sk-`, `EAA`, uzun onaltılık, `Bearer`);
   - parola ya da sır ataması;
   - `define` sabitleri;
   - telefon numarası ya da e-posta biçimleri.
3. Temizse dosya, değilse bulunan değerlerin yer tutucuyla değiştirildiği bir kopya, asistanın yalıtılmış test ortamına alınır. Özgün dosya bilgisayardan çıkmaz; sohbete eklenmez. Testler Lokman'ın bilgisayarında koşulamaz: oradaki yalıtılmış ortamda PHP yok ve yönetici yetkisi olmadığı için kurulamıyor.
4. Koşmadan önce `lib.php`'nin test kancalarını (`PM_OFFLINE_TEST`, `pm_test_remote`) içerdiği denetlenir. İçermiyorsa Meta'ya istek gönderebilecek testler koşulmaz ve bu Lokman'a söylenir. Testler sahte anahtar, sahte numara ve geçici veri klasörüyle koşar; gerçek yapılandırma okunmaz.
5. PHP sürümü: hosting 8.2.30 kullanıyor. Testler PHP 8.2.30 ile koşulur. Bu sürüm, php-src'nin resmi `php-8.2.30` etiketinden asistanın ortamında derlenir. Testler ortamdaki 8.4 ile de koşulur; iki sonuç ayrı yazılır. Kendi PHP dosyalarımızda 8.3 ve 8.4'e özgü işlev ya da sözdizimi taraması temiz çıktı; tarama, çalıştırmanın yerini tutmaz.
6. 3. bölümdeki dört test koşulur. Sonuç yalnız sayılar ve dosya/satır olarak raporlanır. Test ortamındaki kopya ardından silinir.

**Sonuç (28.09 21:00).**
- **Dosya:** `lib.php`, 28.004 bayt, sha256 `09b29f7b2099d1c3…`. Lokman 20:41'de indirdi.
- **Tarama** Lokman'ın bilgisayarında yapıldı (`denetim/lib_tara.py`; değer yazdırmaz, sahte sırlarla sınandı: `test_lib_tara.py`).
  - API anahtarı, erişim anahtarı, parola ya da e-posta yok.
  - 7. satırda iki telefon numarası var (`PM_RECIPIENTS`). Yalnız gelen mesajın görünen adını seçmek için kullanılıyor (satır 76).
- **Temiz kopya:** `lib.clean.php` (sha256 `49a6bd87eb263f23…`). İki numara aynı uzunlukta sahte rakamlarla değiştirildi.
  - Yeniden tarama temiz. Kod iskeleti orijinalle aynı; değişen tek satır 7.
  - Orijinal değişmedi (hash ve tarih aynı) ve bilgisayardan çıkmadı; test ortamına yalnız temiz kopya alındı.
  - Tarayıcı kişi adı aramaz. Kodda bir kişinin yalnız ön adı, görünen ad etiketi olarak geçiyor ve kopyada kaldı; numarası temizlendi.
- **Kancalar:**
  - `pm_remote`: `PM_OFFLINE_TEST` + `pm_test_remote`. Dört takım da ikisini tanımlıyor.
  - `pm_stream_media`: `PM_OFFLINE_TEST` + `pm_test_stream`. Bu işlevi yalnız `pm_download` çağırıyor; testler oraya girmiyor.
  - Bütün `curl` çağrıları bu iki işlevde.
- **Ağ yalıtımı:** testler yalnız loopback'i olan ayrı bir ağ ad alanında koştu; dış bağlantı denemesi başarısız oldu. Ayrıca PHP'nin ağ işlevleri (`curl_init`, `curl_exec`, `fsockopen` …) kapatılarak yinelendi; sonuç aynı, yani hiçbir test yolu ağ işlevine ulaşmadı.

| Takım | PHP 8.2.30 (resmi kaynaktan derlendi) | PHP 8.4.21 |
|---|---|---|
| `offline_test.php` | 30/30 | 30/30 |
| `baglanti_test.php` | 16/16 | 16/16 |
| `e2e_vps.py` | 19/19 | 19/19 |
| `e2e_kalici.py` | 18/18 | 18/18 |

- Çıktılarda ve `php -S` günlüklerinde PHP uyarısı, kullanımdan kalkma bildirimi ya da hata yok.
- Test ortamındaki kopya ve geçici test klasörleri silindi. `lib.php`, `lib.clean.php` ve `lib_tara.py` Lokman'ın `15_Kapi_B` klasöründe duruyor.

**Kayıtta kalan sınırlamalar (Lokman, 28.09):** medya indirme yolu (`pm_download` → `pm_stream_media`) B'de sınanmadı; temiz kopyada bir kişinin ön adı kaldı.

**Kural (Lokman, 28.09):** bundan sonraki her dışarı aktarımda kişi adları da maskelenir. Tarayıcıya ad denetimi eklenmeden yeni bir dosya dışarı aktarılmaz.

### C · Eşleşme ve OpenAI anahtarlarının kontrollü yenilenmesi (28.09 onaylandı; yalnız anahtar yenileme)
Kapsam: bugünkü canlı sürümde (v1.1.1, dosya modu) yalnız iki anahtar yenilenir. Postgres, PHP ya da paket yüklemesi yok; mod Patron kalır. Denetimlerin hepsi ücretsizdir: hosting'e `op=settings` ve OpenAI'ye `GET /v1/models` (token harcamaz). Gerçek mesajla uçtan uca deneme ücretlidir ve C'ye dahil değildir.

Kurallar:
- Hiçbir anahtar değeri sohbete, günlüğe, dosya adına ya da depoya girmez; çıktılarda yalnız 12 haneli parmak izi var. OpenAI'nin hata mesajı anahtarın bir parçasını içerdiği için yalnız hata kodu yazılır.
- Eski anahtarlar geri kullanılmaz. Geri dönüş yolu yeni bir anahtar daha üretmektir; `agent.env` yedeğinde anahtar satırı yoktur.
- Eski iki anahtar, iptal edildiklerini sınamak için, yalnız işlem boyunca VPS'te root'a özel bir klasörde (`/root/.portman_kapi_c`, 0700; dosyalar 0600) durur. Son adım onları siler; yarıda kalırsa `temizle` siler.
- İşlem boyunca Patron numarasından mesaj yazılmaz ve ekran görüntüsü alınmaz. Eşleşme anahtarının hosting'e yazıldığı andan servis yeniden başlatılana dek (birkaç dakika) ajan hosting'e bağlanamaz. Gelen mesaj kuyrukta bekler; gönderilemeyen sonuç `data/pending/`'e alınıp sonra gönderilir.

Adımlar (`vps/kapi_c.py`; her adım öncekinin geçtiğini denetler, geçmezse "DUR" ve yapılacak işi yazar):
1. **Sohbet botunun OpenAI anahtarını nereden okuduğu** (salt okunur). Lokman `developer/ai.php`, `developer/config.php` ve `portman_app/kanal/settings.json`'u `16_Kapi_C/`'ye indirir; asistan Mac'te `denetim/lib_tara.py --ara` ile değer yazdırmadan tarar. Amaç: eski anahtar iptal edilince bayilere cevap veren sohbet botunun durmaması. Yeni anahtarın izinleri ve nereye kaydedileceği bu sonuca göre belirlenir.
2. `hazirla`: servis çalışıyor, dosyadaki ve süreçteki anahtar aynı, hosting bugünkü anahtarı kabul ediyor, bugünkü OpenAI anahtarı geçerli. Eski iki anahtar geçici klasöre alınır.
3. Lokman OpenAI'da yeni anahtar oluşturur (eskisini henüz iptal etmez), panele kaydeder, panoyu temizler.
4. `yenile`: `agent.env`'de yeni eşleşme anahtarı. İzin ve sahip korunur; yedekte anahtar satırı yok. Servis yeniden başlatılmaz.
5. Lokman yeni eşleşme anahtarını ekrana getirmeden panoya alır (`… | pbcopy`), DirectAdmin'de `api_token.txt`'ye yapıştırır, panoyu temizler.
6. `ara`: hosting yeni eşleşme anahtarını kabul ediyor, eskisini reddediyor (401); panel yeni bir OpenAI anahtarı veriyor ve o anahtar OpenAI'de geçerli. Biri tutmazsa servis yeniden başlatılmaz.
7. `yeniden_baslat`: servis yeniden başlatılır. Süreç yeni anahtarla çalışıyor olmalı; hosting onu kabul etmeli; günlükte yeniden başlatmadan sonra 401 olmamalı.
8. Lokman OpenAI'da eski anahtarı iptal eder (Revoke).
9. `bitir`: eski eşleşme anahtarı hosting'te, eski OpenAI anahtarı OpenAI'de geçersiz (401); yenileri çalışıyor. Sonra geçici klasör silinir. Eski OpenAI anahtarı hâlâ geçerliyse klasör silinmez, adım yinelenir.

**Adım 1 sonucu (28.09 21:40; dosyalar Lokman'ın Mac'inde tarandı, dışarı çıkmadı).**
- Sohbet botu (`ai.php`) OpenAI anahtarını kendi içinde tutmuyor. `otomatikYanit` → `ayarlarOku()` → `openaiSor` yolunu izliyor; `ayarlarOku`, `jsonOku('ayarlar')` ile `developer/veri/ayarlar.json`'u okuyor (`config.php`).
- Portman'ın okuduğu dosya da aynı: `settings.json` → `ayarlar_json` = `…/public_html/developer/veri/ayarlar.json`. Anahtar tek yerde değişince ikisi birlikte yeni anahtara geçer; eski anahtarın iptali sohbet botunu durdurmaz.
- Bot yalnız `api.openai.com/v1/chat/completions` çağırıyor. Yeni anahtar kısıtlı olabilir: Models okuma, Model capabilities yazma, gerisi kapalı.
- `config.php`'de WhatsApp erişim anahtarı, doğrulama belirteci, panel parolası ve telefon numaraları kodun içinde. C'nin kapsamı dışında; yalnız not edildi. Yerel kopyalar C'den sonra silinmeli.
- Asistanın ortamlarından VPS'in 22. portuna ağ yolu yok: Mac'teki yalıtılmış Linux ortamında "Network is unreachable", bulut ortamında zaman aşımı. Lokman'ın Mac'teki SSH anahtarı bu ortamlardan görünmez ve okunmadı. VPS adımlarını Lokman yürütür.

**Sonuç (28.09; Lokman adımları 21:43–22:23'te yürüttü; çıktılar `16_Kapi_C/2_…9_*.txt`, içlerinde anahtar değeri yok).** Kapı C tamam.

| Anahtar | Eski parmak izi | Yeni parmak izi | Eskisi geçersiz mi | Yenisi çalışıyor mu |
|---|---|---|---|---|
| Eşleşme (VPS ↔ hosting) | `3173020445c2` (A'daki, sızdığı düşünülen) | `9238aa8aadce` | Hosting 401 veriyor (22:03 ve 22:23) | Hosting 200; çalışan süreç ve dosya aynı anahtarla |
| OpenAI | `0acef17e0f05` | `4cf00ec74492` | OpenAI 401 `invalid_api_key` (22:23; Lokman iptal etti) | OpenAI 200; hosting'in verdiği anahtar bu |

- `agent.env`'in izni ve sahibi korundu (0640, root:portman). Yedekte anahtar satırı yok.
- Servis 22:03:53'te yeniden başladı (PID 75217 → 86646). Yeniden başlatmadan sonra günlükte 401 yok. Yenilemeden önce gönderilemeyip bekleyen sonuç 0'dı.
- Eski iki anahtarın geçici kopyası (`/root/.portman_kapi_c`) son adımda silindi. Eski eşleşme anahtarı yeniden başlatmayla süreç belleğinden de çıktı.
- Sohbet botu aynı panel dosyasını okuduğu için yeni OpenAI anahtarına kendiliğinden geçti; bu, koddan gösterildi (adım 1). Gerçek bir mesajla denenmedi; o deneme ücretlidir ve ayrı onay ister.
- Kalan temizlik Lokman'ın kararında: `16_Kapi_C`'deki `config.php` (WhatsApp erişim anahtarı ve panel parolası içeriyor), `ai.php`, `settings.json` ve `15_Kapi_B`'deki `lib.php`/`lib.clean.php` yerel kopyalarının silinmesi.

Sınanması: `testler/kalici/test_kapi_c.py`. Sahte hosting, sahte OpenAI ve sahte systemctl ile uçtan uca sınandı: sıra zorunlu; hosting güncellenmeden yeniden başlatma yok; iptalsiz bitiş yok; hiçbir çıktıda anahtar parçası yok.

### D · VPS'e Postgres kurulumu (trafik değişmez)
```
ssh root@<VPS> 'bash -s' < vps/pg_kurulum.sh
```
- Kurulanlar: Postgres 16; yalnız yerel bağlantı; parolasız `portman` rolü (peer); saf psycopg; günlük `pg_dump`.
- **Yedeklerin otomatik silinmesi varsayılan olarak kapalı (pilot).** Açmak ayrı bir tercih ve ayrı onaydır: `ssh root@<VPS> 'PM_YEDEK_SAKLA_GUN=14 bash -s' < vps/pg_kurulum.sh`. Kapalıyken yedekler birikir; disk VPS betiğiyle izlenir.
- **Yerel bağlantı şartı sağlanmıyorsa betik durur**, uyarıp geçmez. Durdurma koşulları:
  - `listen_addresses` yerel değilse;
  - `pg_hba.conf` yerel olmayan bir adrese TCP açıyorsa;
  - 5432 yerel olmayan bir adreste dinleniyorsa;
  - güvenlik duvarında 5432 kuralı varsa.

  O durumda rol, veritabanı, yedek klasörü ve cron oluşmaz.
- `portman` veritabanı zaten var ama sahibi `portman` değilse betik ona dokunmaz ve durur.
- **Geri yükleme denemesi yalnız kendi açtığı veritabanını siler.** Deneme veritabanının adı her çalıştırmada benzersizdir ve üzerine o çalıştırmanın işareti yazılır; silmeden önce bu işaret denetlenir. Aynı adda başka bir veritabanı varsa dokunulmaz ve betik durur. Geri yükleme başarısızsa deneme veritabanı incelenmek üzere bırakılır. Tekrar çalıştırılabilir.
- Bu özelliklerin her biri, ayrı bir geçici Postgres kümesinde uçtan uca sınandı (`test_pg_kurulum.py`). Kasıtlı zayıflatmaların hepsi yakalandı.
- Yedekler yalnız VPS diskindedir. Mac'e kopya F, G ve H'de elle alınır (aşağıda). Otomatik dış yedek bu planın kapsamında değil.
- Ajan dosya modunda kalır.
- Geri alma: `apt-get remove postgresql` ve `/etc/cron.d/portman-pg-yedek` silinir. İçinde veri yoktur.

### E · Hosting PHP ve paket yüklemesi (dosya modu sürer; B geçmiş olmalı)
1. Yedek: `KANAL/feature.php`, `api.php` → `*.before-ie02-<tarih>.php`. `package/` klasörü → `package.before-ie02-<tarih>/`. Yedeklenen iki dosya A'daki tam hash'le aynı olmalı (A'dan beri değişmemiş); farklıysa E durur.
2. Depodan `kanal/feature.php` ve `kanal/api.php` → `KANAL/`.
3. `python3 vps/paketle.py` → `vps/build/current.zip`, `current.sha256`, `SURUM.txt` → `KANAL/package/`. Ajan paketi kendisi günceller. `PORTMAN_PG_DSN` olmadığı için dosya modunda kalır.
4. Doğrulama:
   - `health.json` surum `kanal-v1.2`;
   - `vps-health.json` surum `vps-agent-v1.2`;
   - VPS'ten salt okunur API denetimi (anahtar yazdırılmaz; yalnız `api`, `worker`, `enabled`, `mode`, `dry_run` yazılır). Mac'ten `ssh root@<VPS> 'python3 -' < vps/api_denetim.py`. Beklenen: `api` `kanal-api-v1.2`.
   - Patron numarasından bir mesaj eskisi gibi cevaplanır (dosya modu, gerileme denetimi).
5. Geri alma: yedek dosyalar ve eski paket geri konur.

### F · Kalıcı moda geçiş
Geçiş sırasında gelen mesajlar: 1. adımdan 6. adıma kadar webhook yakalamaya devam eder, satırlar hosting kuyruğunda `queued` bekler; hiçbiri işlenmez ve kaybolmaz. 6. adımda ajan onları geliş sırasıyla alır. Geçiş 24 saati aşarsa hosting o mesajlara cevap göndermez (Meta'nın 24 saat penceresi; satır "held" olur ve uyarıya düşer).

1. `KANAL/settings.json` → `"worker": "off"`. Hiçbir işleyici yeni iş almaz.
2. Boşalma: `processing` satır kalmayana ve `pending` giden satırlar tik ile gidene dek beklenir. Hosting'te:
   ```
   php -r '$s=json_decode(file_get_contents("state.json"),true); $c=[]; foreach(["inbound","outbound"] as $k) foreach($s[$k]??[] as $r) $c[$k][$r["state"]??"?"]=($c[$k][$r["state"]??"?"]??0)+1; echo json_encode($c),"\n";'
   ```
   `inbound.processing` ve `outbound.pending` yok olmalı. `depo_aktar` `processing` satır varken zaten çalışmaz.
3. Yedek:
   - hosting: `tar czf ~/yedek-ie02-<tarih>.tgz -C /home/portatifevcom/portman_app kanal/state.json kanal/durum kanal/projects kanal/settings.json`;
   - VPS: `install -d -m 700 /var/backups/portman; tar czf /var/backups/portman/opt-portman-ie02-<tarih>.tgz -C /opt/portman data app`;
   - ikisi de Mac'e: `scp <hosting>:~/yedek-ie02-<tarih>.tgz YEDEK/` ve `scp root@<VPS>:/var/backups/portman/opt-portman-ie02-<tarih>.tgz YEDEK/`.
4. Hosting'in `durum/` ve `state.json` kopyası VPS'e alınır ve içe aktarılır. Geçici klasör `portman` kullanıcısınındır (root'un ev klasörü `portman`'a kapalıdır):
   ```
   # Mac'ten
   mkdir -p YEDEK/gecis && tar xzf YEDEK/yedek-ie02-<tarih>.tgz -C YEDEK/gecis kanal/state.json kanal/durum
   ssh root@<VPS> 'install -d -o portman -g portman -m 700 /var/tmp/portman-gecis'
   scp -r YEDEK/gecis/kanal root@<VPS>:/var/tmp/portman-gecis/
   # VPS'te
   chown -R portman:portman /var/tmp/portman-gecis
   sudo -u portman env PORTMAN_PG_DSN=dbname=portman /opt/portman/venv/bin/python /opt/portman/app/kalici.py goc
   sudo -u portman env PORTMAN_PG_DSN=dbname=portman /opt/portman/venv/bin/python /opt/portman/app/depo_aktar.py ice --kanal /var/tmp/portman-gecis/kanal
   ```
   - Konuşmalar ve askıdaki sorular Postgres'e geçer. Veritabanı boş değilse aktarma yapılmaz.
   - İşlenmiş mesajlar yalnız tekilleştirme için kaydedilir.
   - Kuyrukta bekleyenler (`kuyrukta_birakildi`) hosting'te kalır; ajan onları claim ile alır.
   - `/var/tmp/portman-gecis` konuşma kopyası içerir; G bittikten sonra ayrı onayla silinir.
5. Kalıcı mod açılır (`worker` hâlâ `off`: ajan bekler, iş almaz):
   ```
   printf 'PORTMAN_PG_DSN=dbname=portman\n' > /etc/portman/pg.env; chown root:portman /etc/portman/pg.env; chmod 640 /etc/portman/pg.env
   mkdir -p /etc/systemd/system/portman-agent.service.d
   printf '[Service]\nEnvironmentFile=/etc/portman/pg.env\n' > /etc/systemd/system/portman-agent.service.d/kalici.conf
   systemctl daemon-reload; systemctl restart portman-agent
   ```
   Ajan günlüğünde `mod kalıcı (Postgres)` görünür.
6. `settings.json` → `"worker": "vps"`. Ajan kuyruktakileri sırayla alır; geçiş sırasında gelen mesajlar da buna dahildir.

### G · Kabul gösterimi (gerçek WhatsApp ve gerçek LLM; ücretli kapsam aşağıda)
Lokman Patron numarasından yazar:

| # | Ne yapılır | Beklenen | Kanıt |
|---|---|---|---|
| 1 | "P6001 aynalı olsun" | r01 PDF'i telefona gelir | Sorgu 1, 4 |
| 2 | "yatak odası 1, 120x180" | Portman sorar: değiştirelim mi, ekleyelim mi? Söz belirsiz olduğu için B1 sorusu gelir. "penceresi … olsun" gibi açık bir söz yazılırsa soru gelmez, doğrudan değiştirilir | Sorgu 3 (açık soru, kaynak = bu mesaj) |
| 3 | VPS'te `systemctl restart portman-agent` | Servis yeniden başlar | Ajan günlüğü |
| 4 | "değiştir" | Cevap bu soruya bağlanır; aynı projede r02 (aynalı ve pencere 120x180) telefona gelir | Sorgu 3 (cevaplandı), 4 |
| 5 | r01 PDF'ini alıntılayarak "onaylıyorum" | Reddedilir: "Alıntıladığınız mesaj r01'e ait; güncel plan r02" | Sorgu 5 (kabul false, alıntı rev 1) |
| 6 | r02 PDF'ini alıntılayarak "onaylıyorum" | Kabul edilir: "Onayınız kaydedildi (…, revizyon 2)" | Sorgu 4 (r02 onaylandı), 5 (kabul true; sınır "teslim", Meta teslim bildirimi henüz gelmediyse "gonderildi") |
| 7 | VPS'te: `sudo -u portman env PORTMAN_PG_DSN=dbname=portman /opt/portman/venv/bin/python /opt/portman/app/tekrar_dene.py <1. mesajın izi>` (sorgu 1, `mesaj_izi`) | Aynı kanal mesajı yeniden verilir; ikinci iş açılmaz ("hayır", iş sayısı 1) | Çıktı; sorgu 2 (mesaj başına en çok 1 iş) |

Kanıt: `sudo -u portman psql -d portman -f /opt/portman/app/kanit_sorgulari.sql`. Sorgular salt okunurdur, numaralar maskelidir; mesaj metni ve bayinin sözünü içerebilecek gerekçe alanı yazılmaz. WhatsApp mesaj kimlikleri numarayı base64 olarak içerdiği için yalnız 10 haneli özetleri (`iz`) yazılır; aynı mesaj her sorguda aynı izle görünür. Çıktı sohbete eklenir. Sorgu 4'te "API kabulü" hosting'in WhatsApp API'den kabul aldığı andır; telefona teslim değildir. Teslim, Meta'nın imzalı "delivered/read" bildirimidir.

Gösterimden sonra `vps-health.json` → `errors` alanında "gönderilmedi", "belirsiz", "Meta iletemedi" ya da "hosting'e verilemiyor" uyarısı olmamalı. Yedek: `sudo -u postgres pg_dump -Fc -d portman -f /var/backups/portman/gosterim-<tarih>.dump` ve Mac'e `scp`.

Adım 7 hosting'e dokunmaz. Aynı mesajın hosting kuyruğundan ikinci kez gelmesi (claim → Postgres → "yoksay" sonucu) gerçek PHP hattıyla `e2e_kalici.py`'de sınanır (kapı B). Canlıda hosting kuyruğunu elle düzenlemek önerilmez. Meta'nın aynı mesajı yeniden teslim etmesini PHP zaten kimliğe göre tekilleştiriyor (`offline_test.php`).

Bu yedi adım, kayıtlı çıkarım ve sahte hosting ile `test_baglanti.py::test_canli_gosterim_provasi_sahte_hosting` testinde provadan geçti. Prova canlı doğrulama değildir.

Adım 2'de LLM mesajı revizyon değil yeni talep sayabilir. O zaman akış başka bir soruya gider; bu da kaydedilir, uydurulmaz. Böyle olursa adım model koduyla yinelenir ("P6001 yatak odası 1 penceresi 120x180") ya da D-01 sorusu için 2 saat beklenir.

**Ücretli kapsam (E ve G birlikte).** Planlı gerçek çağrılar yalnız bu iki kapıda olur. A, B, C, D, F ve H kendiliğinden gerçek LLM ya da WhatsApp çağrısı yapmaz: öz-test paket başına bir kez koşar, servis yeniden başlatmaları onu tekrarlamaz. Ama F ve H'de kuyrukta bekleyen gerçek mesaj varsa işlenir ve cevaplanır; Patron modunda bunlar yalnız Lokman'ın mesajlarıdır.

| Kapı | OpenAI (gpt-4o-mini) | WhatsApp giden mesaj |
|---|---|---|
| E | Paket öz-testi 1 çağrı (şema hatasında 1 tekrar) ve gerileme mesajı 1 çağrı (+1): 2–4 | Gerileme mesajının cevabı: metin + PDF, en çok 3 |
| G | 7 adımda yaklaşık 8 çağrı (tekrarlarla en çok 16) | Yaklaşık 12 |
| Toplam | 10–20 çağrı | Yaklaşık 15 |

- OpenAI: 22.09'daki ölçüme göre çağrı başına yaklaşık 3.100 giriş ve 200 çıkış token'ı. Toplamda en çok ~62.000 giriş ve ~4.000 çıkış token'ı. Tutar, o günkü OpenAI fiyatıyla OpenAI panelinden izlenir; burada doğrulanmadı.
- WhatsApp: Meta, 1 Ekim 2026'dan itibaren 24 saatlik pencere içindeki şablonsuz (servis) mesajları, her pazarın utility oranıyla mesaj başına ücretlendiriyor ([Meta](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing/non-template-messages)). 1 Ekim'den önce ücretsizdir.
- Türkiye oranı Meta'nın fiyat sayfası metninde yok; oradaki fiyat dosyasında (CSV/PDF) ([Meta fiyatlandırma](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing)). **E ve G'den hemen önce** asistan o günkü dosyadan Türkiye utility oranını okur, mesaj sayısıyla çarpar ve onaya sunar. Üçüncü taraf sitelerdeki oranlar kullanılmaz.

### H · Geri dönüş (gerektiğinde; onayla)
1. `settings.json` → `"worker": "off"`. Gelen mesajlar kuyrukta bekler. Ajan yeni mesaj almaz; Postgres'te açık kalan işleri bitirir ve sonuçlarını hosting'e verir (boşaltma).
2. Boşalma beklenir. VPS'te:
   ```
   sudo -u portman psql -d portman -tAc "SELECT (SELECT count(*) FROM isler WHERE durum IN ('sirada','isleniyor')) AS acik_is, (SELECT count(*) FROM giden WHERE durum = 'bekliyor') AS bekleyen_giden"
   ```
   `acik_is` 0 olmalı ve diskte bekleyen mesaj olmamalı (`ls /opt/portman/data/kalici_bekleyen/*.json` boş). `bekleyen_giden` de 0 olmalıdır; birkaç dakikada 0'a inmiyorsa (hosting o sonuçları sürekli reddediyor; uyarıda "hosting'e verilemiyor" görünür) beklenmez: o mesajlara cevap gitmez ve sorgu 6'da `bekliyor` görünür. Böylece hosting'teki `durum/` aynası günceldir (her sonuç onu günceller). Hosting'te `processing` satır kalabilir: sonucu hosting'e hiç verilemeyen mesajlardır (Postgres'te sorgu 6'da `gonderilmedi`, sağlık uyarısında görünür). `worker=off` iken onları kimse süpürmez; H.6'da hosting onları "takılı" sayar. Beklemeden devam edilir; bu mesajlara cevap gitmediği Lokman'a uyarıda ve sorgu 6'da görünür.
3. Pilot kayıtları korunur: `sudo -u postgres pg_dump -Fc -d portman -f /var/backups/portman/pilot-<tarih>.dump` ve Mac'e `scp`.
4. Ajan dosya moduna döner: `rm /etc/systemd/system/portman-agent.service.d/kalici.conf; systemctl daemon-reload; systemctl restart portman-agent` (aynı paket, B1/B2 düzeltmeleriyle). Tam dönüş gerekirse E'deki PHP ve paket yedekleri geri konur.
5. Veritabanı silinmez, adı değiştirilir: `sudo -u postgres psql -c "ALTER DATABASE portman RENAME TO portman_pilot_<tarih>"`. Pilot kayıtları orada ve yedekte kalır.
6. `"worker": "vps"`. Ajan dosya modunda kuyruktakileri alır. Eşleşme ve OpenAI anahtarları geri alınmaz; eski anahtar etkinleşmez.

Postgres'e yeniden geçiş: `/opt/portman/data/kalici_bekleyen/` boş olmalı (içinde kalan dosya eski veritabanına aittir; `hatali/` ile birlikte `portman_pilot_<tarih>` yedeğinin yanına taşınır). Sonra `sudo -u postgres createdb -O portman -E UTF8 portman` ve F'nin 1–6. adımları. İçe aktarma yalnız boş veritabanına yapılır; dosya modunda ilerlemiş konuşmalar böylece Postgres'teki eski durumla ezilmez.

## 5. Henüz doğrulanamayan ve kalan riskler

- **Gerçek PHP hattı:** `feature.php` ve `api.php` değişiklikleri gerçek `lib.php` ile yerelde geçti (B), ama canlıda henüz yok. Canlıda E'de (dosya modu) ve G'de (kalıcı mod) görülür.
- **Medya indirme yolu:** `lib.php`'deki `pm_download` → `pm_stream_media` (bayinin gönderdiği dosyanın arşivlenmesi) B'de sınanmadı; testler oraya girmiyor. Bu yol İE-02'de değişmedi.
- **Gerçek WhatsApp ve LLM:** yalnız kapı G'de görülür. Sahte hosting Meta'nın gecikmeli ya da eksik bildirimlerini, 24 saat penceresini ve `dry_run`'ı taklit etmez.
- **VPS:** Postgres kurulumu, systemd ve cron adımları VPS'te koşulmadı (kapı D).
- **Sızan anahtar:** C'de kapandı (28.09). Sızdığı düşünülen eşleşme anahtarı ve onunla alınabilen OpenAI anahtarı artık geçersiz.
- **v1.1.1'den kalan pencere:** hosting `claim` cevabını gönderip ajan onu alamazsa (ağ kopması) ya da ajan cevabı aldıktan sonra diske ya da Postgres'e yazamadan ölürse (milisaniyeler), satır hosting'te 600 sn sonra "failed" olur ve cevapsız kalır. Bu v1.1.1'de de böyledir; hosting kuyruğunda görünür ve yeniden kuyruğa konursa (tekrar gelen mesaj) cevap verilir.
- **VPS saati:** "hosting satırı süpürüldü" kararı VPS saatindeki iki an arasındaki farka dayanır (ajanın mesajı aldığı an ve sonraki başarılı claim). Çalışan sunucuda saat 660 sn'den çok ileri atlarsa (ör. açılışta büyük bir NTP düzeltmesi) ve aynı anda o işin devri hata veriyorsa, hosting'in hâlâ alabileceği bir sonuç "gönderilmedi" sayılabilir; uyarıda ve sorgu 6'da görünür.
- **Süpürme sınırındaki deneme sıklığı:** mesaj alınalı 480 sn olmuş ve sonucu işe özgü bir hatayla hep reddedilen bir iş, "süpürüldü" kesinleşene dek (en çok ~3 dakika) her turda yeniden yüklenir; bu, hosting'in süpürmesinden önce son denemeyi kaçırmamak içindir. Boşaltmada (`worker=off`) claim olmadığı için bu, geçiş bitene dek her turda sürer (H.2).
- **Saat:** Meta'nın hiçbir bildirimi henüz gelmemişse onay sınırı hosting'in API kabul anıdır (hosting saati). Hosting ve Meta saatleri arasındaki fark birkaç saniyeyi geçmezse etkisizdir; gösterimde sorgu 4'te görülür.
- **Uyarının görüneceği yer:** "gönderilmedi", "belirsiz", "Meta iletemedi", "hosting'e verilemiyor" ve Postgres'e yazılamayan mesaj uyarıları `vps-health.json` (`errors`), `vps.log` ve kanıt sorgusu 6'da görünür. Panel dosyalarına dokunulmadığı için panelde ayrı bir uyarı yoktur; Patron'a WhatsApp bildirimi de gitmez.
- **Postgres'e yazılamayan mesaj:** veri hatası veren mesaj `hatali/`'ye alınır ve cevapsız kalır (hosting 600 sn sonra "takılı" sayar); uyarıda görünür. NUL karakteri bilinen tek neden olarak yazmadan önce temizlenir.

## 6. Kabul ve İE-02'nin kapanışı

Kapı G'deki yedi adım kanıt sorgularıyla gösterildiğinde İE-02 kapanır. Sonraki iş İE-03'tür: küçük, kaynaklı, yetki ayrımlı RAG (`IE-02.md` "Sonraki iş").
