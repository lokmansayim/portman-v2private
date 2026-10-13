# PK-07 · Diamond 70,65 m² (Aziz Bey, Manisa; Halil Bey; Portatifev) · pafta okuması (kör test adım 1–3, pafta kipi)

13 Ekim 2026. Kaynak: Mac `~/Desktop/Portatifev Toptan/Bayiler/Aziz Bey - Manisa/70 m² Prefabrik - Halil Bey/`:
`DIAMOND 70 M2 MONTAJ PAFTASI.pdf` (13 sayfa; çizen Ubeydullah Özer, kontrol Lokman Sayım) ve `DIAMOND 70 M2 URETIM DOSYASI.zip` (makine CSV'leri).
Depoda `kaynak/PK07_MONTAJ_PAFTASI.pdf` (`a819c0f1…1b71`) ve `kaynak/PK07_URETIM_DOSYASI.zip` (`c799e4cb…537c`).
Gerçek liste **açılmadı** (`DIAMOND 70 M2 YUKLEME LISTESI.pdf`, `985c3a20…6086`; MUHUR.md).

Aynı klasördeki `70 m² Prefabrik - Halil Bey.xlsx` / `.pdf` ve `… - Revize.xlsx` / `.pdf` (teklif ya da liste olabilir) **açılmadı**:
özetleri MUHUR.md'ye yazıldı, kıyastan sonra bakılacak.

## Neden pafta kipi

Motor çizemiyor:
- iç duvarlar 100 mm;
- salon önde 120 cm çıkıntılı (L plan), önüne ana çatıya paralel küçük beşik ("cumba");
- 100/120 pencere (147,5'lik çelik duvar paneli D01);
- verandada hafif çelik panelli sandviç saçak.

## Okuma

- **Ölçüler:** 785 × 900, brüt 70,65 m² (veranda dahil; paftada "70,65 m²"). Kapalı bina L, veranda 393,5 × 120 = 4,72 m². Dış çevre 33,7 m.
- **Panolar:** 57 (dış 33, iç 24; hepsi 10 cm). İç / dış ayrımı konumdan (kalınlık aynı).
  - Boylar yazıdan: 125,5 (25), 62,75 (11), 74,75 (6), 120,5 (5), 79,75 (2), 40,75 (3), 147,5, 115,5, 74,25, 45,75, 69,25.
  - Köşe: 10 × 5 köşe 6 (biri iç duvarların L birleşimi). 10 × 10 kutu profil 2: A, salonun ön sağ köşesi; B, veranda dikmesi.
- **Pencereler** alıcıya ait: 120/120 × 4, 100/120 × 1 (D01), 60/40 × 1.
  - Karkas (C: çektirme U'su 100 + pencere U'su H geçen) 4 adet bizde (sayfa 4–5).
- **Kapılar** (kanat dörtgenlerinden):
  - dış kapı sağ bölümün önünde, hola açılır (SOL);
  - iç kapılar SOL 3 (oturma, yatak, mutfak) + SAĞ 2 (salon, banyo);
  - üretimde iç kapı panoları çelik (KAPI-01…05, 1250 × 2490).
- **H planı (sayfa 3) okuyucuyla birebir:**
  - kulaklı 11 / dübelli 12;
  - 3'lü kulaklı 1 / dübelli 3;
  - standart 14, 3'lü standart 4.

  Lejant kuralı: "Dış duvarlarda çatı makaslarına denk gelen H'lar" kulaklı. Bu, PK-06'dan sonra sürüm 6'ya alınan kuralla aynı.
- **Çatı:**
  - ana beşik: 785 açıklık, 780 boy (y 120–900), 18,2° (%32,9), eğik 444,75. Makas 7 (MK01–MK07, üretimde alt başlık 8450).
    Sol yüz cumbanın sol yüzüyle aynı düzlemde ve öne 120 uzar.
  - cumba: paralel beşik, 391,5 × 120, eğik 237,64, makas 3 (MK08–MK10, 4515).
  - veranda saçağı: hafif çelik panel 3925 × 1189, üstünde 4 × 125 sandviç panel.
  - aşık 146,7 m (4200'lük boydan 37).
  - kaplama sandviç bordo: 450 × 18 + 240 × 3 + 125 × 4 = 25.
- **Tavan:** ters; omega 42 parça, 112,8 m (veranda yok).
- **Baş makas betopanı** (sayfa 10): 7. **Özel büküm** saçak sacı L 2500 × 2, alın sacı L 2500 × 2 (bordo).
- **Özel profiller:**
  - A: kolon 2500 + çektirme U'su + vidalama aparatı;
  - B: kutu profil 2098;
  - D: dış köşe direği + çektirme U'su;
  - E: kiriş 3935.
- **Elektrik** (göz): duy 5, glop 3 (banyo 1, veranda 2), anahtar 7, priz 13 + çift 1, uydu 1, sigorta 1; zil yok.
- **Özellikler:** Pres Panel, beşik + cumba, sandviç panel bordo, çelik standart dış kapı, Amerikan iç kapı, ters tavan.
  - Saçak ve alın bordo; boya "?".
  - Açıklama: "dış cephe fugalı düz betopan", "çatı izolasyon mineral yün".

## Üreteç sürüm 6.1 (gerçek liste açılmadan; model alanları)

- İç duvar kalınlığı `kal_mm`'den: 100'lük iç pano, H standart 100, iç köşe 10'luk, 3'lü H 100 × 100 × 100.
- Çatı parçasında `kalkan_duvar_cm`: ana çatının ön kalkanının altında yalnız 393,5'lik duvar var.
- Açıklamada dış cephe betopanı → ilk tahmin: dış çevre × 2,5 − boşluklar, × 1,08 ÷ 3,125.
- H ve pencere karkası satırlarına pafta sütunu.
- PK-01/02/03/05/06 çıktıları sürüm 6 ile aynı.

## Liste (adım 3)

`sonuc/PK07_liste.json` / `.xlsx`, 100 satır.

    python3 -I deneme/2026-10-13_pk_07/pafta_oku.py
    python3 deneme/2026-10-13_kor_test_seri/yukleme_listesi.py --yapi deneme/2026-10-13_pk_07/yapi_pafta.json deneme/2026-10-13_pk_07/sonuc \
        --pafta deneme/2026-10-13_pk_07/pafta_katmani.json
