"""GLB'yi geri okur ve "alttan üste yazdırma" önizlemesini çizer (Blender'sız, matplotlib).

Her karede kesit yüksekliğinin altındaki üçgenler gri, kesite en yakın 15 cm turuncu (yeni basılan katman).
Kullanım: python onizleme.py celik_iskelet_90m2.glb onizleme.png
"""
import json, struct, sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


def glb_oku(yol):
    b = open(yol, 'rb').read()
    n_js = struct.unpack_from('<I', b, 12)[0]
    g = json.loads(b[20:20 + n_js]); bin_ = b[20 + n_js + 8:]
    def dizi(i, tip, n):
        a = g['accessors'][i]; v = g['bufferViews'][a['bufferView']]
        return np.frombuffer(bin_, tip, a['count'] * n, v['byteOffset']).reshape(-1, n) if n > 1 else np.frombuffer(bin_, tip, a['count'], v['byteOffset'])
    U = []
    for m in g['meshes']:
        pr = m['primitives'][0]
        P = dizi(pr['attributes']['POSITION'], np.float32, 3); I = dizi(pr['indices'], np.uint32, 1)
        P = np.c_[P[:, 0], -P[:, 2], P[:, 1]]                    # Y-yukarı -> Z-yukarı
        U.append(P[I.reshape(-1, 3)])
    return np.concatenate(U)


def kirp(ucgenler, alt, ust):
    """Üçgenleri alt <= z <= ust bandına kırpar (her düzlem için Sutherland–Hodgman)."""
    cikti = []
    for t in ucgenler:
        poli = list(t)
        for z0, isaret in ((ust, 1), (alt, -1)):
            yeni = []
            for i in range(len(poli)):
                a, b = poli[i], poli[(i + 1) % len(poli)]
                ia, ib = isaret * (a[2] - z0) <= 0, isaret * (b[2] - z0) <= 0
                if ia:
                    yeni.append(a)
                if ia != ib:
                    yeni.append(a + (b - a) * (z0 - a[2]) / (b[2] - a[2]))
            poli = yeni
            if len(poli) < 3:
                break
        if len(poli) >= 3:
            cikti.append(np.array(poli))
    return cikti


T = glb_oku(sys.argv[1])
zmax = T[:, :, 2].max(); tz = T[:, :, 2].min(1)
fig = plt.figure(figsize=(16, 4.6))
for j, oran in enumerate((0.25, 0.5, 0.75, 1.0)):
    H = oran * zmax + 1e-6
    ax = fig.add_subplot(1, 4, j + 1, projection='3d')
    aday = T[tz <= H]
    eski = kirp(aday, -1.0, H - 0.15); yeni = kirp(aday, H - 0.15, H)
    ax.add_collection3d(Poly3DCollection(eski, facecolor='#9aa4ad', edgecolor='#59636c', linewidths=0.08))
    if len(yeni):
        ax.add_collection3d(Poly3DCollection(yeni, facecolor='#ff8a1f', edgecolor='#ff8a1f', linewidths=0.2))
    r = 5.6
    ax.set_xlim(-r, r); ax.set_ylim(-r, r); ax.set_zlim(0, 2 * r * 0.45)
    ax.set_box_aspect((1, 1, 0.45)); ax.view_init(elev=24, azim=-58 + 12 * j); ax.set_axis_off()
    ax.set_title(f'%{int(oran * 100)} · {H:.2f} m', fontsize=10)
fig.suptitle('Çelik iskelet · 90 m² · alttan üste yazdırma önizlemesi (turuncu: yeni basılan 15 cm)', fontsize=11)
plt.tight_layout(); plt.savefig(sys.argv[2], dpi=110)
print('yazıldı:', sys.argv[2], '· üçgen', len(T), '· yükseklik', round(float(zmax), 3), 'm')
