"""Tavan omegası (kart OM-01): hatlar ve parçalar. Kural `kurallar/yerlesim/prefabrik.json › tavan_omegasi_yerlesimi` (karar B).

Ara hatlar mahyaya paraleldir (makasa dik); duvar eksenindeki hatlar duvarın yönündedir. Asma dizme tavanda her iç duvarın ekseninde bir
hat ve her kapalı odada başlangıç sınırından asma aralığıyla ara hatlar; ters tavanda her kapalı odada başlangıç duvarının yüzünden
kitabın aralığıyla. Açık mahalde (ana çatının altındaki veranda) hat duvarın yüzünden kitabın aralığıyla başlar. Odanın öteki sınırına en
kısa boydan yakın hat ya da hattın o kısmı konmaz (L biçimli odada her kol kendi sınırıyla). Her hat dizilimin başladığı uçtan tam
parçalara (parça boyu − pay), kalanı son parçaya bölünür; en kısa boydan kısa kalan parçasız boşluktur.

K5b-2: açık mahale bakan dış duvarın üstündeki 100'lük duvar omegası (kart OM-02) `dis_duvar_hatlari`'ndadır.
"""
from __future__ import annotations

from shapely.affinity import translate
from shapely.geometry import LineString, Polygon, box
from shapely.ops import linemerge, unary_union

from .girdi import YAPISMA_CM, Duvar

ESIK = 1e-6


def _koordinat(eksen: str, s: float, r: float) -> tuple[float, float]:
    """Adım ekseni `eksen`'deki `s` ve koşu eksenindeki `r` → (x, y)."""
    return (s, r) if eksen == "x" else (r, s)


def _kesit(poligon, eksen: str, s: float) -> list[tuple[float, float]]:
    """`poligon`'un adım eksenindeki `s` çizgisiyle kesişimi, koşu ekseninde (r0, r1) parçaları."""
    if poligon.is_empty:
        return []
    x0, y0, x1, y1 = poligon.bounds
    ic = (s + 1e-6) if s <= (x0 if eksen == "x" else y0) + 1e-6 else ((s - 1e-6) if s >= (x1 if eksen == "x" else y1) - 1e-6 else s)
    cizgi = LineString([_koordinat(eksen, ic, -1e5), _koordinat(eksen, ic, 1e5)])
    k = poligon.intersection(cizgi)
    parcalar = [k] if k.geom_type == "LineString" else [g for g in getattr(k, "geoms", []) if g.geom_type == "LineString"]
    out = []
    for g in parcalar:
        r = [c[1] if eksen == "x" else c[0] for c in g.coords]
        if max(r) - min(r) > ESIK:
            out.append((min(r), max(r)))
    return sorted(out)


def _uzak(P, adim: str, yon: int, d: float):
    """`P`'nin, adım ekseninde `yon` yönünde `d` ötesi de `P`'de kalan kısmı: o yandaki sınırına `d`'den yakın olmayan yerler."""
    if d <= ESIK:
        return P
    return P.intersection(translate(P, *((-yon * d, 0.0) if adim == "x" else (0.0, -yon * d))))


def _sinir(duvarlar: list[Duvar], kosu: str, yuz: float, taraf: int, r_aralik: tuple[float, float]) -> tuple[float, Duvar | None]:
    """Odanın bir yandaki sınırı: o yanda koşu eksenine paralel bir duvarın yüzü varsa duvarın kendisi; iç duvarda sınır ekseni,
    dış duvarda yüzüdür (ızgaranın başı dış duvarın iç yüzü). `taraf` −1: oda duvarın arttığı yanda (duvarın yüzü c + h), +1: azaldığı."""
    for d in duvarlar:
        if d.yon != kosu or min(d.a1, r_aralik[1]) - max(d.a0, r_aralik[0]) <= YAPISMA_CM:
            continue
        if abs((d.c + d.h if taraf < 0 else d.c - d.h) - yuz) <= YAPISMA_CM:
            return (d.c if d.tur == "ic" else yuz), d
    return yuz, None


def hatlar(g: dict, K: dict, uyarilar: list | None = None) -> list[dict]:
    """Omega hatları: {yer, eksen (adım ekseni), s, r0, r1, mahal, not[, sirt]}. `K`: okunan değerler (`aralik_asma`, `aralik_ters`, `en_kisa`,
    `sirt_100`: 100'lük iç duvarın üstündeki hattın sırtı, cm).
    Hat konmayan açık mahal parçası `uyarilar`'a yazılır."""
    uyarilar = uyarilar if uyarilar is not None else []
    kosu = "y" if g["cati"]["makas_ekseni"] == "x" else "x"         # mahyaya paralel
    adim = "x" if kosu == "y" else "y"
    duvarlar = g["duvarlar"]
    yon_s = 1 if g["baslangic"][adim] == "min" else -1
    out = []
    ic_kal_mm = {round(2 * d.h * 10) for d in duvarlar if d.tur == "ic"}
    duvar_hatti = g["tavan"] == "asma" or (ic_kal_mm and max(ic_kal_mm) < 100)   # ters tavanda 100'lük iç duvarın üstü 100'lük duvar omegası
    if duvar_hatti:
        for d in sorted((d for d in duvarlar if d.tur == "ic"), key=lambda d: (d.yon, d.c, d.a0)):
            out.append({"yer": "duvar_ekseni", "eksen": "x" if d.yon == "y" else "y", "s": d.c, "r0": d.a0, "r1": d.a1, "mahal": "",
                        "not": f"iç duvar ekseni ({'x' if d.yon == 'y' else 'y'} = {d.c:g})",
                        # 100'lük iç duvarın üstü: 60'lık omeganın ölçüsünde, sırtı geniş (Lokman, 29 Ekim 13:12; D-32; ters tavanda hat yok)
                        **({"sirt": K["sirt_100"]} if round(2 * d.h * 10) >= 100 and K.get("sirt_100") is not None else {})})
    en_kisa = K["en_kisa"]
    for oda in g["odalar"]:
        P = Polygon(oda["poligon"])
        b = P.bounds
        lo, hi = (b[0], b[2]) if adim == "x" else (b[1], b[3])
        r_ar = (b[1], b[3]) if adim == "x" else (b[0], b[2])
        s_lo, d_lo = _sinir(duvarlar, kosu, lo, -1, r_ar)
        s_hi, d_hi = _sinir(duvarlar, kosu, hi, +1, r_ar)
        konumlar = []
        if g["tavan"] == "asma":
            bas, son = (s_lo, s_hi) if yon_s > 0 else (s_hi, s_lo)
            d_son = d_hi if yon_s > 0 else d_lo
            Q = _uzak(P, adim, yon_s, en_kisa - (d_son.h if d_son and d_son.tur == "ic" else 0.0))    # öteki sınır iç duvarda eksen
            k = 1
            while yon_s * ((bas + yon_s * k * K["aralik_asma"]) - son) <= -en_kisa + ESIK:
                konumlar.append(("ara", bas + yon_s * k * K["aralik_asma"], Q)); k += 1
            if not konumlar:                                            # hattı çıkmayan odaya ortasında bir hat (PK-01 hol; PK-02 hol 1)
                konumlar.append(("ara", (s_lo + s_hi) / 2, P))
        else:
            bas, son = (lo, hi) if yon_s > 0 else (hi, lo)
            Q = _uzak(P, adim, yon_s, en_kisa)
            k = 0
            while yon_s * ((bas + yon_s * k * K["aralik_ters"]) - son) <= -en_kisa + ESIK:
                konumlar.append(("duvar_yuzu" if k == 0 and (d_lo if yon_s > 0 else d_hi) else "ara", bas + yon_s * k * K["aralik_ters"], Q)); k += 1
        for yer, s, alan in konumlar:
            for r0, r1 in _kesit(alan, adim, s):
                out.append({"yer": yer, "eksen": adim, "s": round(s, 4), "r0": r0, "r1": r1, "mahal": oda["ad"], "not": ""})
    for v in g["acik"]:                                                 # açık mahal: duvarın yüzünden kitabın aralığıyla (PK-01 veranda)
        P = Polygon(v["poligon"])
        engel = [box(*e) for e in g["engeller"] if box(*e).intersects(P)]
        if engel:
            P = P.difference(unary_union(engel))
        if P.is_empty:
            continue
        parcalar = sorted(getattr(P, "geoms", [P]), key=lambda p: -p.area)
        P = parcalar[0]
        for q in parcalar[1:]:                                          # profil mahali bölerse hat en büyük parçaya (kural); öteki parçalar uyarı
            qb = q.bounds
            if (qb[2] - qb[0] if adim == "x" else qb[3] - qb[1]) >= en_kisa - ESIK:
                uyarilar.append({"katman": "tavan omegası", "metin": f"{v['ad']}: profil mahali bölüyor; {q.area / 1e4:.2f} m²'lik parçaya hat konmadı "
                                                                     f"(kural en büyük parçaya koyar)"})
        b = P.bounds
        lo, hi = (b[0], b[2]) if adim == "x" else (b[1], b[3])
        r_ar = (b[1], b[3]) if adim == "x" else (b[0], b[2])
        _s, d_lo = _sinir([d for d in duvarlar if d.tur == "dis"], kosu, lo, -1, r_ar)
        _s, d_hi = _sinir([d for d in duvarlar if d.tur == "dis"], kosu, hi, +1, r_ar)
        yon = yon_s if (d_lo and d_hi) or not (d_lo or d_hi) else (1 if d_lo else -1)
        bas, son = (lo, hi) if yon > 0 else (hi, lo)
        duvarli = d_lo if yon > 0 else d_hi
        Q = _uzak(P, adim, yon, en_kisa)
        k = 0
        while yon * ((bas + yon * k * K["aralik_ters"]) - son) <= -en_kisa + ESIK:
            s = bas + yon * k * K["aralik_ters"]
            for r0, r1 in _kesit(Q, adim, s):
                out.append({"yer": "duvar_yuzu" if k == 0 and duvarli else "ara", "eksen": adim, "s": round(s, 4), "r0": r0, "r1": r1,
                            "mahal": v["ad"], "not": "açık mahal"})
            k += 1
    return out


def dis_duvar_hatlari(g: dict, K: dict) -> list[dict]:
    """Çatı kenarına gelmeyen dış duvarların 100'lük duvar omegası (kart OM-02; Lokman, 21 Ekim; D-32): kapalı kısmın açık mahalle (ana çatının
    altındaki veranda, giriş nişi) ortak sınırındaki dış duvarın ekseninde, ortak sınır boyunca; ucu köşeye bir duvar kalınlığından yakınsa
    duvarın ucuna (panolar gibi). Tavanın türüne bakılmaz. Taşan veranda (BK-14) `g["acik"]`'ta değildir: ona bakan duvar ana çatının
    kenarındadır. Hat: {yer: duvar_ekseni, dis: True, eksen, s, r0, r1, mahal, not, sirt}."""
    out = []
    for v in g["acik"]:
        sinir = Polygon(v["poligon"]).boundary
        for d in sorted((d for d in g["duvarlar"] if d.tur == "dis"), key=lambda d: (d.yon, d.c, d.a0)):
            for yuz in d.yuzler:
                cizgi = LineString([(d.a0, yuz), (d.a1, yuz)] if d.yon == "x" else [(yuz, d.a0), (yuz, d.a1)])
                k = cizgi.intersection(sinir)
                cizgiler = [q for q in getattr(k, "geoms", [k]) if q.geom_type == "LineString" and q.length > ESIK]
                if not cizgiler:
                    continue
                k = linemerge(cizgiler)                                 # sınırdaki ara köşeler ortak sınırı bölmesin
                for p in getattr(k, "geoms", [k]):
                    if p.length < K["en_kisa"] - ESIK:
                        continue
                    r = [c[0] if d.yon == "x" else c[1] for c in p.coords]
                    r0, r1 = min(r), max(r)
                    r0 = d.a0 if r0 - d.a0 <= 2 * d.h + YAPISMA_CM else r0
                    r1 = d.a1 if d.a1 - r1 <= 2 * d.h + YAPISMA_CM else r1
                    e = "x" if d.yon == "y" else "y"
                    out.append({"yer": "duvar_ekseni", "dis": True, "eksen": e, "s": d.c, "r0": r0, "r1": r1, "mahal": v["ad"], "sirt": K["sirt_100"],
                                "not": f"dış duvar ekseni ({e} = {d.c:g}), {v['ad']} mahaline bakar"})
    return out


def parcala(r0: float, r1: float, tam: float, en_kisa: float, sondan: bool) -> tuple[list[tuple[float, float]], float]:
    """Hattı (r0, r1) dizilimin başladığı uçtan `tam` boylarda parçalara böler; kalan `en_kisa`'dan kısaysa parçasız boşluktur.
    `sondan`: dizilim koşu ekseninin büyük ucundan başlar. Döner: ([(a, b)…], boşluk boyu)."""
    out, kalan = [], r1 - r0
    u = r1 if sondan else r0
    while kalan > tam + ESIK:
        out.append((u - tam, u) if sondan else (u, u + tam))
        u = u - tam if sondan else u + tam
        kalan -= tam
    if kalan >= en_kisa - ESIK:
        out.append((u - kalan, u) if sondan else (u, u + kalan))
        return out, 0.0
    return out, kalan
