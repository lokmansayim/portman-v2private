import ezdxf, matplotlib, sys; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ezdxf import bbox
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy
x0, y0, x1, y1, ad = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
px = float(sys.argv[6]) if len(sys.argv) > 6 else 2400
doc = ezdxf.readfile('t_fix.dxf'); msp = doc.modelspace(); cache = bbox.Cache(); sub = []
for e in msp:
    try:
        b = bbox.extents([e], cache=cache)
        if b.has_data and b.extmax.x >= x0 and b.extmin.x <= x1 and b.extmax.y >= y0 and b.extmin.y <= y1 and (b.extmax.x-b.extmin.x) < 3*(x1-x0): sub.append(e)
    except Exception: pass
w, h = x1 - x0, y1 - y0; s = px / w
fig = plt.figure(figsize=(px / 100, h * s / 100)); ax = fig.add_axes([0, 0, 1, 1])
cfg = Configuration(lineweight_scaling=0.6, background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.COLOR)
Frontend(RenderContext(doc), MatplotlibBackend(ax), config=cfg).draw_entities(sub)
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.axis('off')
fig.savefig(ad, dpi=100, facecolor='white'); print(len(sub))
