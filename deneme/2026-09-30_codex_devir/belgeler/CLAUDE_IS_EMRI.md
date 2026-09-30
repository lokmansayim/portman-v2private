# Claude'a devir görevi — yerel inceleme ve entegrasyon adayı

İş, ana geliştirme sorumluluğunu devralmak değil; zaten Claude'da olan sorumluluğa bu yerel çalışma paketini eklemektir. Yeni resmî İE numarası atanmadı.

## İlk somut çıktı

1. Paketin hash/bütünlük kontrolünü yap; mevcut ana deponun DURUM, K02/K04/K16 ve ilgili Motor–IFC–Blender koduyla karşılaştır. Paketteki repo belgeleri 30.09 tarihli okuma kopyasıdır; mevcut çalışma commitini ayrıca kaydet.
2. Üç model ve P9401 A–D çatı seçeneklerini “alındı / yeniden üretilebilir / uyarlama gerekli / kaynak kararı gerekli” olarak eşleştir. Kaynak SHA, çalışma revizyonu, açık fark, Lokman kabulü, teknik kontrol ve entegrasyon alanlarını koru.
3. Mevcut depoda aynı işi yapan modülleri belirle. Bu prototipin verisini ve yararlı dönüşüm/kontrol düzeltmelerini mevcut yola bağlayan en küçük yerel aday değişikliği hazırla. Kaynak inceleme görüntüleyicisi ile motorun üretim/veri kaydını karıştırma; ikinci kalıcı doğruluk kaydı kurma.
4. İlk karşılaştırmayı P9401 üzerinde yap: kaynak model + dört çatı seçeneği ve gövdenin korunması. Çatı B/C/D'yi seçilmiş ürün veya genel katalog kuralı sayma.
5. Kod haritasındaki yeniden üretim engellerini çöz veya açık bırak: eski make_blend/shear, yerel shader adı, sabit yollar, sıra numaralı seçimler, IFC metin-replace sarmalayıcısı, başarısızlıkta durmayan raporlayıcılar. Değişiklik varsa kaydedilmiş çıktı üzerinden tekrar kontrol et.
6. Lokman'a kısa bir devir kabul raporu ver: alınanlar, tekrar doğrulananlar, mevcut sisteme bağlananlar, açık kalan kararlar ve bir sonraki somut işlem. Eski test sayılarını yeni çalıştırmış gibi aktarma.

## Korunacak sınırlar

- İE-02 kapalıdır; yeniden açılmaz. Yeni mimari/baştan kurulum veya rakip motor yok.
- İlk üç model + IFC şimdi; detay BIM/BOM sonra. Diğer 34 model katalog kapsamında kalır.
- Özgün kaynaklar ve önceki revizyonlar korunur. Kaynakta olmayan ölçüye sessiz varsayım eklenmez.
- P9401 çatı isteği modele özgü tasarımdır. Genel çizim/üretim kuralına dönüşmesi ayrı kapsam/onay ister.
- K04 kapı ölçüsü ve K16 seçimi açık karar olarak kalır.
- Yerel aday hazırlığı yapılabilir. Harcama, yeni veri paylaşımı, silme ve canlı değişiklik Lokman'ın açık onayına bağlıdır; bu devir bunları onaylamaz.
- Lokman görsel seçimi teknik/üretim kabulü sayılmaz. IFC şema geçişi kaynak plan doğruluğu sayılmaz.
