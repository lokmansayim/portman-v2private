"""İE-43 · Montaj paftasından plan geometrisi ve İş Emri taslağı (disk arşivi, 2019–2020 prefabrik paftaları).

Paftanın çizgilerinden okunur, pafta düzeltilmez:
- duvar: 6 ya da 10 cm aralıklı paralel çizgi çifti (pano blokları açılarak); yalnız 0° ve 90° (v1);
- gövde: 10'luk duvarların dış kutusu; akslar 125,5 / 2 ızgarası, ızgaraya oturmayan duvar ek aks olur;
- oda: aks hücrelerinin duvarsız kenarlardan dolgusu, adı `pafta_kart`'ın oda yazısından (yazının noktası hangi bölgedeyse);
- açıklık: pano blokları (pencere, vasistas, kapı), ölçüsü en yakın açıklık yazısından;
- taşan veranda: gövdenin dışındaki kesik çizgili dikdörtgen ve kolon kareleri; köşedekilerden fazla kolon `ara_kolon` olur (D-109,
  `veranda_ara_kolonu`); paftanın makas planında ana çatı verandayı da örtüyorsa (elle okunur) veranda gövdenin açık mahali olur
  (`verandayi_govdeye_al`, `ev.py --ana-cati-verandasi`; D-129, D-131);
- pano dizilimi: her duvarın pano ekleri (bandı enine kesen, boyu duvar kalınlığı kadar çizgiler).
Okunamayan ya da emin olunmayan her şey `uyarilar`'a yazılır (K21); İş Emri'ndeki varsayımlar `varsayimlar`'a.

    python3 plan_geometri.py <dxf|dxf.gz> <kart.json> <plan sırası> <İş Emri çıktı.json> [--geo <geometri.json>]
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import re
import sys

from pathlib import Path
KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK)); sys.path.insert(0, str(Path(__file__).resolve().parent))
import pafta_kart as PK  # noqa: E402

MOD = 125.5
KAL = (6.0, 10.0)
TOL = 0.6
DISLA_KATMAN = ("TEFR", "ÖLÇÜ", "OLCU", "DIM", "YAZI", "TEXT", "ELEK", "AKS")
DISLA_BLOK = ("KLOZET", "LAVABO", "EVYE", "DUS", "TELPRIZ", "ANAHTAR", "GLOP", "FAUCET", "AVIZE", "LAMBA", "PRIZ")
# pano blokları (Astra v1.4.3 şablonu, 2019–2020 paftaları): ad → açıklık türü
ACIKLIK_BLOKLARI = {"BFGNBFGN": "pencere", "NSGNGHN": "vasistas", "DSGVFD": "kapi", "CXVZF": "celik_kapi"}
MAHAL_TURU = [(r"VERANDA|TERAS|SUNDURMA", "veranda"), (r"SALON|OTURMA", "salon"), (r"MUTFAK", "mutfak"),
              (r"Y\.?\s*ODA|YATAK|ÇOCUK|COCUK|ODA", "yatak_odasi"), (r"WC|BANYO|DUŞ|DUS|TUVALET|LAVABO", "banyo"),
              (r"HOL|ANTRE|GİRİŞ|GIRIS|KORİDOR|KORIDOR", "antre_hol")]


def mahal_turu(ad: str) -> str | None:
    for desen, tur in MAHAL_TURU:
        if re.search(desen, ad):
            return tur
    return None


# ------------------------------------------------------------------ çizgiler
KATMAN_KAPI = []        # dışlanan katmandaki kapı blokları (topla okur, geometri uyarır)


def _kapi_blogu(e) -> bool:
    """INSERT'in bloğunda kapı kanadı yayı (r 60–110) var mı."""
    try:
        return any(v.dxftype() == "ARC" and 60 <= v.dxf.radius <= 110 for v in e.block())
    except Exception:
        return False


def _disla(e, derin) -> bool:
    lay = e.dxf.layer.upper() if e.dxf.hasattr("layer") else ""
    if not any(lay.startswith(k) for k in DISLA_KATMAN):
        return False
    # ölçü katmanına konmuş kapı bloğu (çizen yanlış katmana koymuş): kapı olarak okunur
    return not (derin == 0 and e.dxftype() == "INSERT" and _kapi_blogu(e))


def _parcalar(ents, derin=0):
    for e in ents:
        t = e.dxftype()
        if _disla(e, derin):
            continue
        if t == "INSERT":
            if derin >= 3 or any(b in e.dxf.name.upper() for b in DISLA_BLOK):
                continue
            try:
                yield from _parcalar(e.virtual_entities(), derin + 1)
            except Exception:
                pass
        elif t == "LINE":
            yield (float(e.dxf.start.x), float(e.dxf.start.y)), (float(e.dxf.end.x), float(e.dxf.end.y))
        elif t in ("LWPOLYLINE", "POLYLINE"):
            try:
                if t == "LWPOLYLINE":
                    ocs, z = e.ocs(), e.dxf.elevation
                    P = [(lambda v, b: (float(v.x), float(v.y), b))(ocs.to_wcs((p[0], p[1], z)), p[4]) for p in e.get_points("xyseb")]
                    if ocs.uz.z < 0:          # aynalı: OCS'de pozitif çıkıntı WCS'de ters döner
                        P = [(x, y, -b) for x, y, b in P]
                    kapali = e.closed
                else:
                    P = [(v.dxf.location.x, v.dxf.location.y, v.dxf.bulge) for v in e.vertices]
                    kapali = e.is_closed
            except Exception:
                continue
            n = len(P)
            for i in range(n if kapali else n - 1):
                a, b = P[i], P[(i + 1) % n]
                if abs(a[2]) < 1e-6:
                    yield (float(a[0]), float(a[1])), (float(b[0]), float(b[1]))


def _kesik_mi(e, doc) -> bool:
    lt = (e.dxf.get("linetype", "BYLAYER") or "BYLAYER").upper()
    if lt == "BYLAYER":
        try:
            lt = doc.layers.get(e.dxf.layer).dxf.linetype.upper()
        except Exception:
            lt = ""
    return any(k in lt for k in ("ISO02", "ISO03", "DASH", "HIDDEN", "KESIK"))


TEFRIS = [("EVYE", "mutfak"), ("KIT SINK", "mutfak"), ("KITCHEN", "mutfak"), ("OCAK", "mutfak"),
          ("KLOZET", "banyo"), ("DUS", "banyo"), ("LAVABO", "banyo"), ("BANYO", "banyo")]


def _tefris_turu(e, doc) -> str | None:
    """Tefriş bloğunun türü: adından; adı anlamsızsa (2019 şablonunun mutfak tezgâhı "KDJFKLD") içindeki blokların adından
    (tezgâhın içinde "Faucet - kit sink top"). Bir kat iner."""
    ad = e.dxf.name.upper()
    tf = next((v for b, v in TEFRIS if b in ad), None)
    if tf:
        return tf
    try:
        blok = doc.blocks.get(e.dxf.name)
    except Exception:
        blok = None
    for x in (blok if blok is not None else ()):
        if x.dxftype() == "INSERT":
            tf = next((v for b, v in TEFRIS if b in x.dxf.name.upper()), None)
            if tf:
                return tf
    return None


OLCU_YAZI = re.compile(r"^\s*(\d{2,3})\s*/\s*(\d{2,3})\s*$")
OLCU_SATIR = re.compile(r"(?<![\d*/])(\d{2,3})\s*/\s*(\d{2,3})(?![\d*/])")
YUKSEKLIK_YAZI = re.compile(r"(?:\bH\s*=\s*|Y[ÜU]KSEKL[İI][ĞG][İI]\s*:?\s*)(\d{3})", re.I)
YUKSEKLIK = []          # topla'nın okuduğu yükseklik yazıları (cm), geometri() döndürür


def _yay_ekle(yaylar, merkez, r, a0, a1):
    a0, a1 = math.radians(a0), math.radians(a1)
    yaylar.append({"m": (float(merkez[0]), float(merkez[1])), "r": float(r),
                   "u": [(float(merkez[0] + r * math.cos(a)), float(merkez[1] + r * math.sin(a))) for a in (a0, a1)]})


def _yaylar(ents, yaylar, derin=0):
    from ezdxf.math import bulge_to_arc
    for e in ents:
        t = e.dxftype()
        if _disla(e, derin):
            continue
        if t == "ARC" and 60 <= e.dxf.radius <= 110:
            sp, ep = e.start_point, e.end_point          # WCS
            yaylar.append({"m": (lambda v: (float(v.x), float(v.y)))(e.ocs().to_wcs(e.dxf.center)), "r": float(e.dxf.radius),
                           "u": [(float(sp.x), float(sp.y)), (float(ep.x), float(ep.y))]})
        elif t == "LWPOLYLINE":
            ocs, z = e.ocs(), e.dxf.elevation
            P = list(e.get_points("xyb"))
            n = len(P)
            for i in range(n if e.closed else n - 1):
                a, b = P[i], P[(i + 1) % n]
                if abs(a[2]) > 1e-6:
                    m, sa, ea, r = bulge_to_arc((a[0], a[1]), (b[0], b[1]), a[2])
                    if 60 <= r <= 110:
                        u = [ocs.to_wcs((q[0], q[1], z)) for q in (a, b)]
                        mw = ocs.to_wcs((m.x, m.y, z))
                        yaylar.append({"m": (float(mw.x), float(mw.y)), "r": float(r), "u": [(float(q.x), float(q.y)) for q in u]})
        elif t == "INSERT" and derin < 2:
            ad = e.dxf.name.upper()
            if any(b in ad for b in ACIKLIK_BLOKLARI) or any(b in ad for b in DISLA_BLOK):
                continue
            try:
                _yaylar(e.virtual_entities(), yaylar, derin + 1)
            except Exception:
                pass


def topla(doc, kutu):
    """Kutudaki çizgi parçaları, açıklık blokları, kesik çizgiler, küçük kareler, kapı yayları, açıklık yazıları ve tefriş blokları
    (dünya koordinatı)."""
    from ezdxf import bbox as BB
    x0, y0, x1, y1 = kutu
    S, bloklar, kesik, kare, yaylar, olcu_yazi, tefris = [], [], [], [], [], [], []
    for e, k in PK.oge_kutulari(doc.modelspace()):
        if not (k[2] >= x0 and k[0] <= x1 and k[3] >= y0 and k[1] <= y1):
            continue
        k = [float(v) for v in k]
        t = e.dxftype()
        if t in ("TEXT", "MTEXT"):
            yazi = e.plain_text() if t == "MTEXT" else e.dxf.text
            for satir in (yazi or "").splitlines():
                m_ = OLCU_SATIR.search(satir)
                if m_ and 30 <= int(m_.group(1)) <= 400 and 20 <= int(m_.group(2)) <= 240:
                    olcu_yazi.append({"olcu": [int(m_.group(1)), int(m_.group(2))], "m": ((k[0] + k[2]) / 2, (k[1] + k[3]) / 2),
                                      "surgulu": "SÜRGÜ" in yazi.upper() or "SURGU" in yazi.upper()})
                    break
            m_ = YUKSEKLIK_YAZI.search(yazi or "")
            if m_ and 200 <= int(m_.group(1)) <= 400:
                YUKSEKLIK.append(int(m_.group(1)))
            continue
        if t == "INSERT":
            ad = e.dxf.name.upper()
            lay = e.dxf.layer.upper()
            if any(lay.startswith(k_) for k_ in DISLA_KATMAN) and not _disla(e, 0):
                KATMAN_KAPI.append(f"{e.dxf.name} ({e.dxf.layer} katmanında)")
            tf = _tefris_turu(e, doc)
            if tf:
                tefris.append({"tur": tf, "m": ((k[0] + k[2]) / 2, (k[1] + k[3]) / 2)})
            tur = next((v for b, v in ACIKLIK_BLOKLARI.items() if b in ad), None)
            if tur:
                bloklar.append({"tur": tur, "blok": e.dxf.name, "kutu": list(k), "aci": round(e.dxf.rotation % 360, 1),
                                "ayna": (e.dxf.xscale < 0) != (e.dxf.yscale < 0)})
        if t in ("LINE", "LWPOLYLINE") and _kesik_mi(e, doc):
            kesik.extend(_ham([e]))
            continue
        if t == "LWPOLYLINE" and e.closed and k[2] - k[0] <= 12.5 and k[3] - k[1] <= 12.5 and abs((k[2] - k[0]) - (k[3] - k[1])) < 0.6:
            kare.append(list(k))
        _yaylar([e], yaylar)
        for a, b in _parcalar([e]):
            L = math.dist(a, b)
            if L >= 3:
                S.append((a, b, L, math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180))
    return S, bloklar, kesik, kare, yaylar, olcu_yazi, tefris


def _ham(ents):
    for e in ents:
        if e.dxftype() == "LINE":
            yield (e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)
        else:
            ocs, z = e.ocs(), e.dxf.elevation
            P = [(lambda v: (float(v.x), float(v.y)))(ocs.to_wcs((p[0], p[1], z))) for p in e.get_points("xy")]
            for i in range(len(P) - (0 if e.closed else 1)):
                yield P[i], P[(i + 1) % len(P)]


# ------------------------------------------------------------------ duvar bantları
def bantlar(S):
    """Yatay ve düşey duvar bantları: {yon: 'x' (düşey duvar, x sabit) | 'y' (yatay, y sabit), c, s0, s1, t, ekler}."""
    kova = collections.defaultdict(list)
    for a, b, L, aci in S:
        q = round(aci * 2) / 2 % 180
        if q in (0.0, 90.0):
            kova[q].append((a, b))
    duvar = []
    for q, C in kova.items():
        H = []
        for a, b in C:
            if q == 0.0:
                H.append(((a[1] + b[1]) / 2, *sorted((a[0], b[0]))))
            else:
                H.append(((a[0] + b[0]) / 2, *sorted((a[1], b[1]))))
        H.sort()
        bant = []
        for i in range(len(H)):
            oi, a0, a1 = H[i]
            j = i + 1
            while j < len(H) and H[j][0] - oi <= max(KAL) + TOL:
                oj, b0, b1 = H[j]
                t = next((k_ for k_ in KAL if abs(oj - oi - k_) <= TOL), None)
                if t:
                    s0, s1 = max(a0, b0), min(a1, b1)
                    if s1 - s0 >= 10:
                        bant.append({"yon": "y" if q == 0.0 else "x", "c": (oi + oj) / 2, "t": t, "s0": s0, "s1": s1})
                j += 1
        bant.sort(key=lambda b: (b["t"], round(b["c"]), b["s0"]))
        for b in bant:
            if duvar and duvar[-1]["yon"] == b["yon"] and duvar[-1]["t"] == b["t"] and abs(duvar[-1]["c"] - b["c"]) < 1.0 \
                    and b["s0"] <= duvar[-1]["s1"] + 0.5:
                duvar[-1]["s1"] = max(duvar[-1]["s1"], b["s1"])
            else:
                duvar.append(dict(b))
    for w in duvar:            # ekler: bandı enine kesen, boyu ≈ kalınlık olan çizgiler
        ek = set()
        for a, b, L, aci in S:
            if abs(L - w["t"]) > TOL + 0.2:
                continue
            q = round(aci * 2) / 2 % 180
            if (w["yon"] == "y" and q != 90.0) or (w["yon"] == "x" and q != 0.0):
                continue
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            c, s = (my, mx) if w["yon"] == "y" else (mx, my)
            if abs(c - w["c"]) <= 0.8 and w["s0"] - 0.5 <= s <= w["s1"] + 0.5:
                ek.add(round(s, 1))
        w["ekler"] = sorted(ek)
    return [w for w in duvar if w["s1"] - w["s0"] >= 15]


def _uc(w, s):
    return (s, w["c"]) if w["yon"] == "y" else (w["c"], s)


def _yakin(p, w, pay=3.0):
    """p noktası w duvarının bandına (uçlarda payla) değiyor mu."""
    px, py = p
    s, c = (px, py) if w["yon"] == "y" else (py, px)
    return w["s0"] - pay - 6 <= s <= w["s1"] + pay + 6 and abs(c - w["c"]) <= pay + w["t"] / 2 + 6


def _blokta(p, k, pay=3.0):
    return k[0] - pay <= p[0] <= k[2] + pay and k[1] - pay <= p[1] <= k[3] + pay


def bagli_duvarlar(W, kutular=()):
    """Bir ucu (120 cm'den uzunsa) ya da iki ucu başka bir duvara değen bantlar. Açıklık bloğu duvar çizgisini taşımaz: ucu bloğa
    değen bant da bağlıdır (bandın kendisi bloğun içinde değilse)."""
    tut = []
    for w in W:
        a, b = _uc(w, w["s0"]), _uc(w, w["s1"])
        icte = any(_blokta(a, k) and _blokta(b, k) for k in kutular)
        ba = any(v is not w and _yakin(a, v) for v in W) or (not icte and any(_blokta(a, k) for k in kutular))
        bb = any(v is not w and _yakin(b, v) for v in W) or (not icte and any(_blokta(b, k) for k in kutular))
        if (ba and bb) or (w["s1"] - w["s0"] >= 120 and (ba or bb)):
            tut.append(w)
    # ayrıntı bandı: daha uzun paralel bir duvarın hemen yanında ya da içinde (pencere kasası, duş teknesi)
    def ayrinti(w):
        for v in tut:
            if v is w or v["yon"] != w["yon"] or (v["s1"] - v["s0"]) <= (w["s1"] - w["s0"]):
                continue
            if abs(v["c"] - w["c"]) <= (v["t"] + w["t"]) / 2 + 3 and min(v["s1"], w["s1"]) - max(v["s0"], w["s0"]) > 0.5 * (w["s1"] - w["s0"]):
                return True
        return False
    return [w for w in tut if not ayrinti(w)]


# ------------------------------------------------------------------ geometri
def geometri(doc, kutu, plan):
    U = []
    YUKSEKLIK.clear()
    KATMAN_KAPI.clear()
    S, bloklar, kesik, kare, yaylar, olcu_yazi, tefris = topla(doc, kutu)
    for k_ in sorted(set(KATMAN_KAPI)):
        U.append(f"kapı bloğu {k_}: kapı olarak okundu")
    W = bagli_duvarlar(bantlar(S), [b["kutu"] for b in bloklar if b["tur"] in ("pencere", "vasistas")])
    dis = [w for w in W if w["t"] == 10.0]
    if len(dis) < 4:
        raise ValueError(f"dış duvar bulunamadı ({len(dis)} 10'luk bant)")
    xs = [p[0] for w in dis for p in (_uc(w, w["s0"]), _uc(w, w["s1"]))]
    ys = [p[1] for w in dis for p in (_uc(w, w["s0"]), _uc(w, w["s1"]))]
    X0, X1, Y0, Y1 = min(xs) - 5, max(xs) + 5, min(ys) - 5, max(ys) + 5
    Wb, Hb = round(X1 - X0, 2), round(Y1 - Y0, 2)
    kisa = "y" if Hb <= Wb else "x"
    boy = {"x": Wb, "y": Hb}
    mx = lambda x: x - X0           # Motor çerçevesi (arka-sol): x soldan, y arkadan (arka = çizimin üstü)
    my = lambda y: Y1 - y
    # köşe düzeni paftadan: yatay dış duvarlar köşeden geçiyorsa (x 5'ten başlar) düşey dış duvarlar 10'dan başlar → kısa kenar y
    bas = {"x": [], "y": []}
    for w in dis:
        c_ = mx(w["c"]) if w["yon"] == "x" else my(w["c"])
        if abs(c_ - 5) < 1.5 or abs(c_ - (boy[w["yon"]] - 5)) < 1.5:
            u = sorted((my(w["s0"]), my(w["s1"]))) if w["yon"] == "x" else sorted((mx(w["s0"]), mx(w["s1"])))
            bas[w["yon"]] += [u[0], boy["y" if w["yon"] == "x" else "x"] - u[1]]
    yat = [v for v in bas["y"] if v < 15]; dus = [v for v in bas["x"] if v < 15]
    if yat and dus:
        if all(abs(v - 5) < 1.5 for v in yat) and all(abs(v - 10) < 1.5 for v in dus):
            kisa_p = "y"
        elif all(abs(v - 10) < 1.5 for v in yat) and all(abs(v - 5) < 1.5 for v in dus):
            kisa_p = "x"
        else:
            kisa_p = None
        if kisa_p and kisa_p != kisa:
            U.append(f"köşe düzeni paftadan: kısa kenar {kisa_p} (ölçüye göre {kisa} olurdu; {Wb:g} × {Hb:g})")
            kisa = kisa_p
    ilk = {"x": 10.0 if kisa == "x" else 5.0, "y": 10.0 if kisa == "y" else 5.0}

    def izgara(yon, v):
        k = (v - ilk[yon]) / (MOD / 2)
        return abs(k - round(k)) * MOD / 2 <= 1.5, round(ilk[yon] + round(k) * MOD / 2, 2)

    duv, ek = [], {"x": set(), "y": set()}
    for w in W:
        c = mx(w["c"]) if w["yon"] == "x" else my(w["c"])
        a0, a1 = sorted((my(w["s0"]), my(w["s1"]))) if w["yon"] == "x" else sorted((mx(w["s0"]), mx(w["s1"])))
        dis_mi = w["t"] == 10.0 and (abs(c - 5) < 1.5 or abs(c - (boy[w["yon"]] - 5)) < 1.5)
        if dis_mi:
            v = ilk[w["yon"]] if c < boy[w["yon"]] / 2 else boy[w["yon"]] - ilk[w["yon"]]
        else:
            ok, g = izgara(w["yon"], c)
            ayni_hat = any(w2 is not w and w2["yon"] == w["yon"] and abs((mx(w2["c"]) if w2["yon"] == "x" else my(w2["c"])) - c) <= 1.0
                           for w2 in W)
            if not ok and w["t"] == 10.0 and not ayni_hat:   # gövdenin içindeki dış duvar (veranda, niş): yüzü akstaysa o aksın duvarıdır
                for yz in (c - 5, c + 5):
                    ok2, g2 = izgara(w["yon"], yz)
                    if ok2:
                        ok, g = True, g2
                        U.append(f"10'luk duvar {w['yon']}={c:.1f}: yüzü {g2:g} aksında (ekseni aksın {c - g2:+.1f} cm yanında); Motor aksa ortalar")
                        break
            v = g if ok else round(c, 2)
            if not ok:
                ek[w["yon"]].add(v)
        ekler = sorted({round(my(s) if w["yon"] == "x" else mx(s), 1) for s in w["ekler"]})
        duv.append({"yon": w["yon"], "aks": v, "c": round(c, 2), "a0": round(a0, 2), "a1": round(a1, 2), "t": w["t"], "dis": dis_mi,
                    "ekler": ekler})
    # ızgara dışı akslar: 1 cm içindekiler tek aks (aynı hattaki 10'luk ve 6'lık duvar)
    for k in ("x", "y"):
        es = sorted(ek[k]); bir = {}
        for v in es:
            o = next((u for u in bir.values() if abs(u - v) <= 1.0), None)
            bir[v] = o if o is not None else v
        ek[k] = set(bir.values())
        for d in duv:
            if d["yon"] == k and d["aks"] in bir:
                d["aks"] = bir[d["aks"]]
    # aynı hattaki dış duvar parçaları arasındaki ≤ 130 cm boşluk bir açıklık bloğunun yeriyse (blok duvar çizgisini taşımaz) duvar birleşir
    def blok_bosluk(yon, c, lo, hi):
        for b in bloklar:
            k_ = b["kutu"]
            bx0, bx1 = sorted((mx(k_[0]), mx(k_[2]))); by0, by1 = sorted((my(k_[1]), my(k_[3])))
            dik, b0, b1 = ((bx0 + bx1) / 2, by0, by1) if yon == "x" else ((by0 + by1) / 2, bx0, bx1)
            if abs(dik - c) <= 8 and b0 <= lo + 3 and b1 >= hi - 3:
                return True
        return False
    birlesti = True
    while birlesti:
        birlesti = False
        for d1 in duv:
            for d2 in duv:
                if d1 is d2 or d1["yon"] != d2["yon"] or not (d1["dis"] and d2["dis"]) or abs(d1["c"] - d2["c"]) > 0.6 or d1["a1"] > d2["a0"]:
                    continue
                if d2["a0"] - d1["a1"] <= 130 and blok_bosluk(d1["yon"], d1["c"], d1["a1"], d2["a0"]):
                    d1["a1"] = d2["a1"]; d1["ekler"] = sorted(set(d1["ekler"]) | set(d2["ekler"]))
                    duv.remove(d2); birlesti = True
                    break
            if birlesti:
                break
    # duvar çizgisi olmayan kapı: yayın menteşesi ızgaradaki bir aksta, iki ucunda ona dik duvar varsa kapının duvarı o akstadır
    # (çizen kapı bloğunu duvarın yerine koymuş; duvar kapının iki yanındaki dik duvarların yüzleri arasında, 6'lık)
    def yay_duvarda(y_):
        for d in duv:
            for (bx, by), (tx, ty) in ((y_["u"][0], y_["u"][1]), (y_["u"][1], y_["u"][0])):
                bc, bb = (mx(bx), my(by)) if d["yon"] == "x" else (my(by), mx(bx))
                tc, tb = (mx(tx), my(ty)) if d["yon"] == "x" else (my(ty), mx(tx))
                if abs(bc - d["c"]) <= d["t"] / 2 + 4 and d["a0"] - 6 <= bb <= d["a1"] + 6 and 55 <= abs(tb - bb) <= 110 \
                        and 50 <= abs(tc - d["c"]) <= 115 and d["a0"] - 6 <= tb <= d["a1"] + 6:
                    return True
        return False
    for y_ in yaylar:
        if yay_duvarda(y_):
            continue
        m_ = (mx(y_["m"][0]), my(y_["m"][1]))
        for yon in ("x", "y"):
            dik_i, boy_i = (0, 1) if yon == "x" else (1, 0)          # x duvarı: dik koordinat x, boyu y
            uc = [(mx(u[0]), my(u[1])) for u in y_["u"]]
            B = next((u for u in uc if abs(u[dik_i] - m_[dik_i]) <= 3 and 55 <= abs(u[boy_i] - m_[boy_i]) <= 110), None)
            T = next((u for u in uc if u is not B and abs(u[boy_i] - m_[boy_i]) <= 3), None)
            if B is None or T is None:
                continue
            k = (m_[dik_i] - ilk[yon]) / (MOD / 2)
            v = round(ilk[yon] + round(k) * MOD / 2, 2)
            if abs(v - m_[dik_i]) > 8:
                continue
            lo_, hi_ = sorted((m_[boy_i], B[boy_i]))
            dik = [d for d in duv if d["yon"] != yon and d["a0"] - 6 <= v <= d["a1"] + 6]
            alt_ = [d for d in dik if lo_ - 60 <= d["c"] <= lo_ + 3]
            ust_ = [d for d in dik if hi_ - 3 <= d["c"] <= hi_ + 60]
            if not alt_ or not ust_:
                continue
            da, du = max(alt_, key=lambda d: d["c"]), min(ust_, key=lambda d: d["c"])
            a0_, a1_ = round(da["c"] + da["t"] / 2, 2), round(du["c"] - du["t"] / 2, 2)
            if any(d["yon"] == yon and abs(d["aks"] - v) < 0.6 and min(d["a1"], a1_) - max(d["a0"], a0_) > 5 for d in duv):
                continue
            duv.append({"yon": yon, "aks": v, "c": v, "a0": a0_, "a1": a1_, "t": 6.0, "dis": False, "ekler": [], "kaynak": "yay"})
            U.append(f"kapının duvarı yaydan: {yon}={v:g} {a0_:g}–{a1_:g} (paftada bu kapının yanında duvar çizgisi yok; 6'lık sayıldı)")
            break
    AX = sorted({d["aks"] for d in duv if d["yon"] == "x"} | {ilk["x"], Wb - ilk["x"]})
    AY = sorted({d["aks"] for d in duv if d["yon"] == "y"} | {ilk["y"], Hb - ilk["y"]})

    def kaplama(yon, v, lo, hi):
        ar = sorted((max(lo, d["a0"] - 6), min(hi, d["a1"] + 6)) for d in duv if d["yon"] == yon and abs(d["aks"] - v) < 0.6)
        top, cur = 0.0, None
        for a, b in ar:
            if b <= a:
                continue
            if cur is None:
                cur = [a, b]
            elif a <= cur[1]:
                cur[1] = max(cur[1], b)
            else:
                top += cur[1] - cur[0]
                cur = [a, b]
        if cur:
            top += cur[1] - cur[0]
        return top / (hi - lo)

    nX, nY = len(AX) - 1, len(AY) - 1
    sag = lambda i, j: kaplama("x", AX[i + 1], AY[j], AY[j + 1]) >= 0.5      # hücrenin sağ kenarında duvar
    alt = lambda i, j: kaplama("y", AY[j + 1], AX[i], AX[i + 1]) >= 0.5      # alt (öne bakan) kenarında
    grup, G = {}, []
    for c in [(i, j) for i in range(nX) for j in range(nY)]:
        if c in grup:
            continue
        st, g = [c], {c}
        grup[c] = len(G)
        while st:
            i, j = st.pop()
            for ni, nj, ok in ((i + 1, j, i + 1 < nX and not sag(i, j)), (i - 1, j, i > 0 and not sag(i - 1, j)),
                               (i, j + 1, j + 1 < nY and not alt(i, j)), (i, j - 1, j > 0 and not alt(i, j - 1))):
                if ok and (ni, nj) not in grup:
                    grup[(ni, nj)] = len(G)
                    g.add((ni, nj))
                    st.append((ni, nj))
        G.append(g)
    def dis_bolge(g_):
        """Bölgenin bir hücresi gövde kutusunun kenarındaysa ve orada dış duvar yoksa bölge dışarıdır (girinti ya da gövdedeki veranda)."""
        for i, j in g_:
            if (i == 0 and kaplama("x", AX[0], AY[j], AY[j + 1]) < 0.5) or (i == nX - 1 and kaplama("x", AX[nX], AY[j], AY[j + 1]) < 0.5) \
                    or (j == 0 and kaplama("y", AY[0], AX[i], AX[i + 1]) < 0.5) or (j == nY - 1 and kaplama("y", AY[nY], AX[i], AX[i + 1]) < 0.5):
                return True
        return False

    # kutu profil kolon iki kare çizilir (dış ve iç yüz): içteki kare ayrı kolon değildir
    kare = [k for k in kare if not any(o is not k and o[0] - 0.1 <= k[0] and o[1] - 0.1 <= k[1] and k[2] <= o[2] + 0.1 and k[3] <= o[3] + 0.1
                                       and (o[2] - o[0]) > (k[2] - k[0]) for o in kare)]
    kolonlar = [[round(mx(k[0]), 1), round(my(k[3]), 1), round(mx(k[2]), 1), round(my(k[1]), 1)] for k in kare]
    kesik_m = [(mx(a[0]), my(a[1]), mx(b[0]), my(b[1])) for a, b in kesik]
    # oda yazıları: pafta_kart'ın kutusundan dünyaya, oradan Motor çerçevesine
    P0 = plan["kutu_dunya"]
    yazilar = [{"ad": m["ad"], "m2": m["m2"], "x": round(mx(P0[0] + m["x"]), 1), "y": round(my(P0[1] + m["y"]), 1)}
               for m in plan["mahaller"]]

    def hucre(x, y):
        i = next((k for k in range(nX) if AX[k] - 5 <= x <= AX[k + 1] + 5), None)
        j = next((k for k in range(nY) if AY[k] - 5 <= y <= AY[k + 1] + 5), None)
        return (i, j) if i is not None and j is not None else None

    bolge_ad = collections.defaultdict(list)
    disari = []
    for y_ in yazilar:
        h = hucre(y_["x"], y_["y"])
        if h is None or not (0 <= y_["x"] <= Wb and 0 <= y_["y"] <= Hb):
            disari.append(y_)
        else:
            bolge_ad[grup[h]].append(y_)
    odalar = []
    for k, g in enumerate(G):
        alan = sum((AX[i + 1] - AX[i]) * (AY[j + 1] - AY[j]) for i, j in g) / 1e4
        ad = bolge_ad.get(k, [])
        if len(ad) > 1:
            U.append(f"bölge {k}: birden çok oda yazısı {[a['ad'] for a in ad]} (aradaki duvar okunamadı)")
        if not ad and not dis_bolge(g):
            U.append(f"bölge {k}: oda yazısı yok ({alan:.2f} m² aks alanı)")
        dis_ = dis_bolge(g)
        x_lo, x_hi = min(AX[i] for i, j in g), max(AX[i + 1] for i, j in g)
        y_lo, y_hi = min(AY[j] for i, j in g), max(AY[j + 1] for i, j in g)
        icinde = lambda x, y: x_lo - 12 <= x <= x_hi + 12 and y_lo - 12 <= y <= y_hi + 12
        kol = [q for q in kolonlar if dis_ and icinde((q[0] + q[2]) / 2, (q[1] + q[3]) / 2)]
        kes_ = sum(1 for q in kesik_m if dis_ and icinde(q[0], q[1]) and icinde(q[2], q[3]))
        tf = [t["tur"] for t in tefris if any(AX[i] <= mx(t["m"][0]) <= AX[i + 1] and AY[j] <= my(t["m"][1]) <= AY[j + 1] for i, j in g)]
        odalar.append({"bolge": k, "hucreler": sorted(g), "aks_m2": round(alan, 2), "yazilar": ad, "dis": dis_, "kolonlar": kol,
                       "kesik": kes_, "tefris": sorted(set(tf))})
    # açıklıklar: blok → duvar, yön, iki yanındaki bölge
    ac = []
    for b in bloklar:
        bx0, by0, bx1, by1 = b["kutu"]
        k_ = [mx(bx0), my(by1), mx(bx1), my(by0)]          # Motor çerçevesinde kutu
        aday = []
        for d in duv:
            if d["yon"] == "x":
                if k_[0] - 3 <= d["c"] <= k_[2] + 3 and min(k_[3], d["a1"]) - max(k_[1], d["a0"]) > 30:
                    lo, hi = max(k_[1], d["a0"]), min(k_[3], d["a1"])
                    aday.append((d, lo, hi))
            else:
                if k_[1] - 3 <= d["c"] <= k_[3] + 3 and min(k_[2], d["a1"]) - max(k_[0], d["a0"]) > 30:
                    lo, hi = max(k_[0], d["a0"]), min(k_[2], d["a1"])
                    aday.append((d, lo, hi))
        if not aday:
            U.append(f"açıklık bloğu duvarda değil: {b['blok']} {[round(v) for v in k_]}")
            continue
        # kapı bloğu yayı da kapsar: pano boyu yönündeki aralığı en uzun, kutusunun ortasına en yakın duvar
        d, lo, hi = max(aday, key=lambda t: (t[2] - t[1], -abs(t[0]["c"] - ((k_[0] + k_[2]) / 2 if t[0]["yon"] == "x" else (k_[1] + k_[3]) / 2))))
        if b["tur"] in ("kapi", "celik_kapi"):              # kapının panosu: duvar boyunca blok kutusunun pano boyu (yay dikine)
            pass
        orta = (lo + hi) / 2
        ac.append({"tur": b["tur"], "blok": b["blok"], "kaynak": "blok", "duvar_yon": d["yon"], "aks": d["aks"], "c": d["c"], "dis": d["dis"],
                   "bas": round(lo, 2), "bit": round(hi, 2), "orta": round(orta, 2)})
        if b["tur"] in ("kapi", "celik_kapi"):              # açılma yanı: kanadın yayı blok kutusunu duvarın o yanına taşır
            dik = (k_[0] + k_[2]) / 2 if d["yon"] == "x" else (k_[1] + k_[3]) / 2
            if abs(dik - d["c"]) > 15:
                ac[-1]["acilim_yani"] = 1 if dik > d["c"] else 0

    def ayni_yerde(yon, c, lo, hi):
        return any(a["duvar_yon"] == yon and abs(a["c"] - c) < 3 and min(a["bit"], hi) - max(a["bas"], lo) > 20 for a in ac)

    for y_ in yaylar:          # kapı: yayın bir ucu duvar hattında (B), öteki ucu kanadın ucu (T); menteşe T'nin duvara izdüşümü
        bul = None
        for d in duv:
            for (bx, by), (tx, ty) in ((y_["u"][0], y_["u"][1]), (y_["u"][1], y_["u"][0])):
                bc, bb = (mx(bx), my(by)) if d["yon"] == "x" else (my(by), mx(bx))
                tc, tb = (mx(tx), my(ty)) if d["yon"] == "x" else (my(ty), mx(tx))
                if abs(bc - d["c"]) > d["t"] / 2 + 4 or not d["a0"] - 6 <= bb <= d["a1"] + 6:
                    continue
                gen, cik = abs(tb - bb), abs(tc - d["c"])
                if 55 <= gen <= 110 and 50 <= cik <= 115 and d["a0"] - 6 <= tb <= d["a1"] + 6:
                    bul = (d, min(bb, tb), max(bb, tb), 1 if tc > d["c"] else 0)
        if bul is None:
            continue
        d, lo, hi, yan = bul
        if ayni_yerde(d["yon"], d["c"], lo, hi):
            continue
        ac.append({"tur": "kapi", "blok": None, "kaynak": "yay", "genislik": round(hi - lo, 1), "duvar_yon": d["yon"], "aks": d["aks"],
                   "c": d["c"], "dis": d["dis"], "bas": round(lo, 2), "bit": round(hi, 2), "orta": round((lo + hi) / 2, 2),
                   "acilim_yani": yan})
    for y_ in olcu_yazi:                                # pencere: ölçü yazısına en yakın 10'luk duvar (60 cm içinde)
        px, py = mx(y_["m"][0]), my(y_["m"][1])
        en = None
        for d in duv:
            if d["t"] != 10.0:
                continue
            ic_, boy_ = (px, py) if d["yon"] == "x" else (py, px)
            if not d["a0"] <= boy_ <= d["a1"]:
                continue
            u = abs(ic_ - d["c"])
            if u <= 60 and (en is None or u < en[0]):
                en = (u, d, boy_)
        if en is None:
            U.append(f"açıklık yazısı duvara yakın değil: {y_['olcu']} ({px:.0f}, {py:.0f})")
            continue
        _, d, boy_ = en
        E = [d["a0"]] + [e for e in d["ekler"] if d["a0"] + 1 < e < d["a1"] - 1] + [d["a1"]]
        w = y_["olcu"][0]
        # pencere kasası çizgileri (aralığı pencere eni kadar, yazı arasında) pano eki değil
        kasa = {e for e in E for f in E if e < boy_ < f and abs(f - e - w) <= 1.5}
        E = [e for e in E if e not in kasa or e in (d["a0"], d["a1"])]
        # pano eki yarım modül ızgarasındadır: ızgarada en az iki komşusu olmayan tek kasa çizgisi (öteki kasa çizgisi yoksa) elenir
        def izgarada(e):
            return e in (d["a0"], d["a1"]) or sum(1 for f in E if f != e and min((f - e) % (MOD / 2), MOD / 2 - (f - e) % (MOD / 2)) <= 1.5) >= 2
        ust = math.ceil((w + 4) / MOD - 1e-9) * MOD + 3 if w > MOD - 4 else 1.5 * MOD     # panodan geniş pencere: 251'lik (ya da daha çok) pano
        cift = [(a, b) for a in E for b in E if a <= boy_ <= b and w + 3 <= b - a <= ust and izgarada(a) and izgarada(b)] or \
               [(a, b) for a in E for b in E if a <= boy_ <= b and w + 3 <= b - a <= ust]
        if cift:
            lo, hi = min(cift, key=lambda ab: ab[1] - ab[0])                  # pencereyi içine alan en dar pano
        else:
            lo, hi = boy_ - w / 2, boy_ + w / 2                              # pano eki yok: yazının hizası (yaklaşık)
        if ayni_yerde(d["yon"], d["c"], lo, hi):
            continue
        ac.append({"tur": "pencere", "blok": None, "kaynak": "yazi", "olcu": y_["olcu"], "duvar_yon": d["yon"], "aks": d["aks"],
                   "c": d["c"], "dis": d["dis"], "bas": round(lo, 2), "bit": round(hi, 2), "orta": round((lo + hi) / 2, 2),
                   "surgulu": y_.get("surgulu", False)})
    # kapısız geçiş: iki ayrı bölgenin arasındaki iç aks çizgisinde duvarın çizilmediği ≥ 50 cm'lik parça (kapı ya da pencere orada değilse)
    def bosluklar(yon, v, lo, hi):
        ar = sorted((max(lo, d["a0"]), min(hi, d["a1"])) for d in duv if d["yon"] == yon and abs(d["aks"] - v) < 0.6 and d["a1"] > lo and d["a0"] < hi)
        R, cur = [], lo
        for a_, b_ in ar:
            if a_ > cur:
                R.append((cur, a_))
            cur = max(cur, b_)
        if cur < hi:
            R.append((cur, hi))
        return R
    for yon, A, B, n_ in (("x", AX, AY, nX), ("y", AY, AX, nY)):
        for k in range(1, n_):
            for j in range(len(B) - 1):
                c1, c2 = ((k - 1, j), (k, j)) if yon == "x" else ((j, k - 1), (j, k))
                if grup.get(c1) == grup.get(c2) or c1 not in grup or c2 not in grup:
                    continue
                kesen = {d_["aks"]: d_["t"] for d_ in duv if d_["yon"] != yon and d_["a0"] - 1 <= A[k] <= d_["a1"] + 1}
                for lo, hi in bosluklar(yon, A[k], B[j], B[j + 1]):
                    kenar = [lo, hi]
                    lo += kesen.get(lo, 0) / 2 if lo == B[j] else 0           # kesen duvarın yüzünden
                    hi -= kesen.get(hi, 0) / 2 if hi == B[j + 1] else 0
                    c_ = next((d_["c"] for d_ in duv if d_["yon"] == yon and abs(d_["aks"] - A[k]) < 0.6), A[k])
                    if hi - lo >= 50 and not ayni_yerde(yon, c_, lo, hi):
                        ac.append({"tur": "gecis", "blok": None, "kaynak": "bosluk", "genislik": round(hi - lo, 1), "duvar_yon": yon, "aks": A[k],
                                   "c": c_, "dis": False, "bas": round(lo, 2), "bit": round(hi, 2), "orta": round((lo + hi) / 2, 2),
                                   "kenar": kenar})
    # açıklık bloğunun içindeki çizgiler (kapı boşluğu, kasa) pano eki değildir; yaydan okunan kapının kasası boşluktan 6 cm'ye kadar dışarıda
    for d in duv:
        for a in ac:
            if a["duvar_yon"] == d["yon"] and abs(a["c"] - d["c"]) < 1.0:
                pay = 6 if a.get("kaynak") == "yay" else -1
                d["ekler"] = [e for e in d["ekler"] if not a["bas"] - pay < e < a["bit"] + pay]
    # taşan veranda: gövdenin dışındaki kesik çizgiler
    # İE-43 PR-7: eğik kesik çizgi (notun gösterme çizgisi, "dışarıya musluk çekilecek") veranda kenarı değildir; bir cephede veranda
    # ancak o cepheye paralel ve gövdenin tamamen dışında bir kesik çizgi (verandanın dış kenarı) varsa okunur
    kes = []
    for a, b in kesik:
        ax_, ay_, bx_, by_ = mx(a[0]), my(a[1]), mx(b[0]), my(b[1])
        if abs(ax_ - bx_) > 1 and abs(ay_ - by_) > 1:
            continue
        if min(ax_, bx_) < -1 or max(ax_, bx_) > Wb + 1 or min(ay_, by_) < -1 or max(ay_, by_) > Hb + 1:
            kes.append((ax_, ay_, bx_, by_))
    dis_kenar = {"on": lambda q: abs(q[1] - q[3]) <= 1 and min(q[1], q[3]) > Hb + 1,
                 "arka": lambda q: abs(q[1] - q[3]) <= 1 and max(q[1], q[3]) < -1,
                 "sol": lambda q: abs(q[0] - q[2]) <= 1 and max(q[0], q[2]) < -1,
                 "sag": lambda q: abs(q[0] - q[2]) <= 1 and min(q[0], q[2]) > Wb + 1}
    verandalar = []
    if kes:
        for cephe, sec in (("on", lambda q: max(q[1], q[3]) > Hb + 1), ("arka", lambda q: min(q[1], q[3]) < -1),
                           ("sol", lambda q: min(q[0], q[2]) < -1), ("sag", lambda q: max(q[0], q[2]) > Wb + 1)):
            K = [q for q in kes if sec(q)]
            if not K or not any(dis_kenar[cephe](q) for q in K):
                continue
            x0_ = min(min(q[0], q[2]) for q in K); x1_ = max(max(q[0], q[2]) for q in K)
            y0_ = min(min(q[1], q[3]) for q in K); y1_ = max(max(q[1], q[3]) for q in K)
            kol = [[round(mx(k[0]), 1), round(my(k[3]), 1), round(mx(k[2]), 1), round(my(k[1]), 1)] for k in kare]
            if cephe in ("on", "arka"):
                derin = (y1_ - Hb) if cephe == "on" else -y0_
                bas, bit = x0_, x1_
            else:
                derin = -x0_ if cephe == "sol" else x1_ - Wb
                # sol / sağ cephede gerçek çerçeve y önden
                bas, bit = Hb - y1_, Hb - y0_
            kol = [k for k in kol if (cephe == "on" and k[1] > Hb) or (cephe == "arka" and k[3] < 0)
                   or (cephe == "sol" and k[2] < 0) or (cephe == "sag" and k[0] > Wb)]
            verandalar.append({"cephe": cephe, "bas_cm": round(max(bas, 0), 1), "bit_cm": round(bit, 1), "derinlik_cm": round(derin, 1),
                               "kolonlar": kol})
    return {"W": Wb, "H": Hb, "X0": round(X0, 3), "Y1": round(Y1, 3), "kisa": kisa, "ilk": ilk, "AX": AX, "AY": AY,
            "ek": {k: sorted(v) for k, v in ek.items()}, "duvarlar": duv, "odalar": odalar, "disari_yazilar": disari,
            "acikliklar": ac, "verandalar": verandalar, "kolonlar": kolonlar, "uyarilar": U,
            "yukseklik": sorted(set(YUKSEKLIK))}


# ------------------------------------------------------------------ İş Emri taslağı
def _dikdortgenler(hucreler, AX, AY):
    """Hücreleri satır satır dikdörtgenlere birleştirir (aynı sütun aralığındaki ardışık satırlar tek dikdörtgen)."""
    satir = collections.defaultdict(list)
    for i, j in hucreler:
        satir[j].append(i)
    kosular = []
    for j in sorted(satir):
        I = sorted(satir[j])
        bas = I[0]
        for a, b in zip(I, I[1:] + [None]):
            if b != a + 1:
                kosular.append((bas, a, j))
                bas = b
    R = []
    for i0, i1, j in kosular:
        r = next((r for r in R if r[0] == i0 and r[1] == i1 and r[3] == j - 1), None)
        if r:
            r[3] = j
        else:
            R.append([i0, i1, j, j])
    return [[AX[i0], AY[j0], AX[i1 + 1], AY[j1 + 1]] for i0, i1, j0, j1 in sorted(R, key=lambda r: (r[2], r[0]))]


def _olcu_yazisi(plan, g, a):
    """Açıklığın ölçüsü: açıklık yazılarından (pafta_kart) panonun ortasına en yakın olan (en çok 90 cm)."""
    P0 = plan["kutu_dunya"]
    if a["duvar_yon"] == "x":
        px, py = a["c"], a["orta"]
    else:
        px, py = a["orta"], a["c"]
    en = None
    for y in plan["acikliklar"]:
        if not y.get("olcu"):
            continue
        x_, y_ = P0[0] + y["x"] - g["X0"], g["Y1"] - (P0[1] + y["y"])
        d = math.hypot(x_ - px, y_ - py)
        if d <= 90 and (en is None or d < en[0]):
            en = (d, y["olcu"])
    return en[1] if en else None


def pafta_panolari(g):
    """Paftanın pano dizilimi: her duvarda [a0] + ekler + [a1] ardışık parçaları (Motor çerçevesi, arka-sol)."""
    R = []
    for d in g["duvarlar"]:
        E = [d["a0"]] + [e for e in d["ekler"] if d["a0"] + 1 < e < d["a1"] - 1] + [d["a1"]]
        for a0, a1 in zip(E, E[1:]):
            R.append({"yon": d["yon"], "aks": d["aks"], "c": d["c"], "dis": d["dis"], "a0": a0, "a1": a1})
    return R


def _oda_araligi(g, hucreler, yon, c, orta):
    """Odanın c hattındaki duvar boyunca aralığı (orta noktayı içeren kesintisiz parça), aks değerleriyle."""
    AX, AY = g["AX"], g["AY"]
    ar = []
    for i, j in hucreler:
        if yon == "x" and (abs(AX[i] - c) < 6 or abs(AX[i + 1] - c) < 6):
            ar.append((AY[j], AY[j + 1]))
        if yon == "y" and (abs(AY[j] - c) < 6 or abs(AY[j + 1] - c) < 6):
            ar.append((AX[i], AX[i + 1]))
    ar.sort()
    kos = []
    for a, b in ar:
        if kos and a <= kos[-1][1] + 1e-6:
            kos[-1][1] = max(kos[-1][1], b)
        else:
            kos.append([a, b])
    return next(((a, b) for a, b in kos if a - 1 <= orta <= b + 1), None)


def _pano_dizini(g, acik, oda_at, U, oda_hucre, acik_ad=()):
    """Her açıklığa paftadaki panosunun Motor aday listesindeki sırasını yazar (aday: açıklığın iki yanı aynı olan panolar, açıklık
    panoya sığıyor; sıra duvar boyunca a0). Pano bulunamazsa açıklık oda ortasına kalır, uyarı düşer."""
    P = pafta_panolari(g)
    d_ = 12

    def yanlar(p):
        m = (p["a0"] + p["a1"]) / 2
        if p["yon"] == "x":
            return oda_at(p["c"] - d_, m), oda_at(p["c"] + d_, m)
        return oda_at(m, p["c"] - d_), oda_at(m, p["c"] + d_)

    for a in acik:
        bas, bit = a["_pafta"]
        w = {"pencere": float(str(a.get("olcu", "120x")).split("x")[0]) if a["tur"] == "pencere" else 0, "dis_kapi": 90, "ic_kapi": 82,
             "gecis": float(a.get("olcu", 82)) if a["tur"] == "gecis" else 0}[a["tur"]]
        if a["tur"] in ("ic_kapi", "dis_kapi", "gecis") and "__DIS__" not in a["arasi"]:
            cift = set(a["arasi"])
            ok = lambda p, cift=cift: set(yanlar(p)) == cift
        else:
            oda = a["mahal"] if a["tur"] == "pencere" else a["arasi"][1]
            yon = "x" if a["duvar"] in ("sol", "sag") else "y"
            ic_i = {"sol": 1, "sag": 0, "arka": 1, "on": 0}[a["duvar"]]      # oda duvarın hangi yanında (0: sol / arka)
            ok = lambda p, oda=oda, yon=yon, ic_i=ic_i: (p["yon"] == yon and yanlar(p)[ic_i] == oda
                                                         and yanlar(p)[1 - ic_i] in (None, *acik_ad))
        odalar_ = [x_ for x_ in (a["arasi"] if a["tur"] != "pencere" else [a["mahal"]]) if x_ in oda_hucre]

        def parcada(p, odalar_=odalar_, w=w):
            # Motor'un süzgeci: pano ortası ± açıklığın yarısı, odanın (kapıda iki odanın ortak) duvar parçasında (aks değerleriyle)
            m = (p["a0"] + p["a1"]) / 2
            for o in odalar_:
                ar = _oda_araligi(g, oda_hucre[o], p["yon"], p["aks"], m)
                if ar is None or m - w / 2 < ar[0] - 0.5 or m + w / 2 > ar[1] + 0.5:
                    return False
            return True
        P_ = P
        if a["tur"] == "gecis":            # paftada duvarsız boşluk: panosu boşluğun kendisi (komşu panoların uçlarından)
            hy, hc, hk = a["_hat"]
            P_ = P + [{"yon": hy, "aks": hk, "c": hc, "dis": False, "a0": a["_kenar"][0], "a1": a["_kenar"][1]}]
        aday = sorted((p for p in P_ if ok(p) and parcada(p)), key=lambda p: p["a0"])
        hedef = next((k for k, p in enumerate(aday) if p["a0"] - 1 <= (bas + bit) / 2 <= p["a1"] + 1), None)
        if hedef is None:
            U.append(f"açıklığın panosu aday listesinde yok: {a['tur']} {a.get('mahal') or a.get('arasi')} {bas}–{bit}")
            continue
        if a["tur"] == "pencere":       # oda ortasındaki pencere: dizin yazılmaz, Motor'un oda_ortasi kuralı yerleştirir
            p_ = aday[hedef]
            ar = _oda_araligi(g, oda_hucre[a["mahal"]], p_["yon"], p_["aks"], (bas + bit) / 2)
            if ar and abs((ar[0] + ar[1]) / 2 - (bas + bit) / 2) <= 2.0:
                a["_oda_ortasi"] = True
                continue
        a["pano"] = hedef
        a["_aday"] = len(aday)


def _bagli(h):
    h = set(map(tuple, h))
    if not h:
        return False
    st, gor = [next(iter(h))], set()
    while st:
        c = st.pop()
        if c in gor:
            continue
        gor.add(c)
        st += [n for n in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)) if n in h]
    return gor == h


def _bol(hucreler, yazilar, AX, AY):
    """Duvarsız iki (ya da daha çok) odanın bölgesi: bir aks çizgisiyle iki bağlı parçaya bölünür, her parçada bir oda yazısı; yazıdaki m²'ye
    en yakın bölünme seçilir. Dönüş: [(yazı, hücreler), ...] ve aradaki açık sınır çiftleri (yazı adlarıyla)."""
    if len(yazilar) < 2:
        return [(yazilar[0] if yazilar else None, hucreler)], []
    alan = lambda h: sum((AX[i + 1] - AX[i]) * (AY[j + 1] - AY[j]) for i, j in h) / 1e4
    def yer(y):
        i = next((k for k in range(len(AX) - 1) if AX[k] <= y["x"] <= AX[k + 1]), -1)
        j = next((k for k in range(len(AY) - 1) if AY[k] <= y["y"] <= AY[k + 1]), -1)
        return i, j
    en = None
    for eks in (0, 1):
        for k in sorted({c[eks] for c in hucreler})[1:]:
            A = [c for c in hucreler if c[eks] < k]; B = [c for c in hucreler if c[eks] >= k]
            yA = [y for y in yazilar if yer(y)[eks] < k]; yB = [y for y in yazilar if yer(y)[eks] >= k]
            if not yA or not yB or not _bagli(A) or not _bagli(B):
                continue
            hata = 0.0
            for h, ys in ((A, yA), (B, yB)):
                if len(ys) == 1 and ys[0].get("m2"):
                    hata += abs(alan(h) - ys[0]["m2"]) / ys[0]["m2"]
                elif len(ys) > 1:
                    hata += 0.5 * (len(ys) - 1)
            if en is None or hata < en[0]:
                en = (hata, A, yA, B, yB)
    if en is None:
        return [(yazilar[0], hucreler)], []
    _, A, yA, B, yB = en
    pA, aA = _bol(A, yA, AX, AY)
    pB, aB = _bol(B, yB, AX, AY)
    # açık sınır: iki yandan komşu hücreleri olan yazı çiftleri
    ac = aA + aB
    for ya, ha in pA:
        for yb, hb in pB:
            hb_ = set(map(tuple, hb))
            if any((i + 1, j) in hb_ or (i - 1, j) in hb_ or (i, j + 1) in hb_ or (i, j - 1) in hb_ for i, j in ha):
                ac.append((ya["ad"], yb["ad"]))
    return pA + pB, ac


def veranda_ara_kolonu(v: dict, H: float) -> tuple[int | None, str | None]:
    """D-109 (BK-40, PC-45; Lokman, kart 16 Kasım 2026 08:42:16 "Kolon arası en çok 565 cm"): taşan verandanın dış kenarında kolon ekseni
    arası 565 cm'yi geçerse Motor ara kolon koyar (`geometry._gerekli_ara_kolon`); daha kısa verandada pafta ara kolon gösteriyorsa İş Emri
    `ara_kolon` yazar. Pafta kuralın istediğinden az ara kolon gösteriyorsa sayı yazılmaz (Motor koyar), not düşer; paftadaki yer Motor'un
    eşit aralığından 5 cm'den çok ayrılıyorsa not düşer (pafta düzeltilmez). `v`: `geometri`'nin verandası (kolon kareleri g çerçevesinde;
    sol ve sağ cephede gerçek çerçeve y önden, `H - y`). Dönüş: (İş Emri'nin `ara_kolon`'u ya da None, varsayım notu ya da None)."""
    from motor.geometry import _gerekli_ara_kolon
    kol, en = v["kolonlar"], v["bit_cm"] - v["bas_cm"]
    gerekli = _gerekli_ara_kolon(en)
    if len(kol) <= 2:
        if gerekli:
            return None, (f"paftada {len(kol)} kolon; dış kenar {en:g} cm, Motor kolon ekseni arası 565 cm kuralıyla {gerekli} ara kolon "
                          f"koyar (D-109).")
        return None, None
    ara = len(kol) - 2
    if v["cephe"] in ("on", "arka"):
        u = sorted((q[0] + q[2]) / 2 - v["bas_cm"] for q in kol)
    else:
        u = sorted(H - (q[1] + q[3]) / 2 - v["bas_cm"] for q in kol)
    pafta = [round(c, 1) for c in u[1:-1]]
    esit = [round(en * i / (ara + 1), 1) for i in range(1, ara + 1)]
    yer = ("" if all(abs(a - b) <= 5 for a, b in zip(pafta, esit)) else
           f" Paftada ara kolon {', '.join(f'{c:g}' for c in pafta)} cm'de; Motor eşit aralıkla {', '.join(f'{c:g}' for c in esit)} cm'ye koyar.")
    if ara < gerekli:
        return None, f"paftada {ara} ara kolon; Motor kolon ekseni arası 565 cm kuralıyla {gerekli} ara kolon koyar (D-109).{yer}"
    return ara, f"paftada {len(kol)} kolon; İş Emri'ne ara_kolon: {ara} yazıldı (D-109).{yer}"


def verandayi_govdeye_al(ie: dict, g: dict, ad: str = "VERANDA") -> dict:
    """Paftanın makas planında ana çatı taşan verandayı da örtüyorsa (ana makaslar verandanın üstünde; saçağın ölçüsü gövde + veranda +
    2 × 25) veranda gövdenin açık mahalidir (D-129, D-131; disk arşivi 110 ve 120 m²). Bu okuma makas planından yapılır, kodla değil;
    araç yalnız dönüşümü yapar (`ev.py --ana-cati-verandasi`). Yalnız ön cephenin tamamını tutan veranda (v1).

    - gövde verandanın derinliği kadar uzar (`dis_olcu_cm.y`, ızgara `y_pano`); veranda `tur: veranda` mahal olur (gövdedeki veranda gibi);
    - ön cephedeki dış kapı verandaya açılır (`arasi` `__DIS__` → veranda);
    - paftadaki ara kolonlar dikme olur, paftadaki yerinde (merkez 0,25 cm'ye, gerçek çerçevede sol-alt köşe; köşe kolonlarını Motor koyar,
      D-38); kenarın kirişi ara kolonlarda bölünür (D-129);
    - verandanın iki varsayım satırı (D-109 ara kolonu, ayrı çatı) tek satırla değişir.
    `ie` okuyucunun (uydurulmuş) İş Emri'si, `g` aynı paftanın `geometri`'si. Yeni İş Emri döner; `ie` değişmez."""
    ie = json.loads(json.dumps(ie))
    V = ie.get("verandalar") or []
    k = next((i for i, v in enumerate(V) if v["ad"] == ad), None)
    if k is None:
        raise ValueError(f"{ad}: İş Emri'nde taşan veranda yok")
    v = V.pop(k)
    if not V:
        ie.pop("verandalar")
    y_ = ie["yapi"]
    X, Yb = y_["dis_olcu_cm"]["x"], y_["dis_olcu_cm"]["y"]
    if v["cephe"] != "on" or abs(v["bas_cm"]) > 1 or abs(v["bit_cm"] - X) > 1:
        raise ValueError(f"{ad}: yalnız ön cephenin tamamını tutan veranda gövdeye alınır ({v['cephe']}, {v['bas_cm']:g}–{v['bit_cm']:g})")
    gv = next(q for q in g["verandalar"] if q["cephe"] == "on")
    kisa = y_["kisa_kenar"]
    ilk = {"x": 10.0 if kisa == "x" else 5.0, "y": 10.0 if kisa == "y" else 5.0}
    Yn = Yb + v["derinlik_cm"]
    y_["dis_olcu_cm"]["y"] = Yn
    y_["grid"]["y_pano"] = math.ceil((Yn - 2 * ilk["y"]) / 62.75 - 1e-6) / 2
    ie["mahaller"].append({"ad": ad, "tur": "veranda", "konum_cm": [[ilk["x"], Yb - ilk["y"], X - ilk["x"], Yn - ilk["y"]]]})
    for a in ie["acikliklar"]:
        if a["tur"] == "dis_kapi" and a.get("duvar") == "on" and "__DIS__" in a.get("arasi", []):
            a["arasi"] = [ad if m == "__DIS__" else m for m in a["arasi"]]
            a.pop("duvar")
    orta = sorted(round((q[0] + q[2]) / 2 * 4) / 4 for q in gv["kolonlar"])
    ara = orta[1:-1]
    if ara:
        ie["dikmeler"] = (ie.get("dikmeler") or []) + [[c - 5.0, 0.0] for c in ara]
    ie["varsayimlar"] = [s for s in ie.get("varsayimlar", []) if not s.startswith(f"{ad}: ")]
    ie["varsayimlar"].append(
        f"{ad}: paftanın makas planında ana çatı verandayı da örtüyor; veranda gövdenin açık mahali (gövde {Yb:g} + {v['derinlik_cm']:g} = "
        f"{Yn:g} cm). Paftada {len(orta)} kolon; ara kolonlar paftadaki yerinde ({', '.join(f'{c:g}' for c in ara) or 'yok'} cm), kiriş "
        f"onlarda bölünür (D-129).")
    return ie


def aciklik_sayilari(g) -> dict:
    """Bölge başına pencere ve kapı sayısı (yazısız odanın adı için). Açıklığın iki yanı `is_emri`'deki gibi duvardan 12 cm öteden;
    vasistas pencere, kapı ve kapısız geçiş kapı sayılır."""
    AX, AY = g["AX"], g["AY"]
    hb = {tuple(h): o["bolge"] for o in g["odalar"] for h in o["hucreler"]}

    def bolge(x, y):
        i = next((k for k in range(len(AX) - 1) if AX[k] <= x <= AX[k + 1]), None)
        j = next((k for k in range(len(AY) - 1) if AY[k] <= y <= AY[k + 1]), None)
        return hb.get((i, j)) if i is not None and j is not None else None

    say = collections.defaultdict(lambda: {"pencere": 0, "kapi": 0})
    for a in g["acikliklar"]:
        x, y = (a["c"], a["orta"]) if a["duvar_yon"] == "x" else (a["orta"], a["c"])
        yanlar = (bolge(x - 12, y), bolge(x + 12, y)) if a["duvar_yon"] == "x" else (bolge(x, y - 12), bolge(x, y + 12))
        tur = "pencere" if a["tur"] in ("pencere", "vasistas") else "kapi"
        for b in {b for b in yanlar if b is not None}:
            say[b][tur] += 1
    return say


def is_emri(g, plan, kod, teknik=None):
    V, U = [], list(g["uyarilar"])
    AX, AY = g["AX"], g["AY"]
    mahaller, ad_bolge, acik_ad, girintiler, dikmeler, acik_sinir = [], {}, set(), [], [], []
    sayac = collections.Counter()
    kapali = [o for o in g["odalar"] if not o["dis"]]
    # yazısız odalar (2018 şablonu): tefrişten (evye mutfak, klozet / duş banyo); penceresiz ve en az iki kapılı oda hol;
    # kalan en büyük salon, kalanlar yatak odası
    yazisiz = [o for o in kapali if not o["yazilar"]]
    salon_var = any(mahal_turu(o["yazilar"][0]["ad"]) == "salon" for o in kapali if o["yazilar"])
    say = aciklik_sayilari(g)
    tahmin = {}
    for o in sorted(yazisiz, key=lambda o: -o["aks_m2"]):
        if "banyo" in o["tefris"]:
            tahmin[o["bolge"]] = "BANYO"
        elif not o["tefris"] and say[o["bolge"]]["pencere"] == 0 and say[o["bolge"]]["kapi"] >= 2:
            tahmin[o["bolge"]] = "HOL"
        elif not salon_var and o["aks_m2"] >= 9:
            tahmin[o["bolge"]] = "SALON & MUTFAK" if "mutfak" in o["tefris"] else "SALON"
            salon_var = True
        elif "mutfak" in o["tefris"]:
            tahmin[o["bolge"]] = "MUTFAK"
        elif o["aks_m2"] < 5:
            tahmin[o["bolge"]] = "HOL"
        else:
            tahmin[o["bolge"]] = "YATAK ODASI"
    for o in g["odalar"]:
        if o["dis"]:
            veranda = o["kolonlar"] or o["kesik"] or any(mahal_turu(y["ad"]) == "veranda" for y in o["yazilar"])
            if veranda:
                ad = next((y["ad"] for y in o["yazilar"]), "VERANDA")
                sayac[ad] += 1
                if sayac[ad] > 1:
                    ad = f"{ad} {sayac[ad]}"
                mahaller.append({"ad": ad, "tur": "veranda", "konum_cm": _dikdortgenler(o["hucreler"], AX, AY)})
                acik_ad.add(ad)
                for h in o["hucreler"]:
                    ad_bolge[tuple(h)] = ad
                for q in o["kolonlar"]:          # dikme: gerçek çerçevede sol-alt köşe (y önden)
                    dikmeler.append([round(q[0], 1), round(g["H"] - q[3], 1)])
                V.append(f"{ad}: gövdenin içinde açık mahal (paftada {'kolon' if o['kolonlar'] else 'kesik çizgi'}); {len(o['kolonlar'])} dikme yazıldı.")
            else:
                girintiler += _dikdortgenler(o["hucreler"], AX, AY)
                V.append(f"Girinti {o['aks_m2']:.2f} m² (gövde kutusunun kenarında duvarsız bölge, paftada kolon ya da kesik çizgi yok).")
            continue
        if len(o["yazilar"]) > 1:
            parca, acik_ciftler = _bol([tuple(h) for h in o["hucreler"]], o["yazilar"], AX, AY)
            adlar = {}
            for y_, h_ in parca:
                ad = y_["ad"]
                sayac[ad] += 1
                if sayac[ad] > 1:
                    ad = f"{ad} {sayac[ad]}"
                adlar[y_["ad"]] = ad
                mahaller.append({"ad": ad, "tur": mahal_turu(ad) or "antre_hol", "konum_cm": _dikdortgenler(h_, AX, AY)})
                for h in h_:
                    ad_bolge[tuple(h)] = ad
            for a_, b_ in acik_ciftler:
                acik_sinir.append([adlar[a_], adlar[b_]])
            ozet = ", ".join(f"{y_['ad']} paftada {y_['m2']} m²" for y_, _ in parca)
            V.append(f"{' ve '.join(adlar.values())}: paftada aralarında duvar yok; aks çizgisinden bölündü, sınır açık ({ozet}).")
            continue
        if o["yazilar"]:
            ad = o["yazilar"][0]["ad"]
        else:
            ad = tahmin[o["bolge"]]
            V.append(f"Bölge {o['bolge']} ({o['aks_m2']:.2f} m² aks alanı): paftada oda adı yok; {ad} sayıldı"
                     f" ({'tefriş: ' + ', '.join(o['tefris']) if o['tefris'] else 'tefriş yok'}).")
        sayac[ad] += 1
        if sayac[ad] > 1:
            ad = f"{ad} {sayac[ad]}"
        tur = mahal_turu(ad) or "antre_hol"
        mahaller.append({"ad": ad, "tur": tur, "konum_cm": _dikdortgenler(o["hucreler"], AX, AY)})
        for h in o["hucreler"]:
            ad_bolge[tuple(h)] = ad

    def oda_at(x, y):
        i = next((k for k in range(len(AX) - 1) if AX[k] <= x <= AX[k + 1]), None)
        j = next((k for k in range(len(AY) - 1) if AY[k] <= y <= AY[k + 1]), None)
        return ad_bolge.get((i, j)) if i is not None and j is not None else None

    verandalar = []
    for k, v in enumerate(g["verandalar"]):
        ad = "VERANDA" if not sayac["VERANDA"] and k == 0 else f"VERANDA {sayac['VERANDA'] + k + 1}"
        verandalar.append({"ad": ad, "cephe": v["cephe"], "bas_cm": v["bas_cm"], "bit_cm": v["bit_cm"], "derinlik_cm": v["derinlik_cm"]})
        ara, not_ = veranda_ara_kolonu(v, g["H"])
        if ara:
            verandalar[-1]["ara_kolon"] = ara
        if not_:
            V.append(f"{ad}: {not_}")
        V.append(f"{ad}: çatısı paftanın planında yok; İş Emri'ne yazılmadı (Motor ana çatının eğimiyle beşik alır, uyarıyla).")
    acik = []
    for a in g["acikliklar"]:
        x, y = (a["c"], a["orta"]) if a["duvar_yon"] == "x" else (a["orta"], a["c"])
        d = 12
        if a["duvar_yon"] == "x":
            yanlar = (oda_at(x - d, y), oda_at(x + d, y))       # (sol, sağ)
        else:
            yanlar = (oda_at(x, y - d), oda_at(x, y + d))       # (arka, ön)
        dis_yan = [k for k in (0, 1) if yanlar[k] is None or yanlar[k] in acik_ad]
        ic_yan = [k for k in (0, 1) if k not in dis_yan]
        iz = {"_pafta": [a["bas"], a["bit"]], "_hat": [a["duvar_yon"], a["c"], a["aks"]], "_kaynak": a.get("kaynak")}
        if "kenar" in a:
            iz["_kenar"] = a["kenar"]
        if len(dis_yan) == 1 and ic_yan:
            oda = yanlar[ic_yan[0]]
            # odanın o yöndeki yüzü: düşey duvar odanın sağındaysa "sag"; yatay duvar odanın önündeyse (Motor y büyük) "on"
            duvar = ({0: "sol", 1: "sag"} if a["duvar_yon"] == "x" else {0: "arka", 1: "on"})[dis_yan[0]]
            if a["tur"] in ("pencere", "vasistas"):
                olcu = a.get("olcu") or _olcu_yazisi(plan, g, a) or ([60, 40] if a["tur"] == "vasistas" else None)
                if not olcu:
                    U.append(f"pencerenin ölçüsü okunamadı: {a.get('blok')} {a['duvar_yon']}={a['c']} {a['bas']}–{a['bit']} oda {oda}")
                    continue
                acik.append({"tur": "pencere", "olcu": f"{olcu[0]}x{olcu[1]}", "mahal": oda, "duvar": duvar, **iz})
                if a.get("surgulu"):
                    acik[-1]["acilis"] = "surgulu"
            else:
                dis = yanlar[dis_yan[0]]
                k = {"tur": "dis_kapi", "olcu": 90, "arasi": [dis or "__DIS__", oda], **iz}
                if not dis:
                    k["duvar"] = duvar
                acik.append(k)
        elif len(ic_yan) == 2 and a["tur"] == "gecis" and yanlar[0] != yanlar[1]:
            olcu = round(min(a["genislik"], MOD) - 4, 1)          # boşluğun iki yanında pano kenarı (2 + 2 cm)
            acik.append({"tur": "gecis", "olcu": olcu, "arasi": list(yanlar), **iz})
            V.append(f"{yanlar[0]} ile {yanlar[1]} arası: paftada {a['genislik']:g} cm duvarsız boşluk var, kapı çizilmemiş; "
                     f"İş Emri'ne {olcu:g} cm kapısız geçiş olarak yazıldı.")
        elif len(ic_yan) == 2 and a["tur"] in ("kapi", "celik_kapi") and yanlar[0] != yanlar[1]:
            s_ = a.get("acilim_yani")         # Motor: kapı arasi[0]'dan arasi[1]'e açılır; paftadaki kanat hangi odadaysa o ikinci
            acik.append({"tur": "ic_kapi", "olcu": 82, "arasi": [yanlar[1 - s_], yanlar[s_]] if s_ is not None else list(yanlar), **iz})
        else:
            U.append(f"açıklığın iki yanı okunamadı: {a['tur']} {a.get('blok') or a.get('kaynak')} {a['duvar_yon']}={a['c']} "
                     f"{a['bas']}–{a['bit']} → {yanlar}")
    oda_hucre = collections.defaultdict(list)
    for h, ad in ad_bolge.items():
        oda_hucre[ad].append(h)
    _pano_dizini(g, acik, oda_at, U, oda_hucre, acik_ad)
    yapi_ek = {"x": list(g["ek"]["x"]), "y": list(g["ek"]["y"])}
    kisa = g["kisa"]
    ilk = g["ilk"]
    grid = {f"{k}_pano": math.ceil(((g["W"] if k == "x" else g["H"]) - 2 * ilk[k]) / (MOD / 2) - 1e-6) / 2 for k in ("x", "y")}
    ic_t = collections.Counter(d["t"] for d in g["duvarlar"] if not d["dis"])
    ic = ic_t.most_common(1)[0][0] if ic_t else 6.0
    if len(ic_t) > 1:
        V.append(f"İç duvar kalınlıkları karışık {dict(ic_t)}; çoğunluk {ic:g} cm yazıldı.")
    yuk = 250
    if len(g.get("yukseklik", [])) == 1 and g["yukseklik"][0] in (250, 280, 300):
        yuk = g["yukseklik"][0]
        if yuk != 250:
            V.append(f"Duvar yüksekliği paftadaki yazıdan: {yuk} cm.")
    elif g.get("yukseklik"):
        V.append(f"Paftada yükseklik yazıları {g['yukseklik']}; 250 cm yazıldı.")
    yapi = {"sistem": "prefabrik", "kat_sayisi": 1, "duvar_yuksekligi_cm": yuk, "duvar_kalinligi_cm": {"dis": 10, "ic": ic},
            "olcu_kaynagi": "dis_olcu", "dis_olcu_cm": {"x": g["W"], "y": g["H"]}, "referans_model": kod, "grid": grid,
            "kisa_kenar": kisa, "giris_cephesi": "on", "dis_dusey_duvar": "cevre_aks_disinda",
            "dizilim": {"baslangic": "arka-sol", "hiza": "izgara", "dis_duvar_t_bolme": False, "pencere": "oda_ortasi", "kapi": "mantik",
                        "kose": "oda", "son_pano": "son_aks", "kapi_yeri": "ortada"}}
    yapi["ek_akslar_cm"] = yapi_ek       # aks tablosu her zaman açık (dayanak ve konum_cm aks tablosundan)
    cati = {"tip": "besik", "egim_yuzde": 32.9, "sacak_cm": 30, "topuk_cm": 10, "makas_yonu": "kisa_kenar", "makas_ekseni": kisa}
    V.append("Çatı beşik, %32,9, saçak 30, topuk 10 (paftanın planında eğim yok; prefabrik standardı).")
    ie = {"is_emri_no": f"HDD-{kod}", "revizyon": 1,
          "talep": {"bayi": {"kod": kod, "ad": f"Arşiv {kod}"}, "musteri_adi": kod,
                    "metin": f"İE-43: {kod} montaj paftasından okundu (plan_geometri v1). Pafta düzeltilmedi; farklar uyarılarda."},
          "yapi": yapi, "mahaller": mahaller, "acik_sinirlar": acik_sinir, "acikliklar": acik, "cati": cati,
          "cikti": {"pdf": True, "dxf": True, "pafta": "A2", "icerik": ["aksli_plan"]},
          "varsayimlar": V, "_uyarilar": U}
    if verandalar:
        ie["verandalar"] = verandalar
    if girintiler:
        ie["girintiler"] = girintiler
    if dikmeler:
        ie["dikmeler"] = dikmeler
    return ie


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dxf")
    ap.add_argument("kart")
    ap.add_argument("plan", type=int)
    ap.add_argument("cikti")
    ap.add_argument("--kod", default="HD")
    ap.add_argument("--geo")
    a = ap.parse_args()
    plan = json.load(open(a.kart, encoding="utf-8"))[a.plan]
    doc = PK.yukle(a.dxf)
    g = geometri(doc, plan["kutu_dunya"], plan)
    if a.geo:
        json.dump(g, open(a.geo, "w"), ensure_ascii=False)
    ie = is_emri(g, plan, a.kod, plan.get("teknik"))
    json.dump(ie, open(a.cikti, "w"), ensure_ascii=False, indent=1)
    print("gövde", g["W"], "×", g["H"], "kısa", g["kisa"], "AX", g["AX"], "AY", g["AY"], "ek", g["ek"])
    for m in ie["mahaller"]:
        print(" ", m["ad"], m["tur"], m["konum_cm"])
    for x in ie["acikliklar"]:
        print(" ", x)
    for v in ie.get("verandalar", []):
        print(" ", v)
    for u in ie["_uyarilar"]:
        print(" UYARI", u)


if __name__ == "__main__":
    main()
