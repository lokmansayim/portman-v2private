"""Çerçeve geometrisinden Alpha Mini makine işlemleri (BK-78, deneme).

Girdi: MRD çerçevesinin parçaları (eksen uçları, boy, LABEL_NRM/INV). Çıktı: her parçanın işlemleri
(DIMPLE vida, SWAGE köşeleme, NOTCH kertme, LIP_CUT düzleme, CUT kesim). SERVICE_HOLE (servis deliği)
kuralı yok, üretilmez. Kurallar Mac `Alpha mini AI/_inceleme/IS-8, IS-9` (12 Kasım 2026) ve makine
ayarı (Unbak U1 2000M: köşeleme kalıbı 68, kertme 50, düzleme 62 mm).
"""
from __future__ import annotations

import math

YARIM = 27.0          # kanat 54 mm'nin yarısı: eksenden sırta ve ağza
KOSELEME = 34.0       # 68 / 2
KOSELEME_ADIM = 68.0
KERTME = 25.0         # 50 / 2
DUZLEME = 62.0
DUZLEME_UC = 31.0     # 62 / 2
EPS = 1.0


class Parca:
    def __init__(self, p: dict, sira: int):
        self.p, self.sira = p, sira
        self.x1, self.y1 = p["x1"], p["y1"]
        dx, dy = p["x2"] - p["x1"], p["y2"] - p["y1"]
        self.L = math.hypot(dx, dy)
        self.ux, self.uy = dx / self.L, dy / self.L
        s = 1.0 if p["yon"] == "LABEL_NRM" else -1.0
        self.nx, self.ny = -self.uy * s, self.ux * s   # ağzın baktığı yön
        self.islem: list[tuple[str, float]] = []

    def t(self, x, y):
        return (x - self.x1) * self.ux + (y - self.y1) * self.uy

    def n(self, x, y):
        return (x - self.x1) * self.nx + (y - self.y1) * self.ny

    def nokta(self, t, n=0.0):
        return (self.x1 + self.ux * t + self.nx * n, self.y1 + self.uy * t + self.ny * n)

    def uc(self, hangi):
        return self.nokta(0.0 if hangi == 0 else self.L)


def _kesis(ax, ay, aux, auy, bx, by, bux, buy):
    """a + t·au = b + s·bu → (t, s); paralelse None."""
    d = aux * buy - auy * bux
    if abs(d) < 1e-9:
        return None
    t = ((bx - ax) * buy - (by - ay) * bux) / d
    s = ((bx - ax) * auy - (by - ay) * aux) / d
    return t, s


def _icinde(b: Parca, x, y, pay=EPS) -> bool:
    return abs(b.n(x, y)) <= YARIM + pay and -pay <= b.t(x, y) <= b.L + pay


def _duzleme(alan: Parca, giren: Parca) -> list[float]:
    """Giren parçanın gövdesinin, alan parçanın dudak çizgisini kestiği yerde düzleme vuruşları."""
    dx, dy = alan.nokta(0.0, YARIM)
    ts = []
    for k in (-YARIM, YARIM):
        gx, gy = giren.nokta(0.0, k)
        r = _kesis(dx, dy, alan.ux, alan.uy, gx, gy, giren.ux, giren.uy)
        if r is None:
            return []
        ts.append(r[0])
    t1, t2 = min(ts) - 1.0, max(ts) + 1.0     # iki yana 1 mm pay
    w = t2 - t1
    if w <= DUZLEME + 1e-6:                    # payla kalıba sığar: tek vuruş, ortadan
        yer = [(t1 + t2) / 2]
    elif w - 2.0 <= DUZLEME + 1e-6:            # gövde sığar, payla taşar: ikinci vuruş bitiş kenarına
        yer = [(t1 + t2) / 2, t2 - DUZLEME_UC]
    else:                                      # gövde sığmaz: baş ve bitiş kenarına, arası 62 adım
        ilk, son = t1 + DUZLEME_UC, t2 - DUZLEME_UC
        yer = [ilk]
        v = ilk + DUZLEME
        while v < son - 1e-6:
            yer.append(v)
            v += DUZLEME
        yer.append(son)
    return [min(max(v, DUZLEME_UC), alan.L - DUZLEME_UC) for v in yer]


def uret(parcalar: list[dict]) -> list[list[tuple[str, float]]]:
    P = [Parca(p, i) for i, p in enumerate(parcalar)]
    # vida: eksenlerin kesiştiği yer, iki parça birbirine değiyorsa
    for i, a in enumerate(P):
        for b in P[i + 1:]:
            r = _kesis(a.x1, a.y1, a.ux, a.uy, b.x1, b.y1, b.ux, b.uy)
            if r is None:
                continue
            ta, tb = r
            if -YARIM - EPS <= ta <= a.L + YARIM + EPS and -YARIM - EPS <= tb <= b.L + YARIM + EPS:
                x, y = a.nokta(ta)
                if _icinde(a, x, y, YARIM) and _icinde(b, x, y, YARIM):
                    a.islem.append(("DIMPLE", ta))
                    b.islem.append(("DIMPLE", tb))
    # uçlar
    def _dik(p):
        return abs(p.uy) > 0.99

    def _uca_yakin(b, x, y):
        t = b.t(x, y)
        return min(abs(t), abs(t - b.L)) <= 2 * YARIM

    def _icte(a, hangi, b):
        """Giren parçanın karşı parçanın içinde kalan en uzun boyu (iki kanat kenarından büyüğü)."""
        uc_t = 0.0 if hangi == 0 else a.L
        en = 0.0
        for k in (-YARIM, YARIM):
            kx, ky = a.nokta(uc_t, k)
            fx, fy = b.nokta(0.0, YARIM)
            r = _kesis(kx, ky, a.ux, a.uy, fx, fy, b.ux, b.uy)
            if r:
                en = max(en, abs(r[0]))
        return en

    kose_bitti = set()
    for a in P:
        for hangi in (0, 1):
            ex, ey = a.uc(hangi)
            adaylar = [b for b in P if b is not a and abs(a.ux * b.uy - a.uy * b.ux) > 1e-6 and _icinde(b, ex, ey)]
            if not adaylar:
                continue
            b = adaylar[0]
            ic = 1.0 if hangi == 0 else -1.0
            uc_t = 0.0 if hangi == 0 else a.L
            yer = lambda d: uc_t + ic * d  # noqa: E731
            if _uca_yakin(b, ex, ey):     # köşe: iki parça uç uca
                anahtar = frozenset((a.sira, b.sira))
                if anahtar in kose_bitti:
                    continue
                kose_bitti.add(anahtar)
                bx, by = (b.uc(0) if abs(b.t(ex, ey)) < abs(b.t(ex, ey) - b.L) else b.uc(1))
                bh = 0 if abs(b.t(ex, ey)) < abs(b.t(ex, ey) - b.L) else 1
                if _dik(a) and not _dik(b):
                    giren, alan, gh = a, b, hangi
                elif _dik(b) and not _dik(a):
                    giren, alan, gh = b, a, bh
                elif abs(abs(a.uy) - abs(b.uy)) < 1e-3:
                    giren, alan, gh = (a, b, hangi) if a.sira < b.sira else (b, a, bh)
                else:
                    a.islem += [("LIP_CUT", v) for v in _duzleme(a, b)]
                    b.islem += [("LIP_CUT", v) for v in _duzleme(b, a)]
                    continue
                gt = 0.0 if gh == 0 else giren.L
                giren.islem.append(("SWAGE", gt + (1 if gh == 0 else -1) * KOSELEME))
                alan.islem += [("LIP_CUT", v) for v in _duzleme(alan, giren)]
                continue
            ortx, orty = a.nokta(a.L / 2)
            if b.n(ortx, orty) > 0:   # ağızdan giriş
                a.islem.append(("SWAGE", yer(KOSELEME)))
                icte = _icte(a, hangi, b)
                if icte > 67.0 + 1e-6:
                    v = icte - 33.0
                    while v > KOSELEME + 1e-6 or v == icte - 33.0:
                        a.islem.append(("SWAGE", yer(v)))
                        v -= KOSELEME_ADIM
                b.islem += [("LIP_CUT", v) for v in _duzleme(b, a)]
            else:                     # sırttan geliş
                r = _kesis(a.x1, a.y1, a.ux, a.uy, b.x1, b.y1, b.ux, b.uy)
                a.islem.append(("NOTCH", yer(KERTME)))
                if r:
                    if abs(r[0] - uc_t) > 22.0 + 1e-6:
                        a.islem.append(("NOTCH", r[0] + ic * 3.0))
                    b.islem.append(("SWAGE", r[1]))
                a.islem += [("LIP_CUT", v) for v in _duzleme(a, b)]
    for a in P:   # aynı yere aynı işlem iki kez vurulmaz
        gor, yeni = set(), []
        for k, v in a.islem:
            if (k, round(v, 1)) in gor:
                continue
            gor.add((k, round(v, 1)))
            yeni.append((k, v))
        a.islem = yeni
    for a in P:
        a.islem.append(("CUT", a.p["boy"]))
    return [a.islem for a in P]


def kiyas(parcalar: list[dict], uretilen, tolerans: float = 0.6, haric=("SERVICE_HOLE",)) -> dict:
    """İşlem türüne göre (tutan, dosyadaki, fazla)."""
    sonuc: dict[str, list[int]] = {}
    for p, u in zip(parcalar, uretilen):
        turler = {k for k, _ in p["islemler"]} | {k for k, _ in u}
        for tur in turler - set(haric):
            dosya = sorted(v for k, v in p["islemler"] if k == tur)
            bizim = sorted(v for k, v in u if k == tur)
            kalan = list(bizim)
            tut = 0
            for v in dosya:
                j = next((i for i, w in enumerate(kalan) if abs(w - v) <= tolerans), None)
                if j is not None:
                    kalan.pop(j)
                    tut += 1
            s = sonuc.setdefault(tur, [0, 0, 0])
            s[0] += tut
            s[1] += len(dosya)
            s[2] += len(kalan)
    return sonuc


SIRA = ("DIMPLE", "LIP_CUT", "SWAGE", "NOTCH", "SERVICE_HOLE", "CUT")


def islemli(veri: dict, servis_deligi_koru: bool = True) -> dict:
    """Çerçevenin işlemlerini geometriden yeniden üretir; mrd.yaz ile dosyaya yazılabilir.
    Servis deliğinin kuralı yok: istenirse kaynaktakiler korunur."""
    yeni = dict(veri)
    uretilen = uret(veri["parcalar"])
    parcalar = []
    for p, u in zip(veri["parcalar"], uretilen):
        isl = list(u)
        if servis_deligi_koru:
            isl += [(k, v) for k, v in p["islemler"] if k == "SERVICE_HOLE"]
        isl.sort(key=lambda kv: (SIRA.index(kv[0]) if kv[0] in SIRA else 99, kv[1]))
        isl = [(k, round(v, 2)) for k, v in isl]
        parcalar.append(dict(p, islemler=isl))
    yeni["parcalar"] = parcalar
    return yeni
