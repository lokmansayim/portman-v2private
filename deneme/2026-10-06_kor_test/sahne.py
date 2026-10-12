#!/usr/bin/env python3
"""Yapının dıştan görünen yüzeyleri (3B): görünüşler bu yüzeylerden çizilir.

Girdi: `yapi.kur()` ve `cati_genel.cati_kur()` sonuçları. Çıktı: yüzey listesi. Her yüzey bir düzlem çokgendir:
    {"kose": [(x, y, z), ...], "tur": duvar | pencere | kapi | gecit | kalkan | cati | alin | kiris | kolon | baca | korkuluk, "ad": ..., "oncelik": n}
Çokgenin köşeleri dışarıdan bakınca saat yönünün tersinedir (normal dışarı bakar).
"""
from __future__ import annotations

import math

from shapely.geometry import Point, box
from shapely.ops import unary_union

from yapi import NORMAL, _kenar, _yukseklik

DIS_SINIFLAR = ("dis", "veranda")


def _dikdortgen(eks: str, sabit: float, lo: float, hi: float, z0a: float, z1a: float, z0b: float | None = None, z1b: float | None = None, n=(0, 0)):
    """Düşey düzlemde dörtgen: eksen 'x' ise y = sabit düzleminde, x: lo..hi. Köşeler normal n'ye göre dışarıdan saat yönünün tersine."""
    z0b = z0a if z0b is None else z0b
    z1b = z1a if z1b is None else z1b
    if eks == "x":
        k = [(lo, sabit, z0a), (hi, sabit, z0b), (hi, sabit, z1b), (lo, sabit, z1a)]
        ters = n[1] > 0                                # +y'ye bakan yüzde x soldan sağa azalır
    else:
        k = [(sabit, lo, z0a), (sabit, hi, z0b), (sabit, hi, z1b), (sabit, lo, z1a)]
        ters = n[0] < 0
    return k[::-1] if ters else k


def normal(kose) -> tuple[float, float, float]:
    nx = ny = nz = 0.0
    for (x0, y0, z0), (x1, y1, z1) in zip(kose, kose[1:] + kose[:1]):
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    b = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / b, ny / b, nz / b


def sahne_kur(y: dict, c: dict) -> list[dict]:
    t = y["tanim"]
    kap = t["yuz_kaplamalari"]
    adli = y["adli"]
    S: list[dict] = []

    def ekle(kose, tur, ad="", oncelik=0, **ek):
        S.append(dict(kose=[tuple(map(float, p)) for p in kose], tur=tur, ad=ad, oncelik=oncelik, **ek))

    # ── dış duvar yüzleri ve açıklıkları ─────────────────────────────────────
    for f in y["yuzler"]:
        if f["bolge_sinifi"] not in DIS_SINIFLAR:
            continue
        d = adli[f["duvar"]]
        eks, sabit0, a0, a1 = _kenar(d["kutu"], f["kenar"])
        n = NORMAL[f["kenar"]]
        kal = kap[f["kaplama"]]["kalinlik"]
        sabit = sabit0 + kal * (n[1] if eks == "x" else n[0])
        tur = {"korkuluk": "korkuluk", "kolon": "kolon"}.get(d["sinif"], "duvar")
        for lo, hi in f["araliklar"]:
            if f["uzun"]:
                h0, h1 = _yukseklik(d, min(max(lo, d["_bas"]), d["_son"])), _yukseklik(d, min(max(hi, d["_bas"]), d["_son"]))
            else:
                uc = d["_bas"] if f["kenar"] in ("sol", "alt") else d["_son"]
                h0 = h1 = _yukseklik(d, uc)
            ekle(_dikdortgen(eks, sabit, lo, hi, 0.0, h0, 0.0, h1, n), tur, d["ad"], 0, bolge=f["bolge"])
        if not f["uzun"]:
            continue
        for ac in y["acikliklar"]:
            if ac["duvar"] != d["ad"]:
                continue
            for lo, hi in f["araliklar"]:
                b0, b1 = max(lo, ac["a0"]), min(hi, ac["a1"])
                if b1 - b0 < 1:
                    continue
                on = 0.4
                s2 = sabit + on * (n[1] if eks == "x" else n[0])
                tur_a = {"pencere": "pencere", "dis_kapi": "kapi", "ic_kapi": "kapi", "gecit": "gecit"}[ac["tur"]]
                ekle(_dikdortgen(eks, s2, b0, b1, ac["z0"], ac["z1"], None, None, n), tur_a, ac["ad"], 2, en=ac["en"], bolge=f["bolge"])

    # ── kirişler (veranda): açıkta kalan kısımlarının yan yüzleri ────────────
    kd = kap["dis"]["kalinlik"]
    izler = []
    for kr in t.get("kirisler", []):
        if kr.get("bolge") != "veranda":
            continue
        x0, y0, x1, y1 = kr["kutu"]
        yatay = (x1 - x0) >= (y1 - y0)
        for lo, hi in kr["acik"]:
            izler.append((box(lo, y0, hi, y1) if yatay else box(x0, lo, x1, hi), kr["alt"], kr["ust"]))
    if izler:
        g = unary_union([i[0] for i in izler]).buffer(kd, join_style=2)
        z0, z1 = min(i[1] for i in izler), max(i[2] for i in izler)
        for cokgen in (g.geoms if g.geom_type == "MultiPolygon" else [g]):
            halka = list(cokgen.exterior.coords)
            if not cokgen.exterior.is_ccw:
                halka = halka[::-1]
            for p, q in zip(halka, halka[1:]):          # saat yönünün tersine halkada dış normal, kenarın sağındadır
                ekle([(p[0], p[1], z0), (q[0], q[1], z0), (q[0], q[1], z1), (p[0], p[1], z1)], "kiris", "veranda kirişi", 1)

    # ── kalkanlar ────────────────────────────────────────────────────────────
    for k in c["kalkanlar"]:
        if len(k["kose"]) < 3:
            continue
        dis_yon = {"kuzey": -1.0, "guney": 1.0, "dogu": -1.0, "bati": 1.0}[k["ic"]]      # kalkan, çatının olduğu yanın tersine bakar
        if k["eksen"] == "y":
            kose = [(s, k["konum"], z) for s, z in k["kose"]]
            hedef = (0.0, dis_yon, 0.0)
        else:
            kose = [(k["konum"], s, z) for s, z in k["kose"]]
            hedef = (dis_yon, 0.0, 0.0)
        nn = normal(kose)
        if nn[0] * hedef[0] + nn[1] * hedef[1] < 0:
            kose = kose[::-1]
        ekle(kose, "kalkan", k["ad"], 0)

    # ── çatı: üst yüz ve serbest kenarlarda alın bandı ───────────────────────
    ct = t["cati"]
    for dz in c["duzlemler"]:
        ust = dz.get("ust_pay", ct.get("ust_pay", 7.0))          # makas üstünden kaplamanın üstüne (aşık + panel)
        alt = dz.get("alt_pay", ct.get("topuk", 10.0))           # serbest kenarda bandın makas üstünden aşağı inişi
        ustk = [(p[0], p[1], dz["kot"](p) + ust) for p in dz["plan"]]
        if normal(ustk)[2] < 0:
            ustk = ustk[::-1]
        ekle(ustk, "cati", dz["ad"], 0, egim=dz["egim"])
        for e in c["kenarlar"]:
            if dz["ad"] != e["duzlemler"][0] or e["tur"] not in ("sacak", "alin", "ust"):
                continue
            p, q = e["p"], e["q"]
            zp, zq = dz["kot"](p), dz["kot"](q)
            kose = [(p[0], p[1], zp - alt), (q[0], q[1], zq - alt), (q[0], q[1], zq + ust), (p[0], p[1], zp + ust)]
            # dışarı bakmalı: düzlemin içine doğru olan yönün tersine
            ic = dz["cokgen"].representative_point()
            nn = normal(kose)
            mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
            if nn[0] * (ic.x - mx) + nn[1] * (ic.y - my) > 0:
                kose = kose[::-1]
            ekle(kose, "alin", f"{dz['ad']} {e['tur']}", 1)

    # ── baca: çatının üstünde kalan kısmı ────────────────────────────────────
    for d in y["duvarlar"]:
        if d["sinif"] != "baca" or not d.get("ust_kot"):
            continue
        x0, y0, x1, y1 = d["kutu"]
        x0, y0, x1, y1 = x0 - 1.25, y0 - 1.25, x1 + 1.25, y1 + 1.25          # dış kaplama (Boardex)
        def cati_kotu(px, py):
            en = None
            for dz in c["duzlemler"]:
                if dz["cokgen"].buffer(0.01).contains(Point(px, py)):
                    z = dz["kot"]((px, py)) + dz.get("ust_pay", ct.get("ust_pay", 7.0))
                    en = z if en is None else max(en, z)
            return en or 0.0
        zt = d["ust_kot"]
        for kn, (pa, pb) in {"alt": ((x0, y0), (x1, y0)), "sag": ((x1, y0), (x1, y1)), "ust": ((x1, y1), (x0, y1)), "sol": ((x0, y1), (x0, y0))}.items():
            ekle([(pa[0], pa[1], cati_kotu(*pa)), (pb[0], pb[1], cati_kotu(*pb)), (pb[0], pb[1], zt), (pa[0], pa[1], zt)], "baca", d["ad"], 1)
        ekle([(x0, y0, zt), (x1, y0, zt), (x1, y1, zt), (x0, y1, zt)], "baca", d["ad"], 1)
    for s in S:
        s["normal"] = normal(s["kose"])
    return S


BAKIS = {   # taraf: (yatay eksenin plan yönü, bakış yönü)
    "on": ((1.0, 0.0), (0.0, 1.0)),          # güneyden kuzeye bakış
    "arka": ((-1.0, 0.0), (0.0, -1.0)),
    "sol": ((0.0, -1.0), (1.0, 0.0)),        # batıdan doğuya bakış
    "sag": ((0.0, 1.0), (-1.0, 0.0)),
}


def izdusum(S: list[dict], taraf: str) -> list[dict]:
    """Görünüş: bakışa dönük yüzeyler, uzaktan yakına sıralı; köşeler (yatay, kot)."""
    (hx, hy), (vx, vy) = BAKIS[taraf]
    cik = []
    for s in S:
        n = s["normal"]
        if -(n[0] * vx + n[1] * vy) < 0.02:           # bakışa dönük değil (ya da yandan)
            continue
        k2 = [(p[0] * hx + p[1] * hy, p[2]) for p in s["kose"]]
        der = [p[0] * vx + p[1] * vy for p in s["kose"]]
        cik.append(dict(s, k2=k2, derinlik=sum(der) / len(der), yakin=min(der)))
    cik.sort(key=lambda s: (-s["derinlik"], s["oncelik"]))
    return cik
