# Blender Python konsolunda çalışır: exec(open(".../13_Kiyas/bul.py").read())
# .blend dosyalarını ve Blender'ın son dosyalar listesini bulur, sonucu 13_Kiyas/blend_arama.json'a yazar. Hiçbir dosyayı değiştirmez.
import os, json, time, bpy, addon_utils
ev = os.path.expanduser("~")
cikti = os.path.join(ev, "Desktop", "Claude Portman Çalışması", "13_Kiyas", "blend_arama.json")
atla = {"Library", ".Trash", "node_modules", ".cache", ".git", "Applications", "anaconda3", ".anaconda", ".conda", "Pictures", "Music", "Movies"}
bulunan = []
t0 = time.time()
for kok, dizinler, dosyalar in os.walk(ev):
    dizinler[:] = [d for d in dizinler if d not in atla and not d.startswith(".")]
    for f in dosyalar:
        if f.lower().endswith((".blend", ".ifc")):
            p = os.path.join(kok, f)
            try:
                st = os.stat(p)
                bulunan.append({"yol": p, "boyut": st.st_size, "degisme": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))})
            except OSError:
                pass
    if time.time() - t0 > 60:
        break
son = []
rf = os.path.join(bpy.utils.user_resource("CONFIG"), "recent-files.txt")
if os.path.exists(rf):
    son = [s.strip() for s in open(rf, encoding="utf-8") if s.strip()]
bonsai = [m.__name__ for m in addon_utils.modules() if "bonsai" in m.__name__.lower() or "blenderbim" in m.__name__.lower()]
sonuc = {"blender": bpy.app.version_string, "son_dosyalar": son, "bulunan": sorted(bulunan, key=lambda d: d["degisme"], reverse=True),
         "bonsai_modulleri": bonsai, "cevrimici_erisim": bpy.context.preferences.system.use_online_access,
         "depolar": [(r.name, r.remote_url, r.enabled) for r in bpy.context.preferences.extensions.repos], "sure_s": round(time.time() - t0, 1)}
os.makedirs(os.path.dirname(cikti), exist_ok=True)
json.dump(sonuc, open(cikti, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("TAMAM:", cikti, len(bulunan), "dosya")
