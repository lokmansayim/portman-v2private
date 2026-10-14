#!/usr/bin/env python3
"""İE-14 · plan şemasından Yapı Tanımı 0.5: duvar kutuları, mahaller, kapı ve pencere konumları, çatı düzlemleri koddan.

Girdi: `beyin/plan_sema.PlanTaslagi`'nın sözlüğü (LLM'in ya da elle yazılmış plan). Mahaller dış yüze göre (köken binanın güneybatı
dış köşesi, +x doğu, +y kuzey, cm) 5 cm ızgarada dikdörtgen birleşimidir. 14a sınırları: dış ölçü dikdörtgendir; en çok bir veranda,
tek dikdörtgen, ya bir cephe boyunca tam uzunlukta şerit ya da bir köşede. Veranda çatının altındaysa (kolonlu) çatı bütün dikdörtgeni
örter; pergola ya da açık veranda yalnız şerit olabilir (çatı kapalı dikdörtgeni örter; L çatı 14b). Çatı beşik ya da kırma.

Kurallar (Ç8801 tanım üretecinin formülleri, `deneme/2026-10-10_c8801/tanim/c8801_tanim_uret.py`; KT-02'nin kırması ve kolonları):
- Dış duvar: dış yüz ± kaplama 1,25 ± karkas 8. Yatay dış duvar dış köşeyi örter, iç (girinti) köşede düşey duvarın dış yüzünde
  biter; düşey dış duvar dış köşede yatay duvarın karkasından sonra başlar, girinti köşesini örter (Ç8801 DG/DKB gibi).
- İç duvar: iki ayrı mahalin ortak kenarının ekseninde ±4. Düşey duvar köşeyi (L) örter, T'de yatay duvarın yüzünde durur;
  yatay duvar düşey duvarların yüzünde durur ve kesişmede (+) bölünür; dış duvara karkasın iç yüzünde değer. Duvarlar üst üste binmez.
- Kapı: ortak kenarın (dış kapıda cephe parçasının) içinde, birleşimlerden pay bırakarak; dış kapı 95 × 210, iç kapı 90 × 214.
  İç kapı odaya açılır (öncelik banyo, yatak odası, mutfak, depo, salon, hol); konum iki uç ve orta arasından, yayı başka kapının
  yayına (15 cm payla) binmeyen ilki.
- Pencere: mahalin cephe parçasında eşit aralıkla (aynı parçadaki dış kapıyla birlikte), üst kot 200 (kat 270 − lento 70).
- Çatı: saçak 30, topuk 10, saçak kotu 280, eğim %33 (verilmezse), panel 8; beşik 2 düzlem + 2 kalkan, kırma 4 düzlem.
- Veranda kolonu 30 × 8 (KT-02), boştaki köşede ve açık kenarlarda en çok 400 cm arayla; açık kenarlarda kiriş (alt 240, üst 270).
  Çatı altındaki veranda yalnız kırma çatıyla (beşikte kalkan açık kenara otururdu; denetçi reddeder).

Hesapta LLM yoktur: aynı plan aynı tanımı verir. Geçersiz plan `PlanHatasi` (ihlal listesi) verir; geometri denetimi ayrıca
`yapi.kur` ve açıklık denetimiyle yapılır (`beyin/plan_denetim.py`).

Kullanım: python -m motor.genel.plan_derle plan.json tanim.json [--kod YENI]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

IZGARA = 5
K = 1.25            # kaplama
D = 8.0             # karkas
Y = D / 2           # iç duvarın yarı kalınlığı
SACAK, TOPUK, DUVAR_USTU, PANEL = 30.0, 10, 270, 8.0
SACAK_KOTU = DUVAR_USTU + TOPUK
EGIM = 0.33
UST_KOT = 200       # pencere üstü: kat 270 − lento 70
PAY_KOSE = K + D + 10       # açıklığın dış köşeden payı (dış duvarın iç yüzünden 10)
PAY_BIRLESIM = Y + 10       # iç duvar birleşiminden pay
DIS_KAPI = (95, 210)
IC_KAPI = (90, 214)
KOLON = (30.0, D)           # veranda kolonu: kenar boyunca 30, derinlik karkas (KT-02)
KOLON_ARALIK = 400.0
ACILIM_ONCELIK = ["banyo", "yatak_odasi", "mutfak", "depo", "salon", "hol"]
YAY_PAYI = 15.0           # kapı yayları arasında boşluk (paftadaki kapı genişliği yazısı başka yayın altında kalmasın)
BOS, VERANDA = -1, -2
CEPHE_ADI = {"G": "güney", "K": "kuzey", "B": "batı", "D": "doğu"}
ICERI = {"G": "ust", "K": "alt", "B": "sag", "D": "sol"}     # cepheden içeri açılım


class PlanHatasi(Exception):
    def __init__(self, ihlaller: list[str]):
        super().__init__("; ".join(ihlaller))
        self.ihlaller = ihlaller


def r2(v: float) -> float:
    return round(float(v), 2)


def _kosuler(dizi) -> list[tuple[int, int]]:
    """Doğru dizisindeki ardışık True koşuları: [(bas, son)) yarı açık."""
    out, bas = [], None
    for i, v in enumerate(list(dizi) + [False]):
        if v and bas is None:
            bas = i
        elif not v and bas is not None:
            out.append((bas, i))
            bas = None
    return out


# ── ızgara ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
class Izgara:
    """Bütün dış dikdörtgen 5 cm hücrelerde: mahal sırası (≥ 0), veranda (−2), boş (−1)."""

    def __init__(self, W: int, H: int):
        self.W, self.H = W, H
        self.nx, self.ny = W // IZGARA, H // IZGARA
        self.lab = np.full((self.nx, self.ny), BOS, dtype=int)

    def kapali(self, i: int, j: int) -> bool:
        return 0 <= i < self.nx and 0 <= j < self.ny and self.lab[i, j] >= 0

    def deger(self, i: int, j: int) -> int:
        return int(self.lab[i, j]) if 0 <= i < self.nx and 0 <= j < self.ny else BOS


def _yerlestir(p: dict) -> tuple[Izgara, list[dict], dict | None, list[str]]:
    W, H = int(p["dis_olcu"]["en"]), int(p["dis_olcu"]["boy"])
    iz = Izgara(W, H)
    hata: list[str] = []
    ver = [m for m in p["mahaller"] if m["islev"] == "veranda"]
    odalar = [m for m in p["mahaller"] if m["islev"] != "veranda"]
    if len(ver) > 1:
        hata.append("en çok bir veranda olabilir (14a)")

    def hucreler(m, r):
        if len(r) != 4:
            hata.append(f"{m['ad']}: dikdörtgen dört sayı olmalı ({r})")
            return None
        x0, y0, x1, y1 = (int(v) for v in r)
        if any(v % IZGARA for v in (x0, y0, x1, y1)):
            hata.append(f"{m['ad']}: köşeler {IZGARA} cm ızgarada olmalı ({r})")
            return None
        if x1 <= x0 or y1 <= y0:
            hata.append(f"{m['ad']}: dikdörtgen ters ya da boş ({r})")
            return None
        if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
            hata.append(f"{m['ad']}: {r} dış ölçünün ({W} × {H}) dışına taşıyor")
            return None
        return x0 // IZGARA, y0 // IZGARA, x1 // IZGARA, y1 // IZGARA

    v = None
    if ver:
        v = ver[0]
        if len(v["dikdortgenler"]) != 1:
            hata.append(f"{v['ad']} tek dikdörtgen olmalı")
        else:
            h = hucreler(v, v["dikdortgenler"][0])
            if h:
                a, b, c, d = h
                x0, y0, x1, y1 = (int(t) for t in v["dikdortgenler"][0])
                kenar = [x0 == 0, y0 == 0, x1 == W, y1 == H]
                serit = (x0 == 0 and x1 == W and (y0 == 0) != (y1 == H)) or (y0 == 0 and y1 == H and (x0 == 0) != (x1 == W))
                kose = sum(kenar) == 2 and not ((x0 == 0 and x1 == W) or (y0 == 0 and y1 == H))
                if not (serit or kose):
                    hata.append(f"{v['ad']} bir cephe boyunca tam uzunlukta şerit ya da bir köşede dikdörtgen olmalı (14a); verilen "
                                f"{[x0, y0, x1, y1]}, dış ölçü {W} × {H}")
                elif kose and (v.get("ortu") or "cati") != "cati":
                    hata.append(f"{v['ad']}: köşe veranda çatının altında olmalı (ortu 'cati'; pergolalı ya da açık köşe veranda 14b)")
                iz.lab[a:c, b:d] = VERANDA
    for i, m in enumerate(odalar):
        for r in m["dikdortgenler"]:
            h = hucreler(m, r)
            if not h:
                continue
            a, b, c, d = h
            dolu = iz.lab[a:c, b:d]
            ust = set(dolu[dolu >= 0].tolist()) - {i}
            if ust:
                hata.append(f"{m['ad']} ile {', '.join(odalar[j]['ad'] for j in sorted(ust))} örtüşüyor")
            if (dolu == VERANDA).any():
                hata.append(f"{m['ad']} veranda ile örtüşüyor")
            iz.lab[a:c, b:d] = i
    bos = int((iz.lab == BOS).sum())
    if bos and not hata:
        ii, jj = np.argwhere(iz.lab == BOS)[0]
        hata.append(f"dış ölçünün içinde mahale ait olmayan boşluk var: {bos * IZGARA * IZGARA / 1e4:.2f} m² "
                    f"(ör. x={ii * IZGARA}, y={jj * IZGARA} çevresi); mahaller ve veranda dış dikdörtgeni boşluksuz doldurmalı")
    return iz, odalar, v, hata


# ── duvarlar ───────────────────────────────────────────────────────────────────────────────────────────────────────────
def _dis_kosular(iz: Izgara) -> list[dict]:
    """Kapalı bölgenin dış sınır koşuları. Her biri: {cephe, eksen ('x' yatay | 'y' düşey), c (sabit), a, b (uzun eksen)}."""
    out = []
    for k in range(iz.ny + 1):
        alt = [iz.kapali(i, k - 1) for i in range(iz.nx)]
        ust = [iz.kapali(i, k) for i in range(iz.nx)]
        for a, b in _kosuler([u and not al for u, al in zip(ust, alt)]):
            out.append({"cephe": "G", "eksen": "x", "c": k * IZGARA, "a": a * IZGARA, "b": b * IZGARA})
        for a, b in _kosuler([al and not u for u, al in zip(ust, alt)]):
            out.append({"cephe": "K", "eksen": "x", "c": k * IZGARA, "a": a * IZGARA, "b": b * IZGARA})
    for k in range(iz.nx + 1):
        sol = [iz.kapali(k - 1, j) for j in range(iz.ny)]
        sag = [iz.kapali(k, j) for j in range(iz.ny)]
        for a, b in _kosuler([s and not so for s, so in zip(sag, sol)]):
            out.append({"cephe": "B", "eksen": "y", "c": k * IZGARA, "a": a * IZGARA, "b": b * IZGARA})
        for a, b in _kosuler([so and not s for s, so in zip(sag, sol)]):
            out.append({"cephe": "D", "eksen": "y", "c": k * IZGARA, "a": a * IZGARA, "b": b * IZGARA})
    return out


def _dis_duvar(iz: Izgara, k: dict) -> list[float]:
    """Dış sınır koşusunun karkas kutusu. Uçlar: dış köşe / girinti köşesi (sınıf başı açıklama)."""
    c, a, b, ce = k["c"], k["a"], k["b"], k["cephe"]
    ic = {"G": +1, "K": -1, "B": +1, "D": -1}[ce]                 # içerisi: G → yukarı, K → aşağı, B → sağ, D → sol
    if k["eksen"] == "x":
        j = c // IZGARA if ic > 0 else c // IZGARA - 1              # içerideki hücre satırı
        girinti_a = iz.kapali(a // IZGARA - 1, j)
        girinti_b = iz.kapali(b // IZGARA, j)
        x0 = a - K if girinti_a else a + K
        x1 = b + K if girinti_b else b - K
        y0, y1 = (c + K, c + K + D) if ic > 0 else (c - K - D, c - K)
        return [x0, y0, x1, y1]
    i = c // IZGARA if ic > 0 else c // IZGARA - 1
    girinti_a = iz.kapali(i, a // IZGARA - 1)
    girinti_b = iz.kapali(i, b // IZGARA)
    y0 = a - K - D if girinti_a else a + K + D
    y1 = b + K + D if girinti_b else b - K - D
    x0, x1 = (c + K, c + K + D) if ic > 0 else (c - K - D, c - K)
    return [x0, y0, x1, y1]


def _duvarlar(iz: Izgara) -> tuple[list[dict], dict[str, list[tuple[dict, str]]]]:
    lab = iz.lab
    dikey, yatay = [], []
    for k in range(1, iz.nx):
        sol, sag = lab[k - 1, :], lab[k, :]
        for a, b in _kosuler((sol >= 0) & (sag >= 0) & (sol != sag)):
            dikey.append((k * IZGARA, a * IZGARA, b * IZGARA))
    for k in range(1, iz.ny):
        alt, ust = lab[:, k - 1], lab[:, k]
        for a, b in _kosuler((alt >= 0) & (ust >= 0) & (alt != ust)):
            yatay.append((k * IZGARA, a * IZGARA, b * IZGARA))

    def yatay_gecer(y, x):
        return any(yy == y and xa < x < xb for yy, xa, xb in yatay)

    def dikey_gecer(x, y):
        return any(xx == x and ya < y < yb for xx, ya, yb in dikey)

    duvarlar = []
    dis_ad: dict[str, list[tuple[dict, str]]] = {}
    sayac = {"G": 0, "K": 0, "B": 0, "D": 0}
    for k in sorted(_dis_kosular(iz), key=lambda k: ("GKBD".index(k["cephe"]), k["c"], k["a"])):
        sayac[k["cephe"]] += 1
        ad = f"D{k['cephe']}" + (str(sayac[k["cephe"]]) if sayac[k["cephe"]] > 1 else "")
        duvarlar.append({"ad": ad, "sinif": "dis", "kutu": [r2(v) for v in _dis_duvar(iz, k)], "yukseklik": DUVAR_USTU,
                         "not": f"{CEPHE_ADI[k['cephe']]} dış duvar"})
        dis_ad.setdefault(k["cephe"], []).append((k, ad))
    ic = []
    for x, ya, yb in sorted(dikey):
        i0, i1 = x // IZGARA - 1, x // IZGARA
        if not (iz.kapali(i0, ya // IZGARA - 1) and iz.kapali(i1, ya // IZGARA - 1)):
            a = ya + K + D                                         # dış duvara değer: karkasın iç yüzünde
        else:
            a = ya + Y if yatay_gecer(ya, x) else ya - Y
        if not (iz.kapali(i0, yb // IZGARA) and iz.kapali(i1, yb // IZGARA)):
            b = yb - K - D
        else:
            b = yb - Y if yatay_gecer(yb, x) else yb + Y
        ic.append(("y", x, a, b))
    for y, xa, xb in sorted(yatay):
        j0, j1 = y // IZGARA - 1, y // IZGARA
        a = xa + K + D if not (iz.kapali(xa // IZGARA - 1, j0) and iz.kapali(xa // IZGARA - 1, j1)) else xa + Y
        b = xb - K - D if not (iz.kapali(xb // IZGARA, j0) and iz.kapali(xb // IZGARA, j1)) else xb - Y
        kes = sorted(x for e, x, da, db in ic if e == "y" and xa < x < xb and da <= y - Y + 1e-6 and db >= y + Y - 1e-6)
        sinir = [a] + [v for x in kes for v in (x - Y, x + Y)] + [b]
        for s0, s1 in zip(sinir[::2], sinir[1::2]):
            if s1 - s0 > 1e-6:
                ic.append(("x", y, s0, s1))
    for n, (e, c, a, b) in enumerate(ic, 1):
        kutu = [c - Y, a, c + Y, b] if e == "y" else [a, c - Y, b, c + Y]
        duvarlar.append({"ad": f"I{n}", "sinif": "ic", "kutu": [r2(v) for v in kutu], "yukseklik": DUVAR_USTU})
    _ = dikey_gecer
    return duvarlar, dis_ad


# ── açıklıklar ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def _cephe_parcalari(iz: Izgara, dis_ad: dict, i: int) -> dict[str, list[tuple[float, float, str, float, float]]]:
    """Mahalin (sıra i) cephe parçaları: cephe → [(bas, son, duvar adı, koşu başı, koşu sonu)] uzun eksen boyunca."""
    out: dict[str, list] = {}
    for ce, liste in dis_ad.items():
        for k, ad in liste:
            if k["eksen"] == "x":
                j = k["c"] // IZGARA if ce == "G" else k["c"] // IZGARA - 1
                seri = [iz.deger(x, j) == i for x in range(k["a"] // IZGARA, k["b"] // IZGARA)]
            else:
                ii = k["c"] // IZGARA if ce == "B" else k["c"] // IZGARA - 1
                seri = [iz.deger(ii, y) == i for y in range(k["a"] // IZGARA, k["b"] // IZGARA)]
            for a, b in _kosuler(seri):
                out.setdefault(ce, []).append((k["a"] + a * IZGARA, k["a"] + b * IZGARA, ad, k["a"], k["b"]))
    return out


def _ortak_parcalar(iz: Izgara, i: int, j: int) -> list[tuple[str, float, float, float, int]]:
    """i ve j mahallerinin ortak kenar parçaları: (eksen yönü, sabit koordinat, bas, son, j'nin yanı +1/−1)."""
    lab = iz.lab
    out = []
    for k in range(1, iz.nx):
        sol, sag = lab[k - 1, :], lab[k, :]
        for a, b in _kosuler((sol == i) & (sag == j)):
            out.append(("y", k * IZGARA, a * IZGARA, b * IZGARA, +1))
        for a, b in _kosuler((sol == j) & (sag == i)):
            out.append(("y", k * IZGARA, a * IZGARA, b * IZGARA, -1))
    for k in range(1, iz.ny):
        alt, ust = lab[:, k - 1], lab[:, k]
        for a, b in _kosuler((alt == i) & (ust == j)):
            out.append(("x", k * IZGARA, a * IZGARA, b * IZGARA, +1))
        for a, b in _kosuler((alt == j) & (ust == i)):
            out.append(("x", k * IZGARA, a * IZGARA, b * IZGARA, -1))
    return out


def _dagit(s0: float, s1: float, enler: list[float]) -> list[float] | None:
    """[s0, s1] aralığına sırayla açıklık başları: eşit dilimlerin ortası; dilim dar ise 20 cm aralıkla yan yana; sığmazsa None."""
    n = len(enler)
    L = s1 - s0
    if sum(enler) + 20 * (n - 1) > L + 1e-6:
        return None
    dilim = L / n
    if any(e > dilim + 1e-6 for e in enler):
        top = sum(enler) + 20 * (n - 1)
        x = s0 + (L - top) / 2
        out = []
        for e in enler:
            out.append(x)
            x += e + 20
        return out
    return [s0 + dilim * (k + 0.5) - e / 2 for k, e in enumerate(enler)]


def _acikliklar(p: dict, iz: Izgara, odalar: list[dict], duvarlar: list[dict], dis_ad: dict, ver: dict | None) -> tuple[list[dict], list[str]]:
    sira = {m["ad"]: i for i, m in enumerate(odalar)}
    ver_ad = ver["ad"] if ver else None
    hata: list[str] = []
    parca_ogeleri: dict[tuple, list[dict]] = {}       # (cephe, bas, son, duvar, koşu başı, koşu sonu) → öğeler
    iceri_kapilar = []
    girisi = False

    def veranda_cephesi(parcalar: dict) -> list[str]:
        """Mahalin verandaya bakan cepheleri (cephe parçasının önündeki hücre veranda)."""
        out = []
        for ce, liste in parcalar.items():
            for s0, s1, ad, _, _ in liste:
                k = next(k for k, a in dis_ad[ce] if a == ad)
                orta = (s0 + s1) / 2 // IZGARA
                if k["eksen"] == "x":
                    j = k["c"] // IZGARA - 1 if ce == "G" else k["c"] // IZGARA
                    if iz.deger(int(orta), j) == VERANDA:
                        out.append(ce)
                else:
                    ii = k["c"] // IZGARA - 1 if ce == "B" else k["c"] // IZGARA
                    if iz.deger(ii, int(orta)) == VERANDA:
                        out.append(ce)
        return out

    for kp in p["kapilar"]:
        a, b = (list(kp["arasinda"]) + ["", ""])[:2]
        a, b = ("dis" if x == ver_ad else x for x in (a, b))
        if b == "dis" and a != "dis":
            a, b = b, a
        if a == "dis":
            if b not in sira:
                hata.append(f"kapı: '{b}' adlı mahal yok")
                continue
            parcalar = _cephe_parcalari(iz, dis_ad, sira[b])
            uzun = sorted(parcalar, key=lambda c: -max((s1 - s0 for s0, s1, *_ in parcalar[c]), default=0))
            cepheler = [kp["cephe"]] if kp.get("cephe") else veranda_cephesi(parcalar) + uzun
            cepheler = [c for c in cepheler if parcalar.get(c)]
            if not cepheler:
                hata.append(f"dış kapı: {b} " + (f"{CEPHE_ADI[kp['cephe']]} cephesine değmiyor" if kp.get("cephe") else "hiçbir cepheye değmiyor"))
                continue
            c = cepheler[0]
            pc = max(parcalar[c], key=lambda r: r[1] - r[0])
            parca_ogeleri.setdefault((c, *pc), []).insert(0, {"tur": "dis_kapi", "mahal": b, "en": DIS_KAPI[0], "yuk": DIS_KAPI[1],
                                                              "giris": not girisi})
            girisi = True
        else:
            if a not in sira or b not in sira:
                hata.append(f"kapı: {', '.join(repr(x) for x in (a, b) if x not in sira)} adlı mahal yok")
                continue
            ortak = _ortak_parcalar(iz, sira[a], sira[b])
            if not ortak:
                hata.append(f"kapı: {a} ile {b} komşu değil (ortak duvarları yok)")
                continue
            iceri_kapilar.append((a, b, max(ortak, key=lambda o: o[3] - o[2])))
    for pc in p["pencereler"]:
        if pc["mahal"] not in sira:
            hata.append(f"pencere: '{pc['mahal']}' adlı mahal yok")
            continue
        parcalar = _cephe_parcalari(iz, dis_ad, sira[pc["mahal"]]).get(pc["cephe"], [])
        if not parcalar:
            hata.append(f"pencere: {pc['mahal']} {CEPHE_ADI[pc['cephe']]} cephesine değmiyor")
            continue
        parca = max(parcalar, key=lambda r: r[1] - r[0])
        en, yuk = (int(v) for v in pc["olcu"].split("x"))
        for _ in range(int(pc.get("adet") or 1)):
            parca_ogeleri.setdefault((pc["cephe"], *parca), []).append({"tur": "pencere", "mahal": pc["mahal"], "en": en, "yuk": yuk})

    out: list[dict] = []
    np_, nk = 0, 0
    for (c, s0, s1, duvar, k0, k1), ogeler in sorted(parca_ogeleri.items(), key=lambda kv: ("GKBD".index(kv[0][0]), kv[0][3], kv[0][1])):
        u0 = s0 + (PAY_KOSE if abs(s0 - k0) < 1e-6 else PAY_BIRLESIM)
        u1 = s1 - (PAY_KOSE if abs(s1 - k1) < 1e-6 else PAY_BIRLESIM)
        baslar = _dagit(u0, u1, [o["en"] for o in ogeler]) if u1 > u0 else None
        if baslar is None:
            hata.append(f"{ogeler[0]['mahal']} {CEPHE_ADI[c]} cephesine {len(ogeler)} açıklık sığmıyor "
                        f"({' + '.join(str(o['en']) for o in ogeler)} cm ve aralar, kullanılabilir {max(0, u1 - u0):.0f} cm)")
            continue
        for o, bas in zip(ogeler, baslar):
            if o["tur"] == "pencere":
                np_ += 1
                out.append({"ad": f"P{np_}", "tur": "pencere", "duvar": duvar, "bas": r2(round(bas * 2) / 2), "en": o["en"], "yuk": o["yuk"],
                            "alt": UST_KOT - o["yuk"], "etiket": f"{o['en']}/{o['yuk']}", "mahal": o["mahal"], "acilim": "ust"})
            else:
                nk += 1
                out.append({"ad": f"K{nk}", "tur": "dis_kapi", "duvar": duvar, "bas": r2(round(bas * 2) / 2), "en": o["en"], "yuk": o["yuk"],
                            **({"giris": True} if o["giris"] else {}), "mentese": "son", "acilim": ICERI[c], "not": o["mahal"]})
    islev = {m["ad"]: m["islev"] for m in odalar}
    for a, b, (e, sabit, s0, s1, yan) in iceri_kapilar:
        # kapı odaya açılır, hole açılmaz: açılım önceliği yüksek olan mahale (banyo, yatak odası, mutfak, depo, salon, hol)
        if ACILIM_ONCELIK.index(islev[a]) < ACILIM_ONCELIK.index(islev[b]):
            a, b, yan = b, a, -yan
        u0, u1 = s0 + PAY_BIRLESIM, s1 - PAY_BIRLESIM
        # ortak kenarın ucu dış duvara değiyorsa köşe payı
        if e == "x":
            j0, j1 = sabit // IZGARA - 1, sabit // IZGARA
            if not iz.kapali(s0 // IZGARA - 1, j0) or not iz.kapali(s0 // IZGARA - 1, j1):
                u0 = s0 + PAY_KOSE
            if not iz.kapali(s1 // IZGARA, j0) or not iz.kapali(s1 // IZGARA, j1):
                u1 = s1 - PAY_KOSE
        else:
            i0, i1 = sabit // IZGARA - 1, sabit // IZGARA
            if not iz.kapali(i0, s0 // IZGARA - 1) or not iz.kapali(i1, s0 // IZGARA - 1):
                u0 = s0 + PAY_KOSE
            if not iz.kapali(i0, s1 // IZGARA) or not iz.kapali(i1, s1 // IZGARA):
                u1 = s1 - PAY_KOSE
        en = IC_KAPI[0]
        if u1 - u0 < en - 1e-6:
            hata.append(f"kapı: {a} ile {b} arasındaki ortak duvar kapıya yetmiyor ({max(0, u1 - u0):.0f} cm kullanılabilir, kapı {en})")
            continue
        acilim = ("sag" if yan > 0 else "sol") if e == "y" else ("ust" if yan > 0 else "alt")
        from shapely.geometry import box
        kutular = {d["ad"]: d["kutu"] for d in duvarlar}
        yaylar = [kapi_yayi(o, kutular[o["duvar"]]) for o in out if o["tur"] in ("dis_kapi", "ic_kapi")]
        # aday konumlar: iki uç (köşeye yakın) ve orta, her biri iki menteşe yönüyle; yayı başka kapıya binmeyen ilki
        secim = None
        for bas in (u0, (u0 + u1) / 2 - en / 2, u1 - en):
            bas = r2(round(bas * 2) / 2)
            duvar = next((d for d in duvarlar if d["sinif"] == "ic" and
                          ((e == "y" and abs((d["kutu"][0] + d["kutu"][2]) / 2 - sabit) < 1e-6 and d["kutu"][1] - 1e-6 <= bas and bas + en <= d["kutu"][3] + 1e-6) or
                           (e == "x" and abs((d["kutu"][1] + d["kutu"][3]) / 2 - sabit) < 1e-6 and d["kutu"][0] - 1e-6 <= bas and bas + en <= d["kutu"][2] + 1e-6))),
                         None)
            if duvar is None:
                continue
            for mentese in ("bas", "son"):
                aday = {"ad": f"K{nk + 1}", "tur": "ic_kapi", "duvar": duvar["ad"], "bas": bas, "en": en, "yuk": IC_KAPI[1],
                        "mentese": mentese, "kanat": [80, 200], "acilim": acilim, "not": b}
                if secim is None:
                    secim = aday
                yay = kapi_yayi(aday, duvar["kutu"])
                if all(yay.buffer(YAY_PAYI).intersection(q).area <= 25 for q in yaylar) and \
                        all(yay.intersection(box(*d["kutu"])).area <= 1 for d in duvarlar if d["ad"] != duvar["ad"]):
                    secim = aday
                    break
            else:
                continue
            break
        if secim is None:
            hata.append(f"kapı: {a} ile {b} arasındaki kapı tek bir duvar parçasına sığmıyor")
            continue
        nk += 1
        out.append(secim)
    if not any(o.get("giris") for o in out) and not hata:
        hata.append("dış kapı yok (en az bir ['dis', '<mahal>'] kapısı gerekir)")
    return out, hata


def kapi_yayi(a: dict, kutu: list[float]):
    """Kapının açılım alanı: menteşe ucunda, kapı genişliği yarıçaplı çeyrek daire (shapely). Kutu: kapının duvarının karkas kutusu."""
    from shapely.geometry import Point, box
    x0, y0, x1, y1 = kutu
    r = float(a["en"])
    son = a.get("mentese") == "son"
    if (x1 - x0) >= (y1 - y0):
        hx, hy = a["bas"] + (r if son else 0), (y1 if a.get("acilim") == "ust" else y0)
        kare = box(a["bas"], hy, a["bas"] + r, hy + r) if a.get("acilim") == "ust" else box(a["bas"], hy - r, a["bas"] + r, hy)
    else:
        hx, hy = (x1 if a.get("acilim") == "sag" else x0), a["bas"] + (r if son else 0)
        kare = box(hx, a["bas"], hx + r, a["bas"] + r) if a.get("acilim") == "sag" else box(hx - r, a["bas"], hx, a["bas"] + r)
    return Point(hx, hy).buffer(r).intersection(kare)


# ── veranda kolonları ──────────────────────────────────────────────────────────────────────────────────────────────────
def _kolonlar(iz: Izgara, R: list[int]) -> list[dict]:
    """Çatı altındaki verandanın kolonları: dış dikdörtgen kenarındaki (açık) kenarlarında, binaya değmeyen uçlarda ve en çok
    400 cm arayla. Kutular dış yüzden kaplama kadar içeride (KT-02 gibi)."""
    from shapely.geometry import Point, box
    W, H = iz.W, iz.H
    x0, y0, x1, y1 = R
    kapali = box(0, 0, W, H).difference(box(x0, y0, x1, y1))
    kenarlar = []
    if y0 == 0:
        kenarlar.append(("x", K, (x0, x1)))
    if y1 == H:
        kenarlar.append(("x", H - K - D, (x0, x1)))
    if x0 == 0:
        kenarlar.append(("y", K, (y0, y1)))
    if x1 == W:
        kenarlar.append(("y", W - K - D, (y0, y1)))
    kutular: list[list[float]] = []
    alinan = []
    for e, sabit, (a, b) in sorted(kenarlar, key=lambda k: -(k[2][1] - k[2][0])):
        def uc(v):
            p = Point(v, 0 if (e == "x" and sabit < H / 2) else H) if e == "x" else Point(0 if sabit < W / 2 else W, v)
            return kapali.distance(p) > 1
        bos_a, bos_b = uc(a), uc(b)
        L = b - a
        n = max(1, math.ceil(L / KOLON_ARALIK))
        konumlar = [a + L * t / n for t in range(n + 1)]
        if not bos_a:
            konumlar = konumlar[1:]
        if not bos_b:
            konumlar = konumlar[:-1]
        for v in konumlar:
            s = min(max(v - KOLON[0] / 2, a + K), b - K - KOLON[0])
            kutu = [s, sabit, s + KOLON[0], sabit + D] if e == "x" else [sabit, s, sabit + D, s + KOLON[0]]
            if any(abs(kutu[0] - q[0]) < KOLON[0] + D and abs(kutu[1] - q[1]) < KOLON[0] + D for q in alinan):
                continue                                           # köşe kolonu öteki kenarda alındı
            alinan.append(kutu)
            kutular.append(kutu)
    return [{"ad": f"KLN{n}", "sinif": "kolon", "kutu": [r2(v) for v in k], "yukseklik": 240} for n, k in enumerate(kutular, 1)]


def _kirisler(iz: Izgara, R: list[int]) -> list[dict]:
    """Çatı altındaki verandanın kirişleri (KT-02 KRS01–05 gibi): her açık kenarda kolon hizasında, alt 240 / üst 270; binaya değen ucu
    dış duvarın karkasına kadar uzanır. `acik`: kirişin açıkta kalan aralığı (uzun eksen boyunca)."""
    from shapely.geometry import Point, box
    W, H = iz.W, iz.H
    x0, y0, x1, y1 = R
    kapali = box(0, 0, W, H).difference(box(x0, y0, x1, y1))
    out = []

    def uc_binada(px, py):
        return kapali.distance(Point(px, py)) <= 1
    if y0 == 0 or y1 == H:
        for yk, yy in ((K, 0), (H - K - D, H)) if (y0 == 0 and y1 == H) else (((K, 0),) if y0 == 0 else ((H - K - D, H),)):
            ba, bb = x0 > 0 and uc_binada(x0, yy), x1 < W and uc_binada(x1, yy)
            a = x0 - K - D if ba else (x0 + K if x0 > 0 else K)
            b = x1 + K + D if bb else (x1 - K if x1 < W else W - K)
            out.append({"kutu": [r2(a), r2(yk), r2(b), r2(yk + D)], "acik": [[r2(x0 - K if ba else a), r2(x1 + K if bb else b)]]})
    if x0 == 0 or x1 == W:
        for xk, xx in ((K, 0), (W - K - D, W)) if (x0 == 0 and x1 == W) else (((K, 0),) if x0 == 0 else ((W - K - D, W),)):
            ba, bb = y0 > 0 and uc_binada(xx, y0), y1 < H and uc_binada(xx, y1)
            a = y0 - K - D if ba else K + D                      # açık uçta yatay kirişin karkasından sonra başlar
            b = y1 + K + D if bb else H - K - D
            out.append({"kutu": [r2(xk), r2(a), r2(xk + D), r2(b)], "acik": [[r2(y0 - K if ba else a), r2(y1 + K if bb else b)]]})
    return [{"ad": f"KRS{n}", "alt": 240, "ust": 270, "bolge": "veranda", "not": "veranda kirişi (İE-14)", **k} for n, k in enumerate(out, 1)]


# ── çatı ───────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _duzlem(ad, plan, yukari, egim, sacak, notu):
    return {"ad": ad, "plan": [[r2(x), r2(y)] for x, y in plan], "yukari": yukari, "egim": round(egim, 5), "sacak_kotu": SACAK_KOTU,
            "sacak": sacak, "ust_pay": round(PANEL * math.sqrt(1 + egim ** 2), 3), "not": notu}


def cati_uret(R: tuple[float, float, float, float], tip: str, mahya: str | None, egim: float | None) -> dict:
    """Dikdörtgen (dış yüzler) üstüne beşik ya da kırma. Mahya verilmezse uzun kenar boyunca."""
    x0, y0, x1, y1 = R
    e = EGIM if egim is None else round(egim / 100, 5)
    if mahya not in ("x", "y"):
        mahya = "x" if (x1 - x0) >= (y1 - y0) else "y"
    X0, Y0, X1, Y1 = x0 - SACAK, y0 - SACAK, x1 + SACAK, y1 + SACAK
    duz, kal = [], []
    if mahya == "x":
        ym = (Y0 + Y1) / 2
        if tip == "besik":
            duz = [_duzlem("güney", [[X0, Y0], [X1, Y0], [X1, ym], [X0, ym]], [0, 1], e, {"y": Y0}, "güney yüzü"),
                   _duzlem("kuzey", [[X0, ym], [X1, ym], [X1, Y1], [X0, Y1]], [0, -1], e, {"y": Y1}, "kuzey yüzü")]
            kal = [{"ad": "batı kalkanı", "eksen": "x", "konum": r2(x0), "aralik": [r2(y0), r2(y1)], "ic": "dogu", "ust": ["güney", "kuzey"]},
                   {"ad": "doğu kalkanı", "eksen": "x", "konum": r2(x1), "aralik": [r2(y0), r2(y1)], "ic": "bati", "ust": ["güney", "kuzey"]}]
        else:
            h = (Y1 - Y0) / 2
            duz = [_duzlem("güney", [[X0, Y0], [X1, Y0], [X1 - h, ym], [X0 + h, ym]], [0, 1], e, {"y": Y0}, "güney yüzü"),
                   _duzlem("kuzey", [[X0 + h, ym], [X1 - h, ym], [X1, Y1], [X0, Y1]], [0, -1], e, {"y": Y1}, "kuzey yüzü"),
                   _duzlem("batı", [[X0, Y0], [X0 + h, ym], [X0, Y1]], [1, 0], e, {"x": X0}, "batı kırması"),
                   _duzlem("doğu", [[X1, Y0], [X1, Y1], [X1 - h, ym]], [-1, 0], e, {"x": X1}, "doğu kırması")]
    else:
        xm = (X0 + X1) / 2
        if tip == "besik":
            duz = [_duzlem("batı", [[X0, Y0], [xm, Y0], [xm, Y1], [X0, Y1]], [1, 0], e, {"x": X0}, "batı yüzü"),
                   _duzlem("doğu", [[xm, Y0], [X1, Y0], [X1, Y1], [xm, Y1]], [-1, 0], e, {"x": X1}, "doğu yüzü")]
            kal = [{"ad": "güney kalkanı", "eksen": "y", "konum": r2(y0), "aralik": [r2(x0), r2(x1)], "ic": "kuzey", "ust": ["batı", "doğu"]},
                   {"ad": "kuzey kalkanı", "eksen": "y", "konum": r2(y1), "aralik": [r2(x0), r2(x1)], "ic": "guney", "ust": ["batı", "doğu"]}]
        else:
            h = (X1 - X0) / 2
            duz = [_duzlem("batı", [[X0, Y0], [xm, Y0 + h], [xm, Y1 - h], [X0, Y1]], [1, 0], e, {"x": X0}, "batı yüzü"),
                   _duzlem("doğu", [[X1, Y0], [X1, Y1], [xm, Y1 - h], [xm, Y0 + h]], [-1, 0], e, {"x": X1}, "doğu yüzü"),
                   _duzlem("güney", [[X0, Y0], [X1, Y0], [xm, Y0 + h]], [0, 1], e, {"y": Y0}, "güney kırması"),
                   _duzlem("kuzey", [[X1, Y1], [X0, Y1], [xm, Y1 - h]], [0, -1], e, {"y": Y1}, "kuzey kırması")]
    adi = {"besik": "beşik", "kirma": "kırma"}[tip]
    yon = "doğu–batı" if mahya == "x" else "kuzey–güney"
    return {"tip": tip, "tip_adi": f"{adi} (mahya {yon})", "sacak": int(SACAK), "topuk": TOPUK, "duvar_ustu": DUVAR_USTU,
            "panel_kalinligi": int(PANEL), "duzlemler": duz, "kalkanlar": kal}


# ── ana çağrı ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def derle(p: dict, kod: str = "YENI", ad: str | None = None) -> dict:
    """Plan şeması → Yapı Tanımı 0.5. Geçersizse PlanHatasi(ihlaller)."""
    W, H = int(p["dis_olcu"]["en"]), int(p["dis_olcu"]["boy"])
    if W % IZGARA or H % IZGARA or W <= 0 or H <= 0:
        raise PlanHatasi([f"dış ölçü {IZGARA} cm ızgarada ve artı olmalı ({W} × {H})"])
    hata: list[str] = []
    adlar = [m["ad"] for m in p["mahaller"]]
    if len(set(adlar)) != len(adlar):
        hata.append("mahal adları tekil olmalı: " + ", ".join(sorted({a for a in adlar if adlar.count(a) > 1})))
    if "dis" in adlar:
        hata.append("'dis' mahal adı olamaz (dış kapı için ayrılmış)")
    iz, odalar, ver, h = _yerlestir(p)
    hata += h
    if hata:
        raise PlanHatasi(hata)
    duvarlar, dis_ad = _duvarlar(iz)
    acikliklar, h = _acikliklar(p, iz, odalar, duvarlar, dis_ad, ver)
    if h:
        raise PlanHatasi(h)
    mahaller = []
    for m in odalar:
        en_buyuk = max(m["dikdortgenler"], key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
        e = {"ad": m["ad"], "nokta": [r2((en_buyuk[0] + en_buyuk[2]) / 2), r2((en_buyuk[1] + en_buyuk[3]) / 2)], "islev": [m["islev"]], "sinif": "ic"}
        if m["islev"] == "banyo":
            e["islak"] = True
        mahaller.append(e)
    siniflar = {"dis": {"ad": "dış duvar (DIS-80)", "profil": "80x45x1,2", "yalitim": True, "yuz": {"ic": "ic", "dis": "dis", "veranda": "dis"}},
                "ic": {"ad": "iç duvar (IC-80)", "profil": "80x45x1,2", "yalitim": True, "yuz": {"ic": "ic"}}}
    kapali = [int(v) for v in np.argwhere(iz.lab >= 0).min(axis=0) * IZGARA] + \
             [int(v) for v in (np.argwhere(iz.lab >= 0).max(axis=0) + 1) * IZGARA]
    cati_R = (kapali[0], kapali[1], kapali[2], kapali[3])
    kirisler: list[dict] = []
    if ver is not None:
        x0, y0, x1, y1 = (int(v) for v in ver["dikdortgenler"][0])
        ortu = ver.get("ortu") or "cati"
        mahaller.append({"ad": ver["ad"], "sinif": "veranda", "islev": ["veranda"], "poligon": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
                         "nokta": [r2((x0 + x1) / 2), r2((y0 + y1) / 2)], "ortu": ortu})
        if ortu == "cati":
            cati_R = (0, 0, W, H)
            siniflar["kolon"] = {"ad": "veranda kolonu", "profil": "80x45x1,2", "yalitim": False, "yuz": {"veranda": "dis", "dis": "dis"}}
            duvarlar += _kolonlar(iz, [x0, y0, x1, y1])
            kirisler = _kirisler(iz, [x0, y0, x1, y1])
    ct = p.get("cati") or {"tip": "besik"}
    cati = cati_uret(cati_R, ct.get("tip") or "besik", ct.get("mahya_yonu"), ct.get("egim_yuzde"))
    alan = W * H / 1e4
    return {
        "sema": "portman.yapi_tanimi/0.5-taslak", "kod": kod, "ad": ad or f"Yeni plan, tek kat çelik, {alan:.0f} m² (TASLAK)",
        "aile": "tek_kat_celik", "paket": "baz", "birim": "cm", "kat": "zemin",
        "kaynak": {"cizim": "İE-14 plan üreteci: plan şemasından koddan derlendi (motor/genel/plan_derle.py); mühendis kabulü yok (D-18)",
                   "koordinat": "Köken binanın güneybatı dış köşesi; +x doğu, +y kuzey; cm"},
        "kat_yuksekligi": DUVAR_USTU, "duvar_panelleri": "tahmin",
        "yuz_kaplamalari": {"dis": {"kalinlik": K, "malzeme": ["boardex"]}, "ic": {"kalinlik": K, "malzeme": ["alcipan"]}},
        "duvar_siniflari": siniflar, "duvarlar": duvarlar, "mahaller": mahaller, "acikliklar": acikliklar, "kirisler": kirisler, "lento": 70,
        "cati": cati,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="İE-14 plan şeması → Yapı Tanımı 0.5")
    ap.add_argument("plan", type=Path)
    ap.add_argument("cikti", type=Path)
    ap.add_argument("--kod", default="YENI")
    a = ap.parse_args(argv)
    try:
        t = derle(json.loads(a.plan.read_text(encoding="utf-8")), kod=a.kod)
    except PlanHatasi as e:
        raise SystemExit("plan geçersiz:\n- " + "\n- ".join(e.ihlaller))
    a.cikti.write_text(json.dumps(t, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("yazıldı", a.cikti, "| duvar", len(t["duvarlar"]), "| mahal", len(t["mahaller"]), "| açıklık", len(t["acikliklar"]))


if __name__ == "__main__":
    main()
