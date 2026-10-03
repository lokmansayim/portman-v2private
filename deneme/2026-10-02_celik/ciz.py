#!/usr/bin/env python3
"""Çelik (A1) deneme çizicisi: Yapı Tanımı taslağından plan, alanlar ve Boardex metrajı.

Deneme kodudur; canlıda değildir ve Motor'un yerine geçmez.
Duvar kalınlığı duvar tipinin katmanlarından hesaplanır (duvar_tipleri.json).
`--cizim-kalinligi` ile arşivdeki çizimin kalınlıkları (12 / 11 cm) kullanılır ve
hesaplanan mahal alanları çizimdeki etiketlerle karşılaştırılır (okuma denetimi).

Seçenek (değişiklik operatörü): `--secenek secenekler/<kod>.json` tanımın alanlarını değiştirir;
çıktı adlarına seçeneğin kodu eklenir. Örnek: dış duvar karkası 140 mm.

Kullanım:
    python ciz.py C8201.json                    # katmanlardan: plan + rapor
    python ciz.py C8201.json --cizim-kalinligi  # çizimle karşılaştırma; fark varsa çıkış kodu 1
    python ciz.py C8201.json --secenek secenekler/dis_karkas_140.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Polygon as MplPolygon
from shapely.geometry import Point, box
from shapely.ops import unary_union

BURADA = Path(__file__).resolve().parent
LEVHA_M2 = 1.20 * 2.40
ETIKET_TOL = 0.06  # çizim etiketleri 0,1 m²'ye yuvarlı


def tr(v: float, n: int = 1) -> str:
    return f"{v:.{n}f}".replace(".", ",")


def secenek_uygula(tanim: dict, yollar) -> tuple[dict, str]:
    """Seçenek dosyalarını tanıma uygular. Dönen ek, çıktı adlarına eklenir."""
    ek, uygulanan = "", []
    for y in yollar or []:
        sc = json.loads(Path(y).read_text(encoding="utf-8"))
        for k, v in sc["degisiklik"].items():
            if k not in tanim:
                raise SystemExit(f"Seçenek {sc['kod']}: tanımda '{k}' alanı yok.")
            tanim[k] = v
        ek += "_" + sc["kod"]
        uygulanan.append({"kod": sc["kod"], "ad": sc["ad"]})
    tanim["secenekler"] = uygulanan
    return tanim, ek


def karkas_mm(tipler: dict, ad: str) -> float:
    return next(k["kalinlik"] for k in tipler["tipler"][ad]["katmanlar"] if k["malzeme"] == "Çelik karkas")


def kalinliklar(tipler: dict, tanim: dict, cizim: bool) -> tuple[float, float]:
    if cizim:
        k = tipler["cizim_kalinliklari_kayit"]
        return float(k["dis_cm"]), float(k["ic_cm"])

    def toplam(ad: str) -> float:
        return sum(k["kalinlik"] for k in tipler["tipler"][ad]["katmanlar"]) / 10.0

    return toplam(tanim["dis_duvar_tipi"]), toplam(tanim["ic_duvar_tipi"])


def ic_duvar_kutusu(d: dict, ti: float, hepsi=()):
    """İç duvarın plandaki dikdörtgeni. Ucu, kendisine dik başka bir iç duvarın aksında bitiyorsa yarım kalınlık uzatılır:
    L birleşimde dış köşe dolar; T birleşimde uzantı öteki duvarın içinde kalır."""
    bas, son = d["bas"], d["son"]
    for o in hepsi:
        if o is d or o["yon"] == d["yon"] or not (o["bas"] - 1e-6 <= d["aks"] <= o["son"] + 1e-6):
            continue
        if abs(o["aks"] - bas) < 1e-6:
            bas -= ti / 2
        if abs(o["aks"] - son) < 1e-6:
            son += ti / 2
    if d["yon"] == "dusey":
        return box(d["aks"] - ti / 2, bas, d["aks"] + ti / 2, son)
    return box(bas, d["aks"] - ti / 2, son, d["aks"] + ti / 2)


def oda_koseleri(poligon) -> tuple[int, int]:
    """Odanın (iç köşe, dış köşe) sayısı. İç köşe: iki duvarın odanın içinde buluştuğu köşe; dış köşe: odaya doğru çıkıntı yapan köşe."""
    from shapely.geometry.polygon import orient
    k = list(orient(poligon, 1.0).exterior.coords)[:-1]
    ic = dis = 0
    for i in range(len(k)):
        (x0, y0), (x1, y1), (x2, y2) = k[i - 1], k[i], k[(i + 1) % len(k)]
        capraz = (x1 - x0) * (y2 - y1) - (y1 - y0) * (x2 - x1)
        if capraz > 1e-6:
            ic += 1
        elif capraz < -1e-6:
            dis += 1
    return ic, dis


def yuz_parcalari(poligon, tanim: dict, td: float, ti: float, duvar: str) -> list:
    """Odanın sınırının, verilen duvarın yüzü üzerinde kalan parçaları: [((x0, y0), (x1, y1)), ...].
    Parçalar saat yönünün tersine sıralıdır (oda, parçanın solunda kalır). duvar: iç duvar adı ya da dis:alt | dis:ust | dis:sol | dis:sag."""
    from shapely.geometry.polygon import orient
    W, H = tanim["kapali"]["en"], tanim["kapali"]["boy"]
    if duvar.startswith("dis:"):
        yatay = duvar in ("dis:alt", "dis:ust")
        sabitler = [{"dis:alt": td, "dis:ust": H - td, "dis:sol": td, "dis:sag": W - td}[duvar]]
        alt, ust = -1e9, 1e9
    else:
        d = next(x for x in tanim["ic_duvarlar"] if x["ad"] == duvar)
        yatay = d["yon"] == "yatay"
        sabitler = [d["aks"] - ti / 2, d["aks"] + ti / 2]
        alt, ust = d["bas"] - ti / 2 - 1e-6, d["son"] + ti / 2 + 1e-6
    k = list(orient(poligon, 1.0).exterior.coords)
    parcalar = []
    for (x0, y0), (x1, y1) in zip(k, k[1:]):
        if yatay and abs(y0 - y1) < 1e-6 and any(abs(y0 - c) < 1e-6 for c in sabitler) and min(x0, x1) >= alt and max(x0, x1) <= ust:
            parcalar.append(((x0, y0), (x1, y1)))
        elif not yatay and abs(x0 - x1) < 1e-6 and any(abs(x0 - c) < 1e-6 for c in sabitler) and min(y0, y1) >= alt and max(y0, y1) <= ust:
            parcalar.append(((x0, y0), (x1, y1)))
    return parcalar


def yuz_boyu(poligon, tanim: dict, td: float, ti: float, duvar: str) -> float:
    """Odanın sınırının, verilen duvarın yüzü üzerinde kalan boyu (cm)."""
    return sum(math.dist(a, b) for a, b in yuz_parcalari(poligon, tanim, td, ti, duvar))


def osb_takviye_hesapla(tanim: dict, mahaller: list, td: float, ti: float) -> dict | None:
    """İç duvarda OSB takviyesi (Ubeydullah, 3 Ekim 2026): bütün oda değil, yalnız dolap ve TV ünitesi gelen duvarların metrajı.
    Tanımdaki `osb_takviye.duvarlar` listesinden: her duvarın o odaya bakan yüzünün boyu × duvar yüksekliği − o yüzdeki boşluklar."""
    ot = tanim.get("osb_takviye")
    if not ot:
        return None
    h = tanim["duvar_yuksekligi"] / 100.0
    satirlar, brut, bosluk = [], 0.0, 0.0
    for dv in ot["duvarlar"]:
        m = next((x for x in mahaller if x["ad"] == dv["mahal"]), None)
        if m is None:
            raise SystemExit(f"OSB takviyesi: mahal bulunamadı: {dv['mahal']}")
        parcalar = yuz_parcalari(m["poligon"], tanim, td, ti, dv["duvar"])
        boy = sum(math.dist(a, b) for a, b in parcalar)
        if boy <= 0:
            raise SystemExit(f"OSB takviyesi: {dv['mahal']} mahalinin {dv['duvar']} duvarına bakan yüzü yok.")
        bos = [a for a in tanim["acikliklar"] if a["duvar"] == dv["duvar"] and aciklik_kutusu(a, tanim, td, ti).buffer(0.5).intersects(m["poligon"])]
        b = sum(bosluk_m2(a) for a in bos)
        brut += boy / 100.0 * h
        bosluk += b
        if dv["duvar"].startswith("dis:"):
            duvar_adi = {"dis:alt": "alt dış duvar", "dis:ust": "üst dış duvar", "dis:sol": "sol dış duvar", "dis:sag": "sağ dış duvar"}[dv["duvar"]]
        else:
            duvar_adi = next(x for x in tanim["ic_duvarlar"] if x["ad"] == dv["duvar"]).get("not", dv["duvar"]) + " duvar"
        satirlar.append({"mahal": dv["mahal"], "duvar": dv["duvar"], "duvar_adi": duvar_adi, "neden": dv.get("neden"), "boy_cm": boy, "bosluk_m2": b,
                         "parcalar": parcalar, "bosluk_araliklari": [(a["bas"], a["bas"] + a["en"]) for a in bos]})
    return {"duvarlar": satirlar, "brut_m2": brut, "bosluk_m2": bosluk, "net_m2": brut - bosluk}


def aciklik_kutusu(a: dict, tanim: dict, td: float, ti: float):
    """Açıklığın duvarı boydan boya kestiği dikdörtgen."""
    W, H = tanim["kapali"]["en"], tanim["kapali"]["boy"]
    b, e = a["bas"], a["bas"] + a["en"]
    dv = a["duvar"]
    if dv == "dis:alt":
        return box(b, 0, e, td)
    if dv == "dis:ust":
        return box(b, H - td, e, H)
    if dv == "dis:sol":
        return box(0, b, td, e)
    if dv == "dis:sag":
        return box(W - td, b, W, e)
    d = next(x for x in tanim["ic_duvarlar"] if x["ad"] == dv)
    if d["yon"] == "dusey":
        return box(d["aks"] - ti / 2, b, d["aks"] + ti / 2, e)
    return box(b, d["aks"] - ti / 2, e, d["aks"] + ti / 2)


def bosluk_m2(a: dict) -> float:
    """Açıklığın duvarda bıraktığı boşluk (m²). Kapıda kaba boşluk ayrıca verilmişse o kullanılır."""
    en, yuk = a.get("bosluk", (a["en"], a["yuk"]))
    return en * yuk / 1e4


def veranda_cercevesi(tanim: dict) -> dict | None:
    """Veranda çerçevesi (Lokman, 3 Ekim 2026 13:27): sırtı 80 mm, genişliği 30 cm; kirişler yanlara ve karşıya,
    altlarına 240 cm, kiriş gibi dikmeler. Kirişler `kiris_kenarlari`nda, dikmeler `dikme_kenari` boyunca eşit aralıkla."""
    v = tanim.get("veranda")
    if not v or "cerceve" not in v:
        return None
    c = v["cerceve"]
    x0, y0, x1, y1 = v["x"], v["y"], v["x"] + v["en"], v["y"] + v["boy"]
    kenar = {"alt": ((x0, y0), (x1, y0)), "ust": ((x0, y1), (x1, y1)), "sag": ((x1, y0), (x1, y1)), "sol": ((x0, y0), (x0, y1))}
    kirisler = [kenar[k] for k in c["kiris_kenarlari"]]
    (ax_, ay_), (bx_, by_) = kenar[c["dikme_kenari"]]
    n, g, sr = c["dikme_adedi"], c["genislik"], c["sirt"]
    dikmeler = []
    for i in range(n):
        if ax_ == bx_:   # düşey kenar: dikmenin geniş yüzü kenar boyunca
            y = ay_ + i * (by_ - ay_ - g) / max(n - 1, 1)
            x = ax_ - sr if c["dikme_kenari"] == "sag" else ax_
            dikmeler.append(box(x, y, x + sr, y + g))
        else:
            x = ax_ + i * (bx_ - ax_ - g) / max(n - 1, 1)
            y = ay_ - sr if c["dikme_kenari"] == "ust" else ay_
            dikmeler.append(box(x, y, x + g, y + sr))
    return {"kirisler": kirisler, "kiris_boyu": sum(math.dist(a, b) for a, b in kirisler), "dikmeler": dikmeler,
            "sirt": sr, "genislik": g, "dikme_boyu": c["dikme_boyu"], "dikme_adedi": n, "dikme_kenari": c["dikme_kenari"],
            "kiris_kenarlari": list(c["kiris_kenarlari"])}


def hesapla(tanim: dict, tipler: dict, cizim: bool) -> dict:
    W, H = tanim["kapali"]["en"], tanim["kapali"]["boy"]
    td, ti = kalinliklar(tipler, tanim, cizim)
    ic_kutu = box(td, td, W - td, H - td)
    dis_halka = box(0, 0, W, H).difference(ic_kutu)
    ic = unary_union([ic_duvar_kutusu(d, ti, tanim["ic_duvarlar"]) for d in tanim["ic_duvarlar"]]).intersection(ic_kutu)
    bosluk = ic_kutu.difference(ic)
    parcalar = list(bosluk.geoms) if hasattr(bosluk, "geoms") else [bosluk]
    mahaller = []
    for m in tanim["mahaller"]:
        p = next((g for g in parcalar if g.contains(Point(*m["nokta"]))), None)
        if p is None:
            raise SystemExit(f"Mahal bulunamadı: {m['ad']}")
        ic_kose, dis_kose = oda_koseleri(p)
        mahaller.append({"ad": m["ad"], "poligon": p, "alan_m2": p.area / 1e4, "cevre_m": p.length / 100.0,
                         "ic_kose": ic_kose, "dis_kose": dis_kose, "islev": list(m.get("islev", []))})
    if len(parcalar) != len(mahaller):
        raise SystemExit(f"Kapalı kısım {len(parcalar)} parçaya bölündü, {len(mahaller)} mahal tanımlı.")
    v = tanim.get("veranda")
    veranda_m2 = v["en"] * v["boy"] / 1e4 if v else 0.0
    # Boardex: dış duvarların tüm çevre uzunluğu × yükseklik − kapı ve pencere boşlukları (Lokman, 2 Ekim)
    h = tanim["duvar_yuksekligi"] / 100.0
    cevre = 2 * (W + H) / 100.0
    bosluklar = sum(bosluk_m2(a) for a in tanim["acikliklar"] if a["duvar"].startswith("dis:"))
    net = cevre * h - bosluklar
    ic_cevre = 2 * ((W - 2 * td) + (H - 2 * td)) / 100.0          # dış duvarların iç yüzü (alçıpan yüzü)
    # Lento kuralı (Lokman, 2 Ekim 20:40): lento her zaman 70 cm; pencerenin üst kotu = duvar yüksekliği − lento.
    # Kapılarda başlık kotu açıklığın kendi yüksekliğidir: iç kapı boşluğu 214 (Lokman, 3 Ekim 13:27), dış kapı 210 (modeller ve listeler).
    ust_kot = tanim["duvar_yuksekligi"] - tanim["lento"] if "lento" in tanim else None
    kotlar = []
    for a in tanim["acikliklar"]:
        if "yuk" not in a:
            continue
        if a["tur"] == "pencere":
            if ust_kot is None:
                continue
            alt, ust = ust_kot - a["yuk"], ust_kot
            if alt < 0:
                raise SystemExit(f"Lento kuralına uymayan pencere: {a}")
        else:
            alt, ust = 0, a["yuk"]
            if ust > tanim["duvar_yuksekligi"]:
                raise SystemExit(f"Kapı duvardan yüksek: {a}")
        kotlar.append({"duvar": a["duvar"], "bas": a["bas"], "en": a["en"], "tur": a["tur"], "alt": alt, "ust": ust})
    return {
        "aciklik_ust_kotu": ust_kot, "aciklik_kotlari": kotlar,
        "td": td, "ti": ti, "dis_halka": dis_halka, "ic_duvarlar": ic, "mahaller": mahaller,
        "osb_takviye": osb_takviye_hesapla(tanim, mahaller, td, ti),
        "kapali_brut_m2": W * H / 1e4, "kapali_net_m2": sum(m["alan_m2"] for m in mahaller),
        "veranda_m2": veranda_m2, "toplam_oturum_m2": W * H / 1e4 + veranda_m2,
        "boardex": {"cevre_m": cevre, "yukseklik_m": h, "brut_m2": cevre * h, "bosluk_m2": bosluklar,
                    "net_m2": net, "levha_adedi_firesiz": math.ceil(net / LEVHA_M2 - 1e-9)},
        "dis_duvar": {"tip": tanim["dis_duvar_tipi"], "karkas_mm": None if cizim else karkas_mm(tipler, tanim["dis_duvar_tipi"]),
                      "ic_yuz_cevre_m": ic_cevre, "ic_yuz_net_m2": ic_cevre * h - bosluklar},
    }


def osb_takviye_satiri(ot: dict, kisa: bool = False) -> str:
    """Planın altındaki bilgi satırı: OSB takviyesi gelen duvarlar ve net alan. `kisa`: paftadaki dar sütun için."""
    if kisa:
        return (f"OSB takviyesi (turuncu çizgi): dolap ve TV ünitesi duvarları, {len(ot['duvarlar'])} duvar, "
                f"{tr(sum(d['boy_cm'] for d in ot['duvarlar']) / 100, 2)} m · net {tr(ot['net_m2'])} m²")
    duvar = " + ".join(f"{d['duvar_adi']} {tr(d['boy_cm'] / 100, 2)} m" for d in ot["duvarlar"])
    return f"OSB takviyesi (turuncu çizgi; dolap ve TV ünitesi duvarları): {duvar} · net {tr(ot['net_m2'])} m²"


def kapi_ciz(ax, a: dict, tanim: dict, td: float, ti: float):
    """Kapı kanadı (açık konumda) ve açılım yayı."""
    W, H = tanim["kapali"]["en"], tanim["kapali"]["boy"]
    b, e, r = a["bas"], a["bas"] + a["en"], a["en"]
    mh = b if a.get("mentese", "bas") == "bas" else e
    dv, ac = a["duvar"], a.get("acilim", "ic")
    if dv.startswith("dis:"):
        yatay = dv in ("dis:alt", "dis:ust")
        if dv == "dis:alt":
            yuz, yon = td, 1
        elif dv == "dis:ust":
            yuz, yon = H - td, -1
        elif dv == "dis:sol":
            yuz, yon = td, 1
        else:
            yuz, yon = W - td, -1
        if ac != "ic":
            yuz, yon = (0 if yon == 1 else (H if yatay else W)), -yon
    else:
        d = next(x for x in tanim["ic_duvarlar"] if x["ad"] == dv)
        yatay = d["yon"] == "yatay"
        yon = 1 if ac in ("ust", "sag") else -1
        yuz = d["aks"] + yon * ti / 2
    if yatay:  # duvar x boyunca; kanat y yönünde açılır
        hx, hy = mh, yuz
        ax.plot([hx, hx], [hy, hy + yon * r], color="#8a4b2a", lw=1.2)
        kapali = 0 if mh == b else 180
        acik = 90 if yon == 1 else 270
    else:      # duvar y boyunca; kanat x yönünde açılır
        hx, hy = yuz, mh
        ax.plot([hx, hx + yon * r], [hy, hy], color="#8a4b2a", lw=1.2)
        kapali = 90 if mh == b else 270
        acik = 0 if yon == 1 else 180
    t1, t2 = sorted([kapali % 360, acik % 360])
    if t2 - t1 > 180:
        t1, t2 = t2, t1 + 360
    ax.add_patch(Arc((hx, hy), 2 * r, 2 * r, theta1=t1, theta2=t2, color="#8a4b2a", lw=0.8, ls=(0, (3, 2))))


def olcu(ax, p1, p2, metin, kaydir=0.0, yatay=True):
    (x1, y1), (x2, y2) = p1, p2
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="<->", color="#444", lw=0.7, shrinkA=0, shrinkB=0))
    if yatay:
        ax.text((x1 + x2) / 2, y1 + kaydir, metin, ha="center", va="bottom" if kaydir >= 0 else "top", fontsize=7.5, color="#222")
    else:
        ax.text(x1 + kaydir, (y1 + y2) / 2, metin, ha="right" if kaydir <= 0 else "left", va="center", fontsize=7.5, color="#222", rotation=90)


def plan_eksen(ax, tanim: dict, s: dict, cizim: bool = False, baslik: bool = True, bilgi: bool = True):
    """Planı verilen eksene çizer."""
    W, H = tanim["kapali"]["en"], tanim["kapali"]["boy"]
    td, ti = s["td"], s["ti"]
    v = tanim.get("veranda")
    renk = {"Yaşam Alanı": "#fdf1d6", "Hol": "#f3ead9", "Banyo": "#dcefee", "Yatak Odası 1": "#e3ebf7", "Yatak Odası 2": "#e3ebf7"}
    for m in s["mahaller"]:
        ax.add_patch(MplPolygon(list(m["poligon"].exterior.coords), closed=True, fc=renk.get(m["ad"], "#f2f2f2"), ec="none", zorder=1))
        c = m["poligon"].representative_point()
        ax.text(c.x, c.y + 14, m["ad"].upper(), ha="center", va="center", fontsize=9, weight="bold", zorder=6)
        ax.text(c.x, c.y - 14, f"{tr(m['alan_m2'])} m²", ha="center", va="center", fontsize=9, zorder=6)
    if v:
        ax.add_patch(MplPolygon([(v["x"], v["y"]), (v["x"] + v["en"], v["y"]), (v["x"] + v["en"], v["y"] + v["boy"]), (v["x"], v["y"] + v["boy"])],
                                closed=True, fc="#e9f2e0", ec="#7aa35c", hatch="///", lw=1.0, zorder=1))
        ax.text(v["x"] + v["en"] / 2, v["y"] + v["boy"] / 2 + 14, "VERANDA", ha="center", fontsize=9, weight="bold", zorder=6,
                bbox=dict(fc="white", ec="none", pad=1.5))
        ax.text(v["x"] + v["en"] / 2, v["y"] + v["boy"] / 2 - 14, f"{tr(s['veranda_m2'])} m²", ha="center", fontsize=9, zorder=6,
                bbox=dict(fc="white", ec="none", pad=1.5))
    vc = veranda_cercevesi(tanim)
    if vc:   # kirişler (üstte; kesik çizgi) ve dikmeler
        for (ax_, ay_), (bx_, by_) in vc["kirisler"]:
            ax.plot([ax_, bx_], [ay_, by_], color="#4d4d4d", lw=2.2, ls=(0, (4, 2)), zorder=4)
        for dk in vc["dikmeler"]:
            ax.add_patch(MplPolygon(list(dk.exterior.coords), closed=True, fc="#1f1f1f", ec="#1f1f1f", lw=0.8, zorder=5))
    delik = unary_union([aciklik_kutusu(a, tanim, td, ti) for a in tanim["acikliklar"]])
    for g, fc in ((s["dis_halka"].difference(delik), "#3a3a3a"), (s["ic_duvarlar"].difference(delik), "#6b6b6b")):
        for p in (g.geoms if hasattr(g, "geoms") else [g]):
            ax.add_patch(MplPolygon(list(p.exterior.coords), closed=True, fc=fc, ec="none", zorder=3))
    for a in tanim["acikliklar"]:
        k = aciklik_kutusu(a, tanim, td, ti)
        x1, y1, x2, y2 = k.bounds
        if a["tur"] == "pencere":
            ax.add_patch(MplPolygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)], closed=True, fc="#cfe6f7", ec="#2a78b8", lw=1.0, zorder=4))
            et = f"{a['en']}/{a['yuk']}"
            dv = a["duvar"]
            if dv == "dis:alt":
                ax.text((x1 + x2) / 2, -16, et, ha="center", va="top", fontsize=7.5, color="#1f5f93")
            elif dv == "dis:ust":
                ax.text((x1 + x2) / 2, H + 16, et, ha="center", va="bottom", fontsize=7.5, color="#1f5f93")
            elif dv == "dis:sag":
                ax.text(W + 16, (y1 + y2) / 2, et, ha="left", va="center", fontsize=7.5, color="#1f5f93", rotation=90,
                        bbox=dict(fc="white", ec="none", pad=0.8), zorder=7)
            else:
                ax.text(-16, (y1 + y2) / 2, et, ha="right", va="center", fontsize=7.5, color="#1f5f93", rotation=90)
        else:
            kapi_ciz(ax, a, tanim, td, ti)
    ot = s.get("osb_takviye")
    if ot:   # OSB takviyesi gelen duvar yüzleri (dolap ve TV ünitesi duvarları): odanın içinde, duvara paralel turuncu çizgi; boşluklarda kesilir
        for dv in ot["duvarlar"]:
            for (x0, y0), (x1, y1) in dv["parcalar"]:
                uz = math.hypot(x1 - x0, y1 - y0)
                nx, ny = -(y1 - y0) / uz, (x1 - x0) / uz          # oda, parçanın solundadır
                yatay_p = abs(y1 - y0) < 1e-6
                araliklar = [tuple(sorted((x0, x1) if yatay_p else (y0, y1)))]
                for b0, b1 in dv["bosluk_araliklari"]:
                    yeni = []
                    for c0, c1 in araliklar:
                        if b1 <= c0 or b0 >= c1:
                            yeni.append((c0, c1))
                            continue
                        if b0 > c0:
                            yeni.append((c0, b0))
                        if b1 < c1:
                            yeni.append((b1, c1))
                    araliklar = yeni
                for c0, c1 in araliklar:
                    if yatay_p:
                        ax.plot([c0, c1], [y0 + ny * 5] * 2, color="#e07b00", lw=3.0, solid_capstyle="butt", zorder=5)
                    else:
                        ax.plot([x0 + nx * 5] * 2, [c0, c1], color="#e07b00", lw=3.0, solid_capstyle="butt", zorder=5)
    # ölçü zincirleri: dış yüzler ve iç duvar aksları
    dusey = sorted(d["aks"] for d in tanim["ic_duvarlar"] if d["yon"] == "dusey")
    alt = [0.0] + [x for x in dusey if any(d["aks"] == x and d["bas"] == 0 for d in tanim["ic_duvarlar"])] + [W] + ([v["x"] + v["en"]] if v else [])
    ust = [0.0] + [x for x in dusey if any(d["aks"] == x and d["son"] == H for d in tanim["ic_duvarlar"])] + [W] + ([v["x"] + v["en"]] if v else [])
    for i in range(len(alt) - 1):
        olcu(ax, (alt[i], -84), (alt[i + 1], -84), tr(alt[i + 1] - alt[i]).replace(",0", ""), 3)
    olcu(ax, (0, -122), (alt[-1], -122), tr(alt[-1]).replace(",0", ""), 3)
    for i in range(len(ust) - 1):
        olcu(ax, (ust[i], H + 62), (ust[i + 1], H + 62), tr(ust[i + 1] - ust[i]).replace(",0", ""), 3)
    yatay_sol = [0.0] + sorted(d["aks"] for d in tanim["ic_duvarlar"] if d["yon"] == "yatay" and d["bas"] == 0) + [H]
    for i in range(len(yatay_sol) - 1):
        olcu(ax, (-62, yatay_sol[i]), (-62, yatay_sol[i + 1]), tr(yatay_sol[i + 1] - yatay_sol[i]).replace(",0", ""), -4, yatay=False)
    olcu(ax, (-100, 0), (-100, H), tr(H).replace(",0", ""), -4, yatay=False)
    sag = alt[-1]
    b = s["boardex"]
    bas = f"{tanim['kod']} · {tanim['ad']} · paket: {tanim['paket']}"
    if baslik:
        ax.set_title(bas + ("\nKARŞILAŞTIRMA: arşiv çiziminin duvar kalınlıklarıyla" if cizim else "\nTASLAK · çizim kurallarından yeniden kuruldu · üretim projesi değildir"),
                     fontsize=11, weight="bold", loc="left")
    satirlar = [
        f"Dış ölçü (veranda dahil): {tr(sag).replace(',0', '')} × {H} cm = {tr(s['toplam_oturum_m2'])} m²",
        f"Kapalı kısım: {W} × {H} cm · brüt {tr(s['kapali_brut_m2'], 2)} m² · net {tr(s['kapali_net_m2'])} m²",
        f"Duvar: dış {tr(td)} cm ({tanim['dis_duvar_tipi']}) · iç {tr(ti)} cm ({tanim['ic_duvar_tipi']}) · yükseklik {tanim['duvar_yuksekligi']} cm",
        f"Dış Boardex: {tr(b['cevre_m'])} m × {tr(b['yukseklik_m'], 2)} m − {tr(b['bosluk_m2'])} m² boşluk = {tr(b['net_m2'])} m² "
        f"(fire hariç {b['levha_adedi_firesiz']} levha)",
        "Ölçü zinciri: dış yüzler ve iç duvar aksları · ölçüler cm",
    ]
    if vc:
        satirlar.insert(3, f"Veranda çerçevesi: sırt {vc['sirt']} cm, genişlik {vc['genislik']} cm · kiriş {tr(vc['kiris_boyu'] / 100, 2)} m (kesik çizgi) · "
                           f"dikme {vc['dikme_adedi']} adet, {vc['dikme_boyu']} cm")
    if ot:
        satirlar.insert(-1, osb_takviye_satiri(ot))
    if bilgi:
        ax.text(0, -172, "\n".join(satirlar), ha="left", va="top", fontsize=8.5, linespacing=1.5)
    ax.annotate("GİRİŞ", xy=(433, -4), xytext=(433, -40), ha="center", fontsize=8, color="#b03030",
                arrowprops=dict(arrowstyle="->", color="#b03030", lw=1.0))
    ax.set_xlim(-140, sag + 60)
    ax.set_ylim(-312 if bilgi else -150, H + 100)
    ax.set_aspect("equal")
    ax.axis("off")


def plan_ciz(tanim: dict, tipler: dict, s: dict, cikti: Path, cizim: bool):
    fig, ax = plt.subplots(figsize=(13.5, 9.2), dpi=150)
    plan_eksen(ax, tanim, s, cizim)
    fig.savefig(cikti, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tanim", type=Path)
    ap.add_argument("--cizim-kalinligi", action="store_true")
    ap.add_argument("--secenek", type=Path, action="append", default=[], help="seçenek dosyası (yinelenebilir)")
    ap.add_argument("--cikti", type=Path, default=BURADA / "cikti")
    a = ap.parse_args()
    if a.cizim_kalinligi and a.secenek:
        raise SystemExit("--cizim-kalinligi arşiv çizimiyle karşılaştırma içindir; seçenekle birlikte kullanılmaz.")
    tanim = json.loads(a.tanim.read_text(encoding="utf-8"))
    tanim, sek = secenek_uygula(tanim, a.secenek)
    tipler = json.loads((BURADA / "duvar_tipleri.json").read_text(encoding="utf-8"))
    s = hesapla(tanim, tipler, a.cizim_kalinligi)
    a.cikti.mkdir(parents=True, exist_ok=True)
    ek = "_cizim_kalinligi" if a.cizim_kalinligi else ""
    kod = tanim["kod"].replace("Ç", "C") + sek
    plan_ciz(tanim, tipler, s, a.cikti / f"{kod}_plan{ek}.png", a.cizim_kalinligi)
    etiket = tanim.get("cizim_etiketleri_m2", {})
    satir, fark_var = [], False
    for m in s["mahaller"]:
        e = etiket.get(m["ad"])
        f = None if e is None else m["alan_m2"] - e
        if a.cizim_kalinligi and f is not None and abs(f) > ETIKET_TOL:
            fark_var = True
        satir.append({"mahal": m["ad"], "alan_m2": round(m["alan_m2"], 3), "cizim_etiketi_m2": e, "fark_m2": None if f is None else round(f, 3),
                      "cevre_m": round(m["cevre_m"], 3), "ic_kose": m["ic_kose"], "dis_kose": m["dis_kose"], "islev": m["islev"]})
    rapor = {
        "kod": tanim["kod"], "mod": "cizim_kalinligi" if a.cizim_kalinligi else "katmanlardan",
        "paket": tanim["paket"], "secenekler": tanim["secenekler"],
        "duvar_cm": {"dis": s["td"], "ic": s["ti"]}, "dis_duvar_tipi": tanim["dis_duvar_tipi"], "ic_duvar_tipi": tanim["ic_duvar_tipi"], "mahaller": satir,
        "kapali_net_m2": round(s["kapali_net_m2"], 3), "kapali_brut_m2": round(s["kapali_brut_m2"], 3),
        "veranda_m2": round(s["veranda_m2"], 3), "toplam_oturum_m2": round(s["toplam_oturum_m2"], 3),
        "boardex": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in s["boardex"].items()},
        "dis_duvar": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in s["dis_duvar"].items()},
    }
    if s["osb_takviye"] and not a.cizim_kalinligi:
        o = s["osb_takviye"]
        rapor["osb_takviye"] = {"duvarlar": [{"mahal": d["mahal"], "duvar": d["duvar"], "duvar_adi": d["duvar_adi"], "neden": d["neden"], "boy_cm": round(d["boy_cm"], 2),
                                              "bosluk_m2": round(d["bosluk_m2"], 3)} for d in o["duvarlar"]],
                                "brut_m2": round(o["brut_m2"], 3), "bosluk_m2": round(o["bosluk_m2"], 3), "net_m2": round(o["net_m2"], 3)}
    (a.cikti / f"{kod}_rapor{ek}.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{tanim['kod']} · paket {tanim['paket']} · duvar dış {tr(s['td'])} ({tanim['dis_duvar_tipi']}) / iç {tr(s['ti'])} ({tanim['ic_duvar_tipi']}) cm")
    for r in satir:
        print(f"  {r['mahal']:15s} {tr(r['alan_m2'], 2):>6s} m²   çizim etiketi {r['cizim_etiketi_m2']}   fark {r['fark_m2']:+.2f}")
    print(f"  kapalı net {tr(s['kapali_net_m2'], 2)} · brüt {tr(s['kapali_brut_m2'], 2)} · veranda {tr(s['veranda_m2'], 2)} · toplam {tr(s['toplam_oturum_m2'], 2)} m²")
    b = s["boardex"]
    print(f"  Boardex: {tr(b['brut_m2'])} − {tr(b['bosluk_m2'], 2)} = {tr(b['net_m2'], 2)} m² → {b['levha_adedi_firesiz']} levha (fire hariç)")
    if a.cizim_kalinligi:
        print("  ÇİZİMLE KARŞILAŞTIRMA:", "FARK VAR" if fark_var else "AYNI (bütün mahaller etiketle tutuyor)")
    return 1 if fark_var else 0


if __name__ == "__main__":
    sys.exit(main())
