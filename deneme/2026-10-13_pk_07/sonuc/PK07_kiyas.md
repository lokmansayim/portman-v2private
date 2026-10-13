# PK-07 · Diamond 70,65 m² (Aziz Bey, Manisa) · kendi listemiz ↔ gerçek yükleme listesi (kör test adım 4, pafta kipi)

- **Sıra kanıtı:** kendi listemiz `f3bb50f` (13 Ekim 2026 13:02:48 +03) → Mac'te mühür denetimi 13:02:52 (`985c3a20…6086` aynı) → açılış 13:03:02.
- **Gerçek liste:** `gercek/DIAMOND_70M2_YUKLEME_LISTESI.pdf`, 3 sayfa; şablon **PORTATİFEV YÜKLEME LİSTESİ**, hazırlayan Ubeydullah Özer, 4.08.2026.
  Okunmuş hali `gercek/PK07_gercek.json` (134 satır).
  - Bu seride ilk tam Portatifev listesi; şablonun sahibinin kendi listesi.
  - PVC doğrama satırlarının yanında "ALICIYA AİT" damgası var.
- **Bizim liste:** `PK07_liste.json` / `.xlsx` (üretici sürüm 6.1, pafta kipi; varsayılan Portatifev).

## Özet

| Sonuç (gerçek listenin 134 satırı, tek tek sayıldı) | Satır | Not |
|---|---|---|
| Varsayılan adetle aynı | 41 | panoların 11'i, kiriş E, kolon A, H standart 14, 3'lü H standart 4, baş makas omegası 7 ve betopanı 7, cumba sandviçi 3 × 2400, çatı izolasyonu 8, kapılar (çelik SOL; Amerikan 3 SOL + 2 SAĞ), acil müdahale kapağı, şase pul 27, 5,5 × 110 vida 500, uçlar 5 + 5, inox 8, elektrikte 13 |
| Toplam aynı, ayrım farklı | 16 | 10 pano satırı (dış "FUGALI" ve iç ayrı satır; boy boy toplamlar tutuyor), köşe 5 + özel D 1, saçak sacı 9 + özel büküm 2 = 11, alın sacı 9 + 2 = 11, makas 10 (7 + 3), boya |
| Aday ya da pafta sütunu tuttu | 11 | dış H 11 / 12 ve 3'lü 1 / 3 (dört satır), pencere karkası C 4 (pafta), sandviç kapaması 10, veranda Boardex 2, iniş 8, çelik dübel 27, betopan vidası 500, köpük 2 |
| Farklı: bizim kural hatamız | 13 | aşağıda (1–12) |
| Farklı: karar | 1 | iniş borusu metal L 3000 (özellik tablosunda iniş satırı yok) |
| Alıcıya ait, bilgi için yazılmış | 3 | PVC doğrama 120 × 120 × 4, 100 × 120, 60 × 40 (biz "pencere grubu 0") |
| Dere / iniş adedine bağlı | 4 | açık / kapalı dirsek, iniş kelepçesi, dere kelepçesi (kural doğru, girdi adedi farklı) |
| Farklı: elle ya da göz | 14 | aşık 39 (biz 42, pafta 37), saçak omegası 9 (10), çektirme U'su 5 (2), mahya bandı 3, tavan alçıpanı 20 / 3 (21 / 2), betopan H'ı 7, RYSB 550, NYM 120, anahtar 6 + çift 1 (biz 7 + 0), zil 1, mastik 50, dayson 3 |
| Bizde yok | 31 | özel büküm saçak ve alın 2 + 2, veranda paneli 1, damlalık 4, dış cephe lataları 5 satır, çatı müdahale kapağı, 5,5 × 25 ve 5,5 × 60 vida, kesme taşı, çırpı ipi, buat kasa 31, W otomat 8, sıhhi tesisat 11 satır, boya 4 satır |

**Doğru toplamla 68 / 134 satır** (aynı + ayrım + aday).

- **Panolar:** dış ve iç toplanınca **boy boy hepsi tuttu**; 100/120 pencereli çelik duvar 1470 de tuttu. Tek fark, fugalı dış cephede dış panoların ayrı satır yazılması.
- **H planı altı satırda birebir.** Kulaklı = "makasa denk gelen dış ek" kuralı, PK-06'dan sonra bu sefer kör tuttu.
- **Kapılar yedinci kez tuttu.**
- **Baş makas omegası 7 ve betopanı 7 tuttu.** Omega `kalkan_duvar_cm` ile tuttu (ön kalkanın altında yalnız 393,5'lik duvar var).

## Bizim hatalarımız (sürüm 7'de düzelecek)

1. **Fugalı dış cephe:** açıklamada "dış cephe fugalı düz betopan" varsa dış panolar "(FUGALI)" ayrı satır.
   - Pencere üst ve alt, kapı panosu, vasistas ve çelik duvar da fugalı.
   - Ayrı betopan levhası yok: bizim "dış cephe betopan 27" ilk tahminimiz yanlıştı.
   - Fugalı cephede latalar var:
     - H latası 30;
     - köşe latası 150 ve 130, her dış köşeye bir (5 + 5);
     - pencere latası: pencere çevreleri + kapı (2 boy + en) = 30,5 m → 10 × 2800 + 1 × 2500.
2. **Özel köşe direği D** (L'nin iç köşesi) ayrı satır; iç duvarların L köşesi 10'luk köşe direğine girer (5 + 1).
3. **Köşebent 7.** Portatifev şablon notu "tek kat 7"; PK-06 de 7. PK-01'de 0'dı.
4. **Kolon boyu paftadan:** B 2098 (verandada kirişin altında).
5. **İç duvar 100 ise duvar üstleri 100'lük duvar omegasına:** iç duvarlar 23,2 m ÷ 2,5 → 10 ✓.
   - Ters tavan omegası yalnız oda hatları. Hat sayısı ⌊derinlik ÷ 0,6⌋ + 1 (her gözde iki duvar yüzünde de hat; paftada 112,8 m, bizim yeni hesap 112,1 m).
   - Sonra ÷ 3,65 + 5 → 36 ✓ (biz 38).
6. **Baş makas Z'si** ana çatının alın kenarları × ⌈eğik ÷ 2,8⌉ = 8 (cumba hariç). PK-06 Loftev'de de ana çatı 8. PK-01'de 0'dı.
7. **Alt çerçeve:** iç duvar 100 ise tek satır, (dış çevre 33,7 + iç duvar 23,2) ÷ 3,75 → 16 ✓ (biz 9 + 10).
8. **Sandviç panel yüz başına yukarı:** 8,4 ÷ 1 → 9 + 9 = 18 ✓ (biz toplam 17).
   - PK-01'de 22 ve PK-06'da 30 da yüz başına tutuyor; PK-02 (Loftev) toplamla 17.
9. **Mahya toplam ÷ 2,6:** (8,4 + 1,5) → 4 ✓. PK-06'da da 6 tutuyor (biz parça parça 5).
10. **Veranda saçağı (makassız, sandviç kanopi) dere almaz;** onun yerine damlalık var.
    - Dere 19,5 ÷ 3,8 → 6 ✓ (biz 7).
    - Dere kapağı 4 + 2 = 6 ✓ (biz 8).
11. **Alçıpan vidası** (tavan levhası × 40, 250'nin katı) duvar alçıpanı olmasa da var: 23 × 40 = 920 → 1000 ✓.
12. **Pencere alıcıya ait olsa da pencere vidası (× 20 = 120 ✓) ve 120/120 karkasları (C × 4) bizde.**
    - Montaj bizde. PK-01 dersi 1 ve 9 burada tutmadı.

## Sürüm 7'ye geçenler (kalibrasyon, kör değil; üreteç başlığında O1–O19)

- **PK-07 sürüm 7 ile:** fugalı pano satırları ve latalar, özel köşe D, köşebent 7, kolon B 2098, 60'lık omega 36, 100'lük omega 10,
  saçak / alın 9 + özel 2, Z 8, alt çerçeve 16, sandviç 18, mahya 4, kapama 10, dere 6, kapak 6, kelepçe 48, Boardex 2, alçıpan vidası 1000,
  RYSB 550, pencere vidası 120, karkas C 4, çelik dübel 27, 5,5 × 60 200, kesme taşı 2, çırpı ipi 1, çatı müdahale kapağı 1,
  tesisat takımı (7 satır), boya 5 satır, dayson 3, köpük 2 tutuyor.
- **Hâlâ tutmayanlar:**
  - aşık 38 (39);
  - saçak omegası 10 (9);
  - çektirme U'su 2 (5);
  - iniş 7 (8) ve borusu (metal 3000);
  - H latası 27 (30);
  - buat 30 (31; paftada zil yok);
  - W otomat, damlalık, 5,5 × 25 vida.
- **Kör okumada bir hata:** dış kapının veranda yanındaki anahtar iki tırnaklı (çift). Kıyastan sonra büyütülüp `pafta_katmani.json`'da düzeltildi (6 + 1).
- **Geri test (sürüm 6.1 → 7), öteki projeler:**
  - PK-01'in boş bıraktığı kalemlerde artık PK-07'ye uyuyoruz: köşebent, Z, kapama, Boardex, vidalar, dübel, karkas. PK-01'le farkı bilerek büyüttük (soru 1).
  - Loftev listelerinde (PK-02, -03, -05, -06) tesisat takımı ve köpük 2 tuttu.
  - Sandviç yüz başına PK-02'de 18 oldu (Loftev 17, aday sütununda).
  - Aşık sırası en yakın tamsayıya yuvarlanınca PK-06 ve PK-07 paftasıyla aynı. PK-01'de 38 → 32 (gerçek 36, elle), PK-05'te 27 → 25 (gerçek 30).

## PK-01 ↔ PK-07 (iki Portatifev listesi çelişiyor)

PK-01 (Huma 60) şu kalemlerde 0 ya da boş: köşebent, baş makas Z'si, sandviç kapaması, alçıpan vidası, RYSB, çelik dübel, veranda Boardex,
pencere vidası, pencere karkası. PK-07 bunların hepsini dolduruyor.

PK-07 şablonun sahibinin (Ubeydullah) Ağustos 2026 listesi; şablon notu da "köşebent tek kat 7" diyor. PK-01'deki sıfırlar "doldurulmamış"
gibi duruyor. Sürüm 7'de varsayılan PK-07'ye geçiyor, PK-01 notta kalıyor (soru).

## Kural adayları (tek örnek; varsayılan değil ya da ilk tahmin)

- **Buat kasa** = bütün elektrik noktaları (anahtar 7 + priz 14 + uydu + zil + duy 5 + glop 3) = 31 ✓.
- **5,5 × 60 vida** m² × 2,5 → 100'e yukarı = 200 ✓ (kural kitabındaki Excel motoru formülü).
- **Kesme taşı** m² × 0,02 → 2 ✓ (PK-06 2 ✓). **Çırpı ipi 1. Çatı müdahale kapağı 1.**
- **RYSB** m² × 7,5 → 50'ye yukarı = 550 ✓ (Loftev 250'nin katı).
- **Sıhhi tesisat takımı:** 6 / 15 / 12 / 6 / 15 / 6 / 3, PK-03, -05 ve -07'de birebir aynı; PK-06'da üç ıslak noktayla büyük.
  Vitrifiye 4 takım (duş teknesi, klozet, lavabo, batarya) yalnız burada.
- **Boya (Portatifev):** dış 2 + iç 2 kova (m² × 2 ÷ 100), kenar boyası 10 kg 1, tavan boyası 1, astar 1. Dayson m² × 0,03 yukarı (PK-06 3 ✓; PK-01 aşağı 1).
- **Aşık satırı yuvarlama:** (eğik − 0,2) ÷ 0,6 yukarı değil en yakın.
  - PK-07: 7,08 → 8 sıra (paftada 8); PK-06: 6,998 → 8 (paftada 8).
  - Bizim yukarı yuvarlama PK-07'de 9 dedi.

## Açıklanamayanlar

- Saçak omegası 9: saçak hatları 23,4 m (kanopi dahil) ÷ 2,5 = 10; kanopi hariç 8.
- Çektirme U'su 100 için 5.
- İniş 8: 4 köşe + cumba 2 + ? (9 m'yi geçen sol saçak 9,6).
- Aşık 39: pafta 146,7 m; × 1,05 ÷ 4,2 = 37.
- Tavan alçıpanı 20 / 3 (bizim formül 21 / 2).

## Sorular (Lokman)

1. PK-01 (Huma) listesi mi güncel, PK-07 (Diamond, Ubeydullah) mi? Sürüm 7 PK-07'yi esas alıyor.
2. Fugalı cephede H latası 30: dış ek 27, + 3 neye göre?
3. W otomat Portatifev'de 8, Loftev'de hep 9; kuralı nedir?
