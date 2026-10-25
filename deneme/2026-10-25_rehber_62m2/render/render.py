"""62 m² (beşik + cumba) montaj rehberinin 3B modeli (model.glb) Blender Cycles ile.
Kullanım:
  python render.py gorunum <on_sol|on_sag|arka_sol|catisiz|cati_katman|ic_kose> <cikti.png> [ornek] [olcek]
  python render.py adim <0,1,...|hepsi> <klasör> [ornek] [olcek]
Malzemeler PK-01 render'ıyla aynı ayarda (ham malzeme: betopan, galvaniz; antrasit sac); ışık güneş + gri gradyan ortam."""
import sys, math, os, json, bpy, addon_utils
from mathutils import Vector

kip, sec, cikti = sys.argv[1], sys.argv[2], sys.argv[3]
ornek = int(sys.argv[4]) if len(sys.argv) > 4 else 64
olcek = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
D = os.path.dirname(os.path.abspath(__file__))

bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable('io_scene_gltf2', default_set=True)
sc = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=os.path.join(D, 'model.glb'))

# ---------- Malzemeler ----------
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
def osb():
    """OSB: yönlendirilmiş yonga; açık kahve, yonga dokusu (voronoi + gürültü)."""
    m, b = principled('osb', (0.55, 0.40, 0.22), 0.0, 0.85)
    nt = m.node_tree; g = nt.nodes.new('ShaderNodeNewGeometry'); v = nt.nodes.new('ShaderNodeTexVoronoi'); v.inputs['Scale'].default_value = 60
    v.feature = 'F1'; cr = nt.nodes.new('ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = (0.42, 0.29, 0.14, 1); cr.color_ramp.elements[1].color = (0.70, 0.54, 0.32, 1)
    nt.links.new(g.outputs['Position'], v.inputs['Vector']); nt.links.new(v.outputs['Color'], cr.inputs['Fac']); nt.links.new(cr.outputs['Color'], b.inputs['Base Color'])
    return doku(m, b, 140, 0.25, voronoi=True)
def nem():
    m, b = principled('nem_bariyeri', (0.62, 0.66, 0.70), 0.0, 0.75); return doku(m, b, 220, 0.12)
def cam():
    m, b = principled('cam', (0.92, 0.95, 0.97), 0.0, 0.0)
    b.inputs['Transmission Weight'].default_value = 1.0; b.inputs['IOR'].default_value = 1.5
    return m

GALV, BET, BET_IC, EPS = galvaniz(), betopan(), betopan(0.06), eps()
ANTRASIT = boyali('antrasit', (0.075, 0.08, 0.085), 0.4, 0.25)
TRAPEZ = doku(*principled('trapez', (0.085, 0.09, 0.095), 0.35, 0.36), 700, 0.03)
YENI = {
    'concrete': doku(*principled('beton', (0.50, 0.50, 0.48), 0.0, 0.95), 120, 0.15),
    'frame': GALV, 'dubel': GALV, 'steel': GALV, 'post': GALV, 'truss': GALV, 'tomega': GALV, 'asik': GALV,
    'pdis': BET, 'pic': BET_IC, 'eps': EPS, 'betopan': BET,
    'box': boyali('veranda', (0.09, 0.095, 0.10), 0.45, 0.3),
    'kasa': boyali('kasa', (0.86, 0.86, 0.84), 0.5, 0.0),
    'door': boyali('ic_kapi', (0.62, 0.53, 0.40), 0.55, 0.0),
    'pvc': boyali('pvc_antrasit', (0.11, 0.115, 0.125), 0.38, 0.05),
    'glass': cam(),
    'cdoor': boyali('celik_kapi', (0.06, 0.065, 0.07), 0.4, 0.4),
    'osb': osb(), 'nem': nem(),
    'roof': TRAPEZ, 'ridge': ANTRASIT, 'trim': ANTRASIT, 'gutter': ANTRASIT,
}
def adim(o):
    p = o
    while p is not None:
        if p.name.startswith('s') and '_' in p.name:
            try: return int(p.name[1:p.name.index('_')])
            except ValueError: pass
        p = p.parent
    return None
def anahtar(o):
    return o.material_slots[0].material.name.split('.')[0] if o.material_slots and o.material_slots[0].material else None
def merkez(o):
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector((sum(v.x for v in bb) / 8, sum(v.y for v in bb) / 8, sum(v.z for v in bb) / 8))
nesneler = [o for o in bpy.data.objects if o.type == 'MESH' and adim(o) is not None]
for o in nesneler:
    for s in o.material_slots:
        if s.material:
            k = s.material.name.split('.')[0]
            if k in YENI: s.material = YENI[k]

# Temel plak (veranda dahil; rehberdeki gibi 12 cm taşkın, 12 cm kalın) ve sonsuz zemin
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -0.75, -0.06)); t = bpy.context.active_object
t.scale = (9.24, 7.74, 0.12); t.data.materials.append(YENI['concrete'])
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
gun = bpy.data.lights.new('gunes', 'SUN'); gun.energy = 3.2; gun.angle = math.radians(3)
go = bpy.data.objects.new('gunes', gun); sc.collection.objects.link(go)
def gunes(az, yuk):
    yon = Vector((math.cos(math.radians(yuk)) * math.cos(math.radians(az)), math.cos(math.radians(yuk)) * math.sin(math.radians(az)), math.sin(math.radians(yuk))))
    go.rotation_euler = (-yon).to_track_quat('-Z', 'Y').to_euler()

kam = bpy.data.objects.new('kamera', bpy.data.cameras.new('kamera')); sc.collection.objects.link(kam); sc.camera = kam
kam.data.clip_start = 0.05; kam.data.clip_end = 200
def bak(konum, hedef):
    kam.location = Vector(konum); kam.rotation_euler = (Vector(hedef) - Vector(konum)).to_track_quat('-Z', 'Y').to_euler()

sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = ornek
sc.cycles.use_adaptive_sampling = True; sc.cycles.use_denoising = True
sc.cycles.max_bounces = 6; sc.cycles.transmission_bounces = 6; sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
sc.render.threads_mode = 'FIXED'; sc.render.threads = 2
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'

# Blender koordinatı: x = plan x / 100 − 4,5; y = plan y / 100 − 3; z = yükseklik / 100
KAM = {  # konum, hedef, objektif (mm), güneş (azimut, yükseklik)
    'on_sol':   ((-10.0, -14.2, 3.4), (-0.9, -1.2, 1.45), 40, (-125, 42)),
    'on_sag':   ((10.6, -13.4, 3.3), (0.9, -1.0, 1.5), 40, (-35, 42)),
    'arka_sol': ((-11.5, 14.0, 3.8), (-0.3, 0.3, 1.45), 40, (150, 42)),
    'catisiz':  ((-7.2, -13.0, 13.0), (0.0, -0.6, 0.6), 32, (-50, 55)),
    'cati_katman': ((10.0, 12.5, 8.6), (1.6, 1.4, 2.9), 38, (60, 48)),
    'ic_kose':  ((5.6, -8.2, 2.7), (1.4, -3.3, 2.4), 40, (-35, 42)),
}
ROOF_ADIM = set(range(8, 18))
if kip == 'gorunum':
    kp, kh, lens, (az, yuk) = KAM[sec]
    gizle = set(range(8, 18)) if sec == 'catisiz' else set()
    for o in nesneler:
        if adim(o) in gizle: o.hide_render = True
    if sec == 'cati_katman':   # arka yüzde basamaklı kesit: trapez → nem bariyeri → OSB → aşık ve makas
        kes = {'roof': 0.6, 'ridge': 0.6, 'osb': 3.0}
        for o in nesneler:
            k, c = anahtar(o), merkez(o)
            if k in kes and c.y > 0 and c.x > kes[k]: o.hide_render = True
            if k == 'nem' and c.y > 0:   # tek parça: kutuyla kes
                bpy.ops.mesh.primitive_cube_add(size=1, location=(1.8 + 5, 3, 3)); kk = bpy.context.active_object; kk.scale = (10, 6, 6); kk.hide_render = True; kk.hide_viewport = True
                md = o.modifiers.new('kes', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = kk; md.solver = 'EXACT'
    kam.data.lens = lens; bak(kp, kh); gunes(az, yuk)
    sc.render.resolution_x, sc.render.resolution_y = int(1600 * olcek), int(1000 * olcek)
    sc.render.filepath = cikti
    bpy.ops.render.render(write_still=True)
else:   # adım adım: o adıma kadarki parçalar, yeni parçalar turuncu; kamera rehberin preset() açısı
    KAMR = json.load(open(os.path.join(D, 'model_kamera.json')))
    N = len(KAMR) - 1
    ADIMLAR = list(range(0, N + 1)) if sec == 'hepsi' else [int(a) for a in sec.split(',')]
    tb = lambda v: Vector((v[0], -v[2], v[1]))   # Three (Y yukarı) → Blender (Z yukarı)
    VURGU = principled('vurgu', (0.94, 0.52, 0.06), 0.15, 0.45)[0]
    vb = VURGU.node_tree.nodes['Principled BSDF']; vb.inputs['Emission Color'].default_value = (0.94, 0.52, 0.06, 1); vb.inputs['Emission Strength'].default_value = 0.12
    kayit = [(o, adim(o), [s.material for s in o.material_slots]) for o in nesneler]
    kam.data.sensor_fit = 'VERTICAL'; kam.data.angle_y = math.radians(38)
    gunes(-35, 46)
    sc.render.resolution_x, sc.render.resolution_y = int(1280 * olcek), int(800 * olcek)
    os.makedirs(cikti, exist_ok=True)
    for A in ADIMLAR:
        ust = N if A == 0 else A
        for o, s, mats in kayit:
            o.hide_render = s > ust or (A == N and s in {9, 10, 11, 12, 13, 14, 15, 16, 17})
            for i, sl in enumerate(o.material_slots):
                yeni = mats[i]
                if A > 0 and s == A and mats[i] is not None and not mats[i].name.startswith('cam'): yeni = VURGU
                sl.material = yeni
        k = KAMR[A]; bak(tb(k['pos']), tb(k['hedef']))
        sc.render.filepath = os.path.join(cikti, f'adim_{A:02d}.png')
        bpy.ops.render.render(write_still=True)
        print('ADIM_BITTI', A, flush=True)
