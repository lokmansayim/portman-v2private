"""62 m² prefabrik (beşik + cumba) · 3D yazıcı için basılabilir maket (1:50).
Rehberin verisinden (data.json) iki kapalı (watertight) parça üretir:
  gövde: zemin plağı, dış ve iç duvarlar (pencere ve kapı boşluklu, dış cephede fuga olukları), köşe direkleri, veranda kolon ve kirişleri
  çatı:  ana çatı + cumba; duvar üstünden (250 cm) çatı yüzeyine kadar dolu çatı arası ve saçak taşkınlı çatı kabuğu,
         trapez hadveleri; gövdenin üstüne oturur, çıkarılınca odalar görünür.
Birim: çıktı mm (1:50 → 1 cm = 0,2 mm). Kullanım: python maket.py <data.json> <çıktı klasörü> [ölçek_payda=50] [dosya_öneki=maket62]"""
import sys, os, json, math
import numpy as np, trimesh

veri, cikti = sys.argv[1], sys.argv[2]
PAYDA = float(sys.argv[3]) if len(sys.argv) > 3 else 50
ONEK = sys.argv[4] if len(sys.argv) > 4 else 'maket62'
os.makedirs(cikti, exist_ok=True)
D = json.load(open(veri, encoding='utf-8'))
H, TB, HEEL = D['h'], D['h'] + 0.25, 10.0

def kutu(x0, x1, y0, y1, z0, z1):
    b = trimesh.creation.box(extents=(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)))
    b.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)); return b
def birlestir(L): return trimesh.boolean.union(L, engine='manifold')
def fark(a, L): return trimesh.boolean.difference([a] + L, engine='manifold')
def zarf(pts): return trimesh.convex.convex_hull(np.array(pts))

# ---------- Gövde ----------
govde = [kutu(-12, D['dis'][0] + 12, -162, D['dis'][1] + 12, -12, 0)]          # zemin plağı (veranda dahil), 12 cm
# Cephe fugası (pafta: fugalı duvar detayı): alttan 6 × 38 cm + 2 cm fuga. Maket için oluk 2,5 cm yüksek, 1,5 cm derin (1:50'de 0,5 × 0,3 mm)
FUGA = [38, 78, 118, 158, 198, 238]; FUGA_H, FUGA_D = 2.5, 1.5
for p in D['panels']:
    x0, y0, x1, y1 = p['rect']; pano = kutu(x0, x1, y0, y1, 0, H); op = p['op']; kes = []
    if op:
        a0, a1, s, top = op['a0'], op['a1'], op['s'], op['top']
        kes.append(kutu(a0, a1, y0 - 1, y1 + 1, max(s, -1), top) if p['o'] == 'h' else kutu(x0 - 1, x1 + 1, a0, a1, max(s, -1), top))
    if p['duvar'] == 'dis':   # dış yüz: binanın ortasından uzak taraf
        for f in FUGA:
            z0, z1 = f - (FUGA_H - 2) / 2, f + 2 + (FUGA_H - 2) / 2
            if p['o'] == 'h':
                yy = (y0 - 1, y0 + FUGA_D) if (y0 + y1) / 2 < D['dis'][1] / 2 else (y1 - FUGA_D, y1 + 1)
                kes.append(kutu(x0 - 0.5, x1 + 0.5, *yy, z0, z1))
            else:
                xx = (x0 - 1, x0 + FUGA_D) if (x0 + x1) / 2 < D['dis'][0] / 2 else (x1 - FUGA_D, x1 + 1)
                kes.append(kutu(*xx, y0 - 0.5, y1 + 0.5, z0, z1))
    if kes: pano = fark(pano, kes)
    govde.append(pano)
for k in D['posts']:
    x0, y0, x1, y1 = k['rect']; govde.append(kutu(x0, x1, y0, y1, 0, H))
V = D['veranda']
for x0, y0, x1, y1 in V['kolon']: govde.append(kutu(x0, x1, y0, y1, 0, H - 10))
x0, y0, x1, y1 = V['kiris_on']; govde.append(kutu(x0, x1, y0, y1, H - 10, H))
for x0, y0, x1, y1 in V['kiris']: govde.append(kutu(x0, x1, y0, y1, H - 10, H))
# Çatıyı yerine oturtan 4 köşe tırnağı: dış duvarların iç köşelerinde, duvar üstünden 15 cm (1:50'de 3 mm) yukarı; çatının altında eş cepler
TIRNAK = []
for (cx, cy, sx, sy) in ((10, 10, 1, 1), (890, 10, -1, 1), (10, 590, 1, -1), (890, 590, -1, -1)):
    TIRNAK.append(((cx, cx + sx * 30), (cy, cy + sy * 4)))
    TIRNAK.append(((cx, cx + sx * 4), (cy, cy + sy * 30)))
for (xa, xb), (ya, yb) in TIRNAK: govde.append(kutu(min(xa, xb), max(xa, xb), min(ya, yb), max(ya, yb), H - 1, H + 15))
G = birlestir(govde)

# ---------- Çatı (rehberle aynı geometri) ----------
AN = dict(L=-30, R=630, M=300, tan=108.5 / 330); CU = dict(L=-30, R=604.75, M=287.375, tan=108.5 / 317.375)
for R in (AN, CU): R['th'] = math.atan(R['tan']); R['cos'] = math.cos(R['th'])
VSL = lambda x: -30 + (x + 30) * (330 / 317.375)
VSR = lambda x: -30 + (604.75 - x) * (330 / 317.375)
YUZ = {
    'MB':  dict(E=(0, 630), d=(0, -1), R=AN, poly=[(-30.2, 300), (930.2, 300), (930.2, 631.3), (-30.2, 631.3)]),
    'MFR': dict(E=(0, -30), d=(0, 1), R=AN, poly=[(604.75 + 1.3 * 317.375 / 330, -31.3), (930.2, -31.3), (930.2, 300), (287.375, 300)]),
    'MFL': dict(E=(0, -30), d=(0, 1), R=AN, poly=[(-30.2, VSL(-30.2)), (-30.2, 300), (287.375, 300)]),
    'CL':  dict(E=(-30, 0), d=(1, 0), R=CU, poly=[(-31.3, -180.2), (287.375, -180.2), (287.375, 300), (-31.3, VSL(-31.3))]),
    'CR':  dict(E=(604.75, 0), d=(-1, 0), R=CU, poly=[(287.375, -180.2), (606.05, -180.2), (606.05, VSR(606.05)), (287.375, 300)]),
}
def zs(Y, x, y): return TB + HEEL + ((x - Y['E'][0]) * Y['d'][0] + (y - Y['E'][1]) * Y['d'][1]) * Y['R']['tan']   # aşık oturma yüzü
KAL = 4.0   # çatı kabuğu: aşık oturma yüzünden trapez levhasına ~3,4 cm + 0,6 (eğime dik; OSB ve nem bariyeri yok); hadveler bunun üstünde
def kirp(P, x0, x1, y0, y1):   # dışbükey çokgeni dikdörtgenle kırp
    def k(P, f, ic):
        out = []
        for i in range(len(P)):
            p, q = P[i], P[(i + 1) % len(P)]; a, b = f(p), f(q)
            if a >= 0: out.append(p)
            if (a >= 0) != (b >= 0): t = a / (a - b); out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
        return out
    for f in (lambda p: p[0] - x0, lambda p: x1 - p[0], lambda p: p[1] - y0, lambda p: y1 - p[1]):
        P = k(P, f, None)
        if len(P) < 3: return None
    return P
cati = []
TABAN = [(0, 900, 0, 600), (0, 574.75, -150, 0)]   # bina ve veranda izdüşümü: çatı arası bunun üstünde dolu
for ad, Y in YUZ.items():
    c = Y['R']['cos']
    cx = sum(p[0] for p in Y['poly']) / len(Y['poly']); cy = sum(p[1] for p in Y['poly']) / len(Y['poly'])
    gen = [(x + (x - cx) / math.hypot(x - cx, y - cy) * 0.6, y + (y - cy) / math.hypot(x - cx, y - cy) * 0.6) for x, y in Y['poly']]   # komşu yüzle 0,6 cm örtüşsün: dere ve mahya hattında ince şerit kalmaz
    kenar = [(x, y) for x, y in gen]
    cati.append(zarf([(x, y, zs(Y, x, y)) for x, y in kenar] + [(x, y, zs(Y, x, y) + KAL / c) for x, y in kenar]))   # kabuk
    for r in TABAN:
        Q = kirp(gen, *r)
        if Q: cati.append(zarf([(x, y, H) for x, y in Q] + [(x, y, zs(Y, x, y) + 0.5) for x, y in Q]))   # çatı arası (dolu)
# Trapez hadveleri (27/200): ana çatıda eğim boyunca (x'te ~20 cm aralık), cumbada y'de 20 cm; yüz çokgenine kırpılır
def hadve(Y, u, eksen):
    c = Y['R']['cos']; P = Y['poly']; xs = []
    for i in range(len(P)):
        p, q = P[i], P[(i + 1) % len(P)]; a, b = (p[0], q[0]) if eksen == 'x' else (p[1], q[1])
        if a != b and (a - u) * (b - u) <= 0:
            t = (u - a) / (b - a); xs.append((p[1] + (q[1] - p[1]) * t) if eksen == 'x' else (p[0] + (q[0] - p[0]) * t))
    if len(xs) < 2: return None
    v0, v1 = min(xs) + 6, max(xs) - 6   # uçlar yüz kenarından (dere hattında açılı) içeride kalsın
    if v1 - v0 < 15: return None
    w0, w1, h = 3.7, 2.1, 2.7   # 27/200: taban 74, tepe 42 mm, hadve 27 mm
    pts = []
    for v in (v0, v1):
        for du, dh in ((-w0, 0), (w0, 0), (-w1, h), (w1, h)):
            x, y = (u + du, v) if eksen == 'x' else (v, u + du)
            pts.append((x, y, zs(Y, x, y) + (KAL - 0.6 + dh) / c))
    return zarf(pts)
RX = [-30.2 + 4.5 + k * (960.4 - 9) / 48 for k in range(49)]
RY = [y for y in (-180.2 + 4.5 + k * 20 for k in range(25)) if y < 300]
for ad, Y in YUZ.items():
    for u in (RY if ad[0] == 'C' else RX):
        h = hadve(Y, u, 'y' if ad[0] == 'C' else 'x')
        if h is not None: cati.append(h)
C = birlestir(cati)
BOS = 1.5   # 1:50'de 0,3 mm boşluk
C = fark(C, [kutu(min(xa, xb) - BOS, max(xa, xb) + BOS, min(ya, yb) - BOS, max(ya, yb) + BOS, H - 1, H + 15 + BOS) for (xa, xb), (ya, yb) in TIRNAK])

# ---------- Ölçek ve dışa aktarma (mm) ----------
s = 10.0 / PAYDA
for m in (G, C): m.apply_scale(s)
import manifold3d as m3
def temizle(t, tol=0.005):   # mm altı kıymıkları kaynat: STL'de (float32) kapalı kalsın
    M = m3.Manifold(m3.Mesh(vert_properties=np.asarray(t.vertices, dtype=np.float32), tri_verts=np.asarray(t.faces, dtype=np.uint32))).simplify(tol)
    o = M.to_mesh(); return trimesh.Trimesh(o.vert_properties[:, :3], o.tri_verts)
G, C = temizle(G), temizle(C)
ad = f'1-{int(PAYDA)}'
G.export(os.path.join(cikti, f'{ONEK}_maket_{ad}_govde.stl'))
C.export(os.path.join(cikti, f'{ONEK}_maket_{ad}_cati.stl'))
birlikte = trimesh.util.concatenate([G, C]); birlikte.export(os.path.join(cikti, f'{ONEK}_maket_{ad}_birlesik.stl'))
for n, m in (('gövde', G), ('çatı', C)):
    e = m.bounds[1] - m.bounds[0]
    tekrar = trimesh.load(os.path.join(cikti, f'{ONEK}_maket_{ad}_{"govde" if n == "gövde" else "cati"}.stl'))
    assert tekrar.is_watertight, f'{n}: STL dönüşünde kapalı değil'
    print(f'{n}: kapalı={m.is_watertight} hacim={m.volume / 1000:.1f} cm³ boyut={e[0]:.1f} × {e[1]:.1f} × {e[2]:.1f} mm üçgen={len(m.faces)}')
