---
paths:
  - "motor/**"
  - "is_emri/**"
  - "ref_katalog/**"
  - "ref_yan/**"
  - "kurallar/**"
  - "modeller/**"
---

# Motor ve çizim kuralları (K02, K16, K23, Z-02, Z-07)

- İş Emri koordinatsız ve pano birimlidir; kural kaynağı prefabrik çizim kuralları v1.4.3 (K02). Pano aksı 125,5 cm (`motor/geometry.py` `MOD`). P6001 ve prefabrik katalog planları bu Motor'da kalır.
- **K16 kapandı, (b) (Lokman 11.10.2026; D-08):** çelik ve modül dışı planlar **serbest aksla genel motorda** (`motor/genel/`; Yapı Tanımı 0.5, cm; `python -m motor.genel.uret`). İki motor yan yana yaşar; hangisinin koşacağını aday kaydındaki `motor` alanı ve İş Emri zarfındaki `yapi.sistem` söyler. Genel motorun davranışı kural kitabına bağlıdır (`kurallar/`; yeni davranış her zaman bir kural anahtarına bağlanır, anahtar yoksa eski davranış sürer; kural değişikliği yeni set sürümü). Altın adımlar kural seti 0.19 pimiyle koşar (`kurallar/liste/setler/0.19.json`); `kurallar.json` ilerleyince referans değişmez.
- **Genel motor altın testleri değişmez:** Ç8801 @0.19 plan/görünüşler/pafta PNG ve liste JSON bayt bayt, IFC ve şablon PDF'i içerikçe (`modeller/altin.json`; `testler/referans/` zinciri `genel_parmak_izleri.txt`); tam koşuda yedi modelin çizim setleri ve 0.12–0.19 liste matrisi. Bayi görselinde ve paftada m² brüt oturumdur (`girdi_genel.metraj` `oturum_m2`, listedeki `bina_m2` ile aynı; sınır kutusu değil, D-08 K-A1). Doğrulama geçmezse teslim adıyla PDF yoktur (`.HATALI.pdf`, K23 genel motorda da). Çizim baytları matplotlib'e bağlıdır (`uret.matplotlib_sabitle`: DejaVu Sans, varsayılan hinting; matplotlib sürümü değişirse yeniden dondurma kararı). Toplama sırası her Python sürümünde 3.11 gibi (`motor/genel/toplam.py`). Perspektifler altın değildir (VTK; boyut ve geometri sayıları).
- **Bayi paftası "Örnek Şablon"un aynısıdır** (Lokman, 6.10.2026 19:46; `docs/sartname/plan_paftasi_sablonu.md`; `motor/genel/sablon_pafta.py`): A4 yatay, plan + sol yan + ön görünüş, bina özellikleri, özel istekler, antet; 2. sayfa dört görünüş ve çatı planı; bilinmeyen değer "...", uydurulmaz (K21); koda bağlı seçimler (vasistas eşiği, çatı tipi adları, yazı boyu) `kurallar/cizim/pafta_sablonu.json` anahtarlarıyla; yazı tipleri depodan (`motor/genel/font/`: Comic Relief, Liberation Sans; makineye bağlı değil). Genel motorun `pafta.png`'si mühendis paftasıdır, sette kalır. Model tanımları `modeller/` altındadır: var olan tanım değiştirilmez, yeni dosya ya da sürüm eklenir (D-07); KT'ler müşteri projesidir, bayiye adsız.
- Katalog planları çıkarıcıyla okunur (`motor/cikarici.py`), elle kodlanmaz; artıklar raporlanır, sessiz yuvarlama yoktur (K16).
- DXF yeniden açılıp doğrulanmadan PDF yoktur. Doğrulama geçmezse teslim PDF'i üretilmez; yalnız tanı için `.HATALI.pdf` yazılır (K23, `motor/dxf_out.py`).
- Altın testler değişmez: 6×8 (41 pano, 773 × 1014, 0 cm²), Yan Verandalı 6×8,5 (52 pano, BOM 26 kod), P6001 (36 pano, 773 × 763). Sayılar değişiyorsa önce kural mı değişti, hata mı var, ayrımı yapılır.
- Motor'un `passed` demesi kaynağa (katalog çizimi, mühendis kabulü) uygunluk değildir; insan kabulü ayrı yazılır.
- Kapı genişlikleri çalışma kabulüdür (dış 90, iç 82; K04 açık). Blok adları Astra v1.4.3 şeması; Güncel Şablon 2024'e geçiş beklemede (K03).
- Çıktılar Yapı Tanımı'ndan türetilir (Z-02); BIM çıktısı IFC4 (Z-07). IFC şema doğrulaması üretim doğruluğu değildir.
- `is_emri/`, `ref_katalog/`, `ref_yan/` dondurulmuş girdidir: var olan dosya değiştirilmez; yeni dosya eklenirse iş emrinde yazılır.
