# Tatar 80 m²: bayinin PDF'inden sıfırdan Blender modeli (23 Eylül 2026)

**Kaynak:** Yalnız Mustafa Tatar'ın WhatsApp'tan gönderdiği iki dosya kullanıldı:
- 16.09 tarihli PDF (`.80m2-Model.pdf`): planın tek kaynağı.
- 27.08 tarihli görsel: yalnız ön görünüşteki çatı biçimi için.

Astra'nın Blender çizimi kullanılmadı. Motor'un kural düzeltmeleri de uygulanmadı. Model, bayinin çizdiği planın birebir 3B karşılığı.

## Nasıl kuruldu
1. **`blender_hazirla.py`:** PDF'i okur (`10_Cozumleyici/kod/cozumleyici/pdf_vektor.py`). Çıkardıkları:
   - Bayinin çizdiği her duvar parçası = bir pano
   - Pencere ve kapıların yeri ve ölçüsü
   - Oda poligonları
   - Tefriş çizgileri

   Hepsini `blender_girdi.json` dosyasına yazar.
2. **`blender_ciz.py`:** Yalnız bu JSON'dan modeli kurar. Blender'ın kendi Python'unda da çalışır: `blender -b --python blender_ciz.py -- blender_girdi.json <klasör> --render`
3. **Her pano ayrı bir nesne.** Nesnenin özelliklerinde şunlar yazılı: BOM kalemi, sınıf (tam / yarım / özel / köşe), boy, kalınlık, yükseklik, üzerindeki açıklıklar ve kaynak parça numarası.
4. **Açıklıklar panodan kesildi.** Pencere ve kapılar ayrı nesneler.
5. **BOM sahneden sayıldı:** `blender_bom.csv`.

## Sonuç
- **Nesneler:** 65 pano nesnesi (40 tam, 5 yarım, 14 özel, 6 köşe parçası). Bunlara 8 pencere, 1 çelik dış kapı ve 7 iç kapı boşluğu eklenir.
- **Çatı:** 9 makas, ana çatıda 93,2 m² ve veranda beşiğinde 3,2 m² trapez sac. Veranda için 2 dikme ve 4 kiriş.
- **Ölçüler:** 800 × 969 cm. Mahya 401,9 cm (%33 eğim, 30 cm saçak, 10 cm topuk).

## Bayinin çiziminde bulunan hatalar
1. **3 pencere iki panonun ekine oturuyor.** Pencereli pano tek parça olduğu için bu hâliyle üretilemez. Ya karkaslı özel pano gerekir ya da pencere kaydırılmalı. Montaj renkli planda kırmızıyla işaretli.
   - Yatak 3'teki 120×120 pencere, ekin tam ortasında (60 + 60 cm).
   - Yatak 1'deki 120×120 pencere (20 + 99 cm).
   - Salonun 120×180 ön penceresi (27 + 93 cm).
2. **Banyo vasistası 2 cm taşıyor.** Pencere komşu panoya 2 cm taşıyordu. Bunu çizim toleransı saydım, pencere yarım panoya kırpıldı.
3. **Hol ve WC etiketleri çizimle uyuşmuyor.** Etikette 7,4 ve 4,0 m² yazıyor; çizimden ölçülen alanlar 8,95 ve 2,50 m². Toplam tutuyor, dağılım farklı.
4. **Veranda bina çizgisinin 60 cm dışına taşıyor.** Model bayinin ön görünüşüne göre kuruldu (bkz. varsayım 1).

## BOM karşılaştırması: bayinin çizimi (Blender) ve Motor (kurallı, 10_Cozumleyici)
| Kalem | Blender (bayinin çizimi) | Motor |
|---|---|---|
| Dış tam pano | 23 | 23 |
| – pencereli (120×120 / 120×180 / 60×40) | 6 / 3 / 2 | 4 / 2 / 2 |
| Dış yarım / özel pano | 4 / 4 | 0 / 7 |
| İç tam / yarım / özel pano | 17 / 1 / 10 | 14 / 1 / 13 |
| Dış duvar metrajı | 34,68 m | 34,68 m |
| İç duvar metrajı | 31,51 m | 31,35 m |
| Pencere 120×120 / 120×180 / 60×40 | 4 / 2 / 2 | 4 / 2 / 2 |
| Dış kapı | 1 (100 cm, çizimdeki) | 1 (90 cm, 21.09 kararı) |
| İç kapı boşluğu | 7 (80 cm) | 7 (82 cm) |
| Makas / çatı sacı / veranda taşıyıcı | 9 / 96,4 m² / 2 dikme + 4 kiriş | Motor BOM'unda henüz yok |

Metraj ve doğrama adetleri iki yolda aynı çıktı. Farklar iki yerden geliyor:
- Pencerelerin ek üstüne oturması (Blender'da 11 pencereli pano, Motor'da 8)
- Özel ve yarım pano dağılımı

Bunlar 10_Cozumleyici raporundaki Ubeydullah sorularıyla aynı konular.

## Varsayımlar (teyit edilecek)
1. **Veranda çatısı:** Bayinin 27.08 ön görünüşünde iki alın var. Bu yüzden öne çıkan ikinci, daha alçak bir beşik çizildi (mahya 344 cm). Veranda, bina çizgisinden 60 cm dışarıdaki 2 dikmeye oturuyor. 16.09 satış formunda yalnız "beşik çatı" yazıyor.
2. **Kapı yüksekliği:** Tüm kapı boşlukları 200 cm alındı (250 duvar − 50 lento).
3. **Pencere eşikleri:** BOM notlarından alındı: 120×120 için 80 cm, 120×180 için 20 cm, 60×40 için 160 cm.
4. **Kapsam dışı kalemler çizilmedi:** Bu siparişte iç kapılar kapsam dışı (bayi takıyor), yalnız boşlukları var. Boya, vitrifiye ve tesisat da çizilmedi. Zemin betonu gösterim için çizildi ve "bayi/saha" olarak işaretli.
5. **Çatı dolgusu ve makaslar:** Alın üçgen dolguları ve makas aralığı (≤ 125,5 cm, toplam 9 makas) şimdilik bir kural değil, kabul. Teyit edilecek.
6. **Renkler:** Pencereler beyaz, çatı ve dereler antrasit (satış formundaki gibi).

## Dosyalar
- `Tatar_80m2_bayi_plani.blend`: Blender 5.0 ile kaydedildi. Eski bir sürümde açılmazsa `.glb` dosyasını içe aktarın ya da betiği kendi Blender'ınızda çalıştırın.
- `Tatar_80m2_bayi_plani.glb`: Nesne özellikleriyle (extras) birlikte dışa aktarıldı.
- `01_ust_plan_montaj.png`, `02_dis_perspektif.png`, `03_catisiz_ic_gorunus.png`, `04_on_gorunus.png`, `sunum.png`
- `blender_bom.csv`, `blender_ozet.json`, `blender_girdi.json`
- `kod/blender_hazirla.py`, `kod/blender_ciz.py`

Koleksiyonlar: 01 dış panolar · 02 iç panolar · 03 köşe · 04 doğrama · 05 zemin · 06 oda renkleri · 07 yazılar · 08 bayinin tefrişi · 09 çatı · 10 makaslar · 11 veranda taşıyıcı · 12 arazi. Montaj renklerini görmek için panoların malzemesini `Montaj_*` olarak değiştirin; `01_ust_plan_montaj.png` bu hâliyle alındı.
