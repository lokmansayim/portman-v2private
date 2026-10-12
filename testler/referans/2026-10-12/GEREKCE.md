# Referans · 2026-10-12

Gerekçe: İE-08 (12 Ekim 2026): genel motor (serbest aks, motor/genel) altın seti eklendi: Ç8801 @0.19 her koşuda (genel_c8801), yedi modelin çizim seti ve A/B listeleri ile 0.12–0.18 liste matrisi tam koşuda (genel_matris); izler PNG/PDF bayt, JSON kanonik, IFC içerik (genel_parmak_izleri.txt). Girdi kalıplarına modeller/ ve kurallar/ (setler, cizim, secenekler, bayi) eklendi. Sır taraması: telefon deseni ondalıkları numara sanmıyor, vps/kapi_d_dogrula.sh:25 beklenen bulgu (2 kontrolde fark kalktı). P6001 ve prefabrik altın çıktılar değişmedi (D-08, D-02).

- Dondurulduğu kod: `2d858fe` üzerine kaydedilmemiş değişiklikler
- Ortam: Python 3.11.17, ezdxf 1.4.4, shapely 2.2.0, pydantic 2.14.1, numpy 2.4.6, PyMuPDF 1.28.2
- Önceki referans: 2026-09-28b
- İçerik: 47 girdi dosyası, 22 Beyin vakası, 18 DXF, 18 PDF, 151 genel motor izi

Karar: D-08

## Önceki referansa göre değişen ya da eklenen

- girdi dosyası eklendi: beyin/veri/adaylar_test.json
- girdi dosyası eklendi: beyin/veri/katalog_37_proje_v2.json
- girdi dosyası eklendi: kurallar/bayi/ornek.json
- girdi dosyası eklendi: kurallar/cizim/cizim_seti.json
- girdi dosyası eklendi: kurallar/liste/setler/0.12.json
- girdi dosyası eklendi: kurallar/liste/setler/0.13.json
- girdi dosyası eklendi: kurallar/liste/setler/0.14.json
- girdi dosyası eklendi: kurallar/liste/setler/0.15.json
- girdi dosyası eklendi: kurallar/liste/setler/0.16.json
- girdi dosyası eklendi: kurallar/liste/setler/0.17.json
- girdi dosyası eklendi: kurallar/liste/setler/0.18.json
- girdi dosyası eklendi: kurallar/liste/setler/0.19.json
- girdi dosyası eklendi: kurallar/model/secenekler/dis_karkas_140.json
- girdi dosyası eklendi: modeller/C8201.json
- girdi dosyası eklendi: modeller/C8801.json
- girdi dosyası eklendi: modeller/C8801K.json
- girdi dosyası eklendi: modeller/C8801L.json
- girdi dosyası eklendi: modeller/KT01.json
- girdi dosyası eklendi: modeller/KT01_pafta_sayimi.json
- girdi dosyası eklendi: modeller/KT02.json
- girdi dosyası eklendi: modeller/KT02_pafta_sayimi.json
- girdi dosyası eklendi: modeller/KT03.json
- girdi dosyası eklendi: modeller/KT03_pafta_sayimi.json
- girdi dosyası eklendi: modeller/altin.json
- GENEL çıktısı eklendi: cikti/denetim/genel_c8801/C8801.ifc
- GENEL çıktısı eklendi: cikti/denetim/genel_c8801/C8801.ozet.json
- GENEL çıktısı eklendi: cikti/denetim/genel_c8801/C8801_girdi.json
- GENEL çıktısı eklendi: cikti/denetim/genel_c8801/C8801_gorunusler.png
- GENEL çıktısı eklendi: cikti/denetim/genel_c8801/C8801_pafta.pdf
- GENEL çıktısı eklendi: cikti/denetim/genel_c8801/C8801_pafta.png
- GENEL çıktısı eklendi: cikti/denetim/genel_c8801/C8801_pafta_ozet.json
- GENEL çıktısı eklendi: cikti/denetim/genel_c8801/C8801_pafta_sablon.png
- GENEL çıktısı eklendi: cikti/denetim/genel_c8801/C8801_plan.png
- GENEL çıktısı eklendi: cikti/denetim/genel_c8801/C8801_plan_bayi.png
- GENEL çıktısı eklendi: cikti/denetim/genel_c8801/C8801_yukleme.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.12/C8201/C8201_girdi.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.12/C8201/C8201_yukleme.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.13/C8201/C8201_girdi.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.13/C8201/C8201_yukleme.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.13/KT01_A/KT01_girdi.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.13/KT01_A/KT01_yukleme.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.13/KT01_B/KT01_girdi.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.13/KT01_B/KT01_yukleme.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.14/C8201/C8201_girdi.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.14/C8201/C8201_yukleme.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.14/KT01_A/KT01_girdi.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.14/KT01_A/KT01_yukleme.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.14/KT01_B/KT01_girdi.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.14/KT01_B/KT01_yukleme.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.15/C8201/C8201_girdi.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.15/C8201/C8201_yukleme.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.15/KT02_A/KT02_girdi.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.15/KT02_A/KT02_yukleme.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.15/KT02_B/KT02_girdi.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.15/KT02_B/KT02_yukleme.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.16/C8201/C8201_girdi.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.16/C8201/C8201_yukleme.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.17/C8201/C8201_girdi.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.17/C8201/C8201_yukleme.json
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.17/KT03_A/KT03_girdi.json
- … ve 116 satır daha

## Dosya özetleri

- `denetim_kosum.json`: 140f0f61a9a130aaa7b19fb14d81e0da958b353877628661cc20183080878b03
- `dxf_parmak_izleri.txt`: c6d1a85ee014b891cf61cf34e0868869ebb82cc9ba3da5dbd14d8e5eac1c89e0
- `pdf_parmak_izleri.txt`: 25ad5c6d74b11b65144513bee6c778eec3455fed20dca5cad12b0bf31d37c13b
- `referans_girdiler.json`: 2b89c9e994d147876c75afce2da4661a3b6d673fb824e624d37dccd8a894fc0f
- `genel_parmak_izleri.txt`: e635e89fe8aa75ca7ffb110c885ce65795db9a37bfee389c0ae38eadbb8feef6
