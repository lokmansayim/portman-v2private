"""Alpha Mini üretim dosyaları (BK-76): .bde (BadeCAD) ve .csv (MRD FrameBuilder) okuyucu ve yazıcı.

Üretim dosyası makinenin kesip deldiği çubukların listesidir. Okuyucu dosyayı sayılara çevirir,
yazıcı aynı sayılardan dosyayı bayt bayt geri yazar (testler/uretim/). Montaj rehberi ve paftalar
orijinal üretim çizimini bu okuyucudan alır (Lokman, 24 Kasım 2026).
"""
from . import bde, mrd  # noqa: F401
