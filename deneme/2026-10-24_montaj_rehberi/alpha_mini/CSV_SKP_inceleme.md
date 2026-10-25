# Alpha Mini · Frame Builder CSV ve SKP incelemesi · 25 Ekim 2026

Deneme; canlıda değil, iş emri yok. Devir: `docs/devir/2026-10-24_Alpha_Mini_Devri.md` › 25 Ekim eki.

**Girdi (Lokman, 25 Ekim).** 62 m²'lik bir projenin DVR1 duvar paneli için üç dosya:
- CSV: SketchUp eklentisi MRD Frame Builder'ın üretim çıktısı;
- SKP: aynı panelin SketchUp dosyası;
- ekran görüntüsü.

**Depoya giren (maskeli).**
- `kaynak/DVR1_duvar.csv`: CSV'nin kopyası. Yalnız FRAMESET satırındaki proje adı `PROJE_62M2` yapıldı, öteki satırlar bayt bayt aynı.
- `kaynak/DVR1_fbd.json`: SKP'deki eklenti verisinin kısa dökümü. Kişi adı taşıyan alan (`user_profile`) yazılmadı.
- SKP'nin kendisi depoya girmedi: dosya adında bayi adı, içinde kişi adı var.

## 1. CSV biçimi

Howick biçiminde, düz metin, satır başına bir çubuk:

`COMPONENT, ad, LABEL_NRM|LABEL_INV, adet, boy, C, gövde, flanş, kalınlık, sınıf, x1, y1, x2, y2, (İŞLEM, konum)…`

- **Başlık satırları:**
  - `UNIT,MILLIMETRE`;
  - `VERSION,2`;
  - `PROFILE,54.00x80.00`;
  - `FRAMESET,<panel>,<proje>`.
- **Koordinatlar.** x1..y2 çubuğun **ekseni**dir (orta çizgi; panel düzleminde mm). Konumlar (x1, y1) ucundan ölçülür.
- **İşlemler, adlarıyla:**

  | İşlem | Türkçe | Adet |
  |---|---|---|
  | DIMPLE | vida deliği | 76 |
  | LIP_CUT | dudak kesme | 38 |
  | SWAGE | ezme | 38 |
  | NOTCH | kertme | 4 |
  | SERVICE_HOLE | servis deliği | 12 |
  | CUT | boy kesimi | 21 |

- **Profil:** `80S54-12`, yani gövde 80, flanş 54, 1,2 mm, G550. Düzlem içinde görünen genişlik flanştır (54).
- **Takım ayarı:** `UNBAK U1 2000m Tooling`. Alpha Mini 0,8'in makas profili `80-45-10-0,8`; bu CSV başka profil, büyük olasılıkla başka hat.

## 2. SKP

- **İçerik.** SketchUp 2024. Tek panel var (DVR1, 21 çubuk) ve bir açıklık grubu:
  - pencere 1800 × 1800, eşik ekseni 173, lento altı 2000;
  - lentonun içi Warren kafes.
- **Çubuk verisi.** Eklenti her çubuğa türünü (`code`), eksenini ve hesapladığı işlemleri yazmış:

  | SKP alanı | CSV karşılığı |
  |---|---|
  | `flangeholes` | DIMPLE |
  | `lip_cuts` | LIP_CUT |
  | `swages` | SWAGE |
  | `notches` | NOTCH |
  | `service_holes` | SERVICE_HOLE |
  | `flip_x` doğru / yanlış | LABEL_NRM / LABEL_INV |

- **SKP = CSV.** 168/168 işlem (±0,005 mm), 21/21 etiket. CSV, SKP'nin dışa aktarımıdır.
- **Panel ayarı:**
  - dikme aralığı 600, kuşak 1200;
  - servis deliği yükseklikleri `610|1830`;
  - uç boşluğu 5;
  - vida deliği yeri 27, dudak 10;
  - takım genişlikleri: dudak kesme 46, kertme 48, ezme 55, servis deliği Ø12.
- **Elle yapılmış düzenlemeler.** Kör testte girdi sayılmalı:
  - 1827'deki ara dikme silinmiş, simetri için 1883'e konmuş (2510 − 627);
  - dört servis deliği elle eklenmiş: iki kuşağın ortası 172, üst başlıkta 177 ve 2333.
- **Ölçü notu.** Pencere nesnesi 354–2154 arasında çizilmiş. Sağ pencere dikmesi ise simetrik 2183'te. Bu yüzden çerçeve açıklığı 1802, sağ pay 354. Ekran görüntüsündeki 356 pencere nesnesinin ölçüsüdür.

## 3. İşlemler geometriden türetilebiliyor mu (DVR1)

`duvar_kural.py`, CSV'nin işlem listelerine bakmadan şu girdilerle işlemleri üretir:
- çubuk eksenleri ve türleri;
- servis deliği yükseklikleri;
- elle eklenen dört servis deliği.

Sonra CSV ile kıyaslar.

**Sonuç: 168/168 işlem ±0,1 mm içinde (en büyük sapma 0,05 mm), 21/21 etiket.**

**Kurallar:**
- **Alan ve giren çubuk.** Kesişen her çubuk çiftinde biri "alan" (kanalı açık), öteki "giren"dir. Öncelik sırası:
  1. alt ve üst başlık (plaka);
  2. eşik ve lento;
  3. dikme;
  4. kuşak ve lento çaprazı.
- **DIMPLE:** iki eksenin kesişimine, iki çubuğa da.
- **LIP_CUT** (alan çubuğa):
  - giren çubuğun ekseninin, alanın giren tarafındaki kenarını kestiği yere. Açılı çaprazda bu, eksen kesişiminden 27·cot(açı) kadar kaydırır (9,23 mm);
  - uca en az 31 mm.
- **SWAGE** (giren çubuğa): kesişim uca 54'ten yakınsa uçtan 34; değilse kesişimin kendisine (eşik ve lento, pencere dikmesini ortasından sarar).
- **NOTCH:** eşik ve lentonun uç kesişiminde, uçtan 25.
- **SERVICE_HOLE:** tam boy dikmede döşemeden 610 ve 1830; artı elle eklenenler.
- **Etiket:**
  - alan çubuk girene doğru açılır;
  - hiçbir şey almayan çubuk aşağı açılır, dikeyse +x yönüne;
  - açık yüz çubuk yönünün solundaysa NRM, sağındaysa INV.

**Sınır.** Kurallar bu tek panelden çıkarıldı; bu bir kör test değildir. İkinci bir panelin CSV + SKP'siyle sınanmalıdır. Çerçeve geometrisi (dikme yerleri, boylar, lento çaprazları) da girdi alındı; onu üretmek ayrı iş.

**Biçim.** `--yaz` üretilen işlemleri aynı biçimde CSV'ye yazar. Geri okununca işlemler, boylar ve etiketler aynı çıkar. Yalnız bir tür içindeki işlemlerin sırası eklentininkinden farklıdır; makinenin sıraya bakıp bakmadığı bilinmiyor.

## 4. .bde harfleri: hipotez ve sınama

| Harf | Karşılığı (hipotez) | Kanıt |
|---|---|---|
| **h** | DIMPLE (vida deliği) | Her iki dosyada her giren çubukta tam 2 h var (168/168, 176/176). Başlık ucunda 27 mm; CSV'de plaka ucunda da 27. |
| **f** | LIP_CUT (dudak kesme) | Yalnız başlıklarda (alan çubuk). BDE-58'de 42 başlık ucunun 42'sinde 31 mm; CSV'de plaka ucunda da 31. |
| **w** | SWAGE (ezme) | Yalnız giren çubukta. BDE-58'de 168/168 çubukta iki uçta 25 ± 1 mm. CSV'de bu değer 34; profile ve takıma bağlı sabit. |
| n | NOTCH (kertme)? | Makasta boş, CSV'de var. Yalnız ad benzerliği. |
| s | SERVICE_HOLE (servis deliği)? | Makasta boş, CSV'de var. Yalnız ad benzerliği. |
| l | bilinmiyor | — |

- **Altıncı istasyon.** Lokman'ın listesinde olmayan istasyon büyük olasılıkla **dudak kesme** (LIP_CUT). Liste: kesme, kertme, düzleme, vida, servis deliği.
- **BDE-144 farklı ayarla üretilmiş.**
  - f her çaprazda h'nin yanında birer tane; üst başlığın tepe ucunda yok.
  - w uçtan 20–33 mm arasında değişiyor.
  - Geometri kuralı aynı (PR 88, SL 172), takım kuralı farklı. Ya ayar ya yazılım sürümü değişmiş.
  - Kör testte Alpha Mini'nin bugünkü ayarının hangisi olduğu bilinmeli.
- **Koordinat farkı.** .bde'de koordinatlar eksen değil, çubuğun gövde (sırt) çizgisi gibi görünüyor:
  - SL x = 300'de, alt başlıktaki vida deliği x = 273'te;
  - SL'nin boyu 172, 45'lik flanşla tutuyor; 54'lükle 169 olurdu.

## 5. Açık sorular

1. Bu CSV hangi makineye gidiyor (UNBAK U1 mi)? Alpha Mini CSV okuyor mu? Okuyorsa Portman doğrudan bu biçimi üretebilir.
2. Yazılımcıya:
   - h = DIMPLE, f = LIP_CUT, w = SWAGE, n = NOTCH, s = SERVICE_HOLE doğru mu?
   - l nedir?
   - BDE-58 ve BDE-144 farklı ayarla mı üretildi?
3. İkinci bir panelin CSV + SKP'si (kör test).

## Kanıt (25 Ekim 2026, `deneme/2026-10-24_montaj_rehberi/alpha_mini/` içinde)

```
$ python3 csv_oku.py <yüklenen DVR1.csv> --maskele kaynak/DVR1_duvar.csv
21 parça · toplam boy 23964.9 mm · işlem DIMPLE:76 LIP_CUT:38 CUT:21 SWAGE:38 SERVICE_HOLE:12 NOTCH:4

$ python3 fbd_oku.py <yüklenen .skp> --csv kaynak/DVR1_duvar.csv --json kaynak/DVR1_fbd.json   # openskp 1.3.0
DVR1: 21 çubuk (21 CSV ile eşleşti) · açıklık 1 · stil 80S54-12 · takım ayarı UNBAK U1 2000m Tooling

$ python3 duvar_kural.py kaynak/DVR1_duvar.csv kaynak/DVR1_fbd.json
SKP = CSV (±0,005 mm): işlem 168/168, flip_x ↔ LABEL_NRM 21/21
  TOPLAM 168/168 işlem · en büyük sapma 0.050 mm · etiket 21/21 · elle eklenen servis deliği (girdi) 4

$ python3 bde_rol.py kaynak/BDE-58_cati_makas.bde kaynak/BDE-144_cati_makas.bde
BDE-58:  başlık h:350 f:560 w:0 · giren h:336 f:0 w:378 · giren 168, tam iki h 168, iki ucunda 25±1 w 168 · başlık ucu f: {31: 42}
BDE-144: başlık h:368 f:352 w:0 · giren h:352 f:0 w:352 · giren 176, tam iki h 176, iki ucunda 25±1 w 0 · başlık ucu f: {9: 16, 281: 16, 22: 8}

$ python ciz_duvar.py kaynak/DVR1_duvar.csv gor/DVR1_islemler.png      # proje ortamı (matplotlib)

$ python3 testler/referans/dogrula.py --hizli      # depo kökünde; deneme dışında değişiklik yok
SONUÇ: referansla aynı   (çıkış 0)
```
