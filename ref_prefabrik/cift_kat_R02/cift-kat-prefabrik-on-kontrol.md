# Çift kat prefabrik yapı — çizim öncesi kontrol

Tarih: 12 Eylül 2026  
Durum: İlk talebin kontrol kaydıdır; aşağıdaki 13600 mm ölçüler sonraki kullanıcı talimatıyla değişmiştir. Güncel dış ölçü 12500 × 6000 mm, her kat 75 m² brüttür. Güncel kayıt: `cift-kat-prefabrik-R01-durum.md`. Ana gövde DWG oluşturuldu; iç plan henüz tamamlanmadı.

## Kaynaklar ve öncelik

- İş emri: Kullanıcının bu görevde sunduğu “İŞ EMRİ — ÇİFT KAT PREFABRİK YAPI / YENİ PROJE” metni.
- Geometrik referans: “WhatsApp Image 2026-09-11 at 17.53.28.jpeg”. Fotoğraf üzerindeki yazılı ölçüler okundu; piksel uzunluklarından üretim ölçüsü çıkarılmadı.
- Mevcut kurallar: Masaüstündeki “AI Çizim Dosyaları” arşivinin `prefabrik-cizim-kurallari.md`, `KURALLAR.json` ve `CIZIM_VE_BOM_IS_AKISI.md` dosyaları; sürüm v1.4.3.
- Masaüstü ve önceki çalışma alanındaki birleşik kural belgesi ile JSON kayıtlarının dosya özetleri aynı. Önceki projelerin özel oda ölçüleri, konumları ve adetleri yeni projeye aktarılmadı.
- Bu işte model birimi **mm**. Eski cm birimi, eski dış köşe kesiti ve eski dış ölçü modül hesabının yerine bu iş emrindeki ilgili hükümler geçerli. Eski şablon geometrisinin cm→mm dönüşümü fiziksel boyu değiştirmeden yapılmalı.
- Dış duvar 100 mm; iç duvar 60 mm. Gerçek iç köşedeki 30×60 mm parça, özgün üçlü H bağlantısı, pano içinde merkezlenen kapı/pencere ve tek pano sayımı kuralları korunacak.

## Kesin matematiksel kontroller

Üst ölçü zinciri:

**1200 + 4000 + 2500 + 1200 + 4700 = 13600 mm**

Düşey ölçü zinciri:

**3500 + 2500 = 6000 mm**

İş emrinde verilen ana dış sınır: **13600 × 6000 mm**. Balkonun açık sınırı ile kapalı duvar sınırının ayrımı ayrıca açıklanmalı.

### Cephe modül hesabı

Bu tablo, verilen uzunlukta iki uç kolonu arasında kesintisiz pano diziliminin hesabıdır. Balkonun açık kenarlarını duvar kabul etmez; henüz yerleştirilmiş veya üretim için sayılmış pano listesi değildir.

| Referans cephe uzunluğu | Kolonlar arasındaki mesafe | 1255 mm tam pano | Özel son pano | Kontrol |
|---|---:|---:|---:|---|
| 13600 mm | 13400 mm | 10 | 850 mm | 100 + 10×1255 + 850 + 100 = 13600 ✓ |
| 6000 mm | 5800 mm | 4 | 780 mm | 100 + 4×1255 + 780 + 100 = 6000 ✓ |

Hesap: N = floor((L − 200) / 1255); R = (L − 200) − N×1255. Tam panolar küçültülmedi, kalan boy bölüştürülmedi veya yuvarlanmadı.

### Kat seviyeleri ve sürekli kolon

| Bölge | Başlangıç Z | Bitiş Z | Yükseklik |
|---|---:|---:|---:|
| Zemin kat duvarı | 0 | 2500 | 2500 mm |
| Ara kat çelik kiriş bölgesi | 2500 | 2800 | 300 mm |
| Betopan | 2800 | 2820 | 20 mm |
| Üst kat duvarı | 2820 | 5320 | 2500 mm |

**2500 + 300 + 20 + 2500 = 5320 mm.**

Her gerçek dış bina köşesi için tek fiziksel **100×100×5320 mm** sürekli profil kullanılacak. Alt ve üst katta aynı X-Y konumunu paylaşacak. Katlar veya cepheler üzerinden mükerrer sayılmayacak. Gerçek kapalı bina/balkon sınırı kesinleşmediği için nihai kolon adedi henüz belirlenmedi.

## Çizimi etkileyen belirsizlikler

1. **Alt ölçü zinciri:** Balkon 1200, salon 4000, koridor el yazısı 1200, alt orta oda 3500 ve alt sağ oda 3800 aynı uçtan uca zincir olarak alınırsa toplam **13700 mm** olur. Üstteki 13600 mm toplamdan 100 mm fazladır. Diğer değerler aynı zincirde sabit tutulursa koridora **1100 mm** kalır. Ölçülerin net yüz, duvar ekseni veya dış yüz referansları belirtilmediği için bu fark kendiliğinden duvar kalınlığına bağlanamaz; koridor 1100 mm olarak değiştirilmedi.
2. **Balkon ve dış cephe:** 13600 mm zincir balkonun 1200 mm bölümünü içeriyor. Balkon açık ise kapalı bölümün yatay kapsamı aynı referansla 12400 mm olur; 13600 mm boyunca kesintisiz dış duvar paneli yerleştirmek balkonu kapatabilir. Açık ve kapalı sınırlar ile bunların her iki kattaki devamı açıklanmalı.
3. **Kat planları:** Sunulan tek planın iki katta da aynı oda, balkon ve açıklık düzeniyle uygulanacağı açıkça belirtilmemiş. Dış köşelerin hizalı olması iç planların aynı olduğunu tek başına belirlemez.
4. **Koridor ve banyo kademesi:** El yazısı 1200 ölçüsü girişteki düşey koridor kolunda görülüyor. Yatay koridor kolunun genişliği ile banyo altındaki kademenin yatay ve düşey boyları kesin değil. Fotoğraftaki uzunluk oranlarından türetilmedi.
5. **2760 mm:** Yatak odasının sağ alt bölümünde yazılı bu ölçünün başlangıç ve bitiş yüzleri işaretli değil. Referans yüzleri netleşmeden kesin duvar koordinatına çevrilmedi.
6. **Merdiven:** Kol eni, yatay boy, sahanlık ölçüsü ve basamak/rıht düzeni verilmemiş. 2820 mm kat farkı tek başına bunları belirlemez. Fotoğraftaki basamak çizgileri sayılarak üretim ölçüsü atanmadı.
7. **Pencereler:** Bu proje için pencere adetleri, duvarları ve tipleri açıkça gösterilmiyor. Mevcut katalog ve merkezleme kuralları biliniyor; önceki projedeki pencere konumları yeni plana taşınmadı.

## Kalite kontrol durumu

| Kontrol | Durum |
|---|---|
| A — Ana ölçüler | Yazılı dış ölçüler doğrulandı; CAD geometrisi henüz oluşturulmadı. |
| B — Cephe toplamları | Verilen 13600 ve 6000 mm uzunluklar için aritmetik doğrulandı; gerçek duvar segmentlerinin yerleşimi bekliyor. |
| C — Dış köşe kesiti | 100×100 mm talimatı kaydedildi; fiziksel model kontrolü bekliyor. |
| D — Sürekli kolon | 5320 mm yükseklik doğrulandı; nesne sürekliliği kontrolü bekliyor. |
| E — Ara kat | 300 + 20 = 320 mm ve tüm Z seviyeleri doğrulandı; geometrik kontrol bekliyor. |
| F — İç duvarlar | Mevcut kurallar bulundu; yerleşim açıklaması sonrası uygulanacak. |
| G — Kapı/pencere | Mevcut kaynak/katalog kuralları bulundu; proje açıklıkları tamamlanınca doğrulanacak. |
| H — Çift sayım | Tek fiziksel kolon ilkesi kaydedildi; model ve BOM sayımı henüz yapılmadı. |

## Kayıt durumu

İş emrinin 16. maddesindeki “Kesin olarak bulunamıyorsa ... dur” hükmü gereği belirsiz ölçülerle DWG tamamlanmadı. Bu dosya çizim öncesi kontrol kaydıdır. Nihai DWG, montaj gösterimleri ve aynı sürüm malzeme listesi henüz üretilmedi.
