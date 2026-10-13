# PK-08 · Eren Bey 60 m² (Muhammed Uysal bayisi) · kendi listemiz ↔ gerçek yükleme listeleri (kör test adım 4, pafta kipi)

- **Sıra kanıtı:** kendi listemiz `c997d0a` (13 Ekim 2026 13:21:46 +03) → Mac'te mühür denetimi 13:21:49 (iki dosya da aynı) → açılış 13:22:02.
- **Gerçek listeler:**
  - `gercek/MUYSAL_EREN_BEY_60M2_YUKLEME_LISTESI.xlsx` ("PORTATİF YÜKLEME LİSTESİ"; hazırlayan Lokman Sayım, 21 Ağustos 2025).
    142 satırın 70'inde adet var; vida, elektrik ve sıhhi tesisat grupları ile makas satırları boş. Okunmuş hali `…_LISTESI.json`.
  - `gercek/LOFTEV_PREFABRIK_YUKLEME_LISTESI.xlsx` (20 Ağustos 2025): yalnız cumbanın ("kubbe") ek kalemleriyle boya dolu, taslak.
- **Bizim liste:** `PK08_liste.json` / `.xlsx` (üretici sürüm 7.1, pafta kipi).
- **Okumada iki varsayım vardı:** tavan tipi ve çatı eğimi. Montaj paftası DWG olduğu için bu iki bilgi paftadan okunamadı.

## Özet (dolu 70 satır; yaklaşık sınıflama)

| Sonuç | Satır | Not |
|---|---|---|
| Varsayılan adetle aynı | 15 | pencere üst panel 2, kasalı pano 3, çelik kapı panosu, köşe 100 × 6, saçak omegası 8, baş makas betopanı 6, trapez mahyası 11, şilte 7, iniş 4, dere kapağı 4, iniş borusu L 500 × 4, kapalı dirsek 4, çelik kapı SAĞ, Amerikan kapı 3, köpük 2 |
| Toplam aynı, ayrım farklı | 5 | dış H 18: bizim 16 + 3'lü 2 tutuyor; cumbanın 4 açılı ekini biz H saydık, listede "özel açılı köşe direği + kapaması" 4. Kubbe pencere panoları 2 + 2. 60'lık alt çerçeve 5 (L 3750) |
| Aday tuttu | 3 | köşebent 5 (Loftev), pencere U'su H geçen 4, iniş borusu L 2000 × 4 |
| Girdi / okuma farkı | 13 | aşağıda |
| Kural ya da karar | 20 | kesik panolar tam boy, köşe 60 × 2, çektirme U'ları 8 / 5, baş makas omegası 9, Z 10, alın 10, saçak sacı 250 × 2800 × 5, alt çerçeve 6, kiriş 4400 × 2, dirsek ve kelepçe iniş × 1, dere kelepçesi 50, betopan H'ı 4, dübel 20, mastik 30 … |
| Bizde yok | 13 | kubbe özel pano 2500 × 500, kubbe üstü H 2, kubbe saçak sacı 5, kubbe OSB 1, shingle 1, ters mahya 2, özel mahya (geniş) 2, baş makas menfezi 4, iç kapı kilidi 3 ve menteşe 6, dış kapı kolu, tiner 3, poliüretan mastik 2 |

**Tutan geometri:**
- Kapı adedi ve dış kapı yönü tuttu: SAĞ, mimari plandaki yaydan.
- Köşe direği 6 tuttu.
- Saçak omegası, baş makas betopanı ve trapez mahyası tuttu.
- Dış H toplamı, açılı ekler ayrılınca tuttu.

## Girdi / okuma farkları

1. **Pencereler mimari plana göre:** listede 120/120 × 2 (mimari planda 120/100), 180/180 × 2 (salon ve cumba önü), 50/180 × 2 (pano 53/180).
   - Duvar yerleşim PDF'indeki 105/170 ve 59/170 eski bir sürüm (Loftev taslağında cumba önü 105/180).
   - WC'nin 60/40 vasistası okunmadı (mimari planda etiketsiz).
2. **Tavan asma (dizme):** listede tavan H'ı 65 ve omega kapak 13 var.
   - Omega planındaki 60 cm'lik 13 hattı ters tavan sandık; yanlıştı.
   - 13 kapak = 13 hat. Tavan H'ı = net tavan ÷ (1,255 × 0,625) = 64,5 → 65 ("+5"siz).
   - 60'lık duvar omegası 20.
3. **Trapez sac 100 cm kapatıyor**, L 4500, 17 adet (iki yüz toplamı ÷ 1,0). PK-03'teki trapez 80 cm kapatıyordu, bu başka ürün.
   L 4500 eğimin bizim varsayımımızdan (%33) yüksek olduğunu gösteriyor.
4. **Aşık 50** (biz 33). Eğim ve aşık aralığı bilinmeden açıklanamıyor.
5. **Yeşil alçıpan 5** (biz 2): ıslak hacim WC'den büyük.

## Kural ya da karar (bayi listesi, 2025)

- **Kesik panolar tam 1250 olarak yazılmış:** dış dolu 18, iç dolu 7. Biz 21 / 8 pano, kesikler kendi boyunda.
  PK-02 (Loftev, Kasım 2025) kesikleri boyunda yazmıştı; bu bayinin uygulaması olabilir. Soru.
- **Dere takımında** açık dirsek ve iniş kelepçesi iniş × 1 (PK-07 Portatifev'de × 2). Dere kelepçesi 50.
- **Kubbeli cumba kalemleri** (Loftev taslağıyla aynı): kubbe özel pano 2500 × 500, kubbe üstü H × 2, özel açılı köşe direği + kapaması × 4,
  kubbe saçak sacı 170 × 1500, kubbe OSB 1, shingle 1, pencere panoları 2030 boyunda. Kural adayı: açılı cumba varsa bu takım.

## Sorular (Lokman)

1. Muhammed Uysal'ın listelerinde kesik panolar tam boy mu yazılıyor (sahada kesim)?
2. Bu bayinin listesinde vida, elektrik ve tesisat neden boş? Bayi kendisi mi alıyor?
3. Kubbeli cumba takımı (yukarıdaki 8 kalem) her açılı cumbada aynı mı?

## Lokman'ın cevabı ve model alanı (13.10 14:42, kıyastan sonra)

- **"Eski şablon, eksik doldurulmuş":** kesik panoların tam boy yazılması ve boş vida, elektrik ve tesisat grupları bayinin kuralı değil. Bizim kesikleri kendi boyunda yazmamız doğru.
- **Kubbe takımı = Abdulselam takımı** (AIPrefabrik E2 − E3).
  - `yapi_pafta.json`'daki "cumba kubbesi" parçasına `kubbe: true` eklendi. Kıyastan sonra eklenen bir model alanıdır.
  - Kör liste (`PK08_liste.json`, sürüm 7.1) değişmedi.
  - Sürüm 7.2'de kubbe genel çatı satırlarına girmiyor ve takım ayrıca ekleniyor. Takım: kubbe özel pano 1, kubbe üstü H 2, açılı köşe direği 4, kubbe saçak sacı 3, kubbe makası 3, OSB 1, membran 1, shingle 1.
