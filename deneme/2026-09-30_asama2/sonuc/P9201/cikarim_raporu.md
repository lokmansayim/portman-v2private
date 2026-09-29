# Çıkarım raporu — TEK_KAT_PREFABRIK_PLANLARI.dxf

Dış kutu 835.75 × 1139.5 cm → grid **6.5 × 9.0 pano**.

## Mahaller
| Ad | Tür | Etiket | Etiket m² | Brüt m² (hücre) | Şablon |
|---|---|---|---|---|---|
| YATAK ODASI 1 | yatak_odasi | YATAK ODASI | 12.13 | 12.6 | — |
| YATAK ODASI 2 | yatak_odasi | YATAK ODASI | 11.45 | 11.81 | — |
| YATAK ODASI 3 | yatak_odasi | YATAK ODASI | 9.0 | 9.45 | — |
| HOL | hol | HOL | 1.47 | 6.69 | — |
| SALON | salon | SALON + MUTFAK | 32.72 | 27.96 | — |
| BANYO | banyo | BANYO | 4.51 | 4.73 | — |
| VERANDA | veranda | VERANDA | 16.5 | 18.9 | — |

## Açıklıklar (kaynak konum → Motor pano)
| Tür | Mahal / arası | Duvar | Ölçü | Pano | Menteşe | Kaynak (cm) | Motor pano merkezi | Fark | Şablon |
|---|---|---|---|---|---|---|---|---|---|
| pencere | YATAK ODASI 2 | sol | 120x120 | 1 |  | 133.25–253.25 | 193.25 ([130.5, 256.0]) | 0.0 | — |
| pencere | SALON | sol | 120x120 | 0 |  | 572.5–692.5 | 569.75 ([507.0, 632.5]) | 62.75 | — |
| pencere | SALON | sag | 120x180 | 2 |  | 886.25–1006.25 | 946.25 ([883.5, 1009.0]) | 0.0 | — |
| pencere | YATAK ODASI 1 | sag | 120x180 | 1 |  | 133.25–253.25 | 193.25 ([130.5, 256.0]) | 0.0 | — |
| pencere | YATAK ODASI 3 | sag | 120x180 | 0 |  | 447.0–567.0 | 444.25 ([381.5, 507.0]) | 62.75 | — |
| pencere | BANYO | on | 60x40 | vars. |  | 338.75–398.75 | 449.25 ([386.5, 512.0]) | -80.5 | — |
| ic_kapi | HOL → YATAK ODASI 2 |  | 82 | 2 | sag | 288.5–368.5 | 317.25 ([256.0, 378.5]) | 11.25 | — |
| ic_kapi | HOL → YATAK ODASI 1 |  | 82 | vars. | sol | 288.5–368.5 | 320.25 ([259.0, 381.5]) | 8.25 | — |
| ic_kapi | HOL → YATAK ODASI 3 |  | 82 | vars. | sag | 394.5–474.5 | 444.25 ([381.5, 507.0]) | -9.75 | — |
| ic_kapi | HOL → BANYO |  | 82 | vars. | sag | 336.75–416.75 | 388.0 ([326.75, 449.25]) | -11.25 | — |
| dis_kapi | VERANDA → SALON |  | 90 | 0 | sag | 647.5–747.5 | 697.75 ([637.5, 758.0]) | -0.25 | — |

## Uyuşmazlıklar (çizim ≠ kural) ve notlar
- Duvar Y(2.0) [6.0 cm, 184.5 cm]: çizimde eksen aks+5.00 cm → bu aksa taşındı (uyarlama)
- Duvar X(3.5) [6.0 cm, 326.0 cm]: çizimde eksen aks+3.00 cm → bu aksa taşındı (uyarlama)
- Bir bölgede 2 etiket (HOL, SALON + MUTFAK): duvarsız geçiş → en yakın etikete bölündü (acik_sinir)
- HOL→YATAK ODASI 2 kapısı: çizimde 80.0 cm, İş Emri 82 (standart)
- HOL→YATAK ODASI 1 kapısı: çizimde 80.0 cm, İş Emri 82 (standart)
- HOL→YATAK ODASI 3 kapısı: çizimde 80.0 cm, İş Emri 82 (standart)
- HOL→BANYO kapısı: çizimde 80.0 cm, İş Emri 82 (standart)
- VERANDA→SALON kapısı: çizimde 100.0 cm, İş Emri 90 (standart)
- pencere SALON (sol): kaynak merkez 632.5, Motor pano merkezi 569.75 → fark 62.75 cm (pano 0/5)
- pencere YATAK ODASI 3 (sag): kaynak merkez 507.0, Motor pano merkezi 444.25 → fark 62.75 cm (pano 0/2)
- pencere BANYO: kaynak açıklık (338.75–398.75) hiçbir aday panoyla yarıdan çok örtüşmüyor
- pencere BANYO (on): kaynak merkez 368.75, Motor pano merkezi 449.25 → fark -80.5 cm (pano 0/1)
- ic_kapi HOL → YATAK ODASI 2 (): kaynak merkez 328.5, Motor pano merkezi 317.25 → fark 11.25 cm (pano 2/3)
- ic_kapi HOL → YATAK ODASI 1 (): kaynak merkez 328.5, Motor pano merkezi 320.25 → fark 8.25 cm (pano 0/1)
- ic_kapi HOL → YATAK ODASI 3 (): kaynak merkez 434.5, Motor pano merkezi 444.25 → fark -9.75 cm (pano 0/1)
- ic_kapi HOL → BANYO (): kaynak merkez 376.75, Motor pano merkezi 388.0 → fark -11.25 cm (pano 0/1)
- (not) 70 diyagonal duvar çizgisi yok sayıldı (v0.1 yalnız aksa paralel duvar)
- (not) Plan gövdesi 7 parçadan birleştirildi (pencere/boşluk kesintileri)
- (not) Plan 90° döndürüldü (kısa kenar x'e alındı): kaynak 1139.5×835.75 → 835.75×1139.5
- (not) 6 pencere kasa çentiklerinden çıkarıldı (Pencere katmanı yok/eksik)
