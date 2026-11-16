# Havuz denetimi · ev ev tablo (16 Kasım 2026)

Komut: `python -m araclar.havuz_denetimi --is 4 --kart-klasoru <Proje_Karti> --md <bu dosya>` (`main` 4a654e9f; HD-11 16 Kasım ~08:40). Özet ve açıklama: `docs/raporlar/2026-11-16_havuz_denetimi.md`.

İşaret: ✓ temiz · ✗ hata · ! uyarı · ≠ gerçek projeyle fark · – denetlenmedi (kart yok ya da o Motor'da yok).

- HD-01: Motor kurar, çizim doğrulaması geçer (hata)
- HD-02: Motor uyarısı yok (uyari)
- HD-03: Yükleme listesi yazılır (hata)
- HD-04: Listede adetsiz ya da "Kural yok" satırı yok (hata)
- HD-05: 3D model (IFC) kurulur (hata)
- HD-06: 3D modelde makas yeri uyarısı yok (uyari)
- HD-08: 3D'deki makas sayısı listedekiyle aynı (hata)
- HD-09: Listedeki her makaslı çatı parçası 3D'de de makaslı (uyari)
- HD-10: 3D'deki ana çatı İş Emri'nin çatı biçiminde (hata)
- HD-07: Makas sayısı gerçek projenin kartıyla (bilgi)
- HD-11: Çatı kaplaması gerçek projeninkiyle (bilgi)

| Ev | m² | Oda | Çatı | HD-01 | HD-02 | HD-03 | HD-04 | HD-05 | HD-06 | HD-08 | HD-09 | HD-10 | HD-07 | HD-11 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PA-01 | 60.0 | 2+1 | besik + girintili gövde | ✓ | ! | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| PA-02 | 64.0 | 2+1 | besik + VERANDA: kirma | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ! | ✓ | ≠ | – |
| PA-03 | 70.0 | 2+1 | besik + VERANDA: tek_yon | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ≠ | – |
| PA-04 | 78.0 | 2+1 | besik_cumba + cumba + girintili gövde | ✓ | ✓ | ✓ | ✓ | ✓ | ! | ✓ | ✓ | ✓ | – | – |
| PA-05 | 82.0 | 2+1 | besik_cumba + cumba (çıkıntı 62.75) + girintili gövde | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| PA-06 | 87.0 | 2+1 | besik | ✓ | ! | ✓ | ✓ | ✓ | ! | ✓ | ✓ | ✓ | – | – |
| PA-07 | 90.0 | 3+1 | besik + taşan veranda ÖN VERANDA: besik + taşan veranda ARKA VERANDA: besik | ✓ | ! 2 | ✓ | ✓ | ✓ | ! | ✓ | ! 2 | ✓ | – | – |
| PA-08 | 140.0 | 3+1 | kirma | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | – |
| PA-06-K | 87.0 | 2+1 | kirma | ✓ | ! | ✗ | ✓ | ✓ | ! | ✓ | ✓ | ✗ | – | – |
| PA-06-C | 87.0 | 2+1 | besik_cumba + cumba | ✓ | ! 2 | ✓ | ✓ | ✓ | ! | ✓ | ✓ | ✓ | – | – |
| PA-09 | 64.0 | 2+1 | besik + VERANDA: kirma + kubbe × 1 | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ≠ | – |
| PA-10 | 95.0 | 3+1 | besik | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| PA-11 | 91.0 | 3+1 | besik_cumba + cumba | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| PA-12 | 85.0 | 3+1 | besik | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | – |
| PA-13 | 143.0 | 4+1 | besik + girintili gövde | ✓ | ! 4 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ≠ | – |
| PA-14 | 60.0 | 2+1 | besik_cumba + cumba | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| PA-15 | 70.0 | 2+1 | besik_cumba + cumba | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| PA-16 | 80.0 | 2+1 | besik + kubbe × 1 | ✓ | ! 2 | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ≠ | – |
| PA-17 | 91.0 | 3+1 | besik_cumba + cumba (çıkıntı 220) + girintili gövde | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| PA-18 | 60.0 | 2+1 | besik | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| PA-19 | 84.0 | 2+1 | besik | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| PA-20 | 64.0 | 2+1 | besik + VERANDA: kirma + kubbe × 1 | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ≠ | – |
| PA-21 | 80.0 | 3+1 | besik + girintili gövde | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ≠ | – |
| PA-22 | 102.0 | 2+1 | besik + taşan veranda ÖN TERAS: teras_paneli + taşan veranda ARKA TERAS: teras_paneli | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ≠ | – |
| PA-23 | 49.0 | 2+1 | besik | ✓ | ✓ | ✓ | ✓ | ✓ | ! | ✓ | ✓ | ✓ | ✓ | – |
| PA-24 | 77.0 | 2+1 | kirma | ✓ | ! | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | – |
| PA-25 | 61.0 | 2+1 | besik | ✓ | ! | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | – |
| PA-26 | 71.0 | 2+1 | besik + VERANDA: tek_yon | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| PA-27 | 45.0 | 1+1 | besik_cumba + cumba (çıkıntı 150) + cumba (veranda SUNDURMA) + taşan veranda SUNDURMA: cumba + girintili gövde | ✓ | ! 4 | ✗ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| PA-28 | 46.0 | 1+1 | besik_cumba + cumba (çıkıntı 193.25) + cumba (veranda SUNDURMA) + taşan veranda SUNDURMA: cumba + girintili gövde | ✓ | ! 2 | ✗ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| PA-29 | 40.0 | 1+1 | besik_cumba + cumba (çıkıntı 130.5) + cumba (veranda SUNDURMA) + taşan veranda SUNDURMA: cumba + girintili gövde | ✓ | ! 2 | ✗ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| PA-30 | 83.0 | 3+1 | besik | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ≠ | – |
| PA-31 | 59.0 | 2+1 | besik_cumba + cumba | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| PA-32 | 69.0 | 2+1 | besik_cumba + cumba | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| PA-33 | 142.0 | 3+1 | kirma | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | – |
| PA-34 | 78.0 | 2+1 | kirma | ✓ | ! | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | – |
| PA-35 | 69.0 | 2+1 | besik + VERANDA: tek_yon | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ≠ | – |
| PA-36 | 62.0 | 2+1 | besik | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| PA-37 | 91.0 | 3+1 | besik_cumba + cumba | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| PA-38 | 95.0 | 3+1 | besik | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | – |
| Ç8801 | 88.0 | 2+1 | besik_cumba | ✓ | ✓ | ✓ | ✓ | ✓ | – | – | – | – | – | ✓ |
| Ç8801-K | 88.0 | 2+1 | besik_cumba | ✓ | ✓ | ✓ | ✓ | ✓ | – | – | – | – | – | ✓ |
| Ç8801-L | 88.0 | 2+1 | besik_cumba | ✓ | ✓ | ✓ | ✓ | ✓ | – | – | – | – | – | ✓ |
| Ç8201 | 82.0 | 2+1 | kirma | ✓ | ✓ | ✓ | ✓ | ✓ | – | – | – | – | – | ✓ |
| KT-01 | 99.0 | 2+1 | besik_cumba | ✓ | ! | ✓ | ✓ | ✓ | – | – | – | – | – | ✓ |
| KT-02 | 92.0 | 2+1 | kirma | ✓ | ✓ | ✓ | ✓ | ✓ | – | – | – | – | – | ✓ |
| KT-03 | 94.0 | 2+1 | kirma | ✓ | ! | ✓ | ✓ | ✓ | – | – | – | – | – | ✓ |
| KT-05 | 90.0 | 2+1 | besik_cumba | ✓ | ✓ | ✓ | ✓ | ✓ | – | – | – | – | – | ✓ |
| KT-06 | 90.0 | 2+1 | besik | ✓ | ✓ | ✓ | ✓ | ✓ | – | – | – | – | – | ✓ |
| KT-07 | 90.0 | 2+1 | kirma | ✓ | ! 2 | ✓ | ✓ | ✓ | – | – | – | – | – | ≠ |
| KT-08 | 90.0 | 3+1 | besik_cumba | ✓ | ! 2 | ✓ | ✓ | ✓ | – | – | – | – | – | ✓ |
| KT-09 | 81.0 | 2+1 | besik_cumba | ✓ | ! 3 | ✓ | ✓ | ✓ | – | – | – | – | – | ✓ |
| KT-10 | 82.0 | 2+1 | besik | ✓ | ✓ | ✓ | ✓ | ✓ | – | – | – | – | – | ✓ |
| KT-11 | 49.0 | 1+1 | besik | ✓ | ✓ | ✓ | ✓ | ✓ | – | – | – | – | – | ≠ |
| KT-12 | 130.0 | 3+1 | besik | ✓ | ✓ | ✓ | ✓ | ✓ | – | – | – | – | – | ≠ |
| KT-13 | 167.0 | 3+1 | besik_cumba | ✓ | ! 2 | ✓ | ✓ | ✓ | – | – | – | – | – | ≠ |
| KT04 |  | 4+1 | besik_cumba | ✓ | ✓ | ✓ | ✓ | ✓ | – | – | – | – | – | ✓ |

### Bulgular

- **PA-01** · HD-02 (uyari): Köşe paftadan (yapi.kose_kaynagi: pafta): makas x'i geçiyor ama ön ve arka duvar köşeden geçiyor; İE-17 köşe kuralının istisnası (AP-15)
- **PA-02** · HD-09 (uyari): veranda çatısı: listede 5 makas, 3D modelde bu parçanın makası yok
- **PA-02** · HD-07 (bilgi): makas: liste 12, gerçek proje 13 (kart çatısı: Beşik + Kubbe)
- **PA-03** · HD-04 (hata): Çatı paneli (hafif çelik) · VERANDA çatısı · —: Kural yok
- **PA-03** · HD-07 (bilgi): makas: liste 10, gerçek proje 11 (kart çatısı: Beşik + Cumba)
- **PA-04** · HD-06 (uyari): ['makas yeri (ana çatı): saçak duvarının pano ekleri düzensiz (9 makas, listede 8; aralıklar 125.5, 125.5, 62.75, 125.5, 62.75, 125.5, 125.5, 125.5); eşit aralıklı 8 makas']
- **PA-05** · HD-05 (hata): 3D kurulamadı: PrefabrikCatiHatasi: girintili gövdede yalnız beşik çatı çizilir (ana çatı ve paralel cumbalar); 'besik_cumba' yok
- **PA-06** · HD-02 (uyari): Pencere MUTFAK 160x180: panodan geniş pencere oda ortasına alınmadı; ızgara panosunda kaldı
- **PA-06** · HD-06 (uyari): ['makas yeri: saçak duvarının pano ekleri düzensiz (11 makas, listede 10; aralıklar 74, 125.5, 125.5, 125.5, 125.5, 62.75, 125.5, 62.75, 125.5, 125.5); eşit aralıklı 10 makas']
- **PA-07** · HD-02 (uyari): Dış ölçü 898 × 888 → 898,5 × 888,5 cm: son pano (x: 125, y: 125 cm) 122 ve üzeri olduğu için tam panoya (125,5) tamamlandı (D-30)
- **PA-07** · HD-02 (uyari): Aks noktası (6, 4): dört kollu birleşim; duvar 1 o noktada bölündü (1, 16), uçları geçen duvarın (11) yüzünde; birleşim profili kural kitabında yok
- **PA-07** · HD-06 (uyari): ['makas yeri: iki saçak duvarının pano ekleri farklı; ortak ekler alındı', 'makas yeri: saçak duvarının pano ekleri düzensiz (7 makas, listede 8; aralıklar 125.5, 188.25, 188.25, 125.5, 125.5, 125.5); eşit aralıklı 8 makas']
- **PA-07** · HD-09 (uyari): arka veranda çatısı: listede 2 makas, 3D modelde bu parçanın makası yok
- **PA-07** · HD-09 (uyari): ön veranda çatısı: listede 3 makas, 3D modelde bu parçanın makası yok
- **PA-08** · HD-10 (hata): İş Emri'nde kırma çatı; 3D modelin çatısı GABLE_ROOF (beşik çiziliyor)
- **PA-08** · HD-08 (hata): ana çatı: 3D modelde 16 makas, yükleme listesinde 29 (Makas (ana, mahyaya dik) 11; Makas (kısa, sol uç) 7; Makas (kısa, sağ uç) 7; Makas (çapraz, kırma, sol uç) 2; Makas (çapraz, kırma, sağ uç) 2)
- **PA-06-K** · HD-02 (uyari): Pencere MUTFAK 160x180: panodan geniş pencere oda ortasına alınmadı; ızgara panosunda kaldı
- **PA-06-K** · HD-03 (hata): liste yazılmaz: iki uçlu kırma: mahya y boyunca; makas planı yalnız mahyası x boyunca olan paftayla kıyaslandı (AP-01), liste yazılmaz
- **PA-06-K** · HD-10 (hata): İş Emri'nde kırma çatı; 3D modelin çatısı GABLE_ROOF (beşik çiziliyor)
- **PA-06-K** · HD-06 (uyari): ['makas yeri: saçak duvarının pano ekleri düzensiz (11 makas, listede 10; aralıklar 74, 125.5, 125.5, 125.5, 125.5, 62.75, 125.5, 62.75, 125.5, 125.5); eşit aralıklı 10 makas']
- **PA-06-C** · HD-02 (uyari): Makas y'yi geçiyor ama kisa_kenar x: montaj paftalarında köşe makasın oturduğu duvarlardadır; pano ızgarası iki yönde 5 cm kayık olabilir, kisa_kenar: y doğrulanmalı
- **PA-06-C** · HD-02 (uyari): Pencere MUTFAK 160x180: panodan geniş pencere oda ortasına alınmadı; ızgara panosunda kaldı
- **PA-06-C** · HD-06 (uyari): ['makas yeri (ana çatı): saçak duvarının pano ekleri düzensiz (8 makas, listede 8; aralıklar 130.5, 125.5, 62.75, 125.5, 125.5, 125.5, 94.75); eşit aralıklı 8 makas']
- **PA-09** · HD-05 (hata): 3D kurulamadı: KeyError: 'kubbe'
- **PA-09** · HD-07 (bilgi): makas: liste 15, gerçek proje 16 (kart çatısı: Beşik + Kubbe)
- **PA-12** · HD-08 (hata): ana çatı: 3D modelde 13 makas, yükleme listesinde 11 (Makas (baş) 2; Makas (orta) 9)
- **PA-13** · HD-02 (uyari): Dış ölçü 888,5 × 1638,25 → 888,5 × 1641,5 cm: son pano (y: 122,25 cm) 122 ve üzeri olduğu için tam panoya (125,5) tamamlandı (D-30)
- **PA-13** · HD-02 (uyari): Aks noktası (9, 2): dört kollu birleşim; duvar 1 o noktada bölündü (1, 14), uçları geçen duvarın (12) yüzünde; birleşim profili kural kitabında yok
- **PA-13** · HD-02 (uyari): Aks noktası (7, 13): dört kollu birleşim; duvar 4 o noktada bölündü (4, 15), uçları geçen duvarın (10) yüzünde; birleşim profili kural kitabında yok
- **PA-13** · HD-02 (uyari): Aks noktası (9, 13): dört kollu birleşim; duvar 15 o noktada bölündü (15, 16), uçları geçen duvarın (12) yüzünde; birleşim profili kural kitabında yok
- **PA-13** · HD-07 (bilgi): makas: liste 17, gerçek proje 19 (kart çatısı: Beşik + Çift Cumba)
- **PA-16** · HD-02 (uyari): Köşe paftadan (yapi.kose_kaynagi: pafta): makas x'i geçiyor ama ön ve arka duvar köşeden geçiyor; İE-17 köşe kuralının istisnası (AP-15)
- **PA-16** · HD-02 (uyari): Aks noktası (8, 4): dört kollu birleşim; duvar 1 o noktada bölündü (1, 12), uçları geçen duvarın (9) yüzünde; birleşim profili kural kitabında yok
- **PA-16** · HD-05 (hata): 3D kurulamadı: KeyError: 'kubbe'
- **PA-16** · HD-07 (bilgi): makas: liste 11, gerçek proje 9 (kart çatısı: Beşik + Kubbe (cumba))
- **PA-17** · HD-05 (hata): 3D kurulamadı: PrefabrikCatiHatasi: girintili gövdede yalnız beşik çatı çizilir (ana çatı ve paralel cumbalar); 'besik_cumba' yok
- **PA-20** · HD-05 (hata): 3D kurulamadı: KeyError: 'kubbe'
- **PA-20** · HD-07 (bilgi): makas: liste 16, gerçek proje 14 (kart çatısı: Beşik + Kubbe (cumba))
- **PA-21** · HD-07 (bilgi): makas: liste 10, gerçek proje 11 (kart çatısı: Beşik + Cumba)
- **PA-22** · HD-08 (hata): ana çatı: 3D modelde 5 makas, yükleme listesinde 7 (Makas (baş) 2; Makas (orta) 5)
- **PA-22** · HD-07 (bilgi): makas: liste 7, gerçek proje 14 (kart çatısı: Beşik)
- **PA-23** · HD-06 (uyari): ['makas yeri: saçak duvarının pano ekleri düzensiz (8 makas, listede 7; aralıklar 62.5, 62.75, 125.5, 62.75, 125.5, 125.5, 125.5); eşit aralıklı 7 makas']
- **PA-24** · HD-02 (uyari): Makas y'yi geçiyor ama kisa_kenar x: montaj paftalarında köşe makasın oturduğu duvarlardadır; pano ızgarası iki yönde 5 cm kayık olabilir, kisa_kenar: y doğrulanmalı
- **PA-24** · HD-10 (hata): İş Emri'nde kırma çatı; 3D modelin çatısı GABLE_ROOF (beşik çiziliyor)
- **PA-24** · HD-08 (hata): ana çatı: 3D modelde 6 makas, yükleme listesinde 25 (Makas (ana, mahyaya paralel) 7; Makas (kısa) 14; Makas (çapraz, kırma) 2; Makas (köşe kısa) 2)
- **PA-25** · HD-02 (uyari): Duvar 7: 10.5 cm'lik çok kısa pano (özel pano kuralı doğrulanmalı)
- **PA-25** · HD-08 (hata): ana çatı: 3D modelde 8 makas, yükleme listesinde 7 (Makas (baş) 2; Makas (orta) 5)
- **PA-26** · HD-04 (hata): Çatı paneli (hafif çelik) · VERANDA çatısı · —: Kural yok
- **PA-27** · HD-02 (uyari): Pencere SALON & MUTFAK 150x190: panodan geniş pencere oda ortasına alınmadı; ızgara panosunda kaldı
- **PA-27** · HD-02 (uyari): Pencere YATAK ODASI 150x190: panodan geniş pencere oda ortasına alınmadı; ızgara panosunda kaldı
- **PA-27** · HD-02 (uyari): Duvar 7: 18.0 cm'lik çok kısa pano (özel pano kuralı doğrulanmalı)
- **PA-27** · HD-02 (uyari): Duvar 9: 18.0 cm'lik çok kısa pano (özel pano kuralı doğrulanmalı)
- **PA-27** · HD-03 (hata): liste yazılmaz: beşik + cumba: 2 cumba; liste tek çapraz cumbayı sayar, liste yazılmaz
- **PA-27** · HD-05 (hata): 3D kurulamadı: PrefabrikCatiHatasi: girintili gövdede yalnız beşik çatı çizilir (ana çatı ve paralel cumbalar); 'besik_cumba' yok
- **PA-28** · HD-02 (uyari): Pencere SALON & MUTFAK 150x190: panodan geniş pencere oda ortasına alınmadı; ızgara panosunda kaldı
- **PA-28** · HD-02 (uyari): Pencere YATAK ODASI 150x190: panodan geniş pencere oda ortasına alınmadı; ızgara panosunda kaldı
- **PA-28** · HD-03 (hata): liste yazılmaz: beşik + cumba: 2 cumba; liste tek çapraz cumbayı sayar, liste yazılmaz
- **PA-28** · HD-05 (hata): 3D kurulamadı: PrefabrikCatiHatasi: girintili gövdede yalnız beşik çatı çizilir (ana çatı ve paralel cumbalar); 'besik_cumba' yok
- **PA-29** · HD-02 (uyari): Pencere SALON & MUTFAK 150x190: panodan geniş pencere oda ortasına alınmadı; ızgara panosunda kaldı
- **PA-29** · HD-02 (uyari): Pencere YATAK ODASI 150x190: panodan geniş pencere oda ortasına alınmadı; ızgara panosunda kaldı
- **PA-29** · HD-03 (hata): liste yazılmaz: beşik + cumba: 2 cumba; liste tek çapraz cumbayı sayar, liste yazılmaz
- **PA-29** · HD-05 (hata): 3D kurulamadı: PrefabrikCatiHatasi: girintili gövdede yalnız beşik çatı çizilir (ana çatı ve paralel cumbalar); 'besik_cumba' yok
- **PA-30** · HD-08 (hata): ana çatı: 3D modelde 12 makas, yükleme listesinde 10 (Makas (baş) 2; Makas (orta) 8)
- **PA-30** · HD-07 (bilgi): makas: liste 10, gerçek proje 11 (kart çatısı: Beşik)
- **PA-33** · HD-10 (hata): İş Emri'nde kırma çatı; 3D modelin çatısı GABLE_ROOF (beşik çiziliyor)
- **PA-33** · HD-08 (hata): ana çatı: 3D modelde 15 makas, yükleme listesinde 29 (Makas (ana, mahyaya dik) 11; Makas (kısa, sol uç) 7; Makas (kısa, sağ uç) 7; Makas (çapraz, kırma, sol uç) 2; Makas (çapraz, kırma, sağ uç) 2)
- **PA-34** · HD-02 (uyari): Makas y'yi geçiyor ama kisa_kenar x: montaj paftalarında köşe makasın oturduğu duvarlardadır; pano ızgarası iki yönde 5 cm kayık olabilir, kisa_kenar: y doğrulanmalı
- **PA-34** · HD-10 (hata): İş Emri'nde kırma çatı; 3D modelin çatısı GABLE_ROOF (beşik çiziliyor)
- **PA-34** · HD-08 (hata): ana çatı: 3D modelde 6 makas, yükleme listesinde 25 (Makas (ana, mahyaya paralel) 7; Makas (kısa) 14; Makas (çapraz, kırma) 2; Makas (köşe kısa) 2)
- **PA-35** · HD-04 (hata): Çatı paneli (hafif çelik) · VERANDA çatısı · —: Kural yok
- **PA-35** · HD-07 (bilgi): makas: liste 8, gerçek proje 10 (kart çatısı: Beşik + Cumba)
- **KT-01** · HD-02 (uyari): UYARI: K5: iç kapı boşluğu 80 × 214; kural 90 × 214 (modeldeki ölçü kullanıldı)
- **KT-03** · HD-02 (uyari): UYARI: K6: iç kapı boşluğu 80 × 214; kural 90 × 214 (modeldeki ölçü kullanıldı)
- **KT-07** · HD-02 (uyari): UYARI: karkas kuralı: makas: batı/doğu ailesinin kırma ucunda duvar bulunamadı; uç 0.0 (saçak − saçak payı)
- **KT-07** · HD-02 (uyari): UYARI: karkas kuralı: ara panel: batı/doğu ailesinin kuzey düzleminde 73 cm² parça, kısa kenarı 8.8 cm (makas kalınlığı 8 cm, en küçük parça 100 cm²): panel yok
- **KT-07** · HD-11 (bilgi): tanım sandviç panel çiziyor; gerçek projede "OSB + nem bariyeri + metal kiremit"
- **KT-08** · HD-02 (uyari): UYARI: karkas kuralı: makas: güney cumba batı/güney cumba doğu ailesinde 336.5 konumunda çatının içinde çizgi yok: makas yok
- **KT-08** · HD-02 (uyari): UYARI: karkas kuralı: makas: kuzey cumba batı/kuzey cumba doğu ailesinde 468.2 konumunda çatının içinde çizgi yok: makas yok
- **KT-09** · HD-02 (uyari): UYARI: karkas kuralı: makas: 1. cumba batı/1. cumba doğu ailesinde 142.0 konumunda makas çizgisi 39.4 cm (en kısa 40): makas yok
- **KT-09** · HD-02 (uyari): UYARI: karkas kuralı: makas: 2. cumba batı/2. cumba doğu ailesinin uzanım ucunda duvar bulunamadı; uç 256.0 (düzlemlerin ucu)
- **KT-09** · HD-02 (uyari): UYARI: karkas kuralı: makas: 2. cumba batı/2. cumba doğu ailesinde 256.0 konumunda makas çizgisi 1.4 cm (en kısa 40): makas yok
- **KT-11** · HD-11 (bilgi): tanım tek kat panel (çelik standardı) çiziyor; gerçek projede "OSB + membran + shingle"
- **KT-12** · HD-11 (bilgi): tanım tek kat panel (çelik standardı) çiziyor; gerçek projede "OSB + membran + metal kiremit"
- **KT-13** · HD-02 (uyari): UYARI: K2: iç kapı boşluğu 100 × 214; kural 90 × 214 (modeldeki ölçü kullanıldı)
- **KT-13** · HD-02 (uyari): UYARI: K1: dış kapı boşluğu 100 × 210; kural 95 × 210 (modeldeki ölçü kullanıldı)
- **KT-13** · HD-11 (bilgi): tanım tek kat panel (çelik standardı) çiziyor; gerçek projede "OSB + membran + metal kiremit"
