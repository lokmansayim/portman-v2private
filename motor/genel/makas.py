#!/usr/bin/env python3
"""Çatı karkas kuralı (İE-16 PR-3b): makas dizilimi ve makasın üyeleri; çatı paneli, tavan paneli ve çatı üstü panel.

Yalnız tanım karkas kuralını isterse çalışır (`"karkas": "kural"`; `karkas.kur` çağırır); istemeyen tanımın çıktısı bayt bayt aynıdır.
Sayısal ayarlar `kurallar/karkas/celik_karkas.json`'da (`makas`, `makas_uyeleri`, `cati_paneli`, `tavan_paneli`), her biri durumu ve
kaynağıyla. Tanımdaki `cati.makaslar` (paftadan okunmuş makas yerleri) bu kuralda okunmaz: kör projede o bilgi yoktur.

1. **Aile.** Bir mahya ve iki düzlemi beşik ailedir; aileye girmeyen ve duvar dibine dayanan düzlem tek eğimli ailedir. Aileye girmeyen
   öteki makaslı düzlem kırma yüzüdür: tepe köşesi bir mahyanın ucundaysa o ailenin o ucuna bağlanır. Ana aile en büyük düzlemi
   taşıyandır. Kanat: ana aileye dik, mahyası ana ailenin saçak bandının dışına taşan beşik aile (güneydeki kanat, cumba, çıkma).
2. **Konum.** Makas mahyaya diktir; konumlar mahya boyunca iki uç arasında eşit aralıklı (en çok `aralik_cm`), değer makasın ortası.
   Beşik ailenin ucu: alın → kalkan duvarının iç yüzü; kırma → kırma yüzünün saçağı altındaki duvarın iç yüzü, o konum düşer (ana
   makaslar kırma bölgesinden, üstleri kırma yüzüyle kırpılarak geçer); birleşim → aynı eksenli komşu aile o yöndeyse mahyanın ucu,
   değilse ailenin düzlemlerinin o yöndeki ucu (orada duvar varsa iç yüzü). Kanadın ana çatıya bakan ucu ana ailenin saçağında biter.
   Tek eğimli ailenin ucu: düzlem orada tam derinlikteyse duvarın iç yüzü; değilse (kırma ya da vadi) tam derinliğin bittiği yer.
3. **Makas çizgisi.** Konumda makas yönünde: ailenin iki düzlemi (her biri mahyanın kendi yanında) ve kırma yüzleri içinde, mahyayı
   içeren bitişik parça. Ucunda tek eğimli bir düzlem ya da (ana ailede) kanadın düzlemi sürüyorsa, vadiyi geçip ailenin o yandaki
   saçak hizasına kadar uzanır. Üstü çatı yüzeyi, altı duvar üstü (`duvar_ustu`). `en_kisa_cm`'den kısa çizgi makas olmaz.
4. **Kısa makas ve çapraz.** Kırma ucunun şeridinde (uç duvardan ilk makasa) kırma yüzünün yönünde, tek eğimli düzlemin kırma
   üçgeninde ailenin yönünde; aralık yine en çok `aralik_cm`, uçlardaki konum düşer (köşede çapraz var). Her kırma çizgisinde (kırma
   yüzüyle ailesi ya da tek eğimli düzlemle komşusu arasında) bir çapraz makas.
5. **Üyeler.** Alt başlık (açıklık), üst başlık (çatı yüzeyi boyunca) ve örgü: açıklık en çok `panel_cm` boyunda eşit panellere
   bölünür; iç düğümlerde dikme (düğümdeki yükseklik), her panelde bir çapraz (panel boyu ve panelin ortalama yüksekliğiyle). Biçim ve
   `panel_cm`, KT-01'in (= ÇP-13) karkas modelindeki 16 makastan; biri dışarıda bırakılarak seçildi (`makas_uyeleri`).
6. **Paneller.** Çatı paneli (tanımda `ust_yapi: cati_paneli` düzlemler), yöntem A'nın çatı üstü paneli ve tavan paneli duvar
   paneli kuralıyla kurulur (`karkas.uyeler`; panelin uzun kenarı başlık, dikmeler `dikme_araligi_cm` arayla kısa kenar boyunca).
   Çatı paneli düzlemin açılımında saçak boyunca `cati_paneli_adedi` eşit panele bölünür; çatı üstü paneli saçak boyunca `bolme`
   hedefiyle; tavan paneli ana ailenin makas aralıklarında, mahallerin içinde.

Hesapta LLM yoktur: aynı tanım ve aynı kural aynı sonucu verir. Ölçüler cm; boylar m.
"""
from __future__ import annotations
from .toplam import sum  # noqa: A001 — 3.11 toplama sırası her Python sürümünde (İE-08 GM2; toplam.py)

import math

from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from . import cati_genel

EPS = 0.5          # cm; düzlem sınırı ve nokta eşitliği toleransı
ADIM = 2.0         # cm; makasın üst çizgisi bu aralıkla örneklenir


def _d(k: dict, anahtar: str):
    return k[anahtar]["deger"]


def _esit(p, q, tol: float = 1.0) -> bool:
    return math.hypot(p[0] - q[0], p[1] - q[1]) < tol


def _eksen(dz: dict) -> str:
    """Düzlemin eğim yönü: makas bu eksen boyunca uzanır."""
    yx, yy = dz["yukari"]
    return "x" if abs(yx) > abs(yy) else "y"


def _i(e: str) -> int:
    return 0 if e == "x" else 1


def _oteki(e: str) -> str:
    return "y" if e == "x" else "x"


def _sacak(dz: dict, ex: str):
    return dz["sacak"].get(ex)


# ──────────────────────────────────────────────────────────────── aileler ──
def aileler(c: dict) -> tuple[dict, list[dict], list[dict], list[str]]:
    """(makaslı düzlemler adla, kenarlar, aileler, kırma yüzü olup bir aileye bağlanmayan düzlemler)."""
    dzs = [d for d in c["duzlemler"] if d.get("ust_yapi") != "cati_paneli"]
    adli = {d["ad"]: d for d in dzs}
    kn = [e for e in c["kenarlar"] if all(a in adli for a in e["duzlemler"])]
    aile: list[dict] = []
    for e in kn:
        if e["tur"] != "mahya":
            continue
        a, b = e["duzlemler"]
        ex = _eksen(adli[a])
        ie = _i(_oteki(ex))
        p, q = tuple(e["p"]), tuple(e["q"])
        if p[ie] > q[ie]:
            p, q = q, p
        aile.append({"tur": "besik", "duzlemler": [a, b], "uc": (p, q), "eksen": ex})
    kolda = {x for k in aile for x in k["duzlemler"]}
    dibi = {e["duzlemler"][0] for e in kn if e["tur"] == "duvar_dibi"}
    for a in adli:
        if a not in kolda and a in dibi:
            aile.append({"tur": "tek", "duzlemler": [a], "eksen": _eksen(adli[a])})
    kolda = {x for k in aile for x in k["duzlemler"]}
    serbest = [a for a in adli if a not in kolda]
    for k in aile:
        k["kirma_yuzu"] = {}
        if k["tur"] == "besik":
            for i, u in enumerate(k["uc"]):
                for a in serbest:
                    if _eksen(adli[a]) != k["eksen"] and any(_esit(u, v) for v in adli[a]["plan"]):
                        k["kirma_yuzu"][i] = a
        k["takim"] = k["duzlemler"] + [k["kirma_yuzu"][i] for i in sorted(k["kirma_yuzu"])]
    buyuk = max(dzs, key=lambda d: d["cokgen"].area)["ad"]
    for k in aile:
        k["ana"] = buyuk in k["duzlemler"]
        k["kanatlari"], k["sinir"] = [], {}
    for a in aile:
        if not a["ana"] or a["tur"] != "besik":
            continue
        i = _i(a["eksen"])
        sac = [_sacak(adli[n], a["eksen"]) for n in a["duzlemler"]]
        if None in sac:
            continue
        lo, hi = min(sac), max(sac)
        for k in aile:
            if k["ana"] or k["tur"] != "besik" or k["eksen"] == a["eksen"]:
                continue
            us = [u[i] for u in k["uc"]]
            if min(us) < lo - 1 or max(us) > hi + 1:
                a["kanatlari"].append(k)
                if min(us) < lo - 1:
                    k["sinir"][+1] = min(k["sinir"].get(+1, math.inf), lo)
                else:
                    k["sinir"][-1] = max(k["sinir"].get(-1, -math.inf), hi)
    bagli = {x for k in aile for x in k["kirma_yuzu"].values()}
    return adli, kn, aile, [a for a in serbest if a not in bagli]


# ──────────────────────────────────────────────────────────────── konumlar ──
def _duvar(y: dict, cizgi: float, ee: str, ex: str, bant: tuple[float, float], en_cok: float):
    """`cizgi` konumundaki (ee ekseninde) uç çizgisine paralel, ona en çok `en_cok` uzak, ex'te `bant` ile örtüşen en yakın duvar:
    ee eksenindeki (baş, son) ya da None."""
    en_iyi = None
    for w in y["duvarlar"]:
        if w["sinif"] not in ("dis", "ic", "ek"):
            continue
        x0, y0, x1, y1 = w["kutu"]
        e0, e1 = (x0, x1) if ee == "x" else (y0, y1)
        d0, d1 = (x0, x1) if ex == "x" else (y0, y1)
        if (e1 - e0) > (d1 - d0) or min(d1, bant[1]) - max(d0, bant[0]) < 10:
            continue
        uzak = abs((e0 + e1) / 2 - cizgi)
        if uzak <= en_cok and (en_iyi is None or uzak < en_iyi[0]):
            en_iyi = (uzak, (e0, e1))
    return None if en_iyi is None else en_iyi[1]


def _ic_yuz(w, isaret: int, yedek: float) -> float:
    """Duvarın ailenin içine bakan yüzü (`isaret`: ucun dışarı yönü); duvar yoksa yedek."""
    if w is None:
        return yedek
    return w[1] if isaret < 0 else w[0]


def _esit_bol(a0: float, a1: float, dus0: bool, dus1: bool, S: float) -> list[float]:
    L = a1 - a0
    n = max(1, math.ceil(L / S - 1e-9))
    ks = [a0 + L * i / n for i in range(n + 1)]
    return ks[1 if dus0 else 0: len(ks) - (1 if dus1 else 0)]


def _besik_konumlar(y: dict, adli: dict, kn: list[dict], aile: list[dict], k: dict, sacak: float, S: float, kal: float):
    ex = k["eksen"]; ee = _oteki(ex)
    ie = _i(ee)
    bb = unary_union([adli[a]["cokgen"] for a in k["takim"]]).bounds
    bant = (bb[_i(ex)], bb[_i(ex) + 2])
    uclar = []
    for i, (u, isaret) in enumerate(((k["uc"][0], -1), (k["uc"][1], +1))):    # isaret: ucun dışarı yönü (ee ekseninde)
        turler = {e["tur"] for e in kn if (_esit(e["p"], u) or _esit(e["q"], u)) and any(a in k["duzlemler"] for a in e["duzlemler"])}
        if i in k["kirma_yuzu"]:
            H = k["kirma_yuzu"][i]
            sac = [e for e in kn if e["tur"] == "sacak" and e["duzlemler"] == [H] and abs(e["p"][ie] - e["q"][ie]) < 1]
            uc = max(sac, key=lambda e: e["plan_boy"])["p"][ie] if sac else u[ie] + isaret * 10 * sacak
            uclar.append((_ic_yuz(_duvar(y, uc, ee, ex, bant, sacak + 15), isaret, uc - isaret * sacak), True, "kırma"))
        elif "alin" in turler:
            uclar.append((_ic_yuz(_duvar(y, u[ie], ee, ex, bant, sacak + 15), isaret, u[ie]), False, "alın"))
        elif any(o is not k and o["tur"] == "besik" and o["eksen"] == ex and set(o["takim"]) & set(k["takim"])
                 and any((v[ie] - u[ie]) * isaret > 1 for v in o["uc"]) for o in aile):
            uclar.append((u[ie], False, "birleşim"))
        else:
            ks = [p[ie] for a in k["takim"] for p in adli[a]["plan"]]
            uc = min(ks) if isaret < 0 else max(ks)
            uclar.append((_ic_yuz(_duvar(y, uc, ee, ex, bant, sacak + 15), isaret, uc), False, "uzanım"))
    (a0, d0, n0), (a1, d1, n1) = uclar
    if -1 in k["sinir"] and k["sinir"][-1] + kal / 2 > a0:            # kanadın ana çatıya bakan ucu: makas ana saçağın hemen dışında
        a0, d0, n0 = k["sinir"][-1] + kal / 2, False, "ana saçak"
    if +1 in k["sinir"] and k["sinir"][+1] - kal / 2 < a1:
        a1, d1, n1 = k["sinir"][+1] - kal / 2, False, "ana saçak"
    return _esit_bol(a0, a1, d0, d1, S), (n0, n1), (a0, a1)


def _tek_konumlar(y: dict, adli: dict, kn: list[dict], k: dict, sacak: float, S: float, kal: float):
    """Tek eğimli düzlem: konumlar ve kırma üçgenleri [(son tam makas, saçak köşesi)]."""
    dz = adli[k["duzlemler"][0]]
    ex = k["eksen"]; ee = _oteki(ex)
    ie, ix = _i(ee), _i(ex)
    pol = dz["cokgen"]
    bb = pol.bounds
    sac = max((e for e in kn if e["tur"] == "sacak" and e["duzlemler"] == [dz["ad"]]), key=lambda e: e["plan_boy"])
    derinlik = bb[ix + 2] - bb[ix]

    def derin(e):
        ln = LineString([(e, bb[1] - 1), (e, bb[3] + 1)]) if ee == "x" else LineString([(bb[0] - 1, e), (bb[2] + 1, e)])
        return ln.intersection(pol).length

    def tam_sinir(c, yon):
        """Saçak köşesinden (c) içeri doğru, derinliğin tam olduğu ilk konum (0,5 cm duyarlıkla)."""
        lo, hi = 0.0, abs(sac["p"][ie] - sac["q"][ie])
        if derin(c - yon * 0.25) >= derinlik - 1.0:
            return c
        for _ in range(40):
            orta = (lo + hi) / 2
            if derin(c - yon * orta) >= derinlik - 1.0:
                hi = orta
            else:
                lo = orta
        return c - yon * hi
    c0, c1 = sorted([sac["p"][ie], sac["q"][ie]])
    uclar, ucgen = [], []
    for c, yon in ((c0, -1), (c1, +1)):
        kose = (c, sac["p"][ix]) if ee == "x" else (sac["p"][ix], c)
        turler = {e["tur"] for e in kn if (_esit(e["p"], kose) or _esit(e["q"], kose)) and dz["ad"] in e["duzlemler"]} - {"sacak"}
        if not turler & {"kirma", "vadi"}:
            w = _duvar(y, c, ee, ex, (bb[ix], bb[ix + 2]), sacak + 15)
            uclar.append((_ic_yuz(w, yon, c - yon * sacak), "alın"))
            continue
        b = tam_sinir(c, yon) - yon * kal / 2
        uclar.append((b, "kırma" if "kirma" in turler else "vadi"))
        if "kirma" in turler:
            ucgen.append((b, c))
    (a0, n0), (a1, n1) = uclar
    return _esit_bol(a0, a1, False, False, S), (n0, n1), ucgen


# ──────────────────────────────────────────────────────────────── çizgiler ──
def _araliklar(dz: dict, ex: str, a: float, bb) -> list[tuple[float, float]]:
    """`a` konumunda ex yönündeki doğrunun düzlemin içinde kalan aralıkları (ex ekseninde)."""
    i = _i(ex)
    ln = LineString([(bb[0] - 10, a), (bb[2] + 10, a)]) if ex == "x" else LineString([(a, bb[1] - 10), (a, bb[3] + 10)])
    kes = ln.intersection(dz["cokgen"].buffer(EPS))
    parcalar = [kes] if kes.geom_type == "LineString" else [g for g in getattr(kes, "geoms", []) if g.geom_type == "LineString"]
    out = []
    for g in parcalar:
        if g.is_empty:
            continue
        cs = [p[i] for p in g.coords]
        out.append((min(cs), max(cs)))
    return sorted(out)


def _icinde(ar: list[tuple[float, float]], s: float) -> bool:
    return any(lo - 1e-9 <= s <= hi + 1e-9 for lo, hi in ar)


def _profil(adli: dict, ex: str, a: float, s0: float, s1: float, kapsam: dict[str, list]) -> dict:
    """[s0, s1] boyunca üst çizgi: her noktada kapsayan düzlemlerin en yükseği. Dönen: noktalar, yükseklikler, boylar."""
    n = max(2, int(math.ceil((s1 - s0) / ADIM)) + 1)
    ss = [s0 + (s1 - s0) * j / (n - 1) for j in range(n)]
    zz = []
    for s in ss:
        p = (s, a) if ex == "x" else (a, s)
        kot = [adli[ad]["kot"](p) for ad, ar in kapsam.items() if _icinde(ar, s)]
        zz.append(max(kot) if kot else (zz[-1] if zz else None))
    if zz[0] is None:
        ilk = next(z for z in zz if z is not None)
        zz = [ilk if z is None else z for z in zz]
    return {"ss": ss, "zz": zz}


def _birlesik(ar: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[list[float]] = []
    for lo, hi in sorted(ar):
        if out and lo <= out[-1][1] + 1e-6:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return [(lo, hi) for lo, hi in out]


def _besik_cizgi(adli: dict, k: dict, a: float, bb, uzanan: list[str]):
    ex = k["eksen"]; i = _i(ex)
    A, B = k["duzlemler"]
    m = k["uc"][0][i]
    kapsam = {}
    for n in k["takim"]:
        ar = _araliklar(adli[n], ex, a, bb)
        if n in (A, B):                                        # aile düzlemi mahyanın kendi yanında
            up = adli[n]["yukari"][i]
            ar = [(lo, min(hi, m)) if up > 0 else (max(lo, m), hi) for lo, hi in ar]
            ar = [(lo, hi) for lo, hi in ar if hi - lo > 1e-6]
        if ar:
            kapsam[n] = ar
    parcalar = _birlesik([x for ar in kapsam.values() for x in ar])
    if not parcalar:
        return None
    icinde = [p for p in parcalar if p[0] - EPS <= m <= p[1] + EPS]
    s0, s1 = icinde[0] if icinde else max(parcalar, key=lambda p: p[1] - p[0])
    # vadi üçgeni: uçta tek eğimli düzlem ya da kanat düzlemi sürüyorsa ailenin o yandaki saçağına kadar
    for n in (A, B):
        hedef = _sacak(adli[n], ex)
        if hedef is None:
            continue
        yon = -1 if adli[n]["yukari"][i] > 0 else +1
        uc = s0 if yon < 0 else s1
        if (hedef - uc) * yon <= EPS:
            continue
        ek = _birlesik([x for o in uzanan for x in _araliklar(adli[o], ex, a, bb)])
        for lo, hi in ek:
            if lo - EPS <= uc <= hi + EPS:
                yeni = max(lo, hedef) if yon < 0 else min(hi, hedef)
                for o in uzanan:
                    ar = [(max(x0, min(uc, yeni)), min(x1, max(uc, yeni))) for x0, x1 in _araliklar(adli[o], ex, a, bb)]
                    ar = [(x0, x1) for x0, x1 in ar if x1 - x0 > 1e-6]
                    if ar:
                        kapsam[o] = kapsam.get(o, []) + ar
                if yon < 0:
                    s0 = yeni
                else:
                    s1 = yeni
                break
    return {"s0": s0, "s1": s1, **_profil(adli, ex, a, s0, s1, kapsam)}


def _tek_cizgi(adli: dict, ad: str, ex: str, a: float, bb, sinir: tuple[float, float] | None = None):
    ar = _araliklar(adli[ad], ex, a, bb)
    if sinir:
        ar = [(max(lo, sinir[0]), min(hi, sinir[1])) for lo, hi in ar]
        ar = [(lo, hi) for lo, hi in ar if hi - lo > 1e-6]
    if not ar:
        return None
    s0, s1 = max(ar, key=lambda p: p[1] - p[0])
    return {"s0": s0, "s1": s1, **_profil(adli, ex, a, s0, s1, {ad: [(s0, s1)]})}


# ──────────────────────────────────────────────────────────────── üyeler ──
def _yukseklik(ss: list[float], hh: list[float], s: float) -> float:
    if s <= ss[0]:
        return hh[0]
    if s >= ss[-1]:
        return hh[-1]
    j = min(int((s - ss[0]) / (ss[-1] - ss[0]) * (len(ss) - 1)), len(ss) - 2)
    while ss[j + 1] < s:
        j += 1
    while ss[j] > s:
        j -= 1
    t = (s - ss[j]) / (ss[j + 1] - ss[j]) if ss[j + 1] > ss[j] else 0.0
    return hh[j] + t * (hh[j + 1] - hh[j])


def uyeler(ss: list[float], zz: list[float], duvar_ustu: float, panel: float) -> dict[str, float]:
    """Makasın üyeleri, tür tür boy (m): alt başlık, üst başlık, dikmeler, çaprazlar."""
    hh = [z - duvar_ustu for z in zz]
    acik = ss[-1] - ss[0]
    n = max(1, math.ceil(acik / panel - 1e-9))
    pe = acik / n
    hk = [_yukseklik(ss, hh, ss[0] + pe * j) for j in range(n + 1)]
    ust = sum(math.hypot(ss[j + 1] - ss[j], zz[j + 1] - zz[j]) for j in range(len(ss) - 1))
    return {"alt_baslik": acik / 100, "ust_baslik": ust / 100, "dikme": sum(hk[1:-1]) / 100,
            "capraz": sum(math.hypot(pe, (hk[j] + hk[j + 1]) / 2) for j in range(n)) / 100}


def _kayit(tur: str, aile: str, ex: str, a: float, cz: dict, duvar_ustu: float, panel: float) -> dict:
    u = uyeler(cz["ss"], cz["zz"], duvar_ustu, panel)
    return {"tur": tur, "aile": aile, "eksen": ex, "konum": round(a, 2), "s": [round(cz["s0"], 2), round(cz["s1"], 2)],
            "acik_cm": round(cz["s1"] - cz["s0"], 2), "h_en_cok_cm": round(max(cz["zz"]) - duvar_ustu, 2),
            "uyeler_m": {ad: round(v, 4) for ad, v in u.items()}, "profil_boyu_m": round(sum(u.values()), 4)}


def makaslar(t: dict, c: dict, y: dict, k: dict) -> dict:
    """Makaslar (tam, kısa, çapraz) ve ailelerin kaydı."""
    mk = _d(k, "makas")
    S, kal, en_kisa = mk["aralik_cm"], mk["kalinlik_cm"], mk["en_kisa_cm"]
    panel = _d(k, "makas_uyeleri")["panel_cm"]
    sacak = t["cati"].get("sacak", 30.0)
    duvar_ustu = t["cati"].get("duvar_ustu", 270.0)
    adli, kn, aile, serbest = aileler(c)
    if not aile:
        return {"makaslar": [], "aileler": [], "baglanmayan_kirma_yuzleri": serbest}
    bb = unary_union([d["cokgen"] for d in adli.values()]).bounds
    tekler = [x["duzlemler"][0] for x in aile if x["tur"] == "tek"]
    out, kayit = [], []
    for f in aile:
        ex = f["eksen"]; ee = _oteki(ex)
        ad = "/".join(f["duzlemler"])
        if f["tur"] == "besik":
            ks, nedenler, uclar = _besik_konumlar(y, adli, kn, aile, f, sacak, S, kal)
            uzanan = tekler + [x for kk in f["kanatlari"] for x in kk["takim"]]
            for a_ in ks:
                cz = _besik_cizgi(adli, f, a_, bb, uzanan)
                if cz and cz["s1"] - cz["s0"] >= en_kisa:
                    out.append(_kayit("makas", ad, ex, a_, cz, duvar_ustu, panel))
            for i, H in sorted(f["kirma_yuzu"].items()):     # kırma ucunun şeridi: kırma yüzünün yönünde kısa makaslar
                w = uclar[i]
                a1 = ks[0] if i == 0 else ks[-1]
                hb = adli[H]["cokgen"].bounds
                ln = LineString([(w, hb[1] - 1), (w, hb[3] + 1)]) if ee == "x" else LineString([(hb[0] - 1, w), (hb[2] + 1, w)])
                kes = ln.intersection(adli[H]["cokgen"])
                if kes.is_empty or kes.geom_type != "LineString":
                    continue
                cc = [q[_i(ex)] for q in kes.coords]
                for pos in _esit_bol(min(cc), max(cc), True, True, S):
                    cz = _tek_cizgi(adli, H, ee, pos, bb, (-math.inf, a1) if i == 0 else (a1, math.inf))
                    if cz and cz["s1"] - cz["s0"] >= en_kisa:
                        out.append(_kayit("kisa", H, ee, pos, cz, duvar_ustu, panel))
        else:
            ks, nedenler, ucgen = _tek_konumlar(y, adli, kn, f, sacak, S, kal)
            uclar = (ks[0], ks[-1])
            for a_ in ks:
                cz = _tek_cizgi(adli, f["duzlemler"][0], ex, a_, bb)
                if cz and cz["s1"] - cz["s0"] >= en_kisa:
                    out.append(_kayit("makas", ad, ex, a_, cz, duvar_ustu, panel))
            for b, cpos in ucgen:                             # kırma üçgeni: ailenin yönünde kısa makaslar
                for pos in _esit_bol(min(b, cpos), max(b, cpos), True, True, S):
                    cz = _tek_cizgi(adli, f["duzlemler"][0], ex, pos, bb)
                    if cz and cz["s1"] - cz["s0"] >= en_kisa:
                        out.append(_kayit("kisa", ad, ex, pos, cz, duvar_ustu, panel))
        kayit.append({"aile": ad, "tur": f["tur"], "eksen": f["eksen"], "ana": f["ana"], "uclar": list(nedenler),
                      "konumlar": [round(v, 2) for v in ks], "kirma_yuzleri": [f["kirma_yuzu"][i] for i in sorted(f["kirma_yuzu"])],
                      "kanatlari": ["/".join(x["duzlemler"]) for x in f["kanatlari"]]})
    # çaprazlar: kırma çizgisi boyunca, saçak köşesinden tepeye
    for e in kn:
        if e["tur"] != "kirma":
            continue
        a_, b_ = e["duzlemler"]
        bagli = any((a_ in f["duzlemler"] and b_ in f["kirma_yuzu"].values()) or (b_ in f["duzlemler"] and a_ in f["kirma_yuzu"].values()) for f in aile)
        if not (bagli or a_ in tekler or b_ in tekler):
            continue
        L = e["plan_boy"]
        z0, z1 = e["kot"]
        if z0 > z1:
            z0, z1 = z1, z0
        n = max(2, int(math.ceil(L / ADIM)) + 1)
        ss = [L * j / (n - 1) for j in range(n)]
        zz = [z0 + (z1 - z0) * s / L for s in ss]
        u = uyeler(ss, zz, duvar_ustu, panel)
        out.append({"tur": "capraz", "aile": "/".join(e["duzlemler"]), "eksen": None, "konum": None,
                    "s": [[round(v, 2) for v in e["p"]], [round(v, 2) for v in e["q"]]], "acik_cm": round(L, 2),
                    "h_en_cok_cm": round(z1 - duvar_ustu, 2), "uyeler_m": {ad: round(v, 4) for ad, v in u.items()},
                    "profil_boyu_m": round(sum(u.values()), 4)})
    return {"makaslar": out, "aileler": kayit, "baglanmayan_kirma_yuzleri": serbest}


# ──────────────────────────────────────────────────────────────── paneller ──
def panel_uyeleri(pol: Polygon, k: dict, capraz: bool = True) -> dict[str, float]:
    """Düz (açılımdaki) bir panelin üyeleri, duvar paneli kuralıyla (m): çevre (başlıklar ve uç dikmeler), ara dikmeler
    (`dikme_araligi_cm` arayla, uzun kenara dik), kuşaklar (`kusak_kotlari_cm`, uzun kenara paralel) ve çapraz payı
    (kısa kenar × (a + b × uzun kenar); karkas kuralının `capraz_payi`). Dikdörtgende `karkas.uyeler` ile aynı."""
    x0, y0, x1, y1 = pol.bounds
    du, dv = x1 - x0, y1 - y0
    uzun_u = du >= dv
    L, H = (du, dv) if uzun_u else (dv, du)
    S = _d(k, "dikme_araligi_cm")

    def kesit(sabit, deger):
        ln = (LineString([(deger, y0 - 1), (deger, y1 + 1)]) if sabit == "u" else LineString([(x0 - 1, deger), (x1 + 1, deger)]))
        return ln.intersection(pol).length
    dikme = sum(kesit("u" if uzun_u else "v", (x0 if uzun_u else y0) + S * j) for j in range(1, int(math.ceil(L / S - 1e-9))))
    kusak = sum(kesit("v" if uzun_u else "u", (y0 if uzun_u else x0) + z) for z in _d(k, "kusak_kotlari_cm")
                if z < H - _d(k, "kusak_ust_payi_cm"))
    cp = _d(k, "capraz_payi")
    u = {"cevre": pol.length / 100, "dikme": dikme / 100, "kusak": kusak / 100}
    if capraz:
        u["capraz"] = H / 100 * (cp["a_m_m"] + cp["b_m_m2"] * L / 100)
    return u


def _acilim(dz: dict) -> Polygon:
    return dz["acilim"] if dz["acilim"].is_valid else dz["acilim"].buffer(0)


def _saciga_bol(pol: Polygon, n: int) -> list[Polygon]:
    """Açılımdaki çokgen saçak boyunca (u ekseni) n eşit şeride."""
    x0, y0, x1, y1 = pol.bounds
    out = []
    for j in range(n):
        p = pol.intersection(box(x0 + (x1 - x0) * j / n, y0 - 1, x0 + (x1 - x0) * (j + 1) / n, y1 + 1))
        for g in ([p] if p.geom_type == "Polygon" else list(getattr(p, "geoms", []))):
            if g.geom_type == "Polygon" and g.area > 1.0:
                out.append(g)
    return out


def cati_panelleri(c: dict, y: dict, k: dict) -> list[dict]:
    """Tanımda çatı paneli yazan düzlemler (`ust_yapi: cati_paneli`): açılım saçak boyunca `cati_paneli_adedi` eşit panele."""
    cp = _d(k, "cati_paneli")
    out = []
    for dz in c["duzlemler"]:
        if dz.get("ust_yapi") != "cati_paneli":
            continue
        ek_yapi = any(b["sinif"] == "ek" and dz["cokgen"].contains(b["net"].representative_point()) for b in y["bolgeler"].values())
        et = cp["et_ek_yapi"] if ek_yapi else cp["et_acik_alan"]
        for j, p in enumerate(_saciga_bol(_acilim(dz), int(dz.get("cati_paneli_adedi", 1))), 1):
            u = panel_uyeleri(p, k)
            out.append({"duzlem": dz["ad"], "sira": j, "ortu": "ek yapı" if ek_yapi else "açık alan", "profil": f"80x45x{et}",
                        "olcu_cm": [round(p.bounds[2] - p.bounds[0], 2), round(p.bounds[3] - p.bounds[1], 2)],
                        "uyeler_m": {a: round(v, 4) for a, v in u.items()}, "profil_boyu_m": round(sum(u.values()), 4)})
    return out


def ust_panelleri(c: dict, k: dict) -> list[dict]:
    """Yöntem A'nın çatı üstü panelleri: makaslı her düzlemin açılımı saçak boyunca `bolme` hedefiyle eşit panellere."""
    hedef = _d(k, "bolme")["hedef_cm"]
    out = []
    for dz in c["duzlemler"]:
        if dz.get("ust_yapi") == "cati_paneli":
            continue
        pol = _acilim(dz)
        n = max(1, math.ceil((pol.bounds[2] - pol.bounds[0]) / hedef - 1e-9))
        for j, p in enumerate(_saciga_bol(pol, n), 1):
            u = panel_uyeleri(p, k)
            out.append({"duzlem": dz["ad"], "sira": j, "olcu_cm": [round(p.bounds[2] - p.bounds[0], 2), round(p.bounds[3] - p.bounds[1], 2)],
                        "uyeler_m": {a: round(v, 4) for a, v in u.items()}, "profil_boyu_m": round(sum(u.values()), 4)})
    return out


def tavan_panelleri(c: dict, y: dict, k: dict, mk: dict) -> list[dict]:
    """Yöntem A'nın tavan panelleri: ana ailenin makas aralıkları (uç duvarlara kadar) şerit; şerit her mahalle (ve verandayla)
    kesilir, her parça bir panel. Çatı paneli altındaki mahal ve çatısız veranda hariç."""
    tp = _d(k, "tavan_paneli")
    makasli = unary_union([d["cokgen"] for d in c["duzlemler"] if d.get("ust_yapi") != "cati_paneli"])
    panelli = [d["cokgen"] for d in c["duzlemler"] if d.get("ust_yapi") == "cati_paneli"]
    bolgeler = [b for b in y["bolgeler"].values() if b["sinif"] in ("ic", "ek", "veranda")
                and makasli.contains(b["net"].representative_point()) and not any(p.contains(b["net"].representative_point()) for p in panelli)]
    ana = [f for f in mk["aileler"] if f["ana"] and f["tur"] == "besik"]
    if not ana or not bolgeler:
        return []
    ex = ana[0]["eksen"]; ee = _oteki(ex)
    ana = [f for f in ana if f["eksen"] == ex]
    ie = _i(ee)
    tavan_geo = unary_union([b["net"] for b in bolgeler])
    lo, hi = tavan_geo.bounds[ie], tavan_geo.bounds[ie + 2]
    sinirlar = sorted({v for f in ana for v in f["konumlar"]} | {lo, hi})
    sinirlar = [v for v in sinirlar if lo - EPS <= v <= hi + EPS]
    out = []
    for a0, a1 in zip(sinirlar, sinirlar[1:]):
        if a1 - a0 < 1.0:
            continue
        bb = tavan_geo.bounds
        serit = box(a0, bb[1] - 1, a1, bb[3] + 1) if ee == "x" else box(bb[0] - 1, a0, bb[2] + 1, a1)
        for b in bolgeler:
            p = serit.intersection(b["net"])
            for g in ([p] if p.geom_type == "Polygon" else list(getattr(p, "geoms", []))):
                if g.geom_type != "Polygon" or g.area < 100.0:
                    continue
                u = panel_uyeleri(g, k, capraz=tp["capraz"])
                out.append({"mahal": b["ad"], "serit": [round(a0, 2), round(a1, 2)],
                            "olcu_cm": [round(g.bounds[2] - g.bounds[0], 2), round(g.bounds[3] - g.bounds[1], 2)],
                            "uyeler_m": {a: round(v, 4) for a, v in u.items()}, "profil_boyu_m": round(sum(u.values()), 4)})
    return out


def kur(t: dict, y: dict, k: dict, yontem: str | None = None) -> dict:
    """Çatının karkas kaydı: makaslar, çatı panelleri ve (yöntem A: `yontem == "panel"`) çatı üstü ve tavan panelleri."""
    c = cati_genel.cati_kur(t["cati"])
    mk = makaslar(t, c, y, k)
    out = {"makaslar": mk["makaslar"], "aileler": mk["aileler"], "baglanmayan_kirma_yuzleri": mk["baglanmayan_kirma_yuzleri"],
           "cati_panelleri": cati_panelleri(c, y, k)}
    if yontem == "panel":
        out["ust_panelleri"] = ust_panelleri(c, k)
        out["tavan_panelleri"] = tavan_panelleri(c, y, k, mk)
    return out
