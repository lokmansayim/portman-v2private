# Devir · Render'lı montaj rehberinin VPS'te herkese açık yayını · 24 Ekim 2026

Dal: `claude/montaj-rehberi-devir`. Girdi: `deneme/2026-10-24_montaj_rehberi/rehber/` ve `render/gorsel/`. Render devri bitince son görseller oradan alınır.

## Amaç

Montaj rehberini, render görselleriyle birlikte, Lokman'ın kendi VPS'inde herkese açık bir adreste yayınlamak. Bayiler ve müşteriler linkle açar; giriş yok.

## Bağımlılık

Render oturumunun çıktısı: son görünümler ve rehbere eklenmiş galeri. Hazır değilse mevcut sürümle (artefakt sürüm 8) ve köşe render'ıyla başlanabilir.

## Kurallar (AGENTS.md; bu işte doğrudan geçerli)

- **Onay.** Sunucu ya da canlı değişiklik ve yeni veri paylaşımı için **Lokman'ın ayrı açık onayı** gerekir. Herkese açık yayın ikisini de içerir.
- **VPS erişimi.** VPS'e asistan bağlanmaz. Betik hazırlanır, Lokman Mac'inden koşar, çıktı dosyaya yazılır ve okunur.
  - Sunucuda kopyası olan betik: `ssh -n portman-vps 'timeout 120 bash …' > çıktı.txt 2>&1`.
  - Geçici betik: `ssh portman-vps 'timeout 300 bash -s' < betik > çıktı.txt 2>&1`.
  - Bir dakikadan uzun iş: `setsid` ile.
- **Hosting.** Hosting'e yalnız DirectAdmin üzerinden girilir. Yayın hosting'e konacaksa dosyayı Lokman DirectAdmin'den yükler.
- **KVKK (herkese açık sayfa).**
  - Kişi ve bayi adı yok. Başlık `uret.py --proje` ile: kod (PK-01) ya da Lokman'ın seçeceği bir model adı. Gerçek proje adı kullanılmaz.
  - Telefon yok. Sır yok.
- **İç notlar temizlenir.** Ör. "Lokman'ın teyidinde", "paftada yok, teyit bekliyor", kaynak dosya ve tedarikçi adları, `.bde ile teyit` gibi geliştirme notları. Bunların yerine müşteriye dönük kısa metinler konur; Lokman onaylar.
- **Ücret.** Statik yayın; LLM ve WhatsApp maliyeti yok.

## Teknik durum

- **Sayfa.** Tek dosya HTML (~90 KB, veri gömülü).
  - Three.js 0.160.0 ve OrbitControls jsdelivr CDN'den importmap ile geliyor; yazı tipleri Google Fonts'tan.
  - Herkese açık yayında öneri: `three.module.js` ve `OrbitControls.js` aynı klasöre konur, importmap yerel yola çevrilir. Böylece dış bağımlılık kalmaz, sürüm sabit olur.
- **Görseller.** Render PNG'leri (1–2 MB) WebP ya da JPEG'e küçültülür, ör. 1600 px ve 200–400 KB.
- **Sunucu tarafı bilinmiyor.** Önce depodaki `vps/` betikleri ve `hosting/` kayıt kopyası okunur:
  - hangi web sunucusu ve alan adı kullanılıyor;
  - TLS nasıl sağlanıyor;
  - canlı Portman servisi hangi portta.
- **Yayın canlı servisle çakışmamalı.** Seçenekler:
  - ayrı alt yol ya da alt alan adı (ör. `rehber.<alan>`);
  - salt okunur statik klasör, dizin listesi kapalı;
  - güvenlik başlıkları;
  - gerekirse `noindex` (Lokman karar verir).
- **Alternatif.** claude.ai artefaktı Paylaş menüsünden herkese açık link olarak da paylaşılabilir. Lokman kendi VPS'ini istedi; bu seçenek yalnız bilgi olarak.

## Önerilen adımlar

1. **İş emri ve kararlar.** `/is-emri` ile açılır, ör. "BK-xx Montaj rehberi yayını". Plan modunda; Lokman'ın onayıyla. Kararlar tek soruda sorulur:
   - adres (alt alan adı ya da yol);
   - VPS mi hosting mi;
   - başlıkta kod mu model adı mı.
2. **Yayın paketi.** `deneme/…/yayin/` altında, betikle üretilir:
   - maskeli `index.html`, yerel Three.js, küçültülmüş görseller;
   - `SHA256SUMS`.
3. **Yerel kontrol.** Playwright ile:
   - konsol hatası yok;
   - masaüstü ve telefon genişliğinde ekran görüntüsü;
   - 17 adım açılıyor, parçaya dokununca kart açılıyor;
   - dış istek yok (yerel Three.js).
4. **Sunucu betiği.** `vps/rehber_yayin.sh`:
   - yedek al;
   - klasörü kur ve dosyaları yerleştir;
   - web sunucusu yapılandırmasını ekle, sözdizimini sına, reload et;
   - geri dönüş adımı ve kuru koşu (`--dene`) olsun.
5. **Lokman koşar.** Onaydan sonra betiği Lokman koşar. Çıktı okunur. Doğrulama:
   - `curl -I` (200, başlıklar);
   - sayfanın telefonda açılması (Lokman).
6. **Kapanış.** `DURUM.md` ve devir notu güncellenir; durum kanıtla yazılır ("Canlıda çalışıyor").

## Güncelleme · 24 Ekim 2026 öğleden sonra

**Render işi bitti (kart 103):**
- Rehberde galeri var.
- Görseller `deneme/2026-10-24_montaj_rehberi/rehber/gorsel/*.jpg` (her biri 50–300 KB); sayfa onlara `gorsel/…` göreli yoluyla bağlanıyor.
- Yayın paketi: `uret.py` çıktısı `index.html` olur, yanına `gorsel/` klasörü konur.

**Herkese açık sürümde maskelenecekler (görsel ve metin):**
- Pafta görselindeki "Lokman'ın çizimleri" ibaresi ve kartlardaki "Lokman çizimi", "Lokman, fotoğraflar", "teyit bekliyor" notları.
- `__PROJE__` adı.
- Galeri `GORSELLER` dizisi, şablonda.

## Kapanış · 25–26 Ekim 2026

**Durum: Canlıda çalışıyor** → https://rehber.portatifev.com

**Kararlar (Lokman, 25 Ekim):**
- Adres alt alan adı, VPS'te; başlıkta kod; arama motorlarına kapalı (noindex).
- 26 Ekim 10:11: 62 m² Beşik + Cumba rehberi PK-01'in yerine.

**Sunucu:**
- Betik `vps/rehber_yayin.sh`; tek dosya kurulum `<rehber>/yayin/cikti/rehber_kur.sh`.
- Koşturma, Mac'ten: `ssh portman-vps 'timeout 300 bash -s -- --dene|--uygula|--geri' < rehber_kur.sh > çıktı.txt 2>&1`.
- `portman.conf` ve Portman servisleri değişmez.

**Paketler:**
- PK-01: `deneme/2026-10-24_montaj_rehberi/yayin/` (`paketle.py`, `dene.py`).
- 62 m²: `deneme/2026-10-25_rehber_62m2/yayin/`.
- 62 m² paketi esbuild ile yorumsuz yazılır: `paketle.py --npm <npm pack> --esbuild <yol>`. Gereken npm paketleri: three@0.160.0, @fontsource/barlow-condensed, ibm-plex-mono ve source-sans-3, esbuild@0.23.1.

**Sürümler (sunucuda):**
- `20261025191940`: PK-01, `onceki`.
- `20261026103836`: 62 m², `guncel`.

**Dikkat:**
- İlk `--uygula` DNS denetimindeki `::ffff:` hatasıyla durmuştu; hiçbir şey değişmedi, betik düzeltildi (`5285247`).
- Yeni rehber yayını: aynı paketleyiciyle yeni `rehber_kur.sh`, önce `--dene`, sonra `--uygula`.
