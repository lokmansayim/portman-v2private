# KT-01 · kararlardan sonra durum

Lokman'ın 7 Ekim 2026 07:45 cevapları ve 08:02 düzeltmeleri işlendikten sonra, gerçek listenin adetli her satırı güncel kural setinin verdiği iki listeyle. Tablo `kararlar_kiyas.py` ile üretilir; elle düzeltilmez. Açıklamalar `kararlar_notlari.json`dan.

| Liste | Aynı satır | Ne demek |
|---|---|---|
| Düzeltilmiş (7 Ekim 03:46) | 48 / 98 | kararlardan önce: yalnız bizim hatalarımız düzeltilmişti |
| Kararlardan sonra, aynı yöntemle (B) | 63 / 98 | güncel kurallar; proje yapıldığı gibi tavan omegası ve aşıkla; elektrik sayıları paftadan |
| Kararlardan sonra, çelik standardıyla (A) | 60 / 98 | güncel kurallar; çatı ve tavan paneliyle: bu proje bugün sipariş edilse çıkacak liste |

Aynı yöntemle farklı kalan 35 satır:

| Tür | Satır | Anlamı |
|---|---|---|
| karar | 12 | Lokman'ın kararı o listeden farklı |
| yöntem | 3 | liste omega ve aşıklı yöntemle hazırlanmış; çelikte artık yok |
| elle | 16 | listenin elle hesabı, yuvarlaması ya da elle dizilimi |
| ölçü | 2 | ölçünün alındığı yüz (karar: bizdeki) |
| soru | 2 | kural bekliyor |

Çelik ağırlığı (kg): gerçek liste 1 937 · B 1 937 · A 2 588 (A'da tavan ve çatı panelleri eklenir).

## Çelik standardıyla (A) gelen, gerçek listede olmayan satırlar

| Kalem | Boyut | Adet | kg | Durum |
|---|---|---|---|---|
| Tavan paneli (makas arası) | roll form çelik | 7 | 291 | lokman |
| Çatı paneli (makas üstü, sırt 80 mm) | roll form çelik | 10 | 361 | lokman |
| Saçaklar için Boardex | 12,5 × 1200 × 2400 | 3 |  | uydurma |
| Saçak yüzü için Boardex | 12,5 × 1200 × 2400 | 2 |  | muhendis |
| Alın (kalkan kenarı) için Boardex | 12,5 × 1200 × 2400 | 4 |  | soru |

## Satır satır

| Kalem (gerçek liste) | Gerçek | Düzeltilmiş (03:46) | Kararlardan sonra (B) | Çelik standardı (A) | Değişikliği doğuran karar | Hâlâ farklıysa nedeni |
|---|---|---|---|---|---|---|
| **Çelik panel** | | | | | | |
| Dış cephe duvar panelleri | 9 | 9 | 9 | 9 |  |  |
| İç cephe duvar panelleri | 6 | 6 | 6 | 6 |  |  |
| Kolon | 1 | 1 | 1 | 1 |  |  |
| Kiriş | 3 | 3 | 3 | 3 |  |  |
| Veranda duvarı ve korkuluğu | 3 | 3 | 3 | 3 |  |  |
| Çatı makas panelleri | 16 | 16 | 16 | 16 |  |  |
| Baca karkası | 4 | 4 | 4 | 4 |  |  |
| Müştemilat duvar panelleri | 3 | 3 | 3 | 3 |  |  |
| Müştemilat çatı paneli | 1 | 1 | 1 | 1 |  |  |
| Parça C profil 1,2 | 3 | 3 | 3 | 3 |  |  |
| Parça C profil 0,8 | 3 | 3 | 3 | 3 |  |  |
| **Metal aksam** | | | | | | |
| Tavan omegası | 47 | 34 | 34 ✗ | — |  | yöntem: çelikte tavan omegası yok (C2). Kural prefabrik çalışılınca; duvar yüzünde omega hattı olmadığı da söylendi: listedeki 47 o paftanın dizilimi. |
| Köşebent | 76 | 67 | 67 ✗ | 67 ✗ |  | karar: önemli bir detay değil, mevcut kural uygulanır (C1 b, C7; 08:02). Listede 76. |
| Aşık | 54 | 48 | 48 ✗ | — |  | yöntem: çelikte aşık yok (C2). Kural prefabrik çalışılınca. |
| Alın sacı | 10 | 10 | 10 | — |  |  |
| Baş makas Z'si | 9 | 9 | 9 | — |  |  |
| Saçak sacı | 11 | 12 | 11 | — | Bindirme 20 cm (C1 a): 24,46 m ÷ 2,3 → 11. |  |
| Saçak omegası | 10 | 11 | 11 ✗ | — |  | yöntem: çatı ve tavan paneli varsa saçak omegası kullanılmaz (C1 c). Kural prefabrik çalışılınca. |
| **Dış cephe kaplama** | | | | | | |
| Dış cephe Boardex: bina (duvarlar, veranda içi, makas alnı, baca) | 47 | 44 | 44 ✗ | 44 ✗ |  | elle: listede makas alnı için iki tam kalkan alınmış, dört satır ayrı ayrı yukarı yuvarlanmış (değişmedi). |
| Dış cephe Boardex: müştemilat (duvarlar, çatı panelinin saçağı) | 13 | 11 | 11 ✗ | 11 ✗ |  | elle: listede müştemilat duvarları 2,70 m ile çarpılmış; modelde 2,25–2,50 m. Müştemilat göz ardı edilecek (C3). |
| Veranda tavanı (Boardex) | 5 | — | 5 | 5 | Çelikte veranda tavanı her zaman Boardex (C1 j): 12,4 m² → 5 levha. |  |
| Nem bariyeri: bina | 89 | 88 | 88 ✗ | 88 ✗ |  | ölçü: liste dış çevreyi karkas yüzünden alıyor; karar: bizdeki, kaplanmış yüz (C8). |
| Nem bariyeri: müştemilat | 32 | 27 | 27 ✗ | 27 ✗ |  | elle: listede müştemilat duvarları 2,70 m ile çarpılmış. Müştemilat göz ardı edilecek (C3). |
| **İç cephe kaplama** | | | | | | |
| Tavan alçıpan beyaz | 22 | 22 | 22 | 22 |  |  |
| Tavan alçıpan yeşil | 2 | 6 | 2 | 2 | Veranda tavanı Boardex'e geçti (C1 j): yeşil tavan yalnız ıslak hacim, 6 → 2. |  |
| Tavan alçıpan yeşil: müştemilat | 6 | 6 | 6 | 6 |  |  |
| Duvar alçıpan beyaz | 48 | 47 | 47 ✗ | 47 ✗ |  | ölçü: liste oda çevresini karkas yüzünden alıyor; karar: bizdeki, kaplanmış yüz (C8). |
| Duvar alçıpan yeşil | 7 | 7 | 7 | 7 |  |  |
| Duvar alçıpan yeşil: müştemilat | 10 | 9 | 9 ✗ | 9 ✗ |  | elle: listede müştemilat duvarları 2,70 m ile çarpılmış. Müştemilat göz ardı edilecek (C3). |
| İç duvar OSB | 55 | 55 | 55 | 55 |  |  |
| İç duvar OSB: müştemilat | 10 | 9 | 9 ✗ | 9 ✗ |  | elle: listede müştemilat duvarları 2,70 m ile çarpılmış. Müştemilat göz ardı edilecek (C3). |
| Duvar izolasyonu | 15 | 14 | — ✗ | — | Listeden çıktı: "göndermiyoruz yok say" (C1 h); 08:02: "evet çıkar". | karar: gönderilmiyor. Listede 15 paket var. |
| **Çatı kaplamaları** | | | | | | |
| Sandviç panel L 5070 | 17 | 16 | 16 ✗ | 16 ✗ |  | elle: listede paneller elle dizilmiş, çapraz kesilen parçalar eşlenmemiş; toplam aynı (33). Bizde boy 10 mm'ye yukarı: L 5080 (C9). |
| Sandviç panel L 3420 | 6 | 6 | 6 | 6 |  |  |
| Sandviç panel L 2870 | 6 | 5 | 5 ✗ | 5 ✗ |  | elle: listedeki dizilim; toplam aynı (33). Bizde L 2880 (C9). |
| Sandviç panel L 2340 | 4 | 6 | 6 ✗ | 6 ✗ |  | elle: listedeki dizilim; toplam aynı (33). Bizde L 2350 (C9). |
| Metal kiremit mahyası | 5 | 5 | 5 | 5 |  |  |
| Sandviç panel kapaması (bina ve müştemilat) | 12 | 14 | 14 ✗ | 14 ✗ |  | karar: kapama dere boyunca; parça L 2500, 20 cm bindirme (C1 i; 08:02): 29,92 m ÷ 2,3 = 13,01 → 14 (14. parça 2 cm'den doğuyor). Listede L 2800 ile 12. |
| Ters mahya | 2 | 2 | 2 | 2 |  |  |
| Ters mahya kenar kutuları | 4 | — | 4 | 4 | Listeye girdi: cumbalı çatılarda olmazsa olmaz (08:02); ters mahya 2 × 2 = 4. |  |
| Damlalık (bina ve müştemilat) | 6 | 5 | 5 ✗ | 5 ✗ |  | soru: damlalık listeden çıkık (C1 g). Bizdeki 5 adet, çatının duvara dayandığı kenar için geçici 'duvar dibi sacı' satırı; o kenara ne konacağı soruldu. |
| Mahya bandı | 4 | 3 | 3 ✗ | 3 ✗ |  | karar: damlalık olmadığı için formülde terimi de yok (C1 g): 3. Listede damlalık terimiyle 4. |
| Çatı izolasyonu | 10 | 10 | 10 | 10 |  |  |
| **Dere** | | | | | | |
| Metal dere | 7 | 7 | 7 | 7 |  |  |
| Dere iniş borusu | 7 | 5 | 7 | 7 | İniş kuralı (C4; eşik öneri): her saçak köşesine bir, boyu 9 m'yi geçen dere hattının ortasına bir: 5 köşe + 2 orta = 7. |  |
| Dere iniş aparatı | 7 | 5 | 7 | 7 | İniş sayısına bağlı (7). |  |
| Dere kapağı | 4 | 4 | 4 | 4 |  |  |
| Açık dirsek | 14 | 10 | 14 | 14 | İniş sayısına bağlı (7 × 2). |  |
| Kapalı dirsek | 7 | 5 | 7 | 7 | İniş sayısına bağlı (7). |  |
| İniş kelepçesi | 14 | 10 | 14 | 14 | İniş sayısına bağlı (7 × 2). |  |
| Dere kelepçesi | 56 | 56 | 56 | 56 |  |  |
| **Kapı ve pencere** | | | | | | |
| Melamin kapı (80'lik kanat) | 2 | 2 | 2 | 2 |  |  |
| Melamin kapı (70'lik kanat) | 1 | 1 | 1 | 1 |  |  |
| **Elektrik** | | | | | | |
| Tijli duy | 7 | 6 | 7 | 7 | Karar değil: elektrik sayıları bu listede projenin paftasından alındı. |  |
| Yuvarlak glop | 5 | 5 | 5 | 5 |  |  |
| Ampul | 12 | 11 | 12 | 12 | Karar değil: elektrik sayıları paftadan (duy + glop). |  |
| NYM kablo (3 × 2,5) | 140 | 180 | 137 ✗ | 137 ✗ | Kabloda en uzak mesafe sigortadan (C1 q): 10,06 m; sayılar paftadan: 9 × 10,06 + 23 × 2 → 137. | elle: listede 140 elle yazılmış (9 × 11 + 20 × 2 = 139 okuması uyuyor). |
| NYM kablo (2 × 1,5) | 120 | 160 | 115 ✗ | 115 ✗ | Kabloda en uzak mesafe sigortadan (C1 q): 10,06 m; sayılar paftadan: 9 × 10,06 + 12 × 2 → 115. | elle: listede 120 elle yazılmış. |
| Uydu kablo | 25 | 25 | 25 | 25 |  |  |
| Besleme kablosu | 5 | 5 | 5 | 5 |  |  |
| Besleme kablo borusu | 5 | 5 | 5 | 5 |  |  |
| Tekli anahtar | 4 | 5 | 4 | 4 | Karar değil: elektrik sayıları paftadan. |  |
| Çiftli anahtar | 4 | 3 | 4 | 4 | Karar değil: elektrik sayıları paftadan. |  |
| Tekli priz | 16 | 16 | 16 | 16 |  |  |
| Çiftli priz | 3 | 2 | 3 | 3 | Karar değil: elektrik sayıları paftadan. |  |
| Uydu prizi | 1 | 1 | 1 | 1 |  |  |
| Zil | 1 | 1 | 1 | 1 |  |  |
| Buat kasa | 35 | 32 | 33 ✗ | 33 ✗ | Karar değil: anahtar ve priz sayıları paftadan (28 + 5 oda = 33). | karar: oda sayısı bizdeki gibi (C6: "bizdekine uy"): 5 mahal. Listede 7 ile 35. |
| W otomat (sigorta) | 9 | 9 | 9 | 9 |  |  |
| Sigorta kutusu | 1 | 1 | 1 | 1 |  |  |
| İzole bant | 5 | 6 | 6 ✗ | 6 ✗ |  | elle: listede aşağı yuvarlanmış (5,9 → 5). |
| Kaçak akım rölesi | 1 | 1 | 1 | 1 |  |  |
| **Vida** | | | | | | |
| RYSB pul başlı | 750 | 743 | 743 ✗ | 743 ✗ |  | elle: listede 750'ye yuvarlanmış; bizde 743. |
| Alçıpan vidası | 8 000 | 6 250 | 6 250 ✗ | 6 500 ✗ |  | karar: levha başına 40 yeterli (C1 m). Listede levha başına 50 ve elle yuvarlama. |
| OSB ve yalıpan vidası | 3 550 | 3 000 | 3 000 ✗ | 3 000 ✗ |  | karar: levha başına 40 (C1 m). Listede 50 ve elle yuvarlama. |
| Trapez vida (5,5 × 25) | 1 800 | 1 750 | 1 000 ✗ | 1 250 ✗ | Yalnız çelik birleşim yerleri: panel başına 10, köşebent terimi duruyor (C1 n; 08:02): (46 panel + 6 parça C profil) × 10 + 67 × 6 = 922 → 1000. Parça C profiller şablondaki gibi sayıldı; sayılıp sayılmayacağı soruldu. | karar: omega ve aşık için vida konmaz. Listede onlar için de var (1800). |
| Trapez vida (5,5 × 60) | 250 | 250 | 250 | 250 |  |  |
| Trapez vida (5,5 × 110) | 750 | 750 | 750 | 750 |  |  |
| Çelik dübel | 42 | 42 | 42 | 42 |  |  |
| Şase pul | 42 | 42 | 42 | 42 |  |  |
| 8'lik trapez uç | 7 | 7 | 7 | 7 |  |  |
| PH2 uç | 7 | 7 | 7 | 7 |  |  |
| 230'luk kesme taşı | 2 | 7 | 7 ✗ | 7 ✗ |  | karar: önemli değil, formül ne veriyorsa (C1 o): 7. Listede 2. |
| İnox taş | 10 | 10 | 10 | 10 |  |  |
| Çırpı ipi | 1 | 1 | 1 | 1 |  |  |
| Acil müdahale kapağı | 1 | — | 1 | 1 | Her yapıya 1 adet, standart (C6). |  |
| **Boya** | | | | | | |
| Tavan boyası | 1 | 1 | 1 | 1 |  |  |
| Astar | 1 | 1 | 1 | 1 |  |  |
| Silikonize mastik | 3 | — | 7 ✗ | 7 ✗ | Pencere başına 1 adet (C6): 7 pencere → 7. | karar: pencere başına 1. Listede 3. |
| Dayson | 4 | 6 | 6 ✗ | 6 ✗ |  | karar: Excel motoruna uyulur (C1 p): m² × 0,06 → 6. Listede 4. |
| Poliüretan köpük | 2 | 2 | 2 | 2 |  |  |
