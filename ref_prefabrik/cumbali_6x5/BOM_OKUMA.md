# Cumbalı 6×5 — BOM kaydı

7 Eylül 2026. Kullanıcı mevcut planı doğru kabul etti ve benzersiz malzemelerin bloklanıp Excel yükleme listesine dönüştürülmesini istedi. Kapılı/pencereli duvarlar tek pano; kapı ve pencereler ayrıca sayılır. Kullanıcı prototipi sorunsuz bulduktan sonra aynı gün bu akışı yeni el çizimi/PDF işleri için standartlaştırdı. Güncel v1.4 kuralları ve CIZIM_VE_BOM_IS_AKISI.md geçerlidir; eski liste hazırlamama tercihi yeni işler için kaldırıldı.

## Dosyalar ve sayım

- `prefabrik-cumbali-6x5-BOM.dwg`: onaylı plan geometrisini koruyan, malzeme kodlu ayrı çizim. AutoCAD'de kaydedildi ve yeniden dışa aktarılarak doğrulandı.
- `Cumbali-6x5-Yukleme-Listesi.xlsx`: YÜKLEME ve Blok Sayımı sayfaları. YÜKLEME adetleri Blok Sayımı satırlarından SUMIFS ile hesaplanır.
- `BOM_SAYIM_KAYDI.json`: malzeme kataloğu, eski/yeni blok eşleştirmesi, konum, nesne referansı ve sayım kapsamı.
- `BOM_DOGRULAMA.json`: kaydedilen DWG üzerinden geometri ve adet doğrulaması.

20 malzeme kodu, yönlenme farkları nedeniyle 26 aktif blok adı vardır. Aynı fiziksel kalemin H/V çizim varyantları tek malzeme kodunda toplanır. Bir binada 35 pano, 6 pencere, 4 kapı, 11 bağlantı gösterimi ve 2 veranda profil gösterimi bulunur. İkinci plan kopyası aynı elemanların gösterimidir; sayılmaz. Ön görünüş ve makas çizgileri ilave malzeme sayılmaz.

## Yeniden sayarken

1. Kullanıcının açık ve son kaydedilmiş DWG'sini doğrulayın; arşiv otomatik eşitlenmez.
2. BOM blok adındaki ikinci alan malzeme kodudur: `BOM_D01_...`. Üst seviye malzeme INSERT'lerinde `AI_BOM` XData ilk değeri kod, ikinci değeri `ANA` veya `KOPYA`dır.
3. Yalnız ANA bina üst bloklarını sayın. Kapı ve pencere iç INSERT'lerini ayrıca birer doğrama olarak sayın; pano içindeki iki duvar dikdörtgenini ayrı pano saymayın. Kaynak blok tanımlarını ve kullanılmayan tanımları saymayın.
4. Veranda iki kenar çizgisi birlikte tek profil bloğudur. Aynı profilin iki çizgisini iki malzeme saymayın.
5. Konum/rol etiketi değiştiyse bir bina kapsamını yeniden doğrulayın. Excel DWG'ye canlı bağlı değildir; DWG değişince kaynak sayımı yenilenmelidir.

## Birimler ve eksikler

DWG cm, listede mm kullanılır. Panolarda uzunluk × kalınlık × yükseklik, pencerelerde en × yükseklik verilir. 1255 mm modülü örnek yükleme dosyasındaki 1250 mm ile değiştirmeyin.

Kapılardaki 820/970 mm değerleri plan açıklıklarıdır; ürün sipariş ölçüsü değildir. Bağlantıların kesiti çizimdeki gösterimden alınmıştır; profil türü ve kesim boyu doğrulanmadan üretim ölçüsü sayılmamalıdır. Veranda 1255/3815 mm değerleri dış sınır ölçüleridir. Bu kalemlerde Excel sarı açıklama taşır.

Çatı makaslarının üretim parçaları ve adetleri, çatı kaplaması, tesisat ve sarf malzemeleri mevcut planda tanımlı değildir. Eski yükleme listesinden bu miktarları aktarmayın. Bu dosya çizilmiş malzemelerin BOM'udur; eksik üretim verileri tamamlanmadan tam sevkiyat listesi değildir.
