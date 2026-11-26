# Devir · Alpha Mini imalat çıktısı (.bde) · 24 Ekim 2026

> **Karar (Lokman, 25 Ekim 2026): hedef biçim .bde değil, CSV.** Roll-form makineleri Meosis programı üzerinden CSV ile üretim yapıyor. CSV'yi bugün SketchUp eklentisi MRD Frame Builder çıkarıyor.
> - .bde'yi çözmeye gerek yok.
> - Portman bu CSV'yi kendisi üretecek. Kör test Frame Builder'ın gerçek CSV'siyle yapılır.
> - Aşağıdaki .bde bölümleri yalnız kayıt ve makas geometrisi için duruyor.
>
> Ayrıntı: `deneme/2026-10-25_alpha_mini_csv/CSV_SKP_inceleme.md` › §5.


Dosyalar: `deneme/2026-10-25_alpha_mini_csv/` (26 Kasım 2026'da `main`'e taşındı; önceki yeri `claude/montaj-rehberi-devir` ve `claude/optimistic-planck-0490xu` dallarında `deneme/2026-10-24_montaj_rehberi/alpha_mini/`). Deneme; canlıda değil, iş emri yok.

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

## 25 Ekim eki: Frame Builder CSV ve SKP

Ayrıntı ve kanıt: `deneme/2026-10-25_alpha_mini_csv/CSV_SKP_inceleme.md`.

- **Gelen.** Lokman 62 m²'lik bir projenin DVR1 duvar panelini gönderdi. Depoya maskeli girdi:
  - `kaynak/DVR1_duvar.csv`: MRD Frame Builder CSV'si, Howick biçimi;
  - `kaynak/DVR1_fbd.json`: SKP'deki eklenti verisinin dökümü.
- **CSV işlemleri adlarıyla yazıyor:** DIMPLE (vida deliği), LIP_CUT (düzleme), SWAGE (köşeleme), NOTCH (kertme), SERVICE_HOLE (servis deliği), CUT (kesim). SKP'nin kendi işlem listesiyle 168/168 aynı; CSV, SKP'nin dışa aktarımı.
- **Duvar kuralları çıkarıldı.** `duvar_kural.py` işlemleri yalnız geometriden ve beş sabitten (31, 34, 25, 610|1830, W 54) üretiyor:
  - 168/168 işlem ±0,1 mm, 21/21 etiket;
  - kurallar aynı panelden çıktı, kör test değil; ikinci panel gerekli.
- **.bde harfleri (hipotez):**
  - h = DIMPLE, f = LIP_CUT, w = SWAGE;
  - BDE-58'de sayıyla tutuyor: f başlık ucunda 31 (42/42), w giren çubukta iki uçta 25 (168/168), her giren çubukta 2 h;
  - n, s büyük olasılıkla NOTCH ve SERVICE_HOLE; l bilinmiyor;
  - "altıncı istasyon" büyük olasılıkla köşeleme (SWAGE; terimler 26 Kasım'da BK-76'ya göre düzeltildi: LIP_CUT düzleme).
- **BDE-144 başka takım ayarıyla üretilmiş.** f her çaprazda bir, w uçtan 20–33. Kör test için Alpha Mini'nin bugünkü ayarı sorulmalı.
- **CSV'nin profili 80S54-12 (1,2 mm), takım ayarı "UNBAK U1".** Alpha Mini 0,8'in makas profilinden farklı. Hangi makineye gittiği ve Alpha Mini'nin CSV okuyup okumadığı soruldu.
- **Sıra (karardan sonra).**
  1. Lokman'dan Frame Builder'ın bir çatı makası CSV + SKP'si; ilk hedef makas.
  2. Makas işlem kuralları çıkarılır; `duvar_kural.py`'nin makas karşılığı yazılır.
  3. İkinci bir duvar paneliyle duvar kuralları kör sınanır.
  4. İE-16 "Alpha Mini CSV çıktısı" planı: Plan modu, Lokman'ın onayı. Kabul koşulu: Frame Builder CSV'siyle kör test (çubuk sayısı, boylar ±1 mm, işlem türleri ve konumları ±1 mm, etiket).
  - Yazılımcıya harf tablosu sorusu düştü.

## 26 Kasım eki: `main`'e taşındı

- **Neden:** Portman Project'in oturumları bu bulguları bulamadı. Bulgular yalnız birleşmemiş dallardaydı. Lokman PR'ı istedi (26 Kasım 2026).
- **Taşınanlar:** `deneme/2026-10-25_alpha_mini_csv/`:
  - kural motoru `duvar_kural.py`;
  - okuyucular `csv_oku.py`, `fbd_oku.py`, `bde_oku.py`;
  - `bde_rol.py`, `ciz_duvar.py`;
  - not `CSV_SKP_inceleme.md`, kaynak dosyalar, görsel.
  - Montaj rehberinin denemeleri taşınmadı; rehber yapılmayacak (D-142).
- **BK-76 ile ilişki:**
  - `main`'deki `araclar/uretim/` .bde ve MRD CSV'yi okur ve bayt bayt geri yazar; işlem üretmez.
  - Bu klasördeki kural motoru işlemleri geometriden üretir.
  - İkisi birleşince Portman CSV'yi kendisi yazar.
- **Terimler BK-76'ya göre:** DIMPLE vida deliği, SWAGE köşeleme, NOTCH kertme, LIP_CUT düzleme. 25 Ekim notlarındaki "ezme" ve "dudak kesme" buna çevrildi.
- **Kör test (Lokman'ın 26 Kasım görseli):**
  - Kubbe üretim dosyalarında kural dosyaları görmeden duvarda 139/139, makasta (KMK14) 161/163 tuttu. Makastaki 2 fazla işlem mahya düğümünde.
  - Görseli üreten kod depoda değil; bu oturum o sınamayı koşmadı.
- **Sıradaki:**
  - Makas CSV üreteci ayrı bir oturumda, iş emriyle (Plan modu, Lokman'ın onayı).
  - Kabul: MRD CSV'siyle kör test.
  - Kubbe makasındaki 2 fazla işlem ilk bulgu.
