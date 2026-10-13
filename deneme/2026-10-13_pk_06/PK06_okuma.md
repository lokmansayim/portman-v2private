# PK-06 · Sevim Güler 82 + 10 m² (Çorlu; Mehmet Yıldırım bayisi; Loftev) · pafta okuması (kör test adım 1–3, pafta kipi)

13 Ekim 2026. Kaynak: Mac `~/Desktop/Portatifev Toptan/Bayiler/Mehmet Yıldırım Çorlu/İlk Dönem/Sevim Güler/Montaj Pafta ve Yükleme/1–8.pdf`
(depoda `kaynak/PK06_1..8.pdf`). Sekiz sayfanın hiçbiri liste değil: 1 müşteri onay (özellik tablosu; "PROJE ADI XXX", çizen XXX),
2 montaj planı, 3 tavan omega, 4–5 makas ve dere, 6 aşık, 7 çatı kaplaması, 8 elektrik. Gerçek liste **açılmadı** (`3cf21751…e2fe` xlsx; MUHUR.md).

## Neden pafta kipi

Motor bu planı çizemiyor: **L plan** (salon ana bloğun soluna 188,25 taşıyor; önünde 298,5 × 313,75 veranda, dikmeleri ana bloğun 120 cm
dışında), **160/180 pencereler 251'lik iki modüllük panoda** (biri verandaya bakan "sürgülü pencere"), **verandaya ana çatıya paralel ikinci
beşik**. Geometri `pafta_oku.py` ile paftanın vektörlerinden okunur (`pafta_montaj.json` → `yapi_pafta.json`).

## Okuma

- **Ölçüler:** ana blok 951,25 × 773, salon çıkıntısı 188,25 × 449,3; kapalı brüt 81,99 m² ("82"), veranda dikme dışından 9,99 m² ("+ 10").
  Dış çevre 38,25 m (L planın çevresi zarfınkiyle aynı). Odalar net 76,3 m².
- **Panolar:** 55 (dış 30, iç 25). Boylar yazıdan: 125,5 (dış 23, iç 16), 251 (2), 62,75 (dış 4, zeytin), 115,5, 122,5 (4), 120,5 (2), 119,5,
  60,75, 49,75. Çizimdeki 62,57 / 49,57 sapmaları yazıdaki ölçüye oturtuldu.
  Köşe: dış 6 (5 × 10; L'nin iç köşesi de 5 × 10 çizilmiş), iç 2 (3 × 6); veranda dikmesi 2 (10 × 10).
- **Pencereler** (etiketten panoya): 120/120 × 3 (arka yatak 1, ön yatak 2, sağ yatak 3), 120/180 × 1 (salon arka), 160/180 × 2 (salon solu ve
  mutfağın veranda duvarı, "Sürgülü Pencere"), 60/40 × 2 (banyo, çamaşır odası).
- **Kapılar** (kanat dörtgenlerinden, menteşe sözleşmesiyle): dış kapı verandadan salona (SOL; kanat 82 çizilmiş, listede 900 × 2000, L4);
  iç kapılar mutfak SAĞ, yatak 2 SOL, yatak 3 SAĞ, banyo SOL, yatak 1 SOL, çamaşır odası SAĞ (119,5'lik panoda, hola açılır).
- **Odalar** (sayfa 8): salon (hol açık), hol ("Acil Müdahale Kapağı"), çamaşır odası ("k.m.", "ç.m."; 60/40), banyo, yatak 1, mutfak (buzdolabı,
  bulaşık makinesi, ısıtıcı H 110, fırın, davlumbaz), yatak 2, yatak 3. Çamaşır odası ıslak sayılmadı (kural yalnız banyo / WC; soru).
- **Ekler:** dış pano eki 19 (ön ve arka duvarda 12, makas ayağında), dış T 5 (3'ü ön / arkada), iç pano eki 13, iç T 4. Salon–veranda duvarı
  çatının ortasında kalır, kulaklı sayılmadı → kulaklı tahmini 15.
- **Çatı:**
  - ana beşik: 1139,5 × 773, 10 makas (MK01–MK10, 125,5'te bir), kesitten eğim %34,0 (yükselme 140,06 / 411,51, eğik 434,69), saçak 30;
  - veranda çatısı: ana çatıya **paralel** beşik, 120,3 × 333,8, MK11–MK12, eğim %32,8; ön yüzü ana çatının ön yüzüyle aynı düzlemde
    (aşık planında ön yüzün alt dört sırası 120,25 uzuyor), arka yüzü ayrı (4 × 150,25). Dere içi (ters mahya) yok; ön saçak tek hat 13,2 m.
  - aşık 202,8 m (4200'lük boydan 52); kaplama tek kat panel 30 şerit 87 × 444,9.
- **Tavan:** ters tavan; omega planında 61 parça, 169,6 m (veranda dahil).
- **Elektrik** (göz): duy 7, glop 3, anahtar 7 + çift 1, priz 20, uydu 1, zil 1, 12'li sigorta kutusu 1.
- **Özellikler:** Press Panel, beşik, tek kat panel antrasit, çelik dış kapı, Amerikan panel iç kapı, Sandeco boya, ters tavan, saçak 30 antrasit,
  metal dere; **iniş borusu boş**; alıcıya ait kalem ve açıklama yok.

## Motor'un çizemedikleri (İE-13)

L plan ve öne taşan veranda (madde 5), 160/180 iki modüllük pano (4), paralel ek beşik ve aynı düzlemde devam eden yüz (6).

## Liste (adım 3)

Üreteç sürüm 5.1 (5'e ek tek model alanı: `capraz: false` ek beşik ters mahya almaz; PK-06 okumasından, gerçek liste açılmadan), pafta kipi:
`sonuc/PK06_liste.json` / `.xlsx`, 108 satır.

    python3 -I deneme/2026-10-13_pk_06/pafta_oku.py
    python3 deneme/2026-10-13_kor_test_seri/yukleme_listesi.py --yapi deneme/2026-10-13_pk_06/yapi_pafta.json deneme/2026-10-13_pk_06/sonuc \
        --pafta deneme/2026-10-13_pk_06/pafta_katmani.json
