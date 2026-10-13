# PK-06 · Sevim Güler 82 + 10 m² (Çorlu) · kendi listemiz ↔ gerçek yükleme listesi (kör test adım 4, pafta kipi)

- **Sıra kanıtı:** kendi listemiz `90869d0` (13 Ekim 2026 12:41:20 +03) → Mac'te mühür denetimi 12:41:30 (`3cf21751…e2fe` xlsx ve
  `5874e5e7…3555` pdf aynı) → açılış 12:41:40.
- **Gerçek liste:** `gercek/SEVIM_GULER_82+10M2_YUKLEME_LISTESI.xlsx`, sayfa "PREFABRİK"; şablon **LOFTEV YÜKLEME LİSTESİ**, 92 m² tek kat,
  hazırlayan Şafak Filiz, 22.01.2026. Okunmuş hali `gercek/PK06_gercek.json` (100 satır). "ÇELİK" ve "BATUHAN TINMAZ" sayfaları boş şablon;
  "VİDA BİLGİ" sayfasında vida kuralları var (aşağıda).
- **Bizim liste:** `PK06_liste.json` / `.xlsx` (üretici sürüm 5.1, pafta kipi; varsayılan Portatifev).

## Özet

| Sonuç (gerçek listenin 100 satırı, tek tek sayıldı) | Satır | Not |
|---|---|---|
| Varsayılan adetle aynı | 45 | panoların 15'i (16 satır), köşe 6 + 2, kolon 2, çektirme U'su 60, 100'lük duvar omegası 3, alt çerçeve 11 + 12, aşık 52, mahya 6, dere 8, kelepçe 64, dere kapağı 6, kapılar (çelik SOL; Amerikan 3 SOL + 3 SAĞ), betopan H'ı 5, acil müdahale kapağı, elektrikte 13 |
| Toplam aynı, ayrım farklı | 4 | dış H 19 (kulaklı 13 / dübelli 6; aday 12 / 7), iç H 17 (H 4 / 3'lü 13; biz 13 / 4, yer değişmiş gibi) |
| Aday ya da pafta sütunu tuttu | 9 | 3'lü H 3 / 2 (iki satır), çelik dübel 24, RYSB 750, betopan vidası 500, tek kat panel vidası 750, köpük 2, tek kat panel 30 (pafta), baş makas Z'si 8 (aday 10'un ana çatı payı) |
| Farklı: bizim kural hatamız | 9 | baş makas omegası ve betopanı, şilte, pencere U'ları 2, inox ve uçlar 3, iki modüllük pano boyu (aşağıda) |
| Farklı: karar (Loftev ↔ Portatifev) | 4 | köşebent 7, profil vidalama 6, iniş borusu L 2000, dayson 3 |
| Farklı: elle ya da açıklanamadı | 15 | kiriş boyları 3, 60'lık omega 50 (biz 47 + 5), saçak omegası 14 (11), saçak sacı 16 (12), alın 9 (10), iniş 7 (8) ve ona bağlı 4 satır, NYM 140 / 120, izole bant 3 |
| Bizde yok | 14 | damlalık 1, tek kat panel kapaması 16, 5,5 × 25 vida 1400, 5,5 × 60 vida 100, kesme taşı 2, çırpı ipi 1, W otomat 9, sıhhi tesisat 7 satır |

**Pafta kipi üçüncü kez çalıştı:** 16 pano satırının 15'i birebir; tek fark iki modüllük pencere panosunun sipariş boyu (2510 ↔ 2500).
**Menteşeler kanat dörtgenlerinden okununca beşinci kez tuttu** (3 SOL + 3 SAĞ, dış kapı SOL). **J2 (100'lük duvar omegası) ve J3 (dere ÷ 3,8)
ikinci / üçüncü kez tuttu.** Elektrik göz sayımının 9 kalemi de birebir.

**Gerçek listede olmayanlar** (bu listede hiç satır yok; PK-03 ve PK-05'te vardı): **makas** (makas grubunda yalnız aşık), **tavan alçıpanı**
(ters tavan; PK-03'te 20 + 6), **PVC pencereler ve pencere vidası**, boya grubu ve mastik. Liste 22.01.2026 tarihli, başka hazırlayan; bunların
ayrı bir listeye mi gittiği, alıcıya mı ait olduğu bilinmiyor → soru.

## Bizim hatalarımız (sürüm 6'da düzelecek)

1. **Kulaklı H, makasın denk geldiği her dış ekte:** salon–veranda duvarındaki ek (x 130,4) MK09'un tam altında; listede kulaklı 13 / dübelli 6.
   Okuyucu bu duvarı "saçak değil" diye dışarıda bırakmıştı (12 / 7). Kural: makas konumuna denk gelen dış duvar eki kulaklı.
2. **Açık çatı parçası (veranda çatısı) kalkan kalemi ve şilte almaz:** sol kalkanın altında duvar yok (kiriş). Listede baş makas omegası 7
   (ana çatı 2 × 7,73 ÷ 2,5), Z'si 8 (ana çatı), betopanı 6 (ana çatı); biz verandayı da sayıp 8 / 10 / 7 dedik. Şilte 11 = ana çatının saçaklı
   tabanı ÷ 9,6 (veranda parçası hariç; Loftev adayı verandayla 12 dedi).
3. **Kiriş boyları** 1110 / 2990 / 3140 (biz 1102,5 / 2985 / 3137,5): 10 mm'ye yukarı yuvarlanmış gibi, ama PK-03'te 1155 yuvarlanmamıştı → kural değil, elle.
4. **Tek kat panel yüz başına yukarı ve paftadaki boy:** arka yüz 11,995 ÷ 0,87 → 14, ön yüz (verandaya uzayan düzlem dahil) 13,2 ÷ 0,87 → 16 = 30;
   boy L 4450 (paftada şerit 444,9; eğik + ≈ 5 cm). Veranda arka yüzü artan parçalardan; ayrı veranda satırı yok. Biz 28 × 4400 + 4 × 2100.
5. **Veranda tavan omegası ayrı satır değil** (PK-03 dersi 10 ikinci kez): listede tek satır 50.
6. **Pencere U'ları:** çektirme U'su 100 4, pencere U'su H geçen 5; Portatifev (2 / 1) da Loftev adayı (6 / 8) da tutmadı.
7. **İnox taşı m² ÷ 10 aşağı, uçlar inox ÷ 2** ("VİDA BİLGİ" sayfası): 92 → 9, 8'lik uç ve PH2 4 (biz 10 / 7 / 7). PK-01'de de tutuyor;
   PK-02, -03, -05'te listeler farklı (elle).
8. **İki modüllük pencere panosunun sipariş boyu 2510** (PK-03'te 2500): kesintisiz modül boyu; karar.

## Sürüm 6'ya geçenler (kalibrasyon, kör değil)

- **N1** açık çatı parçası (`acik: true`): baş makas omegası 7, betopan 6, Z adayı 8, şilte adayı 11 — dördü de tuttu.
- **N2** veranda tavan omegası ayrı satır değil (PK-01, -03, -06).
- **N3** aday sütunu: W otomat 9, PVC iniş L 2000, profil vidalama kolon × 3 (PK-03, -06 ✓), inox m² ÷ 10 aşağı (PK-01, -05, -06 ✓; PK-02, -03 ✗),
  uçlar inox ÷ 2 (yalnız PK-06 ✓).
- **Kulaklı H** okuyucuda: makasın denk geldiği dış ek → 13 / 6 ve 3 / 2 tuttu.
- Geri test (sürüm 5 → 6): PK-01 ve PK-03'te fazla veranda omega satırı düştü, öteki varsayılan adetler aynı; PK-02, -05 yalnız aday sütunu.
- Geçmeyenler: kiriş yuvarlaması, tek kat panel yüz başına (PK-02 sandviçte toplam yukarı 17 tutuyordu), pencere U'ları, saçak sacı / omegası,
  iniş 7, iki modüllük pano 2510 (PK-03 2500).

## VİDA BİLGİ sayfası (veri; kural adayı)

- Aşık (420) 10, omega 375 → 10, omega 240 → 6, çelik panel 10, köşebent 240 → 6 adet 5,5 × 25 vida.
  Bu listeyle hesap: aşık 520 + 60'lık omega 500 + 2500'lük omegalar (3 + 14 + 7) × 6 = 144 + köşebent 42 = 1206;
  alt çerçeveler eklenirse 1388 → listede 1400.
- RYSB: 70 m² 500, 100 m² 750. Alçıpan vidası levha başına 40. Betopan / OSB levha başına 40. Pencere başına 20.
- Çelik dübel: orta boy duvar panosu başına 3. Şase pul = dübel. İnox = m² ÷ 10. Uç ve kesme taşı = inox ÷ 2.

## Karar (Loftev ↔ Portatifev), elle ve açık sorular

**Karar:**
- pencere karkası satırı yok (Loftev: U'lar yerinde);
- köşebent 7 (Portatifev şablon notu "tek kat 7" ile aynı; Loftev PK-02 3, PK-03 / -05 5);
- profil vidalama aparatı 6 (kolon × 3; PK-03'te de 6);
- iniş borusu PVC L 2000 + L 500 (özellik boş; PK-03 ve -05 de 2000);
- şase pul yok, çelik dübel 24 (aday ✓);
- boya grubu ve mastik yok;
- dayson 3 (biz 2).

**Elle ya da açıklanamadı:**
- 60'lık omega 50: oda hatları + veranda + duvar üstleri ÷ 3,65 + 3 = 49,9 → 50 tutuyor, ama PK-03'te aynı formül 43 verir (gerçek 39).
- Saçak omegası 14 / saçak sacı 16 + özel büküm damlalık 1: saçak hatları 26,7 m (biz 11 / 12). Veranda kirişleri (7,2 m) eklenince omega 13,6 → 14.
- Alın sacı 9 (biz 10; ÷ 2,5 ile 9).
- İniş 7: 4 köşe + veranda 2 + 1 orta? Biz 8 (aday 6). Dirsek ve kelepçe iniş adedine bağlı kural tuttu (14 / 7 / 14).
- NYM 140 / 120, izole bant 3.
- İç H ile iç 3'lü H yer değiştirmiş gibi.

**Bizde kural yok:**
- tek kat panel kapaması 16 × L 2500 (PK-05'te 6 = alın kenarları ÷ 2,5; burada değil);
- W otomat **9** (PK-02, -03, -05, -06: dördünde de 9 → sabit aday);
- sıhhi tesisat 7 satır: PK-03 / -05 setiyle aynı kalemler, boru 10 (6) ve normal dirsek 20 (15) fazla; üç ıslak nokta (banyo, mutfak, çamaşır);
  sabit takım değil, ölçekli.

**Sorular (Lokman):**
1. Bu listede makas, tavan alçıpanı ve pencereler neden yok (ayrı liste mi, alıcıya mı ait)?
2. Çamaşır odası ıslak hacim mi (tesisat ve yeşil alçıpan)?
3. 9 m'yi geçen saçağa orta iniş: PK-01 var, PK-03 yok, PK-06'da 1?

## Motor için (İE-13)

L plan ve öne taşan veranda (madde 5), 160/180 iki modüllük pano (4), ana çatıya paralel ve ön yüzü aynı düzlemde devam eden veranda beşiği (6).
