# PK-01 · Huma 60 m² · kendi listemiz ↔ gerçek yükleme listesi (kör test adım 4)

- **Sıra kanıtı:** kendi listemiz `aebcfca` (13 Ekim 2026 10:48:50 +03) → gerçek liste mühürle karşılaştırıldı (SHA `17e43b88…d106` aynı) ve 10:49:17'de açıldı.
- **Gerçek liste:** `gercek/HUMA_60M2_YUKLEME_LISTESI.xlsx` (tek sayfa "1 KATLI"; hazırlayan Ubeydullah Özer, 1 Ekim 2026; iletişim alanı boş). Okunmuş hali `gercek/PK01_gercek.json`.
  Listede her kalemin yanında **fabrikanın kendi formülü ve açıklaması** var ("KABA HESAP", "KESİN HESAP", "AÇIKLAMA" sütunları). Kural adaylarının çoğu oradan.
- **Bizim liste:** `PK01_liste.json` / `.xlsx` (75 satır; 64 adetli, 11 "kural yok").

Sınıflar (KT raporlarındaki gibi): **girdi** (bizim okuma ya da İş Emri hatamız) · **kural** (bizim kuralımız yanlış ya da eksik) · **karar** (fabrika başka türlü yapıyor; hangisi kural, Lokman karar verir) · **elle** (fabrika kendi formülünün verdiğinden farklı adet yazmış) · **eksik** (gerçek listede var, bizde kuralı yok).

## Özet

Gerçek listede adedi dolu (alıcıya ait olmayan) **97 satır** var.

| Sonuç | Satır | Not |
|---|---|---|
| Adet ve kalem aynı | 41 | panoların 23'ü, köşe 60, kirişler, kolon, H 60, üçlü H 60, saçak ve alın sacı, 100'lük alt çerçeve, makas, sandviç panel, mahya, dere takımının 6'sı |
| Toplam aynı, ayrım ya da ölçü farklı | 12 | köşe direği (3 standart + 3 özel), dış H ve dış üçlü H (kulaklı / dübelli), iç kapı (sağ / sol), iniş borusu (2500 + 500) |
| Adet farklı | 13 | aşağıda |
| Bizde kuralı yok (eksik) | 31 | elektrik grubu 16, asma tavan malzemeleri, vida, çektirme ve pencere U'su, pencere karkası, baş makas omegası, betopan, mahya bandı, dayson |

Bizim fazlamız (gerçek listede 0 ya da yok): pencereler (gerçekte **alıcıya ait**), köşebent 61, baş makas Z'si 8, tavan omegası 25, yeşil alçıpan 3, alçıpan ve pencere vidası.

**Panolar:** 50 panonun **50'si** tür ve boyca tutuyor. Ama yalnız bu sipariş boyu kuralıyla: **net boydan 2,5 mm düşülür, 5 mm'ye aşağı yuvarlanır** (1115 → 1110, 627,5 → 625, 602,5 → 600, T'de kısalan 122,5 → 1220, 120,5 → 1200).
Commit'lenen listemiz Motor'un net boyunu yazmıştı. Ayrıca P6001'den gelen "T panosu listede 1250" kuralı **yanlıştı**: gerçekte 1220 ve 1200.

## Grup grup

### 1001 Panel (25 satır)

| Gerçek | Adet | Bizim (commit'lenen) | Sonuç | Sınıf |
|---|---|---|---|---|
| 100'lük yapıştırma dolu 1250 | 12 | 12 | ✓ | |
| 100'lük dolu 1110 / 830 / 775 / 625 / 600 / 400 / 370 / 365 | 2 / 1 / 1 / 2 / 2 / 1 / 1 / 1 | net boy 1115 / 835 / 780 / 627,5 / 602,5 / 405 / 375 / 370 aynı adetlerle | adet ✓, boy yazılışı ✗ | **kural** (sipariş boyu) |
| 100'lük vasistaslı pano 1250 | 1 | 1 | ✓ | |
| 60'lık dolu 1250 | 7 | 7 | ✓ | |
| 60'lık dolu 1220 / 1200 (T'de kısalan) | 2 / 2 | 4 × 1250 ("liste kuralı", P6001) | ✗ | **kural** (P6001 kuralı yanlış) |
| 60'lık dolu 775 / 595 / 315 | 1 / 1 / 2 | 780 / 597,5 / 320 | adet ✓, boy ✗ | kural (sipariş boyu) |
| Pencere üst panel 1250 × 500 | 5 | 5 | ✓ | |
| Pencere alt panel 120/120 (h 800) / 120/180 (h 200) | 3 / 2 | 3 / 2 | ✓ | |
| Karkaslı çelik kapı panosu 1250 | 1 | 1 | ✓ | |
| 60'lık karkaslı + kasalı 1250 / 1220 | 3 / 2 | 3 / 2 | ✓ | |

### 1002 Metal aksam

| Gerçek | Adet | Bizim | Sonuç | Sınıf | Fabrikanın formülü / açıklaması |
|---|---|---|---|---|---|
| 10'luk köşe direği 100 × 100 + özel köşe direği B, C, D | 3 + 1 + 1 + 1 | 6 | toplam ✓ | **karar** (özel köşe hangi köşede?) | — |
| 6'lık köşe direği | 1 | 1 | ✓ | | |
| Köşebent L 2500 | **0** | 61 | ✗ | **kural** (çelik kuralı prefabrikte geçmiyor) | "Tek kat için 7 adet yazılır; kullanılır diye ekstradan" ama 0 girilmiş |
| Kutu profil kiriş 3240 / 1900 | 1 / 1 | 3240 / 1900 | ✓ | | |
| Özel kutu profil kolon 100 × 100 × 2500 | 1 | 1 | ✓ | | |
| Profil vidalama aparatı | 2 | — | eksik | elle | "özel profillerde; ekstradan ekledik" |
| H dübelli & kulaklı / H dübelli (100) | 12 / 7 | 19 | toplam ✓ | **karar** (pafta katmanında 12 / 7 tutuyor: kulaklı = makasa denk gelen ek) | — |
| H standart 60 | 10 | 10 | ✓ | | |
| 3'lü H dübelli & kulaklı / dübelli | 2 / 3 | 5 | toplam ✓ | karar (pafta 2 / 3) | — |
| 3'lü H standart 60 | 4 | 4 | ✓ | | |
| Çektirme U'su 60 | 2 | kural yok | eksik | | "duvarların ortasına gelen adet + 2; iki çektirme U'su sırt sırta H olur" |
| Çektirme U'su 100 | 2 | kural yok | eksik | elle | "(pencere × 2 × pencere eni) ÷ 244 + 2" = 4,9; "pencere özel iletiliyor, 2 fix yaz" |
| 100'lük pencere U'su H geçen | 1 | kural yok | eksik | elle | "(pencere × 2 × pencere boyu) ÷ 250"; 7 çıkar, 1 girilmiş |
| Özel pencere karkası 120 × 120 / 120 × 180 | 3 / 2 | kör kasa yalnız 120/180 × 2 | ✗ | **kural** (her pencereye karkas) | — |
| 60'lık duvar omegası (asma dizme tavan) L 3750 | 8 | (tavan omegası 25) | ✗ | **kural** (tavan sistemi farklı) | "düz tavan olan yerlerde 125,5 cm'de bir; veranda tavanı ters tavan" |
| 100'lük duvar omegası | 0 | kural yok | ✓ (0) | | "saçak ve baş makas omegası gelmeyen dış duvarlara; uzunluk ÷ 250" |
| 100'lük saçak omegası | 9 | 10 | ✗ 1 | kural / elle | "uzunluk ÷ 250"; kaba 8 → 9 girilmiş. Bizim: her saçak kenarı (10,6 m) ÷ 2,5 ayrı yukarı |
| Saçak sacı 30'luk (3'ü menfezli) | 10 | 10 | ✓ | | "(saçak kenarları ÷ 230) + 2"; kaba 9,2 |
| Alın sacı 30'luk | 7 | 7 | ✓ | | "(alın eğik kenarları ÷ 230) + 2"; kaba 6,0 |
| Baş makas omegası L 2500 | 5 | — | eksik | **kural** | "makas alınlarının duvar üstüne geldiği uzunluk ÷ 250" = 2 × 600 ÷ 250 = 4,8 |
| Baş makas Z'si L 2800 | **0** | 8 | ✗ | **kural** (prefabrikte yok: yerine baş makas omegası) | formül 5 verir, 0 girilmiş |
| Baş makas betopanı 1250 × 2500 | 4 | kural yok (pafta katmanı 4 ✓) | eksik | pafta | "AutoCAD'de betopan çizilerek bulunur" |
| 100'lük alt çerçeve L 3750 | 9 | 9 | ✓ | | "dış duvar ÷ 375" |
| 60'lık alt çerçeve | **L 2500 × 9** | L 3750 × 6 | ✗ | **kural** (parça boyu 2500) | "iç duvar ÷ 250" |

### 1004 · 1005 · 1006 Tavan, makas, çatı

| Gerçek | Adet | Bizim | Sonuç | Sınıf | Formül |
|---|---|---|---|---|---|
| Aşık L 4200 | 36 | 38 (pafta 42) | ✗ 2 | elle / karar | "(aşık uzunlukları ÷ 410) + 5"; kaba 41,2 (+5 = 47); 36 girilmiş |
| Makas 80 × 0,8 | 9 | 2 baş + 7 orta | ✓ | | ağırlık 268,56 |
| Sandviç panel (100 cm kapatır) | 22 · **L 3500** | 22 · L 3525 | adet ✓, boy ✗ 25 mm | **kural** (taşma yok ya da 50'ye yuvarlama) | — |
| Metal kiremit mahyası L 2800 | 5 | mahya 5 | ✓ | | |
| Sandviç panel kapaması | 0 | — | ✓ (0) | | kaba 8,2 |
| Mahya bandı (rulo 10 m) | 2 | — | eksik | | "düz ve ters mahya uzunlukları ÷ 1000" |
| Çatı izolasyonu 100 mm (9,6 m²/paket) | 4 | şilte 7 | ✗ 3 | **elle** | "çatı taban alanı (30 cm payla) ÷ 9,6" = 6,4; 4 girilmiş |
| Veranda / sundurma tavanı Boardex | 0 | — | ✓ (0) | | kaba 2,5 |
| Tavan beyaz alçıpan 1200 × 2500 | **8** | 17 | ✗ 9 | **elle / kural** | "(tavan alanı × 1,05 ÷ 3) + 2 (ıslak zemin hariç)" = 15,6 → 8 girilmiş |
| Tavan yeşil alçıpan | 0 | 3 (veranda) | ✗ | **karar** (Lokman 7 Ekim: veranda tavanı yeşil alçıpan; listede veranda "ters tavan", yeşil yalnız ıslak hacim formülünde) | "(WC tavanı × 1,05 ÷ 3) + 1" = 1,55 → 0 |

### 1011 Dere

| Gerçek | Adet | Bizim | Sonuç | Sınıf |
|---|---|---|---|---|
| Metal dere L 4000 | 6 | 6 | ✓ | ("÷ 380, 20 cm bindirme") |
| Dere inişi aparatı | 6 | 6 | ✓ | |
| Dere kapağı | **4** | 5 | ✗ | **kural** (Excel motorunda beşik 5) |
| PVC iniş borusu L 2500 + L 500 | 6 + 6 | L 3000 × 6 | adet ✓, parça ✗ | **kural** (iniş başına 2500 + 500) |
| Açık / kapalı dirsek, PVC kelepçe, dere kelepçesi | 12 / 6 / 12 / 48 | 12 / 6 / 12 / 48 | ✓ | |

### 1003 Kapı ve pencere · depo · vida · elektrik · tesisat · boya

| Gerçek | Adet | Bizim | Sonuç | Sınıf |
|---|---|---|---|---|
| Prefabrik çelik kapı | alıcıya ait | 0 (alıcıya ait) | ✓ | |
| Amerikan kapı 82 × 196 sağ / sol | 3 / 2 | 80 × 198 × 5 | toplam ✓; ölçü ✗; sağ / sol yok | **kural** (ölçü; sağ / sol D-13 menteşesinden çıkar) |
| **Pencere grubu** | **alıcıya ait** | PVC pencere 3 + 2, vasistas 1 | ✗ | **girdi** (paftanın açıklamasında "pencere detayı alıcıya ait"; listede pencere grubunun tamamı) |
| Acil müdahale kapağı | alıcıya ait | `alici_ait`'te var, satır yok | ✓ (0) | |
| Tavan H'ı L 1185 (asma dizme tavan) | 66 | kural yok | eksik | "duvar omegalarına dik, 62,5 cm'de bir"; kaba 65 |
| PVC omega kapak L 3750 | 10 | — | eksik | "duvar üstü omegalar hariç ÷ 3,65" |
| PVC plastik betopan haşı | 5 | — | eksik | "standart 3 ile 5 arası" |
| Çelik dübel / şase pul | 0 / 24 | — | eksik | "dübelli H adedi kadar" (12 + 7 + 2 + 3 = 24): pul 24, dübel 0 girilmiş |
| Vida: 16 mm betopan ve kapı kolu 250 · 5,5 × 110 sandviç panel 400 · trapez uç 4 · PH2 uç 4 · inox taş 6 | | alçıpan vidası 800 ✗, pencere vidası 120 ✗ | ✗ / eksik | **kural** (prefabrik vida takımı farklı; gerçekte alçıpan vidası 0) |
| Elektrik grubu: glop 2, ampul 8, NYM 3 × 2,5 130 m, 2 × 1,5 100 m, uydu kablo 25 m, besleme 5 + boru 5, anahtar 4 + 2, priz 15 + 4, uydu prizi 1, zil 1, sigorta kutusu 1, izole bant 4, kaçak akım rölesi 2 | 16 satır | kural yok | eksik | **karar** (elektrik planı olmadan bu adetler nereden? m² / oda kuralı mı, sabit takım mı) |
| Sıhhi tesisat, vitrifiye, batarya | alıcıya ait | 0 | ✓ | |
| Boya grubu, mastik | alıcıya ait | 0 | ✓ | |
| Dayson (antrasit) | 1 | — | eksik | "beşikte m² × 0,03" = 1,8 → 1 |

## Bizim hatalarımız (varsayılan hesap düzelecek; protokol §5)

1. **Pencere grubu alıcıya ait** (girdi): `alici_ait` paftanın açıklamasından tam okunmamış.
2. **Pano sipariş boyu** (kural): net − 2,5 mm, 5 mm'ye aşağı. 50 / 50 tutuyor. P6001'in "T panosu 1250" kuralı kalkar.
3. **Her pencereye özel pencere karkası** (kural): kör kasa yalnız 120/180'de değil.
4. **60'lık alt çerçeve L 2500** (iç duvar ÷ 2,5).
5. **Baş makas Z'si yok, baş makas omegası var** (kalkan duvar üstü boyu ÷ 2,5).
6. **Köşebent prefabrikte 0** (çelik kuralı uygulanmaz).
7. **Dere kapağı beşikte 4; iniş borusu iniş başına L 2500 + L 500.**
8. **Tavan sistemi "asma dizme tavan":** 60'lık duvar omegası (125,5'te bir), tavan H'ı (62,5'te bir), PVC omega kapak, betopan haşı. Bizim yöntem B tavan omegası bu yapıda yok.
9. **Vida takımı prefabrikte farklı** (sandviç panel trapez vidası, betopan vidası, uçlar, inox taş).
10. **İç kapı ölçüsü 82 × 196**; sağ / sol ayrımı.

## Karar bekleyenler (Lokman)

1. **Fabrika kendi formülünden az yazdığında hangisi doğru?**
   - aşık: formül 47, girilen 36;
   - çatı izolasyonu: formül 6,4, girilen 4;
   - beyaz alçıpan: formül 15,6, girilen 8;
   - saçak omegası: formül 8, girilen 9.

   Bu satırlarda biz kuralı mı izleyelim, sevk edileni mi?
2. **Özel köşe direkleri (B, C, D):** hangi köşelerde, kuralı ne?
3. **H'da kulaklı / dübelli ayrımı:** "makasa denk gelen dış ek kulaklı" kural olsun mu? Paftada 12 / 7 tutuyor.
4. **Elektrik grubu** planı olmayan projede nasıl sayılıyor (sabit takım mı, m² / oda mı)?
5. **Veranda tavanı:** yeşil alçıpan mı (7 Ekim kuralı), ters tavan mı (bu listede)?
6. **Fabrika şablonunun formül sütunu:** "PORTATİFEV YÜKLEME LİSTESİ", Ubeydullah, 1 Ekim 2026. Bu formüller kural kitabına toptan alınsın mı? Her biri bir sonraki PK'da sınanır.
