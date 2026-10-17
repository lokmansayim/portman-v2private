# Arşivi yeniden kullanma

**Güncel sürüm v1.4.3 — 7 Eylül 2026.** Yeni el çizimi/PDF işlerinde önce `CIZIM_VE_BOM_IS_AKISI.md` okunur. Excel BOM standart teslimdir; eski liste hazırlamama tercihi yeni işler için kaldırılmıştır. Son prototipin ölçü ve adetleri yeni projeye taşınmaz.

1. Dosya bulmak için DOSYA_DIZINI.json içindeki kısa adları ve göreli yolları okuyun.
2. Kural uygulamadan önce KURALLAR.json ve prefabrik-cizim-kurallari.md dosyalarını okuyun. JSON genel, koşullu, projeye özel ve çalışma değerlerini ayırır. Tam açıklamalar birleşik belgede ve JSON bölümlerinde bulunur.
3. Son kullanıcı düzeltmesi eski tarife göre önceliklidir. Proje ölçülerini yeni projeye otomatik taşımayın.
4. Dosya üzerinde çalışmadan önce güncel olup olmadığını kontrol edin; masaüstü arşivi otomatik eşitlenmez. Kullanıcının açık çizimini ve sonraki talimatını esas alın.
5. Dosya bulunamazsa dizindeki konumu kontrol edin; yapılmamış çizim veya kayıt işlemini tamamlanmış saymayın.

## 6 Eylül 2026 — v1.2 için dikkat edilecek noktalar

- Genel kurallardaki 62,75 cm yarım pano yerleşimi isteğe bağlıdır; 125,5 cm ana aks aralığı korunur. İç duvarın orta ekseni konumlandırılır, yüzü değil.
- Yatak odaları koridordan erişilir ve kapılar oda içine, komşu duvara doğru açılır. Dış veranda girişi bu düzeltmenin kapsamına girmez.
- Cumbalı 6 × 5 projenin banyo kademesi ve korunacak koridoru `cumbali-6x5-proje-notlari.md` içinde ayrı proje kararıdır. Önceki 6 × 8 projenin alan ve çatı ölçülerini güncel projeye aktarmayın.
- Ana çatı ve cumba için her iki yanda 30 cm yatay saçak vardır; toplam saçak ilavesi 60 cm'dir.

## 6 Eylül 2026 — v1.3 bağlantı düzeltmesi

- Pano pano ilerleyin. 30×60 mm iç köşe direğini yalnız gerçek köşede, 3×6 veya 6×3 cm yönlenmesiyle kullanın; 6×6 cm kareye çevirmeyin.
- Düz pano birleşimine ve T ortasına köşe parçası eklemeyin. Üçlü H ayrı bir parçadır; Güncel Şablon 2024 özgün bağlantısını inceleyin, boşluk kapatmak için ilave dolgu uydurmayın.
- Cumbalı projede onaylanan üç panel boyu 122,5 cm (banyo kapılı), 59,75 cm (kısa kademe) ve 119,5 cm (sağ oda koridor kapılı) olarak proje notlarında bulunur. Bunlar bütün panelin boylarıdır; diğer birleşimlere otomatik ±3 cm uygulamayın.
- Yalnız boşluk kontrolü yeterli değildir: köşe parçasının gerçek ölçüsünü, hangi birleşimde kullanıldığını ve kaynak üçlü H geometrisini de doğrulayın.

6 Eylül v1.3 uygulaması kullanıcı tarafından ekranda onaylandı, DWG kaydedildi ve gerçek AutoCAD dışa aktarımı üzerinden bağımsız son kontrol geçti. Bu kayıt birikimlidir: önceki birim, pano, aks, duvar, kapı/pencere, veranda, alan, çatı ve ön görünüş kuralları korunmuştur. Projeye özel değerler kendi kapsamlarında kalır.

## 7 Eylül 2026 — BOM ve yükleme listesi

`BOM ve Yükleme Listeleri/Cumbalı 6x5/BOM OKUMA.md` dosyasını okuyun. Malzeme kodlu ayrı DWG, Excel ve sayım kayıtları bu klasördedir. Ana/kopya ayrımıyla tek bina sayılır; çizim geometrisi v1.3 ile aynıdır.

## 7 Eylül 2026 — Yan verandalı yeni 2+1

Son çizim ve Excel `2+1 Çizimleri/Yan Verandalı 6x8p5` klasöründedir. Önce bu klasördeki `PROJE NOTLARI.md` dosyasını okuyun. 773×1076,75 cm uyarlama ve kapısız salon geçişi yalnız bu projeye aittir. Yeni BOM kodları için kökteki `MALZEME_KATALOGU.json` kullanılır. Önceki cumbalı prototip ayrı olarak korunmuştur.

## Üçlü H kanallarına pano geçmesi — 7 Eylül 2026, v1.4.1

H boşluklu bağlantıdır: panolar kanallarına girip gerçek gövde yüzlerine dayanır. Dört düğümün 12 kanalı gerçek pano geometrisiyle doğrulandı; 6×6 cm sanal kapatma ile denetim yapılmaz. Yan verandalı çizim ve Excel yenilendi. Ayrıntı birleşik kurallarda ve projenin PROJE NOTLARI.md dosyasındadır.

## Saha montaj planı — 7 Eylül 2026, v1.4.2

Yeni işlerde ayrı montaj planı kopyası eklenir. Standart panolar sade, standart dışı panolar farklı renkli ve gerçek toplam boy ölçülüdür. Yerleşim ve ölçek aynıdır; montaj kopyası BOM sayılmaz. Ayrıntılar birleşik kurallardadır.

## Veranda iç köşesinde 100×50 bağlantı — 7 Eylül 2026, v1.4.3

- 10 cm dış duvar ile 6 cm iç duvarın veranda girintisindeki gerçek iç köşe birleşiminde, dış köşedekiyle aynı 100×50 mm köşe parçası kullanılır. Doğrudan 100 mm panodan 60 mm panoya geçiş yapılmaz.
- Köşe bloğu gerçek 10×5 cm kesiti korunarak uygun yönde döndürülür. Pano uçları bağlantı yüzlerine ulaşır; boşluk, çakışma veya sanal kapatma yapılmaz.
- 30×60 mm iç köşe kuralı 6 cm iç duvarların kendi gerçek köşelerine aittir. Bu 10 cm dış duvar birleşiminde 100×50 mm parça kullanılır. Düz ve üçlü H/T birleşimlerine keyfi köşe eklenmez.
- Etkilenen pano boyu gerçek geometri üzerinden yeniden hesaplanır. ANA, KOPYA ve MONTAJ birlikte güncellenir; standart dışı pano mor ve gerçek toplam boy ölçülü olur. Kapı/pencere etkilenirse yeniden ortalanır.
- Dış ve iç köşede kullanılan fiziksel parça aynıysa tek malzeme kodunda toplanır; yönlenmesi yeni ürün sayılmaz. BOM yalnız ANA binayı sayar. Yeni işlere bu projenin pano boyları/adetleri aktarılmaz.

## Montaj planında pencere etiketleri — 7 Eylül 2026

Montaj planında her pencere, BOM ile eşleşen malzeme kodu ve en×yükseklik ölçüsüyle kendi konumunda belirtilir. Ölçü birimi görünür yazılır. Pencere etiketleri açık mavi (4), özel pano boy ölçüleri mor (6) gösterilir. Bu pencere tanımıdır; standart panoya toplam boy ölçüsü ekleme yasağını değiştirmez. Geometri ve BOM adetleri korunur.

## Blender çizim ve aktarım kuralları — 7 Eylül 2026

Blender/3D aktarım işlerinde ayrıca `BLENDER_CIZIM_KURALLARI.md` ve `BLENDER_KURALLAR.json` okunur. Bunlar ayrı v1.0 aktarım kaydıdır; AutoCAD/BOM v1.4.3 kuralları korunur. Güncel CAD gerçek geometrisi kullanılır; panel, birleşim, açıklık ve BOM kimlikleri korunur. Proje onayları genel üretim ölçüsü yapılmaz. Referans model/veri/kod yolları Blender JSON’undadır.
