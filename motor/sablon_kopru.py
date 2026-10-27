"""BK-14 · Pano Motor'unun planını canlıdaki Örnek Şablon paftasıyla çizmek için Yapı Tanımı biçimine yazar.

Lokman, 27 Ekim 2026 16:43: "uzun zamandır seninle çalıştığımız kurallar nerede, sıfırdan çizim yapıyorsun … eğim hatalı, görünüşler hatalı,
pencereler hatalı". Bayiye giden çizim biçimi onaylıdır: çizim seti (`kurallar/cizim/cizim_seti.json`, Lokman 7 Ekim 2026) ve Örnek Şablon
paftası (`kurallar/cizim/pafta_sablonu.json`, `motor/genel/sablon_pafta.py`; Lokman 6 Ekim 2026). D-12: biçim iki motorda ortak olabilir,
geometri motoru ortak değildir.

Bu modül geometri kurmaz. Pano Motor'unun kurduğu planı (`G.kur`: duvarlar, köşeler, açıklıklar, mahaller, taşan verandalar; açıklık kotları
`ifc_uret.hazirla`'dan) ve çatı düzlemlerini, genel motorun çizim katmanının okuduğu Yapı Tanımı sözlüğüne aktarır; sonra şablon paftası
(`sablon_pafta.pafta_pdf`) onu çizer: 1. sayfa sol yan görünüş + plan + ön görünüş + bina özellikleri, 2. sayfa çatı planı ve dört görünüş.

Değerler İş Emri'nden: kat yüksekliği `duvar_yuksekligi_cm` (250 / 280 / 300, D-14); açıklık üst kotu 200, eşik 200 − boy (BK-13); eğim,
saçak ve topuk `cati`'dan. Genel motorun varsayımları (kat 270, %33) buraya girmez. Çatıyı tek yer kurar (`cati`); beşik dışı çatı İE-17'nin.
"""
from __future__ import annotations

import contextlib
import copy
import json
import sys
from pathlib import Path

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from . import geometry as G

TUR = {"pencere": "pencere", "ic_kapi": "ic_kapi", "dis_kapi": "dis_kapi", "gecis": "gecit"}
KAPLAMA_CM = 0.0               # prefabrik pano tek parça: karkas üstüne ayrı kaplama yok (çelikte boardex / alçıpan 1,25)


class KopruHatasi(G.IsEmriHatasi):
    pass


def _ad(s: str) -> str:
    return " ".join(str(s).split())


# ─────────────────────────────────────────────────────────────────── çatı ──
def cati(plan: G.Plan, ie: dict) -> dict:
    """Çatı: genel motorun `cati` biçimi (düzlemler, kalkanlar, gizli kenarlar). Ana çatı `sunum.cati_tanimi`'nin düzlemleri aynen; taşan
    verandaların çatısı `veranda.cati`'nın düzlemleri, ana çatının saçağının altında kalan kısmı kırpılarak (planda üst üste binmesin). Veranda
    çatısı ana çatının yüzünü aşıyorsa (`veranda.ana_catiya_tasma`, Motor'un uyarısı) kırpma yanlış olur: köprü durur (K16; iki çatının
    birleşimi şablonda yok). Kalkanlar: ana çatının iki alnı (dış duvarın dış yüzünde, duvarlar arasında) ve beşik veranda çatısının dış
    kenardaki alnı (kirişin üstü, kolon dış yüzleri arasında); genel motordaki gibi saçak payı alına girmez. Kaplama kalınlığı pano Motor'unun
    IFC'siyle aynı (`ust_pay`: düzlemin 10 cm üstünde 4 cm sac)."""
    from . import sunum, veranda as VR
    c = sunum.cati_tanimi(plan, ie)
    if c is None:
        raise KopruHatasi(f"Çatı tipi şablon paftasında yok: {(ie.get('cati') or {}).get('tip')} (yalnız beşik; İE-17)")
    c = copy.deepcopy(c)
    x0, y0, x1, y1 = G.govde_kutusu(plan)
    if (ie.get("cati") or {}).get("makas_ekseni", "x") == "x":     # mahya y boyunca: alınlar ön ve arka dış yüzde
        kalkan = [{"ad": "ön kalkan", "eksen": "y", "konum": y0, "aralik": [x0, x1], "ic": "kuzey", "ust": ["sol", "sağ"]},
                  {"ad": "arka kalkan", "eksen": "y", "konum": y1, "aralik": [x0, x1], "ic": "guney", "ust": ["sol", "sağ"]}]
    else:
        kalkan = [{"ad": "sol kalkan", "eksen": "x", "konum": x0, "aralik": [y0, y1], "ic": "dogu", "ust": ["ön", "arka"]},
                  {"ad": "sağ kalkan", "eksen": "x", "konum": x1, "aralik": [y0, y1], "ic": "bati", "ust": ["ön", "arka"]}]
    ana = unary_union([Polygon(d["plan"]) for d in c["duzlemler"]])
    gizli = []
    for v in plan.dis_verandalar:
        t = VR.ana_catiya_tasma(plan, ie, v)
        if t is not None and t > 0.5:
            raise KopruHatasi(f"Veranda {v['ad']}: çatısı ana çatının yüzünü {t:.0f} cm aşıyor; iki çatının birleşimi şablon paftasında "
                              f"çizilmez (Motor'un uyarısı)")
        vc = VR.cati(v, ie)
        on = v["ad"].lower()
        adlar = []
        for d in vc["duzlemler"]:
            xs = [q[0] for q in d["plan"]]; ys = [q[1] for q in d["plan"]]
            ux, uy = d["yukari"]                                        # saçak çizgisi: düzlemin yukarı yönüne göre en alçak kenarı
            d = dict(d, sacak={"x": min(xs) if ux > 0 else max(xs)} if abs(ux) > abs(uy) else {"y": min(ys) if uy > 0 else max(ys)})
            p = Polygon(d["plan"]).difference(ana)
            if p.is_empty or p.area < 1.0:
                continue
            if p.geom_type != "Polygon":
                raise KopruHatasi(f"Veranda {v['ad']}: çatı düzlemi ana çatıyla kırpılınca birden çok parça kalıyor")
            halka = [[round(a, 4), round(b, 4)] for a, b in list(p.exterior.coords)[:-1]]
            ad = f"{on} {d['ad']}"
            adlar.append(ad)
            c["duzlemler"].append(dict(d, ad=ad, plan=halka))
            for a, b in zip(halka, halka[1:] + halka[:1]):              # ana çatının saçak çizgisinde kalan kenar: saçağın altında, görünmez
                if ana.boundary.buffer(0.05).contains(box(min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]) + 1e-6, max(a[1], b[1]) + 1e-6)):
                    gizli.append({"duzlem": ad, "p": a, "q": b, "tur": "gizli", "not": "ana çatının saçağının altında"})
        if vc["tip"] == "besik" and adlar:
            vx0, vy0, vx1, vy1 = v["rect"]
            k = {"on": ("y", vy0, [vx0, vx1], "kuzey"), "arka": ("y", vy1, [vx0, vx1], "guney"),
                 "sol": ("x", vx0, [vy0, vy1], "dogu"), "sag": ("x", vx1, [vy0, vy1], "bati")}[v["cephe"]]
            kalkan.append({"ad": f"{on} alnı", "eksen": k[0], "konum": k[1], "aralik": k[2], "ic": k[3], "ust": adlar})
    c["kalkanlar"] = kalkan
    c["ust_pay"] = 14.0                                  # ifc_uret: sac düzlemin 10 cm üstünde, 4 cm (genel motorun 7'si çeliğin aşık + paneli)
    if gizli:
        c["kenar_ozel"] = gizli
    c["tip_adi"] = "beşik"
    return c


# ─────────────────────────────────────────────────────────────── duvarlar ──
def _duvarlar(plan: G.Plan) -> tuple[list[dict], dict]:
    """Her pano duvarı bir kutu (panolarının uçtan uca boyu × kalınlık); köşe parçaları kendisine dokunan aynı kalınlıktaki duvara katılır."""
    out, kim = [], {}
    for d in plan.duvarlar:
        if not d.panolar:
            continue
        a0, a1 = min(p.a0 for p in d.panolar), max(p.a1 for p in d.panolar)
        k = [a0, d.c - d.h, a1, d.c + d.h] if d.yon == "x" else [d.c - d.h, a0, d.c + d.h, a1]
        out.append({"ad": f"D{d.id}", "sinif": d.tur, "kutu": k, "yukseklik": None, "_yon": d.yon})
        kim[d.id] = out[-1]
    for i, ko in enumerate(plan.koseler):
        kx0, ky0, kx1, ky1 = ko.rect
        for w in out:
            wx0, wy0, wx1, wy1 = w["kutu"]
            if w["_yon"] == "x" and abs(wy0 - ky0) < 0.01 and abs(wy1 - ky1) < 0.01 and (abs(wx0 - kx1) < 0.01 or abs(wx1 - kx0) < 0.01):
                w["kutu"] = [min(wx0, kx0), wy0, max(wx1, kx1), wy1]; break
            if w["_yon"] == "y" and abs(wx0 - kx0) < 0.01 and abs(wx1 - kx1) < 0.01 and (abs(wy0 - ky1) < 0.01 or abs(wy1 - ky0) < 0.01):
                w["kutu"] = [wx0, min(wy0, ky0), wx1, max(wy1, ky1)]; break
        else:
            out.append({"ad": f"K{i}", "sinif": ko.tur, "kutu": list(ko.rect), "yukseklik": None, "_yon": "x"})
    return out, kim


def _oda(plan: G.Plan, nokta) -> str | None:
    from shapely.geometry import Point
    for m in plan.mahaller.values():
        g = m.poly if m.poly is not None else unary_union([box(*r) for r in m.rects])
        if g.contains(Point(*nokta)):
            return m.ad
    return None


# ──────────────────────────────────────────────────────────────── tanım ──
def tanim(ie: dict) -> dict:
    """İş Emri → genel motorun Yapı Tanımı biçimi (yalnız çizim biçimi için). Geometri pano Motor'undan (`G.kur`)."""
    from . import bayi_gorseli as BG, ifc_uret, sunum, veranda as VR
    ie = copy.deepcopy(ie)
    plan = G.kur(copy.deepcopy(ie))
    hz = ifc_uret.hazirla(copy.deepcopy(ie))
    H0 = float((ie.get("yapi") or {}).get("duvar_yuksekligi_cm", 250))
    kapi_mantik = ((ie.get("yapi") or {}).get("dizilim") or {}).get("kapi") == "mantik"
    duvarlar, kim = _duvarlar(plan)
    for w in duvarlar:
        w["yukseklik"] = H0
    # açıklıklar: pano boşluğu (yer) + hazırlığın kotları (eşik, üst kot)
    acl = []
    for d in plan.duvarlar:
        for p in d.panolar:
            a = p.acilim
            if not a:
                continue
            g = p.gap()
            b0, b1 = (g[0], g[2]) if d.yon == "x" else (g[1], g[3])
            hk = [h for h in hz["acikliklar"] if h["yon"] == d.yon and abs(h["c"] - d.c) < 0.6 and abs(h["a0"] - b0) < 0.6 and abs(h["a1"] - b1) < 0.6]
            if len(hk) != 1:
                raise KopruHatasi(f"Açıklığın kotu bulunamadı: {a.tur} {a.olcu} ({d.yon} {d.c}, {b0}–{b1})")
            z0, z1 = float(hk[0]["z0"]), float(hk[0]["z1"])
            e = {"ad": f"A{len(acl) + 1}", "tur": TUR[a.tur], "duvar": kim[d.id]["ad"], "bas": round(b0, 4), "en": round(b1 - b0, 4),
                 "yuk": round(z1 - z0, 4), "alt": z0}
            if a.tur == "pencere":
                k = G.pencere_kurali(a.olcu)
                e.update(etiket=f"{k.en}/{k.boy}", mahal=a.mahal)
            elif a.icine_normal:
                n = a.icine_normal
                cx, cy = (g[0] + g[2]) / 2, (g[1] + g[3]) / 2
                adim = 15.0 * (1 if n[0] == "+" else -1)
                e["mahal"] = _oda(plan, (cx + adim, cy) if n[1] == "x" else (cx, cy + adim))
                e["mentese"] = "bas" if BG._mentese_a0_ucunda(a, kapi_mantik) else "son"
                e["acilim"] = {"+y": "ust", "-y": "alt", "+x": "sag", "-x": "sol"}[n]
            acl.append(e)
    # mahaller
    mahal = []
    oda_hz = {o["ad"]: o for o in hz["odalar"]}
    dis_ad = {v["ad"] for v in plan.dis_verandalar}
    for m in plan.mahaller.values():
        if m.ad in dis_ad:
            continue
        if m.acik:
            raise KopruHatasi(f"Izgara içindeki açık mahal ({m.ad}) şablon köprüsünde yok; taşan veranda `verandalar` ile yazılır")
        o = oda_hz.get(m.ad)
        if o is None:
            raise KopruHatasi(f"Mahalin poligonu yok: {m.ad}")
        pg = Polygon(o["poligon"])
        pt = pg.representative_point()
        e = {"ad": _ad(m.ad), "nokta": [round(pt.x, 2), round(pt.y, 2)], "sinif": "ic", "islev": [m.tur],
             "etiket_m2": round(m.alan_m2, 2), "_pano_ad": m.ad}
        if pg.envelope.area - pg.area > 1.0:            # L oda: yazı pano Motor'unun yerinde (bayi paftası ile aynı); dikdörtgende şablon yerleştirir
            e["etiket_yeri"] = [round(float(o["etiket_xy"][0]), 2), round(float(o["etiket_xy"][1]), 2)]
        mahal.append(e)
    # taşan verandalar: mahal (poligon), köşe kolonları, kirişler
    kirisler = []
    for v in plan.dis_verandalar:
        vx0, vy0, vx1, vy1 = v["rect"]
        mahal.append({"ad": _ad(v["ad"]), "sinif": "veranda", "islev": ["veranda"],
                      "poligon": [[vx0, vy0], [vx1, vy0], [vx1, vy1], [vx0, vy1]], "etiket_m2": round(v["net_m2"], 2) if v.get("net_m2") else None})
        for j, (kx0, ky0, kx1, ky1) in enumerate(v["kirisler"]):
            yatay = (kx1 - kx0) >= (ky1 - ky0)
            kirisler.append({"ad": f"{_ad(v['ad'])} kiriş {j + 1}", "kutu": [kx0, ky0, kx1, ky1], "alt": H0 - VR.KIRIS_CM, "ust": H0,
                             "acik": [[kx0, kx1] if yatay else [ky0, ky1]], "bolge": "veranda"})
    for i, (dx0, dy0, dx1, dy1) in enumerate(plan.dikmeler):
        duvarlar.append({"ad": f"KLN{i + 1}", "sinif": "kolon", "kutu": [dx0, dy0, dx1, dy1], "yukseklik": H0 - VR.KIRIS_CM, "kaplama_yuksekligi": H0 - VR.KIRIS_CM})
    for w in duvarlar:
        w.pop("_yon", None)
    for e in acl:                                     # mahal adları tanımdaki yazımla
        if e.get("mahal"):
            e["mahal"] = _ad(e["mahal"])
    for m in mahal:
        m.pop("_pano_ad", None)
    c = cati(plan, ie)
    kod = sunum.kod_adi(ie)
    say = sunum.sayimlar(plan)
    return {"sema": "portman.yapi_tanimi/0.5-taslak", "kod": kod, "ad": f"{kod} · {say['oturum_m2']:.0f} m² · {say['oda_programi']}",
            "aile": "tek_kat_prefabrik", "paket": "baz", "birim": "cm", "kat": "zemin", "musteri_projesi": True,
            "kaynak": {"cizim": "Pano Motor'unun planı (motor/sablon_kopru.py; geometri G.kur, açıklık kotları ifc_uret.hazirla)",
                       "is_emri": f"{ie.get('is_emri_no')} r{int(ie.get('revizyon') or 1):02d}"},
            "kat_yuksekligi": H0, "lento": H0 - 200.0,
            "yuz_kaplamalari": {"dis": {"kalinlik": KAPLAMA_CM, "malzeme": []}, "ic": {"kalinlik": KAPLAMA_CM, "malzeme": []}},
            "duvar_siniflari": {"dis": {"ad": "dış duvar (pano)", "yuz": {"ic": "ic", "dis": "dis", "veranda": "dis"}},
                                "ic": {"ad": "iç duvar (pano)", "yuz": {"ic": "ic"}},
                                "kolon": {"ad": "veranda dikmesi", "yuz": {"veranda": "dis", "dis": "dis"}}},
            "duvarlar": duvarlar, "mahaller": mahal, "acikliklar": acl, "kirisler": kirisler, "cati": c}


# ──────────────────────────────────────────────────────────────── pafta ──
@contextlib.contextmanager
def _zincir_siluetten():
    """Ölçü zincirleri yapının dış çizgisinden. Genel motorun `zincirler`i dış bölgenin bütün halkalarını okur; kolonun çevresindeki 0,02'lik
    halka (yapi.KAPAT) her cephenin zincirine 10 cm'lik kırıntı ekler. Burada zincir iki siluetin noktalarının birleşimi: (1) gövde, taşan
    veranda ve kolonlar tek siluet (verandanın köşeleri), (2) yalnız gövde (veranda arkasındaki cepheye ulaşan duvarlar; bayi çizimindeki
    392 | 116 | 392 gibi). Yalnız bu paftanın çizimi için geçici olarak sarılır; genel motorun çıktıları değişmez."""
    from .genel import ciz_genel
    asil = ciz_genel.zincirler

    def _kapat(g, e=0.05):                                   # kapanış: 2e'den dar boşluklar dolar
        return g.buffer(e, join_style=2).buffer(-e, join_style=2)

    def _ac(g, e=0.05):                                      # açılış: 2e'den dar şeritler (KAPAT çerçevesi) atılır
        return g.buffer(-e, join_style=2).buffer(e, join_style=2)

    def zincirler(y):
        kolon = [d["geo"] for d in y["duvarlar"] if d["sinif"] == "kolon"]
        if not kolon:
            return asil(y)
        dis = y["bolgeler"]["(dış)"]
        dolu = unary_union([Polygon(h) for h in dis["net"].interiors])
        veranda = [Polygon(m["poligon"]) for m in y["tanim"]["mahaller"] if m.get("sinif") == "veranda" and m.get("poligon")]
        tum = _kapat(unary_union([dolu, *veranda, *kolon]))
        govde = _ac(_kapat(dolu.difference(unary_union([*veranda, *kolon]))))
        govde = unary_union([g for g in getattr(govde, "geoms", [govde]) if g.area > 1e4])     # 1 m²'den küçük kırıntı (kolon halkası) atılır
        out = {}
        for sil in (tum, govde):
            z = asil(dict(y, bolgeler=dict(y["bolgeler"], **{"(dış)": dict(dis, net=Polygon(dis["net"].exterior).difference(sil))})))
            for yan, v in z.items():
                out.setdefault(yan, set()).update(v)
        return {yan: sorted(v) for yan, v in out.items()}

    ciz_genel.zincirler = zincirler
    try:
        yield
    finally:
        ciz_genel.zincirler = asil


def _etiket_yerleri(t: dict, ozet: dict) -> dict[str, list[float]]:
    """Oda yazısının (ad + m²) yeri: yazı kutusu odanın içinde ve kapı yaylarının dışında kalsın. Şablon yazı boyunu odanın sınır kutusunun
    eninden seçer (`plan_ciz`); L odada (yatak odası 1: banyonun altındaki parça) bu en kolun eninden büyük, yazı duvarlara biniyordu. Yazı
    boyu ve ölçek ilk çizimden (`mahal_yazi_pt`, `olcek_pt_cm`); yer, varsayılana (L odada pano Motor'unun polylabel noktası, ötekinde şablonun
    temsil noktası) en yakın uygun nokta. Uygun nokta yoksa (küçük antre) yaya ve dışarı en az taşan yer. Varsayılan yer uygunsa dikdörtgen
    odaya dokunulmaz (şablonun kendi yay kaçırması çalışır). Dönen: {mahal adı: [x, y] cm}."""
    from shapely.geometry import Point
    from shapely.prepared import prep
    from .genel import sablon_pafta as SP, yapi
    y = yapi.kur(t)
    s = float(ozet["olcek_pt_cm"])
    yaylar = []
    for a in t["acikliklar"]:
        if a["tur"] not in ("ic_kapi", "dis_kapi"):
            continue
        w = y["adli"][a["duvar"]]; x0, y0, x1, y1 = w["kutu"]; b0, b1 = a["bas"], a["bas"] + a["en"]; r = a["en"]
        mh = b0 if a.get("mentese", "bas") == "bas" else b1
        if w["yon"] == "x":
            f = y1 if a.get("acilim", "ust") == "ust" else y0
            yon = 1 if a.get("acilim", "ust") == "ust" else -1
            merkez, kare = (mh, f), box(b0, min(f, f + yon * r), b1, max(f, f + yon * r))
        else:
            f = x1 if a.get("acilim") == "sag" else x0
            yon = 1 if a.get("acilim") == "sag" else -1
            merkez, kare = (f, mh), box(min(f, f + yon * r), b0, max(f, f + yon * r), b1)
        yaylar.append(Point(merkez).buffer(r, 64).intersection(kare))
    yay = unary_union(yaylar).buffer(2.0 / s) if yaylar else Polygon()
    out = {}
    for m in t["mahaller"]:
        if m.get("sinif") != "ic":
            continue
        ad = m["ad"]; net = y["bolgeler"][ad]["net"]; pt = float(ozet["mahal_yazi_pt"][ad]); k = pt / 8.4
        metin = SP.yazi_eni(ad.upper(), pt, SP.ARIAL); m2 = SP.yazi_eni(f"{y['bolgeler'][ad]['alan_m2']:.0f} m²", pt + 0.2, SP.ARIAL)
        hw = (max(metin, m2) / 2 + 2.5) / s                       # cm; yanlarda 2,5 pt pay
        hu, hd = (4.6 * k + 0.6 * pt + 1.5) / s, (5.4 * k + 0.6 * pt + 1.5) / s
        bos = net.difference(yay); bos_p = prep(bos)
        kutu = lambda x, y_: box(x - hw, y_ - hd, x + hw, y_ + hu)
        L = net.envelope.area - net.area > 100.0
        p0 = m.get("etiket_yeri") or (lambda q: [q.x, q.y])(net.representative_point())
        if bos_p.contains(kutu(*p0)):
            if L:
                out[ad] = [round(p0[0], 1), round(p0[1], 1)]
            continue
        mx0, my0, mx1, my1 = net.bounds
        adaylar = [(mx0 + i * 2.5, my0 + j * 2.5) for i in range(int((mx1 - mx0) / 2.5) + 1) for j in range(int((my1 - my0) / 2.5) + 1)]
        uygun = [q for q in adaylar if bos_p.contains(kutu(*q))]
        if uygun:
            q = min(uygun, key=lambda q: (round((q[0] - p0[0]) ** 2 + (q[1] - p0[1]) ** 2, 3), -q[1], q[0]))
        else:
            q = min(adaylar, key=lambda q: (round(kutu(*q).difference(bos).area, 1), round((q[0] - p0[0]) ** 2 + (q[1] - p0[1]) ** 2, 3), -q[1], q[0]))
        out[ad] = [round(q[0], 1), round(q[1], 1)]
    return out


# ──────────────────────────────────────────────────────────────── pafta ──
def pafta(ie: dict, hedef: Path, bilgi: dict | None = None, dogrulama: dict | None = None) -> dict:
    """İş Emri → canlıdaki Örnek Şablon paftası: `<kod>_pafta.pdf` (2 sayfa) ve `<kod>_pafta_sablon.png` (1. sayfa). Bina özellikleri ve
    özel istekler prefabrik paftanın kuralından (`sunum.ozellikler`), antet `sunum.bayi_paftasi` ile aynı. K23: Motor'un DXF doğrulaması
    (`sunum.motor_dogrulamasi`; verilmezse burada koşulur) geçmezse dosyalar `.HATALI` adıyla yazılır, `teslim` yanlış. Motor'un uyarıları
    (`plan.uyarilar`) özetin `kontrol_notlari`'na eklenir (K16)."""
    import matplotlib
    from . import sunum
    from .genel import sablon_pafta as SP
    from .genel.uret import matplotlib_sabitle
    t = tanim(ie)
    plan = G.kur(copy.deepcopy(ie))
    dogrulama = dogrulama if dogrulama is not None else sunum.motor_dogrulamasi(copy.deepcopy(ie))
    gecti = dogrulama.get("passed") is True
    say = sunum.sayimlar(plan)
    oz, diger = sunum.ozellikler(ie, say)
    kod = t["kod"]; no = ie.get("is_emri_no") or kod; rev = int(ie.get("revizyon") or 1)
    bilgi = dict(bilgi or {})
    bilgi.setdefault("ozellikler", {k: v for k, v in oz.items() if v and v != "..."})
    bilgi.setdefault("proje_adi", f"{kod} · {say['oturum_m2']:.0f} M² · {say['oda_programi']} PREFABRİK KONUT")
    bilgi.setdefault("bayi_adi", ((ie.get("talep") or {}).get("bayi") or {}).get("ad"))
    bilgi.setdefault("ozel_istekler", list(ie.get("ozel_istekler") or []) + diger)
    hedef = Path(hedef); hedef.mkdir(parents=True, exist_ok=True)
    govde = sunum.dosya_govdesi(ie)

    def ciz():
        with matplotlib.rc_context(), _zincir_siluetten():
            matplotlib_sabitle()
            return SP.pafta_pdf(t, hedef, govde, is_emri_no=no, revizyon=rev, bilgi=bilgi)

    o = ciz()
    yer = _etiket_yerleri(t, o)                       # ölçek ve yazı boyu ilk çizimden; ölçek yazı yerinden bağımsız
    if yer:
        for m in t["mahaller"]:
            if m["ad"] in yer:
                m["etiket_yeri"] = yer[m["ad"]]
        o = ciz()
    (hedef / f"{govde}_yapi_tanimi.json").write_text(json.dumps(t, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    o["kontrol_notlari"] = list(o.get("kontrol_notlari") or []) + [{"kaynak": "motor", "not": u} for u in plan.uyarilar]
    o["dogrulama"] = dogrulama; o["teslim"] = gecti
    if not gecti:                                     # K23: doğrulanmayan plan teslim adıyla yazılmaz
        dosyalar = []
        for ad in o["dosyalar"]:
            yeni = ad.replace("_pafta.pdf", "_pafta.HATALI.pdf").replace("_pafta_sablon.png", "_pafta_sablon.HATALI.png")
            (hedef / ad).replace(hedef / yeni); dosyalar.append(yeni)
        o["dosyalar"] = dosyalar
    (hedef / f"{govde}_pafta_ozet.json").write_text(json.dumps(o, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return o


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("is_emri", type=Path); ap.add_argument("cikti", type=Path)
    a = ap.parse_args(argv)
    o = pafta(json.loads(a.is_emri.read_text(encoding="utf-8")), a.cikti)
    print("yazıldı:", ", ".join(o["dosyalar"]), f"· ölçek 1:{o['olcek_1e']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
