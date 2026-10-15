"""İE-14 r3 · P3: beşik + cumba üreticisi (Ç8801'in çatısı; Lokman 10.10.2026: "cumba ana çatıya girip biter").

Kanonik yön: ana gövde doğu–batı bar `[x0, y0, x1, y1]`, mahyası x boyunca; cumba onun güney kenarına bitişik `[a, cy0, b, y0]`. Cumba
kendi beşiğiyle (mahya y boyunca, aynı eğim) ana çatının güney yüzüne girer ve biter: iki vadi cumba saçağının köşelerinden 45°'yle cumba
mahyasının ucunda buluşur. Kalkanlar: ana gövdenin iki ucu (cumba o uçla aynı hizadaysa duvar boydan boya, kalkan aralığı cumbanın dış
yüzünden başlar) ve cumbanın güney alnı. Öteki yönler `cati_ortak` dönüşümleriyle (seçici `cati_uretici`).
"""
from __future__ import annotations

from .cati_ortak import duzlem, kalkan


class CumbaHatasi(ValueError):
    pass


def uret(ana, cumba, b: dict) -> tuple[list, list]:
    x0, y0, x1, y1 = ana
    a, cy0, bb, cy1 = cumba
    if cy1 != y0 or a < x0 or bb > x1:
        raise CumbaHatasi("cumba ana gövdenin güney kenarına bitişik ve onun içinde olmalı")
    S = b["S"]
    X0, Y0, X1, Y1 = x0 - S, y0 - S, x1 + S, y1 + S
    ym = (Y0 + Y1) / 2
    CX0, CX1, CY0 = a - S, bb + S, cy0 - S
    xm = (CX0 + CX1) / 2
    yv = Y0 + (xm - CX0)                                      # cumba mahyasının ana çatıya girdiği nokta (eşit eğim: 45° vadi)
    if yv >= ym:
        raise CumbaHatasi("cumba ana gövdeye göre çok geniş: mahyası ana mahyayı aşıyor (L çatı olmalı)")
    duz = [duzlem(b, "ana güney", [[X0, Y0], [CX0, Y0], [xm, yv], [CX1, Y0], [X1, Y0], [X1, ym], [X0, ym]], [0, 1], {"y": Y0},
                  "ana çatının güney yüzü; cumba buna girip biter"),
           duzlem(b, "ana kuzey", [[X0, ym], [X1, ym], [X1, Y1], [X0, Y1]], [0, -1], {"y": Y1}, "ana çatının kuzey yüzü"),
           duzlem(b, "cumba doğu", [[xm, CY0], [CX1, CY0], [CX1, Y0], [xm, yv]], [-1, 0], {"x": CX1}, "cumbanın doğu yüzü"),
           duzlem(b, "cumba batı", [[CX0, CY0], [xm, CY0], [xm, yv], [CX0, Y0]], [1, 0], {"x": CX0}, "cumbanın batı yüzü")]
    kal = [kalkan("batı kalkanı", "x", x0, (cy0 if a == x0 else y0, y1), "dogu", ["ana güney", "ana kuzey"], "ana çatının batı alnı"),
           kalkan("doğu kalkanı", "x", x1, (cy0 if bb == x1 else y0, y1), "bati", ["ana güney", "ana kuzey"], "ana çatının doğu alnı"),
           kalkan("cumbanın güney kalkanı", "y", cy0, (a, bb), "kuzey", ["cumba batı", "cumba doğu"], "cumbanın güney alnı")]
    return duz, kal
