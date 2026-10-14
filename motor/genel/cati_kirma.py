"""İE-14 r3 · P3: kırma çatı üreticisi (dikdörtgen ayak izi): dört düzlem, kalkan yok. Mahya uzun kenar boyunca (kısa kenarda ters kırma
çıkar; seçici reddeder). Kare ayak izinde piramit (mahya boyu 0, dört üçgen). Kanonik formül; saçak her yanda S, kırmalar 45°."""
from __future__ import annotations

from .cati_ortak import duzlem


def uret(R, mahya: str, b: dict) -> tuple[list, list]:
    x0, y0, x1, y1 = R
    S = b["S"]
    X0, Y0, X1, Y1 = x0 - S, y0 - S, x1 + S, y1 + S
    if mahya == "x":
        ym = (Y0 + Y1) / 2
        h = (Y1 - Y0) / 2
        duz = [duzlem(b, "güney", [[X0, Y0], [X1, Y0], [X1 - h, ym], [X0 + h, ym]], [0, 1], {"y": Y0}, "güney yüzü"),
               duzlem(b, "kuzey", [[X0 + h, ym], [X1 - h, ym], [X1, Y1], [X0, Y1]], [0, -1], {"y": Y1}, "kuzey yüzü"),
               duzlem(b, "batı", [[X0, Y0], [X0 + h, ym], [X0, Y1]], [1, 0], {"x": X0}, "batı kırması"),
               duzlem(b, "doğu", [[X1, Y0], [X1, Y1], [X1 - h, ym]], [-1, 0], {"x": X1}, "doğu kırması")]
    else:
        xm = (X0 + X1) / 2
        h = (X1 - X0) / 2
        duz = [duzlem(b, "batı", [[X0, Y0], [xm, Y0 + h], [xm, Y1 - h], [X0, Y1]], [1, 0], {"x": X0}, "batı yüzü"),
               duzlem(b, "doğu", [[X1, Y0], [X1, Y1], [xm, Y1 - h], [xm, Y0 + h]], [-1, 0], {"x": X1}, "doğu yüzü"),
               duzlem(b, "güney", [[X0, Y0], [X1, Y0], [xm, Y0 + h]], [0, 1], {"y": Y0}, "güney kırması"),
               duzlem(b, "kuzey", [[X1, Y1], [X0, Y1], [xm, Y1 - h]], [0, -1], {"y": Y1}, "kuzey kırması")]
    return duz, []
