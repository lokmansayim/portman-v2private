import ezdxf, matplotlib, sys; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ezdxf import bbox
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy
doc = ezdxf.readfile('t_fix.dxf'); msp = doc.modelspace()
cache = bbox.Cache()
ents = []
for e in msp:
    try:
        b = bbox.extents([e], cache=cache)
        if b.has_data: ents.append((e, b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y))
    except Exception: pass
F = [(7118,31998,2341,1517),(10681,31998,3601,2100),(14567,31998,3601,2100),(18450,31998,3601,2100),(22300,31998,3601,2100),(25965,31998,3601,2100),(29700,31998,3301,2100),(33160,31419,2369,2581),(35700,31998,2700,2100),(38571,31996,2369,1581),(41254,31998,3138,2100),(44554,31998,3138,2100),(48174,31998,3601,2100),(52059,31998,3601,2100),(55861,31585,3601,2517),(59723,31585,3601,2517),(63553,32001,3601,2100),(67386,32001,3601,2100),(72034,32001,3138,2100)]
cfg = Configuration(lineweight_scaling=0.5, background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.BLACK)
for i, (x, y, w, h) in enumerate(F):
    sub = [e for e, a, b_, c, d in ents if a >= x - 5 and c <= x + w + 5 and b_ >= y - 5 and d <= y + h + 5]
    fig = plt.figure(figsize=(w / 180, h / 180)); ax = fig.add_axes([0, 0, 1, 1])
    Frontend(RenderContext(doc), MatplotlibBackend(ax), config=cfg).draw_entities(sub)
    ax.set_xlim(x, x + w); ax.set_ylim(y, y + h); ax.set_aspect('equal'); ax.axis('off')
    fig.savefig(f'pafta_{i:02d}.png', dpi=110, facecolor='white'); plt.close(fig)
    print(i, x, len(sub), flush=True)
