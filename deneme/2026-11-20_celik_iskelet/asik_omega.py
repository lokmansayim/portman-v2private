"""Çelik iskelete aşık ve tavan omegası ekler: prefabrik mantığıyla, bu ev için istisna (Lokman, 20 Kasım 2026).

Kural değerleri depodaki kural dosyalarından okunur:
- Aşık (`kurallar/yerlesim/prefabrik.json › asik_sirasi`, karar C): her çatı yüzünde ilk sıra mahyada, sonra eğik
  boyca 60 cm arayla; saçağa 30 cm'den az kalan sıra konmaz, saçakta bir sıra; sıra 410'luk tam parçalara bölünür.
- Tavan omegası, ters tavan (`tavan_omegasi_yerlesimi`, karar B): her tavan gözünde hat odanın başlangıç (x ya da y
  küçük) yüzünden başlar, 60 cm arayla, makaslara dik; karşı yüze 10 cm'den yakın hat konmaz; 365'lik tam parçalar.
  Kiriş gözü böler; çatı panelli bölümde omega yok (kitap › tavan_omegasi_dizilim).
Kesitler montaj rehberinden (`araclar/paket/rehber/sahne.js`): aşık OMEGA_UP 87 × 30 mm, üst 35, kanatlar makasın
üst başlığında; tavan omegası OMEGA_DN 110 × 35 mm, üst 65, kanatlar alt başlığın altında, şapka aşağı. Sac 1 mm.
Çatı düzlemleri, mahya kenarı ve odalar iskeletin kendisinden ölçülür; iskelet GLB'si değişmez.

Varsayımlar (bu evde):
- Kalkan saçağı 30 cm. Kaynak: paftadaki "Saçak Çıkması 30 cm"; aşık paftasının 1039 ve 853'ü bununla tutuyor.
- İlk hat ve mahya sırası profil yarı eniyle içeri alınır; profil duvara ya da öteki yüze girmez.
- Parçalar sıranın ve hattın arka (y büyük) ya da sol (x küçük) ucundan başlar.
- Duvar ekseni hattı yok. Kural 60'lık ve 100'lük iç duvarı yazıyor; bu evin iç duvarı 80'lik çelik.

Kullanım: python asik_omega.py celik_iskelet_90m2.glb celik_iskelet_90m2_asik_omega.glb [--plan plan.png] [--ozet ozet.json]
"""
import argparse, collections, json, math, os, struct, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iskelet_glb import glb_yaz

KOK = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
KALKAN_SACAGI = 0.30
SAC = 0.001
KIRIS_ALT = 2.60                                    # m; bundan aşağı inen makas parçası kiriştir, tavan gözünü böler
OMEGA_UP = [(-4.35, 0.05), (-2.5, 0.05), (-1.75, 2.95), (1.75, 2.95), (2.5, 0.05), (4.35, 0.05)]      # cm, aşık
OMEGA_DN = [(-5.5, -0.05), (-3.25, -0.05), (-3.25, -3.45), (3.25, -3.45), (3.25, -0.05), (5.5, -0.05)]  # cm, tavan omegası


def kurallar():
    js = lambda yol: json.load(open(os.path.join(KOK, yol), encoding='utf-8'))
    kitap = js('kurallar/liste/kurallar.json'); pf = js('kurallar/liste/prefabrik.json')['kurallar']
    yer = js('kurallar/yerlesim/prefabrik.json')['kurallar']
    return {'asik_aralik': kitap['asik']['aralik_m']['deger'],
            'asik_parca': kitap['parca_boyu_m']['asik']['deger'] - pf['asik_aday']['deger']['pay_m'],
            'sacak_esigi': pf['asik_sacak_esigi_m']['deger'],
            'asik_en_kisa': yer['asik_sirasi']['en_kisa_cm']['deger'] / 100,
            'omega_aralik': kitap['tavan_omegasi_aralik_m']['deger'],
            'omega_parca': kitap['parca_boyu_m']['tavan_omegasi']['deger'] - pf['tavan_omegasi']['deger']['pay_m'],
            'omega_en_kisa': yer['tavan_omegasi_yerlesimi']['en_kisa_cm']['deger'] / 100}


def glb_oku(yol):
    b = open(yol, 'rb').read(); n = struct.unpack_from('<I', b, 12)[0]
    g = json.loads(b[20:20 + n]); B = b[20 + n + 8:]
    def dizi(i, tip, k):
        a = g['accessors'][i]; v = g['bufferViews'][a['bufferView']]
        d = np.frombuffer(B, tip, a['count'] * k, v['byteOffset'])
        return d.reshape(-1, k) if k > 1 else d
    zy = lambda A: np.c_[A[:, 0], -A[:, 2], A[:, 1]].astype(float)            # GLB Y-yukarı -> Z-yukarı
    out = []
    for nd in g['nodes']:
        if 'mesh' not in nd:
            continue
        pr = g['meshes'][nd['mesh']]['primitives'][0]
        out.append({'ad': nd['name'], 'kat': nd['extras']['katman'], 'P': zy(dizi(pr['attributes']['POSITION'], np.float32, 3)),
                    'N': zy(dizi(pr['attributes']['NORMAL'], np.float32, 3)), 'I': dizi(pr['indices'], np.uint32, 1).astype(np.int64)})
    return out


def duzlem_ekseni(P, ince=0.09):
    e = P.max(0) - P.min(0)
    return 'y' if e[1] < ince <= e[0] else 'x' if e[0] < ince <= e[1] else None


def olc(parcalar):
    """Çatı ölçüleri iskeletten: ana çatı, ön makaslar, çatı paneli, veranda çatısı, mahya kenarı, tavan kotu."""
    mk = [p for p in parcalar if p['kat'] == 'Makas']
    tam = [p['P'] for p in mk if duzlem_ekseni(p['P']) == 'y' and np.ptp(p['P'][:, 0]) > 9]
    A = np.vstack(tam)
    zr = A[:, 2].max(); xr = float(A[A[:, 2] > zr - 0.005][:, 0].mean())
    xl, xg = A[:, 0].min(), A[:, 0].max()
    ze = float(np.mean([P[np.abs(P[:, 0] - P[:, 0].min()) < 0.03][:, 2].max() for P in tam]))
    on = np.vstack([p['P'] for p in mk if duzlem_ekseni(p['P']) == 'y' and 5 < np.ptp(p['P'][:, 0]) < 9])
    pan = np.vstack([p['P'] for p in parcalar if p['kat'] == 'Cati_paneli'])
    ust = [(float(p['P'][:, 0].mean()), float(p['P'][:, 2].max())) for p in parcalar
           if p['kat'] == 'Cati_paneli' and duzlem_ekseni(p['P']) == 'x']           # mahyaya paralel üst parçalar
    xs = np.array(ust); orta = xs[xs[:, 1].argmax(), 0]
    sol_, sag_ = xs[xs[:, 0] < orta - 0.1], xs[xs[:, 0] > orta + 0.1]
    ms, cs = np.polyfit(sol_[:, 0], sol_[:, 1], 1); mg, cg = np.polyfit(sag_[:, 0], sag_[:, 1], 1)
    pmx = (cg - cs) / (ms - mg)
    ver = [p['P'] for p in mk if duzlem_ekseni(p['P']) == 'x' and np.ptp(p['P'][:, 1]) > 2 and p['P'][:, 1].max() < -2.7]
    V = np.vstack(ver)
    vt_y, ve_y = V[:, 1].max(), V[:, 1].min()
    vt_z = float(np.mean([P[np.abs(P[:, 1] - P[:, 1].max()) < 0.03][:, 2].max() for P in ver]))
    ve_z = float(np.mean([P[np.abs(P[:, 1] - P[:, 1].min()) < 0.03][:, 2].max() for P in ver]))
    cap = [p['P'] for p in mk if p['P'][:, 0].min() > 3.0 and p['P'][:, 1].min() < -4.9 and np.ptp(p['P'][:, 0]) > 1]
    assert len(cap) == 1, f'mahya kenarı çaprazı bulunamadı ({len(cap)})'
    C = cap[0]
    yat = [t for p in mk if duzlem_ekseni(p['P']) == 'y' for t in p['P'][p['I'].reshape(-1, 3)] if np.ptp(t[:, 2]) < 0.002]
    tavan = collections.Counter(round(float(t[0, 2]), 3) for t in yat).most_common(1)[0][0]
    m = (zr - ze) / (xr - xl)
    return {'mahya_x': xr, 'mahya_z': float(zr), 'sacak_z': ze, 'sol_x': float(xl), 'sag_x': float(xg), 'egim': m,
            'arka_y': float(A[:, 1].max()), 'on_makas_x': float(on[:, 0].min()), 'on_makas_y': float(on[:, 1].min()),
            'panel_on_y': float(pan[:, 1].min()), 'panel_mahya_x': float(pmx), 'panel_mahya_z': float(ms * pmx + cs),
            'panel_sag_egim': float(-mg), 'panel_sag_c': float(cg), 'panel_x': float(pan[:, 0].max()), 'panel_arka_y': float(pan[:, 1].max()),
            'ver_ust_y': float(vt_y), 'ver_ust_z': vt_z, 'ver_sacak_y': float(ve_y), 'ver_sacak_z': ve_z, 'ver_sol_x': float(V[:, 0].min()),
            'mahya_kenari': ((float(C[:, 0].min()), float(C[:, 1].max())), (float(C[:, 0].max()), float(C[:, 1].min()))),
            'tavan_z': tavan}


def kalin(profil, t_cm):
    """Profil çizgisini sac kalınlığıyla kapalı çokgene çevirir (bir yana ofset)."""
    P = np.array(profil, float); n = len(P); Q = np.zeros_like(P)
    for i in range(n):
        a, b = P[max(i - 1, 0)], P[min(i + 1, n - 1)]
        d = (b - a) / np.linalg.norm(b - a); Q[i] = P[i] + t_cm * np.array([-d[1], d[0]])
    return P / 100, Q / 100


def profil_mesh(profil, p0, p1, u, v):
    """Profili p0'dan p1'e çeker; u: kesitin enine ekseni, v: yukarı ekseni (dünya, birim). Düz gölgeli üçgenler."""
    A, B = kalin(profil, SAC * 100)
    ring2 = np.r_[A, B[::-1]]                                           # kapalı kesit
    w = lambda q, o: o + q[0] * u + q[1] * v
    P, N, I = [], [], []
    def yuz(*k):
        k = [np.asarray(x) for x in k]; nn = np.cross(k[1] - k[0], k[2] - k[0]); nn = nn / (np.linalg.norm(nn) or 1)
        for tri in ((0, 1, 2), (0, 2, 3)) if len(k) == 4 else ((0, 1, 2),):
            I.extend(range(len(P), len(P) + 3)); P.extend(k[j] for j in tri); N.extend([nn] * 3)
    m = len(ring2)
    for i in range(m):
        a, b = ring2[i], ring2[(i + 1) % m]
        yuz(w(a, p0), w(b, p0), w(b, p1), w(a, p1))
    for i in range(len(A) - 1):                                         # uç kapakları
        for o, ters in ((p0, True), (p1, False)):
            k = [w(A[i], o), w(A[i + 1], o), w(B[i + 1], o), w(B[i], o)]
            yuz(*(k[::-1] if ters else k))
    return np.array(P), np.array(N), np.array(I)


def parcala(a0, a1, tam, en_kisa, sondan):
    out, kalan = [], a1 - a0
    u = a1 if sondan else a0
    while kalan > tam + 1e-6:
        out.append((u - tam, u) if sondan else (u, u + tam)); u = u - tam if sondan else u + tam; kalan -= tam
    if kalan >= en_kisa - 1e-6:
        out.append((u - kalan, u) if sondan else (u, u + kalan))
    return out


def asiklar(K, O):
    """Dört açık çatı yüzü: ana çatının sol ve sağ yüzü ve çatı panelinin sağ yüzü (sıralar y boyunca), veranda çatısı
    (sıralar x boyunca). Panelin sağ yüzü yalnız ana çatının ön kalkanının önünde açıktadır ve veranda çatısıyla derede
    buluşur (Lokman, 20 Kasım 2026: "şuan gördüğün yerde de aşık olması gerekiyor"; aşık paftasının 216, 216, 184,
    102'si ve 495'lik paralelkenarı). Veranda sıraları soldan dereye kadar uzanır."""
    out = []; ozet = collections.Counter(); boy = collections.Counter()
    yari = 0.0435
    (hx0, hy0), (hx1, hy1) = O['mahya_kenari']
    hip_y = lambda x: hy0 + (x - hx0) * (hy1 - hy0) / (hx1 - hx0)
    hip_x = lambda y: hx0 + (y - hy0) * (hx1 - hx0) / (hy1 - hy0)
    def siralar(L):
        s = []; k = 0
        while L - k * K['asik_aralik'] >= K['sacak_esigi'] - 1e-6:
            s.append(max(k * K['asik_aralik'], yari)); k += 1
        return s + [L - yari]
    m = O['egim']; ca = 1 / math.sqrt(1 + m * m); sa = m * ca
    arka = O['arka_y'] + KALKAN_SACAGI
    for yuz, isaret, xe in (('sol', -1, O['sol_x']), ('sag', 1, O['sag_x'])):
        L = abs(xe - O['mahya_x']) / ca
        n = np.array([-isaret * sa, 0, ca]); d = np.array([isaret * ca, 0, -sa])
        for s in siralar(L):
            x = O['mahya_x'] + isaret * s * ca; z = O['mahya_z'] - s * sa
            if yuz == 'sol':
                on = (O['panel_on_y'] if x < O['on_makas_x'] else O['on_makas_y']) - KALKAN_SACAGI
            else:
                on = O['on_makas_y'] - KALKAN_SACAGI
                if x > hx0:
                    on = min(on, hip_y(x))
            ozet[yuz] += 1; boy[yuz] += arka - on
            for a, b in parcala(on, arka, K['asik_parca'], K['asik_en_kisa'], sondan=True):
                out.append((yuz, profil_mesh(OMEGA_UP, np.array([x, a, z]), np.array([x, b, z]), d, n)))
    # veranda çatısı ve çatı panelinin sağ yüzü bir derede buluşur: z_ver(y) = z_panel(x)
    mv = (O['ver_ust_z'] - O['ver_sacak_z']) / (O['ver_ust_y'] - O['ver_sacak_y']); cb = 1 / math.sqrt(1 + mv * mv); sb = mv * cb
    z_ver = lambda y: O['ver_sacak_z'] + (y - O['ver_sacak_y']) * mv
    dere_x = lambda y: (O['panel_sag_c'] - z_ver(y)) / O['panel_sag_egim']           # panelin sağ yüzü: z = c − m·x
    dere_y = lambda x: O['ver_sacak_y'] + (O['panel_sag_c'] - O['panel_sag_egim'] * x - O['ver_sacak_z']) / mv
    # çatı panelinin sağ yüzü: ana çatının ön kalkanının önünde açıkta; sıralar y boyunca, ön saçaktan kalkana ya da dereye
    mp = O['panel_sag_egim']; cp_ = 1 / math.sqrt(1 + mp * mp); sp_ = mp * cp_
    L = (O['panel_x'] - O['panel_mahya_x']) / cp_
    n = np.array([sp_, 0, cp_]); d = np.array([cp_, 0, -sp_])
    for s in siralar(L):
        x = O['panel_mahya_x'] + s * cp_; z = O['panel_mahya_z'] - s * sp_
        on, son = O['panel_on_y'] - KALKAN_SACAGI, min(O['on_makas_y'], dere_y(x))
        if son - on < K['asik_en_kisa']:
            continue                                                    # sıranın tamamı veranda çatısının altında
        ozet['panel_sag'] += 1; boy['panel_sag'] += son - on
        for a, b in parcala(on, son, K['asik_parca'], K['asik_en_kisa'], sondan=True):
            out.append(('panel_sag', profil_mesh(OMEGA_UP, np.array([x, a, z]), np.array([x, b, z]), d, n)))
    # veranda çatısı: sıralar x boyunca, soldan (dere) mahya kenarına
    L = (O['ver_ust_y'] - O['ver_sacak_y']) / cb
    n = np.array([0, -sb, cb]); d = np.array([0, -cb, -sb])
    for s in siralar(L):
        y = O['ver_ust_y'] - s * cb; z = O['ver_ust_z'] - s * sb
        x0, x1 = min(O['ver_sol_x'], dere_x(y)), hip_x(y)
        ozet['veranda'] += 1; boy['veranda'] += x1 - x0
        for a, b in parcala(x0, x1, K['asik_parca'], K['asik_en_kisa'], sondan=False):
            out.append(('veranda', profil_mesh(OMEGA_UP, np.array([a, y, z]), np.array([b, y, z]), np.array([0.0, 1, 0]) * 0 + d, n)))
    return out, dict(ozet), {k: round(v, 2) for k, v in boy.items()}


def raster(parcalar, x0=-5.0, y0=-5.2, R=0.02, nx=515, ny=525):
    """Plan raster (2 cm): duvarlar (0,05–2,75 m) ve tavanın belirgin altına inen makas parçaları (kiriş, kolon).
    Makasların alt başlığı tavan kotundadır (2,70); engel değildir, hattı bölmez."""
    W = np.zeros((ny, nx), bool)
    for p in parcalar:
        if p['kat'] not in ('Duvar', 'Makas'):
            continue
        for t in p['P'][p['I'].reshape(-1, 3)]:
            if p['kat'] == 'Duvar' and (t[:, 2].max() < 0.05 or t[:, 2].min() > 2.75):
                continue
            if p['kat'] == 'Makas' and t[:, 2].min() > KIRIS_ALT:
                continue
            i0, i1 = int((t[:, 0].min() - x0) / R), int((t[:, 0].max() - x0) / R)
            j0, j1 = int((t[:, 1].min() - y0) / R), int((t[:, 1].max() - y0) / R)
            W[max(j0, 0):j1 + 1, max(i0, 0):i1 + 1] = True
    h, w = W.shape; lab = np.zeros((h, w), np.int32); nl = 0
    for j0 in range(h):
        for i0 in np.nonzero(~W[j0] & (lab[j0] == 0))[0]:
            if lab[j0, i0]:
                continue
            nl += 1; yigin = [(j0, i0)]; lab[j0, i0] = nl
            while yigin:
                j, i = yigin.pop()
                for jj, ii in ((j + 1, i), (j - 1, i), (j, i + 1), (j, i - 1)):
                    if 0 <= jj < h and 0 <= ii < w and not W[jj, ii] and not lab[jj, ii]:
                        lab[jj, ii] = nl; yigin.append((jj, ii))
    dis = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    return {'W': W, 'lab': lab, 'dis': dis, 'x0': x0, 'y0': y0, 'R': R}


def omegalar(K, O, ras):
    lab, R, x0, y0 = ras['lab'], ras['R'], ras['x0'], ras['y0']
    yari = 0.055
    u_v = {'x': (np.array([1.0, 0, 0]), np.array([0, 0, 1.0])), 'y': (np.array([0, 1.0, 0]), np.array([0, 0, 1.0]))}
    out = []; gozler = []
    for l in range(1, lab.max() + 1):
        if l in ras['dis']:
            continue
        jj, ii = np.nonzero(lab == l)
        if len(jj) * R * R < 0.5:
            continue
        cx, cy = x0 + (ii.mean() + 0.5) * R, y0 + (jj.mean() + 0.5) * R
        if cx < O['panel_x'] and cy < O['panel_arka_y']:
            gozler.append({'goz': l, 'alan': round(len(jj) * R * R, 2), 'merkez': [round(cx, 2), round(cy, 2)], 'hat': 0, 'not': 'çatı paneli altında, omega yok'})
            continue
        adim = 'y' if cy < O['on_makas_y'] else 'x'                    # veranda çatısı altında hatlar x boyunca
        lo = (x0 + ii.min() * R) if adim == 'x' else (y0 + jj.min() * R)
        hi = (x0 + (ii.max() + 1) * R) if adim == 'x' else (y0 + (jj.max() + 1) * R)
        konum = []; k = 0
        while lo + k * K['omega_aralik'] <= hi - K['omega_en_kisa'] + 1e-6:
            konum.append(max(lo + k * K['omega_aralik'], lo + yari)); k += 1
        hat = 0
        for s in konum:
            if adim == 'x':
                kol = lab[:, int((s - x0) / R)] == l; a0 = y0
            else:
                kol = lab[int((s - y0) / R), :] == l; a0 = x0
            idx = np.nonzero(kol)[0]
            if not len(idx):
                continue
            kir = np.split(idx, np.nonzero(np.diff(idx) > 1)[0] + 1)
            for kk in kir:
                r0, r1 = a0 + kk[0] * R, a0 + (kk[-1] + 1) * R
                if r1 - r0 < K['omega_en_kisa']:
                    continue
                hat += 1
                eks = 'y' if adim == 'x' else 'x'
                u, v = u_v[adim]
                for a, b in parcala(r0, r1, K['omega_parca'], K['omega_en_kisa'], sondan=(eks == 'y')):
                    p0 = np.array([s, a, O['tavan_z']]) if eks == 'y' else np.array([a, s, O['tavan_z']])
                    p1 = np.array([s, b, O['tavan_z']]) if eks == 'y' else np.array([b, s, O['tavan_z']])
                    out.append((l, r1 - r0, profil_mesh(OMEGA_DN, p0, p1, u, v), (eks, s, a, b)))
        gozler.append({'goz': l, 'alan': round(len(jj) * R * R, 2), 'merkez': [round(cx, 2), round(cy, 2)], 'hat': hat,
                       'yon': 'y boyunca' if adim == 'x' else 'x boyunca', 'baslangic': round(lo, 3)})
    return out, gozler


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('iskelet'); ap.add_argument('glb'); ap.add_argument('--plan'); ap.add_argument('--ozet')
    a = ap.parse_args()
    K = kurallar(); parcalar = glb_oku(a.iskelet); O = olc(parcalar)
    A, asik_sira, asik_boy = asiklar(K, O)
    ras = raster(parcalar)
    M, gozler = omegalar(K, O, ras)
    tum = [(p['kat'], p['ad'], p['P'], p['N'], p['I']) for p in parcalar]
    tum += [('Asik', f'Asik_{yuz}_{i:03d}', *mesh) for i, (yuz, mesh) in enumerate(A)]
    tum += [('Tavan_omegasi', f'Tavan_omegasi_g{l}_{i:03d}', *mesh) for i, (l, _, mesh, _) in enumerate(M)]
    tum.sort(key=lambda t: (t[2][:, 2].min(), t[2][:, 2].max()))
    gruplar = collections.OrderedDict((k, []) for k in ('Duvar', 'Lento', 'Makas', 'Cati_paneli', 'Tavan_omegasi', 'Asik'))
    for s, (kat, ad, P, N, I) in enumerate(tum):
        gruplar[kat].append((ad, P, N, I, {'katman': kat, 'z_alt': round(float(P[:, 2].min()), 4), 'z_ust': round(float(P[:, 2].max()), 4), 'sira': s}))
    glb_yaz(a.glb, gruplar)
    oz = {'kural': {k: round(v, 4) for k, v in K.items()}, 'olcu': O, 'asik_sira': asik_sira, 'asik_sira_boyu_m': asik_boy,
          'asik_parca': len(A), 'asik_toplam_m': round(sum(asik_boy.values()), 2), 'omega_parca': len(M),
          'omega_toplam_m': round(sum(b - a_ for *_, (e, s, a_, b) in M), 2), 'gozler': gozler,
          'parca': {k: len(v) for k, v in gruplar.items()}}
    print(json.dumps({k: oz[k] for k in ('asik_sira', 'asik_sira_boyu_m', 'asik_parca', 'asik_toplam_m', 'omega_parca', 'omega_toplam_m', 'parca')}, ensure_ascii=False))
    for g_ in gozler:
        print('  göz', g_)
    if a.ozet:
        json.dump(oz, open(a.ozet, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if a.plan:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(11, 11))
        ax.imshow(np.where(ras['W'], 0.25, 1.0), origin='lower', cmap='gray', vmin=0, vmax=1,
                  extent=(ras['x0'], ras['x0'] + ras['W'].shape[1] * ras['R'], ras['y0'], ras['y0'] + ras['W'].shape[0] * ras['R']))
        for l, _, _, (e, s, a_, b) in M:
            ax.plot([s, s] if e == 'y' else [a_, b], [a_, b] if e == 'y' else [s, s], color='#1f6feb', lw=2.2, solid_capstyle='butt')
        for yuz, (P, N, I) in A:
            c = P.mean(0); e = np.ptp(P, 0)
            if e[1] > e[0]:
                ax.plot([c[0], c[0]], [P[:, 1].min(), P[:, 1].max()], color='#f28c28', lw=1.2, alpha=0.8)
            else:
                ax.plot([P[:, 0].min(), P[:, 0].max()], [c[1], c[1]], color='#f28c28', lw=1.2, alpha=0.8)
        ax.set_title(f"Mavi: tavan omegası (ters tavan) {len(M)} parça, {oz['omega_toplam_m']} m · Turuncu: aşık {len(A)} parça, {oz['asik_toplam_m']} m", fontsize=10)
        ax.set_aspect('equal'); ax.grid(alpha=0.25); plt.savefig(a.plan, dpi=80, bbox_inches='tight')
