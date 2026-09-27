"""Portman — bayi planından pano bloklu Blender modeli (blender_girdi.json → .blend + render + BOM).

Blender'ın kendi Python'unda da çalışır (yalnız bpy + json):
    blender -b --python blender_ciz.py -- blender_girdi.json <cikti_klasoru> [--render]
ya da bpy modülüyle:
    python3 blender_ciz.py blender_girdi.json <cikti_klasoru> --render

Her pano ayrı nesnedir (bayinin çizdiği parça; boy/kalınlık/sınıf özel özellik olarak üzerinde), pencere ve kapı boşlukları
panodan kesilir, doğramalar ayrı nesnedir. BOM sahnedeki nesneler sayılarak çıkarılır (blender_bom.csv).
Birim: Blender metre; girdi cm.
"""
from __future__ import annotations
import json, math, sys, csv
from pathlib import Path
from collections import Counter, defaultdict

import bpy
import bmesh

CM = 0.01


# ----------------------------------------------------------------------------- argümanlar
def _args():
    a = sys.argv
    if "--" in a:
        a = a[a.index("--") + 1:]
    else:
        a = a[1:]
    girdi = Path(a[0]); out = Path(a[1]); render = "--render" in a
    return girdi, out, render


# ----------------------------------------------------------------------------- sahne yardımcıları
def temiz_sahne():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"; sc.unit_settings.length_unit = "CENTIMETERS"
    return sc


def koleksiyon(ad, ust=None):
    c = bpy.data.collections.new(ad)
    (ust or bpy.context.scene.collection).children.link(c)
    return c


_MAT = {}


def malzeme(ad, renk, metal=0.0, puruz=0.7, gecirgen=0.0, alfa=1.0):
    if ad in _MAT:
        return _MAT[ad]
    m = bpy.data.materials.new(ad)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*renk, 1.0)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = puruz
    if gecirgen:
        for k in ("Transmission Weight", "Transmission"):
            if k in b.inputs:
                b.inputs[k].default_value = gecirgen
    if alfa < 1.0:
        b.inputs["Alpha"].default_value = alfa
    m.diffuse_color = (*renk, alfa)
    _MAT[ad] = m
    return m


def kutular_mesh(ad, kutular, mat, kol, ozellik=None):
    """kutular: [(x0,y0,z0,x1,y1,z1), ...] cm → tek mesh nesnesi."""
    me = bpy.data.meshes.new(ad)
    bm = bmesh.new()
    for (x0, y0, z0, x1, y1, z1) in kutular:
        if x1 - x0 < 1e-3 or y1 - y0 < 1e-3 or z1 - z0 < 1e-3:
            continue
        v = [bm.verts.new((x * CM, y * CM, z * CM)) for x, y, z in
             ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
        for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            bm.faces.new([v[i] for i in f])
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(ad, me)
    ob.data.materials.append(mat)
    kol.objects.link(ob)
    for k, v in (ozellik or {}).items():
        ob[k] = v
    return ob


def poligon_mesh(ad, pts, z0, z1, mat, kol, ozellik=None):
    """Düz poligonu z0..z1 arasında prizmaya çevir (cm)."""
    me = bpy.data.meshes.new(ad)
    bm = bmesh.new()
    alt = [bm.verts.new((x * CM, y * CM, z0 * CM)) for x, y in pts]
    ust = [bm.verts.new((x * CM, y * CM, z1 * CM)) for x, y in pts]
    bm.faces.new(list(reversed(alt))); bm.faces.new(ust)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([alt[i], alt[j], ust[j], ust[i]])
    bm.normal_update()
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(ad, me)
    ob.data.materials.append(mat)
    kol.objects.link(ob)
    for k, v in (ozellik or {}).items():
        ob[k] = v
    return ob


def prizma_mesh(ad, kesit_xz, y0, y1, mat, kol):
    """x-z düzlemindeki kesiti (cm) y0..y1 boyunca çek (makas, çatı yüzü, alın üçgeni)."""
    me = bpy.data.meshes.new(ad)
    bm = bmesh.new()
    on = [bm.verts.new((x * CM, y0 * CM, z * CM)) for x, z in kesit_xz]
    ar = [bm.verts.new((x * CM, y1 * CM, z * CM)) for x, z in kesit_xz]
    bm.faces.new(on); bm.faces.new(list(reversed(ar)))
    n = len(kesit_xz)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([on[j], on[i], ar[i], ar[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(ad, me)
    ob.data.materials.append(mat)
    kol.objects.link(ob)
    return ob


# ----------------------------------------------------------------------------- panolar
SINIF_AD = {"tam": "Tam pano 125,5", "yarim": "Yarım pano 62,75", "ozel": "Özel pano", "kose": "Köşe / bağlantı parçası"}


def pano_kutulari(p):
    """Panoyu açıklık aralıklarıyla böl: açıklık dışında tam yükseklik, açıklıkta alt (denizlik) + üst (lento) parça."""
    x0, y0, x1, y1 = p["rect"]
    H = G["bina"]["duvar_h"]
    if p["yon"] == "x":
        a0, a1 = x0, x1
        def kutu(s0, s1, z0, z1): return (s0, y0, z0, s1, y1, z1)
    else:
        a0, a1 = y0, y1
        def kutu(s0, s1, z0, z1): return (x0, s0, z0, x1, s1, z1)
    acik = sorted(p["acikliklar"], key=lambda a: a["a0"])
    out, s = [], a0
    for a in acik:
        o0, o1 = max(a0, a["a0"]), min(a1, a["a1"])
        if o0 > s:
            out.append(kutu(s, o0, 0, H))
        if a["z0"] > 0:
            out.append(kutu(o0, o1, 0, a["z0"]))
        out.append(kutu(o0, o1, a["z1"], H))
        s = max(s, o1)
    if s < a1:
        out.append(kutu(s, a1, 0, H))
    return out


def panolari_kur(kol_dis, kol_ic, kol_kose):
    A = G["acikliklar"]
    eke_denk = set()
    for ai, a in enumerate(A):
        if a["tur"] == "pencere" and len(a["panolar"]) > 1:
            eke_denk.update(a["panolar"])
    sayac = Counter()
    for p in G["panolar"]:
        kol = kol_kose if p["sinif"] == "kose" else (kol_dis if p["tur"] == "dis" else kol_ic)
        acik_tur = []
        for x in p["acikliklar"]:
            a = A[x["aciklik"]]
            acik_tur.append(f"pencere {a['olcu']}" if a["tur"] == "pencere" else f"kapı {round(a['genislik'])}")
        if p["sinif"] == "kose":
            kalem = f"{'Dış' if p['kalinlik'] >= 8.5 else 'İç'} köşe/bağlantı parçası {p['kalinlik']:.0f}×{p['boy']:.0f}"
        else:
            tur = "Dış" if p["tur"] == "dis" else "İç"
            if acik_tur:
                ek = ", ".join(sorted(set(acik_tur)))
                kalem = f"{tur} {SINIF_AD[p['sinif']].lower()} — {ek}li"
            else:
                kalem = f"{tur} {SINIF_AD[p['sinif']].lower()} — dolu"
            if p["sinif"] == "ozel":
                kalem += f" ({p['boy']:.1f} cm)"
        sayac[(p["tur"], p["sinif"])] += 1
        ad = f"PANO_{'D' if p['tur'] == 'dis' else 'I'}_{p['sinif'].upper()}_{p['boy']:.1f}_{p['id']:02d}"
        mat = MAT["dis"] if p["tur"] == "dis" else MAT["ic"]
        ob = kutular_mesh(ad, pano_kutulari(p), mat, kol, {
            "bom_kalem": kalem, "pano_sinifi": p["sinif"], "duvar": "dis" if p["tur"] == "dis" else "ic",
            "boy_cm": p["boy"], "kalinlik_cm": p["kalinlik"], "yukseklik_cm": G["bina"]["duvar_h"],
            "acikliklar": ", ".join(acik_tur), "pencere_pano_ekinde": p["id"] in eke_denk, "kaynak": "bayi PDF parça #%d" % p["id"]})
        ob["_montaj_sinifi"] = "ek" if p["id"] in eke_denk else p["sinif"]
    return eke_denk


# ----------------------------------------------------------------------------- doğramalar
def dogramalari_kur(kol):
    A = G["acikliklar"]
    n = Counter()
    for ai, a in enumerate(A):
        if not a["panolar"]:
            continue
        p = G["panolar"][a["panolar"][0]]
        x0, y0, x1, y1 = p["rect"]
        c0, c1 = (y0, y1) if a["yon"] == "x" else (x0, x1)
        cm_ = (c0 + c1) / 2
        o0, o1, z0, z1 = a["a0"], a["a1"], a["z0"], a["z1"]
        def kutu(s0, s1, d0, d1, zz0, zz1):
            return (s0, d0, zz0, s1, d1, zz1) if a["yon"] == "x" else (d0, s0, zz0, d1, s1, zz1)
        if a["tur"] == "pencere":
            n[a["olcu"]] += 1
            f, d = 6.0, 3.5                      # kasa eni / yarım derinlik
            kasa = [kutu(o0, o1, cm_ - d, cm_ + d, z0, z0 + f), kutu(o0, o1, cm_ - d, cm_ + d, z1 - f, z1),
                    kutu(o0, o0 + f, cm_ - d, cm_ + d, z0 + f, z1 - f), kutu(o1 - f, o1, cm_ - d, cm_ + d, z0 + f, z1 - f)]
            if o1 - o0 >= 100:
                m = (o0 + o1) / 2
                kasa.append(kutu(m - 3, m + 3, cm_ - d, cm_ + d, z0 + f, z1 - f))
            kutular_mesh(f"PENCERE_{a['olcu']}_{n[a['olcu']]}_KASA", kasa, MAT["pvc"], kol,
                         {"bom_kalem": f"PVC pencere {a['olcu'].replace('x', '×')} (beyaz, 4+12+4)", "olcu": a["olcu"],
                          "esik_cm": z0, "kaynak": "bayi PDF"})
            kutular_mesh(f"PENCERE_{a['olcu']}_{n[a['olcu']]}_CAM", [kutu(o0 + f, o1 - f, cm_ - 0.6, cm_ + 0.6, z0 + f, z1 - f)], MAT["cam"], kol)
        else:
            dis = a["genislik"] >= 95
            n["dis_kapi" if dis else "ic_kapi"] += 1
            if dis:
                kutular_mesh(f"KAPI_DIS_CELIK_{n['dis_kapi']}", [kutu(o0 + 3, o1 - 3, cm_ - 2.5, cm_ + 2.5, 0, z1 - 3)], MAT["celik"], kol,
                             {"bom_kalem": f"Çelik dış kapı {round(a['genislik'])}×{int(z1)}", "kaynak": "bayi PDF"})
                kutular_mesh(f"KAPI_DIS_KASA_{n['dis_kapi']}", [kutu(o0, o0 + 3, cm_ - 5, cm_ + 5, 0, z1), kutu(o1 - 3, o1, cm_ - 5, cm_ + 5, 0, z1),
                                                                 kutu(o0, o1, cm_ - 5, cm_ + 5, z1 - 3, z1)], MAT["celik_kasa"], kol)
            else:
                # iç kapılar bu siparişte kapsam dışı (bayi kendisi takıyor): yalnız boşluk; sayım için işaret nesnesi
                ob = kutular_mesh(f"KAPI_IC_BOSLUK_{n['ic_kapi']}", [kutu(o0, o1, cm_ - 0.2, cm_ + 0.2, z1 - 0.4, z1)], MAT["isaret"], kol,
                                  {"bom_kalem": f"İç kapı boşluğu {round(a['genislik'])}×{int(z1)} (kapı kapsam dışı — bayi)", "kaynak": "bayi PDF"})
    return n


# ----------------------------------------------------------------------------- döşeme, odalar, veranda
def zemin_kur(kol_zemin, kol_oda, kol_yazi):
    Wd = max(p["rect"][2] for p in G["panolar"]); Hd = max(p["rect"][3] for p in G["panolar"])
    ver = G["veranda"]
    if ver:
        vx0, vy0 = ver["poligon"][0]; vx1 = ver["poligon"][1][0]
        taban = [(0, 0), (vx0, 0), (vx0, vy0), (vx1, vy0), (Wd, 0), (Wd, Hd), (0, Hd)]
        taban = [(0, 0), (vx0, 0), (vx0, vy0), (vx1, vy0), (vx1, Hd), (0, Hd)] if vx1 >= Wd - 1 else taban
    else:
        taban = [(0, 0), (Wd, 0), (Wd, Hd), (0, Hd)]
    poligon_mesh("TEMEL_BETON (bayi)", taban, -15, 0, MAT["beton"], kol_zemin,
                 {"bom_kalem": "Zemin betonu — kapsam dışı (bayi/saha)", "kaynak": "bayi PDF dış kutu + veranda kesikli çizgisi"})
    renk = {"yatak": "oda_yatak", "salon": "oda_salon", "mutfak": "oda_mutfak", "banyo": "oda_islak", "wc": "oda_islak", "hol": "oda_hol"}
    font = None
    try:
        fp = Path(__file__).resolve().parent.parent / "kanal" / "DejaVuSans.ttf"
        if fp.exists():
            font = bpy.data.fonts.load(str(fp))
    except Exception:
        font = None
    def yazi(ad, metin, x, y, boy=18):
        cu = bpy.data.curves.new(ad, "FONT"); cu.body = metin; cu.size = boy * CM; cu.align_x = "CENTER"; cu.align_y = "CENTER"
        if font:
            cu.font = font
        ob = bpy.data.objects.new(ad, cu); ob.location = (x * CM, y * CM, 1.2 * CM)
        ob.data.materials.append(MAT["yazi"]); kol_yazi.objects.link(ob)
    for i, o in enumerate(G["odalar"]):
        anah = next((v for k, v in renk.items() if k in o["ad"].lower().replace("ı", "i")), "oda_hol")
        poligon_mesh(f"ODA_{o['ad']}_{i}", [tuple(p) for p in o["poligon"]], 0, 0.6, MAT[anah], kol_oda,
                     {"mahal": o["ad"], "net_m2_cizim": o["net_m2"], "etiket_m2_bayi": o["etiket_m2"]})
        et = f"{o['ad']}\n{str(o['net_m2']).replace('.', ',')} m²"
        if o["etiket_m2"] is not None and abs(o["etiket_m2"] - o["net_m2"]) > 0.3:
            et += f"\n(bayi etiketi {str(o['etiket_m2']).replace('.', ',')})"
        yazi(f"YAZI_{i}", et, *o["etiket_xy"])
    if ver:
        poligon_mesh("VERANDA_ZEMIN", [tuple(p) for p in ver["poligon"]], 0, 0.6, MAT["oda_veranda"], kol_oda, {"mahal": "VERANDA", "net_m2_cizim": ver["net_m2"]})
        if ver.get("etiket_xy"):
            yazi("YAZI_VERANDA", f"VERANDA\n{str(ver['net_m2']).replace('.', ',')} m²\n(60 cm bina dışına taşar)", *ver["etiket_xy"])
    return Wd, Hd


def tefris_kur(kol):
    cu = bpy.data.curves.new("TEFRIS_bayi", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.45 * CM; cu.bevel_resolution = 0
    for (a, b) in G["tefris"]:
        sp = cu.splines.new("POLY"); sp.points.add(1)
        sp.points[0].co = (a[0] * CM, a[1] * CM, 1.0 * CM, 1); sp.points[1].co = (b[0] * CM, b[1] * CM, 1.0 * CM, 1)
    ob = bpy.data.objects.new("TEFRIS_bayi_cizimi", cu); ob.data.materials.append(MAT["tefris"]); kol.objects.link(ob)
    ob["not"] = "Bayinin PDF'indeki tefriş katmanı (yerleşim fikri; BOM'a girmez)"
    return ob


# ----------------------------------------------------------------------------- çatı, makas, veranda taşıyıcı
def cati_kur(kol_cati, kol_makas, Wd, Hd):
    c = G["bina"]["cati"]; H0 = G["bina"]["duvar_h"]
    s, eg, top = c["sacak"], c["egim"], c["topuk"]
    xm = Wd / 2
    z_sacak = H0 + top
    z_mahya = z_sacak + (xm + s) * eg
    t = 4.0                                    # çatı örtüsü kalınlığı (görsel)
    y0, y1 = -s, Hd + s
    sol = [(-s, z_sacak + 10), (xm, z_mahya + 10), (xm, z_mahya + 10 + t), (-s, z_sacak + 10 + t)]
    sag = [(xm, z_mahya + 10), (Wd + s, z_sacak + 10), (Wd + s, z_sacak + 10 + t), (xm, z_mahya + 10 + t)]
    alan = 2 * math.hypot(xm + s, (xm + s) * eg) * (y1 - y0) / 1e4
    for ad, k in (("CATI_SOL", sol), ("CATI_SAG", sag)):
        ob = prizma_mesh(ad, k, y0, y1, MAT["cati"], kol_cati)
        ob["bom_kalem"] = "Trapez çatı sacı (antrasit) — yüzey"; ob["alan_m2_toplam"] = round(alan, 2)
    prizma_mesh("MAHYA", [(xm - 12, z_mahya + 10 + t), (xm, z_mahya + 10 + t + 6), (xm + 12, z_mahya + 10 + t)], y0, y1, MAT["cati"], kol_cati)
    # alın (üçgen) dolguları: ön y=0..10, arka Hd-10..Hd
    zt = lambda x: z_sacak + (min(x, Wd - x) + s) * eg     # makas üst kotu
    ucgen = [(0, H0), (Wd, H0), (Wd, zt(Wd)), (xm, zt(xm)), (0, zt(0))]
    for ad, ya, yb in (("ALIN_ON", 0, 10), ("ALIN_ARKA", Hd - 10, Hd)):
        ob = prizma_mesh(ad, ucgen, ya, yb, MAT["dis"], kol_cati)
        ob["bom_kalem"] = "Çatı alın dolgusu (üçgen) — kural teyit edilecek"
    # makaslar: kısa kenar (x) boyunca, ≤125,5 aralıkla
    n = math.ceil((Hd - 10) / 125.5) + 1
    ys = [5 + i * (Hd - 10) / (n - 1) for i in range(n)]
    for i, y in enumerate(ys):
        e = 5.0; d = 2.5
        parca = []
        # alt başlık
        parca.append((0, y - d, H0, Wd, y + d, H0 + 10))
        ob = kutular_mesh(f"MAKAS_{i + 1:02d}", parca, MAT["makas"], kol_makas,
                          {"bom_kalem": "Çatı makası (baş)" if i in (0, n - 1) else "Çatı makası (orta)", "aciklik_cm": round(Wd, 1)})
        zt = lambda x: z_sacak + (min(x, Wd - x) + s) * eg   # üst başlık alt kotu
        q1, q3 = xm / 2, xm + xm / 2
        uyeler = (("UST_SOL", [(-s, z_sacak), (xm, z_mahya), (xm, z_mahya + 10), (-s, z_sacak + 10)]),
                  ("UST_SAG", [(xm, z_mahya), (Wd + s, z_sacak), (Wd + s, z_sacak + 10), (xm, z_mahya + 10)]),
                  ("DIKME_ORTA", [(xm - 3, H0 + 10), (xm + 3, H0 + 10), (xm + 3, zt(xm)), (xm - 3, zt(xm))]),
                  ("DIKME_SOL", [(q1 - 3, H0 + 10), (q1 + 3, H0 + 10), (q1 + 3, zt(q1)), (q1 - 3, zt(q1))]),
                  ("DIKME_SAG", [(q3 - 3, H0 + 10), (q3 + 3, H0 + 10), (q3 + 3, zt(q3)), (q3 - 3, zt(q3))]),
                  ("CAPRAZ_SOL", [(q1 - 3, H0 + 10), (q1 + 5, H0 + 10), (xm - 3, zt(xm) - 8), (xm - 11, zt(xm) - 8)]),
                  ("CAPRAZ_SAG", [(q3 - 5, H0 + 10), (q3 + 3, H0 + 10), (xm + 11, zt(xm) - 8), (xm + 3, zt(xm) - 8)]))
        for ad, k in uyeler:
            ob2 = prizma_mesh(f"MAKAS_{i + 1:02d}_{ad}", k, y - d, y + d, MAT["makas"], kol_makas)
            ob2.parent = ob
    return {"mahya_cm": round(z_mahya, 1), "makas": n, "cati_alan_m2": round(alan, 2)}


def veranda_tasiyici(kol, kol_cati):
    """Bayinin 27.08 ön görünüşü: sağda öne çıkan ikinci (alçak) beşik = veranda çatısı. Veranda taşması (60 cm) dikmelerle taşınır.
    Ana çatının ön alnı y=0'da veranda kirişine oturur."""
    ver = G["veranda"]
    if not ver:
        return {}
    x0 = ver["poligon"][0][0]; x1 = ver["poligon"][1][0]; yv = ver["poligon"][0][1]; ust = ver["poligon"][2][1]
    H0 = G["bina"]["duvar_h"]; c = G["bina"]["cati"]; s, eg, top = c["sacak"], c["egim"], c["topuk"]
    for i, (xa, xb) in enumerate(((x0, x0 + 10), (x1 - 10, x1))):
        kutular_mesh(f"VERANDA_DIKME_{i + 1}", [(xa, yv, 0, xb, yv + 10, H0 - 10)], MAT["kiris"], kol,
                     {"bom_kalem": "Veranda dikmesi 100×100 flanşlı kutu profil", "boy_cm": H0 - 10})
    kirisler = (("ON", (x0, yv, H0 - 10, x1, yv + 10, H0), x1 - x0), ("ALIN_Y0", (x0, 0, H0 - 10, x1 - 10, 10, H0), x1 - 10 - x0),
                ("YAN_SAG", (x1 - 10, yv + 10, H0 - 10, x1, ust, H0), ust - yv - 10), ("YAN_SOL", (x0, yv + 10, H0 - 10, x0 + 10, 0, H0), -yv - 10))
    for ad, k, L in kirisler:
        kutular_mesh(f"VERANDA_KIRIS_{ad}", [k], MAT["kiris"], kol, {"bom_kalem": "Veranda kirişi 100×100 kutu profil", "boy_cm": round(L, 1)})
    # veranda beşiği: mahya y boyunca, x0-s .. x1+s; öne y=yv-s'ye kadar, arkada ana çatının ön saçağına (y=-s) kadar
    xm = (x0 + x1) / 2; zs = H0 + top; zm = zs + (xm - x0 + s) * eg; t = 4.0
    ya, yb = yv - s, -s
    sol = [(x0 - s, zs + 10), (xm, zm + 10), (xm, zm + 10 + t), (x0 - s, zs + 10 + t)]
    sag = [(xm, zm + 10), (x1 + s, zs + 10), (x1 + s, zs + 10 + t), (xm, zm + 10 + t)]
    alan = 2 * math.hypot(xm - x0 + s, (xm - x0 + s) * eg) * (yb - ya) / 1e4
    for ad, k in (("VERANDA_CATI_SOL", sol), ("VERANDA_CATI_SAG", sag)):
        ob = prizma_mesh(ad, k, ya, yb, MAT["cati"], kol_cati); ob["bom_kalem"] = "Trapez çatı sacı (antrasit) — veranda beşiği"
    zt = lambda x: zs + (min(x - x0, x1 - x) + s) * eg
    alin = [(x0, H0), (x1, H0), (x1, zt(x1)), (xm, zt(xm)), (x0, zt(x0))]
    ob = prizma_mesh("VERANDA_ALIN", alin, yv, yv + 8, MAT["dis"], kol_cati); ob["bom_kalem"] = "Çatı alın dolgusu (üçgen) — kural teyit edilecek"
    return {"veranda_cati_alan_m2": round(alan, 2), "veranda_mahya_cm": round(zm, 1)}


# ----------------------------------------------------------------------------- BOM (sahneden sayım)
def bom_say(out: Path):
    say = Counter(); boy = defaultdict(float)
    for ob in bpy.data.objects:
        k = ob.get("bom_kalem")
        if not k:
            continue
        say[k] += 1
        if "boy_cm" in ob and "kutu profil" in k:
            boy[k] += ob["boy_cm"]
    satir = sorted(say.items())
    with open(out / "blender_bom.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Kalem (sahnedeki nesnelerden sayıldı)", "Adet", "Toplam boy (cm)"])
        for k, v in satir:
            w.writerow([k, v, round(boy[k], 1) if boy[k] else ""])
    return satir


# ----------------------------------------------------------------------------- render
def isik_ve_dunya(sc):
    w = bpy.data.worlds.new("Dunya"); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.78, 0.84, 0.92, 1); bg.inputs[1].default_value = 0.55
    sun = bpy.data.lights.new("Gunes", "SUN"); sun.energy = 2.6; sun.angle = math.radians(6)
    o = bpy.data.objects.new("Gunes", sun); o.rotation_euler = (math.radians(52), math.radians(10), math.radians(-35))
    sc.collection.objects.link(o)
    kol = koleksiyon("12_Arazi")
    kutular_mesh("ARAZI", [(-2500, -2500, -16, 3300, 3500, -15)], malzeme("Cim", (0.33, 0.45, 0.25), puruz=0.95), kol)
    return o


def kamera(sc, ad, konum, hedef, orto=None, lens=32):
    cam = bpy.data.cameras.new(ad)
    if orto:
        cam.type = "ORTHO"; cam.ortho_scale = orto
    else:
        cam.lens = lens
    cam.clip_end = 500
    ob = bpy.data.objects.new(ad, cam); sc.collection.objects.link(ob)
    ob.location = konum
    d = (hedef[0] - konum[0], hedef[1] - konum[1], hedef[2] - konum[2])
    import mathutils
    ob.rotation_euler = mathutils.Vector(d).to_track_quat("-Z", "Y").to_euler()
    return ob


def render(sc, cam, yol, cozunurluk, gizle=(), goster=(), montaj=False, ornek=24):
    sc.camera = cam
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = ornek
    try:
        sc.cycles.use_denoising = True
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = cozunurluk; sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    try:
        sc.view_settings.view_transform = "AgX"
    except Exception:
        sc.view_settings.view_transform = "Filmic"
    sun = bpy.data.objects.get("Gunes")
    if sun:
        sun.hide_render = montaj                      # plan görünüşü: gölgesiz, düz ışık
    sc.world.node_tree.nodes["Background"].inputs[1].default_value = 1.6 if montaj else 0.55
    for kol in bpy.data.collections:
        kol.hide_render = kol.name in gizle
    for kol in goster:
        bpy.data.collections[kol].hide_render = False
    # malzeme takımı
    for ob in bpy.data.objects:
        if ob.name.startswith("PANO_"):
            ob.data.materials[0] = MAT["m_" + ob["_montaj_sinifi"]] if montaj else (MAT["dis"] if ob["duvar"] == "dis" else MAT["ic"])
    sc.render.filepath = str(yol)
    bpy.ops.render.render(write_still=True)


# ----------------------------------------------------------------------------- ana akış
if __name__ == "__main__":
    girdi, out, yap_render = _args()
    out.mkdir(parents=True, exist_ok=True)
    G = json.loads(girdi.read_text(encoding="utf-8"))
    sc = temiz_sahne()
    MAT = {
        "dis": malzeme("Dis_pano_fibercement", (0.62, 0.61, 0.58), puruz=0.85),
        "ic": malzeme("Ic_pano_fibercement", (0.80, 0.79, 0.76), puruz=0.85),
        "pvc": malzeme("PVC_beyaz", (0.95, 0.95, 0.94), puruz=0.35),
        "cam": malzeme("Cam", (0.75, 0.88, 0.95), puruz=0.03, gecirgen=0.9, alfa=0.35),
        "celik": malzeme("Celik_kapi", (0.23, 0.16, 0.12), metal=0.3, puruz=0.4),
        "celik_kasa": malzeme("Celik_kasa", (0.18, 0.18, 0.18), metal=0.5, puruz=0.4),
        "isaret": malzeme("Ic_kapi_isaret", (0.2, 0.45, 0.85)),
        "beton": malzeme("Beton", (0.58, 0.58, 0.56), puruz=0.95),
        "cati": malzeme("Trapez_antrasit", (0.11, 0.12, 0.13), metal=0.5, puruz=0.45),
        "makas": malzeme("Galvaniz", (0.72, 0.74, 0.77), metal=0.8, puruz=0.35),
        "kiris": malzeme("Kutu_profil", (0.30, 0.31, 0.33), metal=0.6, puruz=0.4),
        "tefris": malzeme("Tefris", (0.22, 0.22, 0.24)),
        "yazi": malzeme("Yazi", (0.05, 0.05, 0.08)),
        "oda_yatak": malzeme("Oda_yatak", (0.80, 0.86, 0.95)), "oda_salon": malzeme("Oda_salon", (0.95, 0.90, 0.78)),
        "oda_mutfak": malzeme("Oda_mutfak", (0.90, 0.95, 0.82)), "oda_islak": malzeme("Oda_islak", (0.78, 0.92, 0.93)),
        "oda_hol": malzeme("Oda_hol", (0.92, 0.92, 0.92)), "oda_veranda": malzeme("Oda_veranda", (0.86, 0.80, 0.72)),
        "m_tam": malzeme("Montaj_tam", (0.55, 0.56, 0.58)), "m_yarim": malzeme("Montaj_yarim", (0.98, 0.62, 0.15)),
        "m_ozel": malzeme("Montaj_ozel", (0.85, 0.20, 0.80)), "m_kose": malzeme("Montaj_kose", (0.15, 0.15, 0.15)),
        "m_ek": malzeme("Montaj_pencere_ekte", (0.90, 0.10, 0.10)),
    }
    K = {ad: koleksiyon(ad) for ad in ("01_Panolar_Dis", "02_Panolar_Ic", "03_Kose_Baglanti", "04_Dograma", "05_Zemin",
                                       "06_Oda_Renkleri", "07_Yazilar", "08_Tefris_bayi", "09_Cati", "10_Makaslar", "11_Veranda_Tasiyici")}
    eke_denk = panolari_kur(K["01_Panolar_Dis"], K["02_Panolar_Ic"], K["03_Kose_Baglanti"])
    dog = dogramalari_kur(K["04_Dograma"])
    Wd, Hd = zemin_kur(K["05_Zemin"], K["06_Oda_Renkleri"], K["07_Yazilar"])
    tefris_kur(K["08_Tefris_bayi"])
    cati = cati_kur(K["09_Cati"], K["10_Makaslar"], Wd, Hd)
    cati.update(veranda_tasiyici(K["11_Veranda_Tasiyici"], K["09_Cati"]))
    isik_ve_dunya(sc)
    bom = bom_say(out)
    ozet = {"pano_nesnesi": sum(1 for o in bpy.data.objects if o.name.startswith("PANO_")),
            "pencere_eke_denk_gelen_panolar": sorted(eke_denk), "dograma": dict(dog), "cati": cati, "bom_kalem_sayisi": len(bom)}
    (out / "blender_ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "Tatar_80m2_bayi_plani.blend"))
    try:
        bpy.ops.export_scene.gltf(filepath=str(out / "Tatar_80m2_bayi_plani.glb"), export_format="GLB", export_extras=True)
    except Exception as e:
        print("glb dışa aktarılamadı:", e)
    print(json.dumps(ozet, ensure_ascii=False))
    if yap_render:
        cx, cy = Wd / 2 * CM, Hd / 2 * CM
        ust = kamera(sc, "KAM_UST", (cx, cy - 0.3, 30), (cx, cy - 0.3, 0), orto=11.2)
        render(sc, ust, out / "01_ust_plan_montaj.png", (1300, 1500), gizle=("09_Cati", "10_Makaslar", "11_Veranda_Tasiyici", "12_Arazi"), montaj=True, ornek=12)
        dis = kamera(sc, "KAM_DIS", (cx + 13.5, cy - 15.5, 7.2), (cx + 0.3, cy - 1.2, 1.3), lens=30)
        render(sc, dis, out / "02_dis_perspektif.png", (1600, 1000), gizle=("06_Oda_Renkleri", "07_Yazilar", "08_Tefris_bayi"), ornek=24)
        kes = kamera(sc, "KAM_KESIT", (cx - 9.5, cy - 13.0, 12.5), (cx, cy - 0.5, 0.2), lens=30)
        render(sc, kes, out / "03_catisiz_ic_gorunus.png", (1600, 1100), gizle=("09_Cati", "10_Makaslar", "07_Yazilar"), ornek=24)
        on = kamera(sc, "KAM_ON", (cx, -25, 2.2), (cx, 0, 2.2), orto=10.5)
        render(sc, on, out / "04_on_gorunus.png", (1500, 800), gizle=("06_Oda_Renkleri", "07_Yazilar", "08_Tefris_bayi"), ornek=16)
        bpy.ops.wm.save_as_mainfile(filepath=str(out / "Tatar_80m2_bayi_plani.blend"))
