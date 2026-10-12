# KT-03 · kıyas

Üçüncü kör test (KT-03). Gerçek listenin adetli her satırı, dondurulan iki listemizle (commit 1f7ba6c, 9 Ekim 2026 23:55:13; liste 23:56'da açıldı) ve girdi hatalarımız düzeltildikten sonraki listeyle. Gerçek liste 23 Eylül 2026 tarihli, yeni şablonla ("ÇELİK BİNA"; bina alanı 80 m²), projenin yapıldığı yöntemle (B: tavan omegası ve aşık) hazırlanmış; "aynı" B listesinde sayılır. Üretim dosyası yoktu: çelikte adet karşılaştırılır, bizim kg motorun ortalamasıdır.

Tablo `kt03_kiyas.py` ile üretilir; elle düzeltilmez. Sınıflar ve nedenler `kt03_farklar.json`dan.

| Liste | Aynı satır | Ne demek |
|---|---|---|
| Kör liste, yapıldığı yöntemle (B) | 46 / 102 | dondurulan liste (commit 1f7ba6c); kural seti 0.17; elektrik sayıları paftadan |
| Düzeltilmiş (B) | 48 / 102 | yalnız girdi hatalarımız düzeltildi (makas adedi, veranda ve sundurma çatısının saçağı); kurallar aynı |
| Düzeltilmiş + Eylül 2026 uygulaması (B) | 54 / 102 | yalnız bilgi: `--sablon 2026` katmanı (KT-01'in Eylül 2026 listesinin uygulaması; Lokman 7 Ekim'de cevapladı, varsayılan hesapta değil) |
| Kural soruları listedeki gibi cevaplanırsa (B) | 55 / 102 | yalnız bilgi (`kt03_ne_olur.py`): çatı panelli veranda ve sundurmanın kenarları listedeki gibi (dere, iniş ve alın sacı var, Boardex şeridi yok, tavanı saçağıyla; özel büküm saçak sacı motorda yok); kırma uçlarının çatı panelleri paftadaki adetle |
| Kör liste, çelik standardıyla (A) | 45 / 102 | çatı ve tavan paneli: bu proje bugün sipariş edilse çıkacak liste (bilgi) |
| Düzeltilmiş (A) | 47 / 102 | bilgi |

Kör listede (B) farklı 56 satırın asıl nedeni:

| Sınıf | Satır | Anlamı |
|---|---|---|
| girdi | 2 | girdi hatası |
| kural | 21 | kural hatası |
| karar | 18 | karar farkı |
| elle | 9 | listenin elle hesabı ya da yuvarlaması |
| pafta | 6 | paftadan sayılır |

Bizim hatamız (girdi + kural): 23 satır; ayrıca kör listede gerçek listede olmayan 4 satır (aşağıda).

Düzeltilmiş listede (B) farklı kalan 54 satır:

| Tür | Satır |
|---|---|
| kural | 21 |
| karar | 18 |
| elle | 9 |
| pafta | 6 |

Kural soruları listedeki gibi cevaplanırsa (yalnız bilgi) değişen satırlar: Çatı panelleri (1,2 ve 0,8) 4 → 17 (aynı); Alın sacı (veranda ve sundurma) — → 3 (aynı); Dış cephe Boardex 40 → 39 (aynı); Veranda ve sundurma tavanı (Boardex) 6 → 7 (aynı); Metal dere 11 → 13 (aynı); Dere kapağı — → 4 (aynı); Dere iniş aparatı 9 → 13 (gerçek 11); Dere iniş borusu 9 → 13 (gerçek 11); Açık dirsek 18 → 26 (gerçek 22); Kapalı dirsek 9 → 13 (gerçek 11); İniş kelepçesi 18 → 26 (gerçek 22); Dere kelepçesi 88 → 104 (gerçek 110); Trapez vida (5,5 × 25) 1 250 → 1 500 (gerçek 2 100). Tutan hiçbir satır bozulmadı (denetlenir).

Çelik (adet, kg): gerçek liste 92 · 2 847 — kör B 87 · 2555,8 — kör A 104 · 3184,6 — düzeltilmiş B 85 · 2555,8 — düzeltilmiş A 102 · 3184,6 — + Eylül 2026 (B) 85 · 2555,8 — ne olur (B) 98 · 2555,8. Üretim dosyası olmadığı için bizim kg motorun proje ortalamalarıdır; A'da tavan ve çatı panelleri eklenir.

Gerçek listede adedi yazılmayan satırlar (bizim listede de yok): Melamin kapı (alıcıya ait).

## Kör listede (B) olup gerçek listede olmayan satırlar

| Kalem | Boyut | Adet | Sınıf | Neden |
|---|---|---|---|---|
| Ters mahya kenar kutusu | L 21 × 40 × 21 × 2800 | 8 | karar | Lokman, 7 Ekim 08:02: cumbalı çatılarda olmazsa olmaz (ters mahya × 2 = 8); bu listede yok (KT-02'nin listesinde vardı). |
| Besleme kablo borusu | metre | 5 | karar | motorun kalemi (kat × 5 m); bu listenin şablonunda yok (KT-02'nin listesinde vardı). |
| Şase pul | adet | 52 | karar | motorun kalemi (çelik dübel kadar); bu listenin şablonunda yok (KT-02'nin listesinde vardı). |
| Çırpı ipi | adet | 1 | karar | motorun kalemi (1); bu listenin şablonunda yok (KT-02'nin listesinde vardı). |

Çelik standardıyla (A) gelen, gerçek listede olmayan satırlar: Tavan paneli (makas arası) (7), Çatı paneli (makas üstü, sırt 80 mm) (10), Saçaklar için OUTWEAR Dış Cephe Levhası (5), Saçak yüzü için OUTWEAR Dış Cephe Levhası (3), Ters mahya kenar kutusu (8), Besleme kablo borusu (5), Şase pul (52), Çırpı ipi (1).

## Adet dışı farklar (sayıma girmez)

- Çelik ağırlığı (üretim dosyası yok; bizde motorun proje ortalamaları). Listede / bizde: dış duvar 1 103 / 1 140,4 (39,27 m; listede 28,1 kg/m, kural ortalaması 29,04); iç duvar 536 / 467,3 (23,66 m; listede 22,7 kg/m, kural 19,75); makas 667 / 681,3; çatı panelleri 312 / 64,9 (bizde yalnız veranda ve sundurma; kırma uçlarınınki makas satırında); baca 98 / 55,8; kolon ve kiriş 131 / 116,1; toplam 2 847 / 2 555,8 kg (listede C profiller kg'sız).
- Listenin çelik toplamı 92 adet C profilleri saymıyor (onlar 3 + 3, kg'sız); bizim toplamımız sayıyor (düzeltilmiş B'de 85 = 79 panel + 6 C profil).
- Et kalınlığı: listede makasların 4'ü ve çatı panellerinin 5'i 80 × 1,2; kuralda çatı çeliği 0,8. Dış duvar 140 × 1,2, iç duvar 80 × 1,2, baca 80 × 0,8 (bizimle aynı).
- Listenin yeni sütunu: çelik panelin üretildiği rulo form makinesi (140'lık duvar büyük makinede, öbürleri 1,2 ve 0,8 ayarlı küçük makinede).
- Saçak omegası listede "180'lik geniş saçak omegası (140'lık duvarlar için)" (L 2500); bizde "saçak omegası": 140 mm duvarlı binada ürün ve ölçü kuralı yok.
- Sandviç panel boyları: listede 3660, 3500, 3250, 3000, 2500, 1750 (paftadaki yerleşim); bizde 3680, 3550, 3290, 3160, 2620, 2370, 1630. Paftadaki çatı alanı 112 m² (bizde 112,45 m²).
- Sandviç panel kapaması listede "tek kat panel ve sandviç panel uç kapaması" L 2800; kuralda L 2500.
- Dış cephe levhası listede 12 mm Boardex; kural 12,5 mm. Veranda tavanı satırının adı listede "veranda, sundurma, balkon, tavan".
- Çatı izolasyonu listede Knauf mineral yünü (paket 8,64 m²); bizde çatı şiltesi 80 mm (9,6 m²/adet). Adet aynı (11).
- Pencereler listede pervaz, matik, çift açılım ya da sürgülü, antrasit, Winsa yazılı; 50/50 "vasistas" (bizim kural yalnız 60/40'ı vasistas sayıyor). Adetler aynı.
- Elektrik: listede "duylu armatür" ve "LED ampul" (bizde tijli duy ve ampul); adet aynı. Kompozit çelik kapı listede "(sağ)".
- Bina alanı: liste 80 m² (kapalı kısım); bizde 94 (oturum 93,81 m²: veranda ve açık sundurma dahil; Lokman, 9 Ekim 22:22). Boya kovaları ikisinde de aynı çıktı (80 × 0,02 ve 94 × 0,02 → 2).

## Satır satır

| Kalem (gerçek liste) | Gerçek | Kör B | Düzeltilmiş B | Kör A | Sınıf | Neden | Düzeltilmiş listede kalan |
|---|---|---|---|---|---|---|---|
| **Çelik panel** | | | | | | | |
| Dış cephe duvar panelleri | 15 | 15 | 15 | 15 |  |  |  |
| İç cephe duvar panelleri | 11 | 11 | 11 | 11 |  |  |  |
| Çatı makas panelleri (1,2 ve 0,8) | 34 | 36 ✗ | 34 | 36 ✗ | girdi | makas ve dere paftasında makaslar MK02–MK13 ve MK15–MK36: 34 makas (MK01 ve MK14 numarası yok). Numaraların kesintisiz olduğunu varsayıp 36 saydık. Listede 4 × 1,2 mm + 30 × 0,8 mm = 34. |  |
| Çatı panelleri (1,2 ve 0,8) | 17 | 4 ✗ | 4 ✗ | 4 ✗ | kural | katalog yolunda (üretim dosyası yok) kırma uçlarının çatı panelleri ayrı satır değil; ağırlıkları makas satırındaki ortalamanın içinde (liste öncesi karar 1). Paftada Ç01–Ç18 (Ç10 yok) = 17 panel: kırma uçlarında 13, veranda ve sundurmada 4 (bizim satırımız). Listede 5 × 1,2 + 12 × 0,8 = 17. | kural: kırma uçlarının çatı panelleri katalog yolunda satır değil. |
| Baca panelleri | 8 | 8 | 8 | 8 |  |  |  |
| Kolon ve kiriş panelleri | 7 | 7 | 7 | 7 |  |  |  |
| Parça C profil 1,2 | 3 | 3 | 3 | 3 |  |  |  |
| Parça C profil 0,8 | 3 | 3 | 3 | 3 |  |  |  |
| **Metal aksam** | | | | | | | |
| Tavan omegası | 40 | 31 ✗ | 31 ✗ | — | karar | yöntem B kalemi; çelikte tavan omegası yok (Lokman, 7 Ekim 07:45). Kural tavan alanından (114,2 m ÷ 3,75 = 31); liste paftadaki toplam boydan: 127,76 ÷ 3,65 + 5 = 40 (Eylül 2026 uygulaması; katmanla 40). | karar: yöntem B kalemi; listede paftadaki boy + 5. |
| Köşebent | 70 | 74 ✗ | 74 ✗ | 74 ✗ | elle | listede toplam boy 173,37 m ÷ 2,5 = 70; boyun nasıl bulunduğu formülde yok. Bizde kural (mühendis, 4 Ekim): oda tavan çevreleri 84,42 + veranda tavanı çevresi 20,14 + 29 iç köşe × 2,7 = 182,86 m → 74. | elle: listenin toplam boyu formülsüz. |
| Aşık | 52 | 47 ✗ | 47 ✗ | — | karar | yöntem B kalemi. Boy çok yakın (bizde 185,5 m, listede paftadan 187 m); formül farklı: kural × 1,05 ÷ 4,2 = 47, liste 187 ÷ 4,1 = 45,6 ve adet 52 (Eylül 2026 uygulaması × 1,15 ÷ 4,1 = 52,5; katmanla 53). | karar: yöntem B kalemi; formül. |
| Alın sacı (veranda ve sundurma) | 3 | — ✗ | — ✗ | — | kural | listede veranda ve sundurmanın tek eğimli panel çatılarının eğik kenarlarında "sıfır alın sacı" var (5,2 m ÷ 2,5 → 3). Kuralımız (KT-01'in çatı panelli müştemilatından) çatı panelli çatıda alın sacı yazmıyor; kenarı Boardex şeridi sayıyor. | kural: çatı panelli çatının kenarları sorulacak. |
| Saçak sacı | 19 | 19 | 19 | — |  |  |  |
| Özel büküm saçak sacı | 3 | — ✗ | — ✗ | — | kural | listede veranda ve sundurma çatısının saçaklarında özel büküm saçak sacı (3; iki saçak 5,7 m). Kuralımızda çatı panelli çatıda saçak sacı yok; böyle bir kalem de yok. | kural: çatı panelli çatının kenarları sorulacak. |
| Saçak omegası (geniş, 140'lık duvar) | 16 | 21 ✗ | 21 ✗ | — | karar | yöntem B kalemi. Kural her saçak kenarını ayrı yukarı yuvarlıyor (2025 listelerinden; 21); liste saçaksız cephe boyundan: 40 ÷ 2,5 = 16 (Eylül 2026 katmanı da 16 veriyor; bizim cephe boyu 37,9 m). Listede 140'lık duvar için 180'lik geniş saçak omegası (ürün adı ve ölçüsü: adet dışı farklarda). | karar: yöntem B kalemi; formül. |
| **Dış cephe kaplama** | | | | | | | |
| Dış cephe Boardex | 39 | 40 ✗ | 40 ✗ | 40 ✗ | kural | çatı panelli veranda ve sundurmanın saçak ve alınlarına kuralımız Boardex şeridi ekledi (11,8 m × 0,25 m = 2,9 m²); listede bu kenarlar sacla (özel büküm saçak sacı, sıfır alın sacı). Şerit çıkınca 103,0 m² → 39 (listedeki adet). | kural: çatı panelli çatının kenarları sorulacak. |
| Veranda ve sundurma tavanı (Boardex) | 7 | 6 ✗ | 6 ✗ | 6 ✗ | kural | listede veranda ve sundurmanın tavanı çatılarının saçağıyla birlikte (veranda çatısı 14,84 m² paftada + sundurma; 16,8–17,5 m² → 7). Bizde dış ölçüyle 14,73 m² → 6; saçak altı için kuralımız (KT-01) 15 cm Boardex şeridi sayıyordu. | kural: çatı panelli çatının kenarları sorulacak. |
| **İç cephe kaplama** | | | | | | | |
| Tavan alçıpan beyaz | 23 | 22 ✗ | 22 ✗ | 22 ✗ | karar | liste tavanı karkas yüzlerinden ölçüyor görünüyor (beyaz mahaller 63,6 m² + kiriş 0,8 → 22,5 → 23); kural kaplanmış yüz (Lokman, 7 Ekim C8): 62,7 m² → 22. | karar: ölçünün alındığı yüz. |
| Tavan alçıpan yeşil | 3 | 3 | 3 | 3 |  |  |  |
| Duvar alçıpan beyaz | 59 | 58 ✗ | 58 ✗ | 58 ✗ | karar | liste oda çevrelerini karkas yüzünden alıyor (KT-02'deki gibi); kural kaplanmış yüz (Lokman, 7 Ekim C8): 164,9 m² → 58. | karar: ölçünün alındığı yüz. |
| Duvar alçıpan yeşil | 10 | 10 | 10 | 10 |  |  |  |
| İç duvar OSB | 70 | 68 ✗ | 68 ✗ | 68 ✗ | karar | liste OSB'yi duvar alçıpanından çeviriyor görünüyor (59 + 10 levha × 3,0 ÷ 2,98 = 69,5 → 70); kural bütün iç yüzler × 1,05 ÷ 2,98 = 67,5 → 68. | karar: ölçünün alındığı yüz ve formül. |
| Duvar izolasyonu | 29 | — ✗ | — ✗ | — | karar | Lokman, 7 Ekim 07:45: duvar izolasyonu gönderilmiyor. Listede 250 m² ÷ 8,64 = 29 paket (dış duvar iki kat + iç duvar; bizim yalıtım alanımız 249 m², aynı). | karar: gönderilmiyor. |
| **Çatı kaplamaları** | | | | | | | |
| Sandviç panel (altı boy, toplam) | 43 | 47 ✗ | 47 ✗ | 47 ✗ | pafta | liste adedi çatı kaplaması yerleşim paftasından alıyor (366 × 6, 350 × 16, 325 × 14, 300 × 1, 250 × 4, 175 × 2 = 43; paftada çatı alanı 112 m², bizde 112,45 m²). Bizim dizilimimiz yedi boy, 47 panel. | pafta: yerleşim paftasındaki dizilim. |
| Mahya sacı | 14 | 14 | 14 | 14 |  |  |  |
| Sandviç panel kapaması | 19 | 21 ✗ | 21 ✗ | 21 ✗ | karar | kural L 2500, saçak boyu ÷ 2,3 (Lokman, 7 Ekim 08:02; 8 Ekim 00:45 onay): 47,25 ÷ 2,3 → 21; listede L 2800 (÷ 2,6 → 19; KT-02'deki gibi). | karar: parça boyu L 2500 / L 2800. |
| Ters mahya (vadi sacı) | 4 | 4 | 4 | 4 |  |  |  |
| Damlalık (duvar dibi ve baca; bizde özel mahya) | 6 | 4 ✗ | 4 ✗ | 4 ✗ | karar | çatının duvara dayandığı kenar kuralda özel mahya satırında (kural seti 0.14; damlalık listeden çıkarıldı, Lokman 4 Ekim 15:18): 9,62 m ÷ 2,6 → 4. Listede damlalık: (duvar dibi 10,9 m + bacanın çevresi 2 × (0,84 + 0,38)) ÷ 2,6 → 6. | karar: kalem ve bacanın çevresi. |
| Çatı çıkış kapağı | 1 | — ✗ | — ✗ | — | kural | planda holde "çatı çıkış kapağı 90 × 60" çizili; listede çatı kaplamalarında "çatı çıkış kapağı (çatı kaplamasıyla uyumlu, özel ölçü)" 1 adet, ayrıca depo grubunda acil müdahale kapağı 1 (bizde de 1). Çatı çıkış kapağı için kuralımız yok. | kural: çatı çıkış kapağı sorulacak. |
| İzolasyon bandı (mahya, baca) | 7 | 6 ✗ | 6 ✗ | 6 ✗ | karar | liste formülü damlalığı da sayıyor: (mahya 14 + vadi 4 + damlalık 6) × 2,8 + baca 2,44 = 69,6 m → 7. Kural (mühendis, 4 Ekim; damlalık terimi yok: Lokman): (14 + 4) × 2,8 + baca çevresi 3,04 = 53,4 m → 6. Eylül 2026 katmanı 7. | karar: damlalık terimi. |
| Çatı izolasyonu | 11 | 11 | 11 | 11 |  |  |  |
| **Dere** | | | | | | | |
| Metal dere | 13 | 11 ✗ | 11 ✗ | 11 ✗ | kural | listede veranda ve sundurma çatısının saçaklarında da dere var (dere paftasında da): 41,52 + 5,72 = 47,24 m → 13. Kuralımız (KT-01'in çatı panelli müştemilatı) çatı panelli çatıda dere yazmıyor: 11. | kural: çatı panelli çatının deresi sorulacak. |
| Dere kapağı | 4 | — ✗ | — ✗ | — | kural | veranda ve sundurma derelerinin dört serbest ucu (aynı neden; kuralımızda dere yoktu). | kural: çatı panelli çatının deresi sorulacak. |
| Dere iniş aparatı | 11 | 9 ✗ | 9 ✗ | 9 ✗ | kural | iniş sayısı: paftada 11 (ana çatı 8, veranda 2, sundurma 1); bizde 9 (8 köşe + 1 orta). Ana çatıda sundurmanın üstüne düşen iç köşede paftada iniş yok; veranda ve sundurmada dere olmadığı için inişleri yoktu. | kural: çatı panelli çatının deresi ve alçak çatının üstündeki köşe sorulacak. |
| Dere iniş borusu | 11 | 9 ✗ | 9 ✗ | 9 ✗ | kural | iniş sayısına bağlı (aynı neden): 9 / 11. | kural: iniş sayısı (aynı). |
| Açık dirsek | 22 | 18 ✗ | 18 ✗ | 18 ✗ | kural | iniş sayısına bağlı (iniş × 2): 18 / 22. | kural: iniş sayısı (aynı). |
| Kapalı dirsek | 11 | 9 ✗ | 9 ✗ | 9 ✗ | kural | iniş sayısına bağlı: 9 / 11. | kural: iniş sayısı (aynı). |
| İniş kelepçesi | 22 | 18 ✗ | 18 ✗ | 18 ✗ | kural | iniş sayısına bağlı (iniş × 2): 18 / 22. | kural: iniş sayısı (aynı). |
| Dere kelepçesi | 110 | 88 ✗ | 88 ✗ | 88 ✗ | kural | dere adedine bağlı (dere × 8): 11 dereyle 88. Listede 110 (13 dereyle kural 104 verir; 110 iniş × 10'a uyuyor). | kural: dere adedi (aynı); kalanı elle. |
| **Kapı ve pencere** | | | | | | | |
| PVC pencere 150/130 | 3 | 3 | 3 | 3 |  |  |  |
| PVC pencere 200/220 (sürgülü) | 2 | 2 | 2 | 2 |  |  |  |
| PVC pencere 100/70 | 1 | 1 | 1 | 1 |  |  |  |
| PVC vasistas 50/50 | 1 | 1 | 1 | 1 |  |  |  |
| Kompozit çelik kapı | 1 | 1 | 1 | 1 |  |  |  |
| **Elektrik** | | | | | | | |
| Duylu armatür (tijli duy) | 7 | 7 | 7 | 7 |  |  |  |
| Yuvarlak glop | 4 | 4 | 4 | 4 |  |  |  |
| Ampul | 11 | 11 | 11 | 11 |  |  |  |
| NYM kablo (3 × 2,5) | 140 | 133 ✗ | 133 ✗ | 133 ✗ | elle | liste formülü 9 × 9,9 + (14 + 1 + 4 × 2) × 2 = 135,1, yazılan 140 (10'a yukarı). Bizde 9 × 9,88 + (13 + 1 + 4 × 2) × 2 = 132,9 → 133; uzaklık aynı (9,88 / 9,9), tekli priz bir eksik (paftada 13). | elle: listenin yuvarlaması. |
| NYM kablo (2 × 1,5) | 120 | 111 ✗ | 111 ✗ | 111 ✗ | elle | liste formülü 9 × 9,9 + (5 + 3 × 2) × 2 = 111,1, yazılan 120 (10'a yukarı); bizde 110,9 → 111. | elle: listenin yuvarlaması. |
| Uydu kablo | 25 | 25 | 25 | 25 |  |  |  |
| Besleme kablosu | 5 | 5 | 5 | 5 |  |  |  |
| Tekli anahtar | 5 | 5 | 5 | 5 |  |  |  |
| Çiftli anahtar | 3 | 3 | 3 | 3 |  |  |  |
| Tekli priz | 14 | 13 ✗ | 13 ✗ | 13 ✗ | elle | elektrik paftasında 13 tekli priz (kıyastan sonra yeniden sayıldı: salon 3, yatak odası 3, çocuk odası 3, mutfak 3, banyo 1); listede 14. | elle: listede paftadakinden bir fazla. |
| Çiftli priz | 4 | 4 | 4 | 4 |  |  |  |
| Uydu prizi | 1 | 1 | 1 | 1 |  |  |  |
| Buat kasa | 50 | 32 ✗ | 32 ✗ | 32 ✗ | karar | kural: anahtar + priz + veranda hariç oda sayısı = 8 + 18 + 6 = 32 (Lokman, 7 Ekim C6: bizdekine uy). Listede 50 (formül yok). | karar: formül. |
| Sigorta kutusu | 1 | 1 | 1 | 1 |  |  |  |
| W otomat (sigorta) | 9 | 9 | 9 | 9 |  |  |  |
| Kaçak akım rölesi | 1 | 1 | 1 | 1 |  |  |  |
| İzole bant | 4 | 6 ✗ | 6 ✗ | 6 ✗ | elle | kural bina m² × 0,06 (94 → 5,6 → 6; 80 ile 4,8 → 5); listede 4 (formül yok). | elle: listedeki sayı formülsüz. |
| Zil | 1 | 1 | 1 | 1 |  |  |  |
| **Vida** | | | | | | | |
| RYSB pul başlı | 600 | 705 ✗ | 705 ✗ | 705 ✗ | karar | bina alanı: kural kapalı kısım + veranda + açık sundurma = 94 m² (Lokman, 9 Ekim 22:22); liste 80 × 7,5 = 600. | karar: bina alanı. |
| Alçıpan vidası | 7 100 | 5 750 ✗ | 5 750 ✗ | 6 000 ✗ | karar | kural levha × 40 (Lokman, 7 Ekim 07:45: 40 yeterli): 139 × 40 → 5750; liste levha × 50: 141 × 50 = 7050 → 7100. | karar: levha başına vida. |
| OSB ve yalıpan vidası | 4 000 | 3 500 ✗ | 3 500 ✗ | 3 500 ✗ | elle | listenin formülü OSB × 50 = 3500, yazılan 4000; bizde 3132 → 3500 (500'e yukarı). | elle: listenin yuvarlaması. |
| Pencere vidası (4,8 × 70) | 140 | 140 | 140 | 140 |  |  |  |
| Trapez vida (5,5 × 25) | 2 100 | 1 500 ✗ | 1 250 ✗ | 1 500 ✗ | karar | Lokman, 7 Ekim 07:45: omega ve aşık için trapez vida konmaz (çelik panel × 10 + köşebent × 6 = 1254 → 1500); liste omega ve aşık için de sayıyor (92 × 10 + 52 × 10 + 40 × 6 + 70 × 6 = 2100). Payı: girdi: makas 36 → 34 (çelik panel 81 → 79): 1254 → 1234, 1500 → 1250. | karar: omega ve aşık vidası. |
| Trapez vida (5,5 × 60) | 250 | 250 | 250 | 250 |  |  |  |
| Trapez vida (5,5 × 110) | 1 000 | 750 ✗ | 750 ✗ | 750 ✗ | elle | listenin formülü (panel boyu ÷ 200 × adet) 699,8 verir, yazılan 1000; bizde 681,8 → 750 (250'ye yukarı). | elle: listenin yuvarlaması. |
| **Depo** | | | | | | | |
| Çelik dübel | 76 | 52 ✗ | 52 ✗ | 52 ✗ | elle | kural duvar paneli × 2 = 26 × 2 = 52 (Excel motoru); listede 76 (formül yok; dış 15 + iç 11 + baca 8 + kolon 4 = 38 panel × 2 okuması uyuyor, KT-02'de bu okuma tutmuyordu). | elle: listedeki sayı formülsüz. |
| 8'lik trapez uç | 6 | 7 ✗ | 7 ✗ | 7 ✗ | karar | bina alanı 94 (Lokman, 9 Ekim 22:22: açık sundurma da girer): 94 ÷ 15 → 7; listede 80 ÷ 15 → 6. | karar: bina alanı. |
| PH2 uç | 6 | 7 ✗ | 7 ✗ | 7 ✗ | karar | aynı: bina alanı 94 → 7; listede 80 → 6. | karar: bina alanı. |
| 230'luk kesme taşı | 2 | 7 ✗ | 7 ✗ | 7 ✗ | karar | Lokman, 7 Ekim 07:45: önemli değil, formül ne veriyorsa (bina ÷ 15 = 7); listede m² × 0,02 = 1,6 → 2 (Excel motoru; Eylül 2026 katmanı da 2). | karar: formül. |
| İnox taş | 8 | 10 ✗ | 10 ✗ | 10 ✗ | karar | bina alanı 94 ÷ 10 → 10; listede 80 ÷ 10 = 8. | karar: bina alanı. |
| Acil müdahale kapağı | 1 | 1 | 1 | 1 |  |  |  |
| Poliüretan köpük | 2 | 2 | 2 | 2 |  |  |  |
| Dayson | 5 | 6 ✗ | 6 ✗ | 6 ✗ | elle | listenin formülü 80 × 0,04 = 3,2, yazılan 5; kural bina m² × 0,06 (Excel motoru; Lokman, 7 Ekim: motora uy) = 5,6 → 6. | elle: listenin yuvarlaması. |
| Mastik | 7 | 7 | 7 | 7 |  |  |  |
| Baca borusu | 2 | — ✗ | — ✗ | — | kural | açıklama 4: "Baca olacak. (Karkas ve içi de olacak.)" Bacanın içi için kuralımız yok (liste öncesi karar 6: soru). Listede iki bacaya birer takım: baca borusu 4,3 m, T, kör tapa, maşon, şapka (40 × 40). | kural: bacanın içi sorulacak. |
| Baca T'si | 2 | — ✗ | — ✗ | — | kural | bacanın içi (aynı): 2. | kural: bacanın içi sorulacak. |
| Baca kör tapa | 2 | — ✗ | — ✗ | — | kural | bacanın içi (aynı): 2. | kural: bacanın içi sorulacak. |
| Baca maşonu | 2 | — ✗ | — ✗ | — | kural | bacanın içi (aynı): 2. | kural: bacanın içi sorulacak. |
| Baca şapkası | 2 | — ✗ | — ✗ | — | kural | bacanın içi (aynı): 2 × 40 × 40. | kural: bacanın içi sorulacak. |
| **Mekanik tesisat** | | | | | | | |
| Temiz su borusu | 6 | 6 | 6 | 6 |  |  |  |
| Normal dirsek 20 mm | 15 | 15 | 15 | 15 |  |  |  |
| Kulaklı dirsek 20 mm | 12 | 12 | 12 | 12 |  |  |  |
| Düz T 20 mm | 6 | 6 | 6 | 6 |  |  |  |
| Maşon 20 mm | 15 | 15 | 15 | 15 |  |  |  |
| Taharet musluğu 20 mm | 4 | — ✗ | — ✗ | — | kural | listenin mekanik tesisat grubunda taharet musluğu 4; kuralımızın sıhhi tesisat takımında bu kalem yok (KT-01 ve KT-02 listelerinde de yoktu). | kural: taharet musluğu sorulacak. |
| İç dişli T 20 mm | 6 | 6 | 6 | 6 |  |  |  |
| Atlama parçası | 3 | 3 | 3 | 3 |  |  |  |
| **Boya** | | | | | | | |
| Dış cephe boyası | 2 | 2 | 2 | 2 |  |  |  |
| İç cephe boyası | 2 | 2 | 2 | 2 |  |  |  |
| Tavan boyası | 1 | 1 | 1 | 1 |  |  |  |
| Astar | 1 | 1 | 1 | 1 |  |  |  |
