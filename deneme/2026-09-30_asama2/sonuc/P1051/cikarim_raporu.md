# Çıkarım raporu — TEK_KAT_PREFABRIK_PLANLARI.dxf

Dış kutu 835.75 × 1014.0 cm → grid **6.5 × 8.0 pano**.

## Mahaller
| Ad | Tür | Etiket | Etiket m² | Brüt m² (hücre) | Şablon |
|---|---|---|---|---|---|
| YASAM ALANI | salon | Yaşam Alanı | 38.1 | 31.5 | — |
| YATAK ODASI 1 | yatak_odasi | Yatak Odası | 11.1 | 8.27 | — |
| YATAK ODASI 2 | yatak_odasi | Yatak Odası | 11.1 | 9.45 | — |
| YATAK ODASI 3 | yatak_odasi | Yatak Odası | 10.4 | 11.81 | — |
| BANYO | banyo | Banyo | 4.5 | 12.21 | — |
| HOL | hol | Hol | 3.5 | 8.66 | — |

## Açıklıklar (kaynak konum → Motor pano)
| Tür | Mahal / arası | Duvar | Ölçü | Pano | Menteşe | Kaynak (cm) | Motor pano merkezi | Fark | Şablon |
|---|---|---|---|---|---|---|---|---|---|
| pencere | YASAM ALANI | sol | 120x120 | 1 |  | 164.38–284.37 | 193.25 ([130.5, 256.0]) | 31.13 | — |
| pencere | YATAK ODASI 3 | sol | 120x120 | 1 |  | 478.12–598.12 | 569.75 ([507.0, 632.5]) | -31.63 | — |
| pencere | YATAK ODASI 3 | sol | 120x120 | 3 |  | 760.5–880.5 | 820.75 ([758.0, 883.5]) | -0.25 | — |
| pencere | BANYO | sag | 60x40 | 3 |  | 653.62–713.62 | 695.25 ([632.5, 758.0]) | -11.63 | — |
| pencere | BANYO | sag | 120x120 | 4 |  | 760.5–880.5 | 820.75 ([758.0, 883.5]) | -0.25 | — |
| pencere | YASAM ALANI | on | 120x180 | 1 |  | 106.62–226.62 | 198.25 ([135.5, 261.0]) | -31.63 | — |
| pencere | YASAM ALANI | on | 120x180 | 3 |  | 357.62–477.62 | 449.25 ([386.5, 512.0]) | -31.63 | — |
| pencere | YASAM ALANI | on | 120x180 | 5 |  | 608.62–728.62 | 700.25 ([637.5, 763.0]) | -31.63 | — |

## Uyuşmazlıklar (çizim ≠ kural) ve notlar
- Veranda profili bina kutusunun dışına taşıyor (sol 0.0, sağ 0.0, ön 228.6, arka 0.0 cm); Motor v1 yalnız kutu içindeki kısmı çizer (L biçimli taban desteklenmiyor)
- Duvar Y(5.0) [6.0 cm, 188.25 cm]: çizimde eksen aks-28.38 cm → bu aksa taşındı (uyarlama)
- Bir bölgede 6 etiket (Yaşam Alanı, Yatak Odası, Yatak Odası, Banyo, Hol, Yatak Odası): duvarsız geçiş → en yakın etikete bölündü (acik_sinir)
- Kapı (425.37–525.37) bina dışına açılıyor; Motor v1 dışa açılan kapıyı desteklemiyor — atlandı
- Kapı (633.62–713.62) aynı mahalin (YATAK ODASI 3) iki hücresi arasında (duvar akslara oturmadı) — atlandı
- HOL→BANYO kapısı: çizimde 80.0 cm, İş Emri 82 (standart)
- HOL→YATAK ODASI 1 kapısı: çizimde 80.0 cm, İş Emri 82 (standart)
- HOL→YATAK ODASI 2 kapısı: çizimde 80.0 cm, İş Emri 82 (standart)
- pencere YASAM ALANI (sol): kaynak merkez 224.38, Motor pano merkezi 193.25 → fark 31.13 cm (pano 1/2)
- pencere YATAK ODASI 3 (sol): kaynak merkez 538.12, Motor pano merkezi 569.75 → fark -31.63 cm (pano 1/4)
- pencere BANYO (sag): kaynak merkez 683.62, Motor pano merkezi 695.25 → fark -11.63 cm (pano 3/5)
- pencere YASAM ALANI (on): kaynak merkez 166.62, Motor pano merkezi 198.25 → fark -31.63 cm (pano 1/6)
- pencere YASAM ALANI (on): kaynak merkez 417.62, Motor pano merkezi 449.25 → fark -31.63 cm (pano 3/6)
- pencere YASAM ALANI (on): kaynak merkez 668.62, Motor pano merkezi 700.25 → fark -31.63 cm (pano 5/6)
- ic_kapi ['HOL', 'BANYO']: Motor'da uygun pano yok
- ic_kapi ['HOL', 'YATAK ODASI 1']: Motor'da uygun pano yok
- ic_kapi ['HOL', 'YATAK ODASI 2']: Motor'da uygun pano yok
- Açıklık düşürüldü (Motor: HOL–BANYO arasında duvar yok: {'tur': 'ic_kapi', 'olcu': 82, 'arasi': ['HOL', 'BANYO'], 'mentese': 'sol'}): ic_kapi ['HOL', 'BANYO']
- Açıklık düşürüldü (Motor: HOL–YATAK ODASI 1 arasında duvar yok: {'tur': 'ic_kapi', 'olcu': 82, 'arasi': ['HOL', 'YATAK ODASI 1'], 'mentese': 'sag'): ic_kapi ['HOL', 'YATAK ODASI 1']
- Açıklık düşürüldü (Motor: HOL–YATAK ODASI 2 arasında duvar yok: {'tur': 'ic_kapi', 'olcu': 82, 'arasi': ['HOL', 'YATAK ODASI 2'], 'mentese': 'sol'): ic_kapi ['HOL', 'YATAK ODASI 2']
- (not) 70 diyagonal duvar çizgisi yok sayıldı (v0.1 yalnız aksa paralel duvar)
- (not) 8 pencere kasa çentiklerinden çıkarıldı (Pencere katmanı yok/eksik)
