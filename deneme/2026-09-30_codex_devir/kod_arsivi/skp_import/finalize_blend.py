import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
code=sys.argv[sys.argv.index('--')+1];raw=Path('work/skp_import')/code;out=Path('outputs/Uc_Model_Sunum')/code;d=json.loads((raw/'selected.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str((raw/'source.blend').resolve()))
chosen={n['id']:n for n in d['nodes']};source=bpy.data.collections['SKP_KAYNAK'];selected=[]
# Preserve unselected source copies inside a separate hidden collection.
archive=bpy.data.collections.new('KAYNAK_DIGER_KOPYALAR_GIZLI');bpy.context.scene.collection.children.link(archive);archive.hide_render=True;archive.hide_viewport=True
roofcol=bpy.data.collections.new('CATI_AC_KAPAT');bpy.context.scene.collection.children.link(roofcol)
for ob in list(source.objects):
 n=chosen.get(ob.get('skp_node'))
 if not n:
  source.objects.unlink(ob);archive.objects.link(ob);ob.hide_render=True;ob.hide_viewport=True;continue
 ob.hide_render=False;ob.hide_viewport=False;ob['revision']='SKP-inceleme-01';ob['technical_acceptance']='pending';ob['roof']=n['roof'];selected.append(ob)
 if n['roof']:source.objects.unlink(ob);roofcol.objects.link(ob)
# Source identity retained; UI animation is a presentation sequence only.
order={n['id']:i for i,n in enumerate(d['nodes'])};sc=bpy.context.scene;sc.frame_start=1;sc.frame_end=300
for ob in selected:
 frame=2+int(order[ob['skp_node']]/max(1,len(selected)-1)*260)
 ob.hide_render=True;ob.keyframe_insert(data_path='hide_render',frame=1)
 ob.hide_render=False;ob.keyframe_insert(data_path='hide_render',frame=frame)
sc.frame_set(300);sc.render.resolution_x=1400;sc.render.resolution_y=1000;sc.cycles.samples=48
f=Vector(d['focus']);cam=sc.camera;cam.location=f+Vector((16,-23,15));cam.rotation_euler=(f-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=18
# Neutral presentation ground, excluded from IFC.
bpy.ops.mesh.primitive_plane_add(size=100,location=(f.x,f.y,-.025));ground=bpy.context.object;ground.name='SUNUM_ZEMINI_IFC_DISI';ground['scope']='presentation_only';m=bpy.data.materials.new('Sunum zemin rengi');m.diffuse_color=(.68,.72,.65,1);ground.data.materials.append(m)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str((out/f'{code}_inceleme.blend').resolve()))
sc.render.filepath=str((out/'dis_gorunus.png').resolve());bpy.ops.render.render(write_still=True)
roofcol.hide_render=True;cam.location=f+Vector((10,-14,27));cam.rotation_euler=(f-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=17;sc.render.filepath=str((out/'cati_acik.png').resolve());bpy.ops.render.render(write_still=True)
print('DELIVERED',code,len(selected))
