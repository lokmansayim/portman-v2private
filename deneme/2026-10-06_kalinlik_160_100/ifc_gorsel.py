"""6 Ekim 2026 denemesi: IFC → Blender (bpy, Cycles) görselleri. Panolar tek tek görünür (kenar çizgileri Freestyle ile).

    ~/.cache/portman-bpy/bin/python deneme/2026-10-06_kalinlik_160_100/ifc_gorsel.py model.ifc cikti_klasoru

`deneme/2026-09-23/13_Kiyas/kod/ifc_gorsel.py`'nin devamıdır: IFC, IfcOpenShell geometri motoruyla (boşluklar gerçekten kesilerek)
üçgenlenir; pano hacmi Qto ile karşılaştırılır; kameralar modelin kutusundan hesaplanır. Yalnız görsel doğrulama içindir;
IFC'nin kendisi Blender'a bağlı değildir. bpy ayrı bir sanal ortam ister (Python 3.13).

`--blend`: Blender'da doğrudan açılan dosyayı da yazar (Blender IFC'yi eklentisiz açmaz; Lokman, 6 Ekim 19:46). Her pano ayrı
nesnedir; nesneler katmanlara (koleksiyon) ayrılır: dış panolar, iç panolar, pencereler, kapılar, çatı, makaslar, bağlantılar,
zemin, mahaller (gizli). Pano nesnesinin özel özelliklerinde pafta kodu, malzeme kodu ve ölçüleri durur. Aynı sahneden `.glb` de yazılır.
"""
from __future__ import annotations
import json, math, multiprocessing, sys
from collections import Counter
from pathlib import Path

import numpy as np
import ifcopenshell, ifcopenshell.geom, ifcopenshell.util.element as ue

R_STANDART, R_OZEL, R_IC = (0.80, 0.77, 0.69, 1.0), (0.66, 0.47, 0.80, 1.0), (0.90, 0.89, 0.85, 1.0)


def hacim(verts, faces):
    v = verts.reshape(-1, 3); f = faces.reshape(-1, 3)
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)


def tessellate(ifc_yol: Path):
    f = ifcopenshell.open(str(ifc_yol))
    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)
    it = ifcopenshell.geom.iterator(s, f, max(1, multiprocessing.cpu_count()))
    out = []
    if it.initialize():
        while True:
            sh = it.get()
            e = f.by_id(sh.id)
            g = sh.geometry
            verts = np.array(g.verts, dtype=float); faces = np.array(g.faces, dtype=int)
            mats = [(m.diffuse.r(), m.diffuse.g(), m.diffuse.b(), 1.0 - (m.transparency if m.transparency == m.transparency else 0.0)) for m in g.materials] \
                if hasattr(g.materials[0] if g.materials else None, "diffuse") else []
            kayit = {"id": sh.id, "sinif": e.is_a(), "ad": e.Name, "verts": verts, "faces": faces,
                     "mat_ids": np.array(g.material_ids, dtype=int), "mats": mats, "pano": None}
            if e.is_a("IfcWall"):
                ps = ue.get_psets(e)
                kayit["pano"] = {"dis": bool(ps["Pset_WallCommon"]["IsExternal"]), "sinif": ps["PortatifEv_Pano"]["PanoSinifi"]}
            out.append(kayit)
            if not it.next():
                break
    return f, out


def denetim(f, shapes):
    """Pano hacmi: geometri motorunun (boşluk kesilmiş) hacmi ↔ Qto NetVolume; modelin dış kutusu."""
    satir = []
    for sh in shapes:
        if sh["sinif"] != "IfcWall":
            continue
        q = ue.get_psets(f.by_id(sh["id"]))["Qto_WallBaseQuantities"]
        satir.append((sh["ad"], q["GrossVolume"], q["NetVolume"], abs(hacim(sh["verts"], sh["faces"]))))
    net = sum(r[2] for r in satir); geo = sum(r[3] for r in satir)
    en_kotu = max(satir, key=lambda r: abs(r[3] - r[2]))
    duvar = np.vstack([sh["verts"].reshape(-1, 3) for sh in shapes if sh["sinif"] == "IfcWall"])
    hepsi = np.vstack([sh["verts"].reshape(-1, 3) for sh in shapes if sh["sinif"] not in ("IfcSpace", "IfcOpeningElement")])
    return {"pano": len(satir), "qto_net_hacim_m3": round(net, 4), "geometri_net_hacim_m3": round(geo, 4), "fark_yuzde": round((geo / net - 1) * 100, 3),
            "en_buyuk_fark": {"pano": en_kotu[0], "qto": en_kotu[2], "geometri": round(en_kotu[3], 5)},
            "duvar_kutusu_m": [[round(float(v), 4) for v in duvar.min(axis=0)], [round(float(v), 4) for v in duvar.max(axis=0)]],
            "model_kutusu_m": [[round(float(v), 4) for v in hepsi.min(axis=0)], [round(float(v), 4) for v in hepsi.max(axis=0)]]}


KATMAN = {"dis_pano": "01 Dış panolar", "ic_pano": "02 İç panolar", "pencere": "03 Pencereler", "kapi": "04 Kapılar", "cati": "05 Çatı örtüsü ve alın",
          "makas": "06 Makaslar", "baglanti": "07 Bağlantı profilleri", "zemin": "08 Zemin", "mahal": "09 Mahaller (gizli)", "bosluk": "10 Boşluklar (gizli)"}


def katman_of(sh) -> str:
    s, ad = sh["sinif"], sh["ad"] or ""
    if s == "IfcWall": return "dis_pano" if sh["pano"]["dis"] else "ic_pano"
    if s == "IfcWindow": return "pencere"
    if s == "IfcDoor": return "kapi"
    if s == "IfcSlab": return "cati" if ad.startswith(("CATI", "VERANDA_CATI")) else "zemin"
    if s == "IfcPlate": return "cati"
    if s == "IfcMember": return "makas" if ad.startswith("MAKAS") else "baglanti"
    if s == "IfcSpace": return "mahal"
    if s == "IfcOpeningElement": return "bosluk"
    return "baglanti"


def render(shapes, out: Path, kutu, ornek: int = 24, gorsel: bool = True, blend: Path | None = None, etiket: dict | None = None):
    import bpy, mathutils
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"; sc.unit_settings.length_unit = "CENTIMETERS"
    mat_cache = {}

    def malzeme(rgba, anahtar=None):
        k = anahtar or tuple(round(c, 3) for c in rgba)
        if k in mat_cache:
            return mat_cache[k]
        m = bpy.data.materials.new(str(k)); m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (rgba[0], rgba[1], rgba[2], 1)
        b.inputs["Roughness"].default_value = 0.75
        if rgba[3] < 0.95:
            b.inputs["Alpha"].default_value = max(rgba[3], 0.15)
            if "Transmission Weight" in b.inputs:
                b.inputs["Transmission Weight"].default_value = 0.8
        m.diffuse_color = (rgba[0], rgba[1], rgba[2], max(rgba[3], 0.25))      # Blender'ın düz görünümündeki renk
        mat_cache[k] = m
        return m

    kol = {}
    for anahtar, ad_ in KATMAN.items():
        c = bpy.data.collections.new(ad_); sc.collection.children.link(c); kol[anahtar] = c
    for sh in shapes:
        c = kol[katman_of(sh)]
        v = sh["verts"].reshape(-1, 3); fc = sh["faces"].reshape(-1, 3)
        me = bpy.data.meshes.new(sh["ad"] or sh["sinif"])
        me.from_pydata(v.tolist(), [], fc.tolist()); me.update()
        ob = bpy.data.objects.new(sh["ad"] or sh["sinif"], me); c.objects.link(ob)
        if sh["pano"] is not None:          # pano: standart / kesilmiş (mor) / iç
            p = sh["pano"]
            for k_, v_ in ((etiket or {}).get(sh["ad"]) or {}).items():
                ob[{"kod": "malzeme_kodu", "sira": "pafta_kodu", "duvar": "duvar", "boy_mm": "boy_mm"}.get(k_, k_)] = v_
            ob["pano_sinifi"] = p["sinif"]; ob["dis_duvar"] = bool(p["dis"])
            renk = R_OZEL if (p["dis"] and p["sinif"] in ("ozel", "yarim")) else (R_STANDART if p["dis"] else R_IC)
            me.materials.append(malzeme(renk, ("pano", renk)))
            continue
        mats = sh["mats"] or [(0.7, 0.7, 0.7, 1.0)]
        for m in mats:
            me.materials.append(malzeme(m))
        if len(sh["mat_ids"]) == len(me.polygons):
            for pg, mi in zip(me.polygons, sh["mat_ids"]):
                pg.material_index = max(0, int(mi))

    (x0, y0, z0), (x1, y1, z1) = kutu
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; r = max(x1 - x0, y1 - y0)
    w = bpy.data.worlds.new("D"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.86, 0.90, 0.95, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.75
    sun = bpy.data.lights.new("S", "SUN"); sun.energy = 2.4; sun.angle = math.radians(4)
    so = bpy.data.objects.new("S", sun); so.rotation_euler = (math.radians(50), math.radians(8), math.radians(-32)); sc.collection.objects.link(so)
    me = bpy.data.meshes.new("zemin")
    me.from_pydata([(cx - 6 * r, cy - 6 * r, -0.16), (cx + 6 * r, cy - 6 * r, -0.16), (cx + 6 * r, cy + 6 * r, -0.16), (cx - 6 * r, cy + 6 * r, -0.16)], [], [(0, 1, 2, 3)])
    zo = bpy.data.objects.new("ZEMIN", me); zo.data.materials.append(malzeme((0.42, 0.50, 0.33, 1), "cim")); sc.collection.objects.link(zo)
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = ornek
    try:
        sc.cycles.use_denoising = True
    except Exception:
        pass
    sc.view_settings.view_transform = "Standard"
    # pano kenarları: her pano ayrı nesne olduğu için derzler kenar çizgisi olarak çıkar
    sc.render.use_freestyle = True; sc.render.line_thickness = 1.1
    vl = sc.view_layers[0]; vl.use_freestyle = True
    fs = vl.freestyle_settings
    ls = fs.linesets[0] if len(fs.linesets) else fs.linesets.new("derz")
    ls.select_silhouette = True; ls.select_border = True; ls.select_crease = True
    if ls.linestyle is None:
        ls.linestyle = bpy.data.linestyles.new("derz")
    ls.linestyle.color = (0.12, 0.12, 0.12)

    def kamera(konum, hedef, lens=32):
        cam = bpy.data.cameras.new("K"); cam.lens = lens; cam.clip_end = 600
        o = bpy.data.objects.new("K", cam); sc.collection.objects.link(o); o.location = konum
        o.rotation_euler = mathutils.Vector([hedef[i] - konum[i] for i in range(3)]).to_track_quat("-Z", "Y").to_euler()
        return o

    def gizle(katmanlar):
        for ad, c in kol.items():
            c.hide_render = ad in katmanlar

    dosyalar = []

    def cek(ad, konum, hedef, en=1600, boy=1000, lens=32):
        sc.camera = kamera(konum, hedef, lens)
        sc.render.resolution_x, sc.render.resolution_y = en, boy
        sc.render.filepath = str(out / ad); bpy.ops.render.render(write_still=True); dosyalar.append(ad)

    hz = 1.5
    if gorsel:
        gizle({"mahal", "bosluk"})
        cek("3b_01_on_sag.png", (cx + 1.25 * r, cy - 1.45 * r, 0.62 * r), (cx + 0.02 * r, cy - 0.05 * r, hz))
        cek("3b_02_arka_sol.png", (cx - 1.25 * r, cy + 1.45 * r, 0.62 * r), (cx - 0.02 * r, cy + 0.05 * r, hz))
        gizle({"mahal", "bosluk", "cati", "makas"})        # çatısız: panolar ve doğramalar
        cek("3b_03_catisiz_on_sol.png", (cx - 0.95 * r, cy - 1.35 * r, 1.25 * r), (cx, cy - 0.04 * r, 0.6), boy=1110)
    if blend is not None:
        gizle({"mahal", "bosluk"})
        for anahtar in ("mahal", "bosluk"):            # dosya açılınca da gizli: görünümde ve renderda
            kol[anahtar].hide_viewport = True
        sc.camera = kamera((cx + 1.25 * r, cy - 1.45 * r, 0.62 * r), (cx + 0.02 * r, cy - 0.05 * r, hz))
        sc.render.resolution_x, sc.render.resolution_y = 1600, 1000
        sc["portman_not"] = ("Pano pano model. Her pano ayrı nesne; katmanlar sağ üstteki listede (Outliner). "
                             "Çatıyı kaldırmak için 05 ve 06 numaralı katmanların gözünü kapatın.")
        blend = Path(blend)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()), compress=True)
        dosyalar.append(blend.name)
        try:
            glb = blend.with_suffix(".glb")
            bpy.ops.export_scene.gltf(filepath=str(glb.resolve()), export_format="GLB", use_renderable=True, export_cameras=False, export_lights=False)
            dosyalar.append(glb.name)
        except Exception as e:       # glTF eklentisi bu bpy kurulumunda yoksa .blend yeterlidir
            print("glb yazılamadı:", str(e)[:300])
    return dosyalar


def blend_denetle(yol: Path) -> dict:
    """Yazılan .blend dosyasını yeniden açar: katmanlar, nesne sayıları, pano özellikleri."""
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(Path(yol).resolve()))
    kat = {c.name: len(c.objects) for c in bpy.data.collections}
    panolar = [o for c in bpy.data.collections if c.name.startswith(("01", "02")) for o in c.objects]
    kose = [(o.matrix_world @ v.co) for o in panolar for v in o.data.vertices]
    kutu = [min(k[i] for k in kose) for i in range(3)] + [max(k[i] for k in kose) for i in range(3)]
    return {"blender_surumu": bpy.app.version_string, "dosya_surumu": ".".join(str(v) for v in bpy.data.version), "katman_nesne": kat,
            "pano": len(panolar), "pafta_kodlu_pano": sum(1 for o in panolar if o.get("pafta_kodu")),
            "pano_kutusu_m": [round(v, 4) for v in kutu], "kamera": bpy.context.scene.camera is not None}

if __name__ == "__main__":
    ifc_yol, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    f, shapes = tessellate(ifc_yol)
    d = denetim(f, shapes)
    d["geometri_uretilen_nesne"] = dict(Counter(s["sinif"] for s in shapes))
    etiket_yolu = ifc_yol.parent / "pano_etiketleri.json"
    etiket = json.loads(etiket_yolu.read_text(encoding="utf-8")) if etiket_yolu.exists() else {}
    blend = (out / (ifc_yol.stem + ".blend")) if "--blend" in sys.argv else None
    if "--render" in sys.argv or blend is not None:
        d["gorseller"] = render(shapes, out, d["duvar_kutusu_m"], gorsel="--render" in sys.argv, blend=blend, etiket=etiket)
    if blend is not None:
        d["blend_denetimi"] = blend_denetle(blend)
    (out / "ifc_geometri_denetimi.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(d, ensure_ascii=False, indent=1))
