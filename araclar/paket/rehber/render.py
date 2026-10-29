"""İE-18 · Rehberin render görselleri (62 m² rehberinin "Render görselleri" galerisi): rehberin 3B modeli (`glb.js`'in GLB'si) Blender
Cycles ile birkaç açıdan. 62 m²'nin betiğinden (dal `claude/montaj-rehberi-devir` `6b899b4`, `deneme/2026-10-25_rehber_62m2/render/
render.py`) genelleştirildi: kamera evin kutusundan, malzeme rehberin malzeme anahtarından (renk GLB'den, doku ve pürüz anahtardan),
temel plak GLB'den (rehberin sahnesindeki plak), gizlenecek adımlar `sahne.json`'dan. Bilgisayara bağlı değil; LLM yok, ağ yok.

    <bpy kurulu python> araclar/paket/rehber/render.py <model.glb> <sahne.json> <klasör> [örnek] [ölçek]

`sahne.json` (`galeri.sahne`): {"catisiz": [gizlenen adımlar], "gorunumler": [ad, ...]}. Çıktı: `<klasör>/<ad>.png`, her biri
bittiğinde `RENDER_BITTI <ad>` yazar; çatı katmanlarında etiket yerleri `<klasör>/cati_katman.json` ({anahtar: [x, y] piksel}: kaplama,
aşık, cam yünü, makas). Etiket noktası o türün kameradan görünen bir yüzeyidir (kameradan atılan ışın önce o türe çarpar).
"""
import json
import math
import os
import re
import sys

import bpy
import addon_utils                       # bpy'den sonra (bpy yüklenince bulunur)
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

GORUNUMLER = ("on_sol", "on_sag", "arka_sol", "catisiz", "cati_katman")


def principled(ad, renk, metal=0.0, puruz=0.5):
    m = bpy.data.materials.new(ad); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*renk, 1); b.inputs["Metallic"].default_value = metal; b.inputs["Roughness"].default_value = puruz
    return m, b


def doku(m, b, olc, guc, voronoi=False):
    nt = m.node_tree; g = nt.nodes.new("ShaderNodeNewGeometry"); bump = nt.nodes.new("ShaderNodeBump")
    if voronoi:
        t = nt.nodes.new("ShaderNodeTexVoronoi"); t.feature = "DISTANCE_TO_EDGE"; cikis = t.outputs["Distance"]
    else:
        t = nt.nodes.new("ShaderNodeTexNoise"); t.inputs["Detail"].default_value = 8; cikis = t.outputs["Fac"]
    t.inputs["Scale"].default_value = olc
    nt.links.new(g.outputs["Position"], t.inputs["Vector"]); nt.links.new(cikis, bump.inputs["Height"])
    bump.inputs["Strength"].default_value = guc; nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def izocam():
    """Cam yünü şilte: sarı, lifli (62 m²'dekiyle aynı)."""
    m, b = principled("izocam", (0.80, 0.60, 0.16), 0.0, 1.0)
    nt = m.node_tree; g = nt.nodes.new("ShaderNodeNewGeometry"); t = nt.nodes.new("ShaderNodeTexNoise")
    t.inputs["Scale"].default_value = 90; t.inputs["Detail"].default_value = 12
    cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.62, 0.44, 0.10, 1); cr.color_ramp.elements[1].color = (0.90, 0.72, 0.26, 1)
    nt.links.new(g.outputs["Position"], t.inputs["Vector"]); nt.links.new(t.outputs["Fac"], cr.inputs["Fac"]); nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
    return doku(m, b, 160, 0.6)


def cam():
    m, b = principled("cam", (0.92, 0.95, 0.97), 0.0, 0.0)
    b.inputs["Transmission Weight"].default_value = 1.0; b.inputs["IOR"].default_value = 1.5
    return m


def malzemeler() -> dict:
    """Anahtar → Blender malzemesi; 62 m² render'ının ayarları (ham malzeme: betopan, galvaniz; boyalı parçalar). Rengi eve ait olan
    anahtarlarda (`renkli`) renk GLB'den gelir (ör. beyaz ya da antrasit PVC), doku ve pürüz buradan."""
    galv = doku(*principled("galvaniz", (0.70, 0.72, 0.74), 1.0, 0.28), 900, 0.08)
    bet = doku(*principled("betopan", (0.31, 0.31, 0.30), 0.0, 0.92), 380, 0.08)
    bet_ic = doku(*principled("betopan_ic", (0.37, 0.37, 0.36), 0.0, 0.92), 380, 0.08)
    antrasit = principled("antrasit", (0.075, 0.08, 0.085), 0.25, 0.4)[0]
    return {
        "concrete": doku(*principled("beton", (0.50, 0.50, 0.48), 0.0, 0.95), 120, 0.15),
        "frame": galv, "dubel": galv, "steel": galv, "post": galv, "truss": galv, "tomega": galv, "asik": galv,
        "pdis": bet, "pic": bet_ic, "betopan": bet, "eps": doku(*principled("eps", (0.95, 0.95, 0.94), 0.0, 0.95), 300, 0.5, voronoi=True),
        "box": principled("veranda", (0.09, 0.095, 0.10), 0.3, 0.45)[0],
        "kasa": principled("kasa", (0.86, 0.86, 0.84), 0.0, 0.5)[0],
        "door": principled("ic_kapi", (0.62, 0.53, 0.40), 0.0, 0.55)[0],
        "glass": cam(),
        "cdoor": principled("celik_kapi", (0.06, 0.065, 0.07), 0.4, 0.4)[0],
        "fuga": doku(*principled("fuga", (0.13, 0.13, 0.128), 0.0, 0.95), 380, 0.05),
        "alcipan": principled("alcipan", (0.88, 0.88, 0.86), 0.0, 0.9)[0], "alcipan_y": principled("alcipan_yesil", (0.62, 0.74, 0.58), 0.0, 0.9)[0],
        "boardex": doku(*principled("boardex", (0.66, 0.65, 0.61), 0.0, 0.92), 300, 0.06), "izocam": izocam(),
        "roof": doku(*principled("kaplama", (0.085, 0.09, 0.095), 0.35, 0.36), 700, 0.03), "ridge": antrasit, "trim": antrasit, "gutter": antrasit,
    }


RENKLI = {"pvc": (0.38, 0.05)}          # anahtar → (pürüz, metal); renk GLB'den (sahne.js `D.renk`)


def main(glb, sahne_yolu, cikti, ornek=64, olcek=1.0):
    S = json.load(open(sahne_yolu, encoding="utf-8"))
    gorunumler = S.get("gorunumler") or list(GORUNUMLER)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("io_scene_gltf2", default_set=True)
    sc = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=glb)

    def adim(o):
        p = o
        while p is not None:
            m = re.match(r"(\d\d) ", p.name)
            if m:
                return int(m.group(1))
            p = p.parent
        return None

    def anahtar(o):
        return o.material_slots[0].material.name.split(".")[0] if o.material_slots and o.material_slots[0].material else None

    def merkez(o):
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        return Vector((sum(v.x for v in bb) / 8, sum(v.y for v in bb) / 8, sum(v.z for v in bb) / 8))

    nesneler = [o for o in bpy.data.objects if o.type == "MESH" and adim(o) is not None]
    plak = [o for o in bpy.data.objects if o.type == "MESH" and adim(o) is None and anahtar(o) == "concrete"]   # `glb.js`: rehberin plağı
    ANAHTAR = {o.name: anahtar(o) for o in nesneler}
    YENI = malzemeler()
    for o in plak:
        o.material_slots[0].material = YENI["concrete"]
    for o in nesneler:
        for s in o.material_slots:
            if not s.material:
                continue
            k = s.material.name.split(".")[0]
            if k in YENI:
                s.material = YENI[k]
            elif k in RENKLI:
                b = s.material.node_tree.nodes.get("Principled BSDF") if s.material.use_nodes else None
                if b is not None:
                    b.inputs["Roughness"].default_value, b.inputs["Metallic"].default_value = RENKLI[k]

    # evin kutusu (Blender: x = plan x / 100 − dış x / 2; y = plan y / 100 − dış y / 2, ön cephe y < 0; z yukarı)
    noktalar = [o.matrix_world @ Vector(c) for o in nesneler for c in o.bound_box]
    x0, x1 = min(v.x for v in noktalar), max(v.x for v in noktalar)
    y0, y1 = min(v.y for v in noktalar), max(v.y for v in noktalar)
    z1 = max(v.z for v in noktalar)
    cx, cy, sx, sy = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
    D = math.hypot(sx, sy)

    # sonsuz zemin temel plağın (GLB'den) hemen altında
    alt = min([(o.matrix_world @ Vector(c)).z for o in plak for c in o.bound_box] or [0.0])
    bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, alt - 0.001)); z = bpy.context.active_object
    z.data.materials.append(principled("zemin", (0.66, 0.66, 0.64), 0.0, 0.8)[0])

    # ışık: güneş + gri gradyan ortam (62 m² ile aynı)
    dunya = bpy.data.worlds.new("ortam"); sc.world = dunya; dunya.use_nodes = True
    wn = dunya.node_tree; bg = wn.nodes["Background"]; bg.inputs["Strength"].default_value = 0.9
    tcw = wn.nodes.new("ShaderNodeTexCoord"); sxyz = wn.nodes.new("ShaderNodeSeparateXYZ"); cr = wn.nodes.new("ShaderNodeValToRGB")
    wn.links.new(tcw.outputs["Generated"], sxyz.inputs["Vector"]); wn.links.new(sxyz.outputs["Z"], cr.inputs["Fac"])
    cr.color_ramp.elements[0].position = 0.0; cr.color_ramp.elements[0].color = (0.55, 0.55, 0.56, 1)
    cr.color_ramp.elements[1].position = 1.0; cr.color_ramp.elements[1].color = (0.98, 0.98, 1.0, 1)
    cr.color_ramp.elements.new(0.5).color = (0.84, 0.85, 0.87, 1)
    wn.links.new(cr.outputs["Color"], bg.inputs["Color"])
    gun = bpy.data.lights.new("gunes", "SUN"); gun.energy = 3.2; gun.angle = math.radians(3)
    go = bpy.data.objects.new("gunes", gun); sc.collection.objects.link(go)

    def gunes(az, yuk):
        yon = Vector((math.cos(math.radians(yuk)) * math.cos(math.radians(az)), math.cos(math.radians(yuk)) * math.sin(math.radians(az)), math.sin(math.radians(yuk))))
        go.rotation_euler = (-yon).to_track_quat("-Z", "Y").to_euler()

    kam = bpy.data.objects.new("kamera", bpy.data.cameras.new("kamera")); sc.collection.objects.link(kam); sc.camera = kam
    kam.data.clip_start = 0.05; kam.data.clip_end = 300

    def bak(konum, hedef):
        kam.location = Vector(konum); kam.rotation_euler = (Vector(hedef) - Vector(konum)).to_track_quat("-Z", "Y").to_euler()

    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = ornek
    sc.cycles.use_adaptive_sampling = True; sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6; sc.cycles.transmission_bounces = 6; sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
    sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
    sc.render.resolution_x, sc.render.resolution_y = int(1600 * olcek), int(1000 * olcek)

    # kamera: 62 m²'nin açıları evin köşegenine (D) göre; yön (x, y), yatay uzaklık, yükseklik, hedef yüksekliği, objektif, güneş
    KAM = {
        "on_sol": ((-0.57, -0.82), 1.12, 0.21, 0.50, 40, (-125, 42)),
        "on_sag": ((0.62, -0.79), 1.12, 0.21, 0.50, 40, (-35, 42)),
        "arka_sol": ((-0.63, 0.77), 1.18, 0.23, 0.50, 40, (150, 42)),
        "catisiz": ((-0.49, -0.87), 0.90, 0.84, 0.10, 32, (-50, 55)),
        "cati_katman": ((0.62, 0.78), 0.95, 0.64, 0.80, 38, (60, 48)),
    }
    h_duvar = 2.5
    for ad in gorunumler:
        (dx, dy), uz, yuk, hy, lens, (az, gy) = KAM[ad]
        gizle = set(S.get("catisiz") or []) if ad == "catisiz" else set()
        for o in nesneler:
            o.hide_render = adim(o) in gizle
            if ad == "cati_katman":   # arka-sağ çeyrekte basamaklı kesit: kaplama → aşık → makas; tavanda cam yünü
                k, c = ANAHTAR[o.name], merkez(o)
                if k in ("roof", "ridge") and c.y > cy and c.x > cx + 0.07 * sx:
                    o.hide_render = True
                if k == "asik" and c.y > cy and c.x > cx + 0.33 * sx:
                    o.hide_render = True
        hedef = (cx, cy, hy * h_duvar)
        konum = (cx + dx * uz * D, cy + dy * uz * D, yuk * D)
        kam.data.lens = lens; bak(konum, hedef); gunes(az, gy)
        bpy.context.view_layer.update()      # kameranın matrix_world'ü yenilensin (etiket yerleri bu kameradan izdüşülür)
        sc.render.filepath = os.path.join(cikti, f"{ad}.png")
        if ad == "cati_katman":
            # etiket: o türün kameradan görünen yüzeyi, hedef bölgeye en yakını. Yüzeylerden kameraya ışın; ilk çarptığı parça o türdense
            # nokta görünür (gizli parçalar ışına girmesin diye görünümde de gizlenir)
            for o in nesneler:
                o.hide_viewport = o.hide_render
            bpy.context.view_layer.update()
            dg = bpy.context.evaluated_depsgraph_get()
            etiket = {}
            hedefler = {"roof": (cx + 0.2 * sx, cy - 0.15 * sy), "asik": (cx + 0.2 * sx, cy + 0.25 * sy),
                        "izocam": (cx + 0.22 * sx, cy + 0.3 * sy), "truss": (cx + 0.42 * sx, cy + 0.3 * sy)}
            for k, (tx, ty) in hedefler.items():
                eniyi = None
                for o in nesneler:
                    if ANAHTAR[o.name] != k or o.hide_render:
                        continue
                    yuz = o.data.polygons
                    for i in range(0, len(yuz), max(1, len(yuz) // 24)):
                        p = o.matrix_world @ yuz[i].center
                        yon = p - kam.location
                        var, yer, _n, _i, vurulan, _m = sc.ray_cast(dg, kam.location, yon.normalized(), distance=yon.length + 0.02)
                        if not var or ANAHTAR.get(vurulan.name) != k:
                            continue
                        v = world_to_camera_view(sc, kam, yer)
                        if not (0.06 < v.x < 0.94 and 0.08 < v.y < 0.92 and v.z > 0):
                            continue
                        uz_ = (yer.x - tx) ** 2 + (yer.y - ty) ** 2
                        if eniyi is None or uz_ < eniyi[0]:
                            eniyi = (uz_, v)
                if eniyi:
                    v = eniyi[1]
                    etiket[k] = [round(v.x * sc.render.resolution_x), round((1 - v.y) * sc.render.resolution_y)]
            json.dump(etiket, open(os.path.join(cikti, "cati_katman.json"), "w"))
        bpy.ops.render.render(write_still=True)
        print("RENDER_BITTI", ad, flush=True)
    return z1


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    os.makedirs(a[2], exist_ok=True)
    main(a[0], a[1], a[2], int(a[3]) if len(a) > 3 else 64, float(a[4]) if len(a) > 4 else 1.0)
