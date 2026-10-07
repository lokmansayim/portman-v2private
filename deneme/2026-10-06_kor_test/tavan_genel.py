#!/usr/bin/env python3
"""Tavan omegası dizilimi (yöntem B): tavan gözlerinde makaslara dik, eşit aralıklı hatlar.

Kör test projesinin (KT-01; Eylül 2026) tavan omega paftasındaki dizilim (6 Ekim 2026; `kurallar.json` → `tavan_omegasi_dizilim`).
Varsayılan hesap değildir: 2025 tarihli 62 m² projenin paftasında dizilim başka (duvar yüzünde hat yok; hatlar duvar yüzünden 27–60 cm içeride) ve
bugünkü alan kuralı ona yakın sonuç verir. Bu dizilim yalnız `yukleme.py --sablon 2026` ile kullanılır; hangisinin kural olduğu Lokman'a soruldu.

- Tavan gözü: makaslı çatının altındaki mahal. Odanın içinden geçen kiriş gözü böler (salon ile mutfak arasındaki kirişin iki yanı ayrı göz).
  Veranda tavanı dış ölçüyle (brüt) alınır. Çatı panelli ek yapıda omega yoktur.
- Hatlar makaslara diktir: gözün üstündeki çatı düzleminin saçağına paralel.
- İlk hat gözün bir duvar yüzündedir (en küçük koordinat); sonrakiler 60 cm aralıkla. Karşı yüz 60'ın katına denk geliyorsa oraya da hat gelir.
- Hattın boyu gözün o çizgideki genişliğidir (karkas yüzleri arasında).

Adet `yukleme.py`'de (yalnız `--sablon 2026` ile): toplam boy ÷ (3,75 − 0,10) + 5.

Hesapta LLM yoktur. Yalnız eksenlere paralel duvarlar ve eksenlere paralel yükselen çatı düzlemleri. Ölçüler cm.
"""
from __future__ import annotations

from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

TOL = 1e-3
PAY = 0.05          # cm; duvar yüzündeki hattın gözün içinde sayılması için


def _parcalar(g):
    if g.is_empty:
        return []
    return [p for p in (g.geoms if g.geom_type in ("MultiPolygon", "GeometryCollection") else [g]) if p.geom_type == "Polygon"]


def tavan_gozleri(y: dict, c: dict, veranda_brut: dict[str, Polygon]) -> list[dict]:
    """Tavan gözleri: {mahal, sinif, cokgen, duzlem}. Çatı paneli altındaki mahaller ve üstünde makaslı düzlem olmayan gözler çıkmaz."""
    t = y["tanim"]
    makasli = [dz for dz in c["duzlemler"] if dz.get("ust_yapi") != "cati_paneli"]
    panelli = [dz for dz in c["duzlemler"] if dz.get("ust_yapi") == "cati_paneli"]
    gozler = []
    for b in y["bolgeler"].values():
        if b["sinif"] == "dis":
            continue
        if b["sinif"] == "veranda":
            alan = veranda_brut.get(b["ad"])
            if alan is None:
                continue
        else:
            alan = b["ham"]
            kirisler = [box(*k["kutu"]).buffer(0.02, join_style=2) for k in t.get("kirisler", []) if k.get("bolge") == b["ad"]]
            if kirisler:                              # odanın içinden geçen kiriş tavanı böler
                alan = alan.difference(unary_union(kirisler))
        for p in _parcalar(alan):
            if p.area < 400:
                continue
            nokta = p.representative_point()
            if any(dz["cokgen"].contains(nokta) for dz in panelli):
                continue
            ustteki = max(makasli, key=lambda dz: dz["cokgen"].intersection(p).area, default=None)
            if ustteki is None or ustteki["cokgen"].intersection(p).area < 1.0:
                continue
            gozler.append({"mahal": b["ad"], "sinif": b["sinif"], "cokgen": p, "duzlem": ustteki["ad"], "yukari": ustteki["yukari"]})
    return gozler


def omega_dizilimi(y: dict, c: dict, kur: dict, veranda_brut: dict[str, Polygon]) -> dict:
    """Gözlere göre hatlar ve toplam boy. Dönen: {boy_cm, hat, gozler: [{mahal, yon, hat, boy_cm, hatlar: [{konum, parcalar}]}]}."""
    td = kur["tavan_omegasi_dizilim"]["deger"]
    if (td["ilk_hat"], td["kiris_boler"], td["veranda"]) != ("duvar_yuzunde", True, "brut"):
        raise ValueError("bu kod yalnız şu dizilimi kurar: ilk hat duvar yüzünde, kiriş gözü böler, veranda brüt (`tavan_omegasi_dizilim`)")
    aralik = td["aralik_m"] * 100
    cik = []
    for g in tavan_gozleri(y, c, veranda_brut):
        yx, yy = g["yukari"]
        if min(abs(yx), abs(yy)) > 1e-6:
            raise ValueError(f"yalnız eksenlere paralel yükselen çatı düzlemlerinde kurulur: {g['duzlem']}")
        hat_y = abs(yx) > abs(yy)                    # düzlem x yönünde yükseliyorsa makaslar x boyunca, omega hatları y boyunca (x sabit)
        x0, y0, x1, y1 = g["cokgen"].bounds
        p0, p1 = (x0, x1) if hat_y else (y0, y1)
        govde = g["cokgen"].buffer(PAY, join_style=2)
        hatlar, k = [], 0
        while p0 + k * aralik <= p1 + 0.5:           # karşı duvar yüzü 60'ın katındaysa oraya da hat gelir (yarım cm'ye kadar)
            p = min(p0 + k * aralik, p1)
            cizgi = LineString([(p, y0 - 10), (p, y1 + 10)] if hat_y else [(x0 - 10, p), (x1 + 10, p)])
            kes = govde.intersection(cizgi)
            parcalar = []
            for s in (kes.geoms if kes.geom_type in ("MultiLineString", "GeometryCollection") else [kes]):
                if s.geom_type != "LineString" or s.length - 2 * PAY < 5.0:
                    continue
                a, b_ = (s.coords[0][1], s.coords[-1][1]) if hat_y else (s.coords[0][0], s.coords[-1][0])
                parcalar.append((round(min(a, b_) + PAY, 2), round(max(a, b_) - PAY, 2)))
            if parcalar:
                hatlar.append({"konum": round(p, 2), "parcalar": parcalar})
            k += 1
        boy = sum(b_ - a for h in hatlar for a, b_ in h["parcalar"])
        cik.append({"mahal": g["mahal"], "duzlem": g["duzlem"], "yon": "y" if hat_y else "x", "hat": len(hatlar), "boy_cm": round(boy, 2),
                    "olcu_cm": [round(p1 - p0, 2), round((y1 - y0) if hat_y else (x1 - x0), 2)], "hatlar": hatlar})
    return {"aralik_cm": aralik, "boy_cm": round(sum(g["boy_cm"] for g in cik), 2), "hat": sum(g["hat"] for g in cik), "gozler": cik}
