# Pencere varyasyonları · tek yerde (İE-22, 28 Ekim 2026)

Lokman: "Pencere varyasyonlarını da bir yere toplaman gerekiyor." Kaynaklar: Lokman'ın 28.10 planı, Motor (BK-13 kuralı ve bloklar),
Astra R02, Güncel Şablon 2024 (envanter: 12.490 yazı, 278 blok). Ölçü **EN/BOY cm**; eşik = üst kot − boy (Motor/BK-13: üst kot 200; R02 de 2000 mm).

## 1. Bu evde (Lokman'ın planı) kullanılanlar

| Ölçü | Nerede | Motor bloğu (bugün) | Şablon 2024 adı (kural) | Eşik |
|---|---|---|---|---|
| 120/125 "standart pencere" | zemin ODA, SALON sol; 1. kat ODA 1, ODA 2 ×2 | BOM_D13/D09_1255p0_DIS_P120x125 | 100'LÜK 125'LİK (120x125) PENCERELİ PANO · **yeni (kural)** | 75 |
| 60/125 | zemin MUTFAK ön | BOM_D11_1255p0_DIS_P60x125 | 100'LÜK 125'LİK (60x125) PENCERELİ PANO · yeni (kural) | 75 |
| 60/40 vasistas | WC / BANYO arka | BOM_D04_1255p0_DIS_P03 | 100'LÜK 125'LİK (60x40) VASİSTASLI PANO · **şablonda var** | 160 |
| 120/200 "Fransız pencere" | SALON ön; 1. kat ODA 3 ön | taslakta 120x180 (BOM_D03_…_P02; Motor sınırı boy ≤ 180) | 100'LÜK 125'LİK (120x180) PENCERELİ PANO · yeni (kural) — **Soru 4** | 20 (180'de) / 0 (200'de = kapı gibi) |

## 2. Motor'un bildiği pencereler (BK-13: "ENxBOY", en 30–247, boy 20–180, üst kot 200)

120x120 (eşik 80) · 120x180 (20) · 60x40 (160) · 60x125 (75) · 120x125 (75). En > 121,5 ise 251'lik pencereli pano (komşuyla birleşir). Yeni ölçünün DXF sembolü 120x120'den ölçeklenir.

## 3. Astra R02 (çift kat 150 m²)

120×120 (eşik 800 mm) · 120×180 (eşik 200) · 60×40 vasistas (eşik 1600); her katta ön cephede 3 × 120/180, arkada 2 × 120/120, banyolarda 2 × 60/40. Lento 500, üst kot 2000.

## 4. Güncel Şablon 2024'te geçen ölçü etiketleri (yazı sayısı; pencere + kapı karışık)

| Ölçü | Adet | Not |
|---|---:|---|
| 120/120 | 363 | en yaygın pencere |
| 60/40 | 139 | vasistas |
| 120/180 | 105 | Fransız/boy pencere (`ON_PENCERE_SABLON_120180` bloğu) |
| 78/198 · 80/200 · 90/210 · 90/200 · 80/210 · 80/250 · 100/210 · 95/210 | 90 · 60 · 16 · 12 · 3 · 4 · 4 · 10 | **kapı** ölçüleri (iç 78/198, 80/200; dış 90/210, 90/200) |
| 120/100 | 65 | mutfak penceresi (`100'LÜK 125'LİK (120x100) PENCERELİ PANO` bloğu) |
| 70/180 | 37 | karkaslı pano penceresi (üç katlı ofis notu) |
| 100/110 · 100/120 · 100/180 · 100/220 | 29 · 6 · 18 · 24 | |
| 180/180 · 180/200 · 200/200 · 200/195 · 190/195 · 200/240 | 29 · 24 · 22 · 6 · 11 · 4 | geniş pencereler (251'lik pano gerektirir) |
| 160/180 · 160/200 | 14 · 2 | ekrandaki 1410×530 evin salon penceresi 160/180 |
| 150/220 · 150/120 · 150/150 · 150/140 | 14 · 12 · 9 · 8 | |
| 59/170 · 59/180 · 50/180 | 20 · 14 · 4 | dar boy pencere |
| 80/120 | 11 | merdiven duvarı penceresi (ekrandaki örnek, 1. kat) |
| 105/170 · 105/180 · 120/140 · 120/150 · 120/130 · 60/60 · 30/30 | 10 · 2 · 9 · 7 · 5 · 5 · 18 | 30/30 ve 60/60 havalandırma/vasistas |

Şablonun pencere blokları: `120x120`, `160 200 P`, `ON_PENCERE_SABLON_120180`, `PENCERE_VASİSTAS_60x40`, `PENCERE`, `Konteyner Vasistas`,
`100'LÜK 125'LİK (120x100) PENCERELİ PANO`, `100'LÜK 125'LİK (60x40) VASİSTASLI PANO`, `100 LIK PENCERELİ PANO 122.5 LUK`.
Pencere sipariş paftası: "PENCERE SİPARİŞ", "PENCERE GÖRÜNÜŞLERİ" (×42), "Pencere Detayı" (×21), "PORTATİFEV-150 M² PENCERE LİSTESİ"
(POZ 1: 4 · POZ 2: 1 · POZ 3: 2 · POZ 4: 2 · POZ 5: 2 adet), notu her yerde aynı: **"Verilen ölçüler iç ölçülerdir; dıştan binmeli, içten pervaz
matik; çift açılım; renk iç-dış aynı (beyaz / antrasit gri); pervaz 15 cm."** Özellik tablosunda "Pencereler: Beyaz", "Vasistaslar: Beyaz".

## 5. Karar bekleyenler

- **Soru 4:** 120/200 Fransız pencere: 120x180 mi, döşemeden 120x200 doğrama mı, balkon kapısı mı? (Motor sınırı 180.)
- 120x125 ve 60x125 şablonda yok → kural adıyla yeni blok (yukarıdaki tablo). Şablonun ad kuralı: `<kalınlık>'LÜK <en>'LİK (ENxBOY) PENCERELİ PANO`.
- Pencere **sembolü** (plan): Motor Astra v1.4.3 sembolü; şablonda 120/120 için ayrı blok. Hangisi: K03 ile birlikte.
