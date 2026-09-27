# Çıkarım raporu — normalize.dxf

Dış kutu 968.93 × 800.06 cm → grid **7.5 × 6.5 pano**.

## Mahaller
| Ad | Tür | Etiket | Etiket m² | Brüt m² (hücre) | Şablon |
|---|---|---|---|---|---|
| YATAK ODASI 1 | yatak_odasi | YATAK ODASI | 10.0 | 9.84 | — |
| YATAK ODASI 2 | yatak_odasi | YATAK ODASI | 9.6 | 10.63 | — |
| YATAK ODASI 3 | yatak_odasi | YATAK ODASI | 8.26 | 10.24 | — |
| HOL | hol | HOL | 7.4 | 9.45 | — |
| BANYO | banyo | BANYO | 3.6 | 4.33 | — |
| WC | banyo | WC | 4.0 | 2.36 | — |
| SALON | salon | SALON | 15.35 | 15.75 | — |
| MUTFAK | mutfak | MUTFAK | 8.1 | 7.88 | — |
| VERANDA | veranda | VERANDA | 8.3 | 6.3 | — |

## Açıklıklar (kaynak konum → Motor pano)
| Tür | Mahal / arası | Duvar | Ölçü | Pano | Menteşe | Kaynak (cm) | Motor pano merkezi | Fark | Şablon |
|---|---|---|---|---|---|---|---|---|---|
| pencere | SALON | arka | 120x120 | 1 |  | 464.73–584.73 | 574.75 ([512.0, 637.5]) | -50.02 | — |
| pencere | YATAK ODASI 3 | on | 120x120 | vars. |  | 527.43–647.53 | 574.75 ([512.0, 637.5]) | 12.73 | — |
| pencere | YATAK ODASI 2 | on | 120x120 | 1 |  | 87.83–207.63 | 198.25 ([135.5, 261.0]) | -50.52 | — |
| pencere | YATAK ODASI 1 | arka | 120x120 | 1 |  | 111.63–231.63 | 198.25 ([135.5, 261.0]) | -26.62 | — |
| pencere | SALON | sag | 120x180 | 0 |  | 574.7–694.8 | 632.5 ([569.75, 695.25]) | 2.25 | — |
| pencere | MUTFAK | sag | 120x180 | 1 |  | 92.5–212.6 | 193.25 ([130.5, 256.0]) | -40.7 | — |
| pencere | BANYO | sol | 60x40 | vars. |  | 411.5–471.4 | 444.25 ([381.5, 507.0]) | -2.8 | — |
| ic_kapi | HOL → SALON |  | 82 | 0 | sol | 349.33–429.23 | 386.5 ([323.75, 449.25]) | 2.78 | — |
| ic_kapi | YATAK ODASI 3 → MUTFAK |  | 82 | 2 | sag | 726.03–805.93 | 763.0 ([700.25, 825.75]) | 2.98 | — |
| ic_kapi | HOL → YATAK ODASI 3 |  | 82 | 0 | sol | 250.4–330.3 | 256.0 ([193.25, 318.75]) | 34.35 | — |
| ic_kapi | HOL → WC |  | 82 | vars. | sol | 371.83–451.93 | 386.5 ([326.75, 446.25]) | 25.38 | — |
| ic_kapi | HOL → YATAK ODASI 2 |  | 82 | vars. | sag | 250.9–330.8 | 256.0 ([193.25, 318.75]) | 34.85 | — |

## Uyuşmazlıklar (çizim ≠ kural) ve notlar
- MODÜLE UYARLAMA: dış ölçü 968.93×800.06 modüle oturmuyor (artık W 7.68, H -25.69 cm); en yakın grid 7.5×6.5 (961.25×825.75) alındı, duvarlar en yakın aksa atandı — onay gerekir
- Veranda profili bina kutusunun dışına taşıyor (sol 0.0, sağ 60.0, ön 0.0, arka 0.0 cm); Motor v1 yalnız kutu içindeki kısmı çizer (L biçimli taban desteklenmiyor)
- Kapı sembolü belirsiz (iki kasa adayı eşit puanlı): [(210.93, 383.4), (211.03, 463.3), (130.93, 463.3)]
- Kapı sembolü belirsiz (iki kasa adayı eşit puanlı): [(460.23, 250.4), (460.33, 330.3), (540.23, 330.3)]
- Kapı sembolü belirsiz (iki kasa adayı eşit puanlı): [(210.93, 383.4), (211.03, 463.3), (130.93, 463.3)]
- Kapı sembolü belirsiz (iki kasa adayı eşit puanlı): [(460.23, 250.4), (460.33, 330.3), (540.23, 330.3)]
- Duvar Y(1.5) [6.1 cm, 238.94 cm]: çizimde eksen aks+29.05 cm → bu aksa taşındı (uyarlama)
- Duvar Y(2.5) [10.04 cm, 250.94 cm]: çizimde eksen aks+26.96 cm → bu aksa taşındı (uyarlama)
- Duvar Y(2.5) [6.1 cm, 396.4 cm]: çizimde eksen aks-30.71 cm → bu aksa taşındı (uyarlama)
- Duvar Y(3.0) [5.91 cm, 734.13 cm]: çizimde eksen aks-30.77 cm → bu aksa taşındı (uyarlama)
- Duvar Y(3.0) [5.91 cm, 241.89 cm]: çizimde eksen aks-30.77 cm → bu aksa taşındı (uyarlama)
- Duvar Y(4.0) [5.91 cm, 1635.36 cm]: çizimde eksen aks-30.71 cm → bu aksa taşındı (uyarlama)
- Duvar Y(6.5) [10.04 cm, 1661.14 cm]: çizimde eksen aks-25.71 cm → bu aksa taşındı (uyarlama)
- Duvar X(1.5) [5.9 cm, 361.74 cm]: çizimde eksen aks+12.74 cm → bu aksa taşındı (uyarlama)
- Duvar X(2.5) [6.1 cm, 669.36 cm]: çizimde eksen aks+12.71 cm → bu aksa taşındı (uyarlama)
- Duvar X(2.5) [6.1 cm, 621.54 cm]: çizimde eksen aks+12.71 cm → bu aksa taşındı (uyarlama)
- Duvar X(3.5) [5.9 cm, 669.36 cm]: çizimde eksen aks+12.68 cm → bu aksa taşındı (uyarlama)
- Duvar X(5.5) [6.1 cm, 675.46 cm]: çizimde eksen aks+12.72 cm → bu aksa taşındı (uyarlama)
- Duvar X(6.5) [10.04 cm, 879.76 cm]: çizimde eksen aks+12.79 cm → bu aksa taşındı (uyarlama)
- Duvar X(7.5) [9.84 cm, 681.38 cm]: çizimde eksen aks+12.76 cm → bu aksa taşındı (uyarlama)
- Bir bölgede 2 etiket (HOL, BANYO): duvarsız geçiş → en yakın etikete bölündü (acik_sinir)
- Kapı sembolü belirsiz (iki kasa adayı eşit puanlı): [(210.93, 383.4), (211.03, 463.3), (130.93, 463.3)]
- Kapı (383.4–463.3) aynı mahalin (BANYO) iki hücresi arasında (duvar akslara oturmadı) — atlandı
- HOL→YATAK ODASI 1 kapısı: çizimde 80.1 cm, İş Emri 82 (standart)
- HOL→SALON kapısı: çizimde 79.9 cm, İş Emri 82 (standart)
- YATAK ODASI 3→MUTFAK kapısı: çizimde 79.9 cm, İş Emri 82 (standart)
- VERANDA→HOL kapısı: çizimde 100.1 cm, İş Emri 90 (standart)
- Kapı sembolü belirsiz (iki kasa adayı eşit puanlı): [(460.23, 250.4), (460.33, 330.3), (540.23, 330.3)]
- HOL→YATAK ODASI 3 kapısı: çizimde 79.9 cm, İş Emri 82 (standart)
- HOL→WC kapısı: çizimde 80.1 cm, İş Emri 82 (standart)
- HOL→YATAK ODASI 2 kapısı: çizimde 79.9 cm, İş Emri 82 (standart)
- pencere SALON (arka): kaynak merkez 524.73, Motor pano merkezi 574.75 → fark -50.02 cm (pano 1/3)
- pencere YATAK ODASI 3 (on): kaynak merkez 587.48, Motor pano merkezi 574.75 → fark 12.73 cm (pano 0/1)
- pencere YATAK ODASI 2 (on): kaynak merkez 147.73, Motor pano merkezi 198.25 → fark -50.52 cm (pano 1/2)
- pencere YATAK ODASI 1 (arka): kaynak merkez 171.63, Motor pano merkezi 198.25 → fark -26.62 cm (pano 1/2)
- pencere MUTFAK (sag): kaynak merkez 152.55, Motor pano merkezi 193.25 → fark -40.7 cm (pano 1/2)
- pencere WC: Motor'da uygun pano yok
- ic_kapi ['HOL', 'YATAK ODASI 1']: Motor'da uygun pano yok
- dis_kapi ['VERANDA', 'HOL']: Motor'da uygun pano yok
- ic_kapi HOL → YATAK ODASI 3 (): kaynak merkez 290.35, Motor pano merkezi 256.0 → fark 34.35 cm (pano 0/4)
- ic_kapi HOL → WC (): kaynak merkez 411.88, Motor pano merkezi 386.5 → fark 25.38 cm (pano 0/1)
- ic_kapi HOL → YATAK ODASI 2 (): kaynak merkez 290.85, Motor pano merkezi 256.0 → fark 34.85 cm (pano 0/1)
- Açıklık düşürüldü (Motor: Açıklık için uygun pano yok: {'tur': 'pencere', 'olcu': '60x40', 'mahal': 'WC', 'duvar': 'on'}): pencere WC
- Açıklık düşürüldü (Motor: Açıklık için uygun pano yok: {'tur': 'ic_kapi', 'olcu': 82, 'arasi': ['HOL', 'YATAK ODASI 1'], 'mentese': 'sag'}): ic_kapi ['HOL', 'YATAK ODASI 1']
- Açıklık düşürüldü (Motor: Açıklık için uygun pano yok: {'tur': 'dis_kapi', 'olcu': 90, 'arasi': ['VERANDA', 'HOL'], 'mentese': 'sol'}): dis_kapi ['VERANDA', 'HOL']
- (not) Plan gövdesi 7 parçadan birleştirildi (pencere/boşluk kesintileri)
- (not) Plan 90° döndürüldü (kısa kenar x'e alındı): kaynak 800.06×968.93 → 968.93×800.06
