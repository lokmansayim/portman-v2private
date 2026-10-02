#!/usr/bin/env python3
"""Çelik (A1) deneme çizicisi: Yapı Tanımı taslağından plan, alanlar ve Boardex metrajı.

Deneme kodudur; canlıda değildir ve Motor'un yerine geçmez.
Duvar kalınlığı duvar tipinin katmanlarından hesaplanır (duvar_tipleri.json).
`--cizim-kalinligi` ile arşivdeki çizimin kalınlıkları (12 / 11 cm) kullanılır ve
hesaplanan mahal alanları çizimdeki etiketlerle karşılaştırılır (okuma denetimi).

Kullanım:
    python ciz.py C8201.json                    # katmanlardan: plan + rapor
    python ciz.py C8201.json --cizim-kalinligi  # çizimle karşılaştırma; fark varsa çıkış kodu 1
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


def kalinliklar(tipler: dict, tanim: dict, cizim: bool) -> tuple[float, float]:
    if cizim:
        k = tipler["cizim_kalinliklari_kayit"]
        return float(k["dis_cm"]), float(k["ic_cm"])

    def toplam(ad: str) -> float:
        return sum(k["kalinlik"] for k in tipler["tipler"][ad]["katmanlar"]) / 10.0

    return toplam(tanim["dis_duvar_tipi"]), toplam(tanim["ic_duvar_tipi"])


def ic_duvar_kutusu(d: dict, ti: float):
    if d["yon"] == "dusey":
        return box(d["aks"] - ti / 2, d["bas"], d["aks"] + ti / 2, d["son"])
    return box(d["bas"], d["aks"] - ti / 2, d["son"], d["aks"] + ti / 2)


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


def hesapla(tanim: dict, tipler: dict, cizim: bool) -> dict:
    W, H = tanim["kapali"]["en"], tanim["kapali"]["boy"]
    td, ti = kalinliklar(tipler, tanim, cizim)
    ic_kutu = box(td, td, W - td, H - td)
    dis_halka = box(0, 0, W, H).difference(ic_kutu)
    ic = unary_union([ic_duvar_kutusu(d, ti) for d in tanim["ic_duvarlar"]]).intersection(ic_kutu)
    bosluk = ic_kutu.difference(ic)
    parcalar = list(bosluk.geoms) if hasattr(bosluk, "geoms") else [bosluk]
    mahaller = []
    for m in tanim["mahaller"]:
        p = next((g for g in parcalar if g.contains(Point(*m["nokta"]))), None)
        if p is None:
            raise SystemExit(f"Mahal bulunamadı: {m['ad']}")
        mahaller.append({"ad": m["ad"], "poligon": p, "alan_m2": p.area / 1e4})
    if len(parcalar) != len(mahaller):
        raise SystemExit(f"Kapalı kısım {len(parcalar)} parçaya bölündü, {len(mahaller)} mahal tanımlı.")
    v = tanim.get("veranda")
    veranda_m2 = v["en"] * v["boy"] / 1e4 if v else 0.0
    # Boardex: dış duvarların tüm çevre uzunluğu × yükseklik − kapı ve pencere boşlukları (Lokman, 2 Ekim)
    h = tanim["duvar_yuksekligi"] / 100.0
    cevre = 2 * (W + H) / 100.0
    bosluklar = sum(a["en"] * a["yuk"] / 1e4 for a in tanim["acikliklar"] if a["duvar"].startswith("dis:"))
    net = cevre * h - bosluklar
    return {
        "td": td, "ti": ti, "dis_halka": dis_halka, "ic_duvarlar": ic, "mahaller": mahaller,
        "kapali_brut_m2": W * H / 1e4, "kapali_net_m2": sum(m["alan_m2"] for m in mahaller),
        "veranda_m2": veranda_m2, "toplam_oturum_m2": W * H / 1e4 + veranda_m2,
        "boardex": {"cevre_m": cevre, "yukseklik_m": h, "brut_m2": cevre * h, "bosluk_m2": bosluklar,
                    "net_m2": net, "levha_adedi_firesiz": math.ceil(net / LEVHA_M2 - 1e-9)},
    }


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


def plan_ciz(tanim: dict, tipler: dict, s: dict, cikti: Path, cizim: bool):
    W, H = tanim["kapali"]["en"], tanim["kapali"]["boy"]
    td, ti = s["td"], s["ti"]
    v = tanim.get("veranda")
    fig, ax = plt.subplots(figsize=(13.5, 9.2), dpi=150)
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
    baslik = f"{tanim['kod']} · {tanim['ad']} · paket: {tanim['paket']}"
    ax.set_title(baslik + ("\nKARŞILAŞTIRMA: arşiv çiziminin duvar kalınlıklarıyla" if cizim else "\nTASLAK · çizim kurallarından yeniden kuruldu · üretim projesi değildir"),
                 fontsize=11, weight="bold", loc="left")
    satirlar = [
        f"Dış ölçü (veranda dahil): {tr(sag).replace(',0', '')} × {H} cm = {tr(s['toplam_oturum_m2'])} m²",
        f"Kapalı kısım: {W} × {H} cm · brüt {tr(s['kapali_brut_m2'], 2)} m² · net {tr(s['kapali_net_m2'])} m²",
        f"Duvar: dış {tr(td)} cm ({tanim['dis_duvar_tipi']}) · iç {tr(ti)} cm ({tanim['ic_duvar_tipi']}) · yükseklik {tanim['duvar_yuksekligi']} cm",
        f"Dış Boardex: {tr(b['cevre_m'])} m × {tr(b['yukseklik_m'], 2)} m − {tr(b['bosluk_m2'])} m² boşluk = {tr(b['net_m2'])} m² "
        f"(fire hariç {b['levha_adedi_firesiz']} levha)",
        "Ölçü zinciri: dış yüzler ve iç duvar aksları · ölçüler cm",
    ]
    ax.text(0, -172, "\n".join(satirlar), ha="left", va="top", fontsize=8.5, linespacing=1.5)
    ax.annotate("GİRİŞ", xy=(433, -4), xytext=(433, -40), ha="center", fontsize=8, color="#b03030",
                arrowprops=dict(arrowstyle="->", color="#b03030", lw=1.0))
    ax.set_xlim(-140, sag + 60)
    ax.set_ylim(-312, H + 100)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(cikti, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tanim", type=Path)
    ap.add_argument("--cizim-kalinligi", action="store_true")
    ap.add_argument("--cikti", type=Path, default=BURADA / "cikti")
    a = ap.parse_args()
    tanim = json.loads(a.tanim.read_text(encoding="utf-8"))
    tipler = json.loads((BURADA / "duvar_tipleri.json").read_text(encoding="utf-8"))
    s = hesapla(tanim, tipler, a.cizim_kalinligi)
    a.cikti.mkdir(parents=True, exist_ok=True)
    ek = "_cizim_kalinligi" if a.cizim_kalinligi else ""
    kod = tanim["kod"].replace("Ç", "C")
    plan_ciz(tanim, tipler, s, a.cikti / f"{kod}_plan{ek}.png", a.cizim_kalinligi)
    etiket = tanim.get("cizim_etiketleri_m2", {})
    satir, fark_var = [], False
    for m in s["mahaller"]:
        e = etiket.get(m["ad"])
        f = None if e is None else m["alan_m2"] - e
        if a.cizim_kalinligi and f is not None and abs(f) > ETIKET_TOL:
            fark_var = True
        satir.append({"mahal": m["ad"], "alan_m2": round(m["alan_m2"], 3), "cizim_etiketi_m2": e, "fark_m2": None if f is None else round(f, 3)})
    rapor = {
        "kod": tanim["kod"], "mod": "cizim_kalinligi" if a.cizim_kalinligi else "katmanlardan",
        "duvar_cm": {"dis": s["td"], "ic": s["ti"]}, "mahaller": satir,
        "kapali_net_m2": round(s["kapali_net_m2"], 3), "kapali_brut_m2": round(s["kapali_brut_m2"], 3),
        "veranda_m2": round(s["veranda_m2"], 3), "toplam_oturum_m2": round(s["toplam_oturum_m2"], 3),
        "boardex": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in s["boardex"].items()},
    }
    (a.cikti / f"{kod}_rapor{ek}.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{tanim['kod']} · duvar dış {tr(s['td'])} / iç {tr(s['ti'])} cm")
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
