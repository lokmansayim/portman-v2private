"""Köşe profili render'ı (Blender Cycles, bpy). Kullanım: python kose_render.py <dis|ic> <disaridan|iceriden> <cikti.png> [ornek]
Ölçüler Lokman'ın çiziminden (24.10.2026): kanat = duvar kalınlığı + 3 cm, iç kanat L - 0,5, iç tırnak 3 cm, sac 1 mm.
Pres panel: 8 mm betopan + EPS + 8 mm betopan."""
import sys, math, json, bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

tip, bakis, cikti = sys.argv[sys.argv.index('--') + 1:][:3] if '--' in sys.argv else sys.argv[1:4]
ornek = int(sys.argv[4]) if len(sys.argv) > 4 and '--' not in sys.argv else 96
CM = 0.01
SAC = 0.1 * CM
w, e, L = (10.0, 4.8, 13.0) if tip == 'dis' else (6.0, 3.0, 9.0)
dep = w
H = 55.0      # gösterilen yükseklik (cm); duvar ve profil aynı yükseklikte kesik
UZ = 45.0     # duvar boyu (cm)
BT = 0.8      # betopan kalınlığı (cm)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def mat(ad, renk, metal=0.0, puruz=0.5, kabarcik=None, gurultu=None):
    m = bpy.data.materials.new(ad); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*renk, 1)
    b.inputs['Metallic'].default_value = metal
    b.inputs['Roughness'].default_value = puruz
    if kabarcik or gurultu:
        tc = nt.nodes.new('ShaderNodeNewGeometry'); bump = nt.nodes.new('ShaderNodeBump')
        if kabarcik:   # EPS boncukları
            v = nt.nodes.new('ShaderNodeTexVoronoi'); v.feature = 'DISTANCE_TO_EDGE'; v.inputs['Scale'].default_value = kabarcik
            nt.links.new(tc.outputs['Position'], v.inputs['Vector']); nt.links.new(v.outputs['Distance'], bump.inputs['Height'])
            bump.inputs['Strength'].default_value = 0.5
        else:          # betopan / galvaniz yüzey dokusu
            n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = gurultu; n.inputs['Detail'].default_value = 8
            nt.links.new(tc.outputs['Position'], n.inputs['Vector']); nt.links.new(n.outputs['Fac'], bump.inputs['Height'])
            bump.inputs['Strength'].default_value = 0.08
        nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

CELIK = mat('galvaniz', (0.70, 0.72, 0.74), metal=1.0, puruz=0.28, gurultu=900)
BETOPAN = mat('betopan', (0.31, 0.31, 0.30), puruz=0.92, gurultu=380)
EPS = mat('eps', (0.95, 0.95, 0.94), puruz=0.95, kabarcik=300)
ZEMIN = mat('zemin', (0.72, 0.71, 0.69), puruz=0.75)

def kutu(ad, a0, a1, b0, b1, z0, z1, m):
    """Yerel a (x) ve b (y) aralığında dikdörtgen prizma (cm)."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.active_object; o.name = ad
    o.scale = ((a1 - a0) * CM, (b1 - b0) * CM, (z1 - z0) * CM)
    o.location = ((a0 + a1) / 2 * CM, (b0 + b1) / 2 * CM, (z0 + z1) / 2 * CM)
    o.data.materials.append(m)
    return o

# Köşe profili (O = dış köşe; a = biten duvar boyunca, b = içeri giren duvar boyunca)
kutu('kanat_biten', -SAC / CM, L, -SAC / CM, 0, 0, H, CELIK)
kutu('kanat_giren', -SAC / CM, 0, 0, L, 0, H, CELIK)
kutu('ic_kanat', w, w + SAC / CM, 0, L - 0.5, 0, H, CELIK)
kutu('kutu_tabani', 0, w, e, e + SAC / CM, 0, H, CELIK)
kutu('ic_tirnak', w, w + 3, dep, dep + SAC / CM, 0, H, CELIK)

# Pres paneller (8 mm betopan + EPS + 8 mm betopan)
a_bas = w + SAC / CM            # biten duvar iç kanada dayanır
kutu('biten_dis_betopan', a_bas, UZ, 0, BT, 0, H, BETOPAN)
kutu('biten_eps', a_bas, UZ, BT, dep - BT, 0, H, EPS)
kutu('biten_ic_betopan', a_bas, UZ, dep - BT, dep, 0, H, BETOPAN)
b_bas = e + SAC / CM            # içeri giren duvar kutu tabanında biter
kutu('giren_dis_betopan', 0, BT, b_bas, UZ, 0, H, BETOPAN)
kutu('giren_eps', BT, w - BT, b_bas, UZ, 0, H, EPS)
kutu('giren_ic_betopan', w - BT, w, b_bas, UZ, 0, H, BETOPAN)

# Zemin
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -0.0005)); bpy.context.active_object.data.materials.append(ZEMIN)

# Işık: büyük yumuşak alan ışığı + hafif dolgu + gri ortam
dunya = bpy.data.worlds.new('ortam'); sc.world = dunya; dunya.use_nodes = True
wn = dunya.node_tree; bg = wn.nodes['Background']; bg.inputs['Strength'].default_value = 0.22
tcw = wn.nodes.new('ShaderNodeTexCoord'); sx = wn.nodes.new('ShaderNodeSeparateXYZ'); cr = wn.nodes.new('ShaderNodeValToRGB')
wn.links.new(tcw.outputs['Generated'], sx.inputs['Vector']); wn.links.new(sx.outputs['Z'], cr.inputs['Fac'])
cr.color_ramp.elements[0].position = 0.0; cr.color_ramp.elements[0].color = (0.22, 0.22, 0.23, 1)   # ufuk altı
cr.color_ramp.elements[1].position = 1.0; cr.color_ramp.elements[1].color = (0.98, 0.98, 1.0, 1)    # tepe
el = cr.color_ramp.elements.new(0.5); el.color = (0.62, 0.63, 0.65, 1)                                # ufuk
wn.links.new(cr.outputs['Color'], bg.inputs['Color'])
def isik(ad, konum, guc, boy, hedef=(0.08, 0.08, 0.3)):
    li = bpy.data.lights.new(ad, 'AREA'); li.energy = guc; li.size = boy
    o = bpy.data.objects.new(ad, li); sc.collection.objects.link(o); o.location = konum
    d = Vector(hedef) - Vector(konum); o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
# Kamera
cam = bpy.data.objects.new('kamera', bpy.data.cameras.new('kamera')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 50
hedef = Vector((0.07, 0.07, 0.34)) if bakis == 'disaridan' else Vector((0.10, 0.10, 0.30))
yon = Vector((-0.85, -1.0, 1.05)) if bakis == 'disaridan' else Vector((1.0, 0.9, 1.0))
cam.location = hedef + yon.normalized() * (1.25 if bakis == 'disaridan' else 1.5)
cam.rotation_euler = (hedef - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.dof.use_dof = False
# Işıklar kameraya göre: anahtar sol üstten, dolgu sağdan, arka ışık karşıdan
from mathutils import Matrix
yatay = Vector((yon.x, yon.y, 0)).normalized()
def don(v, derece): return Matrix.Rotation(math.radians(derece), 3, 'Z') @ v
isik('ana', tuple(hedef + don(yatay, 60) * 1.6 + Vector((0, 0, 1.5))), 75, 1.2, tuple(hedef))
isik('dolgu', tuple(hedef + don(yatay, -75) * 2.0 + Vector((0, 0, 0.7))), 16, 2.2, tuple(hedef))
isik('arka', tuple(hedef - yatay * 1.6 + Vector((0, 0, 1.4))), 30, 1.0, tuple(hedef))

# Render ayarları
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = ornek
sc.cycles.use_denoising = True; sc.render.threads_mode = 'FIXED'; sc.render.threads = 2
sc.render.resolution_x, sc.render.resolution_y = 1100, 1000
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.render.filepath = cikti
import os
if not os.environ.get('NORENDER'): bpy.ops.render.render(write_still=True)

# Etiket noktaları (resim pikseli): sonradan yazı eklemek için
bpy.context.view_layer.update()
def px(a, b, z):
    v = world_to_camera_view(sc, cam, Vector((a * CM, b * CM, z * CM)))
    return [round(v.x * sc.render.resolution_x), round((1 - v.y) * sc.render.resolution_y)]
Z = 0.6 * H
noktalar = {'kanat_biten': px(L * 0.6, -0.1, Z), 'kanat_giren': px(-0.1, L * 0.6, Z), 'ic_kanat': px(w + 0.1, (dep + L - 0.5) / 2, Z),
            'ic_tirnak': px(w + 1.5, dep + 0.1, Z), 'kutu': px(w / 2, e / 2, H), 'eps': px(w + 25, dep / 2, H)}
json.dump(noktalar, open(cikti.replace('.png', '.json'), 'w'))
