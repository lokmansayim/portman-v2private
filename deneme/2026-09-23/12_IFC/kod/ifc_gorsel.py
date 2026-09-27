"""IFC'yi IfcOpenShell geometri motoruyla (boşluklar gerçekten kesilerek) üçgenlere çevirir, hacim denetimi yapar ve
Blender (bpy) ile render alır. IFC'nin kendisi Blender'a bağlı değildir; bu betik yalnız görsel doğrulama içindir.

    python3 ifc_gorsel.py model.ifc cikti_klasoru
"""
from __future__ import annotations
import json, math, sys, multiprocessing
from pathlib import Path

import numpy as np
import ifcopenshell, ifcopenshell.geom, ifcopenshell.util.element as ue


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
            out.append({"id": sh.id, "sinif": e.is_a(), "ad": e.Name, "verts": verts, "faces": faces,
                        "mat_ids": np.array(g.material_ids, dtype=int), "mats": mats})
            if not it.next():
                break
    return f, out


def denetim(f, shapes):
    """Pano hacmi: geometri motorunun (boşluk kesilmiş) hacmi ↔ Qto NetVolume."""
    satir = []
    for sh in shapes:
        if sh["sinif"] != "IfcWall":
            continue
        e = f.by_id(sh["id"])
        q = ue.get_psets(e)["Qto_WallBaseQuantities"]
        v = abs(hacim(sh["verts"], sh["faces"]))
        satir.append((e.Name, q["GrossVolume"], q["NetVolume"], v))
    brut = sum(r[1] for r in satir); net = sum(r[2] for r in satir); geo = sum(r[3] for r in satir)
    en_kotu = max(satir, key=lambda r: abs(r[3] - r[2]))
    return {"pano": len(satir), "brut_hacim_m3": round(brut, 4), "qto_net_hacim_m3": round(net, 4), "geometri_net_hacim_m3": round(geo, 4),
            "fark_yuzde": round((geo / net - 1) * 100, 3), "en_buyuk_fark": {"pano": en_kotu[0], "qto": en_kotu[2], "geometri": round(en_kotu[3], 5)}}


def render(shapes, out: Path):
    import bpy, mathutils
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    mat_cache = {}
    def malzeme(rgba, anahtar=None):
        k = anahtar or tuple(round(c, 3) for c in rgba)
        if k in mat_cache:
            return mat_cache[k]
        m = bpy.data.materials.new(str(k)); m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (rgba[0], rgba[1], rgba[2], 1)
        b.inputs["Roughness"].default_value = 0.7
        if rgba[3] < 0.95:
            b.inputs["Alpha"].default_value = max(rgba[3], 0.15)
            if "Transmission Weight" in b.inputs:
                b.inputs["Transmission Weight"].default_value = 0.8
        mat_cache[k] = m
        return m
    kol = {}
    for sh in shapes:
        c = kol.get(sh["sinif"])
        if c is None:
            c = bpy.data.collections.new(sh["sinif"]); sc.collection.children.link(c); kol[sh["sinif"]] = c
        v = sh["verts"].reshape(-1, 3); fc = sh["faces"].reshape(-1, 3)
        me = bpy.data.meshes.new(sh["ad"] or sh["sinif"])
        me.from_pydata(v.tolist(), [], fc.tolist()); me.update()
        ob = bpy.data.objects.new(sh["ad"] or sh["sinif"], me); c.objects.link(ob)
        mats = sh["mats"] or [(0.7, 0.7, 0.7, 1.0)]
        for m in mats:
            me.materials.append(malzeme(m))
        if len(sh["mat_ids"]) == len(me.polygons):
            for p, mi in zip(me.polygons, sh["mat_ids"]):
                p.material_index = max(0, int(mi))
    # ışık, zemin
    w = bpy.data.worlds.new("D"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.8, 0.85, 0.92, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    sun = bpy.data.lights.new("S", "SUN"); sun.energy = 2.6
    so = bpy.data.objects.new("S", sun); so.rotation_euler = (math.radians(52), math.radians(10), math.radians(-35)); sc.collection.objects.link(so)
    me = bpy.data.meshes.new("zemin"); me.from_pydata([(-25, -25, -0.16), (33, -25, -0.16), (33, 35, -0.16), (-25, 35, -0.16)], [], [(0, 1, 2, 3)])
    zo = bpy.data.objects.new("ZEMIN", me); zo.data.materials.append(malzeme((0.33, 0.45, 0.25, 1), "cim")); sc.collection.objects.link(zo)
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 20
    try: sc.cycles.use_denoising = True
    except Exception: pass
    sc.view_settings.view_transform = "AgX"
    def kamera(konum, hedef, orto=None, lens=30):
        cam = bpy.data.cameras.new("K")
        if orto: cam.type = "ORTHO"; cam.ortho_scale = orto
        else: cam.lens = lens
        cam.clip_end = 400
        o = bpy.data.objects.new("K", cam); sc.collection.objects.link(o); o.location = konum
        o.rotation_euler = mathutils.Vector([hedef[i] - konum[i] for i in range(3)]).to_track_quat("-Z", "Y").to_euler()
        return o
    def gizle(siniflar):
        for ad, c in kol.items():
            c.hide_render = ad in siniflar
    cx, cy = 4.0, 4.85
    # 1) dış görünüş (mahal hacimleri gizli)
    gizle({"IfcSpace", "IfcOpeningElement"}); so.hide_render = False
    sc.camera = kamera((cx + 13.5, cy - 15.5, 7.2), (cx + 0.3, cy - 1.2, 1.3))
    sc.render.resolution_x, sc.render.resolution_y = 1600, 1000
    sc.render.filepath = str(out / "ifc_01_dis_gorunus.png"); bpy.ops.render.render(write_still=True)
    # 2) çatısız: panolar + boşluklar + doğrama + mahaller (yarı saydam)
    gizle({"IfcRoof", "IfcSlab_ROOF", "IfcElementAssembly", "IfcMember", "IfcPlate", "IfcOpeningElement"})
    for o in bpy.data.objects:
        if o.name.startswith(("CATI", "VERANDA_CATI")):
            o.hide_render = True
    sc.camera = kamera((cx - 9.5, cy - 13.0, 12.5), (cx, cy - 0.5, 0.2))
    sc.render.resolution_x, sc.render.resolution_y = 1600, 1100
    sc.render.filepath = str(out / "ifc_02_catisiz.png"); bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    ifc_yol, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    f, shapes = tessellate(ifc_yol)
    d = denetim(f, shapes)
    from collections import Counter
    d["geometri_uretilen_nesne"] = dict(Counter(s["sinif"] for s in shapes))
    (out / "ifc_geometri_denetimi.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(d, ensure_ascii=False))
    if "--render" in sys.argv:
        render(shapes, out)
