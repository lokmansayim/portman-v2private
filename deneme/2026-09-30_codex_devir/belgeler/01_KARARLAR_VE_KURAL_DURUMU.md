# Kullanıcı kararları ve kural durumu

Bu metin yeni üretim kuralı oluşturmaz. Kullanıcının bu sohbetteki açık istekleri ile kopyalanan tarihli belgeler ayrı kaynaklardır.

## Bu sohbetin açık kullanıcı kararları

- 37 katalog modeli kapsamda; ilk uçtan uca deneyim bütün kataloğu beklemeyecek.
- Şimdilik P9201/P9401/P9501 üzerinde çalışılıyor. IFC teslimde var; ayrıntılı BIM/BOM sonra.
- Üç sunum biçimi istendi: dış görünüş, döndürme/çatıyı açarak iç inceleme, parçaların sırayla görünmesi.
- Ardından P9401 için videolardaki gibi birkaç çatı alternatifi istendi. Henüz A/B/C/D seçimi veya ölçü onayı verilmedi.
- Bilge ve ajanlar kaynak incelemesi, çizim/düzeltme ve kontrol yapar; Claude ana geliştirici/entegrasyon sorumlusudur. Mevcut Motor–IFC–Blender çalışmaları korunur; yeni bir rakip motor kurulmaz.
- İE-02 tamamlandı, yeniden açılmayacak. Harcama, yeni veri paylaşımı, silme ve canlı değişiklik onayları Lokman'dadır.
- Eksik kaynak ölçüsü sessizce tahmin edilmeyecek. Çizim/aktarım hatası, modele özgü değişiklik ve genel kural adayı ayrılacak. Modele özgü karar bütün kataloğa yayılmayacak.
- Devir, aynı Mac'te dosya erişimli Claude Code'a yerel klasör üzerinden yapılacak.

## Kopyalanan kurallar nasıl kullanılmalı?

| Kaynak | Durumu | Bu çalışmadaki karşılığı |
|---|---|---|
| Prefabrik v1.4.3 ve KURALLAR.json, 07.09 | Tarihli kullanıcı üretim/çizim kayıtları; örnek proje değerleri de içerir | Genel/kapsamlı kurallar ve örnek ölçüler ayrıştırılmalı. SKP mesh'leri bu tur yeniden panolanmadı; tüm kurallara uygunluk iddiası yok. |
| Blender B01–B14 v1.0 | Tarihli aktarım kuralları | Kaynak koruma, birim, eleman kimliği, çatı ayırma ve kayıtlı geometri kontrolü esas alındı. CAD kaynak kabulü/pano ayrımı/BOM eşlemesi tamamlanmadı. |
| K02 | Mevcut motor ve v1.4.3, kayıtlı DXF doğrulanmadan PDF olmaması | Kaynak SKP sunumu motor r02 üretimi değildir. Ölçülü 2D için mevcut Motor yolu korunacak. |
| K04 | İç kapı 82 / dış kapı 90 cm çalışma kabulü; Lokman onayı bekliyor | Onaylı üretim standardı gibi uygulanamaz. Kaynak 80/100 ölçülerini bu tur değiştirmedik. |
| K16 | Modül dışı planlarda modüle uyarlama / serbest aks kararı açık | Bu paket K16(a/b) seçimi yapmaz; önerilen çatılar bu kararı çözmez. |
| Eski genel BOM teslim yönergesi | Üretim akışı başvuru kaydı | Bu fazda kullanıcının yeni “BIM/BOM sonra” kararı geçerli; eski BOM dosyaları yalnız tarihsel karşılaştırma. |
| P9401 Tasarim_Kaydi.json | Modele özgü görsel tasarım varsayımları | B %30,7, C yaklaşık %10,7, D 45 cm parapet gibi değerler onaylı kural değildir. %33 çatı kuralının değiştirilmesi veya üretim onayı anlamına gelmez. |

Prefabrik kuralları hafif çelik aileye otomatik taşınmaz. 125,5 cm pano boyu, duvar kalınlıkları ve bağlantı koşulları kaynak/kapsam eşleştirmeden bütün SKP yüzeylerine uygulanmaz. Bir mesh bir pano veya bir BOM satırı değildir.

AutoCAD kayıtlarındaki cm birimi SketchUp için varsayılamaz: kullanılan SketchUp C API geometri verisi inçtir; metreye 0,0254 katsayısıyla bir kez dönüştürüldü. Modeldeki dünya kotu, onaylı proje sıfır kotu olarak sunulmaz.

## Teknik aktarım düzeltmeleri — üretim kuralı değişikliği değil

1. İç içe dönüşümlerde homojen matris w değeri normalize edildi. P9501'de seçili 19 parçada w=0,5035167782 vardı. 63 örnek nokta yerel SketchUp C API ile bağımsız doğrulandı.
2. Eğik dönüşüm (shear) Blender nesnesinin konum/dönme/ölçeğine ayrılırken bozuluyordu. Tam dünya dönüşümü mesh köşelerine uygulandı, nesne matrisi identity yapıldı. Kaynak geometrisi değiştirilmedi.
3. P9401 kaynak çatı ilk görünüşte yanlış adlandırılmıştı; yüz/mahya incelemesiyle **ana beşik + veranda beşik kolu** olarak düzeltildi. Çatı geometrisi aynı kaldı.
4. Blender'ın Türkçe arayüzünde yeni shader node adı değişebiliyor. Güncel çatı üretim kodu node.type kullanıyor; eski make_blend betiği bu bakımı bekliyor.

Sayısal aktarım kontrollerindeki toleranslar üretim toleransı değildir. Kaynak doğruluğu, aktarım bütünlüğü, Lokman görsel kabulü ve teknik üretim kabulü ayrı kayıtlardır.
