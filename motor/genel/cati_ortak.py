"""İE-14 r3 · P3: tipe göre çatı üreticilerinin ortak araçları (düzlem, kalkan, yön dönüşümleri). Geometri kuralı yoktur; kurallar
üreticilerde ve `kurallar/cizim/cati_uretici.json`'da.

Dönüşümler (`ayna_y`, `devrik`) bir çatıyı kanonik yönden (ör. cumba güneyde) asıl yöne taşır: düzlem köşeleri, yukarı yönü, saçak çizgisi,
kalkanın ekseni, konumu, aralığı ve iç yönü birlikte döner; adlar yönle değişir (güney ↔ kuzey; devrikte güney ↔ batı, kuzey ↔ doğu).
"""
from __future__ import annotations

import math


def r2(v: float) -> float:
    return round(float(v), 2)


def sade(plan: list) -> list:
    """Ardışık aynı köşeyi at (mahya boyu 0 ya da çakışan köşe)."""
    out = []
    for p in plan:
        if not out or abs(out[-1][0] - p[0]) > 1e-6 or abs(out[-1][1] - p[1]) > 1e-6:
            out.append(p)
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) < 1e-6 and abs(out[0][1] - out[-1][1]) < 1e-6:
        out.pop()
    return out


def baglam(kural: dict, egim: float, duvar_ustu: float) -> dict:
    """Bir çatının ortak sayıları: saçak, saçak kotu, eğim, panel."""
    return {"S": float(kural["sacak_cm"]), "sk": float(duvar_ustu) + float(kural["topuk_cm"]), "e": egim,
            "panel": float(kural["panel_kalinligi_cm"])}


def duzlem(b: dict, ad: str, plan: list, yukari: list, sacak: dict, notu: str, egim: float | None = None) -> dict:
    e = b["e"] if egim is None else egim
    return {"ad": ad, "plan": [[r2(x), r2(y)] for x, y in sade(plan)], "yukari": list(yukari), "egim": round(e, 5), "sacak_kotu": r2(b["sk"]),
            "sacak": {k: r2(v) for k, v in sacak.items()}, "ust_pay": round(b["panel"] * math.sqrt(1 + e ** 2), 3), "not": notu}


def kalkan(ad: str, eksen: str, konum: float, aralik: tuple, ic: str, ust: list, notu: str | None = None) -> dict:
    k = {"ad": ad, "eksen": eksen, "konum": r2(konum), "aralik": [r2(aralik[0]), r2(aralik[1])], "ic": ic, "ust": list(ust)}
    if notu:
        k["not"] = notu
    return k


# ── yön dönüşümleri ──────────────────────────────────────────────────────────────────────────────────────────────────────
_AD_Y = {"güney": "kuzey", "kuzey": "güney"}
_AD_D = {"güney": "batı", "batı": "güney", "kuzey": "doğu", "doğu": "kuzey"}
_IC_Y = {"kuzey": "guney", "guney": "kuzey"}
_IC_D = {"dogu": "kuzey", "kuzey": "dogu", "bati": "guney", "guney": "bati"}


def _ad(ad: str, tablo: dict) -> str:
    return " ".join(tablo.get(s, s) for s in ad.split(" "))


def _not(k: dict, tablo: dict) -> dict:
    """Notlardaki yön sözcükleri de çevrilir ("cumbanın güney alnı"; inceleme G11)."""
    return {"not": _ad(k["not"], tablo)} if k.get("not") else {}


def ayna_y(c: dict, c0: float) -> dict:
    """y → 2·c0 − y."""
    out = dict(c)
    out["duzlemler"] = [{**d, "ad": _ad(d["ad"], _AD_Y), "not": _ad(d.get("not") or "", _AD_Y), "plan": [[x, r2(2 * c0 - y)] for x, y in reversed(d["plan"])],
                         "yukari": [d["yukari"][0], -d["yukari"][1]],
                         "sacak": {k: (r2(2 * c0 - v) if k == "y" else v) for k, v in d["sacak"].items()}} for d in c["duzlemler"]]
    ks = []
    for k in c.get("kalkanlar") or []:
        if k["eksen"] == "y":
            ks.append({**k, **_not(k, _AD_Y), "ad": _ad(k["ad"], _AD_Y), "konum": r2(2 * c0 - k["konum"]), "ic": _IC_Y.get(k["ic"], k["ic"]),
                       "ust": [_ad(u, _AD_Y) for u in k["ust"]]})
        else:
            ks.append({**k, **_not(k, _AD_Y), "ad": _ad(k["ad"], _AD_Y), "aralik": [r2(2 * c0 - k["aralik"][1]), r2(2 * c0 - k["aralik"][0])],
                       "ust": [_ad(u, _AD_Y) for u in k["ust"]]})
    out["kalkanlar"] = ks
    return out


def devrik(c: dict) -> dict:
    """x ↔ y (köşegene göre yansıma)."""
    out = dict(c)
    out["duzlemler"] = [{**d, "ad": _ad(d["ad"], _AD_D), "not": _ad(d.get("not") or "", _AD_D), "plan": [[y, x] for x, y in reversed(d["plan"])], "yukari": [d["yukari"][1], d["yukari"][0]],
                         "sacak": {{"x": "y", "y": "x"}[k]: v for k, v in d["sacak"].items()}} for d in c["duzlemler"]]
    out["kalkanlar"] = [{**k, **_not(k, _AD_D), "ad": _ad(k["ad"], _AD_D), "eksen": {"x": "y", "y": "x"}[k["eksen"]], "ic": _IC_D.get(k["ic"], k["ic"]),
                         "ust": [_ad(u, _AD_D) for u in k["ust"]]} for k in c.get("kalkanlar") or []]
    return out
