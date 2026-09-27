# Blender Python konsolunda: exec(open(".../13_Kiyas/astra_incele.py").read())
# Astra'nın .blend dosyalarını mevcut sahneye "ASTRA_..." koleksiyonu olarak ekler (dosyaları değiştirmez) ve envanter çıkarır.
import bpy, os, json, mathutils
from collections import Counter

EV = os.path.expanduser("~")
KLASOR = os.path.join(EV, "Desktop", "Claude Portman Çalışması", "13_Kiyas")
DOSYALAR = {
    "ASTRA_YanVerandali_R01": os.path.join(EV, "Documents/Codex/2026-09-05/prefabrik-2-arti-1-6x8/outputs/blender-aktarim/yan-verandali-2plus1-R01/model.blend"),
    "ASTRA_PEV_5x4_R01": os.path.join(EV, ".codex/.chatgpt-projects/g-p-6a9ea230a0d48191ada01d0bf8806a28/PEV_5x4_R01.blend"),
}


def bbox(obs):
    pts = [o.matrix_world @ mathutils.Vector(c) for o in obs if o.type in ("MESH", "CURVE") for c in o.bound_box]
    if not pts:
        return None
    mn = [min(p[i] for p in pts) for i in range(3)]; mx = [max(p[i] for p in pts) for i in range(3)]
    return {"min_m": [round(v, 3) for v in mn], "max_m": [round(v, 3) for v in mx], "boyut_cm": [round((mx[i] - mn[i]) * 100, 1) for i in range(3)]}


rapor = {}
for ad, yol in DOSYALAR.items():
    if not os.path.exists(yol):
        rapor[ad] = {"hata": "dosya yok", "yol": yol}; continue
    with bpy.data.libraries.load(yol, link=False) as (src, dst):
        dst.objects = list(src.objects)
        kaynak_koleksiyonlar = list(src.collections)
        kaynak_sahneler = list(src.scenes)
    kol = bpy.data.collections.get(ad) or bpy.data.collections.new(ad)
    if kol.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(kol)
    obs = [o for o in dst.objects if o is not None]
    for o in obs:
        if not o.users_collection:
            kol.objects.link(o)
    turler = Counter(o.type for o in obs)
    ozellikli = []
    for o in obs:
        props = {k: (v if isinstance(v, (int, float, str, bool)) else str(v)) for k, v in o.items() if not k.startswith("_")}
        if props:
            ozellikli.append({"ad": o.name, "ozellik": props})
    isimler = Counter()
    for o in obs:
        kok = o.name.split(".")[0].rstrip("0123456789_-")
        isimler[kok] += 1
    mal = Counter(m.name for o in obs if o.type == "MESH" for m in o.data.materials if m)
    mesh_obs = [o for o in obs if o.type == "MESH"]
    boyutlar = Counter()
    for o in mesh_obs:
        d = sorted([round(v * 100, 1) for v in o.dimensions])
        boyutlar[tuple(d)] += 1
    rapor[ad] = {
        "yol": yol, "nesne": len(obs), "tur": dict(turler), "koleksiyonlar": kaynak_koleksiyonlar, "sahneler": kaynak_sahneler,
        "genel_kutu": bbox(obs), "isim_kokleri": dict(isimler.most_common(60)), "malzemeler": dict(mal.most_common(30)),
        "en_sik_mesh_boyutlari_cm": [[list(k), v] for k, v in boyutlar.most_common(25)],
        "ozellikli_nesne": len(ozellikli), "ozellik_ornekleri": ozellikli[:25],
        "tum_nesneler": [{"ad": o.name, "tur": o.type, "boyut_cm": [round(v * 100, 1) for v in o.dimensions],
                          "konum_m": [round(v, 3) for v in o.matrix_world.translation]} for o in obs][:400],
    }
    # ASTRA modelini sahnede yana kaydır (karşılaştırma için: +x yönünde 15 m)
    if ad == "ASTRA_PEV_5x4_R01":
        kol.hide_viewport = True
json.dump(rapor, open(os.path.join(KLASOR, "astra_model_rapor.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("TAMAM", {k: v.get("nesne") for k, v in rapor.items()})
