"""DXF'ten gelen çerçevede dikme aksları: dış duvar çizgisi üzerindeki, tam boy (>=250 cm) düşey gövde yüzlerinin konumu."""
import pickle, collections, numpy as np, sys
import skp_oku
ad = sys.argv[1]
r = pickle.load(open("ara/%s.pkl" % ad, "rb"))
W = [f for f in r["yuzler"] if f["katman"] == "LCAD_Wall"]
P = np.vstack([h for f in W for h in f["halkalar"]]); mn, mx = P.min(0), P.max(0)
def aks(eks_boy, sabit_eks, sabit_deger, tol=16.0):
    xs = []
    for f in W:
        A, n = skp_oku.yuz_alani(f)
        H = f["halkalar"][0]; o = H.max(0) - H.min(0)
        if o[2] < 250: continue                         # tam boy düşey yüz
        if abs(n[eks_boy]) < 0.99: continue             # gövde yüzü: normali duvar boyunca
        c = H.mean(0)
        if abs(c[sabit_eks] - sabit_deger) > tol: continue
        xs.append(c[eks_boy])
    if not xs: return []
    xs = np.sort(xs); k = [[xs[0]]]
    for a in xs[1:]:
        if a - k[-1][-1] > 3.0: k.append([a])
        else: k[-1].append(a)
    return [round(float(np.mean(c)), 1) for c in k]
for adx, eb, se, sd in (("ön (y−)", 0, 1, mn[1]), ("arka (y+)", 0, 1, mx[1]), ("sol (x−)", 1, 0, mn[0]), ("sağ (x+)", 1, 0, mx[0])):
    a = aks(eb, se, sd)
    d = [round(a[i+1]-a[i], 1) for i in range(len(a)-1)]
    c = collections.Counter(d)
    print("%-10s dikme %2d  aralıklar: %s" % (adx, len(a), d))
    print("            en sık: %s" % c.most_common(4))
