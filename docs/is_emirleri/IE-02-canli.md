# İE-02 · Canlıya bağlama planı (Patron numarası)

Dal: `ie-02`. Dayanak: Astra'nın 28 Eylül ikinci değerlendirmesi, D-03 ve D-04. Bu plan onaya sunulur. Her kapı (A–H) ayrı açık onayla açılır; onaylanmayan kapıdan sonrası yapılmaz. Sunucu komutlarını Lokman kendi terminalinden çalıştırır. Hiçbir komut anahtar değeri yazdırmaz; anahtarlar yalnız 12 haneli özet parmak iziyle karşılaştırılır.

## 1. Durum: hazır olan ve olmayan

| Parça | Durum | Kanıt ya da eksik |
|---|---|---|
| Postgres kalıcı akış (depo, işleyici, göç 001–002) | Test edildi, izole | `testler/kalici`: 80 test, gerçek Postgres 16 |
| Ajanın kalıcı modu (`vps/agent.py`) | Test edildi, **sahte hosting ile** | `test_baglanti.py`; sahte hosting `api.php`'yi taklit eder, PHP'yi sınamaz |
| `feature.php` (`context_id`), `api.php` v1.2 (`giden_durum`) | Yazıldı; **gerçek PHP hattında koşulmadı** | `kanal/tests/baglanti_test.php` ve `e2e_kalici.py` `portman/lib.php` ister; bu dosya depoda yok (kapı B) |
| VPS Postgres kurulumu | Betik hazır; VPS'te koşulmadı | `vps/pg_kurulum.sh`: parolasız peer bağlantısı, saf psycopg ve göçler ayrı bir deneme kümesinde sınandı; systemd ve cron adımları VPS'te görülecek |
| Gerçek WhatsApp, gerçek LLM | Denenmedi | Kapı G (kabul gösterimi) |

## 2. Dar değişiklikler (depoda, `ie-02`)

| Dosya | Değişiklik |
|---|---|
| `kanal/feature.php` | Gelen satıra `context_id` (bayinin alıntıladığı mesajın kimliği; yalnız `wamid.` ile başlıyorsa). Sürüm `kanal-v1.2` (`health.json`'da görünür). Başka davranış değişmedi. |
| `kanal/api.php` | Yeni salt okunur işlem `giden_durum`: verilen giden satırların durumu, WhatsApp kimliği, API kabul anı, Meta teslim durumu ve ilk teslim anı; en çok 200 satır. Sürüm `kanal-api-v1.2`. Öteki işlemler değişmedi. |
| `vps/agent.py` | `PORTMAN_PG_DSN` varsa kalıcı mod: claim → Postgres → işleme → hosting'e devir (`result`) → durum eşitleme (`giden_durum`). Tekrar gelen kanal mesajı ikinci iş açmaz. Yeniden başlarken ölü sürecin kirasını düşürür. SIGTERM'de eldeki adımı bitirir. Hosting API v1.2 ve göçler tamam değilse iş almaz. `PORTMAN_PG_DSN` yoksa v1.1.1 dosya modu aynen çalışır (`e2e_vps.py` 19/19). |
| `vps/paketle.py` | Pakete `depo.py`, `kalici.py`, `depo_aktar.py`, `goc/*.sql`, `kanit_sorgulari.sql`, `tekrar_dene.py` eklenir. |
| `kanal/goc/002_…sql` | API kabulü (`kabul_edildi`, `kabul_zamani`) ile Meta teslimi (`teslim_durumu`, `teslim_zamani`) ayrı; `hostingte` durumu; `onay_zinciri` ve `cevap_baglari` görünümleri. |
| `vps/pg_kurulum.sh`, `vps/kanit_sorgulari.sql`, `vps/tekrar_dene.py` | Kurulum (kapı D), salt okunur kanıt sorguları ve tekrar gelen mesaj denemesi (kapı G). |

Dokunulmayanlar: `webhook.php`, `worker.php`, panel dosyaları, `portman/lib.php`, `store.json`, Görev 2/3 ve hosting'teki `worker.py`.

## 3. Gerçek PHP hattı nasıl doğrulanır

Sahte gönderici ve sahte hosting testleri PHP'yi doğrulamaz; bunları tamamlanmış saymıyorum. Doğrulama iki adımda yapılır.

1. **Yerel, gerçek PHP kodu ile (kapı B).** `portman/lib.php`'nin bir kopyası gerekir. Bu dosya kütüphane kodudur; anahtarlar `data/config.json` ve `ayarlar.json`'dadır. Göndermeden önce içinde anahtar olmadığı sayılarak denetlenir (aşağıda). Kopya gelince şunlar koşulur:
   - `php kanal/tests/offline_test.php lib.php`: v1.1.1'in 30 testi, gerileme denetimi;
   - `php kanal/tests/baglanti_test.php lib.php`: `context_id` ve `giden_durum`, 14 test;
   - `python3 kanal/tests/e2e_vps.py lib.php`: dosya modu, gerçek `api.php` ile ajan (`php -S`), 19 test;
   - `python3 kanal/tests/e2e_kalici.py lib.php`: kalıcı mod, gerçek `api.php` + ajan + Postgres; tekrar gelen mesaj ve onay zinciri dahil, 14 test.

   Meta'ya ve OpenAI'ye bağlanılmaz. Bu testler 28.09'da elle yazılmış taslak bir `lib` ile ön denemeden geçti (30/30, 14/14, 19/19, 14/14). Bu ön deneme **sayılmaz**; yalnız benim kodumdaki hataları erken yakalamak içindi.
2. **Canlıda (kapı F ve G).** PHP yüklendikten sonra önce dosya modunda bir Patron mesajı gönderilir (gerileme denetimi). Kalıcı mod bu testten sonra açılır ve kabul gösterimi gerçek Meta ile yapılır.

## 4. Onay kapıları

Yollar: hosting `/home/portatifevcom/portman_app/kanal` (aşağıda `KANAL`), VPS `/opt/portman`, servis `portman-agent`.

### A · Güncel sürümün salt okunur doğrulanması (değişiklik yok)
Hosting'te (SSH ya da DirectAdmin terminali):
```
cd /home/portatifevcom/portman_app/kanal
sha256sum feature.php api.php worker.py | cut -c1-16
php -r '$s=json_decode(file_get_contents("settings.json"),true); echo json_encode(array_intersect_key($s, array_flip(["enabled","worker","mode","dry_run"]))),"\n";'
php -r 'foreach(["health.json","vps-health.json"] as $f){$h=json_decode(@file_get_contents($f),true)?:[]; echo $f," ",$h["surum"]??"-"," ",substr($h["package_sha256"]??"",0,12)," ",date("c",$h["checked_at"]??0),"\n";}'
cat package/SURUM.txt; cut -c1-12 package/current.sha256
stat -c '%y' api_token.txt; tr -d '\n' < api_token.txt | sha256sum | cut -c1-12
```
VPS'te:
```
cat /opt/portman/app/SURUM.txt; cut -c1-12 /opt/portman/app/PACKAGE_SHA256
sha256sum /opt/portman/agent.py | cut -c1-16
systemctl is-active portman-agent; systemctl show portman-agent -p ActiveEnterTimestamp
stat -c '%y' /etc/portman/agent.env; grep '^PORTMAN_API_TOKEN=' /etc/portman/agent.env | cut -d= -f2- | tr -d '\n' | sha256sum | cut -c1-12
```
Karşılaştırma (v1.1.1, `SHA256SUMS`):
- `feature.php` `91c954a62537606e`, `api.php` `455f8c7414442183`, `worker.py` `3687f3763c9a759a`, `agent.py` `72acb4238c1bfb1d`;
- paket `bd1ca27c…` (22.09).

Değer farklıysa "canlı v1.1.1" yazılmaz; fark önce incelenir. İki parmak izi aynıysa ve `api_token.txt` 22.09'dan eskiyse sızan eşleşme anahtarı hâlâ etkindir.

### B · `lib.php` kopyası ile yerel PHP testleri (değişiklik yok)
Hosting'te önce anahtar sayımı yapılır; yalnız sayı yazar, değer yazmaz:
```
grep -cE "EAA[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|app_secret['\"]?\s*=>\s*['\"][^'\"]+" /home/portatifevcom/public_html/portman/lib.php
```
Sonuç 0 ise dosya sohbete eklenir; 0 değilse eklenmez ve birlikte bakarız. Ardından 3. bölümdeki dört test koşulur.

### C · Sızan anahtarın yenilenmesi (A'da etkin çıkarsa; ayrı onay)
1. VPS'te yeni eşleşme anahtarı üretilir; ekrana yazılmaz:
   ```
   umask 077; N=$(openssl rand -hex 32); sed -i "s/^PORTMAN_API_TOKEN=.*/PORTMAN_API_TOKEN=$N/" /etc/portman/agent.env; unset N
   ```
2. Anahtar hosting'e aktarılır.
   - Hosting'e SSH varsa, Mac'ten ekrana yazmadan:
     ```
     ssh root@<VPS> "grep '^PORTMAN_API_TOKEN=' /etc/portman/agent.env | cut -d= -f2-" | ssh <hosting> "umask 077; cat > /home/portatifevcom/portman_app/kanal/api_token.txt"
     ```
   - SSH yoksa değer yalnız Lokman'ın kendi ekranında bir kez gösterilir ve DirectAdmin'de dosyaya yapıştırılır; sohbete yazılmaz.
3. `systemctl restart portman-agent`.
4. Doğrulama: A'daki iki parmak izi yeniden alınır. Yeni değerler birbirine eşit, eskisinden farklı olmalı. `vps-health.json` güncellenmeli. Hosting yalnız dosyadaki anahtarı kabul ettiği için eski anahtar geçersiz olur; `api-audit.json`'da yanlış anahtar denemeleri görünür.
5. OpenAI anahtarı da yenilenir (sızan eşleşme anahtarıyla okunabiliyordu). Lokman OpenAI panelinde yapar; `ayarlar.json` güncellenir. Ücretsizdir. Ayrı onayla.

Geri dönüş bu anahtarları eski hâline getirmez; hiçbir adım eski anahtarı yeniden etkinleştirmez.

### D · VPS'e Postgres kurulumu (trafik değişmez)
```
ssh root@<VPS> 'bash -s' < vps/pg_kurulum.sh
```
- Kurulanlar: Postgres 16; yalnız yerel bağlantı; parolasız `portman` rolü (peer); saf psycopg; günlük `pg_dump` (14 gün saklanır, daha eskisi silinir).
- Betik sonunda boş veritabanıyla bir yedek alıp ayrı veritabanına geri yükler.
- Ajan dosya modunda kalır.
- Geri alma: `apt-get remove postgresql` ve `/etc/cron.d/portman-pg-yedek` silinir. İçinde veri yoktur.

### E · Hosting PHP ve paket yüklemesi (dosya modu sürer)
1. Yedek: `KANAL/feature.php`, `api.php` → `*.before-ie02-<tarih>.php`. `package/` klasörü → `package.before-ie02-<tarih>/`.
2. Depodan `kanal/feature.php` ve `kanal/api.php` → `KANAL/`.
3. `python3 vps/paketle.py` → `vps/build/current.zip`, `current.sha256`, `SURUM.txt` → `KANAL/package/`. Ajan paketi kendisi günceller. `PORTMAN_PG_DSN` olmadığı için dosya modunda kalır.
4. Doğrulama:
   - `health.json` surum `kanal-v1.2`;
   - `settings` `api` alanı `kanal-api-v1.2`;
   - `vps-health.json` surum `vps-agent-v1.2`;
   - Patron numarasından bir mesaj eskisi gibi cevaplanır (dosya modu, gerileme denetimi).
5. Geri alma: yedek dosyalar ve eski paket geri konur.

### F · Kalıcı moda geçiş
1. `KANAL/settings.json` → `"worker": "off"`.
   - Bundan sonra gelen mesajlar kaybolmaz: webhook yakalamaya devam eder, satırlar `queued` bekler.
   - Hiçbir işleyici iş almaz.
2. Boşalma: `state.json`'da `processing` satır kalmayana dek beklenir. Giden `pending` satırlar tik ile gider. `depo_aktar` `processing` satır varken zaten çalışmaz.
3. Yedek:
   - hosting: `tar czf ~/yedek-ie02-<tarih>.tgz -C /home/portatifevcom/portman_app kanal/state.json kanal/durum kanal/projects kanal/settings.json`;
   - VPS: `tar czf /root/yedek-ie02-<tarih>.tgz -C /opt/portman data app`.
   - İkisi de Mac'e indirilir.
4. Hosting'in `durum/` ve `state.json` kopyası VPS'e alınır (`/root/gecis/kanal/`), sonra:
   ```
   sudo -u portman env PORTMAN_PG_DSN=dbname=portman /opt/portman/venv/bin/python /opt/portman/app/kalici.py goc
   sudo -u portman env PORTMAN_PG_DSN=dbname=portman /opt/portman/venv/bin/python /opt/portman/app/depo_aktar.py ice --kanal /root/gecis/kanal
   ```
   - Konuşmalar ve askıdaki sorular Postgres'e geçer.
   - İşlenmiş mesajlar yalnız tekilleştirme için kaydedilir.
   - Kuyrukta bekleyenler (`kuyrukta_birakildi`) hosting'te kalır; ajan onları claim ile alır.
5. Kalıcı mod açılır:
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
| 6 | r02 PDF'ini alıntılayarak "onaylıyorum" | Kabul edilir: "Onayınız kaydedildi (…, revizyon 2)" | Sorgu 4 (r02 onaylandı), 5 (kabul true, sınır teslim) |
| 7 | VPS'te: `sudo -u portman env PORTMAN_PG_DSN=dbname=portman /opt/portman/venv/bin/python /opt/portman/app/tekrar_dene.py <1. mesajın kimliği>` | Aynı kanal mesajı yeniden verilir; ikinci iş açılmaz ("hayır", iş sayısı 1) | Çıktı; sorgu 2 (mesaj başına en çok 1 iş) |

Kanıt: `sudo -u portman psql -d portman -f /opt/portman/app/kanit_sorgulari.sql`. Sorgular salt okunurdur, numaralar maskelidir ve mesaj metni yazılmaz. Çıktı sohbete eklenir.

Adım 7 hosting'e dokunmaz. Aynı mesajın hosting kuyruğundan ikinci kez gelmesi (claim → Postgres → "yoksay" sonucu) gerçek PHP hattıyla `e2e_kalici.py`'de sınanır (kapı B). Canlıda hosting kuyruğunu elle düzenlemek önerilmez. Meta'nın aynı mesajı yeniden teslim etmesini PHP zaten kimliğe göre tekilleştiriyor (`offline_test.php`).

Bu yedi adım, kayıtlı çıkarım ve sahte hosting ile `test_baglanti.py::test_canli_gosterim_provasi_sahte_hosting` testinde provadan geçti. Prova canlı doğrulama değildir.

Adım 2'de LLM mesajı revizyon değil yeni talep sayabilir. O zaman akış başka bir soruya gider; bu da kaydedilir, uydurulmaz. Böyle olursa adım model koduyla yinelenir ("P6001 yatak odası 1 penceresi 120x180") ya da D-01 sorusu için 2 saat beklenir.

**Ücretli kapsam.**
- OpenAI (gpt-4o-mini): yaklaşık 8 çağrı. Maliyeti OpenAI panelinden izlenir; tutarı burada doğrulanmadı.
- WhatsApp: yaklaşık 12 giden mesaj. 1 Ekim 2026'dan itibaren Meta, 24 saatlik pencere içindeki şablonsuz (servis) mesajları da ücretlendiriyor. Oran pazara göre ve utility oranıyla aynı ([Meta](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing/non-template-messages)). Türkiye oranı gösterimden önce Meta'nın fiyat tablosundan okunur. Gösterim 1 Ekim'den önce yapılırsa bu mesajlar ücretsizdir.

### H · Geri dönüş (gerektiğinde; onayla)
1. `settings.json` → `"worker": "off"`. Gelen mesajlar kuyrukta bekler.
2. Ajanın bekleyen sonuçları hosting'e vermesi beklenir. Kontrol: `SELECT count(*) FROM giden WHERE durum = 'bekliyor'` 0 olmalı. Böylece hosting'teki `durum/` aynası günceldir.
3. Pilot kayıtları korunur: `sudo -u postgres pg_dump -Fc -d portman -f /var/backups/portman/pilot-<tarih>.dump`. Veritabanı silinmez.
4. `rm /etc/systemd/system/portman-agent.service.d/kalici.conf; systemctl daemon-reload; systemctl restart portman-agent` → ajan dosya moduna döner (aynı paket, B1/B2 düzeltmeleriyle). Tam dönüş gerekirse E'deki PHP ve paket yedekleri geri konur.
5. `"worker": "vps"`. Eşleşme ve OpenAI anahtarları geri alınmaz; eski anahtar etkinleşmez.

Postgres'e yeniden geçiş, F'deki içe aktarmayla baştan yapılır.

## 5. Kabul ve İE-02'nin kapanışı

Kapı G'deki yedi adım kanıt sorgularıyla gösterildiğinde İE-02 kapanır. Sonraki iş İE-03'tür: küçük, kaynaklı, yetki ayrımlı RAG (`IE-02.md` "Sonraki iş").
