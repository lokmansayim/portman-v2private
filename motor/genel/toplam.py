"""Sürümden bağımsız toplama (İE-08 GM2).

Python 3.12, yerleşik `sum()`'ı kayan noktalı sayılar için dengelenmiş toplamaya (Neumaier) çevirdi; aynı sayılar 3.11'de
soldan sağa toplanır. İki sonuç son bitlerde ayrışır ve `round(x, 2)` eşik değerlerde başka tarafa düşer: Ç8801 listesinde
"oda tavan çevreleri" 82,27 m (3.11) ↔ 82,28 m (3.12), KT-01'de 114,81 ↔ 114,8, KT-02'de çatı paneli 109,54 ↔ 109,55
(12 Ekim 2026 taban kanıtı; çizimler ve IFC her iki sürümde aynı). Altın listeler 3.11 davranışıyla donduruldu (D-02, D-08);
bu modül o davranışı her sürümde sabitler: paket modülleri `from .toplam import sum` ile yerleşik `sum`'ı bununla örter.
Değerler değişmez, yalnız toplama sırası 3.11'deki gibi soldan sağa kalır. numpy'nin `.sum()`'ı bundan etkilenmez (kullanılmıyor
sayılan yerler perspektif hacim denetimidir, altın değil).
"""
from __future__ import annotations

_YOK = object()


def sum(iterable, /, start=_YOK):  # noqa: A001 — bilerek yerleşik adı örter
    """Soldan sağa toplama; 3.11'in `sum()`'ı ile aynı sonuç (`start` verilmezse 0'dan başlar)."""
    toplam = 0 if start is _YOK else start
    for x in iterable:
        toplam = toplam + x
    return toplam
