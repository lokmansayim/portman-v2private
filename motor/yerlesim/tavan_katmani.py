"""İE-15 · K5b-2 · Tavan katmanı: asma dizme tavanın H'ı ve alçıpan gözleri (kural `dizme_tavan`), çatı izolasyonu (kural `cati_izolasyonu`).

Asma dizme tavanda her kapalı odanın tavanı duvarlarla ve omega hatlarıyla (sırt genişliğiyle) sütunlara bölünür; eni en kısa boydan dar
sütun (Motor'un oda çizgisinde duvar kalınlığından kalan şerit) göz almaz. Her sütunda H'lar omegalara dik, koşu ekseninin büyük ucundan
(makas x yönündeyse odanın arka kenarı; montaj rehberiyle aynı) H aralığıyla; son göz `son_en_kisa`'dan kısa kalacaksa o H konmaz. Göz,
sütunun iki H (ya da H ile oda kenarı) arasıdır: ıslak hacimde (liste kuralı `islak_hacim`) yeşil, ötekilerde beyaz alçıpan. Gözün levhaya
kesimi kart modelindedir (`kesim.levha_karti`: raflarla, dar gözler yan yana). Ters tavanda H ve göz yoktur.

Çatı izolasyonu ana çatının her makas aralığında bir şerittir: dış dikdörtgenin dış duvarlarının iç yüzleri arasında, makasa paralel;
ana çatının altındaki gömme veranda ve niş şeridin içindedir (montaj rehberi ve liste gibi). Paket sayısı kart modelinde
(`kesim.paket_karti`). Taşan verandanın yavru makasları bugünkü IFC'de değildir, şerit almaz.
"""
from __future__ import annotations

from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

ESIK = 1e-6
BUYUK = 1e5
DIZME, IZOLASYON = "dizme_tavan", "cati_izolasyonu"           # kuralların adı (`kurallar/yerlesim/prefabrik.json`)


def _kutu(adim: str, a0: float, a1: float, k0: float, k1: float) -> tuple[float, float, float, float]:
    """Adım ekseninde a0..a1, koşu ekseninde k0..k1 → (x0, y0, x1, y1)."""
    return (a0, k0, a1, k1) if adim == "x" else (k0, a0, k1, a1)


def _aralik(q, eksen: str) -> tuple[float, float]:
    b = q.bounds
    return (b[0], b[2]) if eksen == "x" else (b[1], b[3])


def _duvar_kutusu(d) -> tuple[float, float, float, float]:
    return (d.a0, d.c - d.h, d.a1, d.c + d.h) if d.yon == "x" else (d.c - d.h, d.a0, d.c + d.h, d.a1)


def gozler(g: dict, hatlar: list[dict], K: dict) -> list[dict]:
    """Asma dizme tavanın H'ları ve gözleri. `K`: `aralik` (H aralığı, cm), `son_en_kisa`, `en_kisa`, `sirt_60` (sırtı yazılı olmayan omeganın
    sırtı), `islak` (ıslak hacim türleri), `kesit_h` ([en, yükseklik]), `kalinlik` (alçıpan), `omega_h` (omeganın yüksekliği). Odanın türü
    `g["odalar"][i]["tur"]`'dadır (İş Emri'nden)."""
    if g["tavan"] != "asma":
        return []
    kosu = "y" if g["cati"]["makas_ekseni"] == "x" else "x"
    adim = "x" if kosu == "y" else "y"
    duvar = unary_union([box(*_duvar_kutusu(d)) for d in g["duvarlar"]])
    omega = unary_union([box(*_kutu(adim, h["s"] - h.get("sirt", K["sirt_60"]) / 2, h["s"] + h.get("sirt", K["sirt_60"]) / 2, h["r0"], h["r1"]))
                         for h in hatlar if h["eksen"] == adim])
    z0 = g["duvar_h"] - K["omega_h"]
    hw, hh = K["kesit_h"]
    out = []
    for oda in g["odalar"]:
        P = Polygon(oda["poligon"]).difference(duvar).difference(omega)
        renk = "yesil" if oda.get("tur") in K["islak"] else "beyaz"
        sutunlar = sorted((q for q in getattr(P, "geoms", [P]) if q.geom_type == "Polygon" and not q.is_empty
                           and _aralik(q, adim)[1] - _aralik(q, adim)[0] >= K["en_kisa"] - ESIK),
                          key=lambda q: _aralik(q, adim))
        for j, q in enumerate(sutunlar, 1):
            k_lo, k_hi = _aralik(q, kosu)
            cizgiler, t = [], k_hi - K["aralik"]
            while t > k_lo + K["son_en_kisa"] + ESIK:
                cizgiler.append(round(t, 4))
                t -= K["aralik"]
            for i, t in enumerate(cizgiler, 1):
                kes = q.intersection(LineString([_kutu(adim, -BUYUK, BUYUK, t, t)[:2], _kutu(adim, -BUYUK, BUYUK, t, t)[2:]]))
                for c in getattr(kes, "geoms", [kes]):
                    if c.geom_type != "LineString" or c.length < K["en_kisa"] - ESIK:
                        continue
                    a0, a1 = _aralik(c, adim)
                    x0, y0, x1, y1 = _kutu(adim, a0, a1, t - hw / 2, t + hw / 2)
                    out.append({"kural": DIZME, "parca": "tavan_h", "boy_cm": round(a1 - a0, 4),
                                "geo": {"tip": "kutu", "kutu": [x0, y0, z0, x1, y1, z0 + hh]},
                                "bilgi": {"Tavan": "asma", "Mahal": oda["ad"], "Sutun": j, "Sira": i},
                                "aciklama": f"{kosu} = {t:g}, {a0:g}–{a1:g} ({oda['ad']}, {j}. sütun)"})
            sinirlar = [k_hi] + cizgiler + [k_lo]
            for i, (ust, alt) in enumerate(zip(sinirlar, sinirlar[1:]), 1):
                bant = q.intersection(box(*_kutu(adim, -BUYUK, BUYUK, alt, ust)))
                for r in getattr(bant, "geoms", [bant]):
                    if r.geom_type != "Polygon" or r.area < K["en_kisa"] ** 2 - ESIK:
                        continue
                    (a0, a1), (b0, b1) = _aralik(r, adim), _aralik(r, kosu)
                    x0, y0, x1, y1 = r.bounds
                    out.append({"kural": DIZME, "parca": "goz", "alan_m2": round(r.area / 1e4, 4),
                                "geo": {"tip": "kutu", "kutu": [x0, y0, z0 - K["kalinlik"], x1, y1, z0]},
                                "bilgi": {"Tavan": "asma", "Mahal": oda["ad"], "Renk": renk, "Sutun": j, "Sira": i,
                                          "En_cm": round(a1 - a0, 4), "Uzunluk_cm": round(b1 - b0, 4)},
                                "aciklama": f"{oda['ad']}, {j}. sütun {i}. göz ({a1 - a0:g} × {b1 - b0:g})"})
    return out


def izolasyon(g: dict, K: dict) -> list[dict]:
    """Ana çatının her makas aralığında bir şerit: dış duvarların iç yüzleri arasında (makasın uzandığı eksende), iki makasın arası (uç
    duvarların iç yüzüne kırpılır). `K`: `kalinlik` (şeridin gösterim kalınlığı)."""
    mk = sorted(m["konum"] for m in g["makaslar"])
    if len(mk) < 2:
        return []
    t = 2 * max((d.h for d in g["duvarlar"] if d.tur == "dis"), default=0.0)        # dış duvarın kalınlığı
    boy, derin = (g["W"], g["H"]) if g["cati"]["makas_ekseni"] == "x" else (g["H"], g["W"])
    out = []
    for i, (k0, k1) in enumerate(zip(mk, mk[1:]), 1):
        k0, k1 = max(k0, t), min(k1, derin - t)
        if k1 - k0 <= ESIK:
            continue
        x0, y0, x1, y1 = (t, k0, boy - t, k1) if g["cati"]["makas_ekseni"] == "x" else (k0, t, k1, boy - t)
        out.append({"kural": IZOLASYON, "parca": "serit", "alan_m2": round((boy - 2 * t) * (k1 - k0) / 1e4, 4),
                    "geo": {"tip": "kutu", "kutu": [x0, y0, g["duvar_h"], x1, y1, g["duvar_h"] + K["kalinlik"]]},
                    "bilgi": {"Aralik": i, "En_cm": round(k1 - k0, 4), "Uzunluk_cm": round(boy - 2 * t, 4)},
                    "aciklama": f"{i}. makas aralığı ({k0:g}–{k1:g}), {t:g}–{boy - t:g}"})
    return out
