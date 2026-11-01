"""İE-17 · Prefabrik evin dört cephe görünüşünün geometrisi; çizimi canlı ön onay PDF'inin "ÇALIŞMA" görünüşü (`dxf_out.ciz_gorunusler`).
D-31 (29 Ekim 2026): beşik çatı da dört görünüşte (düzlemler `sunum.cati_tanimi`'nden; taşan veranda yalnız beşikte).

Lokman, 27 Ekim 2026 21:06; CIO 21:13: prefabrik bayiye canlıda `dxf_out`'un ön onay PDF'i ve `bayi_gorseli`'nin plan görseli gidiyordu;
biçim bu ikisinden, genel motordan yalnız çatı ve görünüş geometrisi. Bu modül çizmez; `dxf_out` çizer.

- Duvar, pano derzleri, pencere ve kapı Motor'un `Plan`'ından, ön görünüşün kuralıyla (`dxf_out.ciz_on_gorunus`): cephenin dış duvarları
  dışarı yönü o cepheye bakanlar (`G.disari_yon`; açık mahale bakan duvar da), derzler panoların uçları ve cepheye değen dik dış duvarların
  yüzleri (`cepheye_deger`; D-31), açıklık panonun boşluğunda (`Pano.gap`), üst kot 200, eşik 200 − boy (BK-13), kapı 0–200.
- Çatı çizgileri `cati_prefabrik`'in düzlemlerinden (`cati_genel.cati_kur`, genel motorun çatı üreticisi): bu cepheye dik izdüşüm. Bakana
  dönük düzlemin kenarları, önündeki dönük düzlemlerin örttüğü kısım atılarak; yandan görülen düzlem (bakış düzlemin içinde) çizgi olarak
  ve eğimi yazılarak; arkaya bakan düzlem çizilmez (gövdenin ve önündeki düzlemlerin arkasında). Kalkanlar çizilmez (üst kenarları çatının
  çizgisi, alt kenarları duvar üstü) ama arkalarında kalanı örter (ör. sağdan bakışta ana kalkanın arkasındaki cumba saçağı). Kotlar zeminden.
- u ekseni bakanın soldan sağa (`veranda.izdusum` ile aynı yönler), gövdenin sol ucu 0.
"""
from __future__ import annotations

import math

from . import geometry as G

TARAFLAR = ("on", "arka", "sol", "sag")
AD = {"on": "ÖN", "arka": "ARKA", "sol": "SOL", "sag": "SAĞ"}
_YON = {"on": ("x", "-y"), "arka": ("x", "+y"), "sol": ("y", "-x"), "sag": ("y", "+x")}
_BAKANA = {"on": (0.0, -1.0), "arka": (0.0, 1.0), "sol": (-1.0, 0.0), "sag": (1.0, 0.0)}    # planda bakana doğru
YAN_ESIGI = 0.02                    # düzlem normalinin bakışa dik bileşeni bundan küçükse düzlem yandan görülür
KISA_CM = 5.0                       # yandan görülen düzlemin örtüden artan parçası bundan kısaysa çizilmez


def eksen(plan: G.Plan, taraf: str):
    """(u, derinlik, cephe eni): plandaki nokta → görünüşün yatayı; derinlik küçükse bakana yakın."""
    x0, y0, x1, y1 = G.govde_kutusu(plan)
    u = {"on": lambda x, y: x - x0, "arka": lambda x, y: x1 - x, "sol": lambda x, y: y1 - y, "sag": lambda x, y: y - y0}[taraf]
    d = {"on": lambda x, y: y, "arka": lambda x, y: -y, "sol": lambda x, y: x, "sag": lambda x, y: -x}[taraf]
    return u, d, (x1 - x0) if taraf in ("on", "arka") else (y1 - y0)


def cepheye_deger(d, cephe_duvarlari) -> bool:
    """Cepheye dik dış duvar `d` bu cephenin bir dış duvarına değiyor mu: bir ucu o duvarın kalınlığının içinde ve ekseni o duvarın boyunca.
    Değmeyen dik dış duvar (ör. öndeki giriş nişinin yan duvarı arka, sol ya da sağ görünüşte) derz vermez (D-31 madde 7; Lokman, 29 Ekim
    2026 11:21: "2 WC'nin arasında sadece H var, 2 ek çizgi var": nişin yan duvarı arka cephedeki WC ara duvarıyla aynı eksendeydi)."""
    e = 1e-6
    return any(any(w.c - w.h - e <= uc <= w.c + w.h + e for uc in (d.p0, d.p1)) and w.p0 - d.h - e <= d.c <= w.p1 + d.h + e
               for w in cephe_duvarlari)


def gorunur(plan: G.Plan, d, dis: str) -> bool:
    """`dis` yönüne bakan dış duvar o yandan görülüyor mu: önündeki şeritte (duvar yüzünden gövdenin kenarına) gövdenin kapalı kısmı duvarın
    boyunu örtmüyorsa. Gövde = dış kutu − ızgaradaki açık mahaller (niş, köşe verandası); girintili gövdede kutu yerine gövdenin dış çizgisi
    (`G.govde_cokgeni`; İE-24: TK-03'ün girintideki duvarı ön görünüşte görünür). Öndeki giriş nişinin yan duvarları dışarı (nişe) bakar
    ama yandan bakışta gövdenin ardında kalır; yan görünüşte derz ve doğrama vermez (D-31 madde 7)."""
    from shapely.geometry import box
    from shapely.ops import unary_union
    x0, y0, x1, y1 = G.govde_kutusu(plan)
    dis_v = {v["ad"] for v in plan.dis_verandalar}
    acik = [m.poly for m in plan.mahaller.values() if m.acik and m.poly is not None and m.ad not in dis_v]
    govde = G.govde_cokgeni(plan)
    govde = govde.difference(unary_union(acik)) if acik else govde
    yuz = d.c + d.h if dis[0] == "+" else d.c - d.h
    a, b = d.p0, d.p1
    if d.yon == "y":
        serit = box(yuz + 0.5, a, x1 + 1, b) if dis[0] == "+" else box(x0 - 1, a, yuz - 0.5, b)
    else:
        serit = box(a, yuz + 0.5, b, y1 + 1) if dis[0] == "+" else box(a, y0 - 1, b, yuz - 0.5)
    ortu = govde.intersection(serit)
    k = 1 if d.yon == "y" else 0                      # duvar boyunca eksen (y duvarında y); derinlik öteki eksende
    parca = [g.bounds for g in getattr(ortu, "geoms", [ortu]) if not g.is_empty and g.area > 0]
    golge = unary_union([box(r[k], 0, r[k + 2], 1) for r in parca if r[3 - k] - r[1 - k] >= 1.0])    # 1 cm'den ince şerit örtmez
    return (b - a) - golge.intersection(box(a, 0, b, 1)).area >= 1.0


def cephe(plan: G.Plan, taraf: str) -> dict:
    """{"en": cephenin eni, "derz": [u], "acikliklar": [{"tur": pencere | dis_kapi, "u0", "u1", "z0", "z1", "olcu", "acilis"}]} (soldan sağa)."""
    yon, dis = _YON[taraf]
    u, _, en = eksen(plan, taraf)
    uu = (lambda a: u(a, 0.0)) if yon == "x" else (lambda a: u(0.0, a))
    duvarlar = [d for d in plan.duvarlar if d.tur == "dis" and d.yon == yon and G.disari_yon(plan, d) == dis and gorunur(plan, d, dis)]
    us = set()
    for d in duvarlar:
        for p in d.panolar:
            us.add(uu(p.a0)); us.add(uu(p.a1))
    for d in plan.duvarlar:
        if d.tur == "dis" and d.yon != yon and cepheye_deger(d, duvarlar):
            us.add(uu(d.c - d.h)); us.add(uu(d.c + d.h))
    ac = []
    for d in duvarlar:
        for p in d.panolar:
            a = p.acilim
            if not a or a.tur not in ("pencere", "dis_kapi"):
                continue
            g = p.gap()
            u0, u1 = sorted((uu(g[0]), uu(g[2])) if yon == "x" else (uu(g[1]), uu(g[3])))
            ust = G.PENCERE_UST_KOTU_CM
            ac.append({"tur": a.tur, "u0": u0, "u1": u1, "z0": ust - a.yukseklik if a.tur == "pencere" else 0.0, "z1": ust,
                       "olcu": a.olcu if a.tur == "pencere" else None, "acilis": a.acilis})
    return {"en": en, "derz": sorted(v for v in us if 1e-6 < v < en - 1e-6), "acikliklar": sorted(ac, key=lambda k: k["u0"])}


def mahya_boylari(plan: G.Plan, ie: dict) -> list[float]:
    """Çatının mahyalarının plandaki boyları, büyükten küçüğe (`cati_genel.cati_kur` kenarları): beşik + cumbada ana mahya (alın sacaklarıyla)
    ve cumbanın mahyası (saçağından ana çatıya girdiği yere), kırmada kırma uçları arası."""
    from . import cati_prefabrik as CP
    from .genel import cati_genel
    ck = cati_genel.cati_kur(CP.cati(plan, ie))
    return sorted((round(float(k["plan_boy"]), 2) for k in ck["kenarlar"] if k["tur"] == "mahya"), reverse=True)


def cati_cizgileri(plan: G.Plan, ie: dict, taraf: str) -> dict:
    """Çatının bu cephedeki çizgileri: {"cizgiler": [[(u, z), ...]], "egimler": [(u, z, eğim)], "u0", "u1": saçak uçları, "tepe": (u, z),
    "sacak_kotu", "topuklar": [u, ...] (iki uçtan başka görünen saçak uçları, `_topuklar`)}. z zeminden (duvar üstü + topuk saçak ucunda)."""
    from shapely.geometry import LineString, MultiLineString, Polygon
    from shapely.ops import unary_union
    from . import cati_prefabrik as CP
    from .genel import cati_genel
    mc = []
    if (ie.get("cati") or {}).get("tip", "besik") == "besik":       # D-31: beşik de dört görünüşte (Motor'un IFC'siyle aynı düzlemler);
        from . import sunum                                          # taşan verandanın çatısı `dxf_out`'ta ayrı çizilir (`veranda`)
        tanim = sunum.cati_tanimi(plan, ie)
        ck = cati_genel.cati_kur(tanim)
        mc = tanim.get("mahal_catilari") or []
    elif plan.dis_verandalar:
        raise CP.PrefabrikCatiHatasi("beşik dışı ana çatıyla taşan veranda görünüşte çizilmez (iki çatının birleşimi; İE-17 PR-2)")
    else:
        ck = cati_genel.cati_kur(CP.cati(plan, ie))
    u, d, _ = eksen(plan, taraf)
    bx, by = _BAKANA[taraf]
    donuk, yan = [], []
    for dz in ck["duzlemler"]:
        yx, yy = dz["yukari"]
        e = dz["egim"]
        bakis = -e * (yx * bx + yy * by) / math.sqrt(1 + e * e)          # normal (−e·yukarı, 1) ile bakana doğru yönün çarpımı
        k2 = [(u(x, y), z) for x, y, z in dz["ucboyut"]]
        derinlik = sum(d(x, y) for x, y, _z in dz["ucboyut"]) / len(k2)
        if bakis > YAN_ESIGI:
            donuk.append((derinlik, k2))
        elif bakis >= -YAN_ESIGI:
            yan.append((derinlik, k2, e))
    perde = []                                                           # kalkanlar: çizilmez (üst kenarı çatının çizgisi), arkasını örter
    for k in ck["kalkanlar"]:
        kose = [(sv, k["konum"], z) if k["eksen"] == "y" else (k["konum"], sv, z) for sv, z in k["kose"]]
        k2 = [(u(x, y), z) for x, y, z in kose]
        if len(k2) >= 3 and Polygon(k2).area > 1:
            perde.append((sum(d(x, y) for x, y, _z in kose) / len(kose), k2))
    cizgi = []

    def ekle(geo):
        for g in (geo.geoms if isinstance(geo, MultiLineString) else [geo]):
            if isinstance(g, LineString) and g.length > 0.5:
                cizgi.append([(round(a, 4), round(b, 4)) for a, b in g.coords])

    def ortu(derinlik, pay):
        """Bu derinlikten yakın dönük düzlemlerin ve kalkanların izdüşümü. Kalkan 0,5 içeriden (üst kenarı yandan görülen düzlemin çizgisi,
        çizgi kalır); düzlem `pay` kadar: dönük düzlemin halkasında +0,05 (ortak kenar bir kez çizilir), yandan görülen düzlemde −0,5
        (dönük düzlemin kenarındaki kırma ve alın çizgisi kalır, eğimi yazılır)."""
        g = unary_union([Polygon(k2).buffer(pay) for d_, k2 in donuk if d_ < derinlik - 1e-6]
                        + [Polygon(k2).buffer(-0.5) for d_, k2 in perde if d_ < derinlik - 1e-6])
        return None if g.is_empty else g

    for derinlik, k2 in donuk:
        halka, o = LineString(k2 + k2[:1]), ortu(derinlik, 0.05)
        ekle(halka if o is None else halka.difference(o))
    egimler = []
    for derinlik, k2, e in yan:                                          # yandan: noktalar bir doğruda; iki uç arası çizgi
        uc = max(((p, q) for p in k2 for q in k2), key=lambda t: math.hypot(t[0][0] - t[1][0], t[0][1] - t[1][1]))
        cizgi_, o = LineString(uc), ortu(derinlik, -0.5)
        gorunen = cizgi_ if o is None else cizgi_.difference(o)
        parca = [g for g in (gorunen.geoms if isinstance(gorunen, MultiLineString) else [gorunen])
                 if isinstance(g, LineString) and g.length >= KISA_CM]          # örtünün kenarında kalan kırıntı çizilmez
        if not parca:
            continue
        for g in parca:
            ekle(g)
        orta = max(parca, key=lambda g: g.length).interpolate(0.5, normalized=True)
        egimler.append((orta.x, orta.y, e))
    noktalar = [p for c in cizgi for p in c]
    tepe = max(noktalar, key=lambda p: p[1])
    u0, u1 = min(p[0] for p in noktalar), max(p[0] for p in noktalar)
    sacak_kotu = min(p[1] for p in noktalar)
    for m in (m for m in mc if m["tip"] != "kirma"):                     # açık mahalin kendi çatısı (AP-09): ana çatının altında; saçak uçları,
        e_, c_ = _mahal_catisi(plan, m, taraf, u, d, ortu)               # tepe ve saçak kotu ana çatıdan (köşe kırması ana çatının düzlemlerinde)
        egimler += e_
        cizgi += c_
    return {"cizgiler": cizgi, "egimler": sorted(egimler), "u0": u0, "u1": u1, "tepe": tepe, "sacak_kotu": sacak_kotu,
            "topuklar": _topuklar(ck, u, d, ortu, (u0, u1), float((ie.get("cati") or {}).get("topuk_cm", 10)))}


def kapali_golge(plan: G.Plan, taraf: str):
    """Kapalı gövdenin (gövde − açık mahaller − dikmeler) `taraf`tan bakışta ardında kalan plan bölgesi: bakışa paralel dilimlerde gövdenin
    bakana en yakın yüzünden geriye. Duvar üstüne kadar olan şeyler (açık mahalin çatısı, dikme, kiriş) bu bölgedeyse görünmez."""
    from shapely.geometry import box
    from shapely.ops import unary_union
    B = 1e5
    acik = [m.poly for m in plan.mahaller.values() if m.acik and m.poly is not None]
    kapali = G.govde_cokgeni(plan).difference(unary_union(acik + [box(*r) for r in plan.dikmeler]))
    i = 0 if taraf in ("on", "arka") else 1
    cs = sorted({round(c[i], 4) for g in getattr(kapali, "geoms", [kapali]) for c in g.exterior.coords})
    out = []
    for a, b in zip(cs, cs[1:]):
        dilim = kapali.intersection(box(a, -B, b, B) if i == 0 else box(-B, a, B, b))
        alan = [g for g in getattr(dilim, "geoms", [dilim]) if g.geom_type == "Polygon" and g.area > 1e-6]     # dilimin kenarındaki çizgi değil
        if not alan:
            continue
        x0, y0, x1, y1 = unary_union(alan).bounds
        out.append({"on": box(a, y0, b, B), "arka": box(a, -B, b, y1), "sol": box(x0, a, B, b), "sag": box(-B, a, x1, b)}[taraf])
    return unary_union(out)


def _mahal_catisi(plan: G.Plan, m: dict, taraf: str, u, d, ortu):
    """Açık mahalin kendi çatısının (`cati_serit.mahal_catilari`) bu görünüşteki çizgileri: kapalı gövdenin ardında kalan kısmı atılır
    (`kapali_golge`); bakana dönük düzlem halkasıyla, yandan görülen çizgi olarak ve eğimiyle, arkaya bakan çizilmez. Ana çatının bakana yakın
    düzlemlerinin ve kalkanlarının örttüğü kısım atılır (`ortu`). Döner: ([(u, z, eğim)] ya da [], çizgiler)."""
    from shapely.geometry import LineString, MultiLineString, Polygon
    from .veranda import kot
    dz = m["duzlem"]
    gor = Polygon(dz["plan"]).difference(kapali_golge(plan, taraf)).simplify(0.01)    # gölgenin kenara değdiği ara nokta atılır
    parca = [g for g in getattr(gor, "geoms", [gor]) if g.geom_type == "Polygon" and g.area > 1]
    if not parca:
        return [], []
    bx, by = _BAKANA[taraf]
    yx, yy = dz["yukari"]
    bakis = -dz["egim"] * (yx * bx + yy * by)
    if bakis < -YAN_ESIGI:
        return [], []
    cizgi, egim = [], []
    for g in parca:
        k2 = [(u(x, y), kot(dz, x, y)) for x, y in g.exterior.coords[:-1]]
        derinlik = sum(d(x, y) for x, y in g.exterior.coords[:-1]) / len(k2)
        o = ortu(derinlik, 0.05)
        if bakis > YAN_ESIGI:
            hat = LineString(k2 + k2[:1])
        else:
            hat = LineString(max(((p, q) for p in k2 for q in k2), key=lambda t: math.hypot(t[0][0] - t[1][0], t[0][1] - t[1][1])))
        gorunen = hat if o is None else hat.difference(o)
        for h in (gorunen.geoms if isinstance(gorunen, MultiLineString) else [gorunen]):
            if isinstance(h, LineString) and h.length > 0.5:
                cizgi.append([(round(a, 4), round(b, 4)) for a, b in h.coords])
                if bakis <= YAN_ESIGI and not egim and h.length >= KISA_CM:
                    orta = h.interpolate(0.5, normalized=True)
                    egim.append((orta.x, orta.y, dz["egim"]))
    return egim, cizgi


def mahal_cati_parcalari(plan: G.Plan, ie: dict, taraf: str) -> list[dict]:
    """Açık mahalin kendi çatısının dikme ve kirişi bu görünüşte (`veranda.gorunus_parcalari`'nın biçimi: {"tur": kolon | kiris, "u": [(u, z)],
    "derinlik"}): dikme zeminden kendi üst kotuna, kiriş alçak kenarda yatay, açık yandaki eğik kiriş çatının altında eğimle
    (`cati_serit.mahal_catilari`). Eğik kiriş yandan bakışta paralelkenar; boyuna bakışta alçak yandan yalnız ucu görünür (ardı çatının
    altında kalır), yüksek yandan bütün izdüşümü. Kapalı gövdenin ardında kalan çizilmez; bakana daha yakın ya da aynı derinlikte bir kirişin
    yüzünün içinde kalan kiriş yüzü (köşede birleşen iki kirişin ucu) bir kez çizilir."""
    from shapely.geometry import MultiPoint, Polygon as P_, box
    from . import cati_serit, sunum
    if (ie.get("cati") or {}).get("tip", "besik") != "besik":
        return []
    mc = (sunum.cati_tanimi(plan, ie) or {}).get("mahal_catilari") or []
    if not mc:
        return []
    golge = kapali_golge(plan, taraf)
    u, d, _ = eksen(plan, taraf)
    adaylar = []
    for m in mc:
        kutular = [("kolon", r[:4], 0.0, r[4]) for r in m["kolonlar"]] + [("kiris", k[:4], k[4], k[5]) for k in m["kirisler"]]
        for tur, (x0, y0, x1, y1), z0, z1 in kutular:
            g = box(x0, y0, x1, y1).difference(golge)
            if g.is_empty or g.area < 1:
                continue
            gx0, gy0, gx1, gy1 = g.bounds
            us = sorted({round(u(x, y), 4) for x in (gx0, gx1) for y in (gy0, gy1)})
            adaylar.append({"tur": tur, "u": [(us[0], z0), (us[-1], z0), (us[-1], z1), (us[0], z1)],
                            "derinlik": min(d(x, y) for x in (gx0, gx1) for y in (gy0, gy1)), "mahal": m["mahal"]})
        ux, uy = m["duzlem"]["yukari"]
        boyuna = d(ux, uy) - d(0, 0)                                       # > 0: bakan alçak yanda, < 0: yüksek yanda, 0: yandan bakış
        for r in m.get("egik_kirisler") or []:
            g = box(*r).difference(golge)
            if g.is_empty or g.area < 1:
                continue
            kose = [(x, y) for x in (g.bounds[0], g.bounds[2]) for y in (g.bounds[1], g.bounds[3])]
            if boyuna > 1e-9:                                              # alçak yandan: yalnız yakın ucunun yüzü
                dmin = min(d(x, y) for x, y in kose)
                kose = [(x, y) for x, y in kose if abs(d(x, y) - dmin) < 1e-6]
            nok = [(round(u(x, y), 4), round(z, 4)) for x, y in kose for z in cati_serit.kiris_kotu(m, x, y)]
            hull = MultiPoint(nok).convex_hull
            if hull.geom_type != "Polygon" or hull.area < 1:
                continue
            adaylar.append({"tur": "kiris", "u": [(round(a, 4), round(b, 4)) for a, b in list(P_(hull.exterior.coords).exterior.coords)[:-1]],
                            "derinlik": min(d(x, y) for x, y in kose), "mahal": m["mahal"]})
    from shapely.ops import unary_union
    out, kirisler = [p for p in adaylar if p["tur"] != "kiris"], []
    for p in (p for p in adaylar if p["tur"] == "kiris"):                # aynı derinlikte değen kiriş yüzleri tek çizgi (köşede birleşen iki kiriş)
        pp, es = P_(p["u"]), [k for k in kirisler if k["mahal"] == p["mahal"] and abs(k["derinlik"] - p["derinlik"]) < 1e-6
                              and k["poly"].buffer(0.01).intersects(P_(p["u"]))]
        for k in es:
            kirisler.remove(k)
        kirisler.append({**p, "poly": unary_union([pp] + [k["poly"] for k in es])})
    for k in kirisler:
        if any(q is not k and q["derinlik"] < k["derinlik"] - 1e-6 and k["poly"].within(q["poly"].buffer(0.01)) for q in kirisler):
            continue                                                       # bakana daha yakın kirişin ardında
        halka = P_(k["poly"].exterior.coords).simplify(0.01)
        out.append({**{a: b for a, b in k.items() if a != "poly"}, "u": [(round(a, 4), round(b, 4)) for a, b in list(halka.exterior.coords)[:-1]]})
    return out


def _topuklar(ck: dict, u, d, ortu, uclar: tuple, topuk: float) -> list[float]:
    """D-34 (Lokman, 30 Ekim 2026 14:45: "veranda makasları topukları onları da ekle"): çatı parçalarının (ana çatı, cumba) saçağının bu
    görünüşte görünen her ucunda topuk, taşan verandadaki gibi (`veranda.gorunus_parcalari`): ucun u'su; çizgi duvar üstünden saçak kotuna
    (`dxf_out`). Saçak, düzlemin en alçak kenarı (birleşen düzlemde tek çizgi); bakışa dik saçağın ucu bakana yakın noktada görünür, bakışa
    paralel saçağın iki ucu. Görünüşün iki ucundaki topuk zaten çizilir (`uclar`). Önünde kalan kalkan, düzlem ya da yakın saçağın topuk
    bandı (duvar üstü ile saçak kotu arası) ucu örtüyorsa çizilmez: soldan bakışta sağ cumbanın saçak ucu sol cumbanın kalkanının, önden
    bakışta sol cumbanınki ana çatının saçağının arkasında. Dikdörtgen gövdede (tek çatı) bütün saçak uçları görünüşün uçlarındadır: çıktı
    aynen."""
    from shapely.geometry import LineString, MultiLineString, box
    from shapely.ops import linemerge, unary_union
    sacaklar = []                                                        # (u uçları, derinlik uçları, saçak kotu)
    for dz in ck["duzlemler"]:
        k = dz["ucboyut"]
        zs = min(z for _x, _y, z in k)
        kenar = [((xa, ya), (xb, yb)) for (xa, ya, za), (xb, yb, zb) in zip(k, k[1:] + k[:1])
                 if abs(za - zs) < 1e-6 and abs(zb - zs) < 1e-6]
        if not kenar:
            continue
        birlesik = linemerge(kenar)                                      # birleşen düzlemde (ana çatı + cumba) saçak bir çizgi, ara noktası uç değil
        for g in (birlesik.geoms if isinstance(birlesik, MultiLineString) else [birlesik]):
            (xa, ya), (xb, yb) = g.coords[0], g.coords[-1]
            sacaklar.append(((u(xa, ya), u(xb, yb)), (d(xa, ya), d(xb, yb)), zs))
    out = []
    for (ua, ub), (da, db), zs in sacaklar:
        adaylar = [(ua, min(da, db))] if abs(ua - ub) < 1e-6 else [(ua, da), (ub, db)]
        for uu, dd in adaylar:
            if any(abs(uu - v) < 0.5 for v in uclar + tuple(out)):
                continue
            bant = [box(min(a, b), z - topuk, max(a, b), z).buffer(-0.5) for (a, b), (e, f), z in sacaklar
                    if abs(a - b) > 1e-6 and (e + f) / 2 < dd - 1e-6]
            o = unary_union([g for g in [ortu(dd, -0.5)] + bant if g is not None and not g.is_empty])
            cizgi = LineString([(uu, zs - topuk), (uu, zs)])
            if o.is_empty or cizgi.difference(o).length > topuk / 2:
                out.append(round(uu, 4))
    return sorted(out)
