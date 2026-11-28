#!/usr/bin/env python3
"""Çelik karkas iskelet çizimi (İE-47): kafes kolon + kafes makas çerçeveleri, yan görünüş, kolon planı.

Girdi çerçeve tanımıdır (`portman.celik_cerceve/0.1`, ör. `modeller/cerceve/CD4525_cerceve.json`); Yapı Tanımı'na ve genel motorun
öteki çıktılarına dokunmaz. Kural (Lokman, 28 Kasım 2026; kaynak satırları tanımda):

1. **Akslar.** x aksları tanımda yazılı; iki aks arası en çok `makas.aciklik_en_cok_cm` (makas bu açıklığı geçer). y yönünde
   `y_aks_sayisi` aks, dış ölçü eşit bölünür (25 m'de 3 × 833,3; "25 metrelik tarafa da aynı standart").
2. **Kafes kolon.** Dış ölçünün ucundaki aksta `kolon.uc_cm` genişlikte, aks dış yüzde, kolon içeride; ara aksta `kolon.ara_cm`
   genişlikte, aksa ortalı (60 sol + 60 sağ). Her aks kesişiminde bir kolon; plandaki kesiti iki yöndeki genişliklerden. Örgü iki dikme
   arasında zikzak, adım kolon genişliği (45°) ve her adımda yatay.
3. **Kafes makas.** Her x açıklığında bir beşik makas, eğim `makas.egim`; alt başlık kolon tepesinde. Üyeler depodaki makas üretim kodundan
   (`araclar.uretim.makas.besik`; 90 m² evin onaylı kalıbı): alt başlık boyu aks arası, mesnet (SL düşeyi) kolonun iç yüzünde.
4. Profil kesitleri, örgü aralığı ve bağlantılar mühendis hesabıdır: çizim TASLAK'tır, üretim projesi değildir.

    python -m motor.genel.celik_cerceve modeller/cerceve/CD4525_cerceve.json <çıktı klasörü>

Çıktılar: `<kod>_iskelet.png`, `<kod>_iskelet.pdf`, `<kod>_iskelet.dxf` (katmanlar KOLON, MAKAS, AKS, OLCU, YAZI; cm) ve
`<kod>_iskelet.json` (akslar, kolonlar, makaslar, çubuk sayıları). Hesapta LLM yoktur; aynı tanım aynı çizimi verir.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from araclar.uretim import makas as uretim_makas  # noqa: E402
from .toplam import sum  # noqa: E402,A004

SEMA = "portman.celik_cerceve/0.1"


class CerceveHatasi(ValueError):
    pass


def _r(v: float) -> float:
    return round(v, 2)


def kur(t: dict) -> dict:
    """Tanımdan akslar, kolonlar ve makaslar (cm). Hesap yalnız burada; çizim bunu okur."""
    if t.get("sema") != SEMA:
        raise CerceveHatasi(f"şema {SEMA} değil: {t.get('sema')}")
    W, D, H = t["dis_olcu"]["x"], t["dis_olcu"]["y"], t["kolon_yuksekligi"]
    xa = [float(a) for a in t["x_akslari"]]
    if xa[0] != 0 or xa[-1] != W or any(b <= a for a, b in zip(xa, xa[1:])):
        raise CerceveHatasi("x aksları 0'dan dış ölçüye artan sırada olmalı")
    en_cok = t["makas"]["aciklik_en_cok_cm"]
    if any(b - a > en_cok + 1e-6 for a, b in zip(xa, xa[1:])):
        raise CerceveHatasi(f"x açıklığı {en_cok} cm'yi aşıyor: makas geçmez")
    n = t["y_aks_sayisi"]
    ya = [D * i / (n - 1) for i in range(n)]
    if D / (n - 1) > en_cok + 1e-6:
        raise CerceveHatasi(f"y açıklığı {D / (n - 1):.1f} cm, {en_cok} cm'yi aşıyor")
    uc, ara = t["kolon"]["uc_cm"], t["kolon"]["ara_cm"]

    def aralik(a, L):
        if a == 0:
            return (0.0, float(uc))
        if a == L:
            return (L - uc, float(L))
        return (a - ara / 2, a + ara / 2)

    kolonlar = []
    for j, b in enumerate(ya):
        for i, a in enumerate(xa):
            x0, x1 = aralik(a, W)
            y0, y1 = aralik(b, D)
            kolonlar.append({"ad": f"K{j + 1}{i + 1:02d}", "aks": [_r(a), _r(b)], "x": [_r(x0), _r(x1)], "y": [_r(y0), _r(y1)]})
    egim = t["makas"]["egim"]
    makaslar = []
    for i, (a, b) in enumerate(zip(xa, xa[1:])):
        sol, sag = aralik(a, W)[1], aralik(b, W)[0]
        mesnet = _r(sol - a)
        if abs((b - sag) - mesnet) > 1e-6:
            raise CerceveHatasi(f"açıklık {i + 1}: iki mesnet aksa eşit uzaklıkta değil")
        cub, bilgi = uretim_makas.besik((b - a) * 10, egim, topuk=t["makas"]["topuk_mm"], sacak=mesnet * 10)
        makaslar.append({"ad": f"M{i + 1:02d}", "aks": [_r(a), _r(b)], "mesnet_cm": mesnet, "egim": egim,
                         "tepe_cm": _r(H + egim * (b - a) / 2), "cubuk": len(cub), "panel": bilgi["panel"],
                         "cubuklar": [{k: (round(v, 1) if isinstance(v, float) else v) for k, v in c.items()} for c in cub]})
    sacak = float(t.get("sacak_cm", 0))
    for m, yon, uc in ((makaslar[0], -1, xa[0]), (makaslar[-1], 1, xa[-1])):
        if sacak <= 0:
            break
        pd = next(c for c in m["cubuklar"] if c["ad"] == "PD")          # sol üst başlık (yerel mm)
        y_uc = pd["y1"] + egim * (0 - pd["x1"])                          # üst başlık ekseni dış uçta (yerel x = 0)
        m.setdefault("sacak", []).append({"yon": yon, "uc_cm": _r(uc), "boy_cm": sacak,
                                          "ust_cm": _r(H + y_uc / 10), "uc_ust_cm": _r(H + (y_uc - egim * sacak * 10) / 10)})
    return {"kod": t["kod"], "dis_olcu": [W, D], "kolon_yuksekligi": H, "x_akslari": [_r(a) for a in xa],
            "y_akslari": [_r(b) for b in ya], "kolonlar": kolonlar, "makaslar": makaslar, "sacak_cm": sacak,
            "ozet": {"kolon": len(kolonlar), "makas_cercevesi": len(makaslar), "cerceve_hatti": len(ya),
                     "makas_toplam": len(makaslar) * len(ya), "mahya_kotu_cm": max(m["tepe_cm"] for m in makaslar)}}


def _kafes(dikme0, dikme1, h, adim):
    """Kafes kolonun çizgileri (yatay koordinat, düşey koordinat) çiftleri."""
    cizgi = [((dikme0, 0), (dikme0, h)), ((dikme1, 0), (dikme1, h)), ((dikme0, 0), (dikme1, 0))]
    y, s = 0.0, 0
    while y < h - 1e-6:
        y2 = min(y + adim, h)
        cizgi.append(((dikme0, y), (dikme1, y2)) if s == 0 else ((dikme1, y), (dikme0, y2)))
        cizgi.append(((dikme0, y2), (dikme1, y2)))
        y, s = y2, s ^ 1
    return cizgi


def _makas_cizgileri(m, H):
    a = m["aks"][0]
    cizgi = [((a + c["x1"] / 10, H + c["y1"] / 10), (a + c["x2"] / 10, H + c["y2"] / 10)) for c in m["cubuklar"]]
    for s in m.get("sacak", []):                     # saçak payı: üst başlık dış uçtan saçak boyunca uzar, uçta düşey kapama
        x0, x1 = s["uc_cm"], s["uc_cm"] + s["yon"] * s["boy_cm"]
        cizgi.append(((x0, s["ust_cm"]), (x1, s["uc_ust_cm"])))
        cizgi.append(((x1, s["uc_ust_cm"]), (x1, min(s["uc_ust_cm"], H))))
    return cizgi


def cizim_ogeleri(k: dict) -> dict:
    """Üç görünüşün çizgileri ve dikdörtgenleri (cm); PNG/PDF ve DXF aynı listeden çizer."""
    W, D = k["dis_olcu"]
    H = k["kolon_yuksekligi"]
    on = {"kolon": [], "makas": []}
    ilk_sira = [c for c in k["kolonlar"] if c["aks"][1] == k["y_akslari"][0]]
    for c in ilk_sira:
        x0, x1 = c["x"]
        on["kolon"] += _kafes(x0, x1, H, x1 - x0)
    for m in k["makaslar"]:
        on["makas"] += _makas_cizgileri(m, H)
    yan = {"kolon": [], "makas": []}
    ilk_sutun = [c for c in k["kolonlar"] if c["aks"][0] == k["x_akslari"][0]]
    for c in ilk_sutun:
        y0, y1 = c["y"]
        yan["kolon"] += _kafes(y0, y1, H, y1 - y0)
    sc = k["sacak_cm"]                               # kalkan saçağı: aşık ve mahya iki uçta saçak kadar dışarı
    yan["makas"] = [((0, H), (D, H)), ((-sc, k["ozet"]["mahya_kotu_cm"]), (D + sc, k["ozet"]["mahya_kotu_cm"]))]
    plan = [(c["x"][0], c["y"][0], c["x"][1] - c["x"][0], c["y"][1] - c["y"][0], c["ad"]) for c in k["kolonlar"]]
    return {"on": on, "yan": yan, "plan": plan}


def _png_pdf(k, og, t, cikti: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    W, D = k["dis_olcu"]
    H = k["kolon_yuksekligi"]
    tepe = k["ozet"]["mahya_kotu_cm"]
    KOL, MAK = "#1f4e79", "#b03a2e"
    fig = plt.figure(figsize=(16.54, 11.69))
    fig.text(0.03, 0.965, f"{k['kod']} · ÇELİK KARKAS İSKELET ÇİZİMİ   —   TASLAK · profil, örgü ve bağlantı mühendis hesabından · "
             "üretim projesi değildir", fontsize=12, weight="bold")
    fig.text(0.03, 0.945, f"{t['ad']}. Ölçüler cm. Kolon {k['ozet']['kolon']} · makas çerçevesi {k['ozet']['makas_cercevesi']} "
             f"× {k['ozet']['cerceve_hatti']} hat = {k['ozet']['makas_toplam']} makas · mahya kotu {tepe:.1f}", fontsize=9)

    def cizgiler(ax, liste, renk, lw):
        for (p, q) in liste:
            ax.plot([p[0], q[0]], [p[1], q[1]], color=renk, lw=lw, solid_capstyle="butt")

    def olcu(ax, a, b, y, yazi):
        ax.annotate("", (a, y), (b, y), arrowprops=dict(arrowstyle="<->", lw=0.6))
        ax.text((a + b) / 2, y + 12, yazi, ha="center", fontsize=8)

    ax = fig.add_axes([0.03, 0.54, 0.94, 0.37])
    ax.set_title("1 · ÇERÇEVE GÖRÜNÜŞÜ (önden)", fontsize=10, loc="left")
    cizgiler(ax, og["on"]["kolon"], KOL, 0.6)
    cizgiler(ax, og["on"]["makas"], MAK, 0.5)
    xa = k["x_akslari"]
    for c in [c for c in k["kolonlar"] if c["aks"][1] == k["y_akslari"][0]]:
        ax.text(sum(c["x"]) / 2, -35, f"{c['x'][1] - c['x'][0]:g}", ha="center", fontsize=8, color=KOL)
    for a, b in zip(xa, xa[1:]):
        olcu(ax, a, b, -95, f"{b - a:g}")
    olcu(ax, 0, W, -165, f"{W:g}")
    sc = k["sacak_cm"]
    if sc:
        olcu(ax, -sc, 0, H + 60, f"{sc:g}")
        olcu(ax, W, W + sc, H + 60, f"{sc:g}")
    ax.annotate("", (W + 70, 0), (W + 70, H), arrowprops=dict(arrowstyle="<->", lw=0.6))
    ax.text(W + 85, H / 2, f"{H:g}", rotation=90, va="center", fontsize=8)
    ax.annotate("", (W + 70, H), (W + 70, tepe), arrowprops=dict(arrowstyle="<->", lw=0.6))
    ax.text(W + 85, (H + tepe) / 2, f"{tepe - H:.1f}", rotation=90, va="center", fontsize=8)
    ax.set_aspect("equal")
    ax.set_xlim(-80, W + 140)
    ax.set_ylim(-200, tepe + 40)
    ax.axis("off")

    ax = fig.add_axes([0.03, 0.08, 0.52, 0.40])
    ax.set_title("2 · YAN GÖRÜNÜŞ (çerçeve hattı boyunca)", fontsize=10, loc="left")
    cizgiler(ax, og["yan"]["kolon"], KOL, 0.6)
    cizgiler(ax, og["yan"]["makas"][:1], MAK, 1.2)
    p, q = og["yan"]["makas"][1]
    ax.plot([p[0], q[0]], [p[1], q[1]], color=MAK, lw=0.8, ls="--")
    ax.text(D / 2, tepe + 12, "mahya (makas tepesi)", ha="center", fontsize=8, color=MAK)
    ya = k["y_akslari"]
    for c in [c for c in k["kolonlar"] if c["aks"][0] == xa[0]]:
        ax.text(sum(c["y"]) / 2, -35, f"{c['y'][1] - c['y'][0]:g}", ha="center", fontsize=8, color=KOL)
    for a, b in zip(ya, ya[1:]):
        olcu(ax, a, b, -95, f"{b - a:.1f}")
    olcu(ax, 0, D, -165, f"{D:g}")
    if sc:
        olcu(ax, -sc, 0, tepe + 30, f"{sc:g}")
        olcu(ax, D, D + sc, tepe + 30, f"{sc:g}")
    ax.set_aspect("equal")
    ax.set_xlim(-60, D + 60)
    ax.set_ylim(-200, tepe + 60)
    ax.axis("off")

    ax = fig.add_axes([0.58, 0.08, 0.39, 0.40])
    ax.set_title(f"3 · KOLON PLANI · {k['ozet']['kolon']} kafes kolon", fontsize=10, loc="left")
    ax.add_patch(Rectangle((0, 0), W, D, fill=False, ec="k", lw=0.8))
    for a in xa:
        ax.plot([a, a], [-60, D + 60], color="#999", lw=0.4, ls="--")
    for b in ya:
        ax.plot([-60, W + 60], [b, b], color="#999", lw=0.4, ls="--")
    for (x, y, w, h, ad) in og["plan"]:
        ax.add_patch(Rectangle((x, y), w, h, fc=KOL, ec=KOL))
    ax.text(W / 2, -150, "ÖN", ha="center", fontsize=8)
    ax.text(W / 2, D + 90, "ARKA", ha="center", fontsize=8)
    ax.set_aspect("equal")
    ax.set_xlim(-200, W + 200)
    ax.set_ylim(-220, D + 180)
    ax.axis("off")
    fig.text(0.03, 0.015, "\n".join("• " + s for s in t.get("bilinen_sinirlar", [])), fontsize=7, va="bottom")
    fig.savefig(cikti / f"{_dosya(k)}_iskelet.png", dpi=130)
    fig.savefig(cikti / f"{_dosya(k)}_iskelet.pdf")
    plt.close(fig)


def _dxf(k, og, cikti: Path):
    import ezdxf

    doc = ezdxf.new("R2018", setup=True)
    doc.header["$INSUNITS"] = 5  # cm
    for ad, renk in (("KOLON", 5), ("MAKAS", 1), ("AKS", 8), ("YAZI", 7)):
        doc.layers.add(ad, color=renk)
    msp = doc.modelspace()
    W, D = k["dis_olcu"]
    tepe = k["ozet"]["mahya_kotu_cm"]
    dy_yan = -(tepe + 600)
    dy_plan = dy_yan - (tepe + 600) - D
    for ad, liste in (("KOLON", og["on"]["kolon"]), ("MAKAS", og["on"]["makas"])):
        for p, q in liste:
            msp.add_line(p, q, dxfattribs={"layer": ad})
    for ad, liste in (("KOLON", og["yan"]["kolon"]), ("MAKAS", og["yan"]["makas"])):
        for p, q in liste:
            msp.add_line((p[0], p[1] + dy_yan), (q[0], q[1] + dy_yan), dxfattribs={"layer": ad})
    msp.add_lwpolyline([(0, dy_plan), (W, dy_plan), (W, dy_plan + D), (0, dy_plan + D)], close=True, dxfattribs={"layer": "AKS"})
    for (x, y, w, h, ad) in og["plan"]:
        msp.add_lwpolyline([(x, y + dy_plan), (x + w, y + dy_plan), (x + w, y + h + dy_plan), (x, y + h + dy_plan)], close=True,
                           dxfattribs={"layer": "KOLON"})
    msp.add_text(f"{k['kod']} ISKELET - TASLAK", dxfattribs={"layer": "YAZI", "height": 40}).set_placement((0, tepe + 80))
    yol = cikti / f"{_dosya(k)}_iskelet.dxf"
    doc.saveas(yol)
    ezdxf.readfile(yol)  # yeniden açılır (K23)


def _dosya(k):
    return k["kod"].replace("-", "")


def uret(tanim_yolu: Path, cikti: Path) -> dict:
    t = json.loads(Path(tanim_yolu).read_text(encoding="utf-8"))
    k = kur(t)
    og = cizim_ogeleri(k)
    cikti.mkdir(parents=True, exist_ok=True)
    _png_pdf(k, og, t, cikti)
    _dxf(k, og, cikti)
    (cikti / f"{_dosya(k)}_iskelet.json").write_text(json.dumps(k, ensure_ascii=False, indent=1), encoding="utf-8")
    return k


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__)
        return 2
    k = uret(Path(argv[0]), Path(argv[1]))
    o = k["ozet"]
    print(f"{k['kod']}: kolon {o['kolon']} · makas {o['makas_cercevesi']} × {o['cerceve_hatti']} = {o['makas_toplam']} · "
          f"mahya {o['mahya_kotu_cm']:.1f} cm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
