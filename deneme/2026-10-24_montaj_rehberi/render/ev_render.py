"""PK-01 (60 m²) evinin tamamı: montaj rehberindeki 3B model (huma.glb) Blender Cycles ile.
Kullanım: python ev_render.py <on_sag|arka_sol|catisiz> <cikti.png> [ornek] [olcek]
Malzemeler köşe render'ıyla aynı ayarda; ışık ev ölçeğine göre güneş + gri ortam."""
import sys, math, os, bpy, addon_utils
from mathutils import Vector

gorunum, cikti = sys.argv[1], sys.argv[2]
ornek = int(sys.argv[3]) if len(sys.argv) > 3 else 64
olcek = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
D = os.path.dirname(os.path.abspath(__file__))

bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable('io_scene_gltf2', default_set=True)
sc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=os.path.join(D, 'huma.glb'))

# ---------- Malzemeler (köşe render'ıyla aynı) ----------
def principled(ad, renk, metal=0.0, puruz=0.5):
    m = bpy.data.materials.new(ad); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*renk, 1); b.inputs['Metallic'].default_value = metal; b.inputs['Roughness'].default_value = puruz
    return m, b

def doku(m, b, olc, guc, voronoi=False):
    nt = m.node_tree; g = nt.nodes.new('ShaderNodeNewGeometry'); bump = nt.nodes.new('ShaderNodeBump')
    if voronoi:
        t = nt.nodes.new('ShaderNodeTexVoronoi'); t.feature = 'DISTANCE_TO_EDGE'; cikis = t.outputs['Distance']
    else:
        t = nt.nodes.new('ShaderNodeTexNoise'); t.inputs['Detail'].default_value = 8; cikis = t.outputs['Fac']
    t.inputs['Scale'].default_value = olc
    nt.links.new(g.outputs['Position'], t.inputs['Vector']); nt.links.new(cikis, bump.inputs['Height'])
    bump.inputs['Strength'].default_value = guc; nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

def galvaniz():
    m, b = principled('galvaniz', (0.70, 0.72, 0.74), 1.0, 0.28); return doku(m, b, 900, 0.08)
def betopan(acik=0.0):
    m, b = principled('betopan', (0.31 + acik, 0.31 + acik, 0.30 + acik), 0.0, 0.92); return doku(m, b, 380, 0.08)
def eps():
    m, b = principled('eps', (0.95, 0.95, 0.94), 0.0, 0.95); return doku(m, b, 300, 0.5, voronoi=True)
def boyali(ad, renk, puruz=0.42, metal=0.25):
    m, _ = principled(ad, renk, metal, puruz); return m
def cati():
    """Sandviç panel: antrasit boyalı sac, trapez hadveler eğim boyunca (25 cm aralık)."""
    m, b = principled('cati_sandvic', (0.075, 0.08, 0.085), 0.25, 0.38)
    nt = m.node_tree; g = nt.nodes.new('ShaderNodeNewGeometry'); w = nt.nodes.new('ShaderNodeTexWave')
    w.wave_type = 'BANDS'; w.bands_direction = 'Y'; w.inputs['Scale'].default_value = 2 * math.pi / (10 * 0.25)
    cr = nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].position = 0.62; cr.color_ramp.elements[1].position = 0.80
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.6; bump.inputs['Distance'].default_value = 0.03
    nt.links.new(g.outputs['Position'], w.inputs['Vector']); nt.links.new(w.outputs['Fac'], cr.inputs['Fac'])
    nt.links.new(cr.outputs['Color'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m
def cam():
    m, b = principled('cam', (0.92, 0.95, 0.97), 0.0, 0.0)
    b.inputs['Transmission Weight'].default_value = 1.0; b.inputs['IOR'].default_value = 1.5
    return m

GALV, BET, BET_IC, EPS = galvaniz(), betopan(), betopan(0.06), eps()
ANTRASIT = boyali('antrasit', (0.075, 0.08, 0.085), 0.4, 0.25)
YENI = {
    'concrete': doku(*principled('beton', (0.50, 0.50, 0.48), 0.0, 0.95), 120, 0.15),
    'frame': GALV, 'dubel': GALV, 'steel': GALV, 'post': GALV, 'truss': GALV, 'tomega': GALV, 'asik': GALV,
    'pdis': BET, 'pic': BET_IC, 'eps': EPS, 'betopan': BET,
    'box': boyali('veranda', (0.09, 0.095, 0.10), 0.45, 0.3),
    'kasa': boyali('kasa', (0.86, 0.86, 0.84), 0.5, 0.0),
    'door': boyali('ic_kapi', (0.62, 0.53, 0.40), 0.55, 0.0),
    'pvc': boyali('pvc', (0.90, 0.90, 0.88), 0.35, 0.0),
    'glass': cam(),
    'cdoor': boyali('celik_kapi', (0.06, 0.065, 0.07), 0.4, 0.4),
    'roof': cati(), 'ridge': ANTRASIT, 'trim': ANTRASIT, 'gutter': ANTRASIT,
}

def kok(o):
    while o.parent and not o.name.startswith('s'): o = o.parent
    return o
def adim(o):
    p = o
    while p is not None:
        if p.name.startswith('s') and '_' in p.name:
            try: return int(p.name[1:p.name.index('_')])
            except ValueError: pass
        p = p.parent
    return None

gizle = set(range(9, 17)) if gorunum == 'catisiz' else set()
if gorunum == 'kalkan_kesit':   # yalnız kalkan kenarı: makas, betopan, Z, aşık, C kapama, kaplama, alın sacı
    gizle = set(range(0, 11)) | {13, 17}
for o in list(bpy.data.objects):
    if o.type != 'MESH': continue
    if adim(o) in gizle:
        o.hide_render = True; continue
    if gorunum == 'kalkan_kesit' and o.material_slots and o.material_slots[0].material:
        k0 = o.material_slots[0].material.name.split('.')[0]
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]; dx = max(v.x for v in bb) - min(v.x for v in bb)
        if k0 in ('gutter', 'ridge') or (k0 == 'trim' and dx < 0.5):
            o.hide_render = True; continue
    for i, s in enumerate(o.material_slots):
        if s.material:
            k = s.material.name.split('.')[0]
            if k in YENI: s.material = YENI[k]

# Temel plak (rehberdeki gibi 12 cm taşkın, 12 cm kalın)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -0.06)); t = bpy.context.active_object
t.scale = (6.24, 10.24, 0.12); t.data.materials.append(YENI['concrete'])
# Sonsuz zemin
bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, -0.121)); z = bpy.context.active_object
z.data.materials.append(boyali('zemin', (0.66, 0.66, 0.64), 0.8, 0.0))

# ---------- Işık: güneş + gri gradyan ortam ----------
dunya = bpy.data.worlds.new('ortam'); sc.world = dunya; dunya.use_nodes = True
wn = dunya.node_tree; bg = wn.nodes['Background']; bg.inputs['Strength'].default_value = 0.9
tcw = wn.nodes.new('ShaderNodeTexCoord'); sx = wn.nodes.new('ShaderNodeSeparateXYZ'); cr = wn.nodes.new('ShaderNodeValToRGB')
wn.links.new(tcw.outputs['Generated'], sx.inputs['Vector']); wn.links.new(sx.outputs['Z'], cr.inputs['Fac'])
cr.color_ramp.elements[0].position = 0.0; cr.color_ramp.elements[0].color = (0.55, 0.55, 0.56, 1)
cr.color_ramp.elements[1].position = 1.0; cr.color_ramp.elements[1].color = (0.98, 0.98, 1.0, 1)
el = cr.color_ramp.elements.new(0.5); el.color = (0.84, 0.85, 0.87, 1)
wn.links.new(cr.outputs['Color'], bg.inputs['Color'])

KAM = {  # konum, hedef, objektif (mm), güneş yönü (azimut, yükseklik derece)
    'on_sag':   ((11.5, -15.5, 3.1), (0.3, -0.6, 1.45), 40, (-35, 42)),
    'arka_sol': ((-12.0, 14.5, 3.6), (0.0, 0.6, 1.45), 40, (140, 42)),
    'catisiz':  ((-7.5, -11.5, 13.0), (0.15, 0.1, 0.6), 32, (-35, 55)),
    'kalkan':   ((-4.6, -9.0, 2.2), (-2.2, -5.2, 2.75), 50, (-35, 42)),
    'alin_ucu': ((-3.95, -5.85, 2.30), (-3.05, -5.22, 2.70), 45, (-35, 42)),
    'alin_yan': ((-2.6, -6.6, 2.55), (-1.6, -5.3, 3.05), 55, (-35, 42)),
    'kose_dere': ((-4.35, -6.35, 2.05), (-3.25, -5.25, 2.55), 40, (-35, 42)),
    'detay':    ((-6.2, -8.6, 2.5), (-3.05, -5.05, 2.05), 45, (-35, 42)),
    'kalkan_kesit': ((0, 0, 0), (0, 0, 1), 50, (-60, 35)),
}
kp, kh, lens, (az, yuk) = KAM[gorunum]
gun = bpy.data.lights.new('gunes', 'SUN'); gun.energy = 3.2; gun.angle = math.radians(3)
go = bpy.data.objects.new('gunes', gun); sc.collection.objects.link(go)
yon = Vector((math.cos(math.radians(yuk)) * math.cos(math.radians(az)), math.cos(math.radians(yuk)) * math.sin(math.radians(az)), math.sin(math.radians(yuk))))
go.rotation_euler = (-yon).to_track_quat('-Z', 'Y').to_euler()

kam = bpy.data.objects.new('kamera', bpy.data.cameras.new('kamera')); sc.collection.objects.link(kam); sc.camera = kam
kam.data.lens = lens; kam.location = kp
kam.rotation_euler = (Vector(kh) - Vector(kp)).to_track_quat('-Z', 'Y').to_euler()
if gorunum == 'kalkan_kesit':   # ön kalkanın sol yüzü, eğim boyunca alt uçtan ortografik bakış (Lokman'ın kesit çizimi gibi)
    T = math.atan(0.33); d = Vector((math.cos(T), 0, math.sin(T))); n = Vector((-math.sin(T), 0, math.cos(T)))
    C = Vector((-3.304, -5.0 - 0.10, 2.6018)) + n * 0.03
    kam.data.type = 'ORTHO'; kam.data.ortho_scale = 0.56; kam.data.clip_start = 0.01; kam.data.clip_end = 1.5 + 3.3
    kam.location = C - d * 1.5
    kam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = ornek
sc.cycles.use_adaptive_sampling = True; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 8; sc.cycles.transmission_bounces = 8; sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
sc.render.threads_mode = 'FIXED'; sc.render.threads = 2
sc.render.resolution_x, sc.render.resolution_y = int(1600 * olcek), int(1000 * olcek)
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.render.filepath = cikti
bpy.ops.render.render(write_still=True)
