import bpy,sys,json
from pathlib import Path
from mathutils import Vector
code=sys.argv[sys.argv.index('--')+1];folder=Path('work/skp_import')/code
bpy.ops.wm.open_mainfile(filepath=str((folder/'source.blend').resolve()))
# Temporary section preview only; original imported scene is preserved.
for ob in list(bpy.data.objects):
 if ob.type!='MESH':continue
 verts=[ob.matrix_world@v.co for v in ob.data.vertices]
 faces=[list(p.vertices) for p in ob.data.polygons if min(verts[i].z for i in p.vertices)<2.95]
 if not faces:ob.hide_render=True
 else:
  me=bpy.data.meshes.new('preview_cut');me.from_pydata([v.co for v in ob.data.vertices],[],faces);me.materials.append(bpy.data.materials.get('Kaynak varsayilan'));ob.data=me
cam=bpy.context.scene.camera;f={'P9201':Vector((2.8,4.4,1.0)),'P9401':Vector((5.12,4.7,1.0)),'P9501':Vector((15.2,14.6,1.0))}[code];cam.location=f+Vector((9,-13,24));cam.rotation_euler=(f-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=17
sc=bpy.context.scene;sc.cycles.samples=12;sc.render.resolution_x=1000;sc.render.resolution_y=800;sc.render.filepath=str((folder/'cut.png').resolve());bpy.ops.render.render(write_still=True)
