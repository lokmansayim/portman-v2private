"""D-107 · BK-39 · PC-43 · Prefabrikte tavan kirişi: makas yönünde 7 m'yi aşan açıklığa köşeye bir kutu profil.

Kural (Lokman, 15 Kasım 2026; `kurallar/yerlesim/prefabrik.json › tavan_kirisi`): makasın geçtiği yerde makas yönündeki açıklık 7 m'yi
aşarsa odaya bir tavan kirişi (kutu profil 100 × 100) konur. Kiriş makasa dik gider, iki ucu duvara oturur; en kısa çizgi seçilir, iki
çizgi eşitse iki ucu da köşede olan. Makaslar 125,5 cm arayla dizilir (`kurallar/liste/prefabrik.json › makas_aralik_cm`): açıklığın
makasların dizildiği yöndeki genişliği 125,5'ten darsa oraya makas gelmez, kiriş de konmaz (102 m²'nin antresi; Lokman 10:20:13).

Motor makasın yerini değil açıklığın bandını okur: bugünkü kodlarda makas yerleri birbirini tutmuyor (IFC ↔ `cati_serit`; kubbede IFC
kurulmuyor). Yöntem:

1. Kapsam: gövdenin çatısının altı (`geometry.govde_cokgeni`); çıkıntılı cumbada yalnız ana çatının dikdörtgeni
   (`cati_prefabrik.cumba_dikdortgenleri`): cumbanın makası öteki yöne gider (93 m² cumba; Lokman 10:22:20 "gerek yok").
2. Makas yönünde her 2,5 cm'de bir çizgi. Duvar, köşe direği ve dikme çizgiyi keser; iki oda arasındaki duvarsız sınırın kirişi de keser
   (listede var; Lokman, kart 22 Ekim). Parçası 7 m'yi aşan çizgiler, aynı odada ardışık ve birbirine binen parçalarla bir bant olur
   (uçları kayabilir). Parça tek bir kapalı odada değilse (duvarsız geçilen birden çok mahal) kiriş konmaz, sorulur.
3. Aday: makasa dik (kiriş yönündeki) bir duvarın ucu bandın bütün çizgilerinin içinde; duvarın ekseni boyunca boşluk bandın bütün
   makaslarını kesip karşı duvara (sınır kirişine ya da dikmeye değil) varır ve aynı odada kalır. En kısa aday seçilir (1 cm'den az fark
   eşit sayılır, varsayım); eşitse iki ucu köşede olan; ekseni 10 cm'den yakın ve aynı uçlu iki aday tek kiriştir (kalın duvarın ekseni:
   65 m²'de 386,5 ile 389,5). Yine eşit kalırsa ya da aday yoksa kiriş konmaz, uyarı yazılır (K21).
4. Odaya bir kiriş (Lokman 09:39:57 "1 tane profil"): bir odaya iki ayrı kiriş gerekiyorsa ya da kirişten sonra 7 m'yi aşan parça
   kalıyorsa kiriş konmaz, sorulur (K21).

Çıktılar: listede "Kutu profil (kiriş) 100 × 100" satırı, boyu yüzden yüze + 2 × 10 (`duvara_oturma_cm`; kart 10:48:34 "Eskizdeki gibi"),
ucunda kolon yok; DXF'in saha montaj planında kiriş (`dxf_out`, katman TAVAN_KIRISI). Uyarı listede adetsiz "Kural yok" satırıdır;
çizime yazılmaz (kirişsiz evin, katalog planları dahil, DXF'i aynen). Ön onay A4 sayfası (M-02), IFC, kart modeli ve montaj rehberi bu
sürümde kirişi çizmez. Hedef örnek `testler/motor/veri/D107_tavan_kirisi_beklenen.json` (paftalardaki üç kiriş)."""
from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import LineString, MultiLineString, Point, box
from shapely.ops import split, unary_union

from . import geometry as G

KOK = Path(__file__).resolve().parents[1]
YERLESIM = KOK / "kurallar" / "yerlesim" / "prefabrik.json"
LISTE_KURALLARI = KOK / "kurallar" / "liste" / "prefabrik.json"

ADIM = 2.5          # cm: tarama çizgilerinin arası (pano ölçülerinin en küçük adımı)
UCA_YAKIN = 20.0    # cm: adayın boşluğu duvarın ucundan en çok bu kadar ötede başlar (köşe direği, H)
KOSE_PAYI = 16.0    # cm: aynı eksende sürüp biten duvarın ucu bu kadar yakınsa kirişin ucu köşededir
AYNI_KIRIS = 10.0   # cm: ekseni bundan yakın, uçları aynı iki aday tek kiriştir
ESIT_PAYI = 1.0    # cm: boyları bundan az farklı iki aday eşit sayılır (varsayım; Lokman'ın sözü "eşitse")


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


def _engeller(plan: G.Plan, e: str):
    """(duvarlar, engeller, sınır kirişleri). Duvar: pano, açıklığın boşluğu (üstünde lento var) ve köşe direği. Engel: duvarlar ve
    dikmeler. Sınır kirişi: iki oda arasındaki duvarsız sınır, listedeki gibi (açık mahale değen sınır sayılmaz;
    `prefabrik_liste.model_motor › ic_kirisler`); makas ona oturur, makas yönündeki açıklığı sınır çizgisinde keser. Makasa paralel
    sınır açıklığı kesmez. Tavan kirişinin ucu sınır kirişine değil duvara oturur (aday aynı odada kalır)."""
    duvar = unary_union([box(*r) for p in plan.panolar for r in p.rects()] + [box(*q) for p in plan.panolar for q in p.gaps()]
                        + [box(*k.rect) for k in plan.koseler])
    acik_g = [m.poly for m in plan.mahaller.values() if m.poly is not None and (m.acik or m.tur in G.ACIK_MAHAL_TURLERI)]
    sinir = [LineString([(x0, y0), (x1, y1)]) for x0, y0, x1, y1 in plan.acik_sinir_cizgileri
             if not any(g_.distance(Point((x0 + x1) / 2, (y0 + y1) / 2)) < 0.5 for g_ in acik_g)
             and ((abs(x1 - x0) < 1e-6) if e == "x" else (abs(y1 - y0) < 1e-6))]       # makasa dik olanlar
    return duvar, unary_union([duvar] + [box(*d) for d in plan.dikmeler]), (MultiLineString(sinir) if sinir else None)


def bul(plan: G.Plan, ie: dict) -> dict:
    """Plan → {"kirisler": [...], "disinda": [...], "uyarilar": [...]}. Kiriş: oda, yön (kirişin koştuğu eksen), eksen, uçlar, yüzden yüze
    boy, liste boyu, iki ucu köşede mi, açıklık ve kirişin böldüğü iki parça (cm, Motor çerçevesi). `disinda`: 7 m'yi aşıp kiriş almayan
    açıklık ve nedeni. 7 m'yi aşan açıklık yoksa üçü de boş. Plan kurulur kurulmaz çağrılır: çıkıntılı cumbanın dikdörtgeni son kurulan
    ızgaranın tamamlamasından okunur (`cati_prefabrik.cumba_dikdortgenleri` → `geometry.tamamla_gercek_cm`)."""
    K = kural()
    c = ie.get("cati") or {}
    e = c.get("makas_ekseni", "x")
    kyon = "y" if e == "x" else "x"                           # kiriş makasa dik
    sonuc = {"kirisler": [], "disinda": [], "uyarilar": []}
    try:
        kap = _kapsam(plan, c)
    except G.IsEmriHatasi as ex:                              # çatı kurulamıyorsa kiriş de aranmaz; sessizce gövdeye düşülmez
        sonuc["uyarilar"].append(f"Tavan kirişi aranmadı: çatının kapsamı kurulamadı ({ex})")
        return sonuc
    x0, y0, x1, y1 = kap.bounds
    A0, A1, B0, B1 = (x0, x1, y0, y1) if e == "x" else (y0, y1, x0, x1)
    if A1 - A0 <= K["esik"]:                                  # hiçbir çizgi eşiği aşamaz
        return sonuc
    duvar, engel, sinir = _engeller(plan, e)
    duvar_t = duvar.buffer(0.01)
    kapali = [m for m in plan.mahaller.values() if m.poly is not None and not (m.acik or m.tur in G.ACIK_MAHAL_TURLERI)]
    tumu = [m for m in plan.mahaller.values() if m.poly is not None]
    icinde = {m.ad: m.poly.buffer(0.5) for m in kapali}
    cizgi = (lambda a, b, t: LineString([(a, t), (b, t)])) if e == "x" else (lambda a, b, t: LineString([(t, a), (t, b)]))
    eks = (lambda q: q[0]) if e == "x" else (lambda q: q[1])   # makas yönündeki koordinat

    # 1-2) bantlar: aynı odada, ardışık ve birbirine binen açıklık çizgileri (uçları kayabilir)
    bantlar: list = []
    acik_bant: list = []
    t = B0 + ADIM / 2
    while t < B1:
        yeni = []
        parcalar = _parcalar(cizgi(A0 - 1, A1 + 1, t).intersection(kap).difference(engel))
        if sinir is not None:                                 # duvarsız sınırın kirişi açıklığı keser
            parcalar = [q for g in parcalar for q in _parcalar(split(g, sinir))]
        for g in parcalar:
            if g.length <= K["esik"]:
                continue
            oda = next((ad for ad, p_ in icinde.items() if p_.contains(g)), None)
            if oda is None:                                   # tek bir kapalı odada değil
                gecen = sorted(m.ad for m in tumu if m.poly.intersection(g).length > 1)
                if not any(m.ad in gecen for m in kapali):
                    continue                                  # yalnız açık mahal (veranda, balkon, niş): kapsam dışı
                oda = " + ".join(gecen)
            aa = [eks(q) for q in g.coords]
            a0, a1 = min(aa), max(aa)
            bn = next((b for b in acik_bant if b["oda"] == oda and a0 < b["son"] and a1 > b["ilk"] and all(b is not y_ for y_ in yeni)), None)
            if bn is None:
                bn = {"oda": oda, "tek": oda in icinde, "lo": t - ADIM / 2, "satirlar": []}
                bantlar.append(bn)
            bn["satirlar"].append((t, a0, a1))
            bn["hi"], bn["ilk"], bn["son"] = t + ADIM / 2, a0, a1
            yeni.append(bn)
        acik_bant = yeni
        t += ADIM

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

    def disari(bn: dict, ac: float, neden: str, uyari: str | None = None, **ek) -> None:
        sonuc["disinda"].append({"oda": bn["oda"], "aciklik_cm": ac, "neden": neden, **ek})
        if uyari:
            sonuc["uyarilar"].append(f"Tavan kirişi: {bn['oda']} açıklığı {_fmt(ac)} cm, 7 m'yi aşıyor; {uyari}")

    # 3) her bandın kirişi
    secilen: dict = {}
    for bn in bantlar:
        lo, hi = round(bn["lo"], 2), round(bn["hi"], 2)
        a0 = max(s_[1] for s_ in bn["satirlar"])              # bandın bütün çizgilerinin ortak aralığı
        a1 = min(s_[2] for s_ in bn["satirlar"])
        ac = round(max(s_[2] - s_[1] for s_ in bn["satirlar"]), 2)
        if hi - lo < K["makas"]:
            disari(bn, ac, f"bant {_fmt(hi - lo)} cm, makas aralığı {_fmt(K['makas'])} cm'den dar: makas gelmez")
            continue
        if c.get("tip", "besik") not in K["cati_tipleri"]:      # kural bu çatı tipi için yazılmadı: kiriş konmaz, sorulur
            disari(bn, ac, f"çatı tipi {c.get('tip')!r} kuralda yok", "çatı tipi kuralda yok, sorulur")
            continue
        if not bn["tek"]:                                     # duvarsız geçilen birden çok mahal: kural "odaya" der, sorulur
            disari(bn, ac, "açıklık birden çok mahalden geçiyor", "açıklık birden çok mahalden geçiyor, kiriş yeri sorulur")
            continue
        aday: dict = {}
        for w in plan.duvarlar:
            if w.yon != kyon or not a0 + 1 < w.c < a1 - 1:
                continue
            for uc, yon in ((w.p0, -1), (w.p1, 1)):
                uzak = -1e4 if yon < 0 else 1e4
                ray = LineString([(w.c, uc), (w.c, uzak)]) if kyon == "y" else LineString([(uc, w.c), (uzak, w.c)])
                kk = (lambda q: [cc[1] for cc in q.coords]) if kyon == "y" else (lambda q: [cc[0] for cc in q.coords])
                ps = sorted((q for q in _parcalar(ray.intersection(kap.buffer(0.01)).difference(engel)) if q.length > 1),
                            key=lambda q: min(abs(v - uc) for v in kk(q)))
                if not ps:
                    continue
                q = ps[0]
                vs = kk(q)
                s0, s1 = (max(vs), min(vs)) if yon < 0 else (min(vs), max(vs))
                if abs(s0 - uc) > UCA_YAKIN:
                    continue
                ote = Point((w.c, s1 + yon * 0.5) if kyon == "y" else (s1 + yon * 0.5, w.c))
                if not duvar_t.contains(ote):                 # öteki ucu duvara varmıyor (açık kenar, dikme ya da sınır kirişi)
                    continue
                if not icinde[bn["oda"]].contains(q):          # aynı odada kalmalı
                    continue
                u0, u1 = sorted((s0, s1))
                if u0 > lo + 2 or u1 < hi - 2:                # bandın bütün makaslarını taşımalı
                    continue
                key = (round(w.c, 2), round(u0, 2), round(u1, 2))
                ik = (kose(w, s0) and kose(w, s1)) or aday.get(key, {}).get("iki_ucu_kose", False)
                parca = (round(max(w.c - s_[1] for s_ in bn["satirlar"]), 2), round(max(s_[2] - w.c for s_ in bn["satirlar"]), 2))
                aday[key] = {"eksen_cm": round(w.c, 2), "uclar_cm": [round(u0, 2), round(u1, 2)], "yuzden_yuze_cm": round(u1 - u0, 2),
                             "iki_ucu_kose": ik, "parcalar_cm": list(parca), "_h": w.h}
        if not aday:
            disari(bn, ac, "kirişin oturacağı köşe bulunamadı", "köşe bulunamadı, kiriş yeri sorulur")
            continue
        en_kisa = min(d["yuzden_yuze_cm"] for d in aday.values())
        kisa = [d for d in aday.values() if d["yuzden_yuze_cm"] <= en_kisa + ESIT_PAYI]     # en kısa ve ona eşit sayılanlar
        if any(d["iki_ucu_kose"] for d in kisa):              # eşitse iki ucu köşede olan (Lokman, kart 10:22:40)
            kisa = [d for d in kisa if d["iki_ucu_kose"]]
        tek = []
        for d in sorted(kisa, key=lambda d: (d["yuzden_yuze_cm"], -d["_h"], d["eksen_cm"])):
            if not any(abs(d["eksen_cm"] - b["eksen_cm"]) < AYNI_KIRIS and all(abs(u - v) < 1 for u, v in zip(d["uclar_cm"], b["uclar_cm"]))
                       for b in tek):
                tek.append(d)                                 # ekseni 10 cm'den yakın aynı uçlu adaylar tek kiriş (kalın duvar)
        if len(tek) > 1:
            disari(bn, ac, "iki eşit yer", f"iki eşit yer var ({', '.join(_fmt(d['eksen_cm']) for d in tek)}), kiriş yeri sorulur",
                   adaylar_cm=[d["eksen_cm"] for d in tek])
            continue
        k = {key: v for key, v in tek[0].items() if not key.startswith("_")}
        secilen.setdefault(bn["oda"], []).append((bn, ac, k))

    # 4) odaya bir kiriş (Lokman 09:39:57 "1 tane profil"): iki ayrı kiriş ya da kirişten sonra 7 m'yi aşan parça kuralda yok, sorulur
    for oda, lst in secilen.items():
        ayri = {(k["eksen_cm"], *k["uclar_cm"]) for _bn, _ac, k in lst}
        ac = max(a_ for _bn, a_, _k in lst)
        if len(ayri) > 1:
            for bn, a_, _k in lst:
                disari(bn, a_, "odaya birden çok kiriş gerekiyor")
            sonuc["uyarilar"].append(f"Tavan kirişi: {oda} açıklığı {_fmt(ac)} cm, 7 m'yi aşıyor; odaya birden çok kiriş gerekiyor, sorulur")
            continue
        k = dict(lst[0][2])
        k["parcalar_cm"] = [max(k_["parcalar_cm"][0] for _b, _a, k_ in lst), max(k_["parcalar_cm"][1] for _b, _a, k_ in lst)]
        if max(k["parcalar_cm"]) > K["esik"]:
            disari(lst[0][0], ac, f"kirişten sonra {_fmt(max(k['parcalar_cm']))} cm'lik parça kalıyor",
                   f"bir kirişten sonra {_fmt(max(k['parcalar_cm']))} cm'lik parça kalıyor, sorulur")
            continue
        sonuc["kirisler"].append({"oda": oda, "yon": kyon, **k, "liste_boyu_cm": round(k["yuzden_yuze_cm"] + 2 * K["oturma"], 2),
                                  "aciklik_cm": ac})
    return sonuc
