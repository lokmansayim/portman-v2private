---
paths:
  - "motor/**"
  - "is_emri/**"
  - "ref_katalog/**"
  - "ref_yan/**"
---

# Motor ve çizim kuralları (K02, K16, K23, Z-02, Z-07)

- İş Emri koordinatsız ve pano birimlidir; kural kaynağı prefabrik çizim kuralları v1.4.3 (K02). Pano aksı 125,5 cm (`motor/geometry.py` `MOD`). Modül dışı planlar için (a) modüle uyarlama / (b) serbest aks kararı **Lokman'ındır** (K16 açık); serbest aks yalnız `deneme/` altındadır, ana koda alınmaz.
- Katalog planları çıkarıcıyla okunur (`motor/cikarici.py`), elle kodlanmaz; artıklar raporlanır, sessiz yuvarlama yoktur (K16).
- DXF yeniden açılıp doğrulanmadan PDF yoktur. Doğrulama geçmezse teslim PDF'i üretilmez; yalnız tanı için `.HATALI.pdf` yazılır (K23, `motor/dxf_out.py`).
- Altın testler değişmez: 6×8 (41 pano, 773 × 1014, 0 cm²), Yan Verandalı 6×8,5 (52 pano, BOM 26 kod), P6001 (36 pano, 773 × 763). Sayılar değişiyorsa önce kural mı değişti, hata mı var, ayrımı yapılır.
- Motor'un `passed` demesi kaynağa (katalog çizimi, mühendis kabulü) uygunluk değildir; insan kabulü ayrı yazılır.
- Kapı genişlikleri çalışma kabulüdür (dış 90, iç 82; K04 açık). Blok adları Astra v1.4.3 şeması; Güncel Şablon 2024'e geçiş beklemede (K03).
- Çıktılar Yapı Tanımı'ndan türetilir (Z-02); BIM çıktısı IFC4 (Z-07). IFC şema doğrulaması üretim doğruluğu değildir.
- `is_emri/`, `ref_katalog/`, `ref_yan/` dondurulmuş girdidir: var olan dosya değiştirilmez; yeni dosya eklenirse iş emrinde yazılır.
