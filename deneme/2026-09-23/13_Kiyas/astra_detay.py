# Blender Python konsolunda: astra_incele.py'den SONRA çalışır. Hiçbir Astra dosyasını değiştirmez.
# 1) ASTRA_YanVerandali_R01 koleksiyonundaki her nesnenin özelliklerini, dünya kutusunu, malzemesini, yazısını döker.
# 2) model.blend'in bulunduğu klasörü listeler; küçük metin dosyalarının (json/csv/md/txt/py) KOPYASINI 13_Kiyas/astra_kaynak/ altına alır.
import bpy, os, json, glob, shutil, mathutils

KLASOR = glob.glob(os.path.expanduser("~/Desktop/Claude Portman*/13_Kiyas"))[0]
YOL = os.path.expanduser("~/Documents/Codex/2026-09-05/prefabrik-2-arti-1-6x8/outputs/blender-aktarim/yan-verandali-2plus1-R01/model.blend")


def kutu(o):
    if o.type not in ("MESH", "CURVE", "FONT"):
        return None
    pts = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
    mn = [min(p[i] for p in pts) for i in range(3)]; mx = [max(p[i] for p in pts) for i in range(3)]
    return [round(v * 100, 2) for v in mn] + [round(v * 100, 2) for v in mx]


kol = bpy.data.collections["ASTRA_YanVerandali_R01"]
satirlar = []
for o in kol.all_objects:
    props = {}
    for k, v in o.items():
        if k.startswith("_"):
            continue
        try:
            props[k] = v if isinstance(v, (int, float, str, bool)) else (v.to_dict() if hasattr(v, "to_dict") else (list(v) if hasattr(v, "__len__") else str(v)))
        except Exception:
            props[k] = str(v)
    r = {"ad": o.name, "tur": o.type, "ozellik": props, "kutu_cm": kutu(o), "ebat_cm": [round(v * 100, 2) for v in o.dimensions],
         "konum_cm": [round(v * 100, 2) for v in o.matrix_world.translation], "don_derece": [round(v * 57.29578, 2) for v in o.rotation_euler],
         "ebeveyn": o.parent.name if o.parent else None}
    if o.type == "MESH":
        r["malzeme"] = [m.name for m in o.data.materials if m]
        r["kose"] = len(o.data.vertices); r["yuz"] = len(o.data.polygons)
        r["mesh_ozellik"] = {k: str(v) for k, v in o.data.items() if not k.startswith("_")}
        r["modifier"] = [(m.name, m.type) for m in o.modifiers]
    if o.type == "FONT":
        r["metin"] = o.data.body
    if o.type == "CURVE":
        r["egri"] = {"bevel": round(o.data.bevel_depth * 100, 2), "extrude": round(o.data.extrude * 100, 2), "spline": len(o.data.splines)}
        r["malzeme"] = [m.name for m in o.data.materials if m]
    satirlar.append(r)

kaynak_dizin = os.path.dirname(YOL)
liste = []
hedef = os.path.join(KLASOR, "astra_kaynak")
os.makedirs(hedef, exist_ok=True)
ust = os.path.dirname(os.path.dirname(kaynak_dizin))          # .../outputs
for kok, dizinler, dosyalar in os.walk(ust):
    dizinler[:] = [d for d in dizinler if not d.startswith(".")]
    if kok.count(os.sep) - ust.count(os.sep) > 3:
        continue
    for f in dosyalar:
        p = os.path.join(kok, f)
        try:
            st = os.stat(p)
        except OSError:
            continue
        liste.append({"yol": os.path.relpath(p, ust), "bayt": st.st_size})
        if kok == kaynak_dizin and f.lower().endswith((".json", ".csv", ".md", ".txt", ".py")) and st.st_size < 5_000_000:
            shutil.copy2(p, os.path.join(hedef, f))
    if len(liste) > 600:
        break

json.dump({"kaynak": YOL, "nesneler": satirlar, "outputs_listesi": liste}, open(os.path.join(KLASOR, "astra_detay.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=0)
print("TAMAM", len(satirlar), "nesne;", len(liste), "dosya listelendi; kopya:", os.listdir(hedef))
