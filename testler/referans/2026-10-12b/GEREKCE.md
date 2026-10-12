# Referans · 2026-10-12b

Gerekçe: İE-08 kapanış incelemesi düzeltmeleri (12 Ekim 2026, aynı karar D-08): bayi paftası ve görselinde m² sınır kutusu yerine brüt oturum (girdi_genel.metraj oturum_m2; KT-01 110→99, KT-02 107→92, KT-03 100→94), müşteri projeleri (KT) bayiye adsız, Çatı Şekli ve vasistas eşiği kurallar/cizim/pafta_sablonu.json anahtarlarından, uzun değerler kesilmek yerine küçülür, Liberation Sans depodan (makineye bağlı değil), pafta_ozet.json'a oturum_m2; PDF izi bayt yerine içerik (sayfa, çizimler, sözcükler: gömülü yazı tipi sırası depo yoluna bağlıydı); matplotlib rcdefaults; doğrulama geçmezse teslim PDF'i yok (K23, .HATALI.pdf). P6001, çizim seti PNG'leri, listeler ve IFC izleri değişmedi.

- Dondurulduğu kod: `7b6da23` üzerine kaydedilmemiş değişiklikler
- Ortam: Python 3.11.17, ezdxf 1.4.4, shapely 2.2.0, pydantic 2.14.1, numpy 2.4.6, PyMuPDF 1.28.2
- Önceki referans: 2026-10-12
- İçerik: 48 girdi dosyası, 22 Beyin vakası, 18 DXF, 18 PDF, 151 genel motor izi

Karar: D-08

## Önceki referansa göre değişen ya da eklenen

- girdi dosyası eklendi: kurallar/cizim/pafta_sablonu.json
- GENEL parmak izi değişti: cikti/denetim/genel_c8801/C8801_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_c8801/C8801_pafta_ozet.json
- GENEL parmak izi değişti: cikti/denetim/genel_c8801/C8801_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/C8201/C8201_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/C8201/C8201_pafta_ozet.json
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/C8201/C8201_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/C8801/C8801_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/C8801/C8801_pafta_ozet.json
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/C8801/C8801_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/C8801K/C8801K_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/C8801K/C8801K_pafta_ozet.json
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/C8801K/C8801K_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/C8801L/C8801L_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/C8801L/C8801L_pafta_ozet.json
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/C8801L/C8801L_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT01_A/KT01_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT01_A/KT01_pafta_ozet.json
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT01_A/KT01_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT01_A/KT01_plan_bayi.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT01_B/KT01_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT01_B/KT01_pafta_ozet.json
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT01_B/KT01_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT01_B/KT01_plan_bayi.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT02_A/KT02_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT02_A/KT02_pafta_ozet.json
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT02_A/KT02_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT02_A/KT02_plan_bayi.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT02_B/KT02_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT02_B/KT02_pafta_ozet.json
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT02_B/KT02_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT02_B/KT02_plan_bayi.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT03_A/KT03_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT03_A/KT03_pafta_ozet.json
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT03_A/KT03_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT03_A/KT03_plan_bayi.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT03_B/KT03_pafta.pdf
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT03_B/KT03_pafta_ozet.json
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT03_B/KT03_pafta_sablon.png
- GENEL parmak izi değişti: cikti/denetim/genel_matris/0.19/KT03_B/KT03_plan_bayi.png

## Dosya özetleri

- `denetim_kosum.json`: 00cbda28c923fa5716c1b3ad89055b8d2c04bf3c45e8b4f13acc6deacf0f8d41
- `dxf_parmak_izleri.txt`: c6d1a85ee014b891cf61cf34e0868869ebb82cc9ba3da5dbd14d8e5eac1c89e0
- `pdf_parmak_izleri.txt`: 25ad5c6d74b11b65144513bee6c778eec3455fed20dca5cad12b0bf31d37c13b
- `referans_girdiler.json`: 71d4a447c545553755d11a140a6cf92dde8ee82a5c4b0ccbd4801be4a6243d63
- `genel_parmak_izleri.txt`: 65071e72d96274f82a59787671184b7c237596e780f8ee68714788fe037785e9
