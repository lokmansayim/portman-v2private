"""Çatı düzlemleri: eğimli yüzleri (aşağı yön, eğim, düzlem sabiti) kümelerine ayırır; saçak ucu ve mahya kotunu verir.
Kullanım: python cati_olc.py <ad>   (ara/<ad>.pkl okunur)"""
import pickle, collections, numpy as np, sys, re
import skp_oku
def yukle(ad):
    r = pickle.load(open("ara/%s.pkl" % ad, "rb")); return r
def ust_grup(f):
    p = f["yol"].split("/"); return p[1] if len(p) > 1 else ""
def sec(r, ad):
    Y = r["yuzler"]
    if ad.startswith("08"):
        Y = [f for f in Y if np.vstack(f["halkalar"]).mean(0)[1] < 2500]
        W = [f for f in Y if re.match(r"D\d", ust_grup(f))]
        T = [f for f in Y if re.match(r"MK\d", ust_grup(f))]
    else:
        W = [f for f in Y if f["katman"] == "LCAD_Wall"]
        T = [f for f in Y if f["katman"] in ("LCAD_Truss", "LCAD_Roof")]
    return W, T
def kutu(fs):
    P = np.vstack([h for f in fs for h in f["halkalar"]]); return P.min(0), P.max(0)
def duzlemler(T, min_alan=30.0):
    """Eğimli yüzleri (yön, eğim, düzlem sabiti) kümelerine ayırır; alan cm2."""
    K = collections.defaultdict(float); ornek = {}
    for f in T:
        A, n = skp_oku.yuz_alani(f)
        if A < min_alan: continue
        if n[2] < 0: n = -n
        yat = np.hypot(n[0], n[1])
        if n[2] < 0.3 or yat < 0.05: continue
        s = yat / n[2]
        yon = (round(n[0]/yat, 2), round(n[1]/yat, 2))
        p0 = f["halkalar"][0][0]
        # düzlem: z = z0 - s * (yon . (xy - xy0))  -> sabit c = z + s*(yon.xy)
        c = p0[2] + s * (yon[0]*p0[0] + yon[1]*p0[1])
        key = (yon, round(100*s, 1), round(c, 0))
        K[key] += A; ornek[key] = f
    return K
if __name__ == "__main__":
    ad = sys.argv[1]; r = yukle(ad); W, T = sec(r, ad)
    wmn, wmx = kutu(W); tmn, tmx = kutu(T)
    print("duvar kutu", np.round(wmn,1), np.round(wmx,1), "olcu", np.round(wmx-wmn,1))
    print("çatı  kutu", np.round(tmn,1), np.round(tmx,1), "olcu", np.round(tmx-tmn,1))
    K = duzlemler(T)
    # yön + eğim başına en üst düzlem (c en büyük) ve toplam alan
    G = collections.defaultdict(list)
    for (yon, s, c), A in K.items(): G[(yon, s)].append((c, A))
    print("yön(aşağı doğru) eğim%  | toplam alan m2 | en üst düzlemin sabiti c | saçak ucunda z | duvar dış yüzünde z | karşı düzlemle mahya z")
    satir = []
    for (yon, s), L in G.items():
        Atop = sum(a for _, a in L)
        if Atop < 3000: continue
        cmax = max(c for c, a in L if a > 200)
        satir.append((Atop, yon, s, cmax))
    satir.sort(reverse=True)
    ust = {}
    for Atop, yon, s, cmax in satir[:12]:
        # saçak ucu: yön boyunca en uzak çatı noktası; duvar dış yüzü: aynı yönde duvar kutusunun sınırı
        if abs(yon[0]) > 0.99: uc = tmx[0] if yon[0] > 0 else tmn[0]; dv = wmx[0] if yon[0] > 0 else wmn[0]; d_uc = yon[0]*uc; d_dv = yon[0]*dv
        elif abs(yon[1]) > 0.99: uc = tmx[1] if yon[1] > 0 else tmn[1]; dv = wmx[1] if yon[1] > 0 else wmn[1]; d_uc = yon[1]*uc; d_dv = yon[1]*dv
        else: d_uc = d_dv = None
        z_uc = cmax - s/100*d_uc if d_uc is not None else None
        z_dv = cmax - s/100*d_dv if d_dv is not None else None
        ust[(yon, s)] = cmax
        print("  %-14s %5.1f | %8.2f | c=%8.1f | %s | %s" % (yon, s, Atop/1e4, cmax, "%.1f" % z_uc if z_uc is not None else "-", "%.1f" % z_dv if z_dv is not None else "-"))
    # karşılıklı düzlem çiftlerinin kesişimi (mahya)
    for (yon, s), c in ust.items():
        karsi = ((-yon[0] if yon[0] else 0.0, -yon[1] if yon[1] else 0.0), s)
        for (y2, s2), c2 in ust.items():
            if s2 == s and abs(y2[0]+yon[0]) < 0.02 and abs(y2[1]+yon[1]) < 0.02 and (yon[0] > 0 or yon[1] > 0):
                # z = c - s*d ; z = c2 + s*d  -> z = (c+c2)/2 ; d = (c-c2)/(2s)
                print("  mahya: yön %s eğim %.1f -> z=%.1f, konum d=%.1f" % (yon, s, (c+c2)/2, (c-c2)/(2*s/100)))
