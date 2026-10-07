# KT-01 · kör test kıyası

Gerçek yükleme listesinin adetli her satırı, kendi listelerimizle. Tablo `kiyas.py` ile üretilir; elle düzeltilmez. Farkların sınıfı ve açıklaması `kiyas_farklar.json` dosyasındadır; sayımlar koddan.

"Aynı" yalnız adedin aynı olmasıdır. Profil, kalınlık, renk ve kalem adı farkları tablolarda "Bilgi" olarak ve sondaki "Adet dışındaki farklar" bölümünde yazılır; çelikte ağırlık ayrı tablodadır.

## Özet

| Liste | Aynı satır | Açıklama |
|---|---|---|
| Kör liste | 42 / 98 | 6 Ekim 22:47'de dondurulan liste; gerçek liste açılmadan önce |
| Düzeltilmiş | 48 / 98 | yalnız bizim hatalarımız düzeltildikten sonra, bugünkü kurallarla |
| + Eylül 2026 | 61 / 98 | Eylül 2026 listesinin şablonu ve paftalarındaki dizilim de kural olursa (`--sablon 2026`; karar bekliyor) |
| + pafta | 71 / 98 | elektrik ve iniş sayısı da projenin paftalarından sayılırsa |

Çelik ağırlığı (kg): gerçek 1 937 · kör liste 1 995 · düzeltilmiş 1 937 · + eylül 2026 1 937 · + pafta 1 937.

Kör listede gerçek listenin 56 satırı farklıydı. Farkın asıl nedenine göre:

| Sınıf | Satır | Anlamı |
|---|---|---|
| girdi hatası | 2 | projenin belgesinde vardı, yanlış ya da eksik okuduk |
| kural hatası | 27 | o projede ilk kez karşılaşılan durumda kuralımız yoktu ya da varsayımımız tutmadı |
| karar farkı | 20 | mevcut kural o listedeki uygulamadan farklı; karar Lokman'ın |
| elle (liste) | 6 | listenin elle yuvarlaması, elle çizimi ya da kaba hesabı |
| paftadan sayılır | 1 | kör testte paftalardaki adetler girdi değildi |

Bir satırda birden çok neden varsa sınıf asıl nedendir; nedenler eşit ağırlıktaysa ve biri bizim hatamızsa satır bizim hatamız sayılır.

Bizim hatamız olan 29 satırın 12 tanesi düzeltilmiş listede, 2 tanesi Eylül 2026 uygulamasıyla, 3 tanesi pafta sayımıyla tutuyor; 11 tanesinde hatamız düzeldi ama başka bir nedenle fark sürüyor (tablolarda "kalan fark"); 1 tanesi düzeltilemedi (kuralı bilinmiyor). Asıl nedeni başka olan 7 satırda da bizim hatamızın payı vardı (tablolarda "Bizim payımız").
Kör listede tutan 42 satırın 7 tanesi tesadüfen ya da eşikte tutuyordu (birbirini götüren iki fark; tabloda "Not").

Son listede (+ pafta) farklı kalan 27 satır:

| Tür | Satır | Anlamı |
|---|---|---|
| elle | 21 | listenin elle yuvarlaması, kaba hesabı ya da elle çizimi |
| ölçü | 2 | ölçünün nereden alındığı |
| soru | 4 | kural bilinmiyor ya da teyit gerekiyor |

## Çelik ağırlığı (kg)

| Kalem | Gerçek | Kör liste | fark % | Düzeltilmiş | fark % |
|---|---|---|---|---|---|
| Dış cephe duvar panelleri | 731,46 | 722,93 | -1,2 | 731,48 | 0,0 |
| İç cephe duvar panelleri | 317,14 | 316,79 | -0,1 | 317,12 | 0,0 |
| Kolon | 14,82 | 15,41 | +4,0 | 14,82 | 0,0 |
| Kiriş | 78,72 | 84,36 | +7,2 | 78,71 | 0,0 |
| Veranda duvarı ve korkuluğu | 46,44 | 54,59 | +17,5 | 46,44 | 0,0 |
| Çatı makas panelleri | 471,3 | 519,63 | +10,3 | 471,33 | 0,0 |
| Baca karkası | 44,8 | 47,36 | +5,7 | 44,79 | 0,0 |
| Müştemilat duvar panelleri | 125,72 | 130,36 | +3,7 | 125,73 | 0,0 |
| Müştemilat çatı paneli | 76,47 | 73,8 | -3,5 | 76,47 | 0,0 |
| Parça C profil 1,2 | 15 | 15 | 0,0 | 15 | 0,0 |
| Parça C profil 0,8 | 15 | 15 | 0,0 | 15 | 0,0 |
| Toplam | 1936,87 | 1995,2 | +3,0 | 1936,9 | 0,0 |

Ağırlığı %0,5 içinde tutan satır (11 satırda): kör liste 3 · düzeltilmiş 11. Kör listede ağırlık motorun proje ortalamalarından (duvar boyu × kg/m) hesaplanmıştı; korkuluk ve baca da 1,2 mm varsayılmıştı. Düzeltilmiş listede modeldeki profil boyundan ve modelde okunan et kalınlığından: boy × profilin birim ağırlığı (`kurallar.json` → `celik.profil_kg_m`).

## Çelik panel

| Kalem (gerçek liste) | Gerçek | Kör liste | Düzeltilmiş | + Eylül 2026 | + pafta | Kör listedeki farkın sınıfı | Neden | Yapılan | Kalan fark |
|---|---|---|---|---|---|---|---|---|---|
| Dış cephe duvar panelleri | 9 | 9 | 9 | 9 | 9 |  |  |  |  |
| İç cephe duvar panelleri | 6 | 6 | 6 | 6 | 6 |  |  |  |  |
| Kolon | 1 | 1 | 1 | 1 | 1 |  |  |  |  |
| Kiriş | 3 | 3 | 3 | 3 | 3 |  |  |  |  |
| Veranda duvarı ve korkuluğu | 3 | 3 | 3 | 3 | 3 |  | Bilgi: Adet aynı. Kör listede korkuluğu ve giriş çerçevesini 1,2 mm varsaymıştık (54,59 kg). Et kalınlığı karkas modelinde okunabiliyordu, okumamıştık: korkuluk 0,8, giriş çerçevesi 1,2 mm (liste de böyle). Düzeltilmiş listede profil modelden: 46,44 kg (liste 46,44). |  |  |
| Çatı makas panelleri | 16 | 16 | 16 | 16 | 16 |  |  |  |  |
| Baca karkası | 4 | 4 | 4 | 4 | 4 |  | Bilgi: Adet aynı. Kör listede 1,2 mm varsaymıştık (47,36 kg); modelde 0,8 mm okunuyor (liste de böyle): 44,79 kg (liste 44,80). |  |  |
| Müştemilat duvar panelleri | 3 | 3 | 3 | 3 | 3 |  |  |  |  |
| Müştemilat çatı paneli | 1 | 1 | 1 | 1 | 1 |  | Bilgi: Adet aynı. Kör listede ağırlık, 100 m² için verilen çatı paneli ağırlığının oturum alanına oranıydı (73,80 kg) ve boyut 'roll form çelik' yazıyordu; düzeltilmiş listede modeldeki profil boyundan 76,47 kg, 80 × 45 × 0,8 (liste 76,47). |  |  |
| Parça C profil 1,2 | 3 | 3 | 3 | 3 | 3 |  |  |  |  |
| Parça C profil 0,8 | 3 | 3 | 3 | 3 | 3 |  |  |  |  |

## Metal aksam

| Kalem (gerçek liste) | Gerçek | Kör liste | Düzeltilmiş | + Eylül 2026 | + pafta | Kör listedeki farkın sınıfı | Neden | Yapılan | Kalan fark |
|---|---|---|---|---|---|---|---|---|---|
| Tavan omegası | 47 | 34 ✗ | 34 ✗ | 46 ✗ | 46 ✗ | karar farkı | Bugünkü kural 2025 listelerine uydurulmuştu: tavan alanı ÷ 0,60 ÷ 3,75 (125,0 m → 34). Eylül 2026 projesinde iki şey farklı. Dizilim: paftada her tavan gözünde ilk hat duvar yüzünde, toplam 150,34 m; 2025 tarihli 62 m² projenin paftasında duvar yüzünde hat yok, hatlar duvar yüzünden 27–60 cm içeride (o dizilim bu projede yaklaşık 29–30 hat, 107–116 m verir; duvar yüzüne denk gelen hattın sayılıp sayılmamasına göre). Formül: şablonda toplam ÷ 3,65 + 5. | Kural değişmedi (34). Eylül 2026 dizilimi motora eklendi (39 hat, 148,1 m); yalnız o uygulamayla kullanılıyor: ÷ 3,65 + 5 → 46. | elle: paftada verandada fazladan 2,32 m'lik tek bir parça var; o olmadan liste de 46 çıkar. |
| Köşebent | 76 | 67 ✗ | 67 ✗ | 70 ✗ | 70 ✗ | karar farkı | Kural mühendisin 3 ve 4 Ekim tarifinden: oda tavan çevreleri + veranda tavanı çevresi + iç köşeler × 2,7 = 165,3 m ÷ 2,5 → 67. Listede ölçü 181,24 m; şablonun formülünde + 3 yedek var. | Değişmedi (67). Şablondaki + 3 ile 70. | soru: listedeki 181,24 m'nin nasıl toplandığı yazmıyor. Bizim ölçülerimizle şu toplam 2 cm farkla denk geliyor: oda tavan çevreleri karkas yüzünden 83,46 + veranda tavanı 15,28 + 30 köşe × 2,7 + bacanın çevresi 1,48 (listenin mahya bandı formülündeki ölçü; bizim ölçümüzle 1,44) = 181,22 m. 30 köşe, 25 iç köşe ile odaya doğru çıkıntı yapan 5 köşenin toplamı; mühendis 4 Ekim'de çıkıntı yapan köşeler sayılmaz demişti. Öyle sayılırsa 76 çıkıyor (çıkarım; teyit gerekir). |
| Aşık | 54 | 50 ✗ | 48 ✗ | 54 | 54 | karar farkı | Adet formülü: bugünkü kural toplam boy × 1,05 ÷ 4,2 (2025 listelerine uydurma); şablonda × 1,15 ÷ 4,1. Paftada 28 sıra ve verandanın kırma köşesinde eğim yönünde iki parça var: ölçülerin toplamı 189,76 m (listenin hücresinde 189,77). Bizim payımız: sıra kuralımız yanlıştı: her üst kenara boşluğa bakmadan bir mahya aşığı koyuyor, cumbanın doğu yüzünde aşıkları vadide kesiyordu (31 sıra, 199,4 m). Fazla boy adedi yukarı çektiği için fark küçük görünüyordu (50; düzeltilince 48). | Sıra kuralı düzeltildi: üst kenara yalnız altında 30 cm'den fazla boşluk kalıyorsa sıra konuyor (30 sıra, 190,5 m): bugünkü formülle 48, şablondaki formülle 54. Paftayla birebir aynı değil: kural cumba mahyasının iki yanına iki kısa sıra koyuyor (2,48 + 2,78 m; paftada yok), paftadaki iki eğik parça (2,82 + 1,70 m) kuralda yok. İki fark birbirini götürdüğü için toplam boy yakın çıkıyor; yakınlığın bir kısmı tesadüf. |  |
| Alın sacı | 10 | 13 ✗ | 10 | 10 | 10 | kural hatası | Müştemilat çatısının iki alnını (6,74 m) da saymıştık; çatı panelli çatıda alın sacı yok, alın Boardex ile kaplanıyor. | Çatı panelli çatının kenarları çıkarıldı: 20,97 m → 10. Listede alın boyu 22,38 m: güney kalkanının doğu eteği tam boy alınmış (5,02 m); modelde o eteğin 1,41 m'si veranda çatısıyla birleşiyor. Bindirme farkı (karar: bugün 30, şablonda 20 cm) bu satırda sonucu değiştirmiyor: bizim ölçümüzle iki bindirmeyle de 10; listenin ölçüsüyle 30 cm bindirme 11 verirdi. |  |
| Baş makas Z'si | 9 | — ✗ | 9 | 9 | 9 | kural hatası | Kalem bizde yoktu. 105 m² listede (Kasım 2025) vardı; okumuş ama kural yazmamıştık (bizim eksiğimiz). 90 m² listede yok. | Kural eklendi: her alın kenarı ÷ 2,8, ayrı ayrı yukarı → 9. Şablondaki formül (toplam ÷ 2,8) 8 verir; iki listede de yazılan adet formülün üstünde (8 ve 9). Kenar kenar yuvarlama bu iki sayıya uydurulmuş bir kuraldır (durum: uydurma); 105 m² listede alın kenarları tek tek bilinmediği için sınanamadı. Teyit bekliyor. |  |
| Saçak sacı | 11 | 14 ✗ | 12 ✗ | 11 | 11 | kural hatası | Müştemilat saçağını (5,46 m) da saymıştık; çatı panelli çatıda saçak sacı yok. | Çıkarıldı: 24,46 m ÷ 2,2 → 12. Kalan 1 fark karar: bindirme bugün 30 cm (Lokman, 3 Ekim), şablonda 20 cm (÷ 2,3 → 11). |  |
| Saçak omegası | 10 | 14 ✗ | 11 ✗ | 10 | 10 | kural hatası | Müştemilat saçağını da saymıştık (3 parça). | Çıkarıldı → 11 (her saçak kenarı ayrı ayrı yukarı). Kalan 1 fark karar: şablondaki ölçüyle (saçağın altındaki cephe boylarının toplamı 22,96 m ÷ 2,5) 10. |  |

## Dış cephe kaplama

| Kalem (gerçek liste) | Gerçek | Kör liste | Düzeltilmiş | + Eylül 2026 | + pafta | Kör listedeki farkın sınıfı | Neden | Yapılan | Kalan fark |
|---|---|---|---|---|---|---|---|---|---|
| Dış cephe Boardex: bina (duvarlar, veranda içi, makas alnı, baca) | 47 | 53 ✗ | 44 ✗ | 44 ✗ | 44 ✗ | kural hatası | Dış cephe tek satırdı ve müştemilatı da içeriyordu (53); listede bina ve müştemilat ayrı. Kalkanları saçak ucuna kadar almamış, bacanın üst kapağını saymamıştık. | Ek yapı ayrı satır oldu; kalkanlar modeldeki yüzler gibi saçak ucuna kadar; bacaya üst kapak eklendi → 44. | elle: listede makas alnı için iki tam kalkan alınmış (16,87 m²; görünen kalkanlar 13,8 m²) ve dört satır ayrı ayrı yukarı yuvarlanmış (toplam kaba hesap 44,9 → 47). |
| Dış cephe Boardex: müştemilat (duvarlar, çatı panelinin saçağı) | 13 | — ✗ | 11 ✗ | 11 ✗ | 11 ✗ | kural hatası | Ek yapının satırı ayrı değildi; çatı panelinin saçak ve alın kaplaması (3,05 m²) da yoktu. | Ayrı satır; saçak ve alın kaplaması eklendi (ölçüsü listeyle aynı) → 11. | elle: liste müştemilat duvarını 2,70 m ile çarpmış (29,0 m²; modelde duvarlar 2,25–2,50 m: 24,8 m²); fark bütünüyle buradan (2,70 m ile bizde de 13 çıkar). |
| Veranda tavanı (Boardex) | 5 | — ✗ | — ✗ | 5 | 5 | karar farkı | Bugünkü kural (Lokman): veranda tavanı yeşil alçıpan; bizde yeşil tavan satırının içinde (12,4 m²). Listede Boardex. | Değişmedi. Şablonla Boardex 5. |  |
| Nem bariyeri: bina | 89 | 140 ✗ | 88 ✗ | 88 ✗ | 88 ✗ | kural hatası | Varsayımımız Boardex'in bütün net alanıydı (kalkan, baca, korkuluk dahil; tek satır, 140 m²). Listede yalnız duvarlar × 1,08; bina ve müştemilat ayrı. | Kural listedeki gibi: 81,2 m² × 1,08 → 88. | ölçü: liste karkasın dış çevresini alıyor (35,96 m × 2,70); biz açıkta kalan yüzleri (başka duvarın dayandığı yerler düşülmüş: 35,56 m). |
| Nem bariyeri: müştemilat | 32 | — ✗ | 27 ✗ | 27 ✗ | 27 ✗ | kural hatası | Ayrı satır yoktu (bina satırının içindeydi). | Ayrı satır: 24,8 m² × 1,08 → 27. | elle: liste müştemilat duvarını 2,70 m ile çarpmış (modelde 2,25–2,50 m). |

## İç cephe kaplama

| Kalem (gerçek liste) | Gerçek | Kör liste | Düzeltilmiş | + Eylül 2026 | + pafta | Kör listedeki farkın sınıfı | Neden | Yapılan | Kalan fark |
|---|---|---|---|---|---|---|---|---|---|
| Tavan alçıpan beyaz | 22 | 26 ✗ | 22 | 22 | 22 | kural hatası | Müştemilatın tavanını (15,3 m²) beyaz saymıştık (varsayım); listede müştemilat ıslak hacim. İç kirişin kaplamasını (2,0 m²) da duvar satırına yazmıştık; listede tavan satırında. | Müştemilat ıslak hacim ve ayrı satır; kiriş kaplaması tavana alındı → 22. |  |
| Tavan alçıpan yeşil | 2 | 6 ✗ | 6 ✗ | 2 | 2 | karar farkı | Bugünkü kural (Lokman): yeşil = ıslak hacim + veranda tavanı (banyo 3,8 + veranda 12,4 m² → 6). Listede veranda tavanı Boardex; yeşil yalnız banyo (2). | Değişmedi. Şablonla 2. |  |
| Tavan alçıpan yeşil: müştemilat | 6 | — ✗ | 6 | 6 | 6 | kural hatası | Müştemilatı kuru hacim saymıştık (varsayım); projenin çiziminde yazmıyor, listede 'Müştemilat (Islak Zemin)'. | Islak hacim, ayrı satır → 6. |  |
| Duvar alçıpan beyaz | 48 | 56 ✗ | 47 ✗ | 47 ✗ | 47 ✗ | kural hatası | Müştemilatın iç yüzlerini (23,6 m²) beyaz saymıştık. | Müştemilat ayrı ve yeşil; kiriş kaplaması tavana alındı: 134,2 m² → 47. | ölçü: liste oda çevresini karkas yüzünden alıyor (59,16 m; karkas yüzünden bizim ölçümüz de 59,16 m): 135,7 m² → 48. Biz kaplanmış yüzden alıyoruz (58,60 m): 134,2 m² → 47; kaba hesap 46,97, bir levhanın eşiğinde. |
| Duvar alçıpan yeşil | 7 | 7 | 7 | 7 | 7 |  |  |  |  |
| Duvar alçıpan yeşil: müştemilat | 10 | — ✗ | 9 ✗ | 9 ✗ | 9 ✗ | kural hatası | Müştemilatı kuru hacim saymıştık; satırı ayrı değildi. | Islak hacim, ayrı satır: 23,6 m² → 9. | elle: liste müştemilat duvarını 2,70 m ile çarpmış (28,2 m² → 10); modelde duvarlar 2,25–2,50 m. |
| İç duvar OSB | 55 | 64 ✗ | 55 | 55 | 55 | kural hatası | Müştemilat dahil tek satırdı (64). Satırın adında 'OSB 9 mm' yazıyordu; proje notu ve kural 11 mm. | Ek yapı ayrı satır → 55; ad 'OSB 11 mm'. |  |
| İç duvar OSB: müştemilat | 10 | — ✗ | 9 ✗ | 9 ✗ | 9 ✗ | kural hatası | Ayrı satır yoktu. | Ayrı satır: 23,6 m² → 9. | elle: liste müştemilat duvarını 2,70 m ile çarpmış (→ 10). |
| Duvar izolasyonu | 15 | 14 ✗ | 14 ✗ | 15 | 15 | karar farkı | Kuralımız 2025 listelerine uydurulmuştu, zayiatsız: 118,9 m² ÷ 8,64 → 14. Şablonda × 1,05 var (→ 15). | Değişmedi. Şablonla 15. |  |

## Çatı kaplamaları

| Kalem (gerçek liste) | Gerçek | Kör liste | Düzeltilmiş | + Eylül 2026 | + pafta | Kör listedeki farkın sınıfı | Neden | Yapılan | Kalan fark |
|---|---|---|---|---|---|---|---|---|---|
| Sandviç panel L 5070 | 17 | 16 ✗ | 16 ✗ | 16 ✗ | 16 ✗ | elle (liste) | Panel toplamı aynı (33 / 33) ve dört boy aynı (liste 10 mm'ye yuvarlamış). Dağılım farklı: listede yüzler AutoCAD'de elle dizilmiş, çapraz kesilen parçalar eşlenmemiş. Dizilimimiz Lokman'ın kırma çatı kuralıyla parçaları eşliyor: 130,1 m² (liste 133,3 m²). | Değişmedi. Dizilimimiz kırma çatı kuralının çok düzlemli çatıya genellemesi (varsayım; teyit bekliyor). | elle: listede bir uzun panel (L 5070) iki kısa şerit için kullanılmış; dizilim onları L 2345 panelden çıkarıyor. |
| Sandviç panel L 3420 | 6 | 6 | 6 | 6 | 6 |  |  |  |  |
| Sandviç panel L 2870 | 6 | 5 ✗ | 5 ✗ | 5 ✗ | 5 ✗ | elle (liste) | Veranda sundurması 5,18 m: liste 6 şerit saymış; dizilim iki uçtaki çapraz parçaları eşleyip 5 panelde bitiriyor. | Değişmedi. Dizilimimiz kırma çatı kuralının çok düzlemli çatıya genellemesi (varsayım; teyit bekliyor). | elle: listede çapraz kesilen parçalar eşlenmemiş. |
| Sandviç panel L 2340 | 4 | 6 ✗ | 6 ✗ | 6 ✗ | 6 ✗ | elle (liste) | Liste cumba için 3 + kırma üçgeni için 1 panel saymış; dizilim cumbanın batı yanındaki kısa şeritleri de bu boydan çıkarıyor (6). | Değişmedi. Dizilimimiz kırma çatı kuralının çok düzlemli çatıya genellemesi (varsayım; teyit bekliyor). | elle: toplam aynı (33); dağılım elle yerleşimden. |
| Metal kiremit mahyası | 5 | 5 | 5 | 5 | 5 |  | Not: Kör listedeki 5 eşikte tutuyor. Listede mahya boyu 12,85 m: kırma 3,21 m alınmış (duvara kadar). Bizde 12,49 m: kırma 2,85 m (ana çatının alın çizgisine kadar; devamındaki 35 cm ana çatının saçağının altında kalıyor, modelde gizli kenar). Bindirme de farklı (bizde 30, listede 20 cm). Bizim sayımız 12,49 ÷ 2,5 = 4,998: 6'nın eşiğinde. Listenin ölçüsüyle bugünkü kural 6 verirdi; Eylül 2026 bindirmesiyle iki ölçü de 5. |  |  |
| Sandviç panel kapaması (bina ve müştemilat) | 12 | 14 ✗ | 14 ✗ | 12 | 12 | karar farkı | Kural 2025 listelerinden: L 2500, her saçak kenarı ayrı ayrı yukarı → 14. Listede L 2800, toplam saçak ÷ 2,6 → 12 (bina 9 + müştemilat 3). | Değişmedi. Şablonla 12. |  |
| Ters mahya | 2 | 2 | 2 | 2 | 2 |  |  |  |  |
| Ters mahya kenar kutuları | 4 | — ✗ | — ✗ | 4 | 4 | karar farkı | Kalem açık soruydu ('cumbalı çatı çalışılınca sorulacak'): Excel motoru hesaplıyor, 2025 tarihli cumbalı listede yok. Eylül 2026 listesinde var: ters mahya × 2. | Varsayılan hesaba alınmadı. Eylül 2026 uygulamasıyla 4. |  |
| Damlalık (bina ve müştemilat) | 6 | 5 ✗ | 5 ✗ | 6 | 6 | karar farkı | Lokman damlalığı listeden tamamen çıkarmıştı (4 Ekim 15:18). Çatının duvara dayandığı kenar için kuralımız yok; satırı 'duvar dibi sacı' adıyla, mahya parçası gibi ve soru olarak yazmıştık (11,35 m ÷ 2,5 → 5). Listede bu kenarda damlalık (L 2500) var: bina (0,71 + 5,18) ÷ 2,3 → 3, müştemilat 5,46 ÷ 2,3 → 3. Ölçülerimiz listeyle aynı. | Varsayılan hesapta soru satırı duruyor (5). Eylül 2026 uygulamasıyla damlalık → 6. |  |
| Mahya bandı | 4 | 2 ✗ | 3 ✗ | 4 | 4 | karar farkı | Formüldeki damlalık terimi Lokman'ın 4 Ekim kararıyla çıkmıştı: (5 × 2,8 + 2 × 2,8) ÷ 10 → 2. Listede terim duruyor (6 × 2,5 m): terim tek başına 4 verir. Bizim payımız: bacanın çatıdaki çevresini (1,44 m) saymamıştık; listede var. Eklenince bugünkü kuralla 2 → 3. | Baca çevresi eklendi: bugünkü kuralla 3. Eylül 2026 uygulamasıyla (damlalık terimiyle) 4. |  |
| Çatı izolasyonu | 10 | 10 | 10 | 10 | 10 |  | Bilgi: Adet aynı (10); ölçü de yakın (liste 87,91 m², biz 88,69 m²). Kalemin adı farklı: 2025 listelerinde ve bizde 'çatı şiltesi 80 mm', Eylül 2026 listesinde 'çatı izolasyonu 100 mm'. Eylül 2026 uygulamasında ad listedeki gibi yazılıyor; hangi kalınlığın geçerli olduğu soruldu. |  |  |

## Dere

| Kalem (gerçek liste) | Gerçek | Kör liste | Düzeltilmiş | + Eylül 2026 | + pafta | Kör listedeki farkın sınıfı | Neden | Yapılan | Kalan fark |
|---|---|---|---|---|---|---|---|---|---|
| Metal dere | 7 | 8 ✗ | 7 | 7 | 7 | kural hatası | Müştemilat saçağına da dere saymıştık (29,92 m); listede ve dere paftasında yalnız üç saçakta dere var (24,46 m). | Çatı panelli çatıda dere yok → 7. |  |
| Dere iniş borusu | 7 | 7 | 5 ✗ | 5 ✗ | 7 |  | Not: Kör listedeki 7 tesadüf: müştemilat saçağının iki ucuna iniş saymıştık (+ 2), 9,64 m'lik iki saçağın ortasına saymamıştık (− 2). Düzeltilmiş listede Lokman'ın kuralı 5 veriyor (üç dere hattının beş ucu; orta iniş 10 m ve üzeri cephede). Paftada 7 var: 9,64 m'lik iki saçağın ortasına yakın birer iniş daha (altlarındaki cephe 9,04 m). Mühendisin 'ortalama 5 metrede bir' tarifi de 7 veriyor. Lokman'a soru: orta inişin eşiği. |  |  |
| Dere iniş aparatı | 7 | 7 | 5 ✗ | 5 ✗ | 7 |  | Not: İniş sayısına bağlı (bkz. dere iniş borusu). |  |  |
| Dere kapağı | 4 | 6 ✗ | 4 | 4 | 4 | kural hatası | Motorun çatı tipine göre sabitini kullanmıştık (beşik + cumba: 6). Listede paftadan sayılmış: başka bir dere hattıyla buluşmayan dört uç. | Kapak = dere hatlarının serbest uç sayısı → 4. |  |
| Açık dirsek | 14 | 14 | 10 ✗ | 10 ✗ | 14 |  | Not: İniş sayısına bağlı. |  |  |
| Kapalı dirsek | 7 | 7 | 5 ✗ | 5 ✗ | 7 |  | Not: İniş sayısına bağlı. |  |  |
| İniş kelepçesi | 14 | 14 | 10 ✗ | 10 ✗ | 14 |  | Not: İniş sayısına bağlı. |  |  |
| Dere kelepçesi | 56 | 64 ✗ | 56 | 56 | 56 | kural hatası | Dere adedine bağlı (8 × 8). | Dere 7 olunca 56. |  |

## Kapı ve pencere

| Kalem (gerçek liste) | Gerçek | Kör liste | Düzeltilmiş | + Eylül 2026 | + pafta | Kör listedeki farkın sınıfı | Neden | Yapılan | Kalan fark |
|---|---|---|---|---|---|---|---|---|---|
| Melamin kapı (80'lik kanat) | 2 | 2 | 2 | 2 | 2 |  |  |  |  |
| Melamin kapı (70'lik kanat) | 1 | 1 | 1 | 1 | 1 |  |  |  |  |

## Elektrik

| Kalem (gerçek liste) | Gerçek | Kör liste | Düzeltilmiş | + Eylül 2026 | + pafta | Kör listedeki farkın sınıfı | Neden | Yapılan | Kalan fark |
|---|---|---|---|---|---|---|---|---|---|
| Tijli duy | 7 | 7 | 6 ✗ | 6 ✗ | 7 |  | Not: Kör listedeki 7 tesadüf: müştemilata 1 duy saymıştık (paftada müştemilatta duy yok, 2 glop var); salon, mutfak ve holde paftada toplam 5 duy var, kural 4 veriyor. Kuralla 6, pafta sayımıyla 7. |  |  |
| Yuvarlak glop | 5 | 3 ✗ | 5 | 5 | 5 | kural hatası | Müştemilat (depo) mühendisin oda başına kuralında yok; varsayımımız 1 tijli duy idi. Paftada müştemilatta duy yok, 2 glop var. | Depo kuralı paftadaki gibi yazıldı (2 glop, 1 çiftli anahtar; priz yok) → 5. Tek projenin paftası; teyit bekliyor. |  |
| Ampul | 12 | 10 ✗ | 11 ✗ | 11 ✗ | 12 | kural hatası | Duy + glop. Farkın yarısı müştemilat (depo) için yaptığımız varsayımdan (1 duy; paftada 2 glop), yarısı paftadan: salon, mutfak ve holde paftada toplam 5 duy var, oda başına kural 4 veriyor. | Depo kuralı düzeltildi → 11; pafta sayımıyla 12. |  |
| NYM kablo (3 × 2,5) | 140 | 182 ✗ | 180 ✗ | 133 ✗ | 137 ✗ | karar farkı | Bugünkü kural motordaki gibi: sigorta adedi × kapalı kısmın köşegeni (15,23 m; müştemilatı katmak bizim kararımızdı) + priz başına 2 m. Şablonda mesafe 'sigortadan eve en uzun uzaklık yaklaşık'. Projenin elektrik paftasında sigorta kutusu ana giriş kapısının yanında; oradan en uzak köşeye 10,0 m (müştemilat dahil), yalnız ana binada 8,1 m. Bizim payımız: müştemilata saydığımız 1 priz (varsayım; paftada yok) düzeltilince 182 → 180. | Kural değişmedi (180). Eylül 2026 uygulamasıyla mesafe sigorta kutusundan (modelde giriş kapısından 10,06 m): kuraldaki priz sayısıyla 133, pafta sayımıyla 137. | elle: listedeki 140 elle yazılmış, hücrede formül yok. İki okuma da tutuyor: 9 × 11 m + 20 priz × 2 = 139, onluğa yukarı; ya da 96 m taban (9 × 10,67) + (16 + 2 × 3) × 2 = 140 (çiftli priz iki sayılmış, uydu prizi sayılmamış). Bizde taban 9 × 10,06 = 90,5 m ve uydu prizi de sayılıyor: 136,5 → 137. |
| NYM kablo (2 × 1,5) | 120 | 158 ✗ | 160 ✗ | 113 ✗ | 115 ✗ | karar farkı | 3 × 2,5 kabloyla aynı; priz yerine anahtar sayısı. Bizim payımız: müştemilata saydığımız 1 tekli anahtar (varsayım; paftada 1 çiftli) düzeltilince 158 → 160. | Kural değişmedi (160). Eylül 2026 uygulamasıyla: kuraldaki anahtar sayısıyla 113, pafta sayımıyla 115. | elle: listedeki 120 elle yazılmış. İki okuma da tutuyor: 9 × 11 m + 8 anahtar × 2 = 115, onluğa yukarı; ya da 96 m taban + (4 + 2 × 4) × 2 = 120. Bizde 90,5 + 24 = 114,5 → 115. |
| Uydu kablo | 25 | 25 | 25 | 25 | 25 |  |  |  |  |
| Besleme kablosu | 5 | 5 | 5 | 5 | 5 |  |  |  |  |
| Besleme kablo borusu | 5 | 5 | 5 | 5 | 5 |  |  |  |  |
| Tekli anahtar | 4 | 6 ✗ | 5 ✗ | 5 ✗ | 4 | kural hatası | Müştemilata 1 tekli anahtar saymıştık (varsayım); paftada müştemilatta 1 çiftli anahtar var. Kalan fark paftadan: kural 5, pafta 4. | Depo kuralı düzeltildi → 5; pafta sayımıyla 4. |  |
| Çiftli anahtar | 4 | 2 ✗ | 3 ✗ | 3 ✗ | 4 | kural hatası | Müştemilattaki çiftli anahtarı saymamıştık (varsayım: tekli). Kalan fark paftadan: anahtar toplamı kuralla da 8 (liste 8), tekli ve çiftli dağılımı farklı. | Depo kuralı düzeltildi → 3; pafta sayımıyla 4. |  |
| Tekli priz | 16 | 17 ✗ | 16 | 16 | 16 | kural hatası | Müştemilata 1 priz saymıştık (varsayım); paftada müştemilatta priz yok. | Depo kuralı düzeltildi → 16 (pafta sayımı da 16). |  |
| Çiftli priz | 3 | 2 ✗ | 2 ✗ | 2 ✗ | 3 | paftadan sayılır | Paftadan sayılır; priz toplamı kuralla 19 (liste 20). | Kuralla 2, pafta sayımıyla 3. |  |
| Uydu prizi | 1 | 1 | 1 | 1 | 1 |  |  |  |  |
| Zil | 1 | 1 | 1 | 1 | 1 |  |  |  |  |
| Buat kasa | 35 | 33 ✗ | 32 ✗ | 32 ✗ | 33 ✗ | karar farkı | Formül aynı: anahtar + priz + oda sayısı. Listede oda sayısı 7 (8 + 20 + 7); biz veranda hariç mahal sayısını alıyoruz (5; mühendis, 4 Ekim). Bizim payımız: müştemilata saydığımız 1 priz düzeltilince 33 → 32. | Kural değişmedi (32). | soru: oda işlev işlev sayılırsa (iki yatak odası, banyo, salon, mutfak, hol, müştemilat) 7 ediyor; bizde salon, mutfak ve hol tek mahal. Şablonda sigorta için de 'oda sayısı + ekstra yüksek voltajlı noktalar' yazıyor (9 = 7 + 2 olabilir). 2025 tarihli 105 m² listede aynı formül 3 odayla tutuyor. Pafta sayımıyla bizde 28 + 5 = 33. |
| W otomat (sigorta) | 9 | 9 | 9 | 9 | 9 |  | Bilgi: Adet aynı (9). Bizde kural 'bina başına 9' (mühendis); şablonun notu 'oda sayısı + ekstra yüksek voltajlı noktalar'. |  |  |
| Sigorta kutusu | 1 | 1 | 1 | 1 | 1 |  |  |  |  |
| İzole bant | 5 | 6 ✗ | 6 ✗ | 6 ✗ | 6 ✗ | elle (liste) | 98,7 × 0,06 = 5,9: liste 5 yazmış, biz yukarı yuvarlıyoruz (6). | Değişmedi. | elle: aşağı yuvarlanmış. |
| Kaçak akım rölesi | 1 | 1 | 1 | 1 | 1 |  |  |  |  |

## Vida

| Kalem (gerçek liste) | Gerçek | Kör liste | Düzeltilmiş | + Eylül 2026 | + pafta | Kör listedeki farkın sınıfı | Neden | Yapılan | Kalan fark |
|---|---|---|---|---|---|---|---|---|---|
| RYSB pul başlı | 750 | 743 ✗ | 743 ✗ | 743 ✗ | 743 ✗ | elle (liste) | 98,7 × 7,5 = 740: liste 750 yazmış; bizde yuvarlama yok (99 m² × 7,5 = 743). | Değişmedi. | elle: 750'ye yuvarlanmış. |
| Alçıpan vidası | 8 000 | 6 000 ✗ | 6 250 ✗ | 7 750 ✗ | 7 750 ✗ | karar farkı | Levha başına 40 (2025 çalışma kitabının notu); şablonda 50. Levha sayısı da farklıydı (148 / 160). Bizim payımız: levha sayımız değişti (148 → 152: müştemilat ve Boardex satırlarındaki düzeltmeler): 6 000 → 6 250. | Kural değişmedi (6 250). Şablonla 153 levha × 50 = 7 650 → 7 750 (250'ye yuvarlıyoruz). | elle: fark levha sayısından (153 / 160): 3 levha bina Boardex'inden (iki tam kalkan ve satırların ayrı ayrı yuvarlanması), 3 levha müştemilattan (duvarlar 2,70 m ile çarpılmış), 1 levha duvar alçıpanından (çevre karkas yüzünden). |
| OSB ve yalıpan vidası | 3 550 | 3 000 ✗ | 3 000 ✗ | 3 500 ✗ | 3 500 ✗ | karar farkı | OSB başına 40 (motor ve 2025 notu); şablonda 50. | Değişmedi (3 000). Şablonla 3 488 → 3 500 (pafta sayımıyla 3 492). | elle: liste 3 542'yi 50'ye yuvarlamış (3 550; OSB 65 levha, bizde 64); biz 500'e yuvarlıyoruz. |
| Trapez vida (5,5 × 25) | 1 800 | 2 000 ✗ | 1 750 ✗ | 2 000 ✗ | 2 000 ✗ | elle (liste) | Ham sayılar yakındı (bizde 1 786, listede 1 798); fark yuvarlamadan: biz 250'ye yukarı yuvarlıyoruz (2 000), liste 1 800 yazmış (şablonun notu '250 katları genelde gönderiliyor' dediği halde). Formül de farklı (karar): bizde tavan omegası × 10 ve saçak omegası × 6 var (2025 notları); şablonda omega × 6, saçak omegası yok, çelik panel sayısına parça C profiller dahil. Ham sayıların yakınlığı tesadüftü: katsayı farkını, fazla saydığımız aşık ve saçak omegası götürüyordu. Bizim payımız: aşık ve saçak omegası adedimiz fazlaydı (50 ve 14; düzeltilince 48 ve 11): ham sayı 1 786 → 1 748, yuvarlanınca 2 000 → 1 750. | Kural değişmedi. Şablonla ham sayı 1 756 → 2 000. | elle: liste 1 798'i 1 800 yazmış; biz 250'ye yukarı yuvarlıyoruz (1 756 → 2 000). 1 756 ile 1 798 farkı tavan omegası ve köşebent adedinden. |
| Trapez vida (5,5 × 60) | 250 | 250 | 250 | 250 | 250 |  |  |  |  |
| Trapez vida (5,5 × 110) | 750 | 750 | 750 | 750 | 750 |  |  |  |  |
| Çelik dübel | 42 | 42 | 42 | 42 | 42 |  |  |  |  |
| Şase pul | 42 | 42 | 42 | 42 | 42 |  |  |  |  |
| 8'lik trapez uç | 7 | 7 | 7 | 7 | 7 |  |  |  |  |
| PH2 uç | 7 | 7 | 7 | 7 | 7 |  |  |  |  |
| 230'luk kesme taşı | 2 | 7 ✗ | 7 ✗ | 2 | 2 | karar farkı | Kural iki 2025 listesinden: m² ÷ 15 → 7. Şablon ve Excel motoru m² × 0,02 → 2. | Değişmedi. Şablonla 2. |  |
| İnox taş | 10 | 10 | 10 | 10 | 10 |  |  |  |  |
| Çırpı ipi | 1 | 1 | 1 | 1 | 1 |  |  |  |  |
| Acil müdahale kapağı | 1 | — ✗ | — ✗ | — ✗ | — ✗ | karar farkı | Kural (mühendis, 4 Ekim): standart pakette yok, müşteri isterse eklenir. Projenin çiziminde böyle bir istek yazmıyor; listede 1 adet var. | Değişmedi. | soru: bu projede müşteri mi istedi, yoksa kalem artık her listede mi. |

## Boya

| Kalem (gerçek liste) | Gerçek | Kör liste | Düzeltilmiş | + Eylül 2026 | + pafta | Kör listedeki farkın sınıfı | Neden | Yapılan | Kalan fark |
|---|---|---|---|---|---|---|---|---|---|
| Tavan boyası | 1 | — ✗ | 1 | 1 | 1 | girdi hatası | Teknik özelliklerde yalnız dış cephe ve iç cephe boyası alıcıya ait; biz dört boya kalemini de çıkarmıştık. | Kapsam kalem kalem okunuyor → 1. |  |
| Astar | 1 | — ✗ | 1 | 1 | 1 | girdi hatası | Tavan boyasıyla aynı. | → 1. |  |
| Silikonize mastik | 3 | — ✗ | — ✗ | — ✗ | — ✗ | kural hatası | Varsayım: pencereler alıcıya aitse pencere sayısına bağlı kalemler (pencere vidası, mastik) yazılmaz. Pencere vidası listede de yok; mastik 3 adet var. | Değişmedi: hangi kuralla 3 olduğu bilinmiyor. | soru: mastik hangi kuralla yazılıyor (kuralımız pencere adedi: 7; listede 3; üç 2025 listesinde 8). |
| Dayson | 4 | 6 ✗ | 6 ✗ | 3 ✗ | 3 ✗ | karar farkı | Kural motorun formülü: m² × 0,06 → 6. Şablonun notu: beşik çatıda 0,03, kırmada 0,06. | Değişmedi. Şablonla 3. | elle: şablonun kendi notuyla 3 çıkıyor; liste 4 yazmış. |
| Poliüretan köpük | 2 | 2 | 2 | 2 | 2 |  |  |  |  |

## Adet dışındaki farklar

Gerçek listede yazan ama adet karşılaştırmasına girmeyenler: renk, kalem adı, özellik.

| Konu | Gerçek liste | Bizim liste | Yapılan |
|---|---|---|---|
| Renk | Renk kalemin adında yazıyor ('antrasit'): alın sacı, saçak sacı, sandviç panel, metal kiremit mahyası, sandviç panel kapaması, ters mahya, metal dere, dere iniş borusu, dere kapağı, silikonize mastik, dayson. | Dondurulan listede renk yoktu: teknik özelliklerde yazıyordu (çatı kaplama rengi, saçak ve alın rengi), listeye taşınmıyordu (bizim eksiğimiz). | Düzeltildi: renk tanımdan listeye taşınıyor, aynı kalemlerde yazıyor (kural: `renkli_kalemler`); teknik özelliklerdeki haliyle ('antrasit gri'). Mastik satırı bizde olmadığı için rengi de yok. Derenin ve mastiğin hangi renge bağlı olduğu bu projeden çıkmıyor (iki renk aynı): soru. |
| Saçak sacında menfez | Saçak sacının adında '4 adet menfezli' yazıyor (11 saçak sacının 4'ü menfezli). | Bizde böyle bir ayrım yok; kuralı bilinmiyor. | Yapılmadı: menfezli saçak sacının adedi neye göre belirleniyor, soruldu. |
| Boardex kalınlığı | 8 × 1200 × 2400. | 12,5 mm (mühendis, 4 Ekim; Lokman, 2 Ekim). | Varsayılan değişmedi; Eylül 2026 uygulamasında 8 mm yazılıyor. Karar bekliyor. |
| Çatı izolasyonu | 'Çatı izolasyonu (İzocam-Knauf) 100 mm'; duvar izolasyonunda marka ve tip de yazıyor. | 'Çatı şiltesi 80 mm' (2025 listelerindeki ad); marka yazmıyor. | Varsayılan değişmedi; Eylül 2026 uygulamasında 'çatı izolasyonu 100 mm'. Karar bekliyor. |
| Sandviç panel boyu | Boylar 10 mm'ye yuvarlanmış: 5070 · 3420 · 2870 · 2340. | mm'ye yukarı: 5072 · 3421 · 2874 · 2345. | Değişmedi: liste bizden 1–5 mm kısa. Yuvarlama kuralı soruldu. |
| Alıcıya ait kalemler | Satır listede duruyor; adet boş, boyut sütununda 'alıcıya ait' yazıyor (dış kapılar, pencereler, tesisat, dış ve iç cephe boyası). Dış kapı satırlarında kapının yönü de yazıyor ('sol'). | Satır listeye hiç girmiyor. | Değişmedi; istenirse satırlar 'alıcıya ait' notuyla yazılabilir. |
| Saçak omegası ölçüsü | 100 × 2500. | L 2500 (genişlik yazmıyor). | Değişmedi. |
| Öteki ad ve ölçü farkları | Sigorta '16 amper'; saçak sacı '300 × 2500'; profil adında dudak ölçüsü de var ('80 × 45 × 10 × 1,2'); anahtar ve prizler 'takım'; acil müdahale kapağı vida grubunda; sandviç panel kapaması L 2800, damlalık L 2500. | Sigortada amper yok; saçak sacı 'L 2500'; profil '80 × 45 × 1,2'; 'takım' yazmıyor; çatı müdahale kapağı çatı kaplamaları grubunda; kapama L 2500, duvar dibinde geçici 'duvar dibi sacı' L 2800. | Kapama ve damlalık Eylül 2026 uygulamasında listedeki ölçüyle. Ötekiler değişmedi: liste biçimi konusu; istenirse aynı adlar yazılır. |
