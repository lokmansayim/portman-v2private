# Devir · Alpha Mini imalat çıktısı (.bde) · 24 Ekim 2026

Dal: `claude/montaj-rehberi-devir`. Dosyalar: `deneme/2026-10-24_montaj_rehberi/alpha_mini/`. Deneme; canlıda değil, iş emri yok.

## Amaç

Portman'ın çatı makasını Alpha Mini roll-former'ın okuduğu .bde dosyası olarak kendisi üretmesi. İlk hedef çatı makası. Sonra sırayla duvar paneli, çatı paneli, tavan paneli ve iç duvar paneli.

Ölçüt **kör test**: gerçek bir projenin makasını yalnız geometriden üret, makinenin gerçek .bde'siyle satır satır kıyasla. İlk aday BDE-58'in MK01'i.

## Elimizdekiler

- `kaynak/BDE-58_cati_makas.bde`:
  - 58 m² proje, 7 makas (MK01–MK07), 189 çubuk.
  - Profil dosya adında: `((7...80-45-10-0,8-1))`.
  - Rehber şablonunda "PK-02" diye anılmış; kör test kodlarıyla eşleşmesi teyit edilecek.
- `kaynak/BDE-144_cati_makas.bde`: 144 m² proje, 8 makas, 200 çubuk.
- Özgün dosyalar Lokman'ın Mac'inde:
  - Konum: `Portatifev Toptan › Bayiler › <bayi> › <proje> › Üretim Dosyası › ALPHA MİNİ 0,8 › … ÇATI MAKAS PANELLERİ((N...80-45-10-0,8-1)).bde`.
  - Bulmak için bağlı klasörde: `find … -path '*ALPHA MİNİ*' -name '*.bde'`.
  - Dosya adlarında kişi ve bayi adları var; depoya maskeli adla girer.
- Aynı projenin makas ve dere yerleşim paftası (PDF) aynı proje klasöründe, `Montaj Paftaları` altında.
- SketchUp dosyaları (`örnek skp makaslar claude için` klasörü ve bayi klasörleri):
  - 60 m² proje (makas ve panel yerleşimi);
  - 94 m² çelik proje (`.rar` içinde ve 15 cm'lik SKP).
  - Katmanlar: `LCAD_Truss`, `LCAD_Roof`, `LCAD_Wall`.
  - openskp yalnız 2020+ SKP okur; 2019 dosyası açılmadı.
- `bde_oku.py`: okuyucu; makas başına çubuk ve işlem sayımı verir.

## .bde biçimi (okunan)

- ASCII; satır başına bir çubuk: `MKnn KOD boy_mm h: … f: … n: … s: … l: … w: … x1: a y1: b x2: c y2: d`. Bilimsel gösterim olabilir, ör. `-1.33179e-39`, yani 0.
- **Üye kodları:**
  - PU: alt başlık;
  - PD: üst başlık (iki parça);
  - PR/PL: topuk dikmeleri;
  - SL/SR: duvar hattı dikmeleri;
  - BD/BR/BL: çaprazlar.
- **h f n s l w:** çubuk boyunca işlem konumları (mm). Çatı makaslarında yalnız **h, f, w** dolu; n, s, l hep boş.
  - BDE-58 MK01'de h 98, f 80, w 54 işlem.
  - 6 harf büyük olasılıkla makinenin 6 istasyonu. Lokman'ın bildiği istasyonlar: kesme, kertme, düzleme, vida, servis deliği; altıncısı bilinmiyor.
  - **Harf–istasyon eşleşmesi yazılımcıdan bekleniyor** (Lokman sordu, cevap gelmedi).
- **x1 y1 x2 y2:** çubuğun makas düzlemindeki uçları (mm): x açıklık boyunca, y yükseklik.

## Çıkarılan makas kuralı (iki .bde ve SKP'lerden)

- Eğim %33 (18,26°), topuk 10 cm.
- Duvar hattında dikme, uçtan 30 cm içeride. Mahya dikmesi yok.
- Warren zikzak çaprazlar; alt düğümler eşit aralıklı.
- Profil C 80-45-10, 0,8 mm.
- PK-01'e uygulandı (rehberde):
  - ilk üst düğüm uçtan 45 cm, 10 göz × 57 cm;
  - üst düğümler aşık sıralarıyla çakışıyor (saçaktan 47, sonra 60 cm);
  - tepe 118,9 cm; paftada 118,5.
- PK-01'in kendi .bde'si gelince göz aralığı teyit edilir.

## Açık sorular (Lokman)

1. Yazılımcının cevabı: h, f, w (ve n, s, l) harflerinin istasyonları, konumların başlangıç ucu ve yönü, dosya adındaki `((7...80-45-10-0,8-1))` parametreleri.
2. PK-01'in .bde dosyası.
3. Duvar, çatı paneli, tavan ve iç duvar .bde örnekleri.
4. **Kontrol edilecek:** rehberde makas çubukları düzlem içinde 4,5 cm, düzleme dik 8 cm çizildi. C80'in gövdesi makas düzlemindeyse tersi doğru olabilir. .bde koordinatlarından ve Lokman'dan teyit edilecek.

## Sıradaki adımlar

1. **İş emri.** `/is-emri` ile açılır (Plan modu, Lokman'ın onayı), ör. "İE-16 Alpha Mini makas çıktısı". Kabul koşulu kör testtir.
2. **Tablo ve çizim.** `bde_oku.py --json` ile iki dosya tabloya dökülür. Çubuklar x1..y2'den çizilir, SKP'deki makasla üst üste konur.
3. **İşlem kuralları (cevap gelmeden).** Konumların geometriden türetilip türetilemediği denenir. Hipotezler:
   - h: çubuk kesişimlerindeki vida ya da delik;
   - f: kesişimdeki kertme;
   - w: uç işlemi.
   - Her hipotez iki dosyada sayıyla sınanır.
4. **Üreteç.** Makas geometrisinden .bde satırı üretilir; BDE-58 MK01 ile kıyaslanır: çubuk sayısı, boylar ±1 mm, işlem konumları.
5. **Tekrar.** Aynı yol BDE-144'te tekrarlanır (8 göz). Sonra PK-01.

## Kurallar

- Referans girdiler ve altın testler değişmez.
- Kişi ve bayi adları depoya, commit'e ve çıktıya girmez.
- Ücretli deneme yok.
- İlerleme kullanıcı adımlarıyla yazılır, kanıtla.
