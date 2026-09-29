# Çıkarım raporu — TEK_KAT_PREFABRIK_PLANLARI.dxf

Dış kutu 1136.0 × 1134.75 cm → grid **9.0 × 9.0 pano**.

## Mahaller
| Ad | Tür | Etiket | Etiket m² | Brüt m² (hücre) | Şablon |
|---|---|---|---|---|---|
| YATAK ODASI 1 | yatak_odasi | Yatak Odası | 12.4 | 18.51 | — |
| YATAK ODASI 2 | yatak_odasi | Yatak Odası | 12.2 | 12.6 | — |
| YATAK ODASI 3 | yatak_odasi | Yatak Odası | 11.0 | 11.81 | — |
| YASAM ALANI | salon | Yaşam Alanı | 40.0 | 41.34 | — |
| VERANDA | veranda | Veranda | 31.3 | 28.35 | — |
| HOL | hol | Antre & Hol | 9.5 | 10.24 | — |
| BANYO | banyo | Banyo | 4.5 | 4.73 | — |

## Açıklıklar (kaynak konum → Motor pano)
| Tür | Mahal / arası | Duvar | Ölçü | Pano | Menteşe | Kaynak (cm) | Motor pano merkezi | Fark | Şablon |
|---|---|---|---|---|---|---|---|---|---|
| pencere | YASAM ALANI | sol | 120x120 | 0 |  | 570.25–690.25 | 569.75 ([507.0, 632.5]) | 60.5 | — |
| pencere | YATAK ODASI 2 | on | 120x120 | 0 |  | 75.5–195.5 | 72.75 ([10.0, 135.5]) | 62.75 | — |
| pencere | YATAK ODASI 3 | on | 120x120 | 0 |  | 326.5–446.5 | 323.75 ([261.0, 386.5]) | 62.75 | — |
| pencere | BANYO | on | 60x40 | vars. |  | 598.75–658.75 | 700.25 ([637.5, 763.0]) | -71.5 | — |
| ic_kapi | YATAK ODASI 1 → HOL |  | 82 | 1 | sol | 396.5–496.5 | 443.25 ([384.5, 502.0]) | 3.25 | — |
| ic_kapi | HOL → BANYO |  | 82 | vars. | sag | 579.0–659.0 | 639.0 ([577.75, 700.25]) | -20.0 | — |
| ic_kapi | HOL → YATAK ODASI 3 |  | 82 | 0 | sag | 285.5–365.5 | 317.25 ([256.0, 378.5]) | 8.25 | — |
| ic_kapi | HOL → YATAK ODASI 1 |  | 82 | 0 | sol | 285.5–365.5 | 317.25 ([256.0, 378.5]) | 8.25 | — |
| ic_kapi | HOL → YATAK ODASI 2 |  | 82 | vars. | sag | 414.0–494.0 | 442.75 ([381.5, 504.0]) | 11.25 | — |
| ic_kapi | HOL → YASAM ALANI |  | 82 | 1 | sol | 429.75–509.75 | 449.25 ([386.5, 512.0]) | 20.5 | — |

## Uyuşmazlıklar (çizim ≠ kural) ve notlar
- MODÜLE UYARLAMA: dış ölçü 1136.0×1134.75 modüle oturmuyor (artık W -13.5, H -4.75 cm); en yakın grid 9.0×9.0 (1149.5×1139.5) alındı, duvarlar en yakın aksa atandı — onay gerekir
- Veranda profili bina kutusunun dışına taşıyor (sol 0.0, sağ 0.0, ön 0.0, arka 14.7 cm); Motor v1 yalnız kutu içindeki kısmı çizer (L biçimli taban desteklenmiyor)
- Duvar Y(2.0) [6.0 cm, 184.5 cm]: çizimde eksen aks+5.00 cm → bu aksa taşındı (uyarlama)
- Duvar Y(3.0) [6.0 cm, 604.0 cm]: çizimde eksen aks-3.00 cm → bu aksa taşındı (uyarlama)
- Duvar Y(3.0) [6.0 cm, 231.0 cm]: çizimde eksen aks-2.00 cm → bu aksa taşındı (uyarlama)
- Duvar X(3.0) [10.0 cm, 376.5 cm]: çizimde eksen aks-9.50 cm → bu aksa taşındı (uyarlama)
- Duvar X(4.5) [6.0 cm, 545.0 cm]: çizimde eksen aks-8.75 cm → bu aksa taşındı (uyarlama)
- Duvar X(6.0) [6.0 cm, 545.0 cm]: çizimde eksen aks-8.75 cm → bu aksa taşındı (uyarlama)
- Duvar X(7.0) [10.0 cm, 760.5 cm]: çizimde eksen aks-13.75 cm → bu aksa taşındı (uyarlama)
- Duvar X(9.0) [10.0 cm, 210.0 cm]: çizimde eksen aks-8.50 cm → bu aksa taşındı (uyarlama)
- Bir bölgede 3 etiket (Yatak Odası, Yaşam Alanı, Veranda): duvarsız geçiş → en yakın etikete bölündü (acik_sinir)
- Pencere (621.5–741.5) iki açık taraf arasında; atlandı
- YATAK ODASI 1→HOL kapısı: çizimde 100.0 cm, İş Emri 82 (standart)
- HOL→BANYO kapısı: çizimde 80.0 cm, İş Emri 82 (standart)
- HOL→YATAK ODASI 3 kapısı: çizimde 80.0 cm, İş Emri 82 (standart)
- HOL→YATAK ODASI 1 kapısı: çizimde 80.0 cm, İş Emri 82 (standart)
- HOL→YATAK ODASI 2 kapısı: çizimde 80.0 cm, İş Emri 82 (standart)
- HOL→YASAM ALANI kapısı: çizimde 80.0 cm, İş Emri 82 (standart)
- pencere YASAM ALANI (sol): kaynak merkez 630.25, Motor pano merkezi 569.75 → fark 60.5 cm (pano 0/5)
- pencere YATAK ODASI 2 (on): kaynak merkez 135.5, Motor pano merkezi 72.75 → fark 62.75 cm (pano 0/2)
- pencere YATAK ODASI 3 (on): kaynak merkez 386.5, Motor pano merkezi 323.75 → fark 62.75 cm (pano 0/2)
- pencere BANYO: kaynak açıklık (598.75–658.75) hiçbir aday panoyla yarıdan çok örtüşmüyor
- pencere BANYO (on): kaynak merkez 628.75, Motor pano merkezi 700.25 → fark -71.5 cm (pano 0/1)
- ic_kapi YATAK ODASI 1 → HOL (): kaynak merkez 446.5, Motor pano merkezi 443.25 → fark 3.25 cm (pano 1/3)
- ic_kapi HOL → BANYO (): kaynak merkez 619.0, Motor pano merkezi 639.0 → fark -20.0 cm (pano 0/1)
- ic_kapi HOL → YATAK ODASI 3 (): kaynak merkez 325.5, Motor pano merkezi 317.25 → fark 8.25 cm (pano 0/3)
- ic_kapi HOL → YATAK ODASI 1 (): kaynak merkez 325.5, Motor pano merkezi 317.25 → fark 8.25 cm (pano 0/3)
- ic_kapi HOL → YATAK ODASI 2 (): kaynak merkez 454.0, Motor pano merkezi 442.75 → fark 11.25 cm (pano 0/1)
- ic_kapi HOL → YASAM ALANI (): kaynak merkez 469.75, Motor pano merkezi 449.25 → fark 20.5 cm (pano 1/4)
- (not) 70 diyagonal duvar çizgisi yok sayıldı (v0.1 yalnız aksa paralel duvar)
- (not) Plan gövdesi 5 parçadan birleştirildi (pencere/boşluk kesintileri)
- (not) Plan 90° döndürüldü (kısa kenar x'e alındı): kaynak 1134.75×1136.0 → 1136.0×1134.75
- (not) 5 pencere kasa çentiklerinden çıkarıldı (Pencere katmanı yok/eksik)
