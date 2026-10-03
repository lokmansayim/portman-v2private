# Çelik yükleme listesi: yöntem ve taslak (3 Ekim 2026)

Lokman, 3 Ekim 12:03: yükleme listesi sistemi kurulacak. Bundan sonraki çelik modellerde model verilecek, liste aynı sistemle dönecek. Kapsam: tek kat çelik, çift katın üst katı ve çatı ailesi. Canlıya alınacak.

Deneme kodu: `deneme/2026-10-03_yukleme/`. Hesapta LLM yok: aynı girdi her zaman aynı listeyi verir. Buradaki tablolar hesap çıktılarından üretilir (`sonuc/tablolar.md`).

## Kaynaklar

1. **Lokman'ın söyledikleri.** 3 Ekim 13:27'de on bir soruya verdiği cevaplar (aşağıda) ve önceki kurallar.
2. **Gerçek yükleme listeleri.** Lokman'ın bağladığı klasördeki çalışma kitapları. Üçü hesap sayfalarıyla okundu. Üçünde de çatı yöntem B ile (tavan omegası, aşık, saçak sacı) hazırlanmış: PortatifEv bugüne kadar çelikte de bu yöntemi uygulamış. Şimdi baz alınan yöntem A için karşılaştırılacak gerçek liste yok.
   - **90 m²**, beşik çatı, OSB üstü metal kiremit, karkas 80 mm (30 Eylül 2025).
   - **62 m²**, kırma çatı, sandviç panel, dış karkas 140 mm, verandalı (19 Eylül 2025). Ç8201'e en yakın örnek.
   - **105 m²**, beşik + cumba çatı, tek kat panel, dış karkas 140 mm (dosya tarihi 26 Kasım 2025; 11 Kasım tarihli önceki sürümüne de bakıldı).
3. **Excel hesaplama motoru** (`CTKBF V1.1`). Lokman, 13:27: "biz Excel'de hesaplama motoru kullanırken…". Sayfaları: müşteri talebi (girdiler), proje detayları, dış ve iç duvar tonajı, çatı tonajı, çatı kaplama malzemesi, pencere, malzemeler (formüller), notlar. Buradan çelik birim ağırlıkları ile listede elle yazılan kalemlerin formülleri alındı. Fiyatlar alınmadı.

Kişi, bayi, müşteri ve personel adları alınmadı. Çalışma kitapları depoda değil; Lokman'ın Mac'inde.

## Lokman'ın cevapları (3 Ekim 13:27) ve uygulanışı

| # | Konu | Cevap (özet) | Uygulama |
|---|---|---|---|
| 1 | Çelik kg | Excel motorundaki gibi: çeliğin et kalınlığı ve sırt kalınlığına göre, ortalama cephe uzunluğundan. Dış cephe (140'lıksa 140) ve iç cephe (80) uzunluğuyla kg verilir. Kirişler ve makaslar yaklaşık bir makas ölçüsünden ayrıca verilecek. İleride Blender eklentisi (şimdi değil). | Duvar kg = duvar boyu × motorun birim ağırlığı. Dikme, kiriş ve makas motorun ortalamasıyla, "geçici" notuyla. |
| 2 | Çatı örtüsü | "Çatı kaplaması" seçenektir: tek kat panel, sandviç panel, OSB + nem bariyeri + kiremit desen sac vb.; ötekiler zamanla verilecek. Hafif çelikte normalde makas arasına tavan paneli, üstüne çatı paneli konur; "ama biz prefabrikte kullandığımız metod olan tavan omegası, aşık, alın sacı ve saçak sacı yöntemini uyguluyoruz". İki varyant var; şimdilik çatı ve tavan panelli yöntem baz. | Çatı yöntemi A; kaplama seçenek. Üç kaplama da hesaplanıyor. |
| 3 | Veranda kolonu ve kirişi | Kaplanıyor. Her projede sırt 80 mm (çelik karkas), genişlik 30 cm. Bu projede verandanın bütün çerçevesi böyle: kirişler yanlarda ve karşıda; altlarında 240 cm, kiriş gibi dikmeler. | Ç8201: dikme 3 × 240 cm, kiriş 12,38 m; kaplama çevreleri 0,76 ve 0,68 m. Çizime işlendi. |
| 4 | Yeşil alçıpan | Doğru: duvarda ıslak hacim; tavanda ıslak hacim ile veranda tavanı. | Hesap değişmedi; kural teyitli. |
| 5 | Köşebent | Kural olarak bina m² ÷ 2,5; 50 ya da 70 olması çok önemli değil. | Ç8201: 33. Gerçek listelerde bunun yaklaşık iki katı var. |
| 6 | Dere inişi | Her köşeye bir; 10 metrelik cephenin ortasına bir daha (14 metrede üç tane konmaz); 82 m²'de toplam 6. | Kural kodda. Ç8201: 6; çatı planında işaretli. |
| 7 | Bindirme, mahyalar | Saçak, mahya ve alın sacında bindirme hep 30 cm (fire dahil); örnek: "saçak sacı L:2800 ise cephe 10 metre ÷ 2,5". Ters mahya: cumbalı çatıda vadi. Özel mahya: ana bina ile veranda çatısının birleşimi. | Mahya (L 2800) ÷ 2,5 → 11. Yöntem B'de saçak ve alın sacı listelerde L 2500 olduğu için ÷ 2,2 (çıkarım). Dere sayılmadı: 20 cm'de kaldı (soru). |
| 8 | Saçak altı | İki yöntem birlikte kullanılmaz; saçak sacı varsa Boardex kaplanmaz. Ç8201 Boardex kaplamalı, çatı ve tavan panelli. | Baz listede saçak sacı yok; saçaklar için Boardex var. |
| 9 | İç duvarda OSB | İçlerde OSB yoksa mutfak dolabı ve TV ünitesi takılırken mukavemet sağlasın diye gönderilen ürün; "salonun bir odası ile mutfağın 1 odasının tüm yüzeyini hesapla". | Ç8201: Yaşam Alanı'nın bütün duvar yüzeyi 42,5 m² → 15 levha. Okuma teyit bekliyor. |
| 10 | İç kapı | Boşluk en 90, yükseklik 214; kasa sağda, solda, üstte 5'er cm; altta 5 cm şap ve 2–3 cm parke; kanat 200'e düşer. | Dört iç kapı da 90 × 214 (banyo dahil); kanat 200. Kanat eni 80: listelerdeki "80'lik kanat"tan ve 90 − 2 × 5'ten. |
| 11 | Vida, boya, elektrik, tesisat | Bütün paketlerde var; bayilerle paylaşılan katalog ve fiyat listelerinde de. Bayi kuralı olarak ele alınacak (örnek: bir bayi için çelikte standart ne, bir başkası için prefabrikte standart ne); canlıda bayi numaraları birincil anahtar, liste mesajı atana göre. | Dört grup varsayılan olarak listede; bayi kuralıyla kapatılır. |

## Listenin grupları ve bayi kuralı

105 m² listedeki ve Excel motorundaki sırayla: Çelik panel · Metal aksam · Dış cephe kaplama · İç cephe kaplama · Çatı kaplamaları · Dere · Kapı ve pencere · Elektrik · Vida · Sıhhi tesisat · Boya.

- Bir grubun listeye girip girmeyeceği bayinin standardına bağlıdır. Örnek: 90 m² gerçek listede vida, elektrik ve sıhhi tesisat yok; 62 ve 105 m² listelerde var.
- Denemede: `bayi_kurallari_ornek.json` ve `yukleme.py --bayi <anahtar>`. Anahtar canlıda bayinin telefon numarası olacak; dosyada gerçek numara ya da ad yok. Kural grupları açıp kapatır; boya kovası ve vitrifiyeyi dahil eder ya da etmez; çatı yöntemini ve kaplamasını bayinin standardına çevirir.
- Hangi bayinin standardının ne olduğu bilinmiyor; sorulacak.

## Çelik: birim ağırlıklar (Excel motorundan)

Motor, gerçek projelerin tonajını duvar uzunluğuna bölerek ortalama almış (kat yüksekliği 2,70 m):

| Profil (sırt × başlık × et) | Dış duvar kg/m | İç duvar kg/m | Dikme kg/m | Kiriş kg/m |
|---|---|---|---|---|
| 80 × 45 × 0,8 | — | 13,00 | — | — |
| 80 × 45 × 1,2 | 20,33 | 19,75 | 6,42 | 6,55 |
| 140 × 45 × 0,8 | 18,20 | — | — | — |
| 140 × 45 × 1,2 | 29,04 | — | 8,26 | 8,27 |
| 140 × 45 × 1,5 | — | — | — | 11,04 |

Çatı çeliği (80 × 45 × 0,8), saçak dahil çatı planının m²'si başına: beşik 5,70 · dört omuz 7,55 · beşik + cumba 5,65 · beşik + 2 cumba 6,08 kg/m². Dört omuz değeri üç projenin ortalaması (9,46 · 6,86 · 6,33).

- Hesap: duvar kg = duvar boyu × birim ağırlık. Dış duvar boyu = dış çevre; iç duvar boyu plandan (iç duvarların toplam boyu).
- Motor girdi olarak yalnız dikdörtgenin kenarlarını ve bölme sayısını alıyor; iç duvar boyunu (uzun + kısa) × (0,1543 × bölme sayısı + 0,756) diye tahmin ediyor. Planımız olduğu için gerçek boylar kullanıldı.
- Dikme = adet × 2,40 m × birim ağırlık; kiriş = boy × birim ağırlık; çatı = çatı planı × kg/m². Bunlar geçici: Lokman kiriş ve makasları bir makas ölçüsünden verecek.
- Yöntem A'nın tavan paneli ve çatı paneli için motorda değer yok ve ölçüleri bilinmiyor; listede alanları yazılı, kg'ları boş (sorulacak).

### Üç gerçek listeyle karşılaştırma (kg)

| Çelik (kg) | 90 m²: hesap / liste / fark | 62 m²: hesap / liste / fark | 105 m²: hesap / liste / fark |
|---|---|---|---|
| Dış duvar | — | 527 / 577 / −%8,6 | 965 / 1055 / −%8,5 |
| İç duvar | — | 157 / 180 / −%12,8 | 382 / 410 / −%6,9 |
| Duvar toplamı | 1282 / 1345 / −%4,7 | 684 / 757 / −%9,6 | 1347 / 1465 / −%8,1 |
| Kiriş ve kolon | 88 / 100 / −%11,7 | 145 / 161 / −%9,9 | — |
| Çatı | 590 / 535 / +%10,3 | 555 / 426 / +%30,4 | — |
| Toplam | 1990 / 1980 / +%0,5 | 1415 / 1364 / +%3,7 | — |

- Toplamlar %0,5 ve %3,7 farkla tutuyor; ama parçalar tek tek tutmuyor: duvarlar %5–13 eksik, çatı %10–30 fazla. Toplamın tutması, farkların birbirini götürmesinden.
- 140 mm dış karkaslı iki listede dış duvarların çoğu 0,8 mm, üçer paneli 1,2 mm; hesapta hepsi 0,8 alındığı için dış duvar %8,5 ve %8,6 eksik çıkıyor. O iki listede dış duvar 19,9 kg/m'ye geliyor (577 kg ÷ 28,98 m ve 1055 kg ÷ 53,04 m).

### Et kalınlığı (teyit bekliyor)

| Liste | Dış karkas | Dış duvar | İç duvar |
|---|---|---|---|
| 90 m² | 80 mm | hepsi 1,2 mm | 1,2 mm |
| 62 m² | 140 mm | 3 panel 1,2 mm · 7 panel 0,8 mm | 0,8 mm |
| 105 m² | 140 mm | 3 panel 1,2 mm · 20 panel 0,8 mm | 0,8 mm |

Hesapta buna göre varsayıldı: dış karkas 80 mm ise duvarlar 1,2 mm; 140 mm ise dış ve iç duvarlar 0,8 mm. Bu yüzden Ç8201'de dış 140 seçeneği baz paketten daha hafif çıkıyor. Kalınlığın neye göre seçildiği bilinmiyor.

| Ç8201 | Baz (dış 80) | Dış 140 |
|---|---|---|
| Dış duvar (32,0 m) | 80 × 1,2: 651 kg | 140 × 0,8: 582 kg · 140 × 1,2: 929 kg · listelerdeki karışımla (19,9 kg/m): 637 kg |
| İç duvar | 19,68 m · 80 × 1,2: 389 kg · 80 × 0,8: 256 kg | 19,38 m · 80 × 0,8: 252 kg · 80 × 1,2: 383 kg |

## Öteki kurallar

Durum: `lokman` Lokman söyledi · `excel` yükleme listesi çalışma kitabındaki formül · `motor` Excel motorundaki formül ya da not · `uydurma` gerçek listelerdeki adedi tutturan kural · `varsayim` Claude'un varsayımı · `soru` kural bilinmiyor · `bekliyor` değer henüz yok (sorulacak ya da paftadan gelecek) · `model` modeldeki açıklıklardan · `liste` örnekte gerçek listeden alınan sayı. Katsayılar ve kaynakları: `deneme/2026-10-03_yukleme/kurallar.json`.

- **Terim.** PortatifEv listelerinde "alın" beşik çatının kalkan yüzüdür (alın sacı, çatı alnı). Saçak ucundaki düşey yüz (topuk + çatı panelinin düşey ölçüsü; Lokman'ın deyişiyle "saçak genişliği") burada "saçak yüzü" diye geçer; önceki kayıtlarda ve kodun içinde "alın" denmişti.
- **Dış cephe** (excel). Net alan = çevre × kat yüksekliği + dikme ve kiriş kaplaması (adet × çevre × boy) + çatı alnı (kalkan) alanları − kapı ve pencere boşlukları. Boardex = net × 1,15 ÷ (1,2 × 2,4). Motorda ve bir hesap sayfasında zayiat %8 yazıyor; ama üç listedeki adetlere %15 yakın düşüyor (hesap / liste: 32 / 32, 45 / 46, 52 / 51); %8 ile 2–3 levha eksik kalıyor.
- **İç cephe** (excel). Odalar "beyaz" ve "yeşil" diye ayrılır. Oda oda: iç çevre × kat yüksekliği − o odadaki boşluklar. Alçıpan = net × 1,05 ÷ (1,2 × 2,5). Tavan alçıpanı = tavan alanı × 1,05 ÷ 3,0.
- **Kapı boşlukları.** İç kapı 0,90 × 2,14 (lokman; çalışma kitaplarında da aynı). Dış kapı 0,95 × 2,10 (excel: 90 ve 105 m² listeler; 62 m² listede 0,95 × 2,00).
- **Duvar izolasyonu** (uydurma). Dış duvar × kat sayısı (80 mm karkasta 1, 140 mm'de 2) + iç duvar − boşluklar; ÷ 8,64. 105 m² listenin hesap sayfasında "dış × 2" diye yazıyor.
- **Çatı kaplaması** (uydurma). Panel ve sac adedi = çatı yüzeyi × 1,10 ÷ (boy × kapatma genişliği). Kapatma: sandviç panel 100, tek kat panel 87, kiremit desen sac 110 cm. Motorun notu: gerçek adet AutoCAD'de yerleşim yapılarak bulunur.
- **Mahya** (lokman). Mahya hattı ÷ (2,8 − 0,30). Kırma çatıda hat = tepe + dört kırma.
- **Dere** (motor). Metal dere = saçak boyu ÷ (4,0 − 0,20); Lokman'ın 30 cm kuralında dere sayılmadı. Kelepçe = dere × 8. İniş başına: boru 1, aparat 1, açık dirsek 2, kapalı dirsek 1, iniş kelepçesi 2. İniş sayısı Lokman'ın kuralıyla.
- **Köşebent** (lokman). Bina m² ÷ 2,5.
- **Saçak altı.** Yöntem A'da Boardex (lokman). Adet formülü 62 m² listeden (uydurma): saçak boyu × 0,30 × 1,15 ÷ 2,88. Saçak yüzü de Boardex sayıldı (varsayım): saçak ucu çevresi × yüz yüksekliği × 1,15 ÷ 2,88.
- **Yöntem B kalemleri.** Saçak sacı ve alın sacı = boy ÷ (2,5 − 0,30): 30 cm bindirme Lokman'dan; parça boyu L 2500 listelerden (÷ 2,2 çıkarım). Saçak omegası, tavan omegası ve aşık kuralları iki listeye uydurulmuştu; değişmedi.
- **Vida, boya, tesisat** (motor ve excel). Alçıpan vidası = levha × 40; OSB vidası = OSB × 40 + priz × 4 + saçak sacı × 4 + dere kelepçesi × 3; pencere vidası = pencere × 20; trapez (5,5 × 25) = aşık × 10 + omega × 10 ya da 6 + çelik panel × 10 + köşebent × 6; panel vidası = panel boyu ÷ 200 × adet; çelik dübel = duvar paneli × 2; uçlar ve kesme taşı = m² ÷ 15; inox taş = m² ÷ 10; RYSB = m² × 7,5. Boya: 100 m²'ye dış 2, iç 2, tavan 1, astar 1 kova; dayson = m² × 0,06; köpük 2; mastik = pencere adedi. Tesisat: ıslak hacim başına 6 boru, 15 dirsek, 12 kulaklı dirsek, 6 düz T, 15 maşon, 6 iç dişli T, 3 atlama parçası; vitrifiye dahilse duşakabin, klozet, dolap ve batarya grubu.
- **Elektrik.** Duy, glop, anahtar, priz ve sigorta sayıları motorda "montaj paftasından sayılır" diye geçiyor. Sayım olmadan hesaplanamıyor; yalnız sayıma bağlı olmayan kalemler (besleme kablosu, zil, sigorta kutusu, kaçak akım rölesi, izole bant) hesaplanıyor.

## Üç gerçek listeyle karşılaştırma (adet)

Özet: 90 m²: 29 kalemin 15 tanesinde adet aynı; 62 m²: 41 kalemin 30 tanesinde adet aynı; 105 m²: 49 kalemin 31 tanesinde adet aynı. Toplam 119 karşılaştırmanın 76 tanesi aynı.

Tam tablo: `deneme/2026-10-03_yukleme/sonuc/tablolar.md`. Adedi doğrudan listeden alınan satırlar karşılaştırmaya girmedi: dere kapağı, elektrik sayımı ve 105 m² listede iniş sayısı ile ona bağlı dört satır. 90 ve 62 m² listelerde iniş sayısı Lokman'ın kuralından hesaplandı (6; listelerde 7): bu tek fark beş satırda birden görünüyor, yani 43 farkın 10'u oradan.

**Bu bir sınama değil.** `uydurma` kuralların katsayıları 90 ve 62 m² listelere bakılarak seçilmişti; o listelerle tutması kanıt sayılmaz. 105 m² liste levha, çatı ve dere kurallarından sonra eklendi; ama vida, boya, elektrik ve tesisat formülleri onunla aynı anda eklendi, kesme taşı katsayısı 62 ve 105 m² listelere bakılarak seçildi. Onun da çatı planı yok: saçak, mahya, alın boyları ve elektrik sayımı listede yazan değerlerdir. Üç örnekte de çatı uzunlukları ve tavan alanları listelerdeki değerlerdir. Yani hiçbiri kör sınama değil; yöntem A için ise hiç gerçek liste yok.

Adedi tutmayan kalemler:

| Grup | Kalem | Kural | Durum | 90 m²: hesap / liste | 62 m²: hesap / liste | 105 m²: hesap / liste |
|---|---|---|---|---|---|---|
| Metal aksam | Saçak sacı (30'luk) | saçak boyu ÷ (2,5 − 0,30 bindirme) | lokman | 15 / 14 ✗ | 18 / 17 ✗ | 18 / 18 |
| Metal aksam | Alın sacı (30'luk) | alın boyu ÷ (2,5 − 0,30 bindirme) | lokman | 8 / 9 ✗ | — | 8 / 8 |
| Metal aksam | Tavan omegası (60'lık) | tavan alanı ÷ 0,60 ÷ 3,75 | uydurma | 37 / 40 ✗ | 26 / 26 | 42 / 44 ✗ |
| Metal aksam | Aşık | eğim boyunca 60 cm aralıkla sıralar + mahya aşığı; kırmada her sıra çatıyı dolanır; × 1,05 ÷ 4,2 | uydurma | 56 / 57 ✗ | 41 / 41 | — |
| Metal aksam | Köşebent | bina m² ÷ 2,5 | lokman | 36 / 70 ✗ | 25 / 50 ✗ | 42 / 85 ✗ |
| Metal aksam | Saçaklar için Boardex | saçak boyu × saçak eni × 1,15 ÷ 2,88 | uydurma | — | 5 / 5 | 8 / 7 ✗ |
| Dış cephe kaplama | Dış cephe Boardex | (çevre × yükseklik + kolon/kiriş kaplaması + çatı alnı (kalkan) − boşluklar) × 1,15 ÷ 2,88 | excel | 45 / 46 ✗ | 32 / 32 | 52 / 51 ✗ |
| İç cephe kaplama | Duvar alçıpan beyaz | oda oda: (iç çevre × yükseklik − o odadaki boşluklar) toplamı × 1,05 ÷ 3,0 | excel | 66 / 67 ✗ | 32 / 32 | 78 / 79 ✗ |
| İç cephe kaplama | Duvar alçıpan yeşil | oda oda: (iç çevre × yükseklik − o odadaki boşluklar) toplamı × 1,05 ÷ 3,0; yeşil = ıslak hacimler | excel | 9 / 9 | 7 / 8 ✗ | 13 / 14 ✗ |
| İç cephe kaplama | Tavan alçıpan yeşil | tavan alanı × 1,05 ÷ 3,0; yeşil = ıslak hacim + veranda tavanı | lokman | 5 / 6 ✗ | 7 / 7 | 3 / 3 |
| İç cephe kaplama | OSB 9 mm (duvar) | listede yazan alan × 1,05 ÷ 2,98; alanın nasıl seçildiği listede yazmıyor | excel | 13 / 13 | — | 14 / 15 ✗ |
| İç cephe kaplama | Duvar izolasyonu | dış duvar × kat sayısı (80 mm karkasta 1, 140 mm'de 2) + iç duvar − boşluklar; ÷ 8,64 | uydurma | 18 / 18 | 19 / 19 | 39 / 38 ✗ |
| Dere | Dere iniş borusu | 4 köşe + 2 orta (10 m ve üzeri cepheler) | lokman | 6 / 7 ✗ | 6 / 7 ✗ | — |
| Dere | Dere iniş aparatı | iniş sayısı × 1 | motor | 6 / 7 ✗ | 6 / 7 ✗ | — |
| Dere | Açık dirsek | iniş sayısı × 2 | motor | 12 / 14 ✗ | 12 / 14 ✗ | — |
| Dere | Kapalı dirsek | iniş sayısı × 1 | motor | 6 / 7 ✗ | 6 / 7 ✗ | — |
| Dere | İniş kelepçesi | iniş sayısı × 2 | motor | 12 / 14 ✗ | 12 / 14 ✗ | — |
| Boya | Silikonize mastik | pencere adedi | uydurma | 6 / 8 ✗ | 6 / 8 ✗ | 8 / 8 |
| Boya | Dayson | bina m² × 0,06 | motor | 6 / 6 | 4 / 4 | 7 / 6 ✗ |
| Vida | RYSB pul başlı (3,9 × 32) | bina m² × 7,5 | motor | — | 465 / 400 ✗ | 788 / 500 ✗ |
| Vida | Alçıpan vidası (3,5 × 35) | alçıpan ve Boardex levha sayısı × 40; 250'ye yuvarlandı | excel | — | 4000 / 4000 | 7500 / 8500 ✗ |
| Vida | OSB ve yalıpan vidası (3,9 × 32) | OSB levha × 40 + priz × 4 + saçak sacı × 4 + dere kelepçesi × 3; 500'e yuvarlandı | motor | — | 3500 / 3500 | 1000 / 1500 ✗ |
| Vida | Pencere vidası (4,8 × 70) | pencere sayısı × 20 | excel | — | 120 / 120 | 160 / 180 ✗ |
| Vida | Trapez vida (5,5 × 110; sandviç panel) | panel boyu (mm) ÷ 200 × panel adedi; 250'ye yuvarlandı | motor | — | 500 / 750 ✗ | — |
| Vida | Çelik dübel (klipsli) | duvar paneli adedi × 2 | motor | — | 32 / 32 | 72 / 80 ✗ |
| Vida | Şase pul | çelik dübel adedi kadar | motor | — | 32 / 32 | 72 / 80 ✗ |
| Vida | İnox taş | bina m² ÷ 10 | excel | — | 7 / 7 | 11 / 10 ✗ |
| Elektrik | Buat kasa | anahtar + priz + oda sayısı | motor | — | — | 40 / 37 ✗ |
| Elektrik | İzole bant | bina m² × 0,06 | motor | — | — | 7 / 3 ✗ |

Okuma:

- **Köşebent.** Kural (m² ÷ 2,5) üç listede de yaklaşık yarısını veriyor. 105 m² listenin hesap sayfasında oda çevreleri toplamı ÷ 2,5 = 43,7 yazıyor, listede 85 var.
- **İniş sayısı.** Kural 90 ve 62 m² projelerde 6 veriyor (dört köşe + iki uzun cephe); listelerde 7. 105 m² listede 10; cephe ölçüleri olmadığı için kural hesaplanmadı.
- **Saçak sacı.** L 2500 parça ve 30 cm bindirme (÷ 2,2) en yeni listeyi (Kasım 2025) tutturuyor; Eylül 2025 listelerinde birer fazla veriyor. Excel motorundaki 20 cm (÷ 2,3) üç listeyi de tutturuyor (14, 17, 18).
- **İki yöntem aynı listede.** 62 ve 105 m² listelerde hem saçak sacı hem saçaklar için Boardex var; kurala göre birlikte olmaz. 105 m² listede saçak altı 0,50 m alınmış (19,6 m² = 39,2 × 0,50).
- **Levhalar** (Boardex, alçıpan, OSB, izolasyon). Farklar 1 adet: listelerde yuvarlama bir yukarı, bir en yakına yapılmış. 105 m² listede beyaz duvar alçıpanındaki fark çalışma kitabındaki bir hücre hatasından: bir odada iki iç kapı boşluğu (3,85 m²) yerine 2 m² düşülmüş.
- **Sarf kalemleri** (RYSB, alçıpan vidası, izole bant, mastik). Motorun m² formülleri listelerdeki sayıları vermiyor. Mastik üç listede de 8.
- **Tutanlar.** Beyaz tavan alçıpanı, mahya, dere, dere kelepçesi, sıhhi tesisat (105 m²'de yedi kalemin yedisi), uçlar ve kesme taşı.

## Ç8201 taslak

Girdi: `deneme/2026-10-03_yukleme/sonuc/C8201_girdi.json` (geometri Yapı Tanımı taslağından; varsayımlar dosyanın içinde). Çatı yöntemi A; çatı kaplaması örnek olarak sandviç panel. "Dış 140" sütunu yalnız değişenleri gösterir. Bu modelin gerçek listesi yok: taslak yalnız kurallardan çıkıyor.

Not: saçaklar için Boardex'te alan liste yöntemiyle saçak boyu × 0,30 = 11,8 m² (köşeler iki kez sayılır); gerçek saçak altı 11,4 m². İkisi de 5 levha.

| Grup | Kalem | Boyut | Baz | Dış 140 | Ölçü (baz) | kg (baz) | Durum |
|---|---|---|---|---|---|---|---|
| Çelik panel | Dış cephe duvar panelleri | 80 × 45 × 1,2 | 8 | 140 × 45 × 0,8: 582 kg | 32,0 m | 651 | motor |
| Çelik panel | İç cephe duvar panelleri | 80 × 45 × 1,2 | 6 | 80 × 45 × 0,8: 252 kg | 19,7 m | 389 | motor |
| Çelik panel | Veranda dikmeleri (kolon paneli) | 80 × 45 × 1,2 | 3 | aynı | 7,2 m | 46 | motor |
| Çelik panel | Veranda kirişleri (kiriş paneli) | 80 × 45 × 1,2 | 4 | aynı | 12,4 m | 81 | motor |
| Çelik panel | Çatı makas panelleri | 80 × 45 × 0,8 | 25 | aynı | 93,5 m² | 706 | motor |
| Çelik panel | Tavan paneli (makas arası) | roll form çelik |  | 74,8 m² | 76,7 m² |  | bekliyor |
| Çelik panel | Çatı paneli (makas üstü, sırt 80 mm) | roll form çelik |  | aynı | 98,4 m² |  | bekliyor |
| Çelik panel | Boy C profil | 80 × 45 × 0,8 | 3 | aynı |  | 15 | motor |
| Çelik panel | Boy C profil | 80 × 45 × 1,2 | 3 | aynı |  | 15 | motor |
| Çelik panel | Toplam (adedi ve kg'ı bilinenler) |  | 52 | 1697 kg |  | 1902 | motor |
| Metal aksam | Saçak omegası | L 2500 |  | aynı | 39,3 m |  | soru |
| Metal aksam | Saçaklar için Boardex | 1200 × 2400 | 5 | aynı | 11,8 m² |  | uydurma |
| Metal aksam | Saçak yüzü için Boardex | 1200 × 2400 | 3 | aynı | 7,2 m² |  | varsayim |
| Metal aksam | Köşebent | L 2500 | 33 | aynı | 82,0 m² |  | lokman |
| Dış cephe kaplama | Dış cephe Boardex | 1200 × 2400 | 33 | aynı | 80,7 m² |  | excel |
| İç cephe kaplama | Duvar alçıpan beyaz | 1200 × 2500 | 47 | 46 | 132,8 m² |  | excel |
| İç cephe kaplama | Duvar alçıpan yeşil | 1200 × 2500 | 8 | aynı | 20,4 m² |  | excel |
| İç cephe kaplama | Tavan alçıpan beyaz | 1200 × 2500 | 19 | aynı | 54,1 m² |  | motor |
| İç cephe kaplama | Tavan alçıpan yeşil | 1200 × 2500 | 8 | aynı | 22,6 m² |  | lokman |
| İç cephe kaplama | OSB (TV ve mutfak dolabı arkası takviyesi) | 1220 × 2440 | 15 | aynı | 42,5 m² |  | lokman |
| İç cephe kaplama | Duvar izolasyonu | paket 8,64 m² | 13 | 23 | 112,2 m² |  | uydurma |
| Çatı kaplamaları | Sandviç panel | L 4300 · 100 cm kapatır | 26 | aynı | 98,4 m² |  | uydurma |
| Çatı kaplamaları | Metal kiremit mahyası | L 2800 | 11 | aynı | 27,0 m |  | lokman |
| Çatı kaplamaları | Sandviç panel kapaması | L 2500 | 18 | aynı | 39,3 m |  | uydurma |
| Çatı kaplamaları | Çatı şiltesi 80 mm | 9,6 m²/adet | 10 | aynı | 88,9 m² |  | uydurma |
| Dere | Metal dere | L 4000 | 11 | aynı | 39,3 m |  | motor |
| Dere | Dere iniş borusu | L 3000 | 6 | aynı |  |  | lokman |
| Dere | Dere iniş aparatı | adet | 6 | aynı |  |  | motor |
| Dere | Açık dirsek | adet | 12 | aynı |  |  | motor |
| Dere | Kapalı dirsek | adet | 6 | aynı |  |  | motor |
| Dere | İniş kelepçesi | adet | 12 | aynı |  |  | motor |
| Dere | Dere kelepçesi | adet | 88 | aynı |  |  | motor |
| Kapı ve pencere | Melamin kapı (80'lik kanat) | 90 × 214 | 4 | aynı |  |  | lokman |
| Kapı ve pencere | Kompozit çelik kapı | 90 × 210 | 1 | aynı |  |  | model |
| Kapı ve pencere | PVC pencere | 120/180 | 3 | aynı |  |  | model |
| Kapı ve pencere | PVC vasistas | 60/40 | 1 | aynı |  |  | model |
| Kapı ve pencere | PVC pencere | 120/100 | 1 | aynı |  |  | model |
| Kapı ve pencere | PVC pencere | 180/180 | 3 | aynı |  |  | model |
| Elektrik | Duy, glop, ampul, anahtar, priz, sigorta, buat ve NYM kablolar | adet / metre |  | aynı |  |  | bekliyor |
| Elektrik | Uydu kablo | metre | 25 | aynı |  |  | motor |
| Elektrik | Besleme kablosu (sigorta kutuları arası) | metre | 5 | aynı |  |  | motor |
| Elektrik | Besleme kablo borusu | metre | 5 | aynı |  |  | motor |
| Elektrik | Zil | adet | 1 | aynı |  |  | motor |
| Elektrik | Sigorta kutusu (12'li) | adet | 1 | aynı |  |  | motor |
| Elektrik | İzole bant | adet | 5 | aynı | 82,0 m² |  | motor |
| Elektrik | Kaçak akım rölesi | adet | 1 | aynı |  |  | motor |
| Vida | RYSB pul başlı (3,9 × 32) | adet | 615 | aynı | 82,0 m² |  | motor |
| Vida | Alçıpan vidası (3,5 × 35) | adet | 5000 | aynı | 123,0 levha |  | excel |
| Vida | OSB ve yalıpan vidası (3,9 × 32) | adet | 1000 | aynı | 864,0 vida |  | motor |
| Vida | Pencere vidası (4,8 × 70) | adet | 160 | aynı | 8,0 pencere |  | excel |
| Vida | Trapez vida (5,5 × 25) | adet | 750 | aynı | 718,0 vida |  | excel |
| Vida | Trapez vida (5,5 × 60) | adet | 250 | aynı | 205,0 vida |  | motor |
| Vida | Trapez vida (5,5 × 110; sandviç panel) | adet | 750 | aynı | 559,0 vida |  | motor |
| Vida | Çelik dübel (klipsli) | adet | 28 | aynı | 14,0 panel |  | motor |
| Vida | Şase pul | adet | 28 | aynı | 14,0 panel |  | motor |
| Vida | 8'lik trapez uç | adet | 6 | aynı | 82,0 m² |  | motor |
| Vida | PH2 uç | adet | 6 | aynı | 82,0 m² |  | motor |
| Vida | 230'luk kesme taşı | adet | 6 | aynı | 82,0 m² |  | uydurma |
| Vida | İnox taş | adet | 9 | aynı | 82,0 m² |  | excel |
| Vida | Çırpı ipi | adet | 1 | aynı |  |  | motor |
| Sıhhi tesisat | Temiz su borusu | L 4000 | 6 | aynı | 1,0 ıslak hacim |  | motor |
| Sıhhi tesisat | Normal dirsek 20 mm | adet | 15 | aynı | 1,0 ıslak hacim |  | motor |
| Sıhhi tesisat | Kulaklı dirsek 20 mm | adet | 12 | aynı | 1,0 ıslak hacim |  | motor |
| Sıhhi tesisat | Düz T 20 mm | adet | 6 | aynı | 1,0 ıslak hacim |  | motor |
| Sıhhi tesisat | Maşon 20 mm | adet | 15 | aynı | 1,0 ıslak hacim |  | motor |
| Sıhhi tesisat | İç dişli T 20 mm | adet | 6 | aynı | 1,0 ıslak hacim |  | motor |
| Sıhhi tesisat | Atlama parçası (yarım parmak) | adet | 3 | aynı | 1,0 ıslak hacim |  | motor |
| Sıhhi tesisat | Duşakabin (90 × 90) | takım | 1 | aynı | 1,0 ıslak hacim |  | motor |
| Sıhhi tesisat | Klozet | takım | 1 | aynı | 1,0 ıslak hacim |  | motor |
| Sıhhi tesisat | Banyo dolabı | takım | 1 | aynı | 1,0 ıslak hacim |  | motor |
| Sıhhi tesisat | Banyo batarya grubu | takım | 1 | aynı | 1,0 ıslak hacim |  | motor |
| Boya | Dış cephe boyası | kova 17,5 kg | 2 | aynı | 82,0 m² |  | motor |
| Boya | İç cephe boyası | kova 17,5 kg | 2 | aynı | 82,0 m² |  | motor |
| Boya | Tavan boyası | kova 17,5 kg | 1 | aynı | 82,0 m² |  | motor |
| Boya | Astar | kova 17,5 kg | 1 | aynı | 82,0 m² |  | motor |
| Boya | Silikonize mastik | adet | 8 | aynı | 8,0 pencere |  | uydurma |
| Boya | Dayson | adet | 5 | aynı | 82,0 m² |  | motor |
| Boya | Poliüretan köpük | adet | 2 | aynı |  |  | motor |

### Çatı kaplaması seçenekleri

Baz paketin kaplaması söylenmedi. Üç seçenekte değişen kalemler:

| Seçenek | Kalem | Boyut | Adet | Durum |
|---|---|---|---|---|
| Sandviç panel | Sandviç panel | L 4300 · 100 cm kapatır | 26 | uydurma |
| Sandviç panel | Metal kiremit mahyası | L 2800 | 11 | lokman |
| Sandviç panel | Sandviç panel kapaması | L 2500 | 18 | uydurma |
| Sandviç panel | Çatı şiltesi 80 mm | 9,6 m²/adet | 10 | uydurma |
| Sandviç panel | OSB ve yalıpan vidası (3,9 × 32) | adet | 1000 | motor |
| Sandviç panel | Trapez vida (5,5 × 60) | adet | 250 | motor |
| Sandviç panel | Trapez vida (5,5 × 110; sandviç panel) | adet | 750 | motor |
| Tek kat panel | Tek kat panel | L 4300 · 87 cm kapatır | 29 | uydurma |
| Tek kat panel | Metal kiremit mahyası | L 2800 | 11 | lokman |
| Tek kat panel | Tek kat panel kapaması | L 2500 | 18 | uydurma |
| Tek kat panel | Çatı şiltesi 80 mm | 9,6 m²/adet | 10 | uydurma |
| Tek kat panel | OSB ve yalıpan vidası (3,9 × 32) | adet | 1000 | motor |
| Tek kat panel | Trapez vida (5,5 × 60) | adet | 250 | motor |
| Tek kat panel | Trapez vida (5,5 × 76; tek kat panel) | adet | 750 | motor |
| OSB + nem bariyeri + kiremit desen sac | Çatı OSB | 1220 × 2440 | 35 | uydurma |
| OSB + nem bariyeri + kiremit desen sac | Nem bariyeri | m² | 105 | motor |
| OSB + nem bariyeri + kiremit desen sac | Metal kiremit (kiremit desen sac) | L 4300 · 110 cm kapatır | 23 | uydurma |
| OSB + nem bariyeri + kiremit desen sac | Metal kiremit mahyası | L 2800 | 11 | lokman |
| OSB + nem bariyeri + kiremit desen sac | OSB mahyası | L 2800 | 11 | lokman |
| OSB + nem bariyeri + kiremit desen sac | Çatı şiltesi 80 mm | 9,6 m²/adet | 10 | uydurma |
| OSB + nem bariyeri + kiremit desen sac | OSB ve yalıpan vidası (3,9 × 32) | adet | 2500 | motor |
| OSB + nem bariyeri + kiremit desen sac | Trapez vida (5,5 × 60) | adet | 750 | motor |

### Aynı model yöntem B ile

Bayi kuralı çatıyı yöntem B'ye çevirirse (`--bayi ORNEK-BAYI-3`; çıktı `sonuc/C8201_yontem_B.md`): tavan ve çatı paneli ile saçak altı ve saçak yüzü Boardex'i çıkar; saçak sacı 18, saçak omegası 18, tavan omegası 35, aşık 49 girer. Trapez vida 1750 olur.

## Açık sorular

1. **Et kalınlığı.** 80 mm karkasta 1,2 mm, 140 mm'de 0,8 mm (birkaç panel 1,2) mi? Neye göre seçiliyor?
2. **Yöntem A.** Tavan panelinin ve çatı panelinin ölçüsü, adedi, kg'ı. Saçak omegası gerekiyor mu? Saçak yüzü (topuk + panel, 18,4 cm) Boardex'le mi kaplanıyor?
3. **Baz paketin çatı kaplaması** hangisi?
4. **OSB takviyesi.** "Salonun bir odası ile mutfağın 1 odasının tüm yüzeyi": Ç8201'de Yaşam Alanı'nın bütün duvarı alındı (42,5 m², 15 levha). Gerçek listelerde 35,1 m² (90 m² proje) ve 39,3 m² (105 m² proje) var; kalemin adı "TV, klima ve mutfak dolabı arkası". O projelerde salon, mutfak ve holün olduğu mahalin bütün duvarı 71,8 ve 111,9 m². Bütün mahal mi, yalnız dolap ve TV duvarları mı?
5. **Köşebent.** m² ÷ 2,5 gerçek listelerin yarısını veriyor. Kural iki katı mı olmalı?
6. **Bindirme.** Örnekte saçak sacı L 2800; listelerde L 2500. Saçak sacının boyu hangisi? Eylül 2025 listeleri 20 cm ile tutuyor. Derede bindirme de 30 cm mi (motorda 20 cm)?
7. **İniş sayısı.** İki gerçek listede kuraldan bir fazla (7). Neden?
8. **Elektrik.** Sayılar her modelde paftadan mı gelecek, oda başına bir kural mı olacak?
9. **Dış kapı.** Katalog çiziminde 100 cm; listelerde boşluk 95 × 210 (bir listede 95 × 200), kapı 90 × 210.
10. **Veranda dikmeleri.** Sayısı ve yeri neye göre belirleniyor?
11. **Kalınlıklar.** Boardex: 2 Ekim'de 12,5 mm denildi; listelerde ve motorda 8 mm. OSB: listelerde 9 mm; motorda ve 2 Ekim kaydında 11 mm.
12. **Zayiat.** Boardex %15 mi, %8 mi? OSB %5 mi, %15 mi (105 m² listede %15)? Alçıpan %5.
13. **İki yöntem aynı listede.** 62 ve 105 m² listelerde hem saçak sacı hem saçaklar için Boardex var. O Boardex nereye gidiyor?
14. **Yöntem B.** Tavan omegası ve aşık aralığı 60 cm mi (sandviç panelde de)?
15. **Bayi standartları.** Hangi bayide hangi gruplar, hangi çatı yöntemi ve kaplaması standart?

## Canlıya alırken (öneri; ayrı onay gerekir)

- Kurallar veridir: `kurallar.json`'daki her değer kaynağı ve durumuyla bir PostgreSQL tablosuna taşınır; kural değişince kod değişmez.
- Bayi kuralı: bayinin telefon numarası birincil anahtar; karşısında standardı (listeye giren gruplar, çatı yöntemi, çatı kaplaması, paket). Liste, mesajı atan bayinin standardına göre kurulur.
- Hesap deterministik bir modüldür; LLM yalnız talebi anlar (K05).
- Bunların hiçbiri yapılmadı: sunucu ve canlı değişiklik Lokman'ın ayrı onayıyla yapılır.
