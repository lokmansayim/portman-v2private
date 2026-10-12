# Çift kat prefabrik — R01 çalışma durumu

12 Eylül 2026. **Ana gövde oluşturuldu ve kontrol edildi; iç plan ile kapı/pencere açıklıkları henüz tamamlanmadı.**

## Kullanıcının kesinleştirdiği değişiklikler

- Ana dış ölçü: **12500 × 6000 mm**.
- Zemin kat: **75 m² brüt**; üst kat: **75 m² brüt**. Toplam **150 m² brüt**. Bunlar dış ölçülerden hesaplanan alanlardır; net oda alanı değildir.
- Balkon ve merdiven çizim kapsamından çıkarıldı. İki bağımsız daire düzeni esas alınacak.
- Üst bölüm zinciri: **4000 + 2500 + 1200 + 4800 = 12500 mm**; kullanıcı bu dağılımı kabul etti.
- Alt bölüm referans zinciri: **4000 + 1200 + 3500 + 3800 = 12500 mm**.
- Yatay koridor: **1255 − 30 − 30 = 1195 mm net**.
- Ön cephe pencereleri: **1200×1800 mm**; diğer oda pencereleri: **1200×1200 mm**; banyo/WC: **600×400 mm**. Girişin bulunduğu alt kenar ön cephe olarak ele alındı.
- Mevcut prefabrik kuralları v1.4.3, bu görevin mm birimi, yeni dış köşe ve cephe hesabı hükümleriyle birlikte uygulanacak.

## DWG'de oluşturulan geometri

- Aynı X-Y koordinatlarındaki iki katın 3B dış pano yerleşim hacimleri.
- **4 adet**, her biri tek 3B nesne içeren **100×100×5320 mm** sürekli köşe kolonu bloğu. Kesit dış boyu gösterilir; profil et kalınlığı bu kayıtta tanımlanmış değildir.
- Kolonların sol-alt kesit koordinatları: **(0,0), (12400,0), (12400,5900), (0,5900)**. Hepsi Z=0'dan başlar.
- Zemin kat duvar hacimleri: **Z=0–2500 mm**.
- Ara kat çelik kiriş bölgesi referansı: **Z=2500–2800 mm**; Betopan seviyesi: **Z=2800–2820 mm**.
- Üst kat duvar hacimleri: **Z=2820–5320 mm**.
- Ayrı zemin/üst kat gövde planları, gerçek AutoCAD ölçü nesneleri ve düşey kot kontrol görünüşü.
- `ANA_GOVDE_3D` adlı kayıtlı üç boyutlu görünüş.

**Pano hacimleri bu aşamada açıklıksız yerleşim referansıdır.** Çizimde “REZERV” rolündedir; tamamlanmış üretim panosu veya nihai BOM olarak sunulmaz. Ara kat için kot/bölge gösterilmiştir; kiriş adedi, aralığı, ürün kesiti veya bağlantı detayı türetilmemiştir.

## Cephe hesapları — her kat için

**CEPHE A — ÖN, 12500 mm**  
100 kolon + 9×1255 pano + 1005 özel pano + 100 kolon = **12500 mm ✓**

**CEPHE B — SAĞ, 6000 mm**  
100 kolon + 4×1255 pano + 780 özel pano + 100 kolon = **6000 mm ✓**

**CEPHE C — ARKA, 12500 mm**  
100 kolon + 9×1255 pano + 1005 özel pano + 100 kolon = **12500 mm ✓**

**CEPHE D — SOL, 6000 mm**  
100 kolon + 4×1255 pano + 780 özel pano + 100 kolon = **6000 mm ✓**

Bir katta 26 standart + 4 özel = **30 pano yerleşim hacmi**; iki katta **60**. Özel hacimler iki katta toplam 4 adet 1005 mm ve 4 adet 780 mm'dir. Kapı/pencere detayı ve iç panolar eklenmeden bu sayılar sevkiyat listesi değildir.

## Yapılan kontroller

- Gerçek AutoCAD nesnelerinden okunan model dış sınırı: **12500 × 6000 × 5320 mm**.
- Kolon adedi **4**, dört farklı X-Y konumu; bütün kolon blok ölçekleri **1:1:1**.
- Kolonun kendi 3B nesnesinden ölçülen uzunluk/genişlik/yükseklik: **100/100/5320 mm**. Her blokta tek 3B gövde var; katlar boyunca bölünmemiş.
- Zemin ve üst katta 30'ar pano hacmi; gerçek nesne boyları **1255/1005/780 × 100 × 2500 mm**.
- Kolon ve pano hacimleri arasında pozitif hacimli çakışma bulunmadı.
- Plan ve kesit ölçü nesneleri **12500, 6000, 5320 ve 2500 mm** değerlerini gerçek geometriden gösteriyor; ölçü metni elle değiştirilmemiş.
- AutoCAD dosya denetimi: **0 hata**.

## Kalan iş

Referanstaki banyo kapısı yanındaki kademenin yatay/düşey ölçüsü henüz kesinleşmedi. Kullanıcının 1195 mm yanıtı koridor genişliğini çözüyor; kademenin kapı duvarını kaç mm ileri/geri taşıdığı ayrıca ölçülendirilmeli. İş emrinin 16. maddesi gereği bu ölçü fotoğraftan tahmin edilmedi.

İç duvarlar, banyo kademesi, açıklıkların özgün kaynak bloklarıyla yerleşimi, oda net alanları, nihai montaj planı ve nihai Excel BOM henüz hazırlanmadı. Bunlar tamamlanmadan tüm proje bitmiş sayılmaz.

## Dosya

[Ana gövde R01 — DWG](cift-kat-prefabrik-12500x6000-ana-govde-R01.dwg)

Önceki kaynak çizim korunmuştur. Bu görev için yeni dosyada çalışılmıştır.
