"""İE-17 · Prefabrik evin dört cephe görünüşünün geometrisi; çizimi canlı ön onay PDF'inin "ÇALIŞMA" görünüşü (`dxf_out.ciz_gorunusler`).

Lokman, 27 Ekim 2026 21:06; CIO 21:13: prefabrik bayiye canlıda `dxf_out`'un ön onay PDF'i ve `bayi_gorseli`'nin plan görseli gidiyordu;
biçim bu ikisinden, genel motordan yalnız çatı ve görünüş geometrisi. Bu modül çizmez; `dxf_out` çizer.

- Duvar, pano derzleri, pencere ve kapı Motor'un `Plan`'ından, ön görünüşün kuralıyla (`dxf_out.ciz_on_gorunus`): cephenin dış duvarları
  dışarı yönü o cepheye bakanlar (`G.disari_yon`; açık mahale bakan duvar da), derzler panoların uçları ve dik dış duvarların yüzleri,
  açıklık panonun boşluğunda (`Pano.gap`), üst kot 200, eşik 200 − boy (BK-13), kapı 0–200.
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


def cephe(plan: G.Plan, taraf: str) -> dict:
    """{"en": cephenin eni, "derz": [u], "acikliklar": [{"tur": pencere | dis_kapi, "u0", "u1", "z0", "z1"}]} (soldan sağa)."""
    yon, dis = _YON[taraf]
    u, _, en = eksen(plan, taraf)
    uu = (lambda a: u(a, 0.0)) if yon == "x" else (lambda a: u(0.0, a))
    duvarlar = [d for d in plan.duvarlar if d.tur == "dis" and d.yon == yon and G.disari_yon(plan, d) == dis]
    us = set()
    for d in duvarlar:
        for p in d.panolar:
            us.add(uu(p.a0)); us.add(uu(p.a1))
    for d in plan.duvarlar:
        if d.tur == "dis" and d.yon != yon:
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
            ac.append({"tur": a.tur, "u0": u0, "u1": u1, "z0": ust - a.yukseklik if a.tur == "pencere" else 0.0, "z1": ust})
    return {"en": en, "derz": sorted(v for v in us if 1e-6 < v < en - 1e-6), "acikliklar": sorted(ac, key=lambda k: k["u0"])}


def cati_cizgileri(plan: G.Plan, ie: dict, taraf: str) -> dict:
    """Çatının bu cephedeki çizgileri: {"cizgiler": [[(u, z), ...]], "egimler": [(u, z, eğim)], "u0", "u1": saçak uçları, "tepe": (u, z),
    "sacak_kotu"}. z zeminden (duvar üstü + topuk saçak ucunda)."""
    from shapely.geometry import LineString, MultiLineString, Polygon
    from shapely.ops import unary_union
    from . import cati_prefabrik as CP
    from .genel import cati_genel
    if plan.dis_verandalar:
        raise CP.PrefabrikCatiHatasi("beşik dışı ana çatıyla taşan veranda görünüşte çizilmez (iki çatının birleşimi; İE-17 PR-2)")
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
    return {"cizgiler": cizgi, "egimler": sorted(egimler), "u0": min(p[0] for p in noktalar), "u1": max(p[0] for p in noktalar),
            "tepe": tepe, "sacak_kotu": min(p[1] for p in noktalar)}
