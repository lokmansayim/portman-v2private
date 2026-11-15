"""yan_yana.py <dxf> <kart.json> <plan> <geo.json> <ie.json> <çıktı.png> [başlık]: solda paftanın kendisi (çizimden), sağda Motor'un
pano dizilimi. Motor'un panosu gri: paftadaki panoyla aynı (iki ucu 1,5 cm içinde); mavi: 5 cm'ye kadar kaymış (köşe ya da T payı);
pembe: paftada yok."""
import json, math, re, sys
from pathlib import Path
KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK)); sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy
import pafta_kart as PK
import pafta_kiyas as K
from motor import dizilim_kiyas as DK

dxf, kart, j, geo, iey, cikti = sys.argv[1:7]
baslik = sys.argv[7] if len(sys.argv) > 7 else ""
plan = json.load(open(kart))[int(j)]
g = json.load(open(geo))
ie = json.load(open(iey))
# çizim kutusu: gövde + taşan verandalar + 60 cm (başlık ve antet dışarıda kalır)
vd = {"on": 0, "arka": 0, "sol": 0, "sag": 0}
for v in g["verandalar"]:
    vd[v["cephe"]] = max(vd[v["cephe"]], v["derinlik_cm"])
x0, x1 = g["X0"] - vd["sol"] - 60, g["X0"] + g["W"] + vd["sag"] + 60
y0, y1 = g["Y1"] - g["H"] - vd["on"] - 60, g["Y1"] + vd["arka"] + 60

doc = PK.yukle(dxf)
for e in doc.modelspace().query("MTEXT"):     # \pi girinti kodları yazıyı kaydırıyor: çizimde sil
    e.text = re.sub(r"\\pi[-0-9.,]*(?:,[a-z][-0-9.]*)*;", "", e.text)
en, boy = x1 - x0, y1 - y0
fig, axs = plt.subplots(1, 2, figsize=(20, 10 * boy / en + 1.6), dpi=110)
ax = axs[0]
ax.set_facecolor("white")
cfg = Configuration(background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.BLACK)
ctx = RenderContext(doc)
be = MatplotlibBackend(ax)
sec = [e for e, b in PK.oge_kutulari(doc.modelspace()) if b[0] >= x0 - 30 and b[2] <= x1 + 30 and b[1] >= y0 - 30 and b[3] <= y1 + 30]
Frontend(ctx, be, config=cfg).draw_entities(sec)
be.finalize()
ax.set_aspect("equal", adjustable="box"); ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.axis("off")
ax.set_title("Pafta (montaj planı, çizimden)", fontsize=14)

# Motor'un panoları: paftadaki ekle kıyas
satir, ac, mplan = K.karsilastir(g, ie)
H = mplan.H
P = K.pafta_duvarlari(g)
sinif = {}
for d in mplan.duvarlar:
    if d.yon == "x":
        yon, c = "y", H - d.c
        cev = lambda a: a
    else:
        yon, c = "x", d.c
        cev = lambda a: H - a
    ekler = []
    for p in P:
        if p["yon"] == yon and (abs(p["c"] - c) <= 3 or abs(p["aks"] - c) <= 3):
            ekler += [a for a, b in p["parca"]] + [b for a, b in p["parca"]]
    for pn in d.panolar:
        u = sorted((cev(pn.a0), cev(pn.a1)))
        fark = max(min((abs(u[0] - e) for e in ekler), default=99), min((abs(u[1] - e) for e in ekler), default=99))
        sinif[id(pn)] = "ayni" if fark <= 1.6 else ("kaydi" if fark <= 5.1 else "degisti")
n = {k: sum(1 for v in sinif.values() if v == k) for k in ("ayni", "kaydi", "degisti")}
DK.ciz(axs[1], mplan, sinif, f"Motor'un pano dizilimi · {DK.tr(mplan.W)} × {DK.tr(mplan.H)} cm · {len(mplan.panolar)} pano")
axs[1].set_xlim(-vd["sol"] - 60 - 110, mplan.W + vd["sag"] + 60)
axs[1].set_ylim(-vd["on"] - 60 - 60, mplan.H + vd["arka"] + 60)
import uydur as UY
ac_ok = sum(1 for a in ac if UY.yerinde(a))
fig.text(0.5, 0.045, f"{baslik}   Gri: paftadaki panoyla aynı ({n['ayni']}).   Mavi: 5 cm'ye kadar kaymış, köşe ya da T payı ({n['kaydi']}).   "
         f"Pembe: paftada başka yerde ({n['degisti']}).", ha="center", fontsize=12, color="#333333")
fig.text(0.5, 0.015, f"Kapı ve pencere: {ac_ok}/{len(ac)} paftadaki yerinde.   Kırmızı çerçeve pencere, yeşil çerçeve kapı.",
         ha="center", fontsize=12, color="#333333")
fig.set_size_inches(20, 10 * boy / en + 1.6)
for a_ in axs:
    a_.set_aspect("equal", adjustable="box")
plt.tight_layout(rect=(0, 0.07, 1, 1))
fig.savefig(cikti, dpi=110)
print(cikti, n, ac_ok, len(ac))
