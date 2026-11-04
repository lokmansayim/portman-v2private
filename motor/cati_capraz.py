"""İE-15 K6 · Beşik + çıkıntısız çapraz cumbanın çatı parçaları ve makas yerleri (TK-04, AP-06, AP-13, AP-16; D-47).

Çatının düzlemleri ve kalkanları çizimdeki çatıdır (`cati_prefabrik.cati`: ön onay çizimi, görünüşler ve liste aynı tanımı okur); bu modül
geometri kurmaz, tanıma girintili gövdenin çatısındaki (`cati_serit.tanim`) gibi `parcalar` ekler. Bugünkü IFC (`ifc_uret._cati_serit`),
kart modelinin çatı katmanları (`motor/yerlesim/serit.py`) ve montaj rehberi (`araclar/paket/rehber/capraz.py`) makasları buradan okur;
liste (`prefabrik_liste._capraz_cumba_catilari`) aynı kuralla kendisi sayar, kart modeli onunla kıyaslanır (`testler/paket/test_k6_rehber.py`):

- **Ana çatı** gövdenin kutusunda beşik; makaslar gövdenin bütün derinliğini geçer, cumbanın altında da (AP-13 M1–M7, AP-16 MKS1–7,
  AP-06 MK01–08). Yerleri dikdörtgen beşiğin kuralıyla (BK-12 PR-R, `ifc_uret.IfcUretici.cati`): baş makaslar iki kalkan duvarının
  ekseninde, orta makaslar boydan boya kesintisiz koşan saçak duvarının pano eklerinde (iki duvar da kesintisizse ortak ekler); ekler
  düzenli değilse (125,5 arayla değil, sayı listeninkinden farklı) eşit aralıkla, listenin sayısında (⌈(boy − 2 × dış duvar) ÷ 125,5⌉ + 1)
  ve uyarıyla.
- **Cumba** ana çatıya dik küçük beşik; alnı ana çatının saçak duvarında (çıkıntı 0), mahyası dış yüzden derelerin birleştiği yere kadar.
  Makaslar dış uçtaki kalkan duvarının ekseninden 125,5 arayla, derelerin birleştiği yere kadar (D-47; liste aynı yeri sayar): ilki
  cumbanın baş makası (kalkan duvarının üstünde), ötekiler ana çatının üstünde, iki dere arasında (yavru makas; paftada "iki ana makasın
  arasında kısa").

Çıkıntılı cumba (AP-22: gövde girintili) ve birden çok cumba bu sürümde yok: `PrefabrikCatiHatasi` (yanlış çatı kurulmaz).
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from . import geometry as G
from .cati_prefabrik import PrefabrikCatiHatasi

MOD = G.MOD
TOL = 0.01


def _mahya_kenari(t: dict) -> dict:
    """Cumbanın mahya kenarı (`cati_genel.cati_kur`): iki cumba yüzünün ortak yatay kenarı."""
    from .genel import cati_genel
    ck = cati_genel.cati_kur(t)
    mh = [e for e in ck["kenarlar"] if e["tur"] == "mahya" and all(not d.startswith("ana ") for d in e["duzlemler"])]
    if len(mh) != 1:
        raise PrefabrikCatiHatasi(f"beşik + cumba: cumbanın mahyası {len(mh)} kenar (bir beklenir)")
    return mh[0]


def cumba_makaslari(t: dict, ie: dict, plan: G.Plan) -> dict:
    """Cumbanın makasları (D-47): dış uçtaki kalkan duvarının ekseninden 125,5 arayla derelerin birleştiği yere kadar. Dönen: cephe, dış
    yüz, mahyanın dış yüzden birleşime uzaklığı (`birlesim`), makasların dış yüzden uzaklığı (`uzaklik`) ve dünyadaki yeri (`konum`)."""
    from .cati_prefabrik import _cumba
    c = ie.get("cati") or {}
    cephe = c["cumbalar"][0]["cephe"]
    _ana, (cx0, cy0, cx1, cy1) = _cumba(c, tuple(float(v) for v in G.govde_kutusu(plan)))
    h = next(d.h for d in plan.duvarlar if d.tur == "dis")
    dis = {"on": cy0, "arka": cy1, "sol": cx0, "sag": cx1}[cephe]
    ic = 1.0 if cephe in ("on", "sol") else -1.0                                # dış yüzden içeri yön (dizildiği eksende)
    eks = 1 if cephe in ("on", "arka") else 0
    mh = _mahya_kenari(t)
    birlesim = max(abs(v[eks] - dis) for v in (mh["p"], mh["q"]))
    uzak = [h + i * MOD for i in range(int(math.floor((birlesim - h) / MOD - 1e-9)) + 1)]
    return {"cephe": cephe, "dis": dis, "ic": ic, "eks": eks, "h": h, "kutu": [cx0, cy0, cx1, cy1], "birlesim": birlesim, "mahya": mh,
            "uzaklik": uzak, "konum": [dis + ic * u for u in uzak]}


def ana_makaslari(plan: G.Plan, eksen: str, a0: float, a1: float, b0: float, b1: float, h: float) -> tuple[list[float], list[str]]:
    """Ana çatının makas yerleri (mahya boyunca, `a`), dikdörtgen beşiğin kuralıyla (BK-12 PR-R; `ifc_uret.IfcUretici.cati`'deki kural,
    burada planın duvarlarından okunur). Dönen: (yerler, uyarılar)."""
    td = 2 * h
    L = a1 - a0
    n_liste = math.ceil((L - 2 * td) / MOD - 1e-6) + 1
    yon = "x" if eksen == "y" else "y"                                          # saçak duvarı mahyaya paralel

    def sacak_ekleri(b: float, ic: float):
        ar = sorted((p.a0 - a0, p.a1 - a0) for d in plan.duvarlar if d.tur == "dis" and d.yon == yon and abs(d.c - ic * d.h - b) < TOL
                    for p in d.panolar)
        tam = (bool(ar) and ar[0][0] <= td + 1e-6 and ar[-1][1] >= L - td - 1e-6 and all(abs(p[1] - q[0]) < 1e-6 for p, q in zip(ar, ar[1:])))
        return {round(v, 3) for p in ar for v in p if td + 1e-6 < v < L - td - 1e-6} if tam else None

    ekler = [e for e in (sacak_ekleri(b0, 1.0), sacak_ekleri(b1, -1.0)) if e is not None]
    uyari, ys = [], None
    if not ekler:
        uyari.append(f"makas yeri (ana çatı): boydan boya kesintisiz saçak duvarı yok; eşit aralıklı {n_liste} makas")
    else:
        if len(ekler) == 2 and ekler[0] != ekler[1]:
            uyari.append("makas yeri (ana çatı): iki saçak duvarının pano ekleri farklı; ortak ekler alındı")
        aday = [td / 2] + sorted(set.intersection(*ekler)) + [L - td / 2]
        ara = [q - p for p, q in zip(aday, aday[1:])]
        if (len(aday) == n_liste and all(abs(x - MOD) < 0.01 for x in ara[1:-1]) and all(0 < x < MOD + 0.01 for x in (ara[0], ara[-1]))):
            ys = aday
        else:
            uyari.append(f"makas yeri (ana çatı): saçak duvarının pano ekleri düzensiz ({len(aday)} makas, listede {n_liste}; aralıklar "
                         f"{', '.join(f'{x:g}' for x in (round(v, 2) for v in ara))}); eşit aralıklı {n_liste} makas")
    if ys is None:
        ys = [td / 2 + i * (L - td) / (n_liste - 1) for i in range(n_liste)]
    return [a0 + y for y in ys], uyari


def tanim(plan: G.Plan, ie: dict) -> dict:
    """Çizimdeki çatı (`cati_prefabrik.cati`) + `parcalar` (ana çatı ve cumba: `a` mahya boyunca, `b` makas boyunca dış yüzler, mahya,
    mahya kotu, makaslar) ve `uyarilar`; `capraz` True. Girintili gövdenin tanımıyla (`cati_serit.tanim`) aynı anahtarlar."""
    from . import cati_prefabrik as CP
    from .cati_serit import _eksen
    c = ie.get("cati") or {}
    if c.get("tip") != "besik_cumba":
        raise PrefabrikCatiHatasi(f"çapraz cumba tanımı yalnız beşik + cumba çatıda ({c.get('tip')})")
    cs = c.get("cumbalar") or []
    if len(cs) != 1 or float(cs[0].get("cikinti_cm", 0)) != 0 or plan.girintili:
        raise PrefabrikCatiHatasi("beşik + cumba: kart modeli tek, çıkıntısız çapraz cumbayı kurar (çıkıntılı cumba ve çift cumba bu sürümde yok)")
    t = CP.cati(plan, ie)
    s, top, H0 = float(t["sacak"]), float(t["topuk"]), float(t["duvar_ustu"])
    eg = float(c["egim_yuzde"]) / 100.0
    zs = H0 + top
    P, K, eksen = _eksen(ie)
    h = next(d.h for d in plan.duvarlar if d.tur == "dis")
    gx0, gy0, gx1, gy1 = (float(v) for v in G.govde_kutusu(plan))
    (a0, b0), (a1, b1) = K(gx0, gy0), K(gx1, gy1)
    a0, a1, b0, b1 = min(a0, a1), max(a0, a1), min(b0, b1), max(b0, b1)
    yer, uyarilar = ana_makaslari(plan, eksen, a0, a1, b0, b1, h)
    duzenli = not uyarilar
    bm = (b0 + b1) / 2
    ana = {"ad": "ana çatı", "rol": "ana", "a": [a0, a1], "b": [b0, b1], "aciklik_cm": round(b1 - b0, 2), "boy_cm": round(a1 - a0, 2),
           "mahya": [list(P(a0 - s, bm)), list(P(a1 + s, bm))], "mahya_kotu": round(zs + eg * (bm - b0 + s), 2),
           "makas_ust_boy_cm": round((bm - b0 + s) * math.sqrt(1 + eg * eg), 2), "makas_yuksekligi_cm": round(top + eg * (bm - b0 + s), 2),
           "makaslar": [{"konum": round(x, 2), "rol": "bas" if i in (0, len(yer) - 1) else "orta"} for i, x in enumerate(yer)],
           "makas_yeri": "pano ekleri" if duzenli else "eşit aralık", "komsu": None}
    m = cumba_makaslari(t, ie, plan)
    cx0, cy0, cx1, cy1 = m["kutu"]
    if m["eks"] == 1:                                                            # ön ya da arka cephe: cumbanın mahyası y boyunca
        ca, cb = sorted((m["dis"], m["dis"] + m["ic"] * m["birlesim"])), [cx0, cx1]
    else:
        ca, cb = sorted((m["dis"], m["dis"] + m["ic"] * m["birlesim"])), [cy0, cy1]
    cbm = (cb[0] + cb[1]) / 2
    mp, mq = m["mahya"]["p"], m["mahya"]["q"]
    cumba = {"ad": "cumba", "rol": "cumba", "capraz": True, "cephe": m["cephe"], "dis_uc": round(m["dis"], 2), "a": [round(v, 2) for v in ca],
             "b": [round(v, 2) for v in cb], "aciklik_cm": round(cb[1] - cb[0], 2), "boy_cm": round(m["birlesim"], 2),
             "mahya": [[round(v, 4) for v in mp], [round(v, 4) for v in mq]],
             "mahya_kotu": round(zs + eg * (cbm - cb[0] + s), 2),
             "makas_ust_boy_cm": round((cbm - cb[0] + s) * math.sqrt(1 + eg * eg), 2), "makas_yuksekligi_cm": round(top + eg * (cbm - cb[0] + s), 2),
             "makaslar": [{"konum": round(x, 2), "rol": "bas" if i == 0 else "orta", "uzaklik": round(u, 2), **({} if i == 0 else {"ana_ustunde": True})}
                          for i, (x, u) in enumerate(zip(m["konum"], m["uzaklik"]))],
             "makas_yeri": f"kalkan duvarının ekseninden {MOD:g} arayla, derelerin birleştiği yere kadar (D-47)", "komsu": "ana çatı"}
    return {**t, "capraz": True, "parcalar": [ana, cumba], "uyarilar": uyarilar}


def yavru_acikligi(t: dict, q: dict, konum: float) -> tuple[float, float]:
    """Ana çatının üstündeki cumba makasının iki ucu (dereler arası, makasın uzandığı eksende): `konum`daki kesitte cumba yüzlerinin planı."""
    cumba_yuz = unary_union([Polygon(d["plan"]) for d in t["duzlemler"] if not d["ad"].startswith("ana ")])
    mahya_y = abs(q["mahya"][0][0] - q["mahya"][1][0]) < TOL                     # cumbanın mahyası y boyunca: makas x boyunca
    big = 1e5
    hat = LineString([(-big, konum), (big, konum)] if mahya_y else [(konum, -big), (konum, big)])
    kes = cumba_yuz.intersection(hat)
    if kes.is_empty:
        raise PrefabrikCatiHatasi(f"cumba makası {konum:g}: cumbanın yüzlerini kesmiyor")
    xs = [c[0 if mahya_y else 1] for g in getattr(kes, "geoms", [kes]) for c in g.coords]
    return min(xs), max(xs)
