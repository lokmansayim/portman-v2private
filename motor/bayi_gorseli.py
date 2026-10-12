"""İE-04 · Bayi plan görseli: İş Emri'nden telefonda okunur, üstten, ölçülü şematik kat planı (PNG).

Aynı İş Emri'nden Motor'un kurduğu geometriyle çizilir (motor.geometry.kur); ayrı bir geometri yoktur. PDF'e ve DXF'e
dokunmaz. Oda adı ve net m², dış ölçüler, pencere ve kapılar, veranda ve açık kenarlar görünür. Şematiktir; üretim çizimi
değildir (altına yazılır). Bileşik görsel: seçenek mesajı için en çok üç adayın planı yan yana, puanlarıyla.
"""
from __future__ import annotations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Arc

from . import geometry as G

RENK = {"salon": "#f3e7d3", "mutfak": "#f3e7d3", "hol": "#efefef", "yatak_odasi": "#dbe7f3", "banyo": "#d5ecec", "depo": "#e9e9e9",
        "teknik": "#e9e9e9", "calisma": "#dbe7f3", "giyinme": "#dbe7f3", "veranda": "#f7f1e6", "balkon": "#f7f1e6", "teras": "#f7f1e6",
        "sundurma": "#f7f1e6"}
DUVAR = "#2b2b2b"; PENCERE = "#4f93c8"; KAPI = "#8a6d3b"; OLCU = "#555555"


def _fmt(cm: float) -> str:
    return f"{cm:.1f}".rstrip("0").rstrip(".").replace(".", ",")


def plan_gorseli(ie: dict, yol: Path, v: dict | None = None, genislik_px: int = 1400) -> Path:
    """İş Emri → PNG. v: Motor doğrulaması (validation.json; rooms_m2 varsa net alanlar oradan, yoksa geometriden)."""
    plan = G.kur(ie)
    W, H = plan.W, plan.H
    rooms = (v or {}).get("rooms_m2") or {}
    pay = 120.0                                  # ölçü çizgileri için kenar payı (cm)
    fig_w = genislik_px / 100
    fig = plt.figure(figsize=(fig_w, fig_w * (H + 2 * pay + 90) / (W + 2 * pay)), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(-pay, W + pay); ax.set_ylim(-pay - 60, H + pay + 30)
    # mahaller
    for ad, m in plan.mahaller.items():
        poly = m.poly
        if poly is None or poly.is_empty:
            continue
        polys = list(poly.geoms) if hasattr(poly, "geoms") else [poly]
        for pg in polys:
            xs, ys = pg.exterior.xy
            ax.fill(xs, ys, color=RENK.get(m.tur, "#eeeeee"), zorder=1,
                    hatch="//" if m.acik else None, edgecolor="#c9b99b" if m.acik else "none", linewidth=0)
        c = poly.representative_point()
        alan = rooms.get(ad, m.alan_m2)
        ax.text(c.x, c.y + 14, ad, ha="center", va="center", fontsize=10, color="#1f1f1f", zorder=5, fontweight="bold")
        ax.text(c.x, c.y - 16, f"{float(alan):.1f} m²".replace(".", ","), ha="center", va="center", fontsize=9.5, color="#333333", zorder=5)
    # açık kenarlar (veranda profili): kesik çizgi
    for (x0, y0, x1, y1, *_r) in plan.acik_kenarlar:
        ax.plot([x0, x1], [y0, y1], color="#b59a6a", linestyle=(0, (4, 3)), linewidth=1.6, zorder=3)
    # duvarlar ve köşeler
    for d in plan.duvarlar:
        for p in d.panolar:
            for (x0, y0, x1, y1) in p.rects():
                ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=DUVAR, edgecolor=DUVAR, linewidth=0.5, zorder=4))
            g = p.gap()
            if not g or not p.acilim:
                continue
            x0, y0, x1, y1 = g
            if p.acilim.tur == "pencere":
                ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor="white", edgecolor=PENCERE, linewidth=1.2, zorder=4))
                if d.yon == "x":
                    ax.plot([x0, x1], [(y0 + y1) / 2] * 2, color=PENCERE, linewidth=1.0, zorder=5)
                    ax.text((x0 + x1) / 2, y1 + 9 if d.c < H / 2 else y0 - 9, p.acilim.olcu, ha="center", va="bottom" if d.c < H / 2 else "top",
                            fontsize=7, color=PENCERE, zorder=5)
                else:
                    ax.plot([(x0 + x1) / 2] * 2, [y0, y1], color=PENCERE, linewidth=1.0, zorder=5)
                    ax.text(x1 + 9 if d.c < W / 2 else x0 - 9, (y0 + y1) / 2, p.acilim.olcu, ha="left" if d.c < W / 2 else "right", va="center",
                            fontsize=7, color=PENCERE, rotation=90, zorder=5)
            else:
                ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor="white", edgecolor="white", linewidth=0.5, zorder=4))
                w = p.acilim.genislik
                if d.yon == "x":
                    yon = 1 if (p.acilim.icine_normal or "+y").endswith("y") and (p.acilim.icine_normal or "+y").startswith("+") else -1
                    cx = x0 if (p.acilim.mentese or "sag") == "sol" else x1
                    ax.add_patch(Arc((cx, (y0 + y1) / 2), 2 * w, 2 * w, angle=0, theta1=0 if (cx == x0 and yon > 0) else (90 if (cx == x1 and yon > 0) else (180 if cx == x1 else 270)),
                                     theta2=(90 if (cx == x0 and yon > 0) else (180 if (cx == x1 and yon > 0) else (270 if cx == x1 else 360))), color=KAPI, linewidth=1.0, zorder=5))
                else:
                    yon = 1 if (p.acilim.icine_normal or "+x").startswith("+") else -1
                    cy = y0 if (p.acilim.mentese or "sag") == "sol" else y1
                    ax.add_patch(Arc(((x0 + x1) / 2, cy), 2 * w, 2 * w, angle=0, theta1=0 if (cy == y0 and yon > 0) else (270 if (cy == y1 and yon > 0) else (90 if cy == y0 else 180)),
                                     theta2=(90 if (cy == y0 and yon > 0) else (360 if (cy == y1 and yon > 0) else (180 if cy == y0 else 270))), color=KAPI, linewidth=1.0, zorder=5))
    for k in plan.koseler:
        x0, y0, x1, y1 = k.rect
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=DUVAR, edgecolor=DUVAR, linewidth=0.5, zorder=4))
    for (x0, y0, x1, y1) in plan.dikmeler:
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor="#6b5b45", edgecolor="#6b5b45", zorder=4))
    # dış ölçüler
    oy = -pay * 0.55
    ax.annotate("", xy=(0, oy), xytext=(W, oy), arrowprops=dict(arrowstyle="|-|", color=OLCU, lw=1.0, mutation_scale=4), zorder=6)
    ax.text(W / 2, oy - 12, f"{_fmt(W)} cm", ha="center", va="top", fontsize=9.5, color=OLCU, zorder=6)
    ox = -pay * 0.55
    ax.annotate("", xy=(ox, 0), xytext=(ox, H), arrowprops=dict(arrowstyle="|-|", color=OLCU, lw=1.0, mutation_scale=4), zorder=6)
    ax.text(ox - 12, H / 2, f"{_fmt(H)} cm", ha="right", va="center", fontsize=9.5, color=OLCU, rotation=90, zorder=6)
    # başlık ve not
    no = ie.get("is_emri_no", ""); rev = int(ie.get("revizyon") or 1)
    ax.text(W / 2, H + pay * 0.55, f"{no} · r{rev:02d} · {plan.nx:g}×{plan.ny:g} pano ({_fmt(W)}×{_fmt(H)} cm)", ha="center", va="center", fontsize=11,
            color="#1f1f1f", fontweight="bold", zorder=6)
    ax.text(W / 2, -pay - 42, "Şematik kat planı · net alanlar m² · ölçüler cm · üretim çizimi değildir; ölçülü plan PDF'te", ha="center", va="center",
            fontsize=8, color="#666666", zorder=6)
    yol = Path(yol); yol.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(yol, dpi=100, facecolor="white"); plt.close(fig)
    return yol


def bilesik_gorsel(adaylar: list[dict], yol: Path, baslik: str = "", panel_px: int = 460) -> Path | None:
    """Seçenek mesajı için en çok üç adayın plan görseli yan yana (sıra, kod, m², puan). Görseli olmayan aday atlanır; hiç yoksa None."""
    from PIL import Image, ImageDraw, ImageFont
    import matplotlib.font_manager as fm
    secili = [a for a in adaylar if a.get("gorsel_yolu") and Path(str(a["gorsel_yolu"])).is_file()][:3]
    if not secili:
        return None
    font_yol = fm.findfont("DejaVu Sans")
    f_b = ImageFont.truetype(font_yol, 26); f_n = ImageFont.truetype(font_yol, 20); f_s = ImageFont.truetype(font_yol, 16)
    ust, alt, ara = 64, 96, 16
    W = ara + len(secili) * (panel_px + ara); H = ust + panel_px + alt
    img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img)
    if baslik:
        d.text((ara, 18), baslik[:70], font=f_n, fill="#333333")
    for i, a in enumerate(secili):
        x = ara + i * (panel_px + ara); y = ust
        try:
            p = Image.open(str(a["gorsel_yolu"])).convert("RGB")
            p.thumbnail((panel_px, panel_px))
            img.paste(p, (x + (panel_px - p.width) // 2, y + (panel_px - p.height) // 2))
        except Exception:
            d.rectangle([x, y, x + panel_px, y + panel_px], outline="#cccccc")
        d.rectangle([x, y, x + panel_px, y + panel_px], outline="#bbbbbb", width=2)
        d.text((x + 8, y + panel_px + 8), f"{a.get('sira', i + 1)}. {a.get('gosterim') or a.get('kod', '')}", font=f_b, fill="#1f1f1f")
        cati = (a.get("sunum") or {}).get("cati_adi") if isinstance(a.get("sunum"), dict) else None     # İE-08 çelik: çatı adı (K/L farkı)
        m2 = a.get("katalog_m2")
        satir = (f"{m2:g}" if isinstance(m2, (int, float)) else f"{m2}") + " m² katalog" + (f" · kapalı {a.get('kapali_m2')}" if a.get("kapali_m2") is not None else "")
        if cati:
            satir = f"{cati} · {satir}"
        d.text((x + 8, y + panel_px + 42), satir[:44], font=f_s, fill="#444444")
        puan = a.get("puan")
        if puan is not None:
            d.text((x + panel_px - 8, y + panel_px + 8), f"{puan}", font=f_b, fill="#1d5fa8", anchor="ra")
            d.text((x + panel_px - 8, y + panel_px + 42), "/100 puan", font=f_s, fill="#1d5fa8", anchor="ra")
        if a.get("durum") == "test":
            d.text((x + 8, y + 8), "TEST VERİSİ", font=f_s, fill="#b00020")
    yol = Path(yol); yol.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(yol), "PNG", optimize=True)
    return yol
