# AIPrefabrik inceleme seti E1–E5 · açık sorulara kanıt (13 Ekim 2026)

Lokman, 13.10 14:11: "doğrulanmış, üretilmiş gerçek prefabrik projeler; ilk 5'ini incele, sorularını tekrar sırayla sor; kalanlar test verisi".
Klasör `~/Desktop/AIPrefabrik/`. Mühür ve test seti `test_seti/MUHUR.md`.

- **Bu not kör test değil, inceleme.** Listeler paftalarla birlikte açıldı.
- **Kaynaklar** `kaynak/E*/`. SHA'lar mühürle aynı.
- **Okunmuş listeler** `gercek/E*_gercek.json`, `liste_oku.py` ile okundu. Telefon alanı okunmaz. Taramada telefon ya da 11 haneli numara 0.

| | Proje | m² | Çatı / tavan | Liste şablonu | Hazırlayan, tarih | Satır / dolu |
|---|---|---|---|---|---|---|
| E1 | Modern Prefabrik 140 | 140 | dörtomuz, sandviç / düz (asma) | yeni Loftev (çelik panel grubu, kg, makine) | Batuhan Tınmaz 28.09.2026, kontrol Ubeydullah | 136 / 136 |
| E2 | Abdulselam 65, kubbeli | 64,89 | beşik + kubbe, trapez + OSB + nem bariyeri / ters | Portatifev | Ubeydullah 3.07.2026 | 137 / 130 |
| E3 | Abdulselam 65, kubbesiz | 63,76 | beşik, aynı / ters | Portatifev | Ubeydullah 3.07.2026 | 122 / 119 |
| E4 | Ahmet Sayım 92 | 92 | beşik, trapez / ters | yeni Loftev | Şafak Filiz 9.06.2026, kontrol Ubeydullah | 122 / 122 |
| E5 | Aykut Prefabrik 49 (Kübra Top) | 49 | beşik, sandviç / ters | Portatifev | Ubeydullah 19.07.2026 | 115 / 112 |

Bütün montaj paftalarını Ubeydullah çizmiş; kontrol Lokman. E1'in xlsx'inde hesap sütunu (G) var; şablonun kendi formülleri orada (aşağıda).

## Açık sorular ve kanıt (SERI_OZETI sırasıyla)

### 1. PK-01'in sıfırları

PK-01'de 0 olan kalemler: köşebent, baş makas Z'si, sandviç kapaması, alçıpan vidası, RYSB, çelik dübel, veranda Boardex, pencere vidası, pencere karkası.

**Kanıt:** Aynı şablonun (Portatifev) ve aynı hazırlayanın 2026 Temmuz listeleri (E2, E3, E5) bu kalemlerin hepsini dolduruyor:
- köşebent 7;
- Z 8 / 8 / 6;
- kapama 7 (E5 sandviç);
- alçıpan vidası 900 / 725;
- RYSB 500 / 400;
- dübel 20 / 21 / 22;
- Boardex 2;
- pencere vidası 180 / 120 / 150;
- karkas 3 + 2 / 5.

E5'te karkas satırı yok; pencereleri 120 genişlikte değil (aşağıda madde 12).

**Sonuç:** PK-01'deki sıfırlar doldurulmamış hücre; sürüm 7'nin doldurması doğru.

### 2. Loftev ↔ Portatifev farkları

| Kalem | 2025 Loftev (PK-03, PK-05) | PK-02, PK-06 (Loftev) | Portatifev (PK-01, PK-07, E2, E3, E5) | 2026 yeni Loftev (E1, E4) |
|---|---|---|---|---|
| Saçak / alın sacı boyu | 2800 | 2500 | 2500 | 2500 |
| 60'lık alt çerçeve | L 3750 | L 2500 | L 2500 | L 2500 |
| PVC iniş borusu | L 2000 | PK-06 L 2000 (PK-02 metal 3000) | E2, E3 L 2000; PK-01, E5 L 2500 (PK-07 metal 3000) | L 2000 |
| Şase pul | yok | yok | var (= çelik dübel) | yok (klipsli çelik dübel) |
| Baş makas Z'si | var | var | var (PK-01'deki 0 boş hücre) | E4 var; E1 yok (dörtomuz) |
| W otomat | 9 | 9 | 8 | 9 (E1: 25 A × 9 + 32 A × 1) |

**Sonuç:**
- 2800 ve 3750 yalnız 2025 Loftev listelerinde çıkıyor.
- İniş borusunda L 2000 çoğunlukta: 7 liste, L 2500 2 liste.
- Şase pul yalnız Portatifev şablonunda var.

### 3. Islak hacim

E1'in ayrı bir mutfağı var (13,4 m²); listede dört banyo Boardex. Hesap mutfağı ıslak saymıyor:
- **Kuru sayılınca** (H6 formülü): beyaz 36, banyo tavan Boardex 5. İkisi de tuttu.
- **Islak sayılsaydı:** beyaz 31, Boardex 10 olurdu.

Şablonun kendi hücresi de aynı: `98,16 × 1,05 ÷ 3` beyaz, `11,98 × 1,05 ÷ 2,88` banyo tavanı.
- E2, E3 ve E5'te mutfak salona açık; yeşil alçıpan yalnız banyo için 2 (tuttu).
- PK-03 (2025 Loftev) yeşil 6 ile mutfağı ıslak saymış görünüyor.
- Çamaşır odası için örnek yok.

### 4. Orta iniş

Paftadaki iniş daireleri (makas ve dere yerleşim planı):

| Proje | Saçak hatları | İniş | Dağılım |
|---|---|---|---|
| E5 | 2 × 7,6 m | 6 | 4 köşe + iki saçağın ortası |
| E4 | 2 × 12 m | 6 | 4 köşe + iki saçağın ortası |
| E1 | dörtomuz: 2 × 15 m, 2 × 11 m | 6 | 4 köşe + uzun iki saçağın ortası; 11 m'de yok |
| E2, E3 | 2 × ~9 m + veranda | 5 | 4 köşe + veranda iç köşesi |

- Önceki seri: PK-01 6, PK-03 6, PK-07 8 (4 + cumba 2 + orta 2: "açıklanamayan" 8 böylece açıklandı), PK-06 7.
- 2025 listeleri: PK-02, PK-05 ve PK-08'de 4.
- **"9 m'yi geçen saçağa 1" (J4) tutmuyor.** E5'te 7,6 m'de orta var, E1'de 11 m'de yok.
- **Aday:** ana çatının iki (uzun) saçağının ortasına birer iniş, yani 4 + 2 = 6; ek çatı parçası başına 2.

### 5. PK-06'da makas, tavan alçıpanı, pencere yok

Beş listenin hepsinde bu kalemler var. E5'te PVC doğrama "ALICIYA AİT" damgalı, adetsiz. PK-06'nın durumu yeni kanıtla çözülmüyor.

### 6. Fugalı cephede H latası 30

Beş projenin hiçbiri fugalı değil. Yeni kanıt yok.

### 7. W otomat

On liste: Portatifev şablonunda her zaman 8 (49, 60, 65, 70 m²), Loftev şablonunda her zaman 9 (58–140 m²). Sayı alana değil şablona bağlı. E1 (140 m²) 25 A × 9 + 32 A × 1.

### 8. PK-08 bayisi

Yeni kanıt yok; beş listenin hiçbiri bu bayiden değil.

### 9. Kubbeli cumba takımı

E2 ile E3 aynı ev; kubbeli ve kubbesiz hali aynı gün hazırlanmış. Fark, takımın kendisi:

| Kalem | Ölçü | E2 − E3 | PK-08 (2025) |
|---|---|---|---|
| Kubbe karkaslı özel pencere panosu 105/170 | 100 × 1250 × 2030 | +1 | var |
| Kubbe karkaslı özel pencere panosu 59/170 | 100 × 790 × 2030 | +2 | var |
| Kubbe özel pano | 100 × 2500 × 500 | +1 | 1 |
| Kubbe üstü H | 100 × 100 × 500 | +2 | 2 |
| Özel açılı köşe direği + kapaması | 100 × 100 × 2330 | +4 | 4 |
| Kubbe saçak sacı | 170 × 1500 | +3 | 5 |
| Kubbe makas (K-MK14…16) | 80 × 0,8 | +3 | yok |
| Kubbe OSB 11 mm | 1220 × 2440 | +1 | 1 |
| Kubbe üstü membran | paket | +1 | yok |
| Kubbe antrasit shingle | paket | +1 | 1 |
| PVC 105/170, 59/170 | | +1, +2 | var |
| 100'lük dolu pano 1250 / 625 | | −3 / +2 | |
| H (dübelli) | | −2 | |
| 100'lük alt çerçeve | | +1 | |

Ek farklar:
- dübel ve şase pul −1;
- betopan vidası +50, pencere vidası +60, 5,5 × 25 +50, mastik +5.

E2'nin iki salon penceresinin 120/180 olması tasarım seçimi; takıma ait değil. PK-08 ve Loftev taslağıyla aynı takım. E2'de buna ek olarak kubbe makası 3 ve membran 1 var; saçak sacı 3 (PK-08'de 5).

### 10. İE-13

Onay bekliyor.

## İncelemede çıkan yeni kanıt (kural adayı)

**11. Asma (düz) tavan H'ı.**
- E1 140, PVC omega kapak 20.
- PK-08'den çıkarılan formül (net tavan ÷ (1,255 × 0,625), yukarı) 139,7 → 140 verdi.
- Şablonun hücresi ise hat uzunluğu ÷ 1,185 (`160 ÷ 1,185`); not: "duvar omegalarına dik, 62,5 cm'de bir". Kapak: "duvar üstü omegalar hariç ÷ 3,65".

**12. Pencere sınıfı (sürüm 7.1 kuralı tuttu).**
- E5'te 100/100 ve 200/200 için üst / alt panel ve karkas yok. Yerine "100'lük karkaslı betopan kaplı pano (100×100)" × 5 ve "(200×200) 100 × 2475" × 1 var.
- 50/50 vasistas "vasistaslı pano (50/50)".
- 120 genişlikteki pencerelerde (E1–E4) her zaman üst panel + alt panel + özel pencere karkası.

**13. E1 şablon formülleri (G sütunu).**

| Kalem | Formül | Durum |
|---|---|---|
| Saçak omegası | saçak ÷ 2,5 | |
| Saçak sacı | 50,4 ÷ 2,3 | 23 yazılmış |
| 100'lük alt çerçeve | 48 ÷ 3,75 | |
| 60'lık alt çerçeve | 43,63 ÷ 2,5 | 19 |
| Aşık | hat ÷ 4,1 + 5 | |
| Veranda Boardex | alan × 1,08 ÷ 2,88 | O14 doğrulandı |
| Mahya | Σ ÷ 2,6 | O10 doğrulandı |
| Uç kapaması | çevre ÷ 2,6 | O11'de ÷ 2,5 |
| İzolasyon bandı | mahya adedi × 2,8 ÷ 10 | |
| Çatı izolasyonu | alan ÷ 9,6 | |
| Dere kelepçesi | çevre ÷ 3,8 × 8 | |
| RYSB | m² × 7,5 | O16 doğrulandı |
| 5,5 × 60 | m² × 2,5 | O16 doğrulandı |
| Kesme taşı | m² × 0,02 | O16 doğrulandı |
| Trapez uç | m² ÷ 15 | |
| Dayson | m² × 0,06 | Portatifev'de 0,03 |
| Mastik (antrasit) | pencere sayısı | |
| Boya | dış ve iç m² × 0,02, tavan ve astar m² × 0,01 | |
| Çelik dübel | dübelli H toplamı | O16 doğrulandı |
| NYM 3 × 2,5 | 10,85 × W otomat + (priz + çift priz × 2 + uydu) × 2 | E4'te tutmuyor |

**14. Yeni Loftev şablonu (E1, E4).**
- Çelik panel grubu: makas ve çatı panelleri 80 × 45 × 10 × 0,8, kg, "Alpha Mini 0.8" makinesi.
- Satır numarası var.
- "Çatı grubu fiyatlandırma" ve "boya grubu fiyatlandırma" satırları var.

**15. Tavan alçıpanı (H6).**
- E1 36 / 5 ve E5 15 / 2 tuttu.
- E2 ve E3'te beyaz 18 (formül 19; holün 2,23 m²'si sayılmamış gibi).

## Lokman'ın cevapları (13.10 14:35–14:42, soru kartları)

Kayıt `deneme/2026-10-13_kor_test_seri/KARAR_NOTU.md`; üreteç sürüm 7.2 (R1–R6).
1. Standart pakette köşebent, Z, dübel, RYSB ve vidalar her zaman var. Dörtomuz çatıda baş makas Z'si olmaz; E1'de baş makas satırlarının hiçbiri yok. Pencere karkası projeye bağlı.
2. Saçak ve alın sacı 2500 ya da 2800: sac durumuna göre, en güncel liste esas. **Alt çerçeve her zaman L 3750**, 60'lık da. İniş borusu L 2000; bina yüksekliği 2500.
3. Islak hacim yalnız banyo ve WC.
4. İniş: 4 köşe + iki saçak ortası; ek çatı parçası +2.
5. Makas listeden düşemez; PK-06'da mühendis atlamış. Pencere ve tavan alçıpanı müşteri tercihi olabilir; alçıpan %95 standart.
6. H latası = dış 100'lük duvar H'ları + 3 yedek.
7. W otomat Portatifev 8, Loftev 9.
8. PK-08 eski şablon, eksik doldurulmuş.
9. Kubbe takımı = Abdulselam takımı.
10. İE-13'ten önce test setinde kör test.
11. Tek şablon Portatifev.
