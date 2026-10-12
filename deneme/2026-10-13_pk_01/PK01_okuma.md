# PK-01 · Huma 60 m² tek kat prefabrik — kör test, okuma kaydı (13 Ekim 2026 00:20)

İlk prefabrik kör testi (`docs/sartname/prefabrik_kor_test.md`; D-10). Lokman 12 Ekim 23:52'de Mac klasörünü bağladı ("ilk testi bunda yapabilirsin").
Bu belge montaj paftasının **okumasıdır**; motor çizmedi (aşağıda neden). Gerçek yükleme listesi **açılmadı**.

## Kaynak (Mac `~/Desktop/AIPrefabrik/Huma 60 m² Tek Kat /`)

| Dosya | SHA-256 | Durum |
|---|---|---|
| `HUMA 60M2 MONTAJ PAFTASI.pdf` (10 sayfa A3; iLovePDF birleştirme) | `492c7613 0da0e66a 6dce82eb aa67e3f9 da9949eb 314c1034 445d223f aaac658d` | okundu → `kaynak/` |
| `HUMA 60M2 BASMAKAS BETOPAN YERLESIMI.pdf` (AutoCAD 2027, 1 Ekim 2026) | `a3806470 80280982 bbede9cd 72725eeb 9e4101ba dacbb64d 1606bb0f 2addc3f1` | okundu → `kaynak/` |
| `HUMA 60M2 OZEL PROFIL.pdf` (AutoCAD 2027, 1 Ekim 2026) | `6b481fbc 2387aa17 2a955da9 60d44c15 a8d0fd19 6fac9357 12075072 0e293b27 00e` → tam: `6b481fbc2387aa172a955da960d44c15a8d0fd196fac9357120750e293b2700e` | okundu → `kaynak/` |
| `HUMA 60M2 YUKLEME LISTESI.xlsx` (196.855 bayt) | `17e43b88 8bd1a5dd 5bfb06eb b38b620b 1b0c3708 c176a35d 7ea576f1 e948d106` | **mühürlü: açılmadı, kopyalanmadı.** Kendi listemiz depoya kaydedilince açılacak; hash o gün bununla karşılaştırılır |

Pafta künyesi: Huma Prefabrik, 60 m² prefabrik konut; çizen Ubeydullah Özer, kontrol Lokman Sayım (D-11: adlar yazılabilir).

## Teknik özellikler (sayfa 1 tablosu)

Bina yüksekliği 2500 mm · dış duvar **100** mm · iç duvar **60** mm (standart; D-10) · panel türü Pres Panel · çatı beşik · çatı kaplaması
sandviç panel, antrasit gri · dış kapı alıcıya ait · iç kapılar standart Amerikan · dış ve iç cephe boya alıcıya ait · pencere rengi alıcıya ait ·
tavan düz · saçak ve alın rengi antrasit gri. Açıklama: su tesisatı, vitrifiye, boya grubu (mastikler dahil), acil müdahale kapağı alıcıya ait.
Pencere detayı: alıcıya ait.

## Geometri (cm; montaj planı, sayfa 2; dış yüzler)

- Dış ölçü **600 × 1000**; brüt oturum 60,0 m² (veranda dahil; "biz her zaman brüt oturum alırız").
- Çatı: beşik, mahya uzun kenara (1000) paralel; makas açıklığı 600, saçakla 660; eğim 18,2° (= %33), mahya yüksekliği 118,5, mertek boyu 347,38; saçak 30.
- **Pano ızgarası** (modül 125,5) montaj planıyla tam tutuyor:
  - x aksları (sol dış duvarın iç yüzünden): 10 · 135,5 · 261 · 386,5 · 512 · **590** (son pano **78** = 580 − 4 × 125,5). Yarım aks: **198,25** (135,5 + 62,75).
  - y aksları (arka duvar ekseninden, 5): 5 · 130,5 · 256 · 381,5 · 507 · 632,5 · 758 · 883,5 · **995** (son pano **111,5** = 990 − 7 × 125,5).
  - **Dizilim arka-soldan başlar; kesilmiş panolar sağda (78) ve ÖNDE (111,5).** 6 Ekim denemesindeki "kesilen parça sağ ve arka uçta" çıkarımı burada **tutmuyor**: kesim öndedir (veranda tarafı).
  - Paftadaki özel boylar bu ızgaradan çıkıyor: 62,75 (yarım), 122,5 ve 120,5 (T birleşiminde 3 / 5 cm kısalan pano), 59,75 (62,75 − 3), 32 (758 → 790), 37 (758 → 795), 83,5 (800 → 883,5), 60,25 / 40,5 / 37,5 (pencere yan parçaları).
- Duvar aksları: x = 198,25 (yatak odası 1 / banyo; yalnız arka 256'ya kadar), 261 (mutfak ve yatak odası 1 / hol), 386,5 (banyo ve yatak odası 2 / hol ve salon);
  y = 256 (banyo altı), 381,5 (yatak odaları / mutfak ve salon), **795 (hol ve salonun ön duvarı — aks dışı: 758 + 37)**.
- **Aks dışı duvar:** hol ve salonun ön duvarı 790–800'de (ekseni 795), çünkü veranda derinliği 190 (800–990). Bu duvar 125,5 ızgarasının ne tam ne yarım adımında (758'den 37 cm ileride).

## Mahaller (net; cm ve m²)

| Mahal | Net x | Net y | m² (pafta) | Not |
|---|---|---|---|---|
| Yatak odası 1 (sol arka) | 10–195,25 (185,3) üstte; 10–258 (248) altta | 10–378,5 (368,5) | 7,5 | **L biçimli:** banyonun altında x 201–258 şeridi odaya katılmış |
| Banyo | 201,25–383,5 (182,25) | 10–253 (243) | 4,4 | 60/40 arka duvarda |
| Yatak odası 2 (sağ arka) | 389,5–590 (200,5) | 10–378,5 (368,5) | 7,3 | |
| Hol | 264–383,5 (119,5) | 259–790 (531) | 6,3 | beş kapı + dış kapı |
| Mutfak | 10–258 (248) | 384,5–990 (605,5) | 14,9 | ön duvarda 120/180 |
| Salon | 389,5–590 (200,5) | 384,5–790 (405,5) | 8,1 | sağ duvarda 120/120, ön duvarda 120/180 |
| Veranda | 276–600 (324) | 800–990 (190) | 6,6 | sağ ve ön açık (yeşil kesik çizgi); sol duvarı dış duvar (266–276) |

Sayfa 1 zincirleri: üst 201,25 · 188,25 · 210,5 (duvar yüzlerine); alt 266 · 117,5 · 216,5; sol 378,5 · 621,5; sağ 384,5 · 415,5 · 200.

## Açıklıklar

| Tür | Yer | Pano | Not |
|---|---|---|---|
| 120/120 | Yatak odası 1, sol dış duvar | y 130,5–256 (2. pano) | panoda ortalı |
| 120/120 | Yatak odası 2, sağ dış duvar | y 130,5–256 | panoda ortalı |
| 120/120 | Salon, sağ dış duvar | y 507–632,5 (5. pano) | panoda ortalı |
| 60/40 | Banyo, arka dış duvar | x 204,25–326,75 (122,5'lik pano) | |
| 120/180 | Mutfak, ön dış duvar | iki yanında 60,25 (240,5'lik açıklıkta ortalı) | pano sınırı teyit ister |
| 120/180 | Salon, ön dış duvar (y 795) | **iki yanında 40,5 / 37,5 → odada ortalı, 512 aksını geçiyor** | "pano içinde ortalama" kuralına uymuyor; pano yerleşimi teyit ister |
| Kapı 82 | Banyo ↔ hol | banyonun alt duvarı, 264–386,5 (122,5) | kanat banyoya |
| Kapı 82 | Yatak odası 1 ↔ hol | holün sol duvarı, y 256–381,5 (122,5) | |
| Kapı 82 | Yatak odası 2 ↔ hol | holün sağ duvarı, y 256–381,5 | |
| Kapı 82 | Mutfak ↔ hol | holün sol duvarı, y 381,5–507 | |
| Kapı 82 | Salon ↔ hol | holün sağ duvarı, y 381,5–507 | |
| Dış kapı | Veranda ↔ hol | holün ön duvarı (y 795) | **alıcıya ait** (boşluk var, doğrama listeye girmez) |

## Paketin doğrudan verdikleri (listeye girecek adetler; sayım koddan, `pdfplumber`)

- **H profil montaj planı (sayfa 3), 6 tip, 39 adet:** H dübelli & kulaklı (100×100×2500; dış duvarda çatı makasına denk gelen) **12** · H dübelli (dış, makasa denk gelmeyen) **7** · H standart (60×60×2500; iç) **10** · 3'lü H dübelli & kulaklı (100×100×60×2500) **2** · 3'lü H dübelli **3** · 3'lü H standart (60×60×2500; iç) **5**. Dış H 19, iç H 10, üçlü 10.
- **Makas ve dere yerleşim planı (sayfa 7):** **9 makas** MK01–MK09; aralık 117,5 + makas 8 = **125,5 c/c** → makaslar pano akslarında (MK01 arka aks 5, MK09 ön aks 995; son aralık 103,5 + 8 = 111,5 = kesilmiş pano) → 6 Ekim çıkarımı ("makaslar pano akslarında") **tutuyor**: 2 baş + 7 orta. Dere: iki uzun kenarda.
- **Aşık yerleşim planı (sayfa 8):** iki yarı (mertek 347,4), yarı başına **7 sıra**, her sıra 410 + 410 + 240 = 1060 (1000 + 2 × 30 saçak) → **42 parça** (28 × 410, 14 × 240).
- **Tavan omega yerleşim planı (sayfa 6):** boylar 365 × 8, 243 × 1, 240,5 × 1, 249 × 1, 190 × 6 (veranda), 166 × 2, 50 × 1 (okuma; adetler yeniden sayılacak).
- **Baş makas betopan yerleşimi:** iki kalkan için **4 adet 125 × 250** betopan.
- **Özel profil** (ayrı pafta) ve **özel kutu profil & H kaynak detayları** (sayfa 4): okunacak.
- Sayfa 5: betopan 250 × 125 (dış kaplama yerleşimi), sayfa 9: çatı şekli / 350 / 100, sayfa 10: görünüşler — okunacak.

## Motor neden çizmedi (pano motorunun bu projede eksikleri → genişletme iş emri)

1. **Aks dışı duvar:** hol/salon ön duvarı 795'te (758 + 37). Motor ve 6 Ekim denemesi mahal sınırlarını yalnız tam / yarım pano adımında alıyor ("Grid yarım pano adımında"). Gerek: duvar aksının cm ile verilebilmesi; o duvara dik koşularda 37 / 32'lik özel parçalar.
2. **Kesim ucu:** 6 Ekim denemesi kesilen parçayı sağ ve **arka** uca koyuyor (`min(v, Y_SON)`); bu projede kesim **önde** (111,5). Gerek: `kesim_ucu` seçimi (x: sol/sağ, y: ön/arka) ya da dizilimin başlangıç köşesi.
3. **L biçimli mahal:** Motor `konum_pano` listesiyle birden çok dikdörtgeni destekliyor (P6001 yaşam alanı); banyo altındaki şerit için yeterli — teyit koşuda.
4. **Panoyu aşan pencere:** salonun ön 120/180'i 512 aksını geçiyor; Motor pencereyi tek panoda ortalar. Gerek: ya pencere yeri cm ile ya da "odada ortalı" seçeneği; bu paftadaki pano yerleşimi mühendise sorulacak.
5. **Alıcıya ait dış kapı:** boşluk var, doğrama yok — listede "alıcıya ait" satırı; Motor'da `dis_kapi` her zaman doğrama sayıyor.
6. **Veranda dış duvarı:** hol aksı 261 ile veranda sol duvarı (266–276) aynı hizada değil (10 cm kayma); Motor'un veranda kuralı teyit ister.

Bu yüzden kör testin 2–3. adımları (motor çizimi, kendi listemiz) **beklemede**; 1. adım (okuma) bu belge. Gerçek liste mühürlü kalır.

## Kural adayları (bu paketten; Lokman / mühendis teyidiyle kural olur)

- Makas = pano aksı başına bir makas (2 baş + orta), baş makaslar dış duvar ekseninde; makas genişliği 8.
- Aşık: yarı başına 7 sıra; boylar 410 / 410 / 240 (toplam = bina boyu + 2 saçak); bindirme yok görünüyor (teyit).
- H tipleri altıya ayrılıyor: dış–iç × tekli–üçlü × makasa denk gelen (kulaklı) / gelmeyen (dübelli).
- Baş makas betopanı: kalkan başına 2 × (125 × 250).
- Dış duvarlar 100 mm'de bile köşe parçası ve H ölçüleri: H 100×100, iç H 60×60.
- İç duvarın T'ye gelen panosu 3 cm (122,5) ya da 5 cm (120,5) kısalır (Astra v1.4.3 ile aynı).
