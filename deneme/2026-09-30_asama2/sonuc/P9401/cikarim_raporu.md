# Çıkarım raporu — TEK_KAT_PREFABRIK_PLANLARI.dxf

Dış kutu 1024.0 × 888.5 cm → grid **8.0 × 7.0 pano**.

## Mahaller
| Ad | Tür | Etiket | Etiket m² | Brüt m² (hücre) | Şablon |
|---|---|---|---|---|---|
| YATAK ODASI 1 | yatak_odasi | YATAK ODASI | 11.5 | 11.81 | — |
| YATAK ODASI 2 | yatak_odasi | YATAK ODASI | 11.3 | 11.81 | — |
| YATAK ODASI 3 | yatak_odasi | YATAK ODASI | 8.9 | 9.45 | — |
| BANYO | banyo | BANYO | 4.5 | 4.73 | — |
| YASAM ALANI | salon | YAŞAM ALANI | 41.6 | 42.53 | — |
| VERANDA | veranda | VERANDA | 12.0 | 7.88 | — |

## Açıklıklar (kaynak konum → Motor pano)
| Tür | Mahal / arası | Duvar | Ölçü | Pano | Menteşe | Kaynak (cm) | Motor pano merkezi | Fark | Şablon |
|---|---|---|---|---|---|---|---|---|---|
| pencere | BANYO | sol | 60x40 | 1 |  | 359.0–419.0 | 444.25 ([381.5, 507.0]) | -55.25 | — |
| pencere | YATAK ODASI 1 | sol | 120x120 | 1 |  | 638.5–758.5 | 695.25 ([632.5, 758.0]) | 3.25 | — |
| pencere | YASAM ALANI | sag | 120x120 | 3 |  | 518.5–638.5 | 569.75 ([507.0, 632.5]) | 8.75 | — |
| pencere | YATAK ODASI 3 | on | 120x180 | 1 |  | 133.25–253.25 | 198.25 ([135.5, 261.0]) | -5.0 | — |
| pencere | YASAM ALANI | on | 120x180 | 2 |  | 589.0–709.0 | 700.25 ([637.5, 763.0]) | -51.25 | — |
| pencere | YASAM ALANI | on | 120x180 | 4 |  | 834.0–954.0 | 951.25 ([888.5, 1014.0]) | -57.25 | — |
| pencere | YATAK ODASI 2 | arka | 120x120 | 0 |  | 423.62–543.62 | 449.25 ([386.5, 512.0]) | 34.37 | — |
| ic_kapi | YASAM ALANI → YATAK ODASI 1 |  | 82 | vars. | sag | 233.75–313.75 | 261.0 ([198.25, 323.75]) | 12.75 | — |
| ic_kapi | YASAM ALANI → YATAK ODASI 3 |  | 82 | 1 | sol | 283.5–363.5 | 261.0 ([198.25, 323.75]) | 62.5 | — |
| ic_kapi | YASAM ALANI → YATAK ODASI 2 |  | 82 | 0 | sol | 339.75–419.75 | 386.5 ([323.75, 449.25]) | -6.75 | — |
| ic_kapi | YASAM ALANI → BANYO |  | 82 | 1 | sag | 414.0–494.0 | 442.75 ([381.5, 504.0]) | 11.25 | — |
| dis_kapi | VERANDA → YASAM ALANI |  | 90 | 0 | sol | 399.5–499.5 | 451.75 ([391.5, 512.0]) | -2.25 | — |

## Uyuşmazlıklar (çizim ≠ kural) ve notlar
- Veranda profili bina kutusunun dışına taşıyor (sol 0.0, sağ 0.0, ön 62.2, arka 0.0 cm); Motor v1 yalnız kutu içindeki kısmı çizer (L biçimli taban desteklenmiyor)
- Duvar X(2.5) [6.0 cm, 737.0 cm]: çizimde eksen aks+3.00 cm → bu aksa taşındı (uyarlama)
- Duvar X(5.0) [6.0 cm, 743.0 cm]: çizimde eksen aks+3.00 cm → bu aksa taşındı (uyarlama)
- YASAM ALANI→YATAK ODASI 1 kapısı: çizimde 80.0 cm, İş Emri 82 (standart)
- YASAM ALANI→YATAK ODASI 3 kapısı: çizimde 80.0 cm, İş Emri 82 (standart)
- YASAM ALANI→YATAK ODASI 2 kapısı: çizimde 80.0 cm, İş Emri 82 (standart)
- YASAM ALANI→BANYO kapısı: çizimde 80.0 cm, İş Emri 82 (standart)
- VERANDA→YASAM ALANI kapısı: çizimde 100.0 cm, İş Emri 90 (standart)
- pencere BANYO (sol): kaynak merkez 389.0, Motor pano merkezi 444.25 → fark -55.25 cm (pano 1/2)
- pencere YATAK ODASI 1 (sol): kaynak merkez 698.5, Motor pano merkezi 695.25 → fark 3.25 cm (pano 1/3)
- pencere YASAM ALANI (sag): kaynak merkez 578.5, Motor pano merkezi 569.75 → fark 8.75 cm (pano 3/6)
- pencere YATAK ODASI 3 (on): kaynak merkez 193.25, Motor pano merkezi 198.25 → fark -5.0 cm (pano 1/3)
- pencere YASAM ALANI (on): kaynak merkez 649.0, Motor pano merkezi 700.25 → fark -51.25 cm (pano 2/5)
- pencere YASAM ALANI (on): kaynak merkez 894.0, Motor pano merkezi 951.25 → fark -57.25 cm (pano 4/5)
- pencere YATAK ODASI 2 (arka): kaynak merkez 483.62, Motor pano merkezi 449.25 → fark 34.37 cm (pano 0/2)
- ic_kapi YASAM ALANI → YATAK ODASI 1 (): kaynak merkez 273.75, Motor pano merkezi 261.0 → fark 12.75 cm (pano 0/1)
- ic_kapi ['YASAM ALANI', 'YATAK ODASI 3']: kaynak açıklık (283.5–363.5) hiçbir aday panoyla yarıdan çok örtüşmüyor
- ic_kapi YASAM ALANI → YATAK ODASI 3 (): kaynak merkez 323.5, Motor pano merkezi 261.0 → fark 62.5 cm (pano 1/2)
- ic_kapi YASAM ALANI → YATAK ODASI 2 (): kaynak merkez 379.75, Motor pano merkezi 386.5 → fark -6.75 cm (pano 0/5)
- ic_kapi YASAM ALANI → BANYO (): kaynak merkez 454.0, Motor pano merkezi 442.75 → fark 11.25 cm (pano 1/2)
- (not) 70 diyagonal duvar çizgisi yok sayıldı (v0.1 yalnız aksa paralel duvar)
- (not) 7 pencere kasa çentiklerinden çıkarıldı (Pencere katmanı yok/eksik)
