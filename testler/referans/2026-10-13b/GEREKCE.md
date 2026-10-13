# Referans · 2026-10-13b

Gerekçe: D-10 ek 10 (Lokman, 13 Ekim, PR-2b): Bina Özellikleri tablosunda tek satıra sığmayan Pencereler/kapı satırında önce 1× önekleri kalkar, sonra iki satıra sarılır, yazı 5 pt altına inmez (KT-02'de adet sözcüğü de kalkar, varsayım). Değişen yalnız 1. sayfanın özellik değer sütunu: 11 pafta.pdf + 11 pafta_sablon.png izi ve girdi kurallar/cizim/pafta_sablonu.json (2. sayfa ve öteki izler aynı). D-11 (13 Ekim): düzenlenebilir DXF eklendi — 11 *_cizim.dxf izi ve girdi kurallar/cizim/duzenlenebilir.json; mevcut izlerin hiçbiri değişmedi. P6001 DXF/PDF 18/18 aynı.

- Dondurulduğu kod: `e747737`
- Ortam: Python 3.11.17, ezdxf 1.4.4, shapely 2.2.0, pydantic 2.14.1, numpy 2.4.6, PyMuPDF 1.28.2
- Önceki referans: 2026-10-13
- İçerik: 50 girdi dosyası, 22 Beyin vakası, 18 DXF, 18 PDF, 173 genel motor izi

Karar: D-10

## Önceki referansa göre değişen ya da eklenen

- girdi dosyası değişti: kurallar/cizim/pafta_sablonu.json
- girdi dosyası eklendi: kurallar/cizim/duzenlenebilir.json
- GENEL parmak izi değişti: cikti/denetim/genel_c8801/C8801_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_c8801/C8801_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/C8201/C8201_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/C8201/C8201_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/C8801/C8801_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/C8801/C8801_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/C8801K/C8801K_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/C8801K/C8801K_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/C8801L/C8801L_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/C8801L/C8801L_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT01_A/KT01_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT01_A/KT01_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT01_B/KT01_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT01_B/KT01_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT02_A/KT02_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT02_A/KT02_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT02_B/KT02_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT02_B/KT02_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT03_A/KT03_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT03_A/KT03_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT03_B/KT03_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT03_B/KT03_pafta_sablon.png
- GENEL çıktısı eklendi: cikti/denetim/genel_c8801/C8801_cizim.dxf
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.19/C8201/C8201_cizim.dxf
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.19/C8801/C8801_cizim.dxf
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.19/C8801K/C8801K_cizim.dxf
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.19/C8801L/C8801L_cizim.dxf
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.19/KT01_A/KT01_cizim.dxf
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.19/KT01_B/KT01_cizim.dxf
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.19/KT02_A/KT02_cizim.dxf
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.19/KT02_B/KT02_cizim.dxf
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.19/KT03_A/KT03_cizim.dxf
- GENEL çıktısı eklendi: cikti/denetim/genel_matris/0.19/KT03_B/KT03_cizim.dxf

## Dosya özetleri

- `denetim_kosum.json`: 8d1af4d570a16103c51145b737fa2bdc3e6d5694c2a8acef093d58062744f780
- `dxf_parmak_izleri.txt`: c6d1a85ee014b891cf61cf34e0868869ebb82cc9ba3da5dbd14d8e5eac1c89e0
- `pdf_parmak_izleri.txt`: 25ad5c6d74b11b65144513bee6c778eec3455fed20dca5cad12b0bf31d37c13b
- `referans_girdiler.json`: 041af863c97ef55e1d0fbb973e90dc4943c2abdda698c520342d7407e15117d4
- `genel_parmak_izleri.txt`: 802ece78f17c36f570c55dcd18c3ca700a2e4acf1b2fe423988fcab4a327dcee
