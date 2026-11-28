"""Etiketli plan (çizim okuma ikinci döngüsü; Lokman, kart 28 Kasım 2026 05:55:38 UTC "Doğru, böyle kodla").

Bayiye giden plan görselinin yanında ayrı bir görsel: her dış duvar pano ekinde aks (üstte harf, solda rakam), odalar O1, O2 …,
pencereler P1 …, kapılar K1 …. Bayi düzeltmeyi bu adlarla yazar ya da görselin üstüne telefon kalemiyle çizer; kod adları komuta çevirir.
Mühürlü ön onay çizimi (M-02, `motor/dxf_out.py`, `motor/bayi_gorseli.py`) değişmez; bu görsel ondan ayrıdır.

Adlar planın kendisinden ve her seferinde aynı sırayla çıkar (kod verir): akslar soldan sağa ve arkadan öne; odalar ve açıklıklar arkadan
öne, soldan sağa. Görselde arka üstte, ön (giriş) altta.

Kullanım: python -m beyin.etiketli_plan <İş Emri.json> <çıktı.png>
"""
from __future__ import annotations

import copy
import json
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

AKS_BIRLESIK_CM = 40.0                  # bu kadar yakın iki ek tek aks sayılır (görselde üst üste binmesin)


def _harf(i: int) -> str:
    h = string.ascii_uppercase
    return h[i] if i < len(h) else h[i // len(h) - 1] + h[i % len(h)]


def _ekler(plan, yon: str) -> list[float]:
    vs = sorted({round(v, 2) for pn in plan.panolar if pn.duvar.yon == yon and pn.duvar.tur == "dis" for v in (pn.a0, pn.a1)})
    out: list[float] = []
    for v in vs:
        if not out or v - out[-1] > AKS_BIRLESIK_CM:
            out.append(v)
    return out


def etiketler(plan) -> dict:
    """Motor'un `Plan`'ı → {aks_x: [{ad, cm}], aks_y: [{ad, cm}], odalar: [{etiket, ad, alan_m2}], acikliklar: [{etiket, tur, mahal,
    olcu, x, y}]}. Plan çerçevesinde y önden arkaya büyür; aks 1 arka duvardır."""
    aks_x = [{"ad": _harf(i), "cm": x} for i, x in enumerate(_ekler(plan, "x"))]
    aks_y = [{"ad": str(j + 1), "cm": y} for j, y in enumerate(sorted(_ekler(plan, "y"), reverse=True))]
    oda = []
    for m in plan.mahaller.values():
        if m.poly is None:
            continue
        c = m.poly.representative_point()
        b = m.poly.bounds                # sıra: üst kenarı arkada olan önce, aynı sırada soldan (okuma yönü)
        oda.append((-round(b[3], 1), round(b[0], 1), round(c.x, 1), round(c.y, 1), m))
    odalar = [{"etiket": f"O{i}", "ad": m.ad, "alan_m2": round(m.alan_m2, 2), "x": x, "y": y}
              for i, (_, _, x, y, m) in enumerate(sorted(oda, key=lambda t: (t[0], t[1])), 1)]
    ac = []
    for pn in plan.panolar:
        if not pn.acilim:
            continue
        for g in pn.gaps():
            cx, cy = (g[0] + g[2]) / 2, (g[1] + g[3]) / 2
            a = pn.acilim
            ac.append((-round(cy, 1), round(cx, 1), a, pn.duvar.yon))
    acikliklar, n = [], {"P": 0, "K": 0}
    for ny, x, a, yon in sorted(ac, key=lambda t: (t[0], t[1])):
        on = "P" if a.tur == "pencere" else "K"
        n[on] += 1
        acikliklar.append({"etiket": f"{on}{n[on]}", "tur": a.tur, "mahal": a.mahal, "arasi": list(a.arasi or []) or None,
                           "olcu": a.olcu, "x": x, "y": -ny, "duvar_yonu": yon})
    return {"aks_x": aks_x, "aks_y": aks_y, "odalar": odalar, "acikliklar": acikliklar}


def ciz(ie: dict, hedef: Path, baslik: str = "") -> tuple[Path, dict]:
    """İş Emri → etiketli plan PNG'si ve etiket haritası."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    from motor import geometry as G
    from motor import dizilim_kiyas as DK

    plan = G.kur(copy.deepcopy(ie))
    et = etiketler(plan)
    fig, ax = plt.subplots(figsize=(12, 12 * (plan.H + 260) / (plan.W + 260)), dpi=110)
    DK.ciz(ax, plan, None, baslik or f"Etiketli plan · {DK.tr(plan.W)} × {DK.tr(plan.H)} cm")
    mavi = "#1f5fbf"
    for a in et["aks_x"]:
        ax.plot([a["cm"], a["cm"]], [-95, plan.H + 20], color=mavi, lw=0.6, ls=(0, (4, 4)), zorder=1)
        ax.add_patch(Circle((a["cm"], -110), 17, fc="white", ec=mavi, lw=1.2, zorder=7))
        ax.text(a["cm"], -110, a["ad"], ha="center", va="center", fontsize=10, color=mavi, fontweight="bold", zorder=8)
    for a in et["aks_y"]:
        ax.plot([-95, plan.W + 20], [a["cm"], a["cm"]], color=mavi, lw=0.6, ls=(0, (4, 4)), zorder=1)
        ax.add_patch(Circle((-110, a["cm"]), 17, fc="white", ec=mavi, lw=1.2, zorder=7))
        ax.text(-110, a["cm"], a["ad"], ha="center", va="center", fontsize=10, color=mavi, fontweight="bold", zorder=8)
    for o in et["odalar"]:
        ax.text(o["x"], o["y"] + 38, o["etiket"], ha="center", va="center", fontsize=12, color="white", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", fc="#7a3db8", ec="none"), zorder=9)
    for a in et["acikliklar"]:
        x, y = a["x"], a["y"]
        dx, dy = (0, (-30 if y < plan.H / 2 else 30)) if a["duvar_yonu"] == "x" else ((-34 if x < plan.W / 2 else 34), 0)
        ax.text(x + dx, y + dy, a["etiket"], ha="center", va="center", fontsize=9.5, color="white", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", fc="#d40000" if a["etiket"][0] == "P" else "#0a7d2c", ec="none"), zorder=9)
    ax.set_xlim(-150, plan.W + 80)
    ax.set_ylim(-150, plan.H + 70)
    hedef = Path(hedef)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(hedef, dpi=110)
    plt.close(fig)
    return hedef, et


def main(argv: list[str] | None = None) -> int:
    a = argv if argv is not None else sys.argv[1:]
    if len(a) != 2:
        print(__doc__)
        return 2
    yol, et = ciz(json.loads(Path(a[0]).read_text(encoding="utf-8")), Path(a[1]))
    print(yol)
    print(json.dumps(et, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
