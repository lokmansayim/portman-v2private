"""İE-14 r3 · P3: beşik çatı üreticisi (dikdörtgen ayak izi): iki düzlem, iki uçta kalkan (dış yüz çizgisinde).
Mahya `x` (doğu–batı) ya da `y` (kuzey–güney). Kanonik formül; saçak her yanda S."""
from __future__ import annotations

from .cati_ortak import duzlem, kalkan


def uret(R, mahya: str, b: dict) -> tuple[list, list]:
    x0, y0, x1, y1 = R
    S = b["S"]
    X0, Y0, X1, Y1 = x0 - S, y0 - S, x1 + S, y1 + S
    if mahya == "x":
        ym = (Y0 + Y1) / 2
        duz = [duzlem(b, "güney", [[X0, Y0], [X1, Y0], [X1, ym], [X0, ym]], [0, 1], {"y": Y0}, "güney yüzü"),
               duzlem(b, "kuzey", [[X0, ym], [X1, ym], [X1, Y1], [X0, Y1]], [0, -1], {"y": Y1}, "kuzey yüzü")]
        kal = [kalkan("batı kalkanı", "x", x0, (y0, y1), "dogu", ["güney", "kuzey"]),
               kalkan("doğu kalkanı", "x", x1, (y0, y1), "bati", ["güney", "kuzey"])]
    else:
        xm = (X0 + X1) / 2
        duz = [duzlem(b, "batı", [[X0, Y0], [xm, Y0], [xm, Y1], [X0, Y1]], [1, 0], {"x": X0}, "batı yüzü"),
               duzlem(b, "doğu", [[xm, Y0], [X1, Y0], [X1, Y1], [xm, Y1]], [-1, 0], {"x": X1}, "doğu yüzü")]
        kal = [kalkan("güney kalkanı", "y", y0, (x0, x1), "kuzey", ["batı", "doğu"]),
               kalkan("kuzey kalkanı", "y", y1, (x0, x1), "guney", ["batı", "doğu"])]
    return duz, kal
