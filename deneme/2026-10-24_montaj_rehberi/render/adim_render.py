"""Montaj rehberinin adım adım render'ı: her adımda o adıma kadarki parçalar, yeni parçalar turuncu.
Kullanım: python ev_render.py <on_sag|arka_sol|catisiz> <cikti.png> [ornek] [olcek]
Malzemeler köşe render'ıyla aynı ayarda; ışık ev ölçeğine göre güneş + gri ortam."""
import sys, math, os, bpy, addon_utils
from mathutils import Vector

gorunum = 'adim'
ornek = int(sys.argv[1]) if len(sys.argv) > 1 else 32
olcek = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
ADIMLAR = [int(a) for a in sys.argv[3].split(',')] if len(sys.argv) > 3 else list(range(0, 18))
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


# ---------- Adım adım render ----------
import json
VERI = json.load(open(os.path.join(D, '..', 'rehber', 'data.json'), encoding='utf-8'))
DX, DY = VERI['dis']
X = lambda x: x / 100 - DX / 200
Z = lambda y: DY / 200 - y / 100
ODA = {r['step']: r for r in VERI['rooms']}
ROOF = {10, 11, 12, 14, 15, 16}
def oda_merkez(r):
    ax = ay = aw = 0
    for x0, y0, x1, y1 in r['rects']:
        w = (x1 - x0) * (y1 - y0); ax += (x0 + x1) / 2 * w; ay += (y0 + y1) / 2 * w; aw += w
    return ax / aw, ay / aw
P = {0: ((0, 1.5, 0), 0.62, 0.36, 15.5), 1: ((0, 0, 0), 0.45, 1.05, 13), 8: ((X(430), 1.2, Z(100)), 0.55, 0.42, 8),
     9: ((X(0), 2.3, Z(560)), -0.55, 0.42, 5.5), 10: ((X(-15), 2.45, Z(860)), -0.75, 0.15, 4.2),
     11: ((0, 2.4, 0), 0.95, 0.55, 14), 12: ((0, 2.9, 3.6), 0.25, 0.22, 10.5), 13: ((0, 2.3, 0), 0.55, 1.28, 11.5),
     14: ((0, 3.0, 0), 0.95, 0.6, 13), 15: ((0, 2.6, 0), 0.62, 0.5, 15), 16: ((0, 2.0, 0), -0.62, 0.28, 13.5), 17: ((0, 0.8, 0), 0.5, 1.0, 12)}
def kamera_three(adim):   # rehberdeki preset(step) ile aynı
    if adim in ODA:
        cx, cy = oda_merkez(ODA[adim]); t, az, el, dist = (X(cx), 0.7, Z(cy)), 0.5, 1.0, 7.2
    else:
        t, az, el, dist = P[adim]
    pos = (t[0] + math.cos(el) * math.sin(az) * dist, t[1] + math.sin(el) * dist, t[2] + math.cos(el) * math.cos(az) * dist)
    return pos, t
tb = lambda v: Vector((v[0], -v[2], v[1]))   # Three (Y yukarı) → Blender (Z yukarı)

VURGU = principled('vurgu', (0.94, 0.52, 0.06), 0.15, 0.45)[0]
vb = VURGU.node_tree.nodes['Principled BSDF']; vb.inputs['Emission Color'].default_value = (0.94, 0.52, 0.06, 1); vb.inputs['Emission Strength'].default_value = 0.12
nesneler = []
for o in bpy.data.objects:
    if o.type == 'MESH' and adim(o) is not None:
        nesneler.append((o, adim(o), [s.material for s in o.material_slots]))

kam = bpy.data.objects.new('kamera', bpy.data.cameras.new('kamera')); sc.collection.objects.link(kam); sc.camera = kam
kam.data.sensor_fit = 'VERTICAL'; kam.data.angle_y = math.radians(38); kam.data.clip_start = 0.05; kam.data.clip_end = 200
gun = bpy.data.lights.new('gunes', 'SUN'); gun.energy = 3.2; gun.angle = math.radians(3)
go = bpy.data.objects.new('gunes', gun); sc.collection.objects.link(go)
az_g, yuk_g = math.radians(-35), math.radians(46)
yon = Vector((math.cos(yuk_g) * math.cos(az_g), math.cos(yuk_g) * math.sin(az_g), math.sin(yuk_g)))
go.rotation_euler = (-yon).to_track_quat('-Z', 'Y').to_euler()

sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = ornek
sc.cycles.use_adaptive_sampling = True; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 6; sc.cycles.transmission_bounces = 6; sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
sc.render.threads_mode = 'FIXED'; sc.render.threads = 2
sc.render.resolution_x, sc.render.resolution_y = int(1280 * olcek), int(800 * olcek)
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
os.makedirs(os.path.join(D, 'adim'), exist_ok=True)
for A in ADIMLAR:
    ust = 17 if A == 0 else A
    for o, s, mats in nesneler:
        gizli = s > ust or (A == 17 and s in ROOF)
        o.hide_render = gizli
        for i, sl in enumerate(o.material_slots):
            yeni = mats[i]
            if A > 0 and s == A and mats[i] is not None and not mats[i].name.startswith('cam'):
                yeni = VURGU
            sl.material = yeni
    pos, t = kamera_three(A)
    kam.location = tb(pos)
    kam.rotation_euler = (tb(t) - tb(pos)).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(D, 'adim', f'adim_{A:02d}.png')
    bpy.ops.render.render(write_still=True)
    print('ADIM_BITTI', A, flush=True)
