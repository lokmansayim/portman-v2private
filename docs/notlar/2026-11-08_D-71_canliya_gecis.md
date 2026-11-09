# Canlıya kontrollü geçiş (D-71; Kurulum Panosu satır 13 ve 119; 8 Kasım 2026)

Karar: `KARARLAR/D-71.md` (Lokman, 8 Kasım 16:25 UTC kartı, "Şimdi, kontrollü geçelim"). Asistan sunucuya bağlanmaz; komutları Lokman
Mac'inden koşar (`AGENTS.md` › Sunucu erişimi), çıktı dosyaya yazılır ve okunur. Lokman'a giden kısa sürüm: PF
`Canliya_Gecis/2026-11-08_komutlar.md`.

Sıra: **0** etiket → **1** tatbikat (satır 13) → **2** ön bakış ve kurulum (satır 119) → **3** özellikler tek tek (satır 80, 83, 110, 111;
her biri ayrı onay).

## Ön bakış (8 Kasım, asistan; sunucuya dokunmadan)

- **Canlı:** `v2026.10.16` (667658a, 16 Ekim), önceki `v2026.10.15`. Yeni etiket `v2026.11.08` → `main` `d7fdd75b` (PR #142'nin birleşmesi).
  Arada 117 PR (#25…#142).
- **Tatbikat betikleri sunucudakiyle aynı:** `v2026.10.16` ile `main` arasında `vps/yedek_geri_dene.sh`, `kapi12_tatbikat.sh`,
  `geri_don.sh`, `durum.sh`, `ayar.sh` farkı yok. `vps/` altında değişen yalnız `agent.py` (üç yeni ayar anahtarını ajana geçirir),
  `guncelle.sh` (nginx adımına `PM_DATA`), `kurulum.sh` (ilk kurulum şablonu), `nginx/portman.conf` ve `nginx_uygula.sh` (bayiye 3D
  yolu `/3d/<anahtar>/`), yeni `ucb_ac.sh`.
- **Göçler:** 009 `bayi_varsayilanlari` (yeni tablo), 010 `kayit_talepleri` (yeni tablo, dizinler), 011 `kontrol_kapanisi` (iki CHECK
  genişler, üç boş sütun). Yalnız ekler. `v2026.10.16`'nın kodu fazladan uygulanmış göçe bakmaz (`depo.eksik_goc` yalnız eksik olanı
  sayar); geri dönüş güvenli (aşağıda kanıt).
- **Sunucu paketleri:** `vps/gereksinimler.txt` değişmedi. Değişen `kanal/`, `beyin/`, `motor/`, `vps/` dosyalarının içe aktardığı
  dış paketlerin hepsi listede (numpy, ezdxf, matplotlib, pillow, shapely, PyMuPDF, ifcopenshell, psycopg, pydantic, openpyxl, vtk).
- **LLM'in okuması değişmedi:** `beyin/prompt.md` ve `beyin/sema.py` aynı.
- **Ücret:** kurulum LLM'i ve WhatsApp'ı çağırmaz. İki koşul ücret doğurabilir, ön bakış ikisini de gösterir: (a) sunucuda öz-test
  sonucu (`data/self-test-result.json`) yoksa ajan yeni sürümde öz-testi koşar, LLM anahtarı varsa 1 çağrı (~0,03 $); (b) 24 saati
  geçmiş, kararı bekleyen mühendis kontrolü varsa (BK-10, D-19) ilk mesai dakikasında Patron'a 1 bildirim, pencere kapalıysa ücretli
  şablon.
- **Yedekler:** Drive › Portman-Yedek'te her gece bir dosya; en yenisi `portman-20261108-034151.tar.age` (71.144.600 B, 8 Kasım 00:41
  UTC). 20 Ekim'den beri boy aynı: sunucuda yeni kayıt yok.
- **Liste bayiye gitmez:** canlı akış yükleme listesini bayiye göndermez (`kanal/worker.py` › `ekler_uret`); prefabrik liste her
  teklifte Lokman'ın gözünden geçer (D-71).

## Kanıt (8 Kasım 2026, bu bulut ortamı; canlıya, LLM'e, WhatsApp'a bağlanmadan)

- **Yerel kurulum provası** (gerçek ağaçlarla; yerel Postgres 16, sahte systemctl ve sağlık; betik scratchpad'de, depoya girmedi):
  `v2026.10.16`'nın kendi `guncelle.sh`'iyle ilk kurulum (göç 1–8) → sunucudaki gibi kurulu sürümün `guncelle.sh`'iyle `v2026.11.08`
  (yerel etiket, `d7fdd75b`): `dosyalar açıldı (737 dosya; .git yok)`, `içe aktarma tamam`, `genel motor: AYNI (… liste 93 satır, pdf
  var)`, `uygulanan göçler: [9, 10, 11]`, `sağlık: sürüm v2026.11.08, Postgres bağlı`, `nginx: uygulandı … yedek: …onceki-…`,
  çıkış 0 → `geri_don.sh` ile `v2026.10.16` (sağlık geldi, çıkış 0); eski kodda `kalici.py goc` → `yok (güncel)`, `eksik göç: yok`,
  şema `[1…11]` → `geri_don.sh` ile yeniden `v2026.11.08` (çıkış 0).
- **Eski sürümün kalıcı akış testleri yeni şemada:** `v2026.10.16` ağacına göç 009–011 eklenip `pytest testler/kalici` koşuldu
  (sonuç aşağıda, "Doğrulama").
- **Altın set (İE-19, ücretsiz; `python3 -m testler.altin.kos`):** kör dilim (mühür tuttu) karar 15/20, kayıtlı okuma 13/20, uçtan uca
  14/20, güvenlik sayacı 1; açık set karar 67/80, uçtan uca 65/80, güvenlik sayacı 0.
- **Ön bakış betiği:** `pytest testler/kalici/test_kurulum_on_bakis.py` → 4 geçti (temiz sunucu "KURULABİLİR"; açık iş, bekleyen giden,
  hafif etiket, açık özellik, öz-test sonucu yok ve 24 saati geçmiş kontrol "BEKLE" ya da "NOT/DİKKAT"; dosyalar koşudan sonra aynı;
  `bash -s` ile stdin'den koşarken stdin okuyan komut betiğin kalanını yutmaz; işlevsiz ilk hâl bu koşuda `[3/6]`'da kesiliyordu).
- **Doğrulama:** `bash araclar/ortam_kur.sh --dogrula` (yerel tam) ve GitHub `main` koşusu (`d7fdd75b`, 3.11 + 3.12): sonuçlar
  `docs/durum/2026-11-08_1700_D-71.md`'de.

## 0 · Etiket (Lokman Mac'ten; canlıyı değiştirmez)

Bu oturum yalnız iş dalına push edebilir; etiket push'u vekilde 403 ile durdu (8 Kasım 17:00 UTC). Açıklamalı etiketi Lokman Mac'teki
klondan açar (9 Ekim ve 15 Ekim'deki gibi). Etiket `main`'in `d7fdd75b` commit'inde; GitHub `main` koşusu 42499574736 (3.11 + 3.12)
o commit'te yeşil (16:53 UTC).

```
cd ~/Desktop/"Claude Portman Çalışması"
[ -d 30_IE06/depo/.git ] || gh repo clone lokmansayim/portman-v2private 30_IE06/depo
git -C 30_IE06/depo fetch -q origin --tags
git -C 30_IE06/depo tag -a v2026.11.08 d7fdd75b078873707e0c9659c4b91808b0659847 -m "Kontrollü canlı geçiş (D-71; Lokman 8 Kasım 16:25 kartı)" -m "v2026.10.16'dan bu yana main'e giren 117 PR (#25…#142); göç 009, 010, 011 (yalnız ekler); yeni özellikler kapalı. Ayrıntı: docs/notlar/2026-11-08_D-71_canliya_gecis.md"
git -C 30_IE06/depo push -q origin v2026.11.08
git -C 30_IE06/depo ls-remote --tags origin v2026.11.08
```

Beklenen son satır: `<nesne>	refs/tags/v2026.11.08` (ve `^{}` satırı). Ön bakışın `[2/6]` adımı etiketi sunucudan da denetler.

## 1 · Tatbikat (satır 13: Kapı 10 yedekten geri yükleme, Kapı 12 sürüm geri dönüşü)

27 Ekim'deki tatbikatın aynısı, bu gecenin yedeğiyle (`docs/notlar/2026-10-27_Kapi10_12_tatbikat.md`). Sunucudaki kopyalar koşulur;
yeni kod gerekmez. Çıktı dosyalarının adı tarihlidir; 27 Ekim'in dosyalarının üstüne yazılmaz.

```
cd ~/Desktop/"Claude Portman Çalışması"
Y="$(ls -t ~/Downloads/portman-*.tar.age | head -1)"; echo "$Y"
age -d -i ~/.config/portman/yedek.key "$Y" | tar -xOf - portman.dump | ssh portman-vps 'umask 077; cat > /root/portman_geri.dump'
ssh -n portman-vps 'timeout 300 bash /opt/portman/guncel/vps/yedek_geri_dene.sh /root/portman_geri.dump' > tatbikat_kapi10_1108.txt 2>&1
ssh -n portman-vps 'rm -f /root/portman_geri.dump'
ssh -n portman-vps "setsid nohup bash -c 'bash /opt/portman/guncel/vps/kapi12_tatbikat.sh v2026.10.16; echo == çıkış \$?' > /root/kapi12_v2026.10.16_1108.txt 2>&1 < /dev/null &"
# üç dakika sonra:
ssh -n portman-vps 'cat /root/kapi12_v2026.10.16_1108.txt' > tatbikat_kapi12_1108.txt 2>&1
```

Beklenen: 27 Ekim notundaki "Beklenen" satırları (Kapı 10: her tablo `AYNI`, `satır sayısı farkı olan tablo: 0`, `dump şema sürümü: 8
· canlı: 8`, `canlıya dokunulmadı`; Kapı 12: `ön kontrol: açık iş 0 · bekleyen giden 0 …`, `[1/2] geri: v2026.10.16 → v2026.10.15`,
`[2/2] ileri …`, `== bitti: v2026.10.16 etkin · onceki v2026.10.15`, `== çıkış 0`).

## 2 · Ön bakış ve kurulum (satır 119)

**2a · Ön bakış (salt okunur; `vps/kurulum_on_bakis.sh`, sunucuda kopyası yok, commit'e sabit adresten `bash -s` ile; Lokman'a giden
sürümde tatbikatın ikinci bloğuyla birlikte koşulur):**

```
cd ~/Desktop/"Claude Portman Çalışması"
curl -fsSL https://raw.githubusercontent.com/lokmansayim/portman-v2private/6fa9cbcb069d8176b0780d6935a8dc92c115ab96/vps/kurulum_on_bakis.sh | ssh portman-vps 'timeout 120 bash -s -- v2026.11.08' > kurulum_on_bakis.txt 2>&1
```

Beklenen: `guncel: v2026.10.16 · onceki: v2026.10.15`; `disk … boş … MB` (en az 2048); `var: v2026.11.08 → d7fdd75b0788 (açıklamalı)`;
`açık iş 0 · bekleyen giden 0 · şema 8`; `kararı bekleyen mühendis kontrolü: N (24 saati geçmiş: M)`; dört yeni özellik `ayarda yok →
kapalı`, `yeni özelliklerin hepsi kapalı`; `öz-test sonucu var … LLM çağrısı yok`; son satır `== sonuç: KURULABİLİR`. `BEKLE` ya da
`DİKKAT` satırı varsa kurulum koşulmaz, önce asistan okur.

**2b · Kurulum (canlı değişiklik; `setsid`, `timeout` yok: yarıda kesilirse `guncelle.sh`'in geri dönüşü koşmaz):**

```
ssh -n portman-vps "setsid nohup bash -c 'bash /opt/portman/guncel/vps/guncelle.sh v2026.11.08; echo == çıkış \$?' > /root/guncelle_v2026.11.08.txt 2>&1 < /dev/null &"
# beş dakika sonra; son satır "== çıkış …" değilse bir dakika sonra yineleyin:
ssh -n portman-vps 'cat /root/guncelle_v2026.11.08.txt' > kurulum_v2026.11.08.txt 2>&1
ssh -n portman-vps 'bash /opt/portman/guncel/vps/ayar.sh' > ayarlar_v2026.11.08.txt 2>&1
```

Beklenen (`kurulum_v2026.11.08.txt`): `etiket v2026.11.08 → d7fdd75b0788 · main üzerinde · 2026-11-08 Kontrollü canlı geçiş (D-71; …)`; `dosyalar açıldı (737 dosya; .git yok)`;
`içe aktarma tamam: python 3.12…`; `perspektif: …` ve `genel motor: AYNI (…)` (ikisi bilgi amaçlı); `uygulanan göçler: [9, 10, 11]`;
`guncel → /opt/portman/surumler/v2026.11.08 · onceki → /opt/portman/surumler/v2026.10.16`; `sağlık: sürüm v2026.11.08, Postgres
bağlı`; `yayın: /opt/portman/data/yayin/3d hazır (755; data 751…)`; `nginx: uygulandı (… nginx -t tamam, yeniden yüklendi) · yedek:
…portman.conf.onceki-…`; `durum.sh` çıktısı (servisler `active`, şema 11); `== bitti: v2026.11.08 etkin`; `== çıkış 0`. Servisler bir
kez birkaç saniye durur. Sağlık 60 sn içinde gelmezse betik kendiliğinden `v2026.10.16`'ya döner ve `DUR:` yazar.

**Geri dönüş (sorun çıkarsa, Lokman'ın kararıyla):** `ssh -n portman-vps 'timeout 120 bash /opt/portman/guncel/vps/geri_don.sh' >
geri_don.txt 2>&1` → `v2026.11.08 → v2026.10.16`. Göçler geri alınmaz (gerekmez); veritabanı yedekle ezilmez; nginx'in `/3d/` yolu kalır
(sayfa yoksa 404).

## Kurulumla ne değişir

**Ayarı kapalı gelen (her biri ayrı onayla açılır; satır 3'te):** çizim ve PDF ile talep `gorsel_okuma` (İE-20, satır 83), talep ve
revizyon formu `talep_formu` (İE-20, satır 110; Meta'da iki formun kimliği gerekir), WhatsApp'tan bayi kaydı `bayi_kaydi` (İE-22, satır
111), banka modelinde oda büyütme `banka_germe` (İE-23), bayiye 3D bağlantısı `ucb_taban_url` boş (İE-21, satır 80; `ucb_ac.sh`).
Var olan ayarlar (`enabled`, `dry_run`, `mesaj_katmani`, `plan_uretimi`, `llm_once_revizyon`, model) kurulumla değişmez.

**Ayarsız gelen (`main`'de Lokman'ın onayıyla birleşmiş işler; kurulumla hemen çalışır):**
- Prefabrik ön onay çizimi TK-02 r09 düzeninde (M-02; D-29, D-30, D-31, D-34) ve bayi görseli; Motor'un prefabrik kuralları (BK-12…BK-26:
  verandalar, "+" birleşim, girintili gövde, çatılar, lento 80, 125,5'i aşan açıklıksız pano denetimi D-69).
- Kural kitabı ve yükleme listesi (D-39 kart modeli, omega mühürleri M-01, M-03, M-04, trapez 100 M-11); liste bayiye gitmez.
- Çatı seçenek adımı: talepte çatı yoksa plan seçilince "Çatı seçin" (İE-25, M-08).
- 24 saat kuralı (BK-10, D-19): mühendis 24 saatte karar vermezse kontrol kapanır, Patron'a tek bildirim; bayinin açık işi bayinin son
  mesajından 24 saat sonra kapanır (bayiye kapanış mesajı gitmez); plan değişince mühendis kontrolü düşer.
- Her planda 3D sayfası kayıtta üretilir (bağlantı gitmez); nginx `/3d/<anahtar>/` yolu eklenir (sayfa yoksa 404).
- Banka ve genel motor işleri (İE-09, İE-15, İE-17, İE-23 PR-1, İE-24; D-33 müşteri adı çıktılarda).

## 3 · Özellikleri açma (kurulumdan sonra; her biri Lokman'ın ayrı onayıyla, komut o gün verilir)

| Satır | Özellik | Önce | Açma |
|---|---|---|---|
| 80 | Bayiye 3D sayfası | — | `ucb_ac.sh` (örnek adres yazar; `kapat` geri alır); ücretli uçtan uca deneme ayrı onay |
| 83 | Çizim ve PDF ile talep | TK-01 bayi çiziminin gerçek okuma denemesi (1 ücretli çağrı) | `ayar.sh gorsel_okuma '{"acik": true}'` |
| 110 | Talep ve revizyon formu | Meta'da iki formun taslak kipinde kurulması (Lokman'ın telefonu) | `ayar.sh talep_formu '{…kimlikler…}'` |
| 111 | WhatsApp'tan bayi kaydı | `sablon_bayi_karsilama` ayarda mı | `ayar.sh bayi_kaydi '{"acik": true}'` |

## Sonuç

Lokman komutları 9 Kasım 2026'da Mac'inden koştu (saatler İstanbul, +03). Çıktılar PF `Canliya_Gecis/ciktilar_2026-11-09/`'da.

**0 · Etiket (12:24):** `v2026.11.08` açıklamalı, `d7fdd75b`; konu "Kontrollü canlı geçiş (D-71; Lokman 8 Kasım 16:25 kartı)".
GitHub'da `refs/tags/v2026.11.08` → `657e647d` (etiket nesnesi) → `d7fdd75b`.

**1 · Tatbikat (satır 13):**
- Kapı 10 (12:25:33; `tatbikat_kapi10_1108.txt`): 18 tablonun 18'i canlıyla `AYNI`, `satır sayısı farkı olan tablo: 0`,
  `dump şema sürümü: 8 · canlı: 8`, deneme veritabanı silindi, `canlıya dokunulmadı`. Beklenenle aynı.
- Kapı 12 (12:25:39–12:25:50; `tatbikat_kapi12_1108.txt`): `ön kontrol: açık iş 0 · bekleyen giden 0 (şablon 0) · sağlık HTTP 200`;
  `v2026.10.16 → v2026.10.15` (sağlık geldi) → `v2026.10.16` (`sürüm zaten kurulu`, `uygulanan göçler: yok (güncel)`, sağlık geldi);
  nabız zamanlayıcısı tatbikatta durdu, sonunda başladı; `== çıkış 0`. Beklenenle aynı.

**2a · Ön bakış (12:26:40; `kurulum_on_bakis.txt`):** `== sonuç: KURULABİLİR (hiçbir şey değişmedi)`. Disk 170.452 MB boş; etiket
`var: v2026.11.08 → d7fdd75b0788 (açıklamalı)`; `açık iş 0 · bekleyen giden 0 · şema 8`; mühendis kontrolü 0 (24 saati geçmiş 0), fiyat
hatırlatması 0, onay bekleyen revizyon 7 (bayi yeniden yazınca kapanır, mesaj gitmez); dört yeni özellik `ayarda yok → kapalı`, 3D adresi
boş; plan üretimi (İE-14) canlıda açık (`v2026.10.16`'da da açıktı; kurulum ayarı değiştirmez); öz-test sonucu var, LLM çağrısı yok; son
yedek 8 saat önce.

**2b · Kurulum (satır 119; 12:30:39–12:32:19; `kurulum_v2026.11.08.txt`):** `== bitti: v2026.11.08 etkin`, `== çıkış 0`.
- `dosyalar açıldı (737 dosya; .git yok)`; `içe aktarma tamam: python 3.12.3 · numpy 2.5.4 …`; perspektif `TAMAM`; genel motor `AYNI
  (… liste 93 satır, pdf var; 18.4 s)`; `uygulanan göçler: [9, 10, 11]`; `guncel → …/v2026.11.08 · onceki → …/v2026.10.16`;
  `sağlık: sürüm v2026.11.08, Postgres bağlı`.
- `yayın: /opt/portman/data/yayin/3d hazır (755; data 751) · başkasına açıktı, kapatıldı: nabiz · sahibi portman değil, dokunulmadı:
  settings.json`. İkincisi tasarım gereği: `settings.json`'u root `ayar.sh` ile yazar, sır içermez; `nginx_uygula.sh` sahibi portman
  olmayan girdinin yalnız adını yazar (servis okuyamaz olmasın).
- `nginx: uygulandı (80+443; /panel/ 12m; nginx -t tamam, yeniden yüklendi) · yedek: …/portman.conf.onceki-20261109123218`.
- Durum: 9 servisin 9'u `active` (nabız zamanlayıcısı dahil); sağlık HTTP 200, `sorunlar: []`; şema 11; açık iş 0, bekleyen giden 0.
- Etiket satırındaki tarih `2026-11-09` (etiketin açıldığı gün); beklenen satırda `2026-11-08` yazıyordu. Fark yalnız tarihte.

**Ayarlar (`ayarlar_v2026.11.08.txt`; `ayar.sh` birleşik görünümü, `kanal/ayarlar.py` › VARSAYILAN ile):** `enabled: true`,
`dry_run: false`, `mesaj_katmani: true`, `ucb_taban_url: null`; `banka_germe`, `gorsel_okuma`, `talep_formu`, `bayi_kaydi` dördü
`acik: false` (dosyada yok, varsayılandan); `plan_uretimi.acik: true`, `llm_once_revizyon.acik: false`. Beklenenle aynı.

**Bulgu · kurulum iki kez başladı.** `guncelle.sh v2026.11.08` iki kez başlatıldı; iki süreç aynı çıktı dosyasına yazdı.
- 12:30:39'da başlayan ikinci koşu, birincinin kurmakta olduğu `surumler/v2026.11.08`'i (henüz `KURULDU` yok) "yarım kalmış" sayıp
  `surumler/.yarim-v2026.11.08-20261109…` adıyla kenara aldı (silmedi) ve kurulumu baştan sona yaptı.
- Birinci koşunun pip'i klasörü kaybedince `ERROR: Could not install packages due to an OSError` ile düştü; `dur()` yalnız çıkar:
  bağlantı, servis, göç ve nginx adımlarına gelmedi.
- Çıktı dosyasındaki bozuk satır budur: birinci koşunun hata yazısı ikinci koşunun aynı satırının son 20 baytının (zaman damgasının
  sonu, ` (silinmedi)` ve satır sonu) üstüne düştü; görünen parça `ERROR: Could not ins` (20 bayt); birinci koşunun kalan satırlarını ikinci koşu sonradan ezdi.
- Etkisi yok: ikinci koşunun bütün kapıları geçti, sağlık yeni sürümde. Sunucuda `.yarim-…` klasörü duruyor (gizli; sürüm sayısına
  girmez); silinmesi Lokman'ın onayıyla.
- `guncelle.sh`'te ikinci koşuyu durduran kilit yok. Öneri (ayrı iş, Lokman'ın onayıyla): `flock` ile tek koşu; ikinci koşu "kurulum
  sürüyor" deyip çıkar.

**Durum:** Canlı `v2026.11.08` (9 Kasım 12:32). Kurulumun kabulü Lokman'da. Sıradaki: satır 80, 83, 110, 111, her biri ayrı onayla
(yukarıdaki "3 · Özellikleri açma").
