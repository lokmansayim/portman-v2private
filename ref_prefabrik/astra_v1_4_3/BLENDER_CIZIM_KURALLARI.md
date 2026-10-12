# Blender çizim ve CAD aktarım kuralları — v1.0

7 Eylül 2026. AutoCAD/BOM kurallarına bağlı, ayrı Blender kural kaydı. Blender veya 3D aktarım işlerinde önce bu belge ve `BLENDER_KURALLAR.json` okunur. Son kullanıcı talimatı önceliklidir.

## B01 — Kaynağı doğrula

Güncel, kullanıcı tarafından kabul edilmiş DWG, aynı revizyonun yerel DXF/parametre verisi, kuralları ve varsa BOM birlikte doğrulanır. Dosya adı/tarihi tek başına yeterli değildir. Yalnız ilgili proje klasörleri incelenir.

## B02 — Mevcut yapıyı koru

Blender aktarımı yeni plan tasarımı değildir. Orijinal DWG, üretim kuralları ve BOM korunur; çıktılar ayrı aktarım/revizyon klasörüne yazılır. Başka projenin ölçüleri, oda yerleri veya sistemi taşınmaz.

## B03 — Gerçek CAD geometrisini kullan

Ekran görüntüsünden yeniden çizme. Doğrulanmış DWG/DXF nesnelerini oku; iç içe bloklarda taşıma, dönme, ölçek ve aynalamayı uygula. Dış referansları çözümle veya eksik olarak bildir.

## B04 — Birim ve koordinat

Kaynak birimini doğrula; Blender metre dönüşümünü yalnız bir kez uygula. X/Y ve yönlenmeyi koru, Z yönünü ve sıfır kotunu kaydet. Kaynağın cm olması durumunda metre katsayısı 0,01’dir; her dosyanın cm olduğunu varsayma.

## B05 — Panolar ve birleşimler

Her gerçek panel/modül ayrımı korunur. Kalınlık, toplam boy, uç ve birleşim geometrisi kaynaktan gelir. Üçlü H kanalları, gerçek dayama yüzleri ve veranda 100×50 mm iç köşe kuralı korunur; boşluğu sanal dolgu ile gizleme. Aktarım sırasında CAD hatasını sessizce düzeltme, bildir.

## B06 — Doğramalar ve açıklıklar

Kapı/pencere tipi, eni, konumu, yönü ve kotu kaynaktan alınır. Açıklık duvar mesh’inde gerçek boşluktur. Kapı açılım yayı, tarama, ölçü ve yazı yükseltilmez. Tanımsız 3D ürün/aksesuar detayı uydurulmaz; teknik temsil kapsamı belirtilir.

## B07 — Eksik bilgi

Geometriyi etkileyen eksik yüksekliği/kotu önce aynı projenin kayıtlarında ara, yoksa kullanıcıya sor. Bağımsız elemanlarda devam et. Gösterim yüksekliği üretim kesim veya sipariş boyu sayılmaz.

## B08 — Çatı ve veranda

İlk hedef çatısız 3D kat planıdır. Tanımlı çatı ayrı gizlenebilir koleksiyondadır. Yalnız profil/eğim varsa tam çatı montajı uydurma; referans olarak koru. Mevcut %33 eğim, iki yanda 30 cm yatay saçak ve 10 cm topuk kuralları kendi geçerli kapsamlarında uygulanır; eksik çıkma/taşıyıcı/kaplama bilgisi tamamlanmış sayılmaz.

## B09 — Kaynak kimliği

Her fiziksel elemanda kaynak dosya/revizyon, CAD kimliği, tip, ölçü, konum, kural ve ürün/BOM bağlantısı tutulur. Kimlik yoksa DWG’yi değiştirmeden yan eşleştirme dosyası oluştur. Alt mesh’ler ortak kaynak kimliği taşır; yeni revizyonda handle eşliği otomatik varsayılmaz.

## B10 — BOM ilişkisi

Mevcut ürün kodları, reçete ve miktar kuralları korunur. Yalnız ANA bina sayılır; KOPYA/MONTAJ, görünüş ve sunum alt mesh’leri adedi artırmaz. Kapılı/pencereli duvar tek pano, doğrama ayrıca sayılır. Bir mesh bir BOM satırı sayılmaz. Temsil edilmeyen kalemler kapsam farkıyla açıklanır.

## B11 — Kodla tekrar üret

Aynı doğrulanmış veri JSON’dan yerel kodla Blender modeli üretir. Koleksiyonlarda yapı ile ışık/kamera/sunum ayrılır. Yeniden çalıştırma yalnız bu aktarımın ürettiği nesneleri yeniler, çoğaltmaz. Yeni paket/eklenti ücretli servis için kullanıcı yetkisi gerekir.

## B12 — Gerçek geometriyi denetle

Kayıtlı Blender mesh’lerinden dış sınır, kalınlık, bölme yerleri, kapı/pencere konumu-yönü-ölçüsü, boşluklar ve kotlar ölçülür. Kaynakla sayım ve mümkünse hizalı yatay kesit karşılaştırılır. Yalnız beklenen değerleri okuyarak test geçti denmez. Tolerans kaynaktan alınır; yoksa seçilen sayısal tolerans açıkça yazılır ve imalat onayı sayılmaz.

## B13 — Tekrar ve teslim

Bir kez yeniden üretip nesne çoğalmadığını ve ölçülerin değişmediğini kontrol et. Aynı kayıtlı modelden üstten ortografik ve çatısız 3D perspektif üret. .blend, aktarım verisi, CAD–Blender eşleştirmesi, kod, iki PNG, doğrulama/eksikler ve tekrar çalıştırma notu teslim edilir. Hangi DWG ve kural/revizyondan geldiği açıkça belirtilir.

## B14 — Sunum sınırı

Nötr renk, ışık, etiket ve alt sunum düzlemi ürün özelliği veya döşeme reçetesi değildir. Kaynakta bulunmayan mobilya/dekor eklenmez. Tam duvar yüksekliğindeki üst görünüş ile açıklıkları gösteren yatay kesit farklıdır; görüntü türü doğru adlandırılır.

## Referans uygulama — genel kural olmayan değerler

Yan verandalı 2+1, BLENDER-R01; kaynak `yeni-2plus1-yan-verandali.dwg`, v1.4.3 ve 7 Eylül pencere etiketleri. Bu projede kapılar ve kapısız geçiş 200 cm, bağlantı/dikmeler 250 cm **gösterim yüksekliği** olarak kullanıcı tarafından onaylandı. Bunlar yeni projede doğrulanmadan otomatik uygulanmaz. 52 panel, 7 pencere, 5 kapı, 1 açık geçiş; BOM 26 kod/79 adet bu projeye özgüdür. Kullanılan 1 mm sayısal kontrol toleransı imalat onayı değildir.

Referans model, veri, kod ve raporlar: [yan-verandali-2plus1-R01](/Users/lokmansayim/Documents/Codex/2026-09-05/prefabrik-2-arti-1-6x8/outputs/blender-aktarim/yan-verandali-2plus1-R01). Tekrar çalıştırma: [CALISTIRMA.md](/Users/lokmansayim/Documents/Codex/2026-09-05/prefabrik-2-arti-1-6x8/outputs/blender-aktarim/yan-verandali-2plus1-R01/CALISTIRMA.md). Kod bu doğrulanmış revizyona bağlıdır; farklı DWG’ye olduğu gibi çalıştırılmaz.

Bu kayıt mevcut AutoCAD/BOM üretim kurallarının sürümünü veya geçmiş aktarımın dondurulmuş kaynaklarını değiştirmez.
