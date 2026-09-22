# Çıkarıcı v0.1 — 16 katalog planı ilk koşum (22 Eylül 2026)

Amaç (yol haritası 1.1): katalog DXF'ini elle kodlamadan, **aks tanıma** ile İş Emri'ne çevirmek; altın test P6001 (elle kodlanmış şablonla birebir); ardından master DXF'teki 16 planın tamamı.
Araç: `motor/cikarici.py` (LLM yok, yalnız geometri). Her koşum `cikti/cikarici/<kod>/` altına İş Emri JSON, `cikarim_raporu.md/json`, `tani.png` (hücre sahipliği + tespit edilen duvarlar + pencere/kapı) ve Motor çıktısı (DXF/PDF/preview) yazar.

## 1. Altın test — P6001 (elle kodlanmış şablon vs çıkarıcı)
| Ölçüt | Sonuç |
|---|---|
| Dış kutu → grid | 773 × 763 → **6 × 6** (artık 0,0) |
| Mahaller (hücre kümesi) | **5/5 birebir** (VERANDA, YASAM ALANI, YATAK ODASI 1/2, BANYO) |
| Açıklıklar | 9/9 bulundu; **7/9 şablonla aynı**; 2 fark: dış kapı ve banyo kapısı menteşesi (şablon `sag`, çizim `sol`) — çizim incelendi, **çıkarıcı haklı, şablon hatalıydı** |
| Motor | çizdi, doğrulama geçti (PDF/DXF) |

Menteşe kuralı doğrulandı: `mentese = sag` ⇔ a mahalinden b'ye bakarken menteşe sağda (Motor çıktısındaki kanat konumu ile kaynak sembol karşılaştırılarak 4 kapıda teyit edildi).

## 2. 16 plan — özet tablo
Sütunlar: Mod (aks = modüle oturuyor; uyarlama = dış ölçü modülde değil, en yakın grid alındı), Artık (W,H cm), Döndü (kısa kenar x'e alınmak için 90°), Etiketsiz/çok etiketli bölge, katalog dışı pencere, dışa açılan kapı (Motor v1 desteklemiyor), Motor hatası (düşürülen açıklık sayısı).

| Kod | Mod | Kutu (cm) | Grid | Artık (W,H) | Döndü | Mahal | Etiketsiz | Çok etiketli | Pencere | Kapı | Katalog dışı pencere | Dışa kapı | Düşürülen | Uyuşmazlık | Motor çizdi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P6001 | aks | 773×763 | 6×6 | 0, 0 |  | 5 | 0 | 0 | 5 | 4 |  | 0 | 0 | 17 | ✓ |
| P6501 | aks | 647×1015 | 5×8 | −0,5, 1 | 90° | 6 | 0 | 1 | 5 | 4 |  | 0 | 0 | 20 | ✓ |
| P6701 | aks | 584,75×888,5 | 4,5×7 | 0, 0 |  | 5 | 0 | 0 | 6 | 4 |  | 1 | 0 | 15 | ✓ |
| P7001 | uyarlama | 944×740 | 7,5×6 | −17,25, −23 | 90° | 7 | 0 | 1 | 2 | 5 |  | 0 | 0 | 34 | ✓ |
| P7401 | aks | 648×1014 | 5×8 | 0,5, 0 | 90° | 6 | 0 | 1 | 5 | 4 |  | 0 | 0 | 20 | ✓ |
| P7601 | uyarlama | 845×900 | 6,5×7 | 9,25, 11,5 | 90° | 6 | 0 | 0 | 8 | 5 | 90×180 | 0 | 0 | 33 | ✓ |
| P8201 | uyarlama | 961,25×878,75 | 7,5×7 | 0, −9,75 |  | 6 | 0 | 1 | 4 | 4 | 105×170 | 0 | 0 | 26 | ✓ |
| P8501 | uyarlama | 825,25×1010 | 6,5×8 | −10,5, −4 |  | 8 | 0 | 1 | 6 | 5 | 180×180 | 0 | 2 | 30 | ✓ |
| P9201 | aks | 835,75×1139,5 | 6,5×9 | 0, 0 | 90° | 7 | 0 | 1 | 6 | 5 |  | 0 | 0 | 16 | ✓ |
| P9401 | aks | 1024×888,5 | 8×7 | 0, 0 |  | 6 | 0 | 0 | 7 | 5 |  | 0 | 0 | 20 | ✓ |
| P9501 | aks | 898,5×1012,4 | 7×8 | 0, −1,6 |  | 9 | 0 | 3 | 5 | 3 |  | 0 | 4 | 47 | ✓ (iç bölmeler modül dışı) |
| P9901 | uyarlama | 895×1396 | 7×11 | −3,5, 5,5 | 90° | 7 + 4 dış bölge | — | 1 | 2 | 6 | 200×200, 400×200 | 0 | — | 54 | ✗ **taban dikdörtgen değil (artı biçim)** — Motor v1 desteklemiyor |
| P1051 | aks | 835,75×1014 | 6,5×8 | 0, 0 |  | 6 | 0 | 1 | 8 | 0 |  | 1 | 3 | 20 | ✓ (kapılar düştü: iç duvarlar aks ortasında) |
| P1081 | aks | 1024×763 | 8×6 | 0, 0 |  | 6 | 0 | 2 | 6 | 2 | 180×180 | 1 | 2 | 23 | ✓ |
| P1121 | uyarlama | 1136×1134,75 | 9×9 | −13,5, −4,75 | 90° | 7 | 0 | 1 | 4 | 6 |  | 0 | 0 | 29 | ✓ |
| P3701 | uyarlama | 500×750 | 4×6 | −22, −13 | 90° | 5 | 0 | 1 | 1 | 4 |  | 0 | 0 | 22 | ✓ |

**Sayım:** 15/16 Motor'dan geçti (P9901 hariç). Dış ölçüsü modüle tam oturan: **8** (P6001, P6501, P6701, P7401, P9201, P9401, P1051, P1081; 3'ü 90° döndürülerek). Modüle uyarlanan: 7 (artıklar 4–23 cm). İç bölmeleri de modülde olan (kapı/pencere düşmeden, çok etiketli bölge olmadan): P6001, P6701, P9401.

## 3. Bulgular (karar / kural sorusu)
1. **Katalog çizimleri mimari eskiz; 125,5 modül disiplini yok.** Dış ölçüde 8/16 modüler; iç duvarlar birçok planda aks ortasında (P1051: 418/287/314 gibi tam cm ölçüler; P9501, P7001). "Uyarlama" modu duvarı en yakın aksa taşır (±31 cm'e kadar) ve her taşımayı raporlar; ama bu bir **tasarım kararıdır** (oda ölçüleri değişir). Seçenek: (a) 16 planı modüle uyarlayıp Ubeydullah onayıyla yeni "üretim şablonu" yapmak (çıkarıcı önerisi hazır), (b) Motor v2'de serbest aks aralığı (ruhsat ölçüsü için zaten gerekecek).
2. **Pencere konumu kuralı:** çizimlerde pencere oda duvarının ortasında; Motor pano ortasına koyuyor (P6001'de 4 pencerede 31–34 cm fark). Üretimde pencere panosu tek elemansa Motor doğru; değilse kural değişmeli. — Ubeydullah
3. **İç yatay duvar ekseni:** çizimde aks+2 cm (üst yüz modül çizgisinde); kural aks ortalı ±3. Sistematik, tüm planlarda. — Ubeydullah
4. **Katalog dışı doğrama:** 180×180 (P8501, P1081 — sürme kapı olabilir), 200×200 ve 400×200 (P9901), 90×180 (P7601), 105×170 (P8201). Çizim için en yakın katalog ölçüsü konuldu (raporda "UYARLAMA"), İş Emri notunda kaynak ölçü duruyor. Kural tablosuna: hangi doğramalar üretiliyor, iki panolu açıklık var mı?
5. **Dışa açılan kapı** (verandasız giriş: P6701, P1051, P1081) ve **L/T taban** (P9901) Motor v1'de yok → Motor v1.2 iş listesi.
6. **Veranda taşması:** P9401/P7401'de veranda profili bina kutusunun dışına 62 cm taşıyor; v1 kutu içindeki kısmı çiziyor (raporda).
7. **Kapı genişlikleri:** çizimde iç 80 / dış 100; İş Emri 82 / 90 (21.09 kararı). Menteşe yönleri çizimden okunuyor.

## 4. Sıradaki adım
- Ubeydullah ile 30 dk: bulgular 2, 3, 4 (kural tablosuna girecek).
- Lokman: 1. maddede (a) mı (b) mi? (a) seçilirse 8 modüler planın üretim şablonu bu hafta; (b) Motor v2 tasarımı.
- Çıkarıcı v0.2: uyarlama modunda duvarları tek tek değil **oda topolojisini koruyarak** taşımak (kıymık bölge sıfır), pencere/kapı düşürmeden.
