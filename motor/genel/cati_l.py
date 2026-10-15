"""İE-14 r3 · P3: L beşik üreticisi (Ç8801L'nin çatısı; "beşik + cumba" ailesinden, iki kol aynı mahya kotunda).

Kanonik yön: blok doğu–batı `[x0, y0, a, y1]` (mahya x boyunca), kanat doğusunda boydan boya `[a, ky0, x2, ky1]` (mahya y boyunca;
ky0 ≤ y0, ky1 ≥ y1). İki mahya aynı kotta buluşur: kanadın eğimi ona göre hesaplanır (Ç8801L: 0,33 × 350 / 230 = 0,50217). Blok yüzleri
kanadın batı yüzüyle vadi yapar. Kalkanlar: bloğun batı alnı ve kanadın güney ve kuzey alnı (bloğun güney/kuzey dış yüzü kanadınkiyle
aynı hizadaysa kanat alnının aralığı o duvarın başından başlar).
"""
from __future__ import annotations

from .cati_ortak import duzlem, kalkan


class LHatasi(ValueError):
    pass


def uret(blok, kanat, b: dict) -> tuple[list, list]:
    x0, y0, a, y1 = blok
    ka, ky0, x2, ky1 = kanat
    if ka != a or ky0 > y0 or ky1 < y1:
        raise LHatasi("kanat bloğun doğusuna bitişik ve onu boydan boya örtmeli")
    S = b["S"]
    X0, Y0, Y1 = x0 - S, y0 - S, y1 + S
    ym = (Y0 + Y1) / 2
    KX0, KX1, KY0, KY1 = a - S, x2 + S, ky0 - S, ky1 + S
    xm = (KX0 + KX1) / 2
    ek = round(b["e"] * (ym - Y0) / (xm - KX0), 5)          # iki mahya aynı kotta
    duz = [duzlem(b, "blok güney", [[X0, Y0], [KX0, Y0], [xm, ym], [X0, ym]], [0, 1], {"y": Y0}, "bloğun güney yüzü"),
           duzlem(b, "blok kuzey", [[X0, ym], [xm, ym], [KX0, Y1], [X0, Y1]], [0, -1], {"y": Y1}, "bloğun kuzey yüzü"),
           duzlem(b, "kanat batı güney", [[KX0, KY0], [xm, KY0], [xm, ym], [KX0, Y0]], [1, 0], {"x": KX0}, "kanadın batı yüzü, güney", ek),
           duzlem(b, "kanat batı kuzey", [[xm, ym], [xm, KY1], [KX0, KY1], [KX0, Y1]], [1, 0], {"x": KX0}, "kanadın batı yüzü, kuzey", ek),
           duzlem(b, "kanat doğu", [[xm, KY0], [KX1, KY0], [KX1, KY1], [xm, KY1]], [-1, 0], {"x": KX1}, "kanadın doğu yüzü", ek)]
    kal = [kalkan("batı kalkanı", "x", x0, (y0, y1), "dogu", ["blok güney", "blok kuzey"], "bloğun batı alnı"),
           kalkan("kanadın güney kalkanı", "y", ky0, (x0 if ky0 == y0 else a, x2), "kuzey", ["kanat batı güney", "kanat doğu"], "kanadın güney alnı"),
           kalkan("kanadın kuzey kalkanı", "y", ky1, (x0 if ky1 == y1 else a, x2), "guney", ["kanat batı kuzey", "kanat doğu"], "kanadın kuzey alnı")]
    return duz, kal
