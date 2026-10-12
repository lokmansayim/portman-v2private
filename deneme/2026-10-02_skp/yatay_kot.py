"""Üye tipi olmayan (DXF'ten gelen) çerçeve modellerinde: yatay profillerin alt kotları, dikme aralıkları, açıklık başlıkları."""
import pickle, collections, numpy as np, sys
import skp_oku
ad = sys.argv[1]
r = pickle.load(open("ara/%s.pkl" % ad, "rb"))
W = [f for f in r["yuzler"] if f["katman"] == "LCAD_Wall"]
# yatay yüzler (normal ±z), uzun kenarı >= 40 cm: (z, uzunluk)
H = collections.defaultdict(float)
for f in W:
    A, n = skp_oku.yuz_alani(f)
    if abs(n[2]) < 0.99: continue
    P = f["halkalar"][0]; o = P.max(0) - P.min(0); L = max(o[0], o[1]); gen = min(o[0], o[1])
    if L >= 40 and gen >= 3.0:
        H[round(float(P[0][2]), 1)] += L
print("yatay yüz kotları (cm): toplam boy m")
for z, L in sorted(H.items()):
    if L > 150: print("   z=%6.1f  %7.1f m" % (z, L/100))
# kesit genişliği: dar yatay yüzlerin genişlik dağılımı
G = collections.Counter()
for f in W:
    A, n = skp_oku.yuz_alani(f)
    if abs(n[2]) < 0.99: continue
    P = f["halkalar"][0]; o = P.max(0) - P.min(0)
    G[(round(float(min(o[0], o[1])),1))] += 1
print("yatay yüz genişlikleri (cm):", G.most_common(8))
