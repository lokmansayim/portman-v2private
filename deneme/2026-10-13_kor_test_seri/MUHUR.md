# Prefabrik kör test serisi · mühür kaydı (13 Ekim 2026, 10:50)

Lokman, 13 Ekim 10:37: "Buradaki tek kat prefabrikleri bul, yükleme listesi montaj paftası olanları kör teste tabi tut, beraber iyileştirelim";
10:41: "montaj paftası varsa kesinlikle uygulanmıştır, dönüşü olmaz". Kaynak: Mac `~/Desktop/Portatifev Toptan/Bayiler/`.

Gerçek yükleme listeleri **açılmadı, kopyalanmadı**; yalnız SHA-256 özetleri alındı (Mac'te `sha256sum`). Bir PK'nın listesi, o PK için
kendi listemiz depoya commit'lendikten sonra açılır ve özeti bu tabloyla karşılaştırılır (protokol `docs/sartname/prefabrik_kor_test.md` §3–4).
Adlar yazılabilir (D-11). Bulunan dosya adları yalnız dizin listesinden.

| PK | Proje (klasör) | Montaj paftası | Gerçek liste (mühürlü) | SHA-256 | Bayt |
|---|---|---|---|---|---|
| PK-01 | Huma 60 m² (ayrı klasör) | PDF tam set | `HUMA 60M2 YUKLEME LISTESI.xlsx` | `17e43b888bd1a5dd5bfb06ebb38b620b1b0c3708c176a35d7ea576f1e948d106` | 196.855 |
| PK-02 | Mehmet Balaban 58 m² | PDF tam set | `…/Malzeme Listesi/MEHMET BALABAN 58 M2 - PREFABRİK - YÜKLEME LİSTESİ.XLSX` | `9081e5e14b36db504cc4292ceedcf95fc903f72c1b1362e8e3e4ee5f10961f28` | 164.625 |
| | | | aynı, PDF | `9e0a87d11cecb0ffc8c099b7f088886e64eecbc8e6d57543c878db45c7bc5006` | 358.521 |
| | | | üst klasördeki PDF | `588c111a140f9aa501e4cf1e5412a6e3b5bc69d54346c77049de4e807e4f2c29` | 360.341 |
| PK-03 | Doğan Prefabrik 81 m² (Nimet Bey) | PDF tam set + plan DXF | `…/Malzeme Listesi/DOĞAN PREFABRİK YÜKLEME LİSTESİ.XLSX` | `1a42996f551190b96396cd2adf4dd63608c4c6340ed997872e9eac014978ad67` | 171.083 |
| | | | `Montaj Paftaları/DOĞAN PREFABRİK YÜKLEME LİSTESİ.XLSX` (başka sürüm) | `fe5948f5dcbcfb3cdd870d69751758f4b333d54a3d587871d35b3033d97c3f04` | 172.141 |
| PK-04 | İsmail Ürün (Aziz Bey, satıldı) — **çelik karkas, prefabrik pano değil; seriden çıkarıldı (13.10 11:40), genel motor kör testine** | PDF tam set (zemin kat duvar panelleri, aşık, çatı, makas, tavan omega, elektrik) | `Yükleme ve Montaj/İsmail Ürün Yükleme Listesi.pdf` | `0a3ef4ccdf45f52f5bd67c538aa75457ed77b15a6bc4391480f3f92329765e0a` | 481.765 |
| | | | `…-Yazıcı.pdf` | `4edb8d3d10e4bac7bfd8be0c4ad92932751177a3e017266e991d5eaf964adcab` | 512.970 |
| | | | `…-Yazıcı2.pdf` | `ed1a24dbeaa1c17733d335d26b8856d673b373376063f6d617b771b3622b6193` | 513.395 |
| PK-05 | Abdullah Yavuz 60 m² (Mehmet Yıldırım) | panel yerleşimi PDF + DXF | `…/Malzeme Listesi/ABDULLAH YAVUZ YÜKLEME LİSTESİ.XLSX` | `561ad34a90ffee815f73e6013a37a8b7536a118ca5292bb6cf29be2a3c70a779` | 217.461 |
| | | | aynı, PDF | `2a03aa6764ee71b2a975a0ab2db4684534c511384ff06ed7ee95cb4cad5fe866` | 161.954 |
| | | | `…LİSTE Sİ Yazıcı.pdf` | `3f23db158c7751e6d34cee6420016c0b9f00fbb68dc14f6dd9ac16f0ec9fc02b` | 98.637 |
| PK-06 | Sevim Güler 82 + 10 m² (Mehmet Yıldırım) | `Montaj Pafta ve Yükleme/1–8.pdf` (içerikleri henüz bilinmiyor: liste sayfası var mı açmadan denetlenecek) | `SEVİM GÜLER 82+10 M2 YÜKLEME LİSTESİ.XLSX` | `3cf217510de4c60f4c702ca4d1336b2b7cb649a2fb27f313149244012340e2fe` | 212.572 |
| | | | aynı, PDF | `5874e5e764458e9bbeaecce6418b19a3aa7abc4149ece04e2d41b9fac5923555` | 148.166 |
| PK-07 | Diamond 70 m² (Aziz Bey, Halil Bey) | `DIAMOND 70 M2 MONTAJ PAFTASI.pdf` | `DIAMOND 70 M2 YUKLEME LISTESI.pdf` | `985c3a209bd736eb68fe46cab9964569ca85b41ab7cb8cfb68fe29af7ce78086` | 240.638 |
| | | | `70 m² Prefabrik - Halil Bey.xlsx` (açılmadı, içerik bilinmiyor; 13.10 12:58'de eklendi) | `36d5f1f353ad606fa972a309ccf620a774a40c708f966170dd45fe01caec3d76` | 148.179 |
| | | | `… .pdf` | `105c6f87f57ebcc8c6ec57070ed8d461a8632c51c71b749e669c3c0906c5f722` | 340.178 |
| | | | `… - Revize.xlsx` | `d25c68fc4cd2578095b0a698f212869ec2babd3bdb1187badb5e963ab18f5b97` | 148.249 |
| | | | `… - Revize.pdf` | `3c448656a1cbaba830482f0bd68670474ec59f7a7646625b6598109b579ef5f6` | 340.146 |
| PK-08 | Eren Bey 60 m² (Muhammed Uysal) | duvar ve omega yerleşim PDF'leri | `LOFTEV PREFABRİK YÜKLEME LİSTESİ.xlsx` | `dca060f8ff046f69f9466ba6d99d5fa0c2dbec16f5ff75bc4ffdb16f202d531c` | 50.134 |
| | | | `M.Uysal Eren Bey 60 ㎡Yükleme Listeis.xlsx` | `a748c76bf2a1169dee87762aaa78fba37b92385ca020e7e84eb7bac5677441ea` | 48.456 |

## Kör değil (kıyas için değil, kaynak olarak)

- **Altan Bey 60 m² tek kat** — `UĞUR BAŞARIR 60 M2  YÜKLEME LİSTESİ.xlsx` (`37897a98…f2c29`… tam: `37897a98894fc0d095c7a4f2ae34e960f08f1e5bd136581e64850752b4d8be22`) 21 Eylül 2026'da açıldı ve P6001 kurallarının (6 Ekim "liste kuralı") kaynağı oldu (`docs/notlar/2026-09-21_Yukleme_Listesi_Analizi.md`). Kör test olamaz. Aynı klasördeki `Altan Bey 60 duvar yerleşim planı.pdf`, `Makas Aks yerleşim planı.pdf`, `Omega Yerleşim Planı.pdf` P6001'in yeniden çizimi için beklenen "doğru kaynak" olabilir (`docs/sartname/modeller/P6001.md`); Lokman'a sorulacak. Öteki liste: `Altan Bey Fiyatlı Yükleme listesi 60 m².xlsx` (`27bc90114ce85d9b6a33f8db7d76eb838f80126af5e6bbe1a23c5e0e3a6f92ad`).
- PK-08'in Loftev listesi: Uğur Başarır dosyasının öteki sayfaları "Loftev TEK KATLI – 2. BİNA" şablonunu taşıyordu (21 Eylül); aynı proje olabilir, kıyasta not edilir.

## Bu seride yok

- Çift kat: Diamond Bereket 144 m² (H 2800), Altan Bey 150 m², Doğan 162 / 164 m². Çelik: Aytaç Bey 62, Hüseyin Yıldırım 105, Bedirhan Bey 90, Çatalca showroom.
- Montajı yalnız DWG olanlar (burada okunamıyor; PDF çıktısı gelirse eklenir): Doğan 61 / 60 m² (`Doğan Prefabrik 61 m² Yükleme Listesi.xlsx` `d62ffc7a…f07f90`, örnek 60 m² `09504702…2f3c70`), Kenan Karabiber 74 m² (`95cb0173…d74eb`), Altan Bey 135 m² (ön onay PDF'i 62 KB; liste `9d56668b…efb9`), Sibel Akar 87 m² (`37445438…312071`).
- Portman çıktısı (gerçek liste değil): Modern Prefabrik `T1012CV_yukleme_listesi`.

## Açılışlar

| PK | Kendi listemiz (commit) | Mühür denetimi | Açılış | Kıyas |
|---|---|---|---|---|
| PK-01 | `aebcfca` 10:48:50 | `17e43b88…d106` aynı | 10:49:17 | `deneme/2026-10-13_pk_01/sonuc/PK01_kiyas.md` |
| PK-02 | `d31c35c` 11:20:47 | `9081e5e1…961f28` aynı (Mac, 11:21:08) | 11:21:21 | `deneme/2026-10-13_pk_02/sonuc/PK02_kiyas.md` |
| PK-05 | `90bc8e5` 12:21:54 | `561ad34a…a779` aynı (Mac, 12:21:58) | 12:22:10 | `deneme/2026-10-13_pk_05/sonuc/PK05_kiyas.md` |
| PK-03 | `022b0d3` 12:09:37 | `fe5948f5…3f04` ve `1a42996f…ad67` aynı (Mac, 12:09:43) | 12:10:02 | `deneme/2026-10-13_pk_03/sonuc/PK03_kiyas.md` |
| PK-06 | `90869d0` 12:41:20 | `3cf21751…e2fe` xlsx ve `5874e5e7…3555` pdf aynı (Mac, 12:41:30) | 12:41:40 | `deneme/2026-10-13_pk_06/sonuc/PK06_kiyas.md` |

PK-02 klasöründe mühür tablosunda olmayan bir xlsx daha var (`Mehmet Balaban 58 m² .xlsx`, 7 Kasım 2025, `7327bef1…93bd9`); açılmadı, kıyasa girmedi.

PK-06'nın `1–8.pdf` dosyaları okumada açıldı: sekizi de pafta (onay, montaj, tavan omega, makas ve dere × 2, aşık, kaplama, elektrik); liste sayfası yok.
