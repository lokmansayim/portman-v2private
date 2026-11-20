"""Çelik modelin SKP'sinden çelik iskeleti GLB olarak çıkarır (Blender gerekmez).

SKP'deki model içe aktarılmış bir DXF bileşeni; katmanlar BCAD_Wall, BCAD_Truss, BCAD_Roof, BCAD_Header.
Yüzler ortak kenarla birbirine bağlanınca bir parça olur (çoğunlukla bir çubuk; birbirine değen birkaç çubuk
tek parça kalabilir). Her parça GLB'de ayrı bir düğümdür ve katman grubunun altındadır:
Duvar, Makas, Cati_paneli, Lento. Birim metre. Taban ortası (0, 0, 0). GLB Y-yukarı yazılır; Blender
içe aktarınca Z-yukarı olur. Her düğümün `extras`'ında katman, z_alt, z_ust ve sira (alttan üste) var;
Blender bunları özel özellik olarak okur.

Kullanım (openskp 1.3.0 ve numpy): python iskelet_glb.py <çelik model>.skp celik_iskelet.glb [--ozet ozet.json]
"""
import argparse, collections, json, struct
import numpy as np

INC = 0.0254                                   # SKP içi inç -> m
KATMAN = {'BCAD_Wall': 'Duvar', 'BCAD_Truss': 'Makas', 'BCAD_Roof': 'Cati_paneli', 'BCAD_Header': 'Lento'}
KIMLIK = [1.0, 0, 0, 0, 1.0, 0, 0, 0, 1.0, 0, 0, 0, 1.0]


def yuzler(yol):
    from openskp import _core
    p = _core.full_parse(yol); defs = p['defs_dict']; lid = p['layer_id_to_name']
    V = {}; F = []
    def yuru(did, M, ad, kat):
        d = defs.get(did)
        if not d:
            return
        b = d['builder']
        for vid, v in b.vertices.items():
            V[(ad, vid)] = np.array(_core.transform_point(v, M), float) * INC
        for f in b.faces.values():
            halkalar = []; kenarlar = set()
            for loop in f['loops']:
                h = []
                for (eid, yon) in loop:
                    e = b.edges.get(eid)
                    if e is None:
                        h = None; break
                    h.append((ad, e[0] if yon == 1 else e[1])); kenarlar.add((ad, eid))
                if h and len(h) >= 3:
                    halkalar.append(h)
            if halkalar:
                F.append({'kat': lid.get(f.get('layer'), kat), 'halka': halkalar, 'kenar': kenarlar})
        for n, inst in enumerate(b.instances):
            k = lid.get(inst.get('layer'), kat) if inst.get('layer') else kat
            yuru(inst['ref_idx'], _core.multiply_matrices(M, inst['matrix']), f'{ad}/{n}', k)
    yuru('ROOT', KIMLIK, '', 'Layer0')
    return V, F


def parcalar(F):
    kenar_yuz = collections.defaultdict(list)
    for i, f in enumerate(F):
        for e in f['kenar']:
            kenar_yuz[e].append(i)
    par = list(range(len(F)))
    def bul(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for ys in kenar_yuz.values():
        if len(ys) == 2:                       # iki yüzün paylaştığı kenar: aynı profilin katlanma kenarı
            par[bul(ys[0])] = bul(ys[1])
    g = collections.defaultdict(list)
    for i in range(len(F)):
        g[bul(i)].append(i)
    return list(g.values())


def ucgenle(V, f):
    from openskp import _core
    P = np.array([V[k] for k in f['halka'][0]])
    n = np.zeros(3)
    for i in range(len(P)):
        n += np.cross(P[i], P[(i + 1) % len(P)])
    tri = _core.triangulate_face_3d({k: V[k] for h in f['halka'] for k in h}, f['halka'], n)
    nn = np.linalg.norm(n)
    return tri, (n / nn if nn > 1e-12 else np.array([0, 0, 1.0]))


def glb_yaz(yol, gruplar):
    """gruplar: {grup adı: [(ad, konum[N,3], normal[N,3], indis[M], extras)]}. Konumlar Z-yukarı m."""
    ikili = bytearray(); bv = []; acc = []; meshes = []; nodes = []; kok = []
    def ekle(dizi, hedef, tur, tip, bilesen):
        while len(ikili) % 4:
            ikili.append(0)
        bas = len(ikili); ikili.extend(dizi.tobytes())
        bv.append({'buffer': 0, 'byteOffset': bas, 'byteLength': dizi.nbytes, 'target': hedef})
        a = {'bufferView': len(bv) - 1, 'componentType': tur, 'count': len(dizi), 'type': tip}
        if tip == 'VEC3':
            a['min'] = dizi.min(0).tolist(); a['max'] = dizi.max(0).tolist()
        acc.append(a)
        return len(acc) - 1
    yy = lambda P: np.ascontiguousarray(np.c_[P[:, 0], P[:, 2], -P[:, 1]], dtype=np.float32)   # Z-yukarı -> Y-yukarı
    for grup, uyeler in gruplar.items():
        cocuk = []
        for ad, P, N, I, ex in uyeler:
            a_p = ekle(yy(P), 34962, 5126, 'VEC3', 3)
            a_n = ekle(yy(N), 34962, 5126, 'VEC3', 3)
            a_i = ekle(np.ascontiguousarray(I, dtype=np.uint32), 34963, 5125, 'SCALAR', 1)
            meshes.append({'name': ad, 'primitives': [{'attributes': {'POSITION': a_p, 'NORMAL': a_n}, 'indices': a_i, 'material': 0}]})
            nodes.append({'name': ad, 'mesh': len(meshes) - 1, 'extras': ex}); cocuk.append(len(nodes) - 1)
        nodes.append({'name': grup, 'children': cocuk}); kok.append(len(nodes) - 1)
    while len(ikili) % 4:
        ikili.append(0)
    gltf = {'asset': {'version': '2.0', 'generator': 'Portman iskelet_glb.py'}, 'scene': 0,
            'scenes': [{'name': 'Celik_iskelet', 'nodes': kok}], 'nodes': nodes, 'meshes': meshes,
            'materials': [{'name': 'Galvaniz', 'doubleSided': True,
                           'pbrMetallicRoughness': {'baseColorFactor': [0.78, 0.80, 0.82, 1.0], 'metallicFactor': 0.9, 'roughnessFactor': 0.35}}],
            'accessors': acc, 'bufferViews': bv, 'buffers': [{'byteLength': len(ikili)}]}
    js = json.dumps(gltf, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    js += b' ' * (-len(js) % 4)
    with open(yol, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(ikili)))
        f.write(struct.pack('<II', len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack('<II', len(ikili), 0x004E4942)); f.write(bytes(ikili))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('skp'); ap.add_argument('glb'); ap.add_argument('--ozet')
    a = ap.parse_args()
    V, F = yuzler(a.skp)
    G = parcalar(F)
    tum = np.array(list(V.values())); mn, mx = tum.min(0), tum.max(0)
    kayma = np.array([(mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, mn[2]])     # taban ortası 0
    ham = []
    for ys in G:
        kat = KATMAN.get(collections.Counter(F[i]['kat'] for i in ys).most_common(1)[0][0], 'Diger')
        P = []; N = []; I = []
        for i in ys:
            tri, n = ucgenle(V, F[i])
            for t in tri:
                I += [len(P), len(P) + 1, len(P) + 2]
                P += [V[k] - kayma for k in t]; N += [n] * 3
        if I:
            P = np.array(P); ham.append((kat, P, np.array(N), np.array(I)))
    ham.sort(key=lambda h: (h[1][:, 2].min(), h[1][:, 2].max()))
    gruplar = collections.OrderedDict((k, []) for k in ('Duvar', 'Lento', 'Makas', 'Cati_paneli', 'Diger'))
    for s, (kat, P, N, I) in enumerate(ham):
        ex = {'katman': kat, 'z_alt': round(float(P[:, 2].min()), 4), 'z_ust': round(float(P[:, 2].max()), 4), 'sira': s}
        gruplar[kat].append((f'{kat}_{s:04d}', P, N, I, ex))
    gruplar = collections.OrderedDict((k, v) for k, v in gruplar.items() if v)
    glb_yaz(a.glb, gruplar)
    oz = {'parca': {k: len(v) for k, v in gruplar.items()}, 'ucgen': int(sum(len(h[3]) // 3 for h in ham)),
          'olcu_m': [round(float(x), 3) for x in (mx - mn)], 'yuz': len(F)}
    print(json.dumps(oz, ensure_ascii=False))
    if a.ozet:
        json.dump(oz, open(a.ozet, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
