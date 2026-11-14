"""Önce/sonra pano dizilimi görseli (İE-39; Lokman'ın çalışma kuralı 12, 7 Kasım 2026, D-68).

Plan değişikliği önce pano diziliminde gösterilir: önce ve sonra yan yana, değişen panolar renkli, değişmeyen panolar gri ("aynı").
İki plan da Motor'un `Plan`'ından çizilir; Motor'un geometrisi değişmez. Ön onay çizimi (M-02) bu görselden ayrıdır.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon as MPoly, Rectangle  # noqa: E402

MOD = 125.5
RENK = {"ayni": ("#d9d9d9", "#555555"), "kaydi": ("#9cc3f0", "#1f6fd1"), "degisti": ("#f7a8d0", "#c4006a")}
OZEL_RENK = "#7a2fb0"


def tr(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def ciz(ax, plan, sinif: dict | None, baslik: str) -> None:
    """Bir planın pano dizilimi: odalar ve net m², köşeler, panolar (sınıf rengiyle), kapı ve pencere, 125,5 dışı pano boyu, dış ölçü."""
    for m in plan.mahaller.values():
        if m.poly is None:
            continue
        for pg in getattr(m.poly, "geoms", [m.poly]):
            ax.add_patch(MPoly(list(pg.exterior.coords), closed=True, fc="#fffbe6" if m.acik else "#ffffff", ec="none", zorder=0))
        c = m.poly.representative_point()
        ax.text(c.x, c.y, f"{m.ad}\n{tr(m.alan_m2)} m²", ha="center", va="center", fontsize=9.5, color="#222222", zorder=5)
    for k in plan.koseler:
        ax.add_patch(Rectangle((k.rect[0], k.rect[1]), k.rect[2] - k.rect[0], k.rect[3] - k.rect[1], fc="#333333", ec="none", zorder=2))
    for pn in plan.panolar:
        s = (sinif or {}).get(id(pn), "ayni")
        fc, ec = RENK[s]
        for r in pn.rects():
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc=fc, ec=ec, lw=0.8, zorder=3))
        for g in pn.gaps():
            renk = "#d40000" if (pn.acilim and pn.acilim.tur == "pencere") else "#0a7d2c"
            ax.add_patch(Rectangle((g[0], g[1]), g[2] - g[0], g[3] - g[1], fc="none", ec=renk, lw=1.6, zorder=4))
        x0, y0, x1, y1 = pn.rect()
        if pn.duvar.yon == "x":
            ax.plot([x0, x0], [y0 - 8, y1 + 8], color="#000000", lw=0.7, zorder=4)
        else:
            ax.plot([x0 - 8, x1 + 8], [y0, y0], color="#000000", lw=0.7, zorder=4)
        if abs(pn.boy - MOD) > 0.05:
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            renk = ec if s != "ayni" else OZEL_RENK
            if pn.duvar.yon == "x":
                ax.text(cx, cy + (22 if cy > plan.H / 2 else -22), tr(pn.boy), ha="center", va="center", fontsize=7.5, color=renk, zorder=6)
            else:
                ax.text(cx + (22 if cx > plan.W / 2 else -22), cy, tr(pn.boy), ha="center", va="center", fontsize=7.5, rotation=90,
                        color=renk, zorder=6)
    for dk in plan.dikmeler:
        ax.add_patch(Rectangle((dk[0], dk[1]), dk[2] - dk[0], dk[3] - dk[1], fc="#333333", zorder=3))
    ax.annotate("", xy=(0, -60), xytext=(plan.W, -60), arrowprops=dict(arrowstyle="<->", lw=0.8))
    ax.text(plan.W / 2, -82, f"{tr(plan.W)} cm", ha="center", va="top", fontsize=10)
    ax.annotate("", xy=(-60, 0), xytext=(-60, plan.H), arrowprops=dict(arrowstyle="<->", lw=0.8))
    ax.text(-82, plan.H / 2, f"{tr(plan.H)} cm", ha="right", va="center", fontsize=10, rotation=90)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(baslik, fontsize=13, loc="left", fontweight="bold")


def once_sonra(p0, p1, siniflar: dict, yol: Path, baslik_sonra: str, kayma: float, eksen: str, kenar: str) -> Path:
    """Önce ve sonra yan yana (x yönündeki değişimde) ya da alt alta değil, yine yan yana; sonra planında panolar sınıf rengiyle.
    `siniflar`: sonraki planın panosu (id) → 'ayni' | 'kaydi' | 'degisti'. `kayma` cm, `eksen` x | y, `kenar` gerçek çerçevede min | max."""
    yol = Path(yol)
    sayi = Counter(siniflar.values())
    Wm, Hm = max(p0.W, p1.W), max(p0.H, p1.H)
    fig, axs = plt.subplots(1, 2, figsize=(20, 9.5 * (Hm + 230) / (Wm + 260) + 1.6), dpi=120)
    ciz(axs[0], p0, None, f"Önce · {tr(p0.W)} × {tr(p0.H)} cm · {len(p0.panolar)} pano")
    ciz(axs[1], p1, siniflar, f"{baslik_sonra} · {tr(p1.W)} × {tr(p1.H)} cm · {len(p1.panolar)} pano")
    for ax in axs:
        ax.set_xlim(-170, Wm + 90)
        ax.set_ylim(-150, Hm + 60)
    yon = {("x", "max"): "sağa", ("x", "min"): "sola", ("y", "min"): "öne", ("y", "max"): "arkaya"}[(eksen, kenar)]
    yon = yon if kayma > 0 else {"sağa": "sola", "sola": "sağa", "öne": "arkaya", "arkaya": "öne"}[yon]
    fig.text(0.5, 0.035, f"Gri: aynı pano, yeri ve boyu değişmedi ({sayi['ayni']}).   Mavi: aynı pano, duvarla birlikte {tr(abs(kayma))} cm "
             f"{yon} kaydı ({sayi['kaydi']}).   Pembe: boyu değişen ya da yeni pano ({sayi['degisti']}).", ha="center", fontsize=11.5,
             color="#333333")
    fig.text(0.5, 0.012, "Kırmızı çerçeve pencere, yeşil çerçeve kapı. Sayı: 125,5 cm dışındaki pano boyu.", ha="center", fontsize=11.5,
             color="#333333")
    plt.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(yol, dpi=120)
    plt.close(fig)
    return yol
