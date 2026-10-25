"""İE-15 · K3 · Elektrik katmanı: noktalar (duy, glop, anahtar, priz, uydu prizi), zil, sigorta kutusu ve iki hat kablo.

Sayılar Lokman'ın oda kuralıdır, liste üretecinin okuduğu değerlerle (`kurallar/yerlesim/prefabrik.json › elektrik_yerlesimi`; değerler
`okunan` ile liste kurallarından ve kitaptan gelir, burada sayı yazılmaz). Odalar liste üretecinin okuduğu plandan (`motor.geometry.kur`: ad,
tür, alan, çokgen) ve onun sırasıyla gelir: kapalı odalar, sonra açık mahaller, adla birleşerek. Kapalı oda oda takımını, açık mahal veranda
takımını alır (alan ÷ takım alanı, yukarı, en az 1); kitap odası (banyo, WC, mutfak, hol) kitabın sayılarını. Toplam liste üretecinin
`elektrik_oda` sonucuyla aynıdır (test). Kablonun boyu liste üretecinin formülüdür (W otomat × sigortadan en uzak köşe + nokta × nokta başına
metre, yukarı); noktaları modelde yerleşen noktalardır. Kablonun çizgisi yalnız gösterimdir.

Noktaların yeri kuralın `yerler` varsayımıdır, sayıyı değiştirmez. Varsayılan yerde kurulamayan nokta yedek yere konur ve `uyarilar`'a yazılır
(sayı yine kuraldır). Kural uygulanamazsa (girdide kapalı oda yok; en uzak mesafe "sigortadan" değil) parça kurulmaz, "kural yok" yazar.

`katman(ie, plan, D, K)` döner: {parcalar, kural_yok, uyarilar, odalar, kablo, toplam}. Parçalar K2'ninkilerle aynı biçimdedir
({kural, parca, geo, bilgi, aciklama, boy_cm?}); kartı kart modelinde bulunur (`motor/kart_model.py`).
"""
from __future__ import annotations

import copy
import math
from collections import Counter

from shapely.geometry import LineString, MultiLineString, Point, box
from shapely.ops import linemerge, polylabel, unary_union

KURAL = "elektrik_yerlesimi"
KAPILAR = ("ic_kapi", "dis_kapi", "gecis")
KATMAN = "elektrik"


def _tavan(x: float) -> int:
    from motor.prefabrik_liste import TAVAN
    return TAVAN(x)


def _r(v: float) -> float:
    return round(float(v), 2)


# ----------------------------------------------------------------------------- oda kuralı (liste üretecinin `elektrik_oda`'sıyla aynı okuma)
def odalar_ve_sayilar(P, D: dict) -> tuple[list[dict], list[dict]]:
    """Odalar (adla birleşmiş) ve her odanın noktaları ({nokta adı: adet}). Nokta adları pafta katmanındaki adlardır (`elektrik.<ad>`)."""
    from motor.geometry import ACIK_MAHAL_TURLERI
    from motor.prefabrik_liste import ELEKTRIK_NOKTALARI as NOKTA

    EO, AM, KO = D["oda_kurali"], D["acik_mutfak"], D["kitap_odalari"]
    birlesik: dict[tuple, dict] = {}
    mahaller = list(P.mahaller.values())
    for acik, grup in ((False, [m for m in mahaller if not (m.acik or m.tur in ACIK_MAHAL_TURLERI)]),
                       (True, [m for m in mahaller if (m.acik or m.tur in ACIK_MAHAL_TURLERI)])):
        for m in grup:
            b = birlesik.setdefault((acik, m.ad), {"ad": m.ad, "tur": m.tur, "acik": acik, "alan_m2": 0.0, "poligonlar": []})
            if b["tur"] != m.tur:
                raise ValueError(f"elektrik yerleşimi: {m.ad!r} adlı parçalar farklı türde ({b['tur']}, {m.tur}); aynı adlı parçalar tek oda sayılır")
            b["alan_m2"] += m.alan_m2
            if m.poly is not None:
                b["poligonlar"].append(m.poly)
    uyarilar = []
    odalar = list(birlesik.values())
    for o in odalar:
        o["poly"] = unary_union(o.pop("poligonlar")) if o["poligonlar"] else None
    kapali = [o for o in odalar if not o["acik"]]
    mutfak_var = any(o["tur"] == "mutfak" for o in kapali)
    acik_mutfak = None if mutfak_var else next((o["ad"] for o in kapali if o["tur"] == AM["oda"]), None)
    KT = EO["kitaptan"]

    def takim(alan):
        return max(1, _tavan(alan / EO["takim_m2"]))

    def ekle(o, sayilar, carpan=1):
        for kk, n in sayilar.items():
            if kk not in NOKTA:
                raise ValueError(f"elektrik yerleşimi: {kk!r} tanınmıyor ({', '.join(NOKTA)})")
            if n:
                o["sayilar"][NOKTA[kk]] = o["sayilar"].get(NOKTA[kk], 0) + carpan * n

    for o in odalar:
        o["sayilar"] = {}
        if o["acik"]:
            o["takim"] = takim(o["alan_m2"])
            o["kaynak"] = "veranda takımı"
            ekle(o, EO["acik_takimi"], o["takim"])
        elif o["tur"] in KT:
            if KT[o["tur"]] not in KO:
                raise ValueError(f"elektrik yerleşimi: {o['tur']} kitabın {KT[o['tur']]!r} odasıyla sayılır, kitapta yok")
            o["takim"] = None
            o["kaynak"] = f"kitap ({KT[o['tur']]})"
            ekle(o, KO[KT[o["tur"]]])
        else:
            o["takim"] = takim(o["alan_m2"])
            o["kaynak"] = "oda takımı"
            ekle(o, EO["oda_takimi"], o["takim"])
        if not o["acik"] and o["ad"] == acik_mutfak:
            o["kaynak"] += " + tezgah (açık mutfak)"
            ekle(o, AM["ek"])
    if kapali and not (mutfak_var or acik_mutfak):
        uyarilar.append({"katman": KATMAN, "metin": f"mutfak ayrı mahal değil, açık mutfağın odası ({AM['oda']}) da yok; tezgahın prizleri konmadı "
                                                    "(liste üreteci de yazmaz)"})
    uydu = next((o for o in kapali if o["tur"] == D["uydu_odasi"]), None)
    if uydu is None and kapali:
        uydu = kapali[0]
        uyarilar.append({"katman": KATMAN, "metin": f"{D['uydu_odasi']} türünde oda yok; uydu prizi {uydu['ad']} odasına konuldu"})
    if uydu is not None:
        uydu["sayilar"]["uydu_prizi"] = uydu["sayilar"].get("uydu_prizi", 0) + EO["uydu_prizi_ev_basina"]
        uydu["kaynak"] += " + uydu prizi (ev başına)"
    return odalar, uyarilar


# ----------------------------------------------------------------------------- geometri yardımcıları (cm, Motor'un planı)
def _kenarlar(poly) -> list[tuple[str, float, float, float]]:
    """Çokgenin eksene paralel kenarları: (yön, eksen, baş, son); doğrultusundaki ara noktalar atılır."""
    halka = list(poly.simplify(0.01).exterior.coords)
    out = []
    for (x0, y0), (x1, y1) in zip(halka, halka[1:]):
        if abs(y1 - y0) < 1e-6 and abs(x1 - x0) > 1e-6:
            out.append(("x", y0, min(x0, x1), max(x0, x1)))
        elif abs(x1 - x0) < 1e-6 and abs(y1 - y0) > 1e-6:
            out.append(("y", x0, min(y0, y1), max(y0, y1)))
    return out


def _nokta(yon: str, s: float, c: float) -> Point:
    return Point(s, c) if yon == "x" else Point(c, s)


def _icinde(poly, yon: str, s: float, c: float) -> bool:
    return poly.buffer(0.01).contains(_nokta(yon, s, c))


def _bosluklar(P, yon: str, yuz: float) -> list[tuple[float, float]]:
    """`yon` doğrultusundaki ve yüzü `yuz` çizgisinde olan duvarın açıklıkları (kapı, pencere, geçiş), duvar boyunca."""
    out = []
    for d in P.duvarlar:
        if d.yon != yon or abs(abs(yuz - d.c) - d.h) > 1.0:
            continue
        for p in d.panolar:
            if p.acilim:
                g = p.gap()
                out.append((g[0], g[2]) if yon == "x" else (g[1], g[3]))
    return out


def _serbest(a0: float, a1: float, bosluklar, pay: float) -> list[tuple[float, float]]:
    aralik = [(a0, a1)]
    for b0, b1 in sorted(bosluklar):
        b0, b1 = b0 - pay, b1 + pay
        yeni = []
        for x0, x1 in aralik:
            if b1 <= x0 or b0 >= x1:
                yeni.append((x0, x1))
                continue
            if b0 > x0:
                yeni.append((x0, b0))
            if b1 < x1:
                yeni.append((b1, x1))
        aralik = yeni
    return [(x0, x1) for x0, x1 in aralik if x1 - x0 > 1e-6]


def _dagit(araliklar, n: int) -> list[float]:
    """`n` noktayı serbest aralıkların toplam boyunda eşit aralıkla dağıtır (her nokta kendi payının ortasında)."""
    L = sum(b - a for a, b in araliklar)
    out = []
    for k in range(n):
        t = (k + 0.5) * L / n
        for a, b in araliklar:
            if t <= b - a + 1e-9:
                out.append(a + t)
                break
            t -= b - a
    return out


def _kutu_duvar(yon: str, yuz: float, ic: int, s: float, olcu, z: float) -> list[float]:
    """Duvara asılı nokta: duvar boyunca `s`, yüzden `ic` yönüne derinlik, merkez kotu `z`; ölçü [boy, derinlik, yükseklik]."""
    b, d, h = olcu
    p0, p1 = sorted((yuz, yuz + ic * d))
    if yon == "x":
        return [_r(s - b / 2), _r(p0), _r(z - h / 2), _r(s + b / 2), _r(p1), _r(z + h / 2)]
    return [_r(p0), _r(s - b / 2), _r(z - h / 2), _r(p1), _r(s + b / 2), _r(z + h / 2)]


def _kutu_tavan(x: float, y: float, olcu, tavan: float) -> list[float]:
    a, b, t = olcu
    return [_r(x - a / 2), _r(y - b / 2), _r(tavan - t), _r(x + a / 2), _r(y + b / 2), _r(tavan)]


def _orta(par) -> tuple[float, float]:
    """Parçanın ortası: dikdörtgense kutusunun ortası; değilse ağırlık merkezi, içinde ve duvara en içteki noktanın (`polylabel`) yarı
    uzaklığından yakın değilse; yoksa en içteki nokta (L biçimli odanın köşesine düşmesin)."""
    x0, y0, x1, y1 = par.bounds
    if abs(par.area - (x1 - x0) * (y1 - y0)) <= 1e-6 * max(par.area, 1.0):
        return _r((x0 + x1) / 2), _r((y0 + y1) / 2)
    c, e = par.centroid, polylabel(par, tolerance=0.5)
    if par.contains(c) and par.exterior.distance(c) >= par.exterior.distance(e) / 2:
        return _r(c.x), _r(c.y)
    return _r(e.x), _r(e.y)


def tavan_noktalari(poly, n: int) -> list[tuple[float, float]]:
    """Oda uzun ekseni boyunca `n` eşit şerit; her noktası şeridindeki parçanın ortası."""
    x0, y0, x1, y1 = poly.bounds
    uzun_x = (x1 - x0) >= (y1 - y0)
    out = []
    for k in range(n):
        serit = (box(x0 + k * (x1 - x0) / n, y0, x0 + (k + 1) * (x1 - x0) / n, y1) if uzun_x
                 else box(x0, y0 + k * (y1 - y0) / n, x1, y0 + (k + 1) * (y1 - y0) / n))
        par = poly.intersection(serit)
        if par.geom_type != "Polygon":
            par = max((g for g in getattr(par, "geoms", []) if g.geom_type == "Polygon"), key=lambda g: g.area)
        out.append(_orta(par))
    return out


def uzun_duvarlar(poly) -> list[tuple[str, float, float, float, int]]:
    """Odanın iki uzun duvarı (uzun eksene paralel; iki yanın her birinde en uzun kenar): (yön, yüz, baş, son, içe yön)."""
    x0, y0, x1, y1 = poly.bounds
    yon = "x" if (x1 - x0) >= (y1 - y0) else "y"
    orta = (y0 + y1) / 2 if yon == "x" else (x0 + x1) / 2
    kenar = [k for k in _kenarlar(poly) if k[0] == yon]
    out = []
    for yan in ([k for k in kenar if k[1] < orta], [k for k in kenar if k[1] > orta]):
        if not yan:
            continue
        k = max(yan, key=lambda k: k[3] - k[2])
        ic = 1 if _icinde(poly, yon, (k[2] + k[3]) / 2, k[1] + 1) else -1
        out.append((yon, k[1], k[2], k[3], ic))
    return out


def _kapi_bilgisi(d, p) -> dict:
    from motor.geometry import mentese_ucu
    g = p.gap()
    g0, g1 = (g[0], g[2]) if d.yon == "x" else (g[1], g[3])
    u = mentese_ucu(p.acilim) if p.acilim.icine_normal else 0
    kol, mentese = ((g1, 1), (g0, -1)) if u == 0 else ((g0, -1), (g1, 1))
    return {"d": d, "p": p, "g0": g0, "g1": g1, "kol": kol, "mentese": mentese, "orta": (p.a0 + p.a1) / 2 + p.acilim.kayma}


def _yuz(poly, k: dict) -> tuple[float, int] | None:
    """Kapının duvarında `poly`'ye bakan yüz ve içe yön; ikisi de değilse None."""
    d, s = k["d"], (k["g0"] + k["g1"]) / 2
    for yuz, ic in ((d.c + d.h, 1), (d.c - d.h, -1)):
        if _icinde(poly, d.yon, s, yuz + ic * 2):
            return yuz, ic
    return None


# ----------------------------------------------------------------------------- katman
def katman(ie: dict, plan: dict, D: dict, K: dict) -> dict:
    """K3'ün parçaları. `plan`: `motor.ifc_uret.hazirla(ie)` (duvar yüksekliği ve kapının üst kotu); `D`: kuralın çözülmüş değerleri
    (`motor.yerlesim.degerler(...)["elektrik_yerlesimi"]`); `K`: kuralın kendisi (`beklenen` değerler için)."""
    from motor import geometry as G

    P = G.kur(copy.deepcopy(ie))
    O, Z, S = D["olculer_cm"], D["kot_cm"], D["gosterim_cm"]
    tavan_z = plan["bina"]["duvar_h"]
    parcalar, kural_yok = [], []
    odalar, uyarilar = odalar_ve_sayilar(P, D)
    kapali = [o for o in odalar if not o["acik"]]
    if not kapali:
        kural_yok.append({"parca": "elektrik noktaları", "sinif": "IfcFlowTerminal",
                          "neden": f"{KURAL}: girdide kapalı oda yok; oda kuralı uygulanamaz (liste üreteci de oda noktalarını saymaz)"})
        return {"parcalar": [], "kural_yok": kural_yok, "uyarilar": uyarilar, "odalar": _oda_ozeti(odalar), "kablo": [], "toplam": {}}

    def parca(ad_, mahal, yer, geo, aciklama, **bilgi):
        parcalar.append({"kural": KURAL, "parca": ad_, "geo": {"tip": "kutu", "kutu": geo} if isinstance(geo, list) else geo,
                         "bilgi": {"Mahal": mahal, "Yer": yer, **bilgi}, "aciklama": aciklama})

    kapilar = [_kapi_bilgisi(d, p) for d in P.duvarlar for p in d.panolar if p.acilim and p.acilim.tur in KAPILAR and p.acilim.arasi]
    kapi_sayisi = Counter(a for k in kapilar for a in k["p"].acilim.arasi)
    giris = next((k for k in kapilar if k["p"].acilim.tur == "dis_kapi" and k["d"].tur == "dis"), None)   # liste üreteci gibi: dış duvardaki

    def oda_kapilari(o) -> list[dict]:
        """Odanın kapıları, anahtarın aranacağı sırayla: giriş kapısı, sonra komşusunun en çok kapısı olan (sirkülasyon), sonra planın sırası."""
        def komsu(k):
            return next((a for a in k["p"].acilim.arasi if a != o["ad"]), o["ad"])
        aday = [(i, k) for i, k in enumerate(kapilar) if o["ad"] in k["p"].acilim.arasi]
        return [k for _, k in sorted(aday, key=lambda x: (x[1]["p"].acilim.tur != "dis_kapi", -kapi_sayisi[komsu(x[1])], x[0]))]

    for o in odalar:
        poly, ad = o["poly"], o["ad"]
        if poly is not None and poly.geom_type != "Polygon":                   # adla birleşen ayrık parçalar: duvarlar en büyüğünden
            poly = max(poly.geoms, key=lambda g: g.area)
        if poly is None:
            uyarilar.append({"katman": KATMAN, "metin": f"{ad}: planda çokgeni yok; noktaları konmadı"})
            continue
        sy = o["sayilar"]
        duvarlar = uzun_duvarlar(poly)

        # tavan: kapalı odada duy ve glop
        if not o["acik"]:
            tavan = ["tavan_armaturu"] * sy.get("tavan_armaturu", 0) + ["glop"] * sy.get("glop", 0)
            for tur, (x, y) in zip(tavan, tavan_noktalari(poly, len(tavan)) if tavan else []):
                parca(tur, ad, "tavan", _kutu_tavan(x, y, S["duy" if tur == "tavan_armaturu" else "glop"], tavan_z), f"{ad}, tavan ({x:g}, {y:g})")
        else:
            _veranda_glopu(P, o, sy.get("glop", 0), giris, kapilar, D, tavan_z, parca, uyarilar)
            if sy.get("tavan_armaturu"):                                     # veranda takımında duy yok; kural verirse tavana
                for x, y in tavan_noktalari(poly, sy["tavan_armaturu"]):
                    parca("tavan_armaturu", ad, "tavan", _kutu_tavan(x, y, S["duy"], tavan_z), f"{ad}, tavan ({x:g}, {y:g})")

        # anahtarlar: kapının kol tarafında
        anahtar = ["anahtar_tekli"] * sy.get("anahtar_tekli", 0) + ["anahtar_cift"] * sy.get("anahtar_cift", 0)
        if anahtar:
            yerler, neden = [], "kapısı yok"
            for kapi in oda_kapilari(o):                                    # ilk kapıda sığmazsa odanın öbür kapısı
                y, neden = _anahtar_yerleri(poly, kapi, len(anahtar), P, O, S)
                if len(y) > len(yerler):
                    yerler = y
                if len(yerler) == len(anahtar):
                    break
            if len(yerler) < len(anahtar):
                eksik = len(anahtar) - len(yerler)
                uyarilar.append({"katman": KATMAN, "metin": f"{ad}: {neden}; {eksik} anahtar uzun duvara konuldu"})
                y, bos = _duvar_yerleri(duvarlar[:1], eksik, P, O, S["anahtar"][0] / 2, "uzun duvar (yedek)")
                yerler += y
                if bos:
                    uyarilar.append({"katman": KATMAN, "metin": f"{ad}: {bos} (yedek anahtar)"})
            for tur, (yon, yuz, ic, s, yer) in zip(anahtar, yerler):
                parca(tur, ad, yer, _kutu_duvar(yon, yuz, ic, s, S["anahtar"], Z["anahtar"]), f"{ad}, {yer}, {yon} boyunca {s:g}")

        # prizler: iki uzun duvarda sırayla
        priz = ["priz_tekli"] * sy.get("priz_tekli", 0) + ["priz_cift"] * sy.get("priz_cift", 0) + ["uydu_prizi"] * sy.get("uydu_prizi", 0)
        if priz:
            yerler, bos = _duvar_yerleri(duvarlar, len(priz), P, O, S["priz"][0] / 2)
            if bos:
                uyarilar.append({"katman": KATMAN, "metin": f"{ad}: {bos}"})
            for tur, (yon, yuz, ic, s, yer) in zip(priz, yerler):
                parca(tur, ad, yer, _kutu_duvar(yon, yuz, ic, s, S["priz"], Z["priz"]), f"{ad}, {yer}, {yon} boyunca {s:g}")

    # sigorta kutusu ve zil: giriş kapısında (karar E)
    sigorta_n, zil_n = D["sigorta_kutusu"], D["zil"]
    sig_nokta = None
    if giris is not None:
        d = giris["d"]
        ic_oda = next((o for o in kapali if o["ad"] in giris["p"].acilim.arasi and o["poly"] is not None), None)
        yuz = _yuz(ic_oda["poly"], giris) if ic_oda else None
        if yuz is None:                                                    # kapalı tarafı bulunamadı: kapının +normal yüzü
            yuz = (d.c + d.h, 1)
            uyarilar.append({"katman": KATMAN, "metin": "giriş kapısının kapalı odaya bakan yüzü bulunamadı; sigorta kutusu kapının bir yüzüne konuldu"})
        ust = next((a["z1"] for a in plan.get("acikliklar", []) if a.get("alt_tur") == "dis_kapi" and a["yon"] == d.yon
                    and abs(a["a0"] - giris["g0"]) < 0.6 and abs(a["c"] - d.c) < 0.6), None)
        if ust is None:
            raise ValueError("elektrik yerleşimi: giriş kapısı bugünkü IFC'nin planında yok")
        b, dd, h = S["sigorta_kutusu"]
        z = ust + O["sigorta_kapidan"] + h / 2
        if z + h / 2 > tavan_z:
            z = tavan_z - h / 2
            uyarilar.append({"katman": KATMAN, "metin": "sigorta kutusu kapının üstüne sığmadı; tavana dayandı"})
        mahal = ic_oda["ad"] if ic_oda else "—"
        for i in range(sigorta_n):
            s = giris["orta"] + i * (b + O["anahtar_arasi"])
            parca("sigorta_kutusu", mahal, "giriş kapısının üstü", _kutu_duvar(d.yon, yuz[0], yuz[1], s, S["sigorta_kutusu"], z),
                  f"{mahal}, giriş kapısının iç yüzü, kapının üstü")
        sig_nokta = (d.yon, yuz[0] + yuz[1] * dd / 2, giris["orta"])
        dis = (d.c - d.h, -1) if yuz[1] == 1 else (d.c + d.h, 1)
        dis_mahal = next((a for a in giris["p"].acilim.arasi if a != mahal), "dış")
        dis_poly = next((o["poly"] for o in odalar if o["acik"] and o["ad"] == dis_mahal and o["poly"] is not None), None)
        fp, bos, b = P.footprint(), _bosluklar(P, d.yon, dis[0]), S["zil"][0]

        def disarida(s: float) -> bool:
            """Zil kapının dışında: açık mahale açılıyorsa onun içinde, dışarıya açılıyorsa evin dışında; açıklığın önünde değil."""
            for e in (-b / 2, b / 2):
                q = _nokta(d.yon, s + e, dis[0] + dis[1])
                if (not dis_poly.buffer(0.01).contains(q)) if dis_poly is not None else fp.contains(q):
                    return False
            return not any(b0 < s + b / 2 and b1 > s - b / 2 for b0, b1 in bos)
        zil_yeri = None
        for uzak, (uc, yon_), yer in ((u, *k) for u in (O["zil_kapidan"], O["anahtar_kapidan"])     # sonra anahtarın hizası (üstünde)
                                       for k in ((giris["kol"], "kol tarafı"), (giris["mentese"], "menteşe tarafı"))):
            ss = [uc + yon_ * (uzak + i * O["anahtar_arasi"]) for i in range(zil_n)]
            if all(disarida(s) for s in ss):
                zil_yeri = (ss, yer)
                break
        if zil_yeri is None:
            uc, yon_ = giris["kol"]
            zil_yeri = ([uc + yon_ * (O["zil_kapidan"] + i * O["anahtar_arasi"]) for i in range(zil_n)], "kol tarafı")
            if zil_n:
                uyarilar.append({"katman": KATMAN, "metin": "giriş kapısının iki yanında da dışarıda yer yok; zil kol tarafına konuldu"})
        for s in zil_yeri[0]:
            parca("zil", dis_mahal, f"giriş kapısının dışı, {zil_yeri[1]}", _kutu_duvar(d.yon, dis[0], dis[1], s, S["zil"], Z["zil"]),
                  f"giriş kapısının dış yüzü, {zil_yeri[1]}")
    else:
        o = kapali[0]
        yon, yuz, a0, a1, ic = uzun_duvarlar(o["poly"])[0]
        uyarilar.append({"katman": KATMAN, "metin": f"giriş kapısı yok; sigorta kutusu ve zil {o['ad']} odasının uzun duvarına konuldu"})
        b, dd, h = S["sigorta_kutusu"]
        for i in range(sigorta_n):
            parca("sigorta_kutusu", o["ad"], "yedek yer", _kutu_duvar(yon, yuz, ic, a0 + b + i * (b + O["anahtar_arasi"]), S["sigorta_kutusu"],
                                                                     tavan_z - h), f"{o['ad']}, uzun duvar (giriş kapısı yok)")
        for i in range(zil_n):
            parca("zil", o["ad"], "yedek yer", _kutu_duvar(yon, yuz, ic, a1 - S["zil"][0] - i * O["anahtar_arasi"], S["zil"], Z["zil"]),
                  f"{o['ad']}, uzun duvar (giriş kapısı yok)")
        sig_nokta = (yon, yuz + ic * dd / 2, a0 + b)

    # kablo: iki hat, boyu liste üretecinin formülü
    toplam = Counter(p["parca"] for p in parcalar)
    kablo = []
    if D["en_uzak_mesafe"] != K["en_uzak_mesafe"]["beklenen"]:
        for ad_ in ("kablo_priz", "kablo_aydinlatma"):
            kural_yok.append({"parca": ad_, "sinif": "IfcCableSegment",
                              "neden": f"{KURAL}: kablo_en_uzak_mesafe \"{D['en_uzak_mesafe']}\"; kablo yalnız sigortadan en uzak mesafeyle kurulur"})
    else:
        fp = P.footprint()
        kose = [q for g_ in getattr(fp, "geoms", [fp]) for q in g_.exterior.coords]
        if giris is not None:
            d = giris["d"]
            kutu = (giris["orta"], d.c) if d.yon == "x" else (d.c, giris["orta"])
            uzak = max(kose, key=lambda q: math.hypot(q[0] - kutu[0], q[1] - kutu[1]))
            en_uzak = {"m": math.hypot(uzak[0] - kutu[0], uzak[1] - kutu[1]) / 100, "nereden": "giriş kapısından kapalı kısmın en uzak köşesi"}
        else:
            fx0, fy0, fx1, fy1 = fp.bounds
            uzak = (fx1, fy1)
            en_uzak = {"m": math.hypot(fx1 - fx0, fy1 - fy0) / 100, "nereden": "giriş kapısı yok: kapalı kısmın köşegeni"}
        yon, c, s = sig_nokta
        x0, y0 = (s, c) if yon == "x" else (c, s)
        z = tavan_z - O["tavan_alti"]
        dx, dy = uzak[0] - x0, uzak[1] - y0
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        hatlar = (("kablo_priz", "priz", toplam["priz_tekli"] + 2 * toplam["priz_cift"] + toplam["uydu_prizi"],
                   "tekli priz + çiftli priz × 2 + uydu prizi", 1),
                  ("kablo_aydinlatma", "aydınlatma", toplam["anahtar_tekli"] + 2 * toplam["anahtar_cift"], "tekli anahtar + çiftli anahtar × 2", -1))
        w, nm = D["w_otomat"], D["kablo_nokta_basina_m"]
        for ad_, hat, n, nokta_adi, yan in hatlar:
            metre = _tavan(w * en_uzak["m"] + n * nm)
            off = yan * (S["kablo"] + 2)
            geo = {"tip": "cubuk", "p0": [_r(x0 + nx * off), _r(y0 + ny * off), _r(z)], "p1": [_r(uzak[0] + nx * off), _r(uzak[1] + ny * off), _r(z)],
                   "kesit": S["kablo"]}
            formul = f"W otomat {w} × en uzak {en_uzak['m']:.4f} m ({en_uzak['nereden']}) + ({nokta_adi} = {n}) × {nm:g} m, yukarı"
            parcalar.append({"kural": KURAL, "parca": ad_, "boy_cm": metre * 100, "geo": geo,
                             "bilgi": {"Hat": hat, "Noktalar": n, "EnUzak_m": round(en_uzak["m"], 4), "Formul": formul},
                             "aciklama": f"{hat} hattı: {metre} m ({formul}); çizgi sigortadan en uzak köşeye"})
            kablo.append({"parca": ad_, "hat": hat, "noktalar": n, "w_otomat": w, "nokta_basina_m": nm, "en_uzak_m": round(en_uzak["m"], 4),
                          "nereden": en_uzak["nereden"], "metre": metre, "formul": formul, "en_uzak_kose": [_r(uzak[0]), _r(uzak[1])]})
    return {"parcalar": parcalar, "kural_yok": kural_yok, "uyarilar": uyarilar, "odalar": _oda_ozeti(odalar), "kablo": kablo,
            "toplam": dict(sorted(toplam.items()))}


def _oda_ozeti(odalar) -> list[dict]:
    return [{"ad": o["ad"], "tur": o["tur"], "acik": o["acik"], "alan_m2": round(o["alan_m2"], 4), "takim": o.get("takim"), "kaynak": o.get("kaynak"),
             "sayilar": o.get("sayilar", {}),
             "poligon": [[_r(x), _r(y)] for x, y in o["poly"].simplify(0.01).exterior.coords] if o["poly"] is not None and o["poly"].geom_type == "Polygon" else None}
            for o in odalar]


def _anahtar_yerleri(poly, kapi, n: int, P, O: dict, S: dict) -> tuple[list, str]:
    """Kapının kol tarafında, odanın içindeki yüzde yan yana; sığmayan menteşe tarafına. Döner: ([(yön, yüz, iç, s, yer)], sığmama nedeni)."""
    if kapi is None:
        return [], "kapısı yok"
    yuz = _yuz(poly, kapi)
    if yuz is None:
        return [], "kapının odaya bakan yüzü bulunamadı"
    d = kapi["d"]
    bos = _bosluklar(P, d.yon, yuz[0])
    b = S["anahtar"][0]
    out = []
    for (uc, yon_), yer in ((kapi["kol"], "kapının kol tarafı"), (kapi["mentese"], "kapının menteşe tarafı")):
        k = 0
        while len(out) < n:
            s = uc + yon_ * (O["anahtar_kapidan"] + k * O["anahtar_arasi"])
            uclar_ic = all(_icinde(poly, d.yon, s + e, yuz[0] + yuz[1]) for e in (-b / 2, b / 2))
            if not uclar_ic or any(b0 < s + b / 2 and b1 > s - b / 2 for b0, b1 in bos):
                break
            out.append((d.yon, yuz[0], yuz[1], s, yer))
            k += 1
    return out, "kapının yanında yer yok"


def _duvar_yerleri(duvarlar, m: int, P, O: dict, yari: float, yer: str = "uzun duvar") -> tuple[list[tuple], str]:
    """`m` nokta duvarlara sırayla (bir o duvara bir bu duvara); her duvarda açıklıklar dışındaki boyda eşit aralıkla (noktanın kenarı, yarı
    genişliği `yari`, açıklığa `bosluk_payi`'ndan, duvarın ucuna değmeden). Açıklık dışında yeri olmayan duvarın noktaları öbür duvara geçer;
    hiçbirinde yer yoksa açıklık gözetilmez. Döner: noktaların sırasıyla [(yön, yüz, iç, s, yer)] ve not."""
    if not duvarlar:
        raise ValueError("elektrik yerleşimi: odanın eksene paralel duvarı yok")
    W = len(duvarlar)
    serbest = [_serbest(a0 + yari, a1 - yari, _bosluklar(P, yon, yuz), O["bosluk_payi"] + yari) for yon, yuz, a0, a1, ic in duvarlar]
    hedef = [i % W for i in range(m)]
    not_ = ""
    j = next((j for j in range(W) if serbest[j]), None)                   # yeri olan ilk duvar; açıklık gözetilmeyen duvar yer sayılmaz
    for i in range(W):
        if serbest[i] or i not in hedef:
            continue
        if j is None:
            serbest[i] = [(duvarlar[i][2], duvarlar[i][3])]
            not_ = "uzun duvarlarda açıklık dışında yer yok; noktalar açıklık gözetilmeden konuldu"
        else:
            hedef = [j if h == i else h for h in hedef]
            not_ = "bir uzun duvarda açıklık dışında yer yok; noktaları öbür duvara konuldu"
    konum = {i: iter(_dagit(serbest[i], hedef.count(i))) for i in range(W)}
    out = []
    for h in hedef:
        yon, yuz, a0, a1, ic = duvarlar[h]
        out.append((yon, yuz, ic, next(konum[h]), yer))
    return out, not_


def _veranda_glopu(P, o: dict, n: int, giris, kapilar, D: dict, tavan_z: float, parca, uyarilar) -> None:
    """Açık mahalde glop evin duvarında (açık mahalle kapalı kısmın ortak sınırı), kapının iki yanına yarı yarıya."""
    if not n:
        return
    O, Z, S = D["olculer_cm"], D["kot_cm"], D["gosterim_cm"]
    poly, ad = o["poly"], o["ad"]
    fp = P.footprint().buffer(0.5)
    parcalar = []
    for yon, c, a0, a1 in _kenarlar(poly):
        seg = LineString([(a0, c), (a1, c)] if yon == "x" else [(c, a0), (c, a1)])
        kes = seg.intersection(fp)
        parcalar += [g for g in getattr(kes, "geoms", [kes]) if g.geom_type == "LineString" and g.length > 1.0]
    if not parcalar:
        uyarilar.append({"katman": KATMAN, "metin": f"{ad}: evin duvarına değmiyor; glop tavana konuldu"})
        for x, y in tavan_noktalari(poly, n):
            parca("glop", ad, "tavan", _kutu_tavan(x, y, S["glop"], tavan_z), f"{ad}, tavan ({x:g}, {y:g})")
        return
    yol = linemerge(MultiLineString(parcalar))
    kapi = giris if giris is not None and ad in giris["p"].acilim.arasi else next((k for k in kapilar if ad in k["p"].acilim.arasi), None)
    if yol.geom_type != "LineString":
        yol = max(yol.geoms, key=lambda g: (kapi is not None and g.distance(_kapi_noktasi(kapi)) < 1.0, g.length))
    bos, s_kapi = [], None
    for d in P.duvarlar:
        for p in d.panolar:
            if not p.acilim:
                continue
            kes = yol.intersection(box(*p.gap()).buffer(0.6))
            if kes.is_empty:
                continue
            s = [yol.project(Point(q)) for g in getattr(kes, "geoms", [kes]) for q in g.coords]
            bos.append((min(s), max(s)))
            if kapi is not None and p is kapi["p"]:
                s_kapi = (min(s) + max(s)) / 2
    yari = S["glop"][0] / 2                                              # glopun kenarı açıklığa `bosluk_payi`'ndan yaklaşmaz
    if s_kapi is None:
        yanlar = [(_serbest(yari, yol.length - yari, bos, O["bosluk_payi"] + yari), n)]
    else:
        a = _serbest(yari, s_kapi, bos, O["bosluk_payi"] + yari)
        b = _serbest(s_kapi, yol.length - yari, bos, O["bosluk_payi"] + yari)
        na = n // 2 if a and b else (n if a else 0)
        yanlar = [(a, na), (b, n - na)]
    for serbest, k in yanlar:
        if k and not serbest:
            uyarilar.append({"katman": KATMAN, "metin": f"{ad}: evin duvarında açıklık dışında yer yok; glop açıklığa bakmadan konuldu"})
            serbest = [(0.0, yol.length)]
        for s in _dagit(serbest, k):
            q = yol.interpolate(s)
            q0, q1 = yol.interpolate(max(0.0, s - 0.5)), yol.interpolate(min(yol.length, s + 0.5))
            yon = "x" if abs(q1.y - q0.y) < abs(q1.x - q0.x) else "y"
            c, t = (q.y, q.x) if yon == "x" else (q.x, q.y)
            ic = 1 if _icinde(poly, yon, t, c + 2) else -1
            gl = S["glop"]
            parca("glop", ad, "evin duvarı", _kutu_duvar(yon, c, ic, t, [gl[0], gl[2], gl[1]], Z["glop_duvar"]),
                  f"{ad}, evin duvarı, {yon} boyunca {t:.2f}")


def _kapi_noktasi(k: dict) -> Point:
    d, s = k["d"], (k["g0"] + k["g1"]) / 2
    return _nokta(d.yon, s, d.c)
