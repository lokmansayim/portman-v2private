"""BadeCAD / Alpha Mini .bde okuyucu ve yazıcı.

Satır = bir çubuk, alanlar boşlukla:
``<pano> <tip> <boy> h: … f: … n: … s: … l: … w: … x1: <v> y1: <v> x2: <v> y2: <v>``, satır sonu CRLF.

- tip: 1. harf panodaki yer (P dış çerçeve, S iç düşey, N iç yatay, B çapraz, R ve K başka türler);
  2. harf C profilin açık ağzının baktığı yön (R, L, U, D).
- boy: kesim boyu, mm. x1 y1 x2 y2: sırt hizasındaki referans çizgisi, pano düzleminde mm.
- h: vida (birleşim) yerleri; parçanın sol (düşeyde alt) ucundan mm. Kesitte sırttan 27 mm ağız tarafında.
- f, n, s, w: öteki işlem yerleri (adları dosyada yok); l: bilinmiyor.
Biçim sözlüğü: Mac `Alpha mini AI/_inceleme/IS-1-BadeCAD.html` (12 Kasım 2026).
Sayılar dosyada C'nin ``%g`` biçimiyle (6 anlamlı basamak) yazılı; yazıcı aynısını kullanır.
"""
from __future__ import annotations

import math
from collections import OrderedDict
from pathlib import Path

ETIKETLER = ("h", "f", "n", "s", "l", "w")
UCLAR = ("x1", "y1", "x2", "y2")
YONLER = {"R": (1.0, 0.0), "L": (-1.0, 0.0), "U": (0.0, 1.0), "D": (0.0, -1.0)}
VIDA_SIRTTAN_MM = 27.0


def _sayi(t: str) -> float:
    return float(t)


def _bicim(v: float) -> str:
    return "%g" % v


def oku(yol: str | Path) -> dict:
    """{'cubuklar': [...], 'son_satir_bos': bool}. Her çubuk: pano, tip, boy, h…w listeleri, x1…y2."""
    ham = Path(yol).read_bytes()
    satirlar = ham.split(b"\r\n")
    son_bos = satirlar[-1] == b""
    if son_bos:
        satirlar = satirlar[:-1]
    cubuklar = []
    for no, s in enumerate(satirlar, 1):
        t = s.decode("ascii").split(" ")
        c = {"pano": t[0], "tip": t[1], "boy": _sayi(t[2])}
        i = 3
        for e in ETIKETLER:
            if t[i] != e + ":":
                raise ValueError(f"{yol}:{no}: '{e}:' bekleniyordu, '{t[i]}' geldi")
            i += 1
            liste = []
            while not t[i].endswith(":"):
                liste.append(_sayi(t[i]))
                i += 1
            c[e] = liste
        for e in UCLAR:
            if t[i] != e + ":":
                raise ValueError(f"{yol}:{no}: '{e}:' bekleniyordu, '{t[i]}' geldi")
            c[e] = _sayi(t[i + 1])
            i += 2
        if i != len(t):
            raise ValueError(f"{yol}:{no}: satır sonunda fazla alan")
        cubuklar.append(c)
    return {"cubuklar": cubuklar, "son_satir_bos": son_bos}


def yaz(veri: dict) -> bytes:
    satirlar = []
    for c in veri["cubuklar"]:
        t = [c["pano"], c["tip"], _bicim(c["boy"])]
        for e in ETIKETLER:
            t += [e + ":"] + [_bicim(v) for v in c[e]]
        for e in UCLAR:
            t += [e + ":", _bicim(c[e])]
        satirlar.append(" ".join(t))
    metin = "\r\n".join(satirlar) + ("\r\n" if veri["son_satir_bos"] else "")
    return metin.encode("ascii")


def panolar(veri: dict) -> "OrderedDict[str, list[dict]]":
    sonuc: OrderedDict[str, list[dict]] = OrderedDict()
    for c in veri["cubuklar"]:
        sonuc.setdefault(c["pano"], []).append(c)
    return sonuc


def vida_hatti(c: dict, sirttan: float = VIDA_SIRTTAN_MM):
    """Çubuğun vida hattı: (başlangıç x, y, birim yön x, y, uzunluk). Başlangıç sol (düşeyde alt) uç."""
    x1, y1, x2, y2 = c["x1"], c["y1"], c["x2"], c["y2"]
    ters = (x1 > x2) if abs(x1 - x2) > 1e-6 else (y1 > y2)
    if ters:
        x1, y1, x2, y2 = x2, y2, x1, y1
    uzun = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / uzun, (y2 - y1) / uzun
    nx, ny = -uy, ux
    ax, ay = YONLER[c["tip"][1]]
    if nx * ax + ny * ay < 0:
        nx, ny = -nx, -ny
    return (x1 + nx * sirttan, y1 + ny * sirttan, ux, uy, uzun)


def _kesis(a, b):
    ax, ay, aux, auy, _ = a
    bx, by, bux, buy, _ = b
    payda = aux * buy - auy * bux
    if abs(payda) < 1e-9:
        return None
    t = ((bx - ax) * buy - (by - ay) * bux) / payda
    s = ((bx - ax) * auy - (by - ay) * aux) / payda
    return t, s


def vida_denetimi(veri: dict, tolerans: float = 1.0, sirttan: float = VIDA_SIRTTAN_MM) -> tuple[int, int]:
    """(birleşime düşen vida, toplam vida). Her çubuğun vidaları pano içindeki öteki çubukların
    vida hatlarıyla kesişim yerlerine düşmeli; çubuğun parça içindeki kayması en çok vidayı tutan değerdir."""
    toplam = tutan = 0
    for cubuklar in panolar(veri).values():
        hatlar = [vida_hatti(c, sirttan) for c in cubuklar]
        for i, c in enumerate(cubuklar):
            if not c["h"]:
                continue
            yerler = []
            for j, hat in enumerate(hatlar):
                if i == j:
                    continue
                k = _kesis(hatlar[i], hat)
                if k and -300 < k[0] < hatlar[i][4] + 300 and -300 < k[1] < hat[4] + 300:
                    yerler.append(k[0])
            en_iyi = 0
            for t in yerler:
                for h in c["h"]:
                    kay = t - h
                    say = sum(1 for hh in c["h"] if any(abs(kay + hh - y) < tolerans for y in yerler))
                    en_iyi = max(en_iyi, say)
            toplam += len(c["h"])
            tutan += en_iyi
    return tutan, toplam
