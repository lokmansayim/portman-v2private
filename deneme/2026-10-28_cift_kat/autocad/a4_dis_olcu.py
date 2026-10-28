#!/usr/bin/env python3
"""A4 (yatay) paftalar, zemin kat (Lokman 28.10 14:36 / 15:03): sayfa 1 yalnız dış ölçüler (kıyas kopyası, x 3300…),
sayfa 2 akslı pano planı (pano pano ölçüler, akslar, bloklar; x 0…). Profiller görünür (14:41)."""
import ezdxf, matplotlib, pathlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
K = pathlib.Path(__file__).resolve().parent
d = ezdxf.readfile(str(K / "Portman_IE22-CK01_CIFT_KAT_sablon_bloklu_r01.dxf"))
msp = d.modelspace(); ctx = RenderContext(d)
cfg = Configuration(background_policy=BackgroundPolicy.WHITE)
SAYFALAR = [
    ("ZEMİN KAT — yalnız dış ölçüler (dış yüzden dış yüze, cm)", (3300 - 100, -110, 3300 + 763 + 130, 975),
     {"CIFT_KAT_NOT", "AKS", "AKS_YAZI", "OLCULER", "OZEL_PANEL_OLCU_CM"}),
    ("ZEMİN KAT — akslı pano planı (pano pano ölçüler, akslar A–G / 1–7)", (-110, -120, 763 + 130, 975),
     {"CIFT_KAT_NOT", "KIYAS_OLCU"}),
]
out = K / "Portman_IE22-CK01_ZEMIN_dis_olculer_A4.pdf"
with PdfPages(str(out)) as pdf:
    for baslik, (x0, y0, x1, y1), gizli in SAYFALAR:
        def suzgec(e, gizli=gizli, x0=x0, y0=y0, x1=x1, y1=y1):
            if e.dxf.layer in gizli: return False
            p = None
            for alan in ("insert", "start", "defpoint", "center"):
                if e.dxf.hasattr(alan): p = e.dxf.get(alan); break
            if p is None and e.dxftype() == "LWPOLYLINE":
                pts = list(e.get_points()); p = pts[0] if pts else None
            if p is None: return False
            return x0 <= p[0] <= x1 and y0 <= p[1] <= y1
        fig = plt.figure(figsize=(11.69, 8.27))
        ax = fig.add_axes([0.02, 0.02, 0.96, 0.92])
        Frontend(ctx, MatplotlibBackend(ax), config=cfg).draw_layout(msp, finalize=False, filter_func=suzgec)
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal", adjustable="box"); ax.set_axis_off()
        fig.suptitle(baslik + " · İE-22 CK-01 · 28.10.2026 · TASLAK", fontsize=11)
        pdf.savefig(fig, facecolor="white", dpi=200); plt.close(fig)
print("yazıldı", out.name, out.stat().st_size // 1024, "KB")
