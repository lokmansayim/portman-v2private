#!/usr/bin/env python3
"""Tek A4 (yatay): yalnız zemin kat, yalnız dış ölçüler (Lokman 28.10 14:36 "iç ölçüleri boş ver, bir A4'e sadece dış ölçüler ve zemin katı koy").
Kaynak: Portman_IE22-CK01_CIFT_KAT_sablon_bloklu_r01.dxf, zemin katın kıyas kopyası (x 3300…); H simgeleri, köşe kutuları, notlar gizli."""
import ezdxf, matplotlib, pathlib, sys
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
K = pathlib.Path(__file__).resolve().parent
d = ezdxf.readfile(str(K / "Portman_IE22-CK01_CIFT_KAT_sablon_bloklu_r01.dxf"))
msp = d.modelspace(); ctx = RenderContext(d)
GIZLI = {"IC_UCLU_H_100", "DIS_UCLU_H_100", "CIFT_KAT_NOT", "KOSE_PROFIL_100", "AKS", "AKS_YAZI", "OLCULER", "OZEL_PANEL_OLCU_CM"}
x0, y0, x1, y1 = 3300 - 100, -110, 3300 + 763 + 120, 960
def suzgec(e):
    if e.dxf.layer in GIZLI: return False
    p = None
    for alan in ("insert", "start", "defpoint", "center"):
        if e.dxf.hasattr(alan): p = e.dxf.get(alan); break
    if p is None and e.dxftype() == "LWPOLYLINE":
        pts = list(e.get_points()); p = pts[0] if pts else None
    if p is None: return False
    return x0 <= p[0] <= x1 and y0 <= p[1] <= y1
fig = plt.figure(figsize=(11.69, 8.27))                     # A4 yatay
ax = fig.add_axes([0.02, 0.02, 0.96, 0.92])
fe = Frontend(ctx, MatplotlibBackend(ax), config=Configuration(background_policy=BackgroundPolicy.WHITE))
fe.draw_layout(msp, finalize=False, filter_func=suzgec)
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal", adjustable="box"); ax.set_axis_off()
fig.suptitle("ZEMİN KAT — yalnız dış ölçüler (dış yüzden dış yüze, cm) · İE-22 CK-01 · 28.10.2026 · TASLAK", fontsize=11)
out = K / "Portman_IE22-CK01_ZEMIN_dis_olculer_A4.pdf"
fig.savefig(str(out), format="pdf", facecolor="white", dpi=200); plt.close(fig)
print("yazıldı", out.name, out.stat().st_size // 1024, "KB")
