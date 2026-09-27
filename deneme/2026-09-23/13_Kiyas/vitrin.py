# Konsol alanını 3B görünüme çevirir; iki modeli yan yana, bizim çatı/makaslar gizli (Outliner'dan açılabilir) gösterir.
import bpy, mathutils

for o in bpy.data.objects:
    n = o.name
    if n.startswith(("IfcRoof", "IfcElementAssembly", "IfcMember/MAKAS", "IfcPlate/ALIN", "IfcSlab/CATI")):
        try: o.hide_set(True)
        except Exception: pass
    if n.startswith(("IfcSpace", "IfcOpeningElement")):
        try: o.hide_set(True)
        except Exception: pass


def _gorunum():
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            if a.type == "VIEW_3D":
                s = a.spaces.active
                s.shading.type = "SOLID"; s.shading.color_type = "MATERIAL"; s.shading.show_cavity = True; s.shading.show_shadows = True
                s.overlay.show_floor = True
                r = s.region_3d
                r.view_perspective = "PERSP"
                r.view_location = (9.37, 5.2, 0.8)
                r.view_distance = 25.0
                r.view_rotation = mathutils.Euler((0.95, 0.0, 0.22)).to_quaternion()
                a.tag_redraw()
    return None


bpy.app.timers.register(_gorunum, first_interval=0.6)
bpy.context.area.type = "VIEW_3D"
