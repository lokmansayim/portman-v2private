# Blender Python konsolunda, astra_incele.py'den SONRA: exec(open(".../13_Kiyas/yukle_bizim_ifc.py").read())
# 1) Astra'nın Yan Verandalı modelini bu açık sahnede +11 m x yönüne kaydırır (Astra'nın .blend dosyası değişmez).
# 2) Bizim IFC'yi (Motor İş Emri → IFC) Bonsai ile aynı sahneye yükler.
# 3) Workbench ile üç karşılaştırma görüntüsü alır: 13_Kiyas/kiyas_01..03.png
import bpy, os, glob, math, mathutils

K = glob.glob(os.path.expanduser("~/Desktop/Claude Portman*/13_Kiyas"))[0]
IFC = os.path.join(K, "YanVerandali_2plus1_Motor.ifc")
DX = 11.0
sc = bpy.context.scene

a = bpy.data.collections.get("ASTRA_YanVerandali_R01")
if a is not None and not a.get("kaydirma_m"):
    for o in a.all_objects:
        if o.parent is None:
            o.location.x += DX
    a["kaydirma_m"] = DX
p = bpy.data.collections.get("ASTRA_PEV_5x4_R01")
if p is not None:
    p.hide_viewport = True; p.hide_render = True

onceki = set(bpy.data.objects.keys())
if not any(n.startswith("IfcWall/") for n in onceki):
    bpy.ops.bim.load_project(filepath=IFC, should_start_fresh_session=False)
bizim = [o for o in bpy.data.objects if o.name not in onceki or o.name.startswith("Ifc")]

# etiketler (yere yatık yazı)
def yazi(ad, metin, x, y, boy=0.42):
    o = bpy.data.objects.get(ad)
    if o is None:
        cu = bpy.data.curves.new(ad, "FONT"); cu.body = metin; cu.size = boy; cu.align_x = "CENTER"
        o = bpy.data.objects.new(ad, cu); sc.collection.objects.link(o)
    o.location = (x, y, 0.01)
    return o
yazi("ETIKET_PORTMAN", "PORTMAN  Motor Is Emri -> IFC (Bonsai)", 3.865, -1.6)
yazi("ETIKET_ASTRA", "ASTRA  DWG -> Blender aktarimi", DX + 3.865, -1.6)

# görüntü ayarları
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"; sh.color_type = "MATERIAL"; sh.show_cavity = True; sh.cavity_type = "BOTH"; sh.show_shadows = True
sh.show_object_outline = True
sc.render.resolution_x, sc.render.resolution_y = 1800, 1000
sc.render.film_transparent = False
if sc.world is None:
    sc.world = bpy.data.worlds.new("Dunya")
sc.world.color = (0.86, 0.88, 0.9)

def kamera(ad, konum, hedef, orto=None, lens=30):
    cam = bpy.data.cameras.get(ad) or bpy.data.cameras.new(ad)
    cam.type = "ORTHO" if orto else "PERSP"
    if orto: cam.ortho_scale = orto
    else: cam.lens = lens
    cam.clip_end = 500
    o = bpy.data.objects.get(ad) or bpy.data.objects.new(ad, cam)
    if o.name not in sc.collection.objects: sc.collection.objects.link(o)
    o.location = konum
    o.rotation_euler = (mathutils.Vector(hedef) - mathutils.Vector(konum)).to_track_quat("-Z", "Y").to_euler()
    return o

def cati_mi(o):
    n = o.name
    return n.startswith(("IfcRoof", "IfcElementAssembly", "IfcMember/MAKAS", "IfcPlate/ALIN")) or n.startswith("IfcSlab/CATI")

gizli_hep = [o for o in bpy.data.objects if o.name.startswith(("IfcSpace", "IfcOpeningElement", "IfcSite", "IfcBuilding"))]
for o in gizli_hep:
    o.hide_render = True

def cek(dosya, kam, cati_gizle):
    for o in bizim:
        if cati_mi(o): o.hide_render = cati_gizle
    sc.camera = kam
    sc.render.filepath = os.path.join(K, dosya)
    bpy.ops.render.render(write_still=True)

cx = (0 + DX + 7.73) / 2
cek("kiyas_01_perspektif.png", kamera("KIYAS_KAM_1", (cx + 4, -15.5, 11.0), (cx, 5.2, 0.8), lens=26), False)
cek("kiyas_02_catisiz.png", kamera("KIYAS_KAM_2", (cx - 3, -11.0, 15.5), (cx, 5.6, 0.0), lens=26), True)
cek("kiyas_03_ust_plan.png", kamera("KIYAS_KAM_3", (cx, 5.2, 40.0), (cx, 5.2, 0.0), orto=21.5), True)

sayi = {}
for o in bizim:
    k = o.name.split("/")[0]; sayi[k] = sayi.get(k, 0) + 1
print("TAMAM bizim IFC nesneleri:", sayi)
