# P9201 — kaynak incelemesi ve ilk uygulama iş emri

Tarih: 30.09.2026. Durum: yerel iş emri; Lokman üç sunum biçiminin tamamını istedi. SKP-inceleme-01 sunumları ve geometrik IFC hazır; r01 düzeltmesi, çizim kabulü ve canlı entegrasyon yapılmadı. 30.09 ek kararı: ilk aşamada üç model, IFC dahil; ayrıntılı BIM/BOM sonra.
Mevcut model iş kimliği: **PM-KATALOG-P9201**. İncelenen çıktı: **r01**, 22.09.2026, Motor v1.1. Düzeltme hedefi: r02 adayı; uygulayıcı güncel depoda daha yeni revizyon varsa sonraki boş revizyonu kullanır. Bu belgenin sürümü 02'dir; çizim revizyonu değildir. Yeni İE numarası tahsis edilmedi.

## Kaynak ve sürüm

- Görsel kaynak: `/Users/lokmansayim/Desktop/Portatifev Toptan/İçerik Son Hali/TEK KAT PREFABRİK/PORT - P9201/PS-1092.jpg`. Tek plan görseli; dosyada revizyon tarihi yok. P9201 klasörü / PS-1092 pafta adı birlikte korunacak.
- Görsel SHA-256: `00721a420fabf42f97fd1b2091f25084f553e7e43d2742a3d3ee771f1102c8cb`. Arşiv kopyasıyla aynı; klasör adı tek başına teknik onay kanıtı değildir.
- Güncel katalog: `lokmansayim/portman-v2private`, `beyin/veri/katalog_37_proje.json`, Git blob `0ad8e1a2b0f6fbd85a2acc75793e3b1d48258d0b`: P9201, Prefabrik tek kat, 92, 3+1, sayfa alanı 20. Katalog PDF sayfa 20 bu işte ayrıca açılmadı.
- Güncel ana dal ağaç kimliği: `ae393808b01bee755b1d5aa2914df89be3be9a0c`. Bu bir Git ağaç kimliğidir, commit veya canlı paket kimliği değildir.
- Vektör kaynak: depoda `ref_katalog/TEK_KAT_PREFABRIK_PLANLARI.dxf` mevcut. Eski r01 manifestindeki referans SHA-256: `22cc9304106725f555afc59223433b8383fbe3a19ba8ff4a3b40eb23b61fab66`. Güncel DXF ile aynı olduğu henüz doğrulanmadı.
- Mevcut r01 paketi: `/Users/lokmansayim/Documents/Codex/2026-09-22/mer/work/plans/P9201/`; PDF, DXF, is_emri.json, extraction.json, validation.json, manifest.json ve BOM dosyaları mevcut. PDF görsel olarak, JSON kayıtları metin olarak incelendi; bu tur motor testi çalıştırılmadı.
- Arşivdeki `92 M2 PEYZAJLI.skp` geometri olarak açıldı. SHA-256: `31fc08e97bbeee8483cbca308e0648bb10e87d96b187d3bd9ff9e07b214777fc`. SKP-inceleme-01 sunumunun kaynağıdır; JPG/DWG revizyon uyumu ve üretim kabulü bekliyor.
- Depodaki 29.09 tarihli DURUM.md okundu: İE-02 kapalı. Masaüstündeki 23.09 DURUM.md güncel durum olarak kullanılmayacak.

## Kaynaktan okunanlar

Plan başlığı 92,0 m² / 3+1. İki yatak odası 11,4 ve 12,1; çocuk odası 9,0; açık mutfaklı yaşam alanı 32,7; banyo 4,5; ara hol 1,5; veranda 15,7 m².

Ölçü zincirleri: üst 1140 = 382 + 758; alt 1140 = 382 + 256 + 502; sol 836 = 324 + 188 + 324; sağ 836 = 459 + 314 + 63. Görselde birim yazmıyor; cm yorumu DXF birimi ve onaylı kural ile doğrulanacak.

Altı pencere görünür: iki 120/120, üç 120/180, bir 60/40. Beş kanatlı kapı görünür: üç oda, banyo ve veranda–yaşam alanı. Hol–yaşam alanı açık bağlantısı korunacak. Kapı ölçüleri görselde yazmıyor; pencere etiketlerinin genişlik/yükseklik anlamı doğrulanacak.

Mahal etiketleri veranda dahil 86,9 m², veranda hariç 71,2 m² topluyor. Bunlar etiket toplamlarıdır; onaylı net/brüt hesap değildir. 92 m² ile 5,1 m² farkın anlamı açıklanmadan alan hatası denmeyecek. Katalog JSON'unda P9201 yaşam alanı satırı eksik; görselde 32,7 m² mevcut.

## Açık farklar

| Kimlik | Kaynak / r01 | Sınıf ve işlem |
|---|---|---|
| F01 | Yaşam alanı 32,7 / 27,55; hol 1,5 / 6,60 m² | Çıkarımda açık alanın en yakın etikete bölündüğü kayıtlı. Mahal sınırı ve alan tanımı karşılaştırılacak; yalnız etiketi değiştirerek kapatılmayacak. |
| F02 | Veranda JPG 15,7; DXF çıkarım etiketi 16,5; r01 18,90 m² | Kaynaklar arası uyuşmazlık ve çıktı farkı. JPG/DXF/SKP kaynak önceliği kanıtla belirlenecek; sessiz seçim yok. |
| F03 | JPG dış ölçüleri 1140 × 836; r01 dönüşü geri alındığında 1139,5 × 835,75 cm | Birim, hassasiyet ve ölçü referansı doğrulanacak. Yuvarlama/tolerans onayı varsayılmayacak. |
| F04 | Eski çıkarımda salon ve çocuk odası pencereleri 62,75 cm, banyo penceresi -80,5 cm merkez farkı bildiriyor | Kaynak DXF ile yeniden ölçülecek; pano ortasına taşıma kaynakla uyum diye sunulmayacak. |
| F05 | Eski DXF çıkarımında iç kapı 80 → 82; giriş 100 → 90 cm | K04 çalışma kabulü, Lokman onayı bekliyor. Kaynak boşluğu, kanat, kasa ve sipariş ölçüsü ayrıştırılmadan düzeltme uygulanmayacak. |
| F06 | Duvarlarda +5 ve +3 cm aks taşıması; iç kapı merkezlerinde 8,25–11,25 cm farklar kayıtlı | Hangi elemanın neden taşındığı belirlenecek; modele özgü düzeltme ile genel kural ayrılacak. |
| F07 | Motor planı 90° döndürmüş; çocuk odası adı YATAK ODASI 3 olmuş | Karşılaştırma kaynak yönüne hizalanacak; dönüş tek başına çizim hatası değildir. Ad eşleme açık tutulacak. |
| F08 | r01 doğrulama passed=true, warnings=[]; extraction.json içinde uyuşmazlıklar var | Motor iç doğrulaması ile kaynak sadakati ayrı kabul kapılarıdır. Açık farklar teslim raporunda görünür olacak. |

## Uygulayıcı ajana görev

1. Güncel depodaki talimatları, model takip kaydını, P9201 revizyonlarını ve onaylı kuralları oku. Başlangıç commitini, kaynak hashlerini, araç ve kural sürümünü kaydet. Eski r01'i ve kabul edilmiş referansları koru.
2. Mevcut çıkarıcıyı ve P9201 verisini kullan. Önce güncel DXF'nin P9201 bölgesini kaynak JPG ile aynı yönde karşılaştır. Kaynak kimliği, birim, alan ve kapı ölçüsü anlamlarını belirle. Kaynakta bulunmayan değerleri pikselden kesin ölçü diye üretme.
3. F01–F08 için eleman kimliği, kaynak değeri, mevcut değer, önerilen değer, dayanak ve durum tablosu oluştur. DXF/JPG çelişkilerini ayrı tut. Belirsiz öğeleri açık bırakırken bağımsız ve kanıtlı düzeltmeleri ilerlet.
4. Kanıtı ve onaylı kuralı bulunan çıkarım hatalarını yalnız P9201 aday revizyonunda düzelt. Ortak motor/çıkarıcı değişikliği gerekirse minimal değişiklik önerisini Claude'a teslim et; ortak dosyaları eşzamanlı değiştirme. Yeni motor veya mimari kurma. K16(a/b) kararını kendin verme.
5. Çıktıyı mevcut motorla üret; DXF'yi yeniden açarak ölçüleri, duvarları, oda ilişkilerini ve 6 pencere/5 kapıyı tek tek doğrula. Adet eşitliğini konum, boyut ve açılma yönünün doğruluğu yerine kullanma. Sadece değişikliğe uygun mevcut testleri çalıştır; kaynak farkı kontrolünü ayrıca raporla.
6. Lokman'a kaynak yönünde ölçülü 2D çizim ve kaynakla karşılaştırma teslim et. PDF ile yapılandırılmış model verisi aynı revizyonu taşısın. Lokman'ın 30.09 ek kararıyla ilk üç modelin teslimine IFC dahildir; ayrıntılı BIM/BOM daha sonra ele alınacak. Malzemeli dış görünüş, etkileşimli döndürme/çatıyı açma, parçaların sırayla oluşma sunumu ve IFC, mevcut Motor–IFC–Blender yoluyla aynı revizyondan ve Claude entegrasyonuyla üretilecek. IFC yeniden açılarak ana ölçüler, elemanlar ve açıklıklar model/2D ile karşılaştırılacak; yalnız dosyanın oluşması kabul değildir.

Dosya sınırı: modelin ayrı çalışma alanı ve mevcut takip kaydının ilgili satırı. `motor/`, `beyin/`, ortak kurallar ve dondurulmuş referanslarda değişiklik doğrudan uygulanmayacak; gerekiyorsa Claude'a incelemeye hazır yama olarak verilecek. İE-02, canlı sistem, dağıtım, ücretli çağrılar, dış veri aktarımı ve silme bu işin kapsamında değil.

## Kuralların durumu

K02 mevcut motorun kural v1.4.3 ve kaydedilmiş DXF doğrulama yolunu tarif ediyor. K04 kapı ölçülerinin Lokman onayını beklediğini, K16 modüle uyarlama/serbest aks seçiminin açık olduğunu söylüyor. Bu iki açık karar onaylı üretim kuralı diye uygulanamaz. Pano sayısı metre değildir; prefabrik kuralları hafif çeliğe taşınmaz. Yükseklik/çatı gibi JPG'de olmayan bilgiler ancak sürümlü ve kapsamı doğrulanmış kuraldan alınabilir; r01'de var olması onay kanıtı değildir.

## Teslim ve kabul

- Yapılandırılmış P9201 model/iş emri verisi, ölçülü 2D PDF ve DXF, üç sunum biçimi (dış görünüş, etkileşimli iç inceleme, sıralı oluşum), aynı revizyona bağlı IFC, kaynak–çıktı fark kaydı, çalıştırılan test sonucu ve kaynak/çıktı hashleri. Ayrıntılı BIM/BOM sonraki aşamada.
- Her F maddesi: düzeltildi ve yeniden ölçüldü / kaynak kararı bekliyor / kapsam dışı gerekçesiyle açık. Bir fark sessizce tolerans içine alınmaz.
- Lokman görsel kabulü, teknik kontrol ve Claude entegrasyonu ayrı alanlardır. Açık kritik kaynak veya ölçü farkı varken kaynakla uyumlu kabulü verilmez.
- Üretime serbest bırakma bu iş emrinin sonucu değildir; gereken teknik değerlendirme ayrıca Ubeydullah'a aittir.
- Geri bildirim kaydı: model + revizyon + eleman + istek + korunacaklar + sınıf (çizim hatası / modele özgü değişiklik / genel kural adayı) + uygulama kanıtı. Modele özgü değişiklik yeni revizyona yazılır; bütün kataloğa yayılmaz.

## İlk sıra ve takip

37 kayıt kapsamda. Öncelik P9201 → P9401 → P9501; üçü de katalogda 3+1 ve 92/94/95 m². P9501 için açıklık kaybı geçmişi ayrıca kontrol edilecek. P1051 (105,6 m², 3+1) yedek adaydır; yaklaşık 90 m² kabul sınırı kararlaştırılmadan eşdeğer sayılmaz. Diğer 33 kayıt dışlanmadı. Üç alternatifin uçtan uca kabulü kalan 34 modelin bitmesini beklemez. Alanların net/brüt/veranda anlamı doğrulanmadan yalnız katalog m²'siyle uygunluk onayı verilmez.

Mevcut sonuç: ilk kaynak incelemesi ve mevcut SKP üzerinden üç sunum biçimi + geometrik IFC4 hazır. Bu çıktı SKP-inceleme-01 adını taşır; düzeltilmiş motor r02 çıktısı değildir. r01 kaynak uyumu kabul edilmedi; ölçülü 2D düzeltmesi, Lokman kabulü ve Claude entegrasyonu bekliyor. Ayrıntılar: `Uc_Model_Sunum/OKU.md`. Ekteki 37 model takip tablosu yerel başlangıç kaydıdır; depoda eşdeğer kayıt bulunursa oraya aktarılır, ikinci kalıcı doğruluk kaydı kurulmaz.
