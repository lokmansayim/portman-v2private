# PK-03 · Doğan Prefabrik 80 m² (Nimet Bey; Loftev) · montaj paftası okuması (kör test adım 1–3, pafta kipi)

13 Ekim 2026. Kaynak: Mac `~/Desktop/Portatifev Toptan/Bayiler/Doğan Prefabrik Keşan/Proje1 80m2/Montaj Paftaları/` (17 Eylül 2025: montaj ve
elektrik, aşık, çatı kaplaması, makas ve dere, tavan omega) + `PREFABRİK - DOĞAN PORTATİF EV - 81 M2/Montaj Paftaları/` (müşteri onay ve
15 Eylül montaj planı, karşılaştırma için). Çizen Ebru Balcı / Batuhan Tınmaz, satış temsilcisi Lokman Sayım. Gerçek listeler **açılmadı**
(iki sürüm mühürlü: `1a42996f…ad67` 15 Eylül, `fe5948f5…3f04` 17 Eylül; `deneme/2026-10-13_kor_test_seri/MUHUR.md`).

## Neden pafta kipi

Motor bu planı çizemiyor (Lokman 13.10 11:45, "ikisi birden"): **160/180 pencere iki modüllük (251'lik) panoda**, **L plan** (mutfak önde 125,5 cm
çıkıntılı, salonun önünde veranda), **verandaya çapraz beşik** (MK10, MK11). Pano geometrisi `pafta_oku.py` ile doğrudan paftanın vektörlerinden
okunur (`pafta_montaj.json` → `yapi_pafta.json`); liste üreteci sürüm 3 aynı kuralları uygular.

## Okuma

- **Dış ölçü** 951,5 × 898,7 (veranda dahil); kapalı bina 67,3 m², veranda 492 × 241; brüt 79,9 m² (paftada "80 M2").
- **Panolar:** 48 (dış 27, iç 21). 160/180 pencereler 251'lik tek panoda (salon önü, mutfak önü). 62,75'lik özel panolar kırmızı (dış 4, iç 3).
  Köşe: dış 6 (5 × 10), iç 3 (3 × 6); veranda dikmesi 2 (10 × 10).
- **Pencereler** (etiketten panoya): 120/120 × 3 (arka iki, sol bir), 160/180 × 2, 60/40 × 1 (banyo; planda "60/60" yazıyor, görünüş "60/40, 1 adet").
- **Kapılar** (kanat yaylarından, menteşe yönüyle): dış kapı holün önünde (SAĞ; kanat 82 çizilmiş, ölçü K04 90), iç kapılar mutfak, banyo, salon,
  yatak 1 SAĞ; yatak 2 SOL.
- **Ekler:** dış pano eki 18 (saçak duvarında 10), dış T 3 (saçakta 2), iç pano eki 10, iç T 3.
- **Çatı:** ana beşik 1011 × 833 (9 makas, aralık 118; eğim paftada yok: trapez boyu 440'tan %30 alındı), veranda çapraz beşiği 565 × 156
  (MK10, MK11; ana mahyayla aynı yükseklik varsayımıyla %44), ayrıca MK12. Aşık: ana 16 × (410 + 410 + 191,25), veranda 2 × 6 sıra (dere içe uzuyor).
  Kaplama trapez: 440 × 80 × 25 + 300 × 80 × 7.
- **Tavan:** ters tavan (omega 60 cm'de bir; veranda dahil); tavan planında 52 parça, 135,2 m.
- **Elektrik** (göz): duy 6, glop 2, anahtar 5 + çift 1, priz 14 + çift 3, uydu 1, zil 1, sigorta kutusu 1.
- **Özellikler:** poliüretan panel, trapez kırmızı, çelik dış kapı, Amerikan panel iç kapı, Sandeco boya, ters tavan, metal dere ve iniş.
  Açıklama: **"iç cephede alçıpan kaplama yapılacaktır"** (duvar alçıpanı; kuralı yok, üreteçte ilk tahmin).

## Motor'un çizemedikleri (Motor genişletme iş emri için)

1. Pencere ölçüleri yalnız 120/120, 120/180, 60/40: **160/180** yok; iki modüllük pencere panosu (251) yok.
2. Dikdörtgen olmayan dış çizgi: **önde çıkıntı** (mutfak) ve çıkıntının yanında veranda.
3. **Çapraz beşik** (veranda çatısı) ve dere içe doğru uzayan aşıklar; çatı parçaları.
4. Ters tavan / asma tavan ayrımı Motor'da yok (yalnız listede).

## Liste (adım 3)

`deneme/2026-10-13_kor_test_seri/yukleme_listesi.py --yapi yapi_pafta.json` (sürüm 3; varsayılan Portatifev, Loftev farkları "aday"da):
`sonuc/PK03_liste.json` / `.xlsx`, 108 satır.
