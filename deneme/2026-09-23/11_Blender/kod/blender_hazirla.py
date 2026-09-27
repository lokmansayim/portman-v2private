"""Bayi PDF'i → blender_girdi.json (Blender betiğinin tek girdisi; Blender tarafında pymupdf/shapely gerekmez).

Kaynak yalnız bayinin PDF'idir (pdf_vektor ile okunur): duvar parçaları bayinin çizdiği panolardır, pencere/kapı
bayinin koyduğu yerdedir. Motor'un kural düzeltmeleri burada UYGULANMAZ (bayi planının birebir 3B'si).

Birimler cm; orijin ön-sol dış köşe; +x sağa, +y arkaya (ön cephe y=0), z yukarı.
"""
from __future__ import annotations
import json, math, sys
from pathlib import Path

from shapely.geometry import box as sbox, Point, Polygon, LineString
from shapely.ops import unary_union, polylabel

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from cozumleyici.pdf_vektor import VektorPDF, _norm   # noqa: E402

DUVAR_H = 250.0
LENTO = 50.0
PENCERE_ESIK = {"120x120": 80.0, "120x180": 20.0, "60x40": 160.0}   # BOM notlarındaki eşik yükseklikleri
KAPI_UST = DUVAR_H - LENTO                                            # 200: lento kuralı
MOD = 125.5


def _r(v, n=2):
    return round(float(v), n)


def pano_sinifi(L, t):
    if L <= 11.5:
        return "kose"
    if abs(L - MOD) <= 1.2:
        return "tam"
    if abs(L - MOD / 2) <= 1.2:
        return "yarim"
    return "ozel"


def hazirla(pdf: Path) -> dict:
    v = VektorPDF(pdf)
    k = v.calistir()
    W, H = k["dis_kutu_cm"]["W"], k["dis_kutu_cm"]["H"]
    yaz = k.get("olcu_yazilari_cm", {})
    # --- panolar (bayinin çizdiği parçalar)
    panolar = []
    for i, r in enumerate(k["duvar_parcalari"]):
        x0, y0, x1, y1 = r
        w, h = x1 - x0, y1 - y0
        yon = "x" if w >= h else "y"            # x: yatay duvar (x boyunca uzanır)
        L, t = max(w, h), min(w, h)
        panolar.append({"id": i, "rect": [_r(x0), _r(y0), _r(x1), _r(y1)], "yon": yon, "boy": _r(L), "kalinlik": _r(t),
                        "tur": "dis" if t >= 8.5 else "ic", "sinif": pano_sinifi(L, t), "acikliklar": []})
    # --- açıklıklar → panolara kesim aralığı olarak dağıt
    acikliklar = []
    for p in k["pencereler"]:
        x0, y0, x1, y1 = p["kutu"]
        yatay = (x1 - x0) >= (y1 - y0)
        olcu = p["olcu"] or "120x120"
        en, boy = (int(s) for s in olcu.split("x"))
        esik = PENCERE_ESIK.get(olcu, 90.0)
        a0, a1 = (x0, x1) if yatay else (y0, y1)
        c = (y0 + y1) / 2 if yatay else (x0 + x1) / 2
        acikliklar.append({"tur": "pencere", "olcu": olcu, "yon": "x" if yatay else "y", "a0": _r(a0), "a1": _r(a1), "c": _r(c),
                           "z0": esik, "z1": min(esik + boy, KAPI_UST)})
    for d in k["kapilar"]:
        hx, hy = d["mentese"]; kx, ky = d["kapali_uc"]; ox, oy = d["kanat_ucu"]
        yatay = abs(hy - ky) < abs(hx - kx)
        a0, a1 = (min(hx, kx), max(hx, kx)) if yatay else (min(hy, ky), max(hy, ky))
        c = hy if yatay else hx
        acikliklar.append({"tur": "kapi", "genislik": _r(d["genislik_cizim"]), "yon": "x" if yatay else "y", "a0": _r(a0), "a1": _r(a1),
                           "c": _r(c), "z0": 0.0, "z1": KAPI_UST, "mentese": [hx, hy], "kanat_ucu": [ox, oy], "kapali_uc": [kx, ky]})
    for ai, a in enumerate(acikliklar):
        a["panolar"] = []
        for p in panolar:
            if p["yon"] != a["yon"] or p["sinif"] == "kose":
                continue
            x0, y0, x1, y1 = p["rect"]
            pa0, pa1, pc0, pc1 = (x0, x1, y0, y1) if p["yon"] == "x" else (y0, y1, x0, x1)
            # kapı çizgisi duvarın iç yüzünde durur: dik doğrultuda ±12 cm pay
            if not (pc0 - 12 <= a["c"] <= pc1 + 12):
                continue
            o0, o1 = max(pa0, a["a0"]), min(pa1, a["a1"])
            if o1 - o0 > 1.0:
                p["acikliklar"].append({"aciklik": ai, "a0": _r(o0), "a1": _r(o1), "z0": a["z0"], "z1": a["z1"]})
                a["panolar"].append(p["id"])
        # çizim toleransı: açıklık bir panoya yalnız ≤ 5 cm taşıyorsa (çizim kayması) o panodan kesilmez, açıklık ana panoya kırpılır
        if len(a["panolar"]) > 1:
            ort = {pid: next(x for x in panolar[pid]["acikliklar"] if x["aciklik"] == ai) for pid in a["panolar"]}
            buyuk = [pid for pid in a["panolar"] if ort[pid]["a1"] - ort[pid]["a0"] > 5.0]
            if buyuk and len(buyuk) < len(a["panolar"]):
                for pid in a["panolar"]:
                    if pid not in buyuk:
                        kay = ort[pid]["a1"] - ort[pid]["a0"]
                        panolar[pid]["acikliklar"] = [x for x in panolar[pid]["acikliklar"] if x["aciklik"] != ai]
                        a.setdefault("not", []).append(f"çizim toleransı: {kay:.1f} cm komşu panoya taşıyordu, ana panoya kırpıldı")
                a["panolar"] = buyuk
                p0 = panolar[buyuk[0]]
                lo, hi = (p0["rect"][0], p0["rect"][2]) if a["yon"] == "x" else (p0["rect"][1], p0["rect"][3])
                gen = a["a1"] - a["a0"]
                if a["a0"] < lo: a["a0"], a["a1"] = _r(lo + 1.0), _r(lo + 1.0 + gen)
                if a["a1"] > hi: a["a0"], a["a1"] = _r(hi - 1.0 - gen), _r(hi - 1.0)
                for x in p0["acikliklar"]:
                    if x["aciklik"] == ai: x["a0"], x["a1"] = a["a0"], a["a1"]
        # aynı açıklığı iki paralel duvar yüzü yakalarsa (kapı çizgisi iki duvar arasında), en yakın olanı tut
        if len(a["panolar"]) > 1:
            def uzak(pid):
                x0, y0, x1, y1 = panolar[pid]["rect"]
                cc = (y0 + y1) / 2 if a["yon"] == "x" else (x0 + x1) / 2
                return abs(cc - a["c"])
            en = min(uzak(pid) for pid in a["panolar"])
            tut = [pid for pid in a["panolar"] if uzak(pid) <= en + 1.0]
            for pid in a["panolar"]:
                if pid not in tut:
                    panolar[pid]["acikliklar"] = [x for x in panolar[pid]["acikliklar"] if x["aciklik"] != ai]
            a["panolar"] = tut
    # --- odalar: duvar birleşiminin boşlukları + bayinin etiketleri
    birlesim = unary_union([sbox(*p["rect"]).buffer(0.3, join_style=2) for p in panolar]).buffer(-0.3, join_style=2)
    ana = max([birlesim] if isinstance(birlesim, Polygon) else list(birlesim.geoms), key=lambda g: g.area)
    odalar = []
    for hole in ana.interiors:
        poly = Polygon(hole)
        if poly.area < 1e4:
            continue
        et = [m for m in k["mahaller"] if poly.contains(Point(m["x"], m["y"]))]
        ad = et[0]["ad"] if et else "?"
        pl = polylabel(poly, tolerance=1.0)
        odalar.append({"ad": ad, "etiket_m2": et[0]["m2_etiket"] if et else None, "net_m2": _r(poly.area / 1e4),
                       "etiket_xy": [_r(pl.x), _r(pl.y)], "bayi_etiket_xy": [et[0]["x"], et[0]["y"]] if et else None,
                       "poligon": [[_r(x), _r(y)] for x, y in list(poly.exterior.coords)[:-1]]})
    # veranda: bina gövdesi dışındaki etiket + kesikli çizgi kutusu
    govde = Polygon(ana.exterior)
    vk = k.get("veranda_kutu")
    veranda = None
    ver_et = [m for m in k["mahaller"] if not govde.contains(Point(m["x"], m["y"]))]
    if vk:
        x0, y0, x1, _ = vk
        # arka sınır: veranda etiketinin üstündeki ilk duvar yüzü
        ust = min((p["rect"][1] for p in panolar if p["yon"] == "x" and p["rect"][1] > 0 and p["rect"][0] < x1 - 5 and p["rect"][2] > x0 + 5), default=0)
        veranda = {"poligon": [[x0, y0], [x1, y0], [x1, ust], [x0, ust]], "etiket_m2": ver_et[0]["m2_etiket"] if ver_et else None,
                   "net_m2": _r((x1 - x0) * (ust - y0) / 1e4), "tasma_cm": _r(-y0), "etiket_xy": [ver_et[0]["x"], ver_et[0]["y"]] if ver_et else None}
    # --- tefriş (bayinin mobilya katmanı) → çizgi parçaları (cm)
    tef = []
    for d in v.cizimler:
        if _norm(d.get("layer") or "") not in {"tefris"}:
            continue
        for it in d["items"]:
            if it[0] == "l":
                tef.append([v.cm(it[1].x, it[1].y), v.cm(it[2].x, it[2].y)])
            elif it[0] == "c":
                p0, p1, p2, p3 = it[1], it[2], it[3], it[4]
                pts = []
                for s in range(7):
                    t = s / 6
                    x = (1 - t) ** 3 * p0.x + 3 * (1 - t) ** 2 * t * p1.x + 3 * (1 - t) * t ** 2 * p2.x + t ** 3 * p3.x
                    y = (1 - t) ** 3 * p0.y + 3 * (1 - t) ** 2 * t * p1.y + 3 * (1 - t) * t ** 2 * p2.y + t ** 3 * p3.y
                    pts.append(v.cm(x, y))
                tef += [[pts[j], pts[j + 1]] for j in range(6)]
            elif it[0] == "qu":
                q = it[1]
                pts = [v.cm(q.ul.x, q.ul.y), v.cm(q.ur.x, q.ur.y), v.cm(q.lr.x, q.lr.y), v.cm(q.ll.x, q.ll.y)]
                tef += [[pts[j], pts[(j + 1) % 4]] for j in range(4)]
    tef = [[[_r(a[0]), _r(a[1])], [_r(b[0]), _r(b[1])]] for a, b in tef if math.hypot(a[0] - b[0], a[1] - b[1]) > 0.5]
    return {
        "sema": "portman.blender_girdi/0.1",
        "kaynak": {"dosya": pdf.name, "not": "Bayinin PDF'i (Mustafa Tatar, 16.09.2026, WhatsApp). Motor kuralları uygulanmadı; bayinin çizimi birebir."},
        "bina": {"W": yaz.get("genislik", W), "H": yaz.get("derinlik", H), "duvar_h": DUVAR_H, "lento": LENTO,
                 "cati": {"tip": "besik", "egim": 0.33, "sacak": 30.0, "topuk": 10.0, "makas_yonu": "x (kısa kenar)", "renk": "antrasit"}},
        "panolar": panolar, "acikliklar": acikliklar, "odalar": odalar, "veranda": veranda, "tefris": tef,
        "kanit": k["kanit"], "uyari": k["uyari"],
    }


if __name__ == "__main__":
    pdf = Path(sys.argv[1]); out = Path(sys.argv[2])
    g = hazirla(pdf)
    out.write_text(json.dumps(g, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    print("pano", len(g["panolar"]), Counter((p["tur"], p["sinif"]) for p in g["panolar"]))
    print("açıklık", len(g["acikliklar"]), [(a["tur"], a.get("olcu") or a.get("genislik"), a["panolar"]) for a in g["acikliklar"]])
    print("oda", [(o["ad"], o["etiket_m2"], o["net_m2"]) for o in g["odalar"]])
    print("veranda", g["veranda"]); print("tefriş çizgi", len(g["tefris"]))
