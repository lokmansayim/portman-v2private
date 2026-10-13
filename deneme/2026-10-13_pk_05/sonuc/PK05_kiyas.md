# PK-05 · Abdullah Yavuz 60 m² (Kapaklı) · kendi listemiz ↔ gerçek yükleme listesi (kör test adım 4, pafta kipi)

- **Sıra kanıtı:** kendi listemiz `90bc8e5` (13 Ekim 2026 12:21:54 +03) → Mac'te mühür denetimi 12:21:58 (`561ad34a…a779` aynı) → açılış 12:22:10.
- **Gerçek liste:** `gercek/ABDULLAH_YAVUZ_60M2_YUKLEME_LISTESI.xlsx`, sayfa "PREFABRİK"; şablon **LOFTEV YÜKLEME LİSTESİ**, 60 m², sevkiyat Kapaklı / Pınarca.
  Okunmuş hali `gercek/PK05_gercek.json` (103 satır). Elektrik planı olmadığı halde listede elektrik grubu var (sabit takıma benziyor).
- **Bizim liste:** `PK05_liste.json` / `.xlsx` (üretici sürüm 4, pafta kipi; varsayılan Portatifev).

## Özet

Varsayılan adetle birebir **≈ 25 satır**. Bunlar:
- pano 7 satır;
- köşe, 3'lü H 60, saçak ve baş makas omegası;
- makas 7 (L 6600);
- yeşil alçıpan 2;
- dere takımının 7'si;
- kapılar (çelik SOL, Amerikan 2 SOL + 2 SAĞ);
- pencereler.

Aday sütunu tutanlar:
- 60'lık duvar omegası 15 ("+5"siz);
- omega kapak 11;
- betopan H'ı 3;
- çelik dübel 26;
- çektirme U'su 100 için 5;
- köpük 2.

Elektrik ve sıhhi tesisat bizde "kural yok": listede 16 + 7 satır.

**Tutan geometri:**
- Pafta kipiyle panolar türce ve adetçe tuttu (dış 32, iç 13). Farklar yalnız boy yuvarlamasında; aşağıya bakın.
- Kapı yönleri tuttu: dış SOL; iç 2 SOL + 2 SAĞ.
- Makas 7 tuttu.
- Kulaklı H toplamı, makas ayağının geldiği ana bölüm yan duvarlarıyla tutuyor: 9. Okuyucu ek bölümün duvarlarını da yanlışlıkla saydı.

## Bizim hatalarımız (sürüm 5)

1. **Standart dışı pencere (80/120) "karkaslı özel pencere panosu"** (100 × 1250 × 2500): PK-03'teki 160/180 ile aynı kural.
   Standart pencereler (120/120, 120/180) üst + alt panel olarak listeleniyor, vasistas ayrı satırda; bunların dışındaki her pencere karkaslı özel pano. Alpha Mini dosyasında da W01 özel pano.
2. **Kulaklı H yalnız makas ayağında:** makassız çatı paneli olan ek bölümün duvarları kulaklı değil (okuyucu hatası; doğru sayım 9 / 15).
3. **Tek yön çatıda saçak yalnız alçak kenarda:** kaplama boyu = makas üst başlığı (6648 → L 6650). Biz iki saçakla 7000 dedik.
4. **Tek kat panel 87 cm kapatır** (kurallar.json'da 1,0): 8,23 ÷ 0,87 = 10 ✓.
5. **Çelik kapı listede her zaman 90 × 200:** paftada ÇK:100/220 yazsa da (PK-02'deki yay dersi gibi).
6. **Tek kat panelde vida 5,5 × 76** ("tek kat panel" satırı).

## Karar (Loftev ↔ Portatifev) ve elle

**Sipariş boyu yuvarlaması:**
- Bu listede kesintisiz 5'e aşağı: 111 → 1110, 108 → 1080, 105 → 1050, 53 → 530, 118,5 → 1185, 62,5 → 625. PK-02 de böyleydi.
- PK-03'te Portatifev gibi 2,5 mm kesintiyle: 115,5 → 1150, 119,5 → 1190.
- Loftev listeleri kendi içinde de karışık.

**PK-03 ile aynı yapılanlar** (Loftev): köşebent 5, baş makas Z'si 7, çektirme U'su 60 → 4, 60'lık alt çerçeve L 3750 (4 ✓), iniş borusu PVC 2000 + 500 (özellikte metal yazıyor).

**Yeni kalemler:**
- sıfır saçak sacı 2;
- özel mahya (geniş) 5;
- tek kat panel kapaması 6;
- çatı izolasyonu Knauf (paket 8,64 m²) 2.

**Sabit takım gibi görünenler:**
- Sıhhi tesisat (7 satır) PK-03 ile birebir aynı.
- Elektrik grubu planı olmayan bu projede de var (W otomat 9 iki listede de).

**Elle:** aşık 30 (biz 27), alın sacı 7 (9), betopan 3 (4), 100'lük alt çerçeve 11 (10), H standart 6 (8), beyaz alçıpan 17 (19; "+2"siz), pencere vidası 140 (120).
