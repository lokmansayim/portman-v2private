# PK-08 · Eren Bey 60 m² (Muhammed Uysal bayisi) · pafta okuması (kör test adım 1–3, pafta kipi)

13 Ekim 2026. Kaynak: Mac `~/Desktop/Portatifev Toptan/Bayiler/Muhammed Uysal/Eren Bey 60 m2 M.U./`. Depoda `kaynak/`:
- `PK08_DUVAR_YERLESIM.pdf` (`eb465f1c…d2a7`, pano yerleşimi);
- `PK08_OMEGA_YERLESIM.pdf` (`db4599b8…cb68`);
- `PK08_KAT_PLANI.pdf` (`d3aa2074…0c06`) ve `PK08_ON_PLAN.pdf` (`feee02b2…fcf3`; Uysallar Yapı mimari planı).

Montaj paftası DWG (`EROL BEY MONTAJ PAFTASI.dwg`), okunamıyor. Özellikler satış teklifinden (`Eren Bey 60 m2 Prefabrik Teklif.pdf`, 19 Ağustos 2025).
Teklif Mac'te okundu ama kopyalanmadı; fiyatı ve kişi bilgisini almadık. Teklifler (60 / 70 m² xlsx, `PREFABRİK - TEKLİF PORTATİFEV.xlsx`) açılmadı.
Gerçek listeler **açılmadı** (`LOFTEV PREFABRİK YÜKLEME LİSTESİ.xlsx` `dca060f8…531c`, `M.Uysal Eren Bey 60 ㎡Yükleme Listeis.xlsx` `a748c76b…41ea`).

## Okuma

- **Ölçüler:** 769,8 × 782,5 (veranda dahil; "60 m²") + açılı cumba (57 cm derin; 31 / 79 / 200,7 / 79 / 31). Brüt 61,7 m², dış çevre 31,3 m.
- **Panolar:** 39 (dış 28, iç 11).
  - Boylar paftadaki yazıya oturtuldu: 113, 122, 125, 124, 120, 59, 56, 24, 25, 31.
  - 240'lık sarı pano: 30 + 180 + 30, pencere 180/180.
  - Cumbada açılı 790'lık iki pano (59/170) ve 200,7'lik ön pano (105/170).
  - Köşe 6 (10 × 5); veranda dikmesi 1 (15 × 15).
- **Pencereler** (bizde): 180/180, 120/100 × 2 (salon solu, yatak 1 sağı; mimari plandan), 59/170 × 2, 105/170.
  Mimari planda cumba pencereleri 50/180, 180/180, 50/180 yazıyor; montaj planı esas alındı.
- **Kapılar** (duvar yerleşim planında yok; mimari plandaki kanat ve yaylardan):
  - dış kapı verandadan salona, SAĞ (yay r 100; listede 90 × 200);
  - yatak 1 SOL, WC SOL, yatak 2 SAĞ.
- **Ekler:**
  - dış H 20 (cumbanın dört açılı eki dahil); kulaklı 4, arka duvarda makasa denk.
  - dış T 2 (biri kulaklı);
  - iç H 6, iç T 1.
- **Çatı:** teklifte "cumba kubbeli beşik, trapez sac". Mahya x yönünde (omega planı); 7 makas.
  - Saçak 25. Eğim paftada yok: %33 varsayıldı.
  - Veranda ana çatının altında.
  - Cumbanın küçük kubbe çatısı ayrı parça: makassız, deresiz, ölçüsü tahmin.
- **Tavan:** omega planı 13 hat × 769,8, 60 cm'de bir → ters tavan varsayıldı (100,1 m).
- **Elektrik planı yok.** Sıhhi tesisat bizde; vitrifiye alıcıya ait.

## Üreteç sürüm 7.1 (gerçek liste açılmadan; model anlamı)

- 120 genişlikteki her pencere standart sayılır (üst + alt panel; 120/100 dahil).
- Vasistas yalnız en ≤ 60 ve boy ≤ 60; 59/170 karkaslı özel pano.
- Çatı parçasında `dere_yok`; vitrifiye alıcıya aitse 0; trapez çatıda yinelenen 5,5 × 60 satırı yazılmaz.
- PK-01…07 çıktıları sürüm 7 ile aynı (PK-03'te yinelenen 5,5 × 60 satırı düştü).

## Liste (adım 3)

`sonuc/PK08_liste.json` / `.xlsx`, 105 satır.

    python3 -I deneme/2026-10-13_pk_08/pafta_oku.py
    python3 deneme/2026-10-13_kor_test_seri/yukleme_listesi.py --yapi deneme/2026-10-13_pk_08/yapi_pafta.json deneme/2026-10-13_pk_08/sonuc \
        --pafta deneme/2026-10-13_pk_08/pafta_katmani.json
