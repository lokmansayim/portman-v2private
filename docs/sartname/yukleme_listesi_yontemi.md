# Çelik yükleme listesi: yöntem ve ilk taslak (3 Ekim 2026)

Lokman, 3 Ekim 12:03: yükleme listesi sistemi kurulacak. Bundan sonraki çelik modellerde model verilecek, liste aynı sistemle dönecek. Kapsam: tek kat çelik, çift katın üst katı ve çatı ailesi. Canlıya alınacak.

Kaynak: Lokman'ın bağladığı klasördeki gerçek yükleme listelerinin çalışma kitapları. İkisi hesap sayfalarıyla birlikte okundu:

- **90 m²**, tek kat, beşik çatı, OSB üstü metal kiremit, karkas 80 mm (liste tarihi 30 Eylül 2025).
- **62 m²**, tek kat, kırma çatı, sandviç panel, dış karkas 140 mm, verandalı (liste tarihi 19 Eylül 2025). Ç8201'e en yakın örnek.

İki listeye daha (100 ve 105 m²) yalnız seçenek çeşitliliği için bakıldı. Kişi, bayi ve firma adları alınmadı. Deneme kodu: `deneme/2026-10-03_yukleme/`.

## Listenin grupları (şablondaki sırayla)

Çelik panel · Metal aksam · Dış cephe kaplama · İç cephe kaplama · Çatı kaplamaları · Dere · Kapı ve pencere · Vida · Boya · Elektrik · Sıhhi tesisat.

Vida, elektrik ve sıhhi tesisat 62 m² listede var, 90 m² listede yok.

## Yöntem: çalışma kitabının kendi formülleri

- **Dış cephe.** Net alan = çevre × kat yüksekliği + kolon ve kiriş kaplaması (adet × çevre × boy) + alın alanları − kapı ve pencere boşlukları. Boardex adedi = net × 1,15 ÷ (1,2 × 2,4). Aynı alan dekoratif sıva, betopan ve dış duvar OSB'si için de kullanılıyor.
- **İç cephe.** Odalar "beyaz" ve "yeşil" diye ayrılıyor. Her oda için iç çevre × kat yüksekliği − o odadaki boşluklar. Alçıpan adedi = net × 1,05 ÷ (1,2 × 2,5). Sütun başlığında "%15 zaiyat" yazıyor; formül %5.
- **İç duvar OSB'si.** Bütün iç yüzler × 1,05 ÷ (1,22 × 2,44); ya da yalnız TV, klima ve mutfak dolabı arkası (alan elle giriliyor).
- **Kapı boşlukları.** İç kapı 0,90 × 2,14; dış kapı 0,95 × 2,10.
- **Vida notları.** 1 alçıpan ya da Boardex için 40 alçıpan vidası; 1 OSB için 40; 1 pencere için 20. Trapez vida (5,5 × 25): aşık 10, omega (375) 10, omega (240) 6, çelik panel 10, köşebent 6. Orta uzunlukta duvar paneline 3 çelik dübel; şase pul = dübel sayısı. İnox taş = bina m² ÷ 10; uçlar ve kesme taşı = inox taş ÷ 2.
- 100 m² listede kalemin adı: "Duvar izolasyonu (dış duvarlar çift kat)"; o projede dış karkas 140 mm.

## Kurallar ve iki gerçek listeyle karşılaştırma

Durum: `excel` çalışma kitabındaki formül · `uydurma` iki listedeki adedi tutturan kural · `varsayim` Claude'un varsayımı · `soru` kural bilinmiyor. ✗ adedin tutmadığı yer.

| Kalem | Kural | Durum | 90 m²: hesap / liste | 62 m²: hesap / liste |
|---|---|---|---|---|
| Dış cephe Boardex | (çevre × yükseklik + kolon/kiriş kaplaması + alın − boşluklar) × 1,15 ÷ 2,88 | excel | 45 / 46 ✗ | 32 / 32 |
| Duvar alçıpan beyaz | oda oda: (iç çevre × yükseklik − o odadaki boşluklar) toplamı × 1,05 ÷ 3,0 | excel | 66 / 67 ✗ | 32 / 32 |
| Duvar alçıpan yeşil | oda oda: (iç çevre × yükseklik − o odadaki boşluklar) toplamı × 1,05 ÷ 3,0 | excel | 9 / 9 | 7 / 8 ✗ |
| Tavan alçıpan beyaz | tavan alanı × 1,05 ÷ 3,0 | uydurma | 25 / 25 | 15 / 15 |
| Tavan alçıpan yeşil | tavan alanı × 1,05 ÷ 3,0; yeşil = ıslak hacim + veranda tavanı | uydurma | 5 / 6 ✗ | 7 / 7 |
| OSB 9 mm (duvar) | girilen alan × 1,05 ÷ 2,98; alanın nasıl belirlendiği bilinmiyor | soru | 13 / 13 | — |
| Duvar izolasyonu | dış duvar × kat sayısı (80 mm: 1, 140 mm: 2) + iç duvar − boşluklar; ÷ 8,64 | uydurma | 18 / 18 | 19 / 19 |
| Çatı OSB | çatı yüzeyi × 1,05 ÷ 2,98 | uydurma | 39 / 39 | — |
| Metal kiremit | saçak boyu ÷ 1,10; boy = eğimli boy | uydurma | 30 / 30 | — |
| Metal kiremit mahyası | mahya hattı (tepe + kırmalar) ÷ (2,8 − 0,20 bindirme) | varsayim | 7 / 7 | 11 / 11 |
| OSB mahyası | mahya hattı ÷ (2,8 − 0,20 bindirme) | varsayim | 7 / 7 | — |
| Özel mahya (geniş) | girilen boy ÷ 2,8; nereye konduğu bilinmiyor | soru | 2 / 2 | — |
| Çatı şiltesi 80 mm | çatı boyu × (bina eni + 0,20) ÷ 9,6 | uydurma | 11 / 11 | 8 / 8 |
| Metal dere | saçak boyu ÷ (4,0 − 0,10 bindirme) | varsayim | 9 / 9 | 10 / 10 |
| Dere iniş borusu | iniş sayısı (7) × 1; iki listede de 7 iniş var, kuralı bilinmiyor | uydurma | 7 / 7 | 7 / 7 |
| Dere iniş aparatı | iniş sayısı (7) × 1; iki listede de 7 iniş var, kuralı bilinmiyor | uydurma | 7 / 7 | 7 / 7 |
| Açık dirsek | iniş sayısı (7) × 2; iki listede de 7 iniş var, kuralı bilinmiyor | uydurma | 14 / 14 | 14 / 14 |
| Kapalı dirsek | iniş sayısı (7) × 1; iki listede de 7 iniş var, kuralı bilinmiyor | uydurma | 7 / 7 | 7 / 7 |
| İniş kelepçesi | iniş sayısı (7) × 2; iki listede de 7 iniş var, kuralı bilinmiyor | uydurma | 14 / 14 | 14 / 14 |
| Dere kapağı | girilen sayı; kuralı bilinmiyor | soru | 6 / 6 | — |
| Dere kelepçesi | dere adedi × 8 | uydurma | 72 / 72 | 80 / 80 |
| Saçak sacı (30'luk) | her saçak kenarı ÷ 2,5, ayrı ayrı yukarı | uydurma | 14 / 14 | 16 / 17 ✗ |
| Saçak omegası | her saçak kenarı ÷ 2,5, ayrı ayrı yukarı | uydurma | 14 / 14 | 16 / 16 |
| Alın sacı (30'luk) | alın boyu × 1,05 ÷ 2,5; alın boyunun nasıl ölçüldüğü bilinmiyor | soru | 7 / 9 ✗ | — |
| Tavan omegası (60'lık) | tavan alanı ÷ 0,60 ÷ 3,75 | uydurma | 37 / 40 ✗ | 26 / 26 |
| Köşebent | oda çevreleri toplamı × 2 ÷ 2,5; 62 m² listeyi tutturmuyor | soru | 71 / 70 ✗ | 42 / 50 ✗ |
| Aşık | eğim boyunca 60 cm aralık + mahya aşığı; kırmada her sıra çatıyı dolanır; × 1,05 ÷ 4,2 | uydurma | 56 / 57 ✗ | 41 / 41 |
| Alçıpan vidası (3,5 × 35) | alçıpan ve Boardex levha sayısı × 40; 250'ye yuvarlandı | excel | — | 4000 / 4000 |
| Pencere vidası (4,8 × 70) | pencere sayısı × 20 | excel | — | 120 / 120 |
| Trapez vida (5,5 × 25) | aşık × 10 + tavan omegası × 10 + saçak omegası × 6 + çelik panel × 10 + köşebent × 6; 250'ye yuvarlandı | excel | — | 1750 / 1750 |
| İnox taş | bina m² ÷ 10 | excel | — | 7 / 7 |
| Dış duvar OSB 9 mm | Boardex ile aynı alan (× 1,15) ÷ 2,98; üst paket | excel | — | 31 / 31 |
| İç duvar OSB 9 mm | bütün iç yüzler (beyaz + yeşil net) × 1,05 ÷ 2,98; üst paket | excel | — | 39 / 39 |
| Sandviç panel | çatı yüzeyi × 1,10 ÷ (panel boyu × 1,00); panel boyu = eğimli boy | uydurma | — | 27 / 27 |
| Sandviç panel kapaması | her saçak kenarı ÷ 2,5, ayrı ayrı yukarı | uydurma | — | 16 / 16 |
| Saçaklar için Boardex | saçak boyu × 0,30 × 1,15 ÷ 2,88 | uydurma | — | 5 / 5 |

56 karşılaştırmanın 46 tanesinde adet aynı. Farkların biri dışında hepsi 1 ile 3 arasında; köşebent 62 m² listede 8 eksik çıkıyor.

**Bu bir sınama değil, uydurmadır.** `uydurma` kuralların katsayıları bu iki listeye bakılarak seçildi; aynı listelerle tutması kanıt sayılmaz. Çatı uzunlukları, tavan alanları ve iniş sayısı gibi girdiler de listelerde yazan değerlerden alındı.

### Üçüncü listeyle kısmi sınama (105 m², tek kat panelli çatı, dış karkas 140 mm)

Bu listenin yalnız ilk sayfasındaki değerlerle, kurallar değiştirilmeden bakıldı. Girdi dosyası kurulmadı; tam bir sınama değildir.

| Kalem | Listedeki ölçü | Kuralın verdiği | Listede |
|---|---|---|---|
| Mahya | 24,6 m | 10 | 10 |
| Metal dere | 39,2 m | 11 | 11 |
| Dere kelepçesi | 11 dere | 88 | 88 |
| İniş başına parçalar | 10 iniş | 10 · 10 · 20 · 10 · 20 | aynı |
| İniş sayısı | — | 7 (varsayılan) | 10 ✗ |
| Tavan alçıpan beyaz | 86,74 m² | 31 | 31 |
| Tavan alçıpan yeşil | 6,72 m² | 3 | 3 |
| Duvar alçıpan beyaz | 223,3 m² | 79 | 79 |
| Duvar alçıpan yeşil | 35,3 m² | 13 | 14 ✗ |
| Tavan omegası | 93,46 m² tavan | 42 | 44 ✗ |
| Dış cephe Boardex | 128 m² | 52 | 51 ✗ |
| Saçaklar için Boardex | 19,6 m² | 8 | 7 ✗ |

Çıkan sonuç: mahya, dere, kelepçe ve alçıpan kuralları üçüncü listede de tutuyor; iniş sayısı sabit değil (7, 7 ve 10); tavan omegası kuralı iki listede 2–3 eksik veriyor; levha adetlerinde yuvarlama listeden listeye değişiyor (yukarı, en yakına ya da bir fazla).

## Listelerden çıkan, kuralları etkileyen bilgiler

- Dış karkas 140 mm olunca duvar yalıtımı dış duvarlarda çift kat: 62 m² listede brüt 189 m² = 2 × dış duvar + iç duvar; 100 m² listede kalemin adında yazıyor.
- Yeşil tavan alçıpanı ıslak hacim ile veranda tavanına gidiyor görünüyor (iki listede de alan buna denk).
- Kırma çatıda mahya uzunluğu tepe ile kırmaların toplamı (62 m² listede 26,43 m); Lokman'ın 3 Ekim 11:57 kuralıyla aynı.
- Sandviç panelli çatıda çatı OSB'si ve metal kiremit yok; "sandviç panel kapaması" var (saçak boyunca).
- 62 m² listede saçak altı için ayrı Boardex kalemi var (saçak boyu × 30 cm).
- Bütün listelerde iç kapılar "melamin kapı (80'lik kanat) 90 × 214", dış kapı "kompozit çelik kapı 90 × 210".
- Çatı örtüsü projeden projeye değişiyor: OSB üstü metal kiremit, sandviç panel, tek kat panel, OSB üstü membran ve shingle.
- Dış cephede Boardex'in yanında dekoratif sıva, betopan ve yalıpan kalemleri de görülüyor.

## Ç8201 ilk taslak

Girdi `deneme/2026-10-03_yukleme/sonuc/C8201_girdi.json`: geometri Yapı Tanımı taslağından, varsayımlar dosyanın içinde. "Dış 140" sütunu yalnız değişen adetleri gösterir.

| Grup | Kalem | Boyut | Baz | Dış 140 | Ölçü (baz) | Durum |
|---|---|---|---|---|---|---|
| Dış cephe kaplama | Dış cephe Boardex | 1200 × 2400 | 33 | aynı | 80,7 m² | varsayim |
| İç cephe kaplama | Duvar alçıpan beyaz | 1200 × 2500 | 47 | 46 | 133,0 m² | excel |
| İç cephe kaplama | Duvar alçıpan yeşil | 1200 × 2500 | 8 | aynı | 20,7 m² | excel |
| İç cephe kaplama | Tavan alçıpan beyaz | 1200 × 2500 | 19 | aynı | 54,1 m² | uydurma |
| İç cephe kaplama | Tavan alçıpan yeşil | 1200 × 2500 | 8 | aynı | 22,6 m² | uydurma |
| İç cephe kaplama | OSB 9 mm (TV, klima ve mutfak dolabı arkası) | 1220 × 2440 |  |  |  | soru |
| İç cephe kaplama | Duvar izolasyonu | paket 8,64 m² | 13 | 23 | 111,1 m² | uydurma |
| Çatı kaplamaları | Sandviç panel | L 4300 · 100 cm kapatır | 26 | aynı | 98,4 m² | uydurma |
| Çatı kaplamaları | Metal kiremit mahyası | L 2800 | 11 | aynı | 27,0 m | varsayim |
| Çatı kaplamaları | Sandviç panel kapaması | L 2500 | 18 | aynı | 39,3 m | uydurma |
| Çatı kaplamaları | Çatı şiltesi 80 mm | 9,6 m²/adet | 10 | aynı | 88,9 m² | uydurma |
| Dere | Metal dere | L 4000 | 11 | aynı | 39,3 m | varsayim |
| Dere | Dere iniş borusu | L 3000 | 7 | aynı |  | soru |
| Dere | Dere iniş aparatı | adet | 7 | aynı |  | soru |
| Dere | Açık dirsek | adet | 14 | aynı |  | soru |
| Dere | Kapalı dirsek | adet | 7 | aynı |  | soru |
| Dere | İniş kelepçesi | adet | 14 | aynı |  | soru |
| Dere | Dere kelepçesi | adet | 88 | aynı |  | uydurma |
| Metal aksam | Saçak sacı (30'luk) | L 2500 | 18 | aynı | 39,3 m | uydurma |
| Metal aksam | Geniş saçak omegası (180 × 2500) | L 2500 | 18 | aynı | 39,3 m | uydurma |
| Metal aksam | Saçaklar için Boardex | 1200 × 2400 | 5 | aynı | 11,8 m² | uydurma |
| Metal aksam | Tavan omegası (60'lık) | L 3750 | 35 | 34 | 127,8 m | uydurma |
| Metal aksam | Köşebent | L 2500 | 56 | 55 | 139,4 m | soru |
| Metal aksam | Aşık | L 4200 | 49 | aynı | 193,5 m | uydurma |
| Kapı ve pencere | Melamin kapı (80'lik kanat) | 90 × 214 | 3 | aynı |  | model |
| Kapı ve pencere | Melamin kapı (çizimde 80 cm; listelerde bütün iç kapılar 90 × 214) | soru | 1 | aynı |  | soru |
| Kapı ve pencere | Kompozit çelik kapı | 90 × 210 | 1 | aynı |  | model |
| Kapı ve pencere | PVC pencere | 120/180 | 3 | aynı |  | model |
| Kapı ve pencere | PVC vasistas | 60/40 | 1 | aynı |  | model |
| Kapı ve pencere | PVC pencere | 120/100 | 1 | 3 |  | model |
| Kapı ve pencere | PVC pencere | 180/180 | 3 | aynı |  | model |
| Vida | Alçıpan vidası (3,5 × 35) | adet | 5000 | aynı | 120,0 levha | excel |
| Vida | Pencere vidası (4,8 × 70) | adet | 160 | aynı | 8,0 pencere | excel |
| Vida | İnox taş | adet | 9 | aynı | 82,0 m² | excel |

Taslakta olmayanlar:

- **Çelik panel grubu** (panel adedi ve kg). Karkas çiziminden gelir; Ç8201'in karkas çizimi yok. Örnek listelerde: 90 m² 44 panel 1980 kg; 62 m² 63 panel 1364 kg.
- Trapez vida ve çelik dübel (çelik panel adedine bağlı), vida grubunun kalanı, boya grubu, elektrik ve sıhhi tesisat.

## Açık sorular

1. Çelik panel adedi ve kg listeye nereden geliyor? Karkas yazılımının çıktısı model başına verilecek mi?
2. Ç8201'in baz paketinde çatı örtüsü sandviç panel mi? (2 Ekim'de "makasların üzerine 8 cm çatı paneli" denildi; 90 m² baz listede OSB üstü metal kiremit var.)
3. Veranda kolonu ve kirişi Boardex'le kaplanıyor mu? Kolon çevresi 0,76 m × 2,40 m ve kiriş çevresi 0,68 m her projede aynı mı?
4. Yeşil alçıpan: duvarda ıslak hacim, tavanda ıslak hacim ile veranda tavanı. Doğru mu?
5. Köşebent neye göre sayılıyor? (90 m²'de 70, 62 m²'de 50.)
6. İniş sayısı neye göre belirleniyor? (Listelerde 7, 7 ve 10.) Dere kapağı neye göre?
7. Mahya ve derede bindirme payı kaç cm? Özel geniş mahya ve ters mahya nereye konuyor?
8. Saçak altı Boardex mi, saçak sacı mı? İkisi birlikte mi?
9. OSB (TV, klima, mutfak dolabı arkası) hangi duvarlara, hangi ölçüyle konuyor?
10. Tavan omegasının aralığı 60 cm mi? Aşık aralığı sandviç panelde de 60 cm mi?
11. Banyo kapısı çizimde 80 cm; listelerde bütün iç kapılar 90 × 214. Hangisi?
12. Vida, boya, elektrik ve sıhhi tesisat grupları her listede olacak mı?
13. Zayiat: Boardex %15, alçıpan ve OSB %5. Kural böyle mi kalsın?
