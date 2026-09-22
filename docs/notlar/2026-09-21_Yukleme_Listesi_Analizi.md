# Yükleme listesi analizi — UĞUR BAŞARIR 60 m² (İkranur Prefabrik) ↔ Motor P6001 BOM'u

Tarih: 21 Eylül 2026, 09:20. Kaynak: Lokman'ın yüklediği `UĞUR BAŞARIR 60 M2 YÜKLEME LİSTESİ.xlsx` (8 sayfa; TEKLİF sayfası bu
projeye ait, diğer 7 sayfa şablonun eski bir projesini taşıyor: Loftev "TEK KATLI – 2. BİNA", CRM 22-1761).
Amaç: motorun üreteceği BOM'un **olması gereken biçimini** görmek ve P6001 çıktısıyla kanıta dayalı karşılaştırmak.
Lokman'ın notu: bu liste doğru referans; AutoCAD şablonundaki liste doğru değil (sonraki aşamada paylaşılacak).

## 1. Listenin yapısı (hedef biçim)
Sütunlar: S | Malzeme | Malzeme Ölçüsü | Adet | Birim Fiyatı | TOPLAM. 12 grup, her grubun kodu var:
1001 Yapıştırma ve karkaslı panel · 1002 Metal aksam · 1003 Kapı ve pencere · 1004 Asma tavan · 1005 Makas · 1006 Çatı ·
1007 Elektrik · 1008 Vida · 1009 Depo · 1010 Sıhhi tesisat · 1011 Dere · 1012 Boya. Sonda grup toplamı, iskonto, ara toplam,
hizmet, genel toplam (KDV hariç). Liste **tam katalogdur**: kullanılmayan kalemler 0 adetle durur, kullanılanların adedi yazılır.
Fiyat sütunları (I…AB): baz fiyat × 1,25 → ×1,12×1,12 → ×1,34/1,4/1,86 → ×1,4108 → ×1,425 → ×2/1,3; dönemler "2021-08",
"2021-09", "2022-001". Yani fiyat = **dönem anlık görüntüsü** (mimari taslaktaki `price_snapshot_id` ile aynı fikir).

## 2. Bu liste P6001 evinin listesi (kanıt)
- Veranda kirişleri: KUTU PROFİL 100×100 **4292,5** ve **2410** mm. Motorun P6001 verandası 439,25 × 251 cm → dış sınır boyları
  4392,5 / 2510; kiriş = dış sınır − 100 (dikme). Birebir.
- Doğramalar: PVC 120/120 ×2, 120/180 ×2, vasistas 60/40 ×1, çelik kapı 90×205 sağ ×1, Amerikan kapı 80×198 ×3 (2 sol, 1 sağ)
  → P6001 İş Emri'yle aynı.
- Dış duvar toplamı: 22 tam pano + 3×625 + 525 = 29.900 mm (1250 nominal) ↔ motor 22×1255 + 2410 = 30.020 mm (1255 aks).

## 3. Kalem kalem karşılaştırma (Adet: liste ↔ motor P6001 rev 2)
| Liste kalemi | Liste | Motor | Durum |
|---|---|---|---|
| 100'lük yapıştırma dolu pano 1250 | 16 | D01 16 | ✓ |
| 100'lük dolu 625 / 525 | 3 / 1 | D06 627,5 ×1, D08 1205 ×1, D10 577,5 ×1 | ✗ kesim farklı, toplam eşit (2400 ↔ 2410) |
| Pencere üst panel 100×1250×500 | 4 | — | motor pencereli panoyu tek parça sayıyor (D02/D03) |
| Pencere alt panel 120/120 (h 800) / 120/180 (h 200) | 2 / 2 | — (eşik 800 / 200 aynı) | üst/alt parçalar yükseklikten türetilecek |
| Vasistas oyma panel 60/40 | 1 | D04 1 | ✓ |
| Dış kapılı karkaslı panel (çelik) | 1 | D09 1 | ✓ |
| 60'lık dolu 1250 | 4 | I01 3 (+ I07 1225 ×1) | ✗ çizimdeki 122,5'lik T panosu listede standart 1250 sayılıyor |
| 60'lık dolu 625 | 2 | I06 627,5 ×2 | ✓ |
| 60'lık dolu 565 / 575 | 1 / 1 | I03 597,5 / I09 577,5 | ≈ (kesim kuralı netleşmeli) |
| 60'lık karkaslı kapılı 1250 / 1220 | 2 / 1 | I11 1255 ×2 / I04 1225 ×1 | ✓ |
| Köşe direği 100×100 / 60×60 | 6 / 1 | B02 6 / B01 1 | ✓ |
| Flanşlı kutu profil 100×100 (veranda dikmesi) | 1 | — | P6001 İş Emri'ne `dikmeler` eklenmeli |
| H 100 (kulaklı+dübelli 8, dübelli 11) | **19** | dış koşularda Σ(pano−1) = **19** | ✓ türetilebilir — kulaklı/dübelli ayrımı kuralı sorulacak |
| H 60 standart | 5 | iç koşular 7 ek − 2 (üçlü H'nin yerini aldığı ekler) = **5** | ✓ türetilebilir |
| 3'lü H 100×100×60 (kulaklı 1 + dübelli 1) | 2 | dış-iç T birleşimi 3 | ✗ (biri pano ortasına geliyor; kural sorulacak) |
| 3'lü H 60 standart | 2 | B03 2 | ✓ |
| Çektirme U'su 100×2440 / 60×2440 | 5 / 3 | — | kural sorulacak |
| 100'lük alt çerçeve 3750 / 60'lık 3750 | 9 / 3 | dış duvar 30,0 m / 3,75 = 8,0→9; iç 11,1 / 3,75 = 3 | ✓ metraj |
| 100'lük duvar omegası 2500 / 60'lık 3750 | 3 / 15 | — | tavan/veranda kuralı sorulacak |
| Saçak omegası 100×2500 / saçak sacı 250×2800 / alın sacı 250×2800 | 7 / 7 / 8 | — | çatı geometrisinden türetilecek |
| Pencere kör kasası 120/180 / pencere U'su | 2 / 6 | — | kural: yalnız 120/180'e kör kasa? |
| Baş makas 8230 / orta makas 8230 | 2 / 5 | — | makas aralığı kuralı (7 makas / 7,73 m) |
| Çatı: tek kat panel L:4350 ×20, mahya ×3, omega aşık 3750 ×37, şilte ×7 | | — | çatı geometrisi (%33, saçak 30) |
| Asma tavan alçıpan 12×1200×2500 ×15 + yeşil ×5 = 60 m²; tavan H'ı 1185 ×70 | | — | tavan alanından |
| Elektrik / tesisat / vida / boya / dere | | — | mahal sayısı, m², pano adedi kurallarıyla |

## 4. Çıkarımlar
1. **Blok sayımı doğru yerde:** planda blok olarak duran her şey (pano, doğrama, köşe direği, üçlü H) motorda zaten sayılıyor ve
   listeyle örtüşüyor. Listenin geri kalanı üç türetme türü ister: **ek sayımı** (pano dizisinden 2'li H), **metraj** (alt çerçeve,
   omega, U), **geometri** (çatı, makas, tavan, saçak/alın). Bunlar plan bloğu değil, model kuralı — DXF'ten sayılmaz, modelden hesaplanır.
2. **Çizim kuralı ≠ BOM kuralı:** çizimde T'de 3 cm kısalan pano (122,5) listede standart 1250 panodur. Motor her panoya iki
   ölçü tutmalı: çizim boyu ve **sipariş boyu**.
3. **Özel pano kesimi** (625+625 mi, 1205 mi) üretim/nakliye kuralı — Lokman'dan.
4. Liste adları blok adlandırma standardı olabilir: `100'LÜK YAPIŞTIRMA DOLU PANO 100*1250*2500` gibi; malzeme kodu XData'da kalır.
5. Fiyat: dönem katsayılı anlık görüntü. CPQ'da `price_snapshot` tablosu olarak modellenir; LLM'e fiyat hesaplatılmaz.

## 5. Lokman'a sorular (sonraki aşamada)
- Kulaklı H ile dübelli H hangi eklerde? (8 kulaklı: makas oturan ekler mi?)
- Çektirme U'su nerede sayılır (5 dış, 3 iç)?
- 100'lük duvar omegası 3 × 2500 ve 60'lık 15 × 3750 neyi kaplıyor (tavan ızgarası mı)?
- Kör kasa yalnız 120/180 pencerede mi?
- Makas adedi ve aralığı kuralı (60 m²'de 2 baş + 5 orta, 8230 boy).
- Bu listenin çizimi (Uğur Başarır) — özel pano kesim farklarını kapatmak için.

## 6. Bugün kesinleşen kurallar
- Çift katlı yapılarda en dış köşeler 100×100 köşe direği.
- Blok adlandırma referansı: yükleme listesi (şablon değil). Mühendisler blokla çalışmıyordu; blok yaklaşımı Lokman'ın kararı.
- Sıra: önce bayi ön onayı; BOM/fiyat/çizim aşamaları sonra. "5 plan" hedefi yok; 37 proje tamamı çıkarılacak ama kurallar
  doğrulandıktan sonra.
