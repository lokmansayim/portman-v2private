"""Genel motor (İE-08, D-08): Yapı Tanımı 0.5'ten (cm, serbest aks) çizim seti, IFC4, perspektifler ve yükleme listesi.

Çelik ve modül dışı planlar bu paketle çizilir; P6001 ve prefabrik katalog pano birimli Motor'da kalır (`motor/geometry.py`, K02).
Kaynak: İE-05'in deneme kodu (`deneme/2026-10-06_kor_test/`, `deneme/2026-10-03_yukleme/`); 11 modül dosya adlarıyla taşındı,
yalnız içe aktarma ve yol satırları değişti (+ `from .toplam import sum`; tek istisna `perspektif.py`: nesne sırasını sabitleyen bir satır).
Bu pakette yeni: `uret` (tek çağrı), `iz` (içerik izleri), `bayi_gorseli`, `sablon_pafta` (Örnek Şablon), `toplam`, `font/`.
Kurallar `kurallar/` (veri), modeller `modeller/` (Yapı Tanımı JSON) altındadır.
"""
