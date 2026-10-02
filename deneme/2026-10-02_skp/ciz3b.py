"""Çözülen SKP yüzeylerini dik izdüşümle çizer (plan, ön, yan, izometrik)."""
import sys, math, pickle, os, collections
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection, LineCollection
import mapbox_earcut as earcut
import skp_oku

PALET = ["#4c78a8","#f58518","#54a24b","#e45756","#72b7b2","#b279a2","#ff9da6","#9d755d","#bab0ac","#eeca3b","#2f4b7c","#a05195","#d45087","#665191","#ffa600","#003f5c"]

def taban(az, el):
    az = math.radians(az); el = math.radians(el)
    # bakış yönü (kameradan sahneye)
    d = np.array([-math.cos(el)*math.cos(az), -math.cos(el)*math.sin(az), -math.sin(el)])
    up = np.array([0,0,1.0])
    if abs(d @ up) > 0.999: up = np.array([0,1.0,0])
    r = np.cross(d, up); r /= np.linalg.norm(r)
    u = np.cross(r, d)
    return r, u, d

def ucgenle(halkalar, r, u):
    if len(halkalar) == 1 and len(halkalar[0]) <= 4:
        return None
    n = skp_oku.alan_normal(halkalar[0])[1]
    h = np.array([1.0,0,0]) if abs(n[0]) < 0.9 else np.array([0,1.0,0])
    a = np.cross(n, h); a /= np.linalg.norm(a); b = np.cross(n, a)
    P = np.vstack(halkalar)
    uv = np.column_stack([P @ a, P @ b])
    son = np.cumsum([len(x) for x in halkalar]).astype(np.uint32)
    try:
        tri = earcut.triangulate_float64(uv, son)
    except Exception:
        return None
    return P[np.array(tri).reshape(-1,3)]

def ciz(ax, yuzler, az, el, renk_fn, kenar=True, lw=0.25, alpha=1.0, isik=True):
    r, u, d = taban(az, el)
    polys = []; cols = []; depth = []
    L = np.array([0.35, -0.5, 0.8]); L /= np.linalg.norm(L)
    for f in yuzler:
        hk = f["halkalar"]
        A, n = skp_oku.alan_normal(hk[0])
        c = np.array(matplotlib.colors.to_rgb(renk_fn(f)))
        if isik:
            s = 0.55 + 0.45*abs(n @ L)
            c = np.clip(c*s, 0, 1)
        tr = ucgenle(hk, r, u) if len(hk) > 1 else None
        if tr is not None:
            for t in tr:
                polys.append(np.column_stack([t @ r, t @ u])); cols.append(c); depth.append((t @ d).mean())
        else:
            h = hk[0]
            polys.append(np.column_stack([h @ r, h @ u])); cols.append(c); depth.append((h @ d).mean())
    sira = np.argsort(depth)[::-1]
    pc = PolyCollection([polys[i] for i in sira], facecolors=[cols[i] for i in sira],
                        edgecolors=(0,0,0,0.55) if kenar else "none", linewidths=lw if kenar else 0, alpha=alpha)
    ax.add_collection(pc)
    ax.autoscale(); ax.set_aspect("equal"); ax.axis("off")

def pafta(yuzler, cikti, baslik="", katman_sira=None, sec=None):
    if sec: yuzler = [f for f in yuzler if sec(f)]
    kat = collections.Counter(f["katman"] for f in yuzler)
    adlar = [k for k, _ in kat.most_common()]
    renk = {k: PALET[i % len(PALET)] for i, k in enumerate(adlar)}
    fn = lambda f: renk[f["katman"]]
    fig, axs = plt.subplots(2, 2, figsize=(20, 14), dpi=110)
    for ax, (az, el, t) in zip(axs.ravel(), [(-60, 28, "izometrik (ön-sol)"), (-90, 90, "plan (üstten)"), (-90, 0, "ön görünüş (−y'den)"), (0, 0, "yan görünüş (+x'ten)")]):
        ciz(ax, yuzler, az, el, fn)
        ax.set_title(t, fontsize=13)
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=renk[k], label="%s (%d)" % (k, kat[k])) for k in adlar[:16]], loc="lower center", ncol=8, fontsize=9, frameon=False)
    fig.suptitle(baslik, fontsize=15)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    fig.savefig(cikti); plt.close(fig)

if __name__ == "__main__":
    yol, cikti = sys.argv[1], sys.argv[2]
    r = skp_oku.oku(yol)
    th = r["p"].get("thumbnail_data")
    if th:
        open(os.path.splitext(cikti)[0] + "_kucukresim.png", "wb").write(th)
    pafta(r["yuzler"], cikti, baslik=sys.argv[3] if len(sys.argv) > 3 else "")
    print("ok", cikti, len(r["yuzler"]))
