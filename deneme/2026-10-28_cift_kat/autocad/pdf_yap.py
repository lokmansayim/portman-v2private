#!/usr/bin/env python3
"""Çift kat çiziminden sohbet için PDF (Lokman 14:02 "PDF olarak ver"): 1–2 kıyas kopyaları, 3–4 akslı pano planları, 5 kesit + kart."""
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
SAYFALAR = [("1 · ZEMİN KAT — kıyas kopyası (duvar yüzünden yüzüne ölçüler)", (3230, -90, 4300, 965)),
            ("2 · 1. KAT — kıyas kopyası", (4330, -90, 5400, 965)),
            ("3 · ZEMİN KAT — akslı pano planı (Şablon 2024 blok adları)", (-90, -90, 870, 965)),
            ("4 · 1. KAT — akslı pano planı", (1010, -90, 1970, 965)),
            ("5 · Kısa kenar kesiti / kat kotları ve malzeme kartı", (-60, -1000, 3100, 980))]
out = K / "Portman_IE22-CK01_CIFT_KAT_sablon_bloklu_r01.pdf"
from PIL import Image
import io
sayfalar = []
for baslik, (x0, y0, x1, y1) in SAYFALAR:          # sayfalar raster (vektör PDF 12 MB oluyordu: ağır kapı sembolleri)
    fig = plt.figure(figsize=(16.5, 11.7))        # A3 yatay
    ax = fig.add_axes([0.02, 0.02, 0.96, 0.93])
    Frontend(ctx, MatplotlibBackend(ax), config=cfg).draw_layout(msp, finalize=False)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal", adjustable="box"); ax.set_axis_off()
    fig.suptitle(baslik + " · İE-22 CK-01 · 28.10.2026 · ölçüler cm · TASLAK", fontsize=12)
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=140, facecolor="white"); plt.close(fig)
    buf.seek(0); sayfalar.append(Image.open(buf).convert("RGB"))
sayfalar[0].save(str(out), save_all=True, append_images=sayfalar[1:], resolution=140.0)
print("pdf yazıldı", out.name, out.stat().st_size // 1024, "KB", len(sayfalar), "sayfa")
