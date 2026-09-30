# İE-04 · Mesaj katmanının canlıya alınması (Kapı M)

Hazırlandı: 30.09.2026 akşam (dal `ie-04`). Lokman'ın 30.09 19:10 isteği: "Astra çizim/veriye başladı, biz WhatsApp tarafını halledelim; VPS ile başlayalım." Bu belge canlıya alma adımlarını, sınırlarını ve geri almayı yazar. **Hiçbir adım bu belgeyle yapılmış sayılmaz; her kapı Lokman'ın açık onayıyla, kendi çıktısı okunarak geçilir.**

## 0. Ne değişir, ne değişmez

| Yer | Şimdi canlıda | Kapı M sonrası |
|---|---|---|
| Hosting `portman_app/kanal/feature.php` | `kanal-v1.2` · `8b47ac75b8dedb77…` | `kanal-v1.3` · `47d63a678d9bc37dee48851ea18dde899763ad68c933bfd0f3afb7357e514351` |
| Hosting `portman_app/kanal/api.php` | `kanal-api-v1.2` · `18eaf8058fb5371a…` | `kanal-api-v1.3` · `36b62e00f45b472313f60ea27d40998036303eb3ea48fd333b9602422cc94360` |
| Hosting `portman_app/kanal/package/` | `kanal-v1.2-20260929-2052` · `9c76af59df065dc5…` (673.389 B, 50 dosya) | `kanal-v1.3-20260930-1948` · `34ae192c15a88defbb0aea757decc77a8ca21644aa7dc34b88d33b6cd5179810` (862.921 B, 60 dosya) |
| VPS `/opt/portman/app` ve `agent.py` | v1.2 paketi | ajan paketi kendisi kurar; `agent.py` paketten güncellenir (`vps-agent` v1.3: `mesaj_katmani`, `ucb_taban_url` ayarları; görselli satır teslimi) |
| VPS Postgres `portman` | göç 001–002 | göç 003 (**yalnız ekler**: `giden.kind`'e `image`, `interactive`; `revizyonlar.ekler`; `secenek_setleri`, `adaylar` tabloları) |
| VPS venv | ezdxf, shapely, pydantic, pymupdf, numpy, psycopg | + matplotlib 3.11.2, pillow, ifcopenshell 0.8.5 (ajan ilk turda pip ile kurar; ≈60 MB + bağımlılıklar; cp312 manylinux tekerlekleri var). Kurulamazsa **ekler üretilmez, akış ve öz-test durmaz** (`worker.ISTEGE_BAGLI`, `test_bagimliliklar.py`) |
| Hosting `settings.json` | `worker vps`, `mode patron` | M1'de dokunulmaz. M2'de tek satır eklenir: `"mesaj_katmani": true` |
| WhatsApp'a gidenler | metin + PDF | **M1'de aynı** (bayrak kapalı = v1.2 davranışı, e2e 18/18). M2'de: görsel başlıklı buton mesajı (Onayla / Revize et) + PDF (+ Patron teknik notu ayrı metin); sorular butonlu; eski buton reddi |
| Anahtarlar, numaralar, veriler | — | değişmez, yazdırılmaz |

Paket farkı (canlı 50 dosya → 60): aynı 42; değişen `SURUM.txt`, `agent.py`, `beyin/karar.py`, `beyin/katalog.py`, `beyin/sema.py`, `depo.py`, `kalici.py`, `worker.py`; yeni `beyin/secenek.py`, `etkilesim.py`, `goc/003_mesaj_katmani.sql`, `motor/bayi_gorseli.py`, `motor/ifc_uret.py`, `motor/ucb_sayfa.py`, `motor/vendor/*` (three.js r128, gömülü; dış ağ yok). Test adayları (`adaylar_test.json`, `TEST*`) pakette **yok**; canlı katalogda 0 aday görünür (`gorunur_adaylar()` = 0).

Yerel kanıt (30.09, bu paketle): 343 Python testi, harness 22/22, PHP çevrimdışı 44/44, gerçek PHP hattı uçtan uca katman kapalı 18/18 ve açık 21/21, referans DXF/PDF parmak izleri 18/18 AYNI (yalnız bilinen sır taraması yanlış pozitifi). `kapi_m_goc.sh` gerçek Postgres'te 001+002'li veritabanında sınandı (`testler/kalici/test_kapi_m.py`: ön koşul reddi, kuru koşum, göç, ikinci koşuda durma).

## 1. Adımlar

Mac klasörü: `27_Kapi_M/` (`yukle/hosting/`, `yukle/paket/`, `betikler/`, `yedek/`, `cikti/`, `KOMUTLAR.txt`). VPS komutlarını Lokman kendi Mac'inde koşar, çıktıyı asistan okur. Hosting'e yalnız DirectAdmin ile girilir.

### M0 · Salt okunur canlı kontrol (onay gerektirmez; değişiklik yok)

`canli_kontrol.sh` → `cikti/0_canli.txt`. Beklenen: servis aktif, kalıcı mod 1, paket `9c76af59…` aynı, açık iş 0, bugünkü yedek var, günlükte hata yok. Beklenmeyen bir şey varsa M1'e geçilmez.

### M1 · Hosting PHP v1.3 + paket v1.3 + göç 003 (bayrak KAPALI; davranış v1.2) — **onay gerekir**

Bu adımda WhatsApp'a giden mesaj biçimi değişmez. Ücret: ajanın öz-testi **1 LLM çağrısı** (≈0,03 $) ve M1.6'daki Patron deneme mesajı **1 LLM çağrısı** (≈0,03 $); WhatsApp bugün ücretsiz.

1. **Yedekler (değişiklik yok).**
   - VPS Postgres: `kapi_g_yedek.sh` ile `portman-m-oncesi-20260930` → `cikti/1_pg_yedek.txt`; dosya `scp` ile `yedek/`'e (göç betiği bu yedeğin 3 saatten yeni olmasını şart koşar).
   - Hosting'ten DirectAdmin ile `yedek/hosting/` içine indirilir: `portman_app/kanal/feature.php`, `api.php`; `package/current.zip`, `current.sha256`, `SURUM.txt`. Asistan Mac'te özetleri karşılaştırır: `8b47ac75…`, `18eaf805…`, `9c76af59…`, `kanal-v1.2-20260929-2052`. Biri farklıysa hiçbir şey yüklenmez.
2. **PHP.** `yukle/hosting/feature.php` ve `api.php` → `portman_app/kanal/` (eskilerinin üzerine). Denetim: `ssh portman-vps 'python3 -' < betikler/api_denetim.py > cikti/2_api.txt` → `api kanal-api-v1.3`, `worker vps`, `mode patron`, `dry_run false`. v1.2 ajanı v1.3 API ile çalışmayı sürdürür (ajanın şartı `kanal-api-v1.2` ve üstü).
3. **Paket.** `yukle/paket/` üçlüsü `portman_app/kanal/package/`'a şu sırayla: `current.zip` → `SURUM.txt` → **en son** `current.sha256`. Ajan ≤30 sn'de görür, indirir, doğrular, `app/`'ı değiştirir, `agent.py`'yi günceller, yeniden başlar. İlk turda: eksik üç paketi pip ile kurar (birkaç dakika), öz-testi koşar (1 LLM çağrısı), sonra günlüğe **"kalıcı mod bekliyor: Postgres göçü uygulanmamış: [3]"** yazar ve **iş almaz** (bu beklenen durumdur; Patron mesajları hosting'te bekler). M1.2–M1.4 arasında mesaj gönderilmez.
4. **Göç 003.** `ssh portman-vps 'PM_BEKLENEN=34ae192c15a88defbb0aea757decc77a8ca21644aa7dc34b88d33b6cd5179810 bash -s' < betikler/kapi_m_goc.sh > cikti/4_goc.txt`. Betik önce kurulu paketi, SQL dosyasını, yedeğin yaşını, açık iş sayısını ve eksik göçün tam olarak `[3]` olduğunu denetler; biri tutmazsa "DUR" der ve hiçbir şey yapmaz. Sonra `kalici.py goc` koşar ve sonucu yazar (`eksik_goc=[]`, iki yeni tablo, `revizyonlar.ekler`, `giden_kind` image/interactive). Ajan ≤5 dk içinde iş almaya döner.
5. **Doğrulama (salt okunur).** `ssh portman-vps 'PM_BEKLENEN=34ae192c… PM_KARAR=73f9037bee1983bc0c331ed0865408b24fcf225fdda46df0aa2407d01aff8257 PM_BASLANGIC="<M1.3 saati>" bash -s' < betikler/kapi_g2_paket.sh > cikti/5_paket.txt` → kurulu paket beklenenle aynı, **60/60 dosya birebir**, `agent.py` paketteki ile aynı, öz-test `passed` (LLM token'ları), hosting paketi aynı, `pg.env` ve `kalici.conf` var. Günlükte "eksik paket kuruluyor" ve pip sonucu; `install-report.json` `kalan_istege_bagli=[]` beklenir (değilse ekler üretilmez, akış sürer; not düşülür).
6. **Patron deneme mesajı (bayrak kapalı):** "Yeni talep: P6001 aynalı olsun" → beklenen **v1.2 ile aynı**: metin (teknik notlu) + PDF, en çok 3 mesaj. `kapi_g_durum.sh` ile iş/giden/maliyet okunur (`cikti/6_durum.txt`). Bu, M1'in kanıtıdır: yeni paket eski davranışı bozmadı.

**M1 geri alma:** PHP için `yedek/hosting/` v1.2 dosyaları geri yüklenir. Paket için `22_Kapi_G2/yukle/` üçlüsü geri yüklenir (`current.sha256` en son); ajan `9c76af59…` paketini ve içindeki `agent.py`'yi geri kurar. Göç 003 geri alınmaz ve alınması gerekmez: v1.2 kodu yeni tablolara ve sütuna bakmaz, `eksik_goc` v1.2 paketinde `[]` kalır. **Veritabanı yedekle ezilmez.** Durdurma: DirectAdmin'de `settings.json` → `"worker": "off"`.

### M2 · Bayrak AÇIK, Patron testleri — **ayrı onay gerekir**

Ön koşul: M1.5 ve M1.6 temiz. Ücret: her serbest metin **1 LLM çağrısı** (≈0,03 $); **buton cevapları LLM çağırmaz**. Aşağıdaki dizi ≈3 LLM çağrısı (≈0,10 $). WhatsApp 1 Ekim'den önce ücretsiz; 1 Ekim'den itibaren servis mesajları ücretli (Türkiye utility tarifesi, o gün Meta'nın dosyasından okunur).

1. DirectAdmin: `portman_app/kanal/settings.json` içine `"mesaj_katmani": true` (JSON virgülüne dikkat). `api_denetim.py` ayarı göstermez; ajan ayarı bir sonraki `settings` turunda alır (≤30 sn). `ucb_taban_url` **yazılmaz** (3D barınağı kararı M3).
2. **T1** Patron: "Yeni talep: P6001 aynalı olsun" (1 LLM). Beklenen: (a) üstünde plan görseli olan mesaj, metin, butonlar **Onayla / Revize et**, altbilgi `PM-… r01`; (b) PDF; (c) Patron teknik notu ayrı metin (`ekler görsel var, IFC var, 3D sayfa`). Görsel WhatsApp'ta açılmalı, butonlar görünmeli.
3. **T2** Patron: **Revize et** butonu (0 LLM). Beklenen: değişiklik sorusu (kural katmanı; buton kimliği `r:<no>:1` teknik notta).
4. **T3** Patron: serbest metin "yatak odası 1 penceresi 120x120 olsun" (1 LLM; 29.09 G'de aynı türden değişiklik gerçek mesajla geçti). Beklenen: aynı projede r02 (yeni İş Emri no); görselli buton mesajı + PDF.
5. **T4** Patron: r01 mesajındaki **eski Onayla** butonuna dokunur (0 LLM). Beklenen: "Bu buton … r01 planına ait; güncel plan … r02" metni; **durum değişmez** (Postgres'te r02 hâlâ `onay_bekliyor`).
6. **T5** Patron: r02 mesajındaki **Onayla** (0 LLM). Beklenen: onaylandı; `revizyonlar` r02 `onaylandi`, `giden.revizyon_id` bağlı.
7. Okuma: `kapi_g_durum.sh` + `kapi_g_teshis.sh` (`cikti/7_*.txt`); WhatsApp ekran görüntüleri (numara maskeli) `27_Kapi_M/cikti/`.

Meta'nın etkileşimli mesajı ya da görsel başlığı reddetmesi ilk kez gerçek hatta görülecek şeydir (yerelde sahte Meta ile geçti). Reddederse: `feature.php` `interactive_invalid` dışındakileri yeniden dener; Patron en azından PDF'i alır; hata `cikti/`'ya alınır, düzeltme yerelde yapılır. **M2 geri alma:** `"mesaj_katmani": false` (ya da satırı silmek) → anında v1.2 davranışı; kod ve göç yerinde kalır.

### M3 · 3D bağlantısı barınağı — **karar + ayrı iş**

3D sayfası (`motor/ucb_sayfa.py`, tek dosya ≈690 KB, dış ağ yok) her revizyonda üretilir ve `revizyonlar.ekler.ucb.dosya` ile VPS'te durur; `ucb_taban_url` ayarı yokken **bağlantı butonu gönderilmez** ve söz veren bir mesaj da gitmez. Seçenekler:

| | Hosting'te statik sayfa | VPS'te statik sunucu |
|---|---|---|
| Yol | `api.php`'ye HTML kabulü + `developer/3d/<tahmin edilemez yol>/<no>/rNN/index.html` (`ucb_taban_url` = o kök) | VPS'e nginx/Caddy + alan adı/sertifika; ajan dosyayı yerel dizine yazar |
| Artı | DirectAdmin dışında sunucu işi yok; mevcut hat | hosting'e dosya taşınmaz |
| Eksi | `api.php` değişikliği (yazma yolu, boyut sınırı, içerik denetimi); hosting'te ≈0,7 MB × revizyon | yeni sunucu yüzeyi, sertifika, güvenlik duvarı kuralı |

Öneri: hosting'te statik sayfa (küçük `api.php` eki, tahmin edilemez yol, yalnız `.html`, üst sınır 2 MB, dizin listesi kapalı). Karar Lokman'ındır; kararla birlikte yerelde yapılır ve ayrı bir kapıyla canlıya alınır. O güne kadar A5'in "3D bağlantısı" kısmı canlıda **Kısmen** kalır.

## 2. Bu kapıdan sonra A1–A6 (beklenen, kanıtla güncellenecek)

| # | M1 sonrası | M2 sonrası |
|---|---|---|
| A1 | canlıda v1.2 (yakın model listesi) | aynı; öncelik sorusu ancak ≥2 gerçek aday kayıtlıyken sorulur |
| A2 | çalışmıyor (0 geçerli aday) | çalışmıyor — Astra'nın üç adayı + teknik kabul gerekir |
| A3 | yalnız P6001 metinle | yalnız P6001 (seçenek seti yok) |
| A4 | P6001 metinle | Revize butonu + metinle r02 (T2–T3) |
| A5 | PDF | görsel + PDF; 3D bağlantısı yok (M3) |
| A6 | metinle | butonla: eski onay reddi, güncel onay kabulü (T4–T5) |

## 3. Kayıtlar

- Betikler: `vps/kapi_m_goc.sh` (yeni), `vps/kapi_g_yedek.sh` (ad deseni `portman-<kapı>-<ne>-<tarih>`), `vps/kapi_g2_paket.sh`, `vps/kapi_g_durum.sh`, `vps/kapi_g_teshis.sh`, `vps/api_denetim.py`, `vps/canli_kontrol.sh`.
- Kod: `kanal/worker.py` `GEREKLI` / `ISTEGE_BAGLI` ayrımı ve kurulum sonrası yeniden denetim; 3D bağlantısı yokken söz veren metin kaldırıldı; Patron teknik notuna ekler özeti.
- Sonuçlar ve saatler bu belgenin altına, çıktı dosyalarına atıfla eklenir (M0 → M1 → M2).

## 4. Onaylar ve kayıt

- **30.09 20:05, Lokman:** M1 onaylandı (M0 ile başlanır); M2, M1.5–M1.6 temiz çıkarsa aynı akşam; M3 için karar: **hosting'te statik sayfa** (ayrı kapıyla, yerelde yapılıp canlıya alınır). Bu satırın altına adımların saatleri ve çıktı dosyaları eklenir.
