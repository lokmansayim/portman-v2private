#!/usr/bin/env python3
"""İE-14 · otomatik çatı üreticisi (ayrı parça; Lokman, 14.10.2026, r2).

Girdi: kapalı ayak izi (dış yüzler, cm; 14a'da dikdörtgen), tip (beşik/kırma), mahya yönü, eğim. Çıktı: Yapı Tanımı 0.5'in `cati`
bölümü (`duzlemler`, `kalkanlar`); bütün sayılar `kurallar/cizim/cati_uretici.json`'dan (anahtar yoksa aynı değer koddan).
Çıktı `cati_genel.cati_kur`'dan geçmek zorundadır (plan denetçisi ve testler koşturur). L ve cumbalı ayak izi 14b.

Kurallar:
- Saçak dış yüzden 30, saçak kotu = duvar üstü + topuk 10; eğim verilmezse %33; üst pay = panel × √(1 + eğim²).
- Mahya verilmezse uzun kenar boyunca. Kırmada mahya her zaman uzun kenardadır (kısa kenarda ters kırma çıkar): verilen mahya
  kısa kenardaysa `CatiHatasi`. Kare ayak izinde kırma piramittir (mahya boyu 0, dört üçgen).
- Beşik: 2 düzlem + uçlarda 2 kalkan (dış yüz çizgisinde). Kırma: 4 düzlem, kalkan yok.

Hesapta LLM yoktur; aynı girdi aynı çatıyı verir. `olc(cati)` bankadaki elle yazılmış çatıyla kıyas için düzlem sayısı, plan alanı ve
kenar toplamlarını (`cati_kur` sınıflamasıyla: saçak, mahya, kırma) verir (K7).
"""
from __future__ import annotations
from .toplam import sum  # noqa: A001 — 3.11 toplama sırası her Python sürümünde (İE-08 GM2; toplam.py)

import json
import math
from pathlib import Path

KURAL_YOLU = Path(__file__).resolve().parents[2] / "kurallar" / "cizim" / "cati_uretici.json"
VARSAYILAN = {"sacak_cm": 30, "topuk_cm": 10, "panel_kalinligi_cm": 8, "egim_varsayim": 0.33, "egim_yuzde_aralik": [10, 60],
              "tipler": ["besik", "kirma"]}
TIP_ADI = {"besik": "beşik", "kirma": "kırma"}


class CatiHatasi(ValueError):
    pass


def kurallar(yol: Path | None = None) -> dict:
    """Kural tablosunun değerleri; dosya ya da anahtar yoksa koddaki varsayılan."""
    k = dict(VARSAYILAN)
    p = Path(yol) if yol else KURAL_YOLU
    if p.exists():
        ham = json.loads(p.read_text(encoding="utf-8"))
        for ad in VARSAYILAN:
            if isinstance(ham.get(ad), dict) and "deger" in ham[ad]:
                k[ad] = ham[ad]["deger"]
    return k


def _r2(v: float) -> float:
    return round(float(v), 2)


def _sade(plan: list) -> list:
    """Ardışık aynı köşeyi at (kare kırmada mahya boyu 0)."""
    out = []
    for p in plan:
        if not out or abs(out[-1][0] - p[0]) > 1e-6 or abs(out[-1][1] - p[1]) > 1e-6:
            out.append(p)
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) < 1e-6 and abs(out[0][1] - out[-1][1]) < 1e-6:
        out.pop()
    return out


def uret(ayak_izi, tip: str = "besik", mahya: str | None = None, egim_yuzde: float | None = None,
         duvar_ustu: float = 270, kural: dict | None = None) -> dict:
    """Dikdörtgen ayak izi (x0, y0, x1, y1; dış yüzler) üstüne çatı. `mahya`: "x" (doğu–batı) ya da "y" (kuzey–güney)."""
    k = kural or kurallar()
    x0, y0, x1, y1 = (float(v) for v in ayak_izi)
    if x1 <= x0 or y1 <= y0:
        raise CatiHatasi(f"ayak izi boş: {ayak_izi}")
    if tip not in k["tipler"]:
        raise CatiHatasi(f"çatı tipi '{tip}' üretilmez (yalnız {', '.join(k['tipler'])}; L ve cumba 14b)")
    if egim_yuzde is None:
        e = float(k["egim_varsayim"])
    else:
        lo, hi = k["egim_yuzde_aralik"]
        if not lo <= egim_yuzde <= hi:
            raise CatiHatasi(f"eğim %{egim_yuzde} aralık dışı (%{lo}–%{hi})")
        e = round(egim_yuzde / 100, 5)
    uzun = "x" if (x1 - x0) >= (y1 - y0) else "y"
    if mahya not in ("x", "y"):
        mahya = uzun
    elif tip == "kirma" and mahya != uzun and abs((x1 - x0) - (y1 - y0)) > 1e-6:
        raise CatiHatasi("kırmada mahya uzun kenar boyunca olur")
    S, sacak_kotu = float(k["sacak_cm"]), float(duvar_ustu) + float(k["topuk_cm"])
    ust_pay = round(float(k["panel_kalinligi_cm"]) * math.sqrt(1 + e ** 2), 3)
    X0, Y0, X1, Y1 = x0 - S, y0 - S, x1 + S, y1 + S

    def duzlem(ad, plan, yukari, sacak, notu):
        return {"ad": ad, "plan": [[_r2(a), _r2(b)] for a, b in _sade(plan)], "yukari": yukari, "egim": round(e, 5),
                "sacak_kotu": _r2(sacak_kotu), "sacak": {kk: _r2(v) for kk, v in sacak.items()}, "ust_pay": ust_pay, "not": notu}

    def kalkan(ad, eksen, konum, aralik, ic, ust):
        return {"ad": ad, "eksen": eksen, "konum": _r2(konum), "aralik": [_r2(aralik[0]), _r2(aralik[1])], "ic": ic, "ust": ust}

    duz, kal = [], []
    if mahya == "x":
        ym = (Y0 + Y1) / 2
        if tip == "besik":
            duz = [duzlem("güney", [[X0, Y0], [X1, Y0], [X1, ym], [X0, ym]], [0, 1], {"y": Y0}, "güney yüzü"),
                   duzlem("kuzey", [[X0, ym], [X1, ym], [X1, Y1], [X0, Y1]], [0, -1], {"y": Y1}, "kuzey yüzü")]
            kal = [kalkan("batı kalkanı", "x", x0, (y0, y1), "dogu", ["güney", "kuzey"]),
                   kalkan("doğu kalkanı", "x", x1, (y0, y1), "bati", ["güney", "kuzey"])]
        else:
            h = (Y1 - Y0) / 2
            duz = [duzlem("güney", [[X0, Y0], [X1, Y0], [X1 - h, ym], [X0 + h, ym]], [0, 1], {"y": Y0}, "güney yüzü"),
                   duzlem("kuzey", [[X0 + h, ym], [X1 - h, ym], [X1, Y1], [X0, Y1]], [0, -1], {"y": Y1}, "kuzey yüzü"),
                   duzlem("batı", [[X0, Y0], [X0 + h, ym], [X0, Y1]], [1, 0], {"x": X0}, "batı kırması"),
                   duzlem("doğu", [[X1, Y0], [X1, Y1], [X1 - h, ym]], [-1, 0], {"x": X1}, "doğu kırması")]
    else:
        xm = (X0 + X1) / 2
        if tip == "besik":
            duz = [duzlem("batı", [[X0, Y0], [xm, Y0], [xm, Y1], [X0, Y1]], [1, 0], {"x": X0}, "batı yüzü"),
                   duzlem("doğu", [[xm, Y0], [X1, Y0], [X1, Y1], [xm, Y1]], [-1, 0], {"x": X1}, "doğu yüzü")]
            kal = [kalkan("güney kalkanı", "y", y0, (x0, x1), "kuzey", ["batı", "doğu"]),
                   kalkan("kuzey kalkanı", "y", y1, (x0, x1), "guney", ["batı", "doğu"])]
        else:
            h = (X1 - X0) / 2
            duz = [duzlem("batı", [[X0, Y0], [xm, Y0 + h], [xm, Y1 - h], [X0, Y1]], [1, 0], {"x": X0}, "batı yüzü"),
                   duzlem("doğu", [[X1, Y0], [X1, Y1], [xm, Y1 - h], [xm, Y0 + h]], [-1, 0], {"x": X1}, "doğu yüzü"),
                   duzlem("güney", [[X0, Y0], [X1, Y0], [xm, Y0 + h]], [0, 1], {"y": Y0}, "güney kırması"),
                   duzlem("kuzey", [[X1, Y1], [X0, Y1], [xm, Y1 - h]], [0, -1], {"y": Y1}, "kuzey kırması")]
    yon = "doğu–batı" if mahya == "x" else "kuzey–güney"
    return {"tip": tip, "tip_adi": f"{TIP_ADI[tip]} (mahya {yon})", "tip_kaynak": "İE-14 çatı üreticisi (motor/genel/cati_uretici.py)",
            "sacak": int(S) if float(S).is_integer() else S, "topuk": k["topuk_cm"], "duvar_ustu": duvar_ustu,
            "panel_kalinligi": k["panel_kalinligi_cm"], "duzlemler": duz, "kalkanlar": kal}


def olc(cati: dict) -> dict:
    """Kıyas ölçüleri (K7): düzlem sayısı, plan alanı (cm²), kenar türlerinin plan boyu toplamı (cm; `cati_kur` sınıflaması)."""
    from . import cati_genel
    c = cati_genel.cati_kur(cati)
    top: dict[str, float] = {}
    for e in c["kenarlar"]:
        top[e["tur"]] = top.get(e["tur"], 0.0) + e["plan_boy"]
    return {"duzlem": len(cati["duzlemler"]), "plan_cm2": round(c["plan_m2"] * 1e4, 1),
            "kenar_plan_cm": {t: round(v, 2) for t, v in sorted(top.items())}, "kalkan": len(cati.get("kalkanlar", []))}
