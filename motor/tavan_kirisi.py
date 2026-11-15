"""D-107 · BK-39 · PC-43 · Prefabrikte tavan kirişi: makas yönünde 7 m'yi aşan açıklığa köşeye bir kutu profil.

Kural (Lokman, 15 Kasım 2026; `kurallar/yerlesim/prefabrik.json › tavan_kirisi`): makasın geçtiği yerde makas yönündeki açıklık 7 m'yi
aşarsa odaya bir tavan kirişi (kutu profil 100 × 100) konur. Kiriş makasa dik gider, iki ucu duvara oturur; en kısa çizgi seçilir, iki
çizgi eşitse iki ucu da köşede olan. Makaslar 125,5 cm arayla dizilir (`kurallar/liste/prefabrik.json › makas_aralik_cm`): açıklığın
makasların dizildiği yöndeki genişliği 125,5'ten darsa oraya makas gelmez, kiriş de konmaz (102 m²'nin antresi; Lokman 10:20:13).

Motor makasın yerini değil açıklığın bandını okur: bugünkü kodlarda makas yerleri birbirini tutmuyor (IFC ↔ `cati_serit`; kubbede IFC
kurulmuyor). Yöntem:

1. Kapsam: gövdenin çatısının altı (`geometry.govde_cokgeni`); çıkıntılı cumbada yalnız ana çatının dikdörtgeni
   (`cati_prefabrik.cumba_dikdortgenleri`): cumbanın makası öteki yöne gider (93 m² cumba; Lokman 10:22:20 "gerek yok").
2. Makas yönünde her 2,5 cm'de bir çizgi; duvar, köşe direği ve dikme olmayan parçası 7 m'yi aşan ve ortası kapalı bir odada olan çizgiler
   aynı açıklığın bandıdır (oda, açıklığın iki ucu, ardışık çizgiler).
3. Aday: makasa dik (kiriş yönündeki) bir duvarın ucu açıklığın içinde; duvarın ekseni boyunca boşluk bandın bütün makaslarını kesip
   karşı duvara varır ve aynı odada kalır. En kısa aday seçilir; eşitse iki ucu köşede olan; ekseni 10 cm'den yakın ve aynı uçlu iki aday
   tek kiriştir (kalın duvarın ekseni: 65 m²'de 386,5 ile 389,5). Yine eşit kalırsa ya da aday yoksa kiriş konmaz, uyarı yazılır (K21).

Çıktılar: listede "Kutu profil (kiriş) 100 × 100" satırı, boyu yüzden yüze + 2 × 10 (`duvara_oturma_cm`; kart 10:48:34 "Eskizdeki gibi"),
ucunda kolon yok; DXF'in saha montaj planında kiriş (`dxf_out`, katman TAVAN_KIRISI). Ön onay A4 sayfası (M-02), IFC, kart modeli ve montaj
rehberi bu sürümde kirişi çizmez. Hedef örnek `testler/motor/veri/D107_tavan_kirisi_beklenen.json` (paftalardaki üç kiriş)."""
from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

from . import geometry as G

KOK = Path(__file__).resolve().parents[1]
YERLESIM = KOK / "kurallar" / "yerlesim" / "prefabrik.json"
LISTE_KURALLARI = KOK / "kurallar" / "liste" / "prefabrik.json"

ADIM = 2.5          # cm: tarama çizgilerinin arası (pano ölçülerinin en küçük adımı)
UCA_YAKIN = 20.0    # cm: adayın boşluğu duvarın ucundan en çok bu kadar ötede başlar (köşe direği, H)
KOSE_PAYI = 16.0    # cm: aynı eksende sürüp biten duvarın ucu bu kadar yakınsa kirişin ucu köşededir
AYNI_KIRIS = 10.0   # cm: ekseni bundan yakın, uçları aynı iki aday tek kiriştir


def _fmt(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def kural() -> dict:
    """`tavan_kirisi` kuralının değerleri: eşik, makas aralığı (liste kuralından okunur), duvara oturma, kesit."""
    k = json.loads(YERLESIM.read_text(encoding="utf-8"))["kurallar"]["tavan_kirisi"]
    dosya, anahtar = k["makas_aralik"]["okunan"].split(" › ")
    liste = json.loads((KOK / dosya).read_text(encoding="utf-8"))
    makas = liste["kurallar"][anahtar.split(".", 1)[1]]["deger"]
    return {"esik": float(k["esik_cm"]["deger"]), "makas": float(makas), "oturma": float(k["duvara_oturma_cm"]["deger"]),
            "kesit": float(k["kesit_cm"]["deger"]), "kalem": k["kalem"], "cati_tipleri": tuple(k["cati_tipleri"])}


def _kapsam(plan: G.Plan, c: dict):
    g = G.govde_cokgeni(plan)
    if c.get("tip") == "besik_cumba":
        from .cati_prefabrik import cumba_dikdortgenleri
        ana, _cumbalar = cumba_dikdortgenleri(c, G.govde_kutusu(plan), plan)
        g = g.intersection(box(*ana))
    return g


def _parcalar(g):
    return [q for q in getattr(g, "geoms", [g]) if not q.is_empty and q.geom_type == "LineString"]


def bul(plan: G.Plan, ie: dict) -> dict:
    """Plan → {"kirisler": [...], "disinda": [...], "uyarilar": [...]}. Kiriş: oda, yön (kirişin koştuğu eksen), eksen, uçlar, yüzden yüze
    boy, liste boyu, iki ucu köşede mi, açıklık ve kirişin böldüğü iki parça (cm, Motor çerçevesi). `disinda`: 7 m'yi aşıp kiriş almayan
    açıklık ve nedeni. 7 m'yi aşan açıklık yoksa üçü de boş. Plan kurulur kurulmaz çağrılır: pano ve duvar uçları son kurulan ızgaradan
    okunur (`geometry.X`, `geometry.Y`)."""
    K = kural()
    c = ie.get("cati") or {}
    e = c.get("makas_ekseni", "x")
    kyon = "y" if e == "x" else "x"                           # kiriş makasa dik
    sonuc = {"kirisler": [], "disinda": [], "uyarilar": []}
    try:
        kap = _kapsam(plan, c)
    except Exception as ex:                                   # çatı kurulamıyorsa kiriş de aranmaz; sessizce gövdeye düşülmez
        sonuc["uyarilar"].append(f"Tavan kirişi aranmadı: çatının kapsamı kurulamadı ({ex})")
        return sonuc
    x0, y0, x1, y1 = kap.bounds
    A0, A1, B0, B1 = (x0, x1, y0, y1) if e == "x" else (y0, y1, x0, x1)
    if A1 - A0 <= K["esik"]:                                  # hiçbir çizgi eşiği aşamaz
        return sonuc
    solid = unary_union([box(*r) for p in plan.panolar for r in p.rects()] + [box(*q) for p in plan.panolar for q in p.gaps()]
                        + [box(*k.rect) for k in plan.koseler] + [box(*d) for d in plan.dikmeler])
    kapali = [m for m in plan.mahaller.values() if m.poly is not None and not (m.acik or m.tur in G.ACIK_MAHAL_TURLERI)]
    oda_of = lambda geom: next((m.ad for m in kapali if m.poly.buffer(0.5).contains(geom)), None)   # noqa: E731
    cizgi = (lambda a, b, t: LineString([(a, t), (b, t)])) if e == "x" else (lambda a, b, t: LineString([(t, a), (t, b)]))
    eks = (lambda q: q[0]) if e == "x" else (lambda q: q[1])   # makas yönündeki koordinat

    gruplar: dict = {}
    t = B0 + ADIM / 2
    while t < B1:
        for g in _parcalar(cizgi(A0 - 1, A1 + 1, t).intersection(kap).difference(solid)):
            if g.length <= K["esik"]:
                continue
            oda = oda_of(g.interpolate(0.5, normalized=True))
            if oda is None:
                continue
            aa = [eks(q) for q in g.coords]
            gruplar.setdefault((oda, round(min(aa), 2), round(max(aa), 2)), []).append(t)
        t += ADIM
    bantlar = []
    for (oda, a0, a1), ts in sorted(gruplar.items()):
        ts.sort()
        bas = ts[0]
        for i in range(1, len(ts) + 1):                       # ardışık çizgiler tek bant
            if i == len(ts) or ts[i] - ts[i - 1] > 1.5 * ADIM:
                bantlar.append({"oda": oda, "aciklik": (a0, a1), "bant": (round(bas - ADIM / 2, 2), round(ts[i - 1] + ADIM / 2, 2))})
                if i < len(ts):
                    bas = ts[i]

    def kose(w, s: float) -> bool:
        """Kirişin `s`'deki ucu köşede mi: aynı eksende süren bir duvar orada biter ya da dik bir duvarın yüzü oradadır ve o duvar kirişin
        ekseninde biter."""
        for z in plan.duvarlar:
            if z is w:
                continue
            if z.yon == kyon and abs(z.c - w.c) < 0.6 and (abs(z.p0 - s) < KOSE_PAYI or abs(z.p1 - s) < KOSE_PAYI):
                return True
            if z.yon != kyon and abs(abs(z.c - s) - z.h) < 0.6 and min(abs(z.p0 - w.c), abs(z.p1 - w.c)) < w.h + 1.5:
                return True
        return False

    for bn in bantlar:
        (a0, a1), (lo, hi) = bn["aciklik"], bn["bant"]
        ac = round(a1 - a0, 2)
        if hi - lo < K["makas"]:
            sonuc["disinda"].append({"oda": bn["oda"], "aciklik_cm": ac,
                                     "neden": f"bant {_fmt(hi - lo)} cm, makas aralığı {_fmt(K['makas'])} cm'den dar: makas gelmez"})
            continue
        if c.get("tip", "besik") not in K["cati_tipleri"]:      # kural bu çatı tipi için yazılmadı: kiriş konmaz, sorulur
            sonuc["disinda"].append({"oda": bn["oda"], "aciklik_cm": ac, "neden": f"çatı tipi {c.get('tip')!r} kuralda yok"})
            sonuc["uyarilar"].append(f"Tavan kirişi: {bn['oda']} açıklığı {_fmt(ac)} cm, 7 m'yi aşıyor; çatı tipi kuralda yok, sorulur")
            continue
        aday: dict = {}
        for w in plan.duvarlar:
            if w.yon != kyon or not a0 + 1 < w.c < a1 - 1:
                continue
            for uc, yon in ((w.p0, -1), (w.p1, 1)):
                uzak = -1e4 if yon < 0 else 1e4
                ray = LineString([(w.c, uc), (w.c, uzak)]) if kyon == "y" else LineString([(uc, w.c), (uzak, w.c)])
                kk = (lambda q: [cc[1] for cc in q.coords]) if kyon == "y" else (lambda q: [cc[0] for cc in q.coords])
                ps = sorted((q for q in _parcalar(ray.intersection(kap.buffer(0.01)).difference(solid)) if q.length > 1),
                            key=lambda q: min(abs(v - uc) for v in kk(q)))
                if not ps:
                    continue
                q = ps[0]
                vs = kk(q)
                s0, s1 = (max(vs), min(vs)) if yon < 0 else (min(vs), max(vs))
                if abs(s0 - uc) > UCA_YAKIN:
                    continue
                ote = Point((w.c, s1 + yon * 0.5) if kyon == "y" else (s1 + yon * 0.5, w.c))
                if not solid.buffer(0.01).contains(ote):      # öteki ucu duvara varmıyor (gövdenin açık kenarı)
                    continue
                if oda_of(q) != bn["oda"]:
                    continue
                u0, u1 = sorted((s0, s1))
                if u0 > lo + 2 or u1 < hi - 2:                # bandın bütün makaslarını taşımalı
                    continue
                key = (round(w.c, 2), round(u0, 2), round(u1, 2))
                ik = (kose(w, s0) and kose(w, s1)) or aday.get(key, {}).get("iki_ucu_kose", False)
                aday[key] = {"eksen_cm": round(w.c, 2), "uclar_cm": [round(u0, 2), round(u1, 2)], "yuzden_yuze_cm": round(u1 - u0, 2),
                             "iki_ucu_kose": ik, "parcalar_cm": [round(w.c - a0, 2), round(a1 - w.c, 2)], "_h": w.h}
        al = sorted(aday.values(), key=lambda d: (round(d["yuzden_yuze_cm"]), not d["iki_ucu_kose"], -d["_h"], d["eksen_cm"]))
        tek = []
        for d in al:
            if not any(abs(d["eksen_cm"] - b["eksen_cm"]) < AYNI_KIRIS and all(abs(u - v) < 1 for u, v in zip(d["uclar_cm"], b["uclar_cm"]))
                       for b in tek):
                tek.append(d)
        if not tek:
            sonuc["disinda"].append({"oda": bn["oda"], "aciklik_cm": ac, "neden": "kirişin oturacağı köşe bulunamadı"})
            sonuc["uyarilar"].append(f"Tavan kirişi: {bn['oda']} açıklığı {_fmt(ac)} cm, 7 m'yi aşıyor; köşe bulunamadı, kiriş yeri sorulur")
            continue
        esit = [d for d in tek if round(d["yuzden_yuze_cm"]) == round(tek[0]["yuzden_yuze_cm"]) and d["iki_ucu_kose"] == tek[0]["iki_ucu_kose"]]
        if len(esit) > 1:
            sonuc["disinda"].append({"oda": bn["oda"], "aciklik_cm": ac, "neden": "iki eşit yer",
                                     "adaylar_cm": [d["eksen_cm"] for d in esit]})
            sonuc["uyarilar"].append(f"Tavan kirişi: {bn['oda']} açıklığı {_fmt(ac)} cm; iki eşit yer var "
                                     f"({', '.join(_fmt(d['eksen_cm']) for d in esit)}), kiriş yeri sorulur")
            continue
        k = {key: v for key, v in tek[0].items() if not key.startswith("_")}
        sonuc["kirisler"].append({"oda": bn["oda"], "yon": kyon, **k, "liste_boyu_cm": round(k["yuzden_yuze_cm"] + 2 * K["oturma"], 2),
                                  "aciklik_cm": ac})
    return sonuc
