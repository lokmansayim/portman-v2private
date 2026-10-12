# KT-02 · Lokman'ın 9 Ekim 22:22 ve 22:44 cevaplarından sonra

İkinci kör test (KT-02), Lokman'ın 9 Ekim 2026 22:22 ve 22:44 cevaplarından sonra. Gerçek listenin adetli her satırı, dondurulan iki listemizle (commit 59602ef) ve düzeltilmiş tanımdan güncel kural setiyle (0.17) çıkan listelerle. Cevaplar yazıldığı gibi: (1) 22:22 "Veranda korkuluğunun her tarafı kaplanıyor iç yüzde kaplanıyor"; 22:44 "var sayılan Boardex yap korkuluk çok önemli değil binde bir çıkar sen var sayılan olarak üst 8 cm iç ve dış ölçüsüne göre şeklinde kurala işle" (kural seti 0.17: korkuluk Boardex; iç ve dış yüz kendi ölçüleriyle, üstü 8 cm); (2) "evet yaz": 80 × 45 × 1,5 için 2,07 kg/m (0.16); (3) "evet girsin": açık sundurma bina alanına girer (hesap zaten öyleydi); (4) "Evet ekle": KT-02'nin tanımı ve çizimleri depoda. Kör listenin sınıfları 22:05 kıyasındaki gibidir (o anın kaydı); "kalan" sütunu cevaplardan sonraki durumu yazar.

Tablo `kt02_kiyas.py` ile üretilir; elle düzeltilmez. Sınıflar ve nedenler `kt02_farklar.json`dan; cevaplardan sonraki notlar `kt02_cevaplar_notlari.json`dan (üstüne yazar).

| Liste | Aynı satır | Ne demek |
|---|---|---|
| Kör liste, yapıldığı yöntemle (B) | 46 / 85 | dondurulan liste (commit 59602ef); kural seti 0.15; elektrik sayıları paftadan |
| Cevaplardan sonra (B) | 57 / 85 | düzeltilmiş tanım, güncel kural seti (0.17); adetler 22:05'teki düzeltilmiş listeyle aynı, 1,5 mm kirişin kg'ı yazılı |
| Kör liste, çelik standardıyla (A) | 46 / 85 | çatı ve tavan paneli: bu proje bugün sipariş edilse çıkacak liste (bilgi) |
| Cevaplardan sonra (A) | 56 / 85 | bilgi |

Kör listede (B) farklı 39 satırın asıl nedeni:

| Sınıf | Satır | Anlamı |
|---|---|---|
| girdi | 11 | girdi hatası |
| kural | 5 | kural hatası |
| karar | 13 | karar farkı |
| elle | 7 | listenin elle hesabı ya da yuvarlaması |
| pafta | 3 | paftadan sayılır |

Bizim hatamız (girdi + kural): 16 satır; ayrıca kör listede gerçek listede olmayan 3 satır (aşağıda).

Cevaplardan sonraki listede (B) farklı kalan 28 satır:

| Tür | Satır |
|---|---|
| karar | 18 |
| elle | 7 |
| pafta | 3 |

Çelik (adet, kg): gerçek liste 105 · 2051,3 — kör B 107 · 1994,3 — kör A 127 · 2728 — cevaplardan sonra B 107 · 2041,2 — cevaplardan sonra A 127 · 2774,9. 1,5 mm kiriş kör B, kör A listelerinde kg'sız (birim ağırlığı o gün kuralda yoktu), cevaplardan sonra B listesinde 46,89 kg, cevaplardan sonra A listesinde 46,89 kg (gerçek listede 46,89); A'da tavan ve çatı panelleri eklenir.

Gerçek listede adedi yazılmayan satırlar (bizim listede de yok): Pencereler (alıcıya ait), Boya grubu (alıcıya ait), Silikonize mastik (alıcıya ait).

## Kör listede (B) olup gerçek listede olmayan satırlar

| Kalem | Boyut | Adet | Sınıf | Neden |
|---|---|---|---|---|
| Alın sacı (30'luk) | 300 × 2500 | 1 | girdi | sundurmanın çatısını ana saçakta bitirip üstte kalan üçgeni kalkan saydık; iki eğik kenarı alın oldu. Düzeltilmiş tanımda yok. |
| Baş makas Z'si | L 2800 | 2 | girdi | aynı nedenle (iki alın kenarı). Düzeltilmiş tanımda yok. |
| Dere kapağı | adet | 2 | girdi | sundurmanın iki deresi ana saçakta serbest uçla bitiyordu. Düzeltilmiş tanımda dereler bağlı, kapak yok. |

Çelik standardıyla (A) gelen, gerçek listede olmayan satırlar: Tavan paneli (makas arası) (8), Çatı paneli (makas üstü, sırt 80 mm) (12), Saçaklar için OUTWEAR Dış Cephe Levhası (5), Saçak yüzü için OUTWEAR Dış Cephe Levhası (4).

## Adet dışı farklar (sayıma girmez)

- Çelik panel grubunun dokuz satırının hepsinde adet de kg da aynı (fark 0,1 kg'dan az; üretim dosyasındaki profil boyu × kuraldaki birim ağırlık). Listede / cevaplardan sonra: dış duvar 656,64 / 656,63; iç duvar 387,55 / 387,52; kolon 88,92 / 88,92; kiriş 1,2 mm 109,56 / 109,55; kiriş 1,5 mm 46,89 / 46,89 (kural seti 0.16: 2,07 kg/m); makas 429,27 / 429,24; çatı panelleri 226,18 / 226,10; veranda duvarı 56,05 / 56,04; veranda desteği 10,24 / 10,28 kg.
- Çelik toplamı: listede 105 adet, 2 051,3 kg; cevaplardan sonra 107 adet, 2 041,2 kg. Fark C profillerde: bizde 3 + 3 adet, 15 + 15 kg (motorun sabiti); listede 2 + 2 adet, 20 + 20 kg (Lokman, 8 Ekim: "C profiller hiç önemli değil").
- Dış cephe levhası listede 8 mm (Boardex); kural 12,5 mm (Lokman, 7 Ekim: listelerdeki 8 mm hatalı giriş). Listede veranda tavanı da aynı satırda.
- Çatı izolasyonu listede 100 mm; kural 80 mm (Lokman, 7 Ekim: listelerdeki 100 mm hatalı giriş). Adet aynı (11).
- Sandviç panel boyları: listede L 4400 ve L 1150; bizde L 4390 ve L 1160 (eğimli boy + 5 cm taşma, 10 mm'ye yukarı).
- Sandviç panel kapaması listede L 2800; kuralda L 2500.
- Saçak sacı listede "7 adet menfezli"; menfezli saçak sacının kuralı yok (KT-01'de de vardı: 4 adet).
- Elektrik: anahtar ve prizler listede "(antrasit)" yazılı (açıklama 6: prizler antrasit renk); bizim satırlarda renk yok. Tekli prizin 2'si listede "kapaklı" ayrı satır (muhtemelen veranda prizleri); toplam aynı (16).
- Kapılar listede sağ ve sol ayrı: melamin kapı 1 sağ + 3 sol, kompozit çelik kapı sağ. Bizde yön yok; toplam aynı.
- Boya ve silikonize mastik listede "alıcıya ait" (adetsiz): liste öncesi kararımızla aynı (açıklama 5).

## Satır satır

| Kalem (gerçek liste) | Gerçek | Kör B | Cevaplardan sonra B | Kör A | Sınıf | Neden | Cevaplardan sonra kalan |
|---|---|---|---|---|---|---|---|
| **Çelik panel** | | | | | | | |
| Dış cephe duvar panelleri | 8 | 8 | 8 | 8 |  |  |  |
| İç cephe duvar panelleri | 6 | 6 | 6 | 6 |  |  |  |
| Kolon | 6 | 6 | 6 | 6 |  |  |  |
| Kiriş (1,2) | 8 | 8 | 8 | 8 |  |  |  |
| Kiriş (1,5) | 1 | 1 | 1 | 1 |  |  kg: kural seti 0.16 ile 22,65 m × 2,07 kg/m (Lokman, 9 Ekim 22:22: "evet yaz"); gerçek listede 46,89. |  |
| Çatı makas panelleri | 33 | 33 | 33 | 33 |  |  |  |
| Çatı panelleri | 31 | 31 | 31 | 31 |  |  |  |
| Veranda duvarı (korkuluk) | 4 | 4 | 4 | 4 |  |  |  |
| Veranda destekleri | 4 | 4 | 4 | 4 |  |  |  |
| Parça C profil 1,2 | 2 | 3 ✗ | 3 ✗ | 3 ✗ | karar | kural motorun sabiti (3 adet, 15 kg); listede 2 adet, 20 kg. Lokman, 8 Ekim 07:23: C profiller önemli değil, öylesine gönderiliyor. | karar: motorun sabiti; listede 2. |
| Parça C profil 0,8 | 2 | 3 ✗ | 3 ✗ | 3 ✗ | karar | kural motorun sabiti (3 adet, 15 kg); listede 2 adet, 20 kg. | karar: motorun sabiti; listede 2. |
| **Metal aksam** | | | | | | | |
| Tavan omegası | 50 | 38 ✗ | 38 ✗ | — | karar | yöntem B kalemi; çelikte tavan omegası yok (Lokman, 7 Ekim 07:45). Kural tavan alanından (÷ 0,60 ÷ 3,75 = 38); liste paftadaki toplam boydan: 161,94 ÷ 3,65 + 5 = 50 (Eylül 2026 uygulaması; katmanla 48). | karar: yöntem B kalemi; listede paftadaki boy + 5. |
| Köşebent | 75 | 63 ✗ | 63 ✗ | 63 ✗ | karar | liste toplam boya +3 ekliyor ve boyu 177,64 m (bizde 155,66): verandanın ve sundurmanın köşeleri de sayılmış görünüyor (8 köşe × 2,7 = 21,6 m). Lokman, 7 Ekim: köşebent kuralı değişmedi. | karar: +3 ve veranda köşeleri; kural değişmedi. |
| Aşık | 58 | 53 ✗ | 53 ✗ | — | karar | yöntem B kalemi. Boy yakın (bizde 209,0 m, listede paftadan 205,47 m); formül farklı: kural × 1,05 ÷ 4,2 = 53, liste × 1,15 ÷ 4,1 = 58 (Eylül 2026 uygulaması). | karar: yöntem B kalemi; formül. |
| Saçak sacı | 20 | 21 ✗ | 20 | — | girdi | sundurmanın çatısı yanlış okundu: ana saçak sundurmanın önünde 2,1 m kesilir. Saçak 46,12 → 44,01 m (listede 44,1): 21 → 20. |  |
| Saçak omegası | 17 | 21 ✗ | 21 ✗ | — | karar | yöntem B kalemi. Kural her saçak kenarını ayrı yukarı yuvarlıyor (2025 listelerinden; 21); liste toplam boydan: 41,62 ÷ 2,5 = 17 (Eylül 2026 katmanı da 17 veriyor). | karar: yöntem B kalemi; formül. |
| **Dış cephe kaplama** | | | | | | | |
| Dış cephe Boardex (veranda tavanı dahil) | 46 | 51 ✗ | 51 ✗ | 51 ✗ | kural | veranda korkuluğunun iki yüzü Boardex sayıldı (13,35 m²); bu listede korkuluk Betopan (ayrı satır). Korkuluk çıkarılınca bizim hesap 38 + 8 (veranda tavanı) = 46: listedeki adet. | karar: korkuluk varsayılan Boardex: iç ve dış yüz kendi ölçüleriyle, üstü 8 cm (Lokman, 9 Ekim 22:44; kural seti 0.17). Bizde 43 + veranda tavanı 8 = 51; listede korkuluk Betopan, dış cephe levhası 46. |
| **İç cephe kaplama** | | | | | | | |
| Tavan alçıpan beyaz | 22 | 22 | 22 | 22 |  |  |  |
| Tavan alçıpan yeşil | 2 | 2 | 2 | 2 |  |  |  |
| Duvar alçıpan beyaz | 53 | 52 ✗ | 52 ✗ | 52 ✗ | karar | liste oda çevrelerini karkas yüzünden alıyor (65,42 m) ve zayiatı boşluklar düşülmeden uyguluyor; kural kaplanmış yüz (Lokman, 7 Ekim C8: bizdeki). | karar: ölçünün alındığı yüz. |
| Duvar alçıpan yeşil | 8 | 8 | 8 | 8 |  |  |  |
| İç duvar OSB | 61 | 59 ✗ | 59 ✗ | 59 ✗ | karar | aynı: liste karkas yüzünden (73,83 m), zayiat boşluklardan önce; kural kaplanmış yüz. | karar: ölçünün alındığı yüz. |
| Betopan (veranda korkuluk kaplaması) | 3 | — ✗ | — ✗ | — | kural | veranda korkuluğu bu listede 8 mm Betopanla kaplanmış (3 levha, 1250 × 2500); kuralımız yoktu, korkuluğu Boardex saydık (KT-01'de korkuluk Boardex'ti). | karar: korkuluk varsayılan Boardex (Lokman, 9 Ekim 22:44: "korkuluk çok önemli değil binde bir çıkar"); listede 3 Betopan (bir yüzü kadar). |
| Duvar izolasyonu | 16 | — ✗ | — ✗ | — | karar | Lokman, 7 Ekim 07:45: duvar izolasyonu gönderilmiyor; listede 16 paket. | karar: gönderilmiyor. |
| **Çatı kaplamaları** | | | | | | | |
| Sandviç panel (uzun) | 28 | 26 ✗ | 26 ✗ | 26 ✗ | pafta | liste adedi AutoCAD yerleşiminden alıyor: her şerit bir tam panel (28 × L 4400). Bizim dizilim çapraz kesilen parçaları eşliyor: 26 × L 4390. | pafta: yerleşimde parçalar eşlenmiyor. |
| Sandviç panel (kısa) | 8 | 5 ✗ | 6 ✗ | 5 ✗ | pafta | sundurmanın üç yüzüne paftada 8 panel (3 + 3 + 2, L 1150); bizde 5 (L 1160). Payı: girdi: sundurmanın çatısı vadiye kadar sürünce 5 → 6. | pafta: yerleşimde parçalar eşlenmiyor. |
| Metal kiremit mahyası | 13 | 13 | 13 | 13 |  |  |  |
| Sandviç panel kapaması | 18 | 21 ✗ | 20 ✗ | 21 ✗ | karar | kural L 2500, saçak (dere) boyu ÷ 2,3 (Lokman, 7 Ekim 08:02; 8 Ekim 00:45 onay); listede L 2800 ile 44,1 ÷ 2,6 = 16,96 (listede 18). Payı: girdi: saçak boyu 2,1 m uzundu (21 → 20). | karar: parça boyu L 2500 / L 2800. |
| Ters mahya | 2 | — ✗ | 2 | — | girdi | sundurmanın çatısı ana çatıya iki vadiyle bağlanıyor (kaplama paftasındaki çentik); biz ana saçakta bitirmiştik. Düzeltilmiş tanımda vadi 3,05 m (listede 3,05): 2. |  |
| Ters mahya kenar kutuları | 4 | — ✗ | 4 | — | girdi | ters mahya eksikti (aynı neden): 2 × 2 = 4. |  |
| Mahya bandı | 5 | 4 ✗ | 5 | 4 ✗ | girdi | formül ters mahyayı da sayıyor; ters mahya eksikti: 4 → 5. |  |
| Çatı izolasyonu | 11 | 11 | 11 | 11 |  |  |  |
| **Dere** | | | | | | | |
| Metal dere | 12 | 13 ✗ | 12 | 13 ✗ | girdi | dere boyu 2,1 m uzundu (sundurma): 46,12 → 44,01 m; 13 → 12. |  |
| Dere iniş borusu | 9 | 10 ✗ | 9 | 10 ✗ | girdi | sundurmanın iki deresi ana dereye bağlanmıyordu (iki serbest uç, ana batı saçağı tek parça 12,24 m): 8 köşe + 2 orta = 10. Düzeltilmiş tanımda 8 köşe + 1 orta = 9 (paftada 9). |  |
| Dere iniş aparatı | 9 | 10 ✗ | 9 | 10 ✗ | girdi | iniş sayısına bağlı (10 → 9). |  |
| Açık dirsek | 18 | 20 ✗ | 18 | 20 ✗ | girdi | iniş sayısına bağlı (20 → 18). |  |
| Kapalı dirsek | 9 | 10 ✗ | 9 | 10 ✗ | girdi | iniş sayısına bağlı (10 → 9). |  |
| İniş kelepçesi | 18 | 20 ✗ | 18 | 20 ✗ | girdi | iniş sayısına bağlı (20 → 18). |  |
| Dere kelepçesi | 96 | 104 ✗ | 96 | 104 ✗ | girdi | dere adedine bağlı (13 → 12): 104 → 96. |  |
| **Kapı ve pencere** | | | | | | | |
| Melamin kapı (80'lik kanat; sağ ve sol) | 4 | 4 | 4 | 4 |  |  |  |
| Kompozit çelik kapı | 1 | 1 | 1 | 1 |  |  |  |
| **Elektrik** | | | | | | | |
| Tijli duy | 5 | 5 | 5 | 5 |  |  |  |
| Yuvarlak glop | 4 | 4 | 4 | 4 |  |  |  |
| Ampul | 9 | 9 | 9 | 9 |  |  |  |
| NYM kablo (3 × 2,5) | 140 | 123 ✗ | 123 ✗ | 123 ✗ | elle | listede elle yazılmış; formülde uzaklık "yaklaşık": 9 × 11 + 21 × 2 = 141 → 140 okuması uyuyor. Bizde 9 × 9,00 + 21 × 2 = 123 (girişteki sigorta kutusundan kapalı kısmın en uzak köşesine). | elle: listenin uzaklık tahmini. |
| NYM kablo (2 × 1,5) | 120 | 99 ✗ | 99 ✗ | 99 ✗ | elle | listede elle yazılmış: 9 × 11 + (5 + 3 × 2) × 2 = 121 → 120 okuması uyuyor. Bizde 9 × 9,00 + 9 × 2 = 99. | elle: listenin uzaklık tahmini. |
| Uydu kablo | 25 | 25 | 25 | 25 |  |  |  |
| Besleme kablosu | 5 | 5 | 5 | 5 |  |  |  |
| Besleme kablo borusu | 5 | 5 | 5 | 5 |  |  |  |
| Tekli anahtar | 5 | 5 | 5 | 5 |  |  |  |
| Çiftli anahtar | 3 | 2 ✗ | 2 ✗ | 2 ✗ | pafta | elektrik paftasında iki çiftli anahtar işareti var (hol girişi, veranda); listede 3. Tekli anahtar (5) aynı. | pafta: listede paftadakinden bir fazla. |
| Tekli priz (kapaklı dahil) | 16 | 16 | 16 | 16 |  |  |  |
| Çiftli priz | 2 | 2 | 2 | 2 |  |  |  |
| Uydu prizi | 1 | 1 | 1 | 1 |  |  |  |
| Zil | 1 | 1 | 1 | 1 |  |  |  |
| Buat kasa | 35 | 31 ✗ | 31 ✗ | 31 ✗ | karar | kural: anahtar + priz + veranda hariç oda sayısı (5): 7 + 19 + 5 = 31 (Lokman, 7 Ekim C6: bizdekine uy). Listede 35: oda sayısı 8 sayılmış görünüyor; çiftli anahtar da 1 fazla. | karar: oda sayısı. |
| W otomat (sigorta) | 9 | 9 | 9 | 9 |  |  |  |
| Sigorta kutusu | 1 | 1 | 1 | 1 |  |  |  |
| İzole bant | 6 | 6 | 6 | 6 |  |  |  |
| Kaçak akım rölesi | 1 | 1 | 1 | 1 |  |  |  |
| **Vida** | | | | | | | |
| RYSB pul başlı | 700 | 690 ✗ | 690 ✗ | 690 ✗ | elle | listede 700: 90 × 7,5 = 675 yukarı yuvarlanmış. Bizde 92 × 7,5 = 690. Payı: karar: bina alanı 92 (açık sundurma dahil; Lokman, 9 Ekim 22:22), projede 90. | elle: listenin yuvarlaması. |
| Alçıpan vidası | 5 000 | 5 500 ✗ | 5 500 ✗ | 6 000 ✗ | elle | listenin formülü (levha × 40) 131 × 40 = 5240 verir; listede 5000 (aşağı yuvarlanmış). Bizde 135 × 40 = 5400 → 5500 (250'ye yukarı). Payı: karar: korkuluğun Boardex'i (Lokman, 9 Ekim 22:44: varsayılan Boardex). | elle: listenin yuvarlaması. |
| OSB ve yalıpan vidası | 2 900 | 3 000 ✗ | 3 000 ✗ | 3 000 ✗ | elle | listenin formülü 2884 verir, 2900'e yuvarlanmış; bizde 2832, kural 500'e yukarı yuvarlıyor (3000). | elle: listenin yuvarlaması. |
| Trapez vida (5,5 × 25) | 2 275 | 1 500 ✗ | 1 500 ✗ | 1 750 ✗ | karar | Lokman, 7 Ekim 07:45: omega ve aşık için trapez vida konmaz (panel × 10 + köşebent × 6 = 1388 → 1500); liste omega ve aşık için de sayıyor (2275). | karar: omega ve aşık vidası. |
| Trapez vida (5,5 × 60) | 250 | 250 | 250 | 250 |  |  |  |
| Trapez vida (5,5 × 110) | 750 | 750 | 750 | 750 |  |  |  |
| Çelik dübel | 34 | 36 ✗ | 36 ✗ | 36 ✗ | elle | listenin formülü (dış ve iç duvar paneli × 2) 28 verir; listede 34 (17 panel). Bizde korkuluk panelleri de sayılıyor: 18 × 2 = 36. | elle: listedeki sayı kendi formülüyle tutmuyor. |
| Şase pul | 34 | 36 ✗ | 36 ✗ | 36 ✗ | elle | çelik dübel kadar (34 / 36). | elle: çelik dübel kadar. |
| 8'lik trapez uç | 6 | 7 ✗ | 7 ✗ | 7 ✗ | kural | bina alanı 92,27 m² sayıldı (oturum; açık sundurma dahil); projede ve listede 90 m². 90 ile 6. | karar: açık sundurma bina alanına girer (Lokman, 9 Ekim 22:22: "evet girsin"): 92 m² ÷ 15 → 7; listede 90 ile 6. |
| PH2 uç | 6 | 7 ✗ | 7 ✗ | 7 ✗ | kural | aynı: bina alanı 92; 90 ile 6. | karar: bina alanı 92 (açık sundurma dahil; Lokman, 9 Ekim 22:22); listede 90 ile 6. |
| 230'luk kesme taşı | 2 | 7 ✗ | 7 ✗ | 7 ✗ | karar | Lokman, 7 Ekim 07:45: önemli değil, formül ne veriyorsa (bina ÷ 15 = 7); listede m² × 0,02 = 2 (Excel motoru). | karar: formül. |
| İnox taş | 9 | 10 ✗ | 10 ✗ | 10 ✗ | kural | bina alanı 92 (sundurma dahil): 9,2 → 10; 90 ile 9. | karar: bina alanı 92 (açık sundurma dahil; Lokman, 9 Ekim 22:22); listede 90 ile 9. |
| Çırpı ipi | 1 | 1 | 1 | 1 |  |  |  |
| Acil müdahale kapağı | 1 | 1 | 1 | 1 |  |  |  |
| **Sıhhi tesisat** | | | | | | | |
| Temiz su borusu | 6 | 6 | 6 | 6 |  |  |  |
| Normal dirsek 20 mm | 15 | 15 | 15 | 15 |  |  |  |
| Kulaklı dirsek 20 mm | 12 | 12 | 12 | 12 |  |  |  |
| Düz T 20 mm | 6 | 6 | 6 | 6 |  |  |  |
| Maşon 20 mm | 15 | 15 | 15 | 15 |  |  |  |
| İç dişli T 20 mm | 6 | 6 | 6 | 6 |  |  |  |
| Atlama parçası | 3 | 3 | 3 | 3 |  |  |  |
| **Boya** | | | | | | | |
| Dayson | 6 | 6 | 6 | 6 |  |  |  |
| Poliüretan köpük | 2 | 2 | 2 | 2 |  |  |  |
