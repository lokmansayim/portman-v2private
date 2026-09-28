# İE-02 · Canlıya bağlama planı (Patron numarası)

Dal: `ie-02`. Dayanak: Astra'nın 28 Eylül ikinci değerlendirmesi, D-03 ve D-04. Bu plan onaya sunulur. Her kapı (A–H) ayrı açık onayla açılır; onaylanmayan kapıdan sonrası yapılmaz. Sunucu komutlarını Lokman kendi terminalinden çalıştırır. Hiçbir komut anahtar değeri yazdırmaz; anahtarlar yalnız 12 haneli özet parmak iziyle karşılaştırılır.

## 1. Durum: hazır olan ve olmayan

| Parça | Durum | Kanıt ya da eksik |
|---|---|---|
| Postgres kalıcı akış (depo, işleyici, göç 001–002) | Test edildi, izole | `testler/kalici`: gerçek Postgres 16 |
| Ajanın kalıcı modu (`vps/agent.py`) | Test edildi, **sahte hosting ile** | `test_baglanti.py`, `test_hosting_devri.py`. Sahte hosting `api.php`'nin bir kısmını taklit eder (600 sn süpürme, hata enjeksiyonu dahil; taklit etmediği yerler dosyasının başında yazılı). PHP'yi sınamaz |
| `feature.php` (`context_id`), `api.php` v1.2 (`giden_durum`) | Yazıldı; **gerçek `lib.php` ile koşulmadı** | `kanal/tests/baglanti_test.php` ve `e2e_kalici.py` `portman/lib.php` ister; bu dosya depoda yok (kapı B) |
| VPS Postgres kurulumu | Betik hazır; VPS'te koşulmadı | `vps/pg_kurulum.sh`: parolasız peer bağlantısı, saf psycopg ve göçler ayrı bir deneme kümesinde sınandı; systemd ve cron adımları VPS'te görülecek |
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
| `vps/anahtar_yenile.py`, `vps/api_denetim.py` | Anahtar yenileme (kapı C.1) ve salt okunur API denetimi (kapı E.4); ikisi de anahtar değeri yazdırmaz. Pakete girmez, Mac'ten `ssh` ile çalıştırılır. |

Dokunulmayanlar: `webhook.php`, `worker.php`, panel dosyaları, `portman/lib.php`, `store.json`, Görev 2/3 ve hosting'teki `worker.py`.

## 3. Gerçek PHP hattı nasıl doğrulanır

Sahte gönderici ve sahte hosting testleri PHP'yi doğrulamaz; bunları tamamlanmış saymıyorum. Doğrulama iki adımda yapılır.

1. **Yerel, gerçek PHP kodu ile (kapı B).** `portman/lib.php`'nin bir kopyası gerekir. Kopya gelince şunlar koşulur:
   - `php kanal/tests/offline_test.php lib.php`: v1.1.1'in 30 testi, gerileme denetimi;
   - `php kanal/tests/baglanti_test.php lib.php`: `context_id`, `giden_durum` ve onun `state.json`'a yazmadığı, 16 test;
   - `python3 kanal/tests/e2e_vps.py lib.php`: dosya modu, gerçek `api.php` ile ajan (`php -S`), 19 test;
   - `python3 kanal/tests/e2e_kalici.py lib.php`: kalıcı mod, gerçek `api.php` + ajan + Postgres; tekrar gelen mesaj, onay zinciri ve süpürmeyi yalnız `claim`'in yaptığı (ajanın tur sırasının dayandığı özellik) dahil, 18 test.

   Meta'ya ve OpenAI'ye bağlanılmaz. Bu testler 28.09'da elle yazılmış taslak bir `lib` ile ön denemeden geçti (30/30, 16/16, 19/19, 18/18). Bu ön deneme **sayılmaz**; yalnız benim kodumdaki hataları erken yakalamak içindi.
2. **Canlıda (kapı E, F ve G).** PHP yüklendikten sonra önce dosya modunda bir Patron mesajı gönderilir (gerileme denetimi). Kalıcı mod bu testten sonra açılır ve kabul gösterimi gerçek Meta ile yapılır.

## 4. Onay kapıları

Yollar: hosting `/home/portatifevcom/portman_app/kanal` (aşağıda `KANAL`), VPS `/opt/portman`, servis `portman-agent`. Mac'teki yedek klasörü `~/PortmanYedek/` (aşağıda `YEDEK`).

### A · Güncel sürümün salt okunur doğrulanması (değişiklik yok)
Hosting'te (SSH ya da DirectAdmin terminali):
```
cd /home/portatifevcom/portman_app/kanal
sha256sum feature.php api.php worker.py | cut -c1-16
php -r '$s=json_decode(file_get_contents("settings.json"),true); echo json_encode(array_intersect_key($s, array_flip(["enabled","worker","mode","dry_run"]))),"\n";'
php -r 'foreach(["health.json","vps-health.json"] as $f){$h=json_decode(@file_get_contents($f),true)?:[]; echo $f," ",$h["surum"]??"-"," ",substr($h["package_sha256"]??"",0,12)," ",date("c",$h["checked_at"]??0),"\n";}'
cat package/SURUM.txt; cut -c1-12 package/current.sha256
stat -c '%y' api_token.txt
php -r 'echo "eşleşme anahtarı parmak izi: ", substr(hash("sha256", trim(file_get_contents("api_token.txt"))), 0, 12), "\n";'
```
VPS'te:
```
cat /opt/portman/app/SURUM.txt; cut -c1-12 /opt/portman/app/PACKAGE_SHA256
sha256sum /opt/portman/agent.py | cut -c1-16
systemctl is-active portman-agent; systemctl show portman-agent -p ActiveEnterTimestamp
stat -c '%y' /etc/portman/agent.env
python3 -c 'import hashlib; v=[l.split("=",1)[1] for l in open("/etc/portman/agent.env") if l.startswith("PORTMAN_API_TOKEN=")][0].strip(); print("eşleşme anahtarı parmak izi:", hashlib.sha256(v.encode()).hexdigest()[:12])'
```
İki parmak izi aynı biçimde hesaplanır (PHP `trim` ve Python `strip`: satır sonu ve boşluk atılır; hosting de anahtarı böyle okur).

Karşılaştırma (v1.1.1, `SHA256SUMS`):
- `feature.php` `91c954a62537606e`, `api.php` `455f8c7414442183`, `worker.py` `3687f3763c9a759a`, `agent.py` `72acb4238c1bfb1d`;
- paket `bd1ca27c…` (22.09).

Değer farklıysa "canlı v1.1.1" yazılmaz; fark önce incelenir. İki parmak izi aynıysa ve `api_token.txt` 22.09'dan eskiyse sızan eşleşme anahtarı hâlâ etkindir.

### B · `lib.php` kopyası ile yerel PHP testleri (değişiklik yok)
`lib.php` kütüphane kodudur; anahtarlar `data/config.json` ve `ayarlar.json`'dadır. Yine de dosya sohbete eklenmeden önce Lokman kendisi bakar. Hosting'te iki komut yalnız satır numarası ve anahtar adını yazar, değer yazmaz:
```
F=/home/portatifevcom/public_html/portman/lib.php
grep -noiE "api_?key|access_?token|app_?secret|client_?secret|password|passwd|db_?pass|parola|sifre|secret|bearer" "$F" | sort -t: -k1,1n -u
grep -nE "EAA[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|[0-9a-f]{32,}|define\(" "$F" | cut -d: -f1 | tr '\n' ' '; echo
```
Lokman bu satırları kendi düzenleyicisinde açar. Hiçbirinde gerçek bir anahtar ya da parola değeri yoksa dosyayı sohbete ekler. Varsa eklemez; o değerleri `X` ile değiştirdiği bir kopyayı ekler ya da birlikte bakarız. Karar sayıma bırakılmaz. Ardından 3. bölümdeki dört test koşulur.

### C · Sızan anahtarın yenilenmesi (A'da etkin çıkarsa; ayrı onay)
Bu adım sırasında Patron numarasından mesaj yazılmaz (anahtar iki tarafta eşleşene kadar ajanın çağrıları 401 alır; kalıcı modda bekleyen sonuçlar geçici hata sayılıp yeniden denenir, dosya modunda `data/pending/`'e alınır).

1. VPS'te yeni eşleşme anahtarı üretilir; ekrana, komut satırına ya da günlüğe yazılmaz, yalnız eski ve yeni parmak izi yazılır. Betik önce anahtar satırı çıkarılmış bir yedek alır; dosyanın izni ve sahibi korunur (`test_vps_betikleri.py`). Mac'ten:
   ```
   ssh root@<VPS> 'python3 -' < vps/anahtar_yenile.py
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
- Kurulanlar: Postgres 16; yalnız yerel bağlantı; parolasız `portman` rolü (peer); saf psycopg; günlük `pg_dump` (14 gün VPS diskinde saklanır, daha eskisi silinir).
- Betik sonunda bir yedek alıp ayrı bir deneme veritabanına geri yükler; geri yükleme başarısızsa durur ve hata verir. Tekrar çalıştırılabilir.
- Yedekler yalnız VPS diskindedir. Mac'e kopya F, G ve H'de elle alınır (aşağıda). Otomatik dış yedek bu planın kapsamında değil.
- Ajan dosya modunda kalır.
- Geri alma: `apt-get remove postgresql` ve `/etc/cron.d/portman-pg-yedek` silinir. İçinde veri yoktur.

### E · Hosting PHP ve paket yüklemesi (dosya modu sürer; B geçmiş olmalı)
1. Yedek: `KANAL/feature.php`, `api.php` → `*.before-ie02-<tarih>.php`. `package/` klasörü → `package.before-ie02-<tarih>/`.
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

**Ücretli kapsam.**
- OpenAI (gpt-4o-mini): yaklaşık 8 çağrı. Maliyeti OpenAI panelinden izlenir; tutarı burada doğrulanmadı.
- WhatsApp: yaklaşık 12 giden mesaj. 1 Ekim 2026'dan itibaren Meta, 24 saatlik pencere içindeki şablonsuz (servis) mesajları da ücretlendiriyor. Oran pazara göre ve utility oranıyla aynı ([Meta](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing/non-template-messages)). Türkiye oranı gösterimden önce Meta'nın fiyat tablosundan okunur. Gösterim 1 Ekim'den önce yapılırsa bu mesajlar ücretsizdir.

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

- **Gerçek PHP hattı:** `feature.php` ve `api.php` değişiklikleri gerçek `lib.php` ile koşulmadı (kapı B).
- **Gerçek WhatsApp ve LLM:** yalnız kapı G'de görülür. Sahte hosting Meta'nın gecikmeli ya da eksik bildirimlerini, 24 saat penceresini ve `dry_run`'ı taklit etmez.
- **VPS:** Postgres kurulumu, systemd ve cron adımları VPS'te koşulmadı (kapı D).
- **v1.1.1'den kalan pencere:** hosting `claim` cevabını gönderip ajan onu alamazsa (ağ kopması) ya da ajan cevabı aldıktan sonra diske ya da Postgres'e yazamadan ölürse (milisaniyeler), satır hosting'te 600 sn sonra "failed" olur ve cevapsız kalır. Bu v1.1.1'de de böyledir; hosting kuyruğunda görünür ve yeniden kuyruğa konursa (tekrar gelen mesaj) cevap verilir.
- **VPS saati:** "hosting satırı süpürüldü" kararı VPS saatindeki iki an arasındaki farka dayanır (ajanın mesajı aldığı an ve sonraki başarılı claim). Çalışan sunucuda saat 660 sn'den çok ileri atlarsa (ör. açılışta büyük bir NTP düzeltmesi) ve aynı anda o işin devri hata veriyorsa, hosting'in hâlâ alabileceği bir sonuç "gönderilmedi" sayılabilir; uyarıda ve sorgu 6'da görünür.
- **Süpürme sınırındaki deneme sıklığı:** mesaj alınalı 480 sn olmuş ve sonucu işe özgü bir hatayla hep reddedilen bir iş, "süpürüldü" kesinleşene dek (en çok ~3 dakika) her turda yeniden yüklenir; bu, hosting'in süpürmesinden önce son denemeyi kaçırmamak içindir. Boşaltmada (`worker=off`) claim olmadığı için bu, geçiş bitene dek her turda sürer (H.2).
- **Saat:** Meta'nın hiçbir bildirimi henüz gelmemişse onay sınırı hosting'in API kabul anıdır (hosting saati). Hosting ve Meta saatleri arasındaki fark birkaç saniyeyi geçmezse etkisizdir; gösterimde sorgu 4'te görülür.
- **Uyarının görüneceği yer:** "gönderilmedi", "belirsiz", "Meta iletemedi", "hosting'e verilemiyor" ve Postgres'e yazılamayan mesaj uyarıları `vps-health.json` (`errors`), `vps.log` ve kanıt sorgusu 6'da görünür. Panel dosyalarına dokunulmadığı için panelde ayrı bir uyarı yoktur; Patron'a WhatsApp bildirimi de gitmez.
- **Postgres'e yazılamayan mesaj:** veri hatası veren mesaj `hatali/`'ye alınır ve cevapsız kalır (hosting 600 sn sonra "takılı" sayar); uyarıda görünür. NUL karakteri bilinen tek neden olarak yazmadan önce temizlenir.

## 6. Kabul ve İE-02'nin kapanışı

Kapı G'deki yedi adım kanıt sorgularıyla gösterildiğinde İE-02 kapanır. Sonraki iş İE-03'tür: küçük, kaynaklı, yetki ayrımlı RAG (`IE-02.md` "Sonraki iş").
