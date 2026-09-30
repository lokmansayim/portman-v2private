import bpy,json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
args=sys.argv[sys.argv.index('--')+1:];code=args[0];j=json.loads((Path('work/skp_import')/code/'scene.json').read_text(encoding='utf-8'))
out=Path('work/skp_import')/code
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene;sc.unit_settings.system='METRIC'
mats={}
for key,raw in j['materials'].items():
 m=bpy.data.materials.new(raw['name']);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=raw['color'];p.inputs['Roughness'].default_value=.6
 if raw['texture']:
  t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(raw['texture']);m.node_tree.links.new(t.outputs['Color'],p.inputs['Base Color'])
  # Keep alpha cutouts only when the source has an alpha channel.
  m.node_tree.links.new(t.outputs['Alpha'],p.inputs['Alpha'])
 elif raw['color'][3]<1:p.inputs['Alpha'].default_value=raw['color'][3]
 mats[key]=m
base=bpy.data.materials.new('Kaynak varsayilan');base.diffuse_color=(.75,.75,.72,1);mats[None]=base
source=bpy.data.collections.new('SKP_KAYNAK');sc.collection.children.link(source)
for n in j['nodes']:
 g=j['meshes'].get(n['geometry']);
 if not g or not g['triangles']:continue
 me=bpy.data.meshes.new(f"geo_{n['id']}");me.from_pydata(g['vertices'],[],g['triangles']);me.update()
 keys=list(dict.fromkeys((v or n['material']) for v in g['materials']));idx={k:i for i,k in enumerate(keys)}
 for k in keys:me.materials.append(mats.get(k,base))
 uv=me.uv_layers.new(name='SKP_UV')
 for i,p in enumerate(me.polygons):
  p.material_index=idx[g['materials'][i] or n['material']]
  for li in p.loop_indices:uv.data[li].uv=g['uv'][me.loops[li].vertex_index]
 ob=bpy.data.objects.new(f"{n['id']:03}_{n['name']}",me);source.objects.link(ob)
 t=n['world_transform'];m=Matrix([[t[c*4+r] for c in range(4)] for r in range(4)])
 for r in range(3):m[r][3]*=.0254
 ob.matrix_world=m;ob.hide_render=n['hidden'];ob.hide_viewport=n['hidden'];ob['source_id']=n.get('source_id',0);ob['skp_node']=n['id'];ob['source_file']=j['source'];ob['source_sha256']=j['sha256'];ob['source_parent']=n['parent'] if n['parent'] is not None else -1
sc.world=bpy.data.worlds.new('Sunum ortamı');sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.68,.75,.85,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.6
bpy.ops.object.light_add(type='SUN',location=(0,0,15));sun=bpy.context.object;sun.rotation_euler=(.5,-.6,-.6);sun.data.energy=3;sun.data.angle=.12
focus={'P9201':(2.8,4.4,1.8),'P9401':(0,0,1.8),'P9501':(15.2,14.6,2)}[code]
# Optional bounding target from supplied source nodes.
if len(args)>1:
 ni=int(args[1]);ob=next(o for o in source.objects if o.get('skp_node')==ni);vs=[ob.matrix_world@Vector(c) for c in ob.bound_box];focus=tuple(sum((v for v in vs),Vector())/8)
f=Vector(focus);bpy.ops.object.camera_add(location=f+Vector((16,-22,16)));cam=bpy.context.object;cam.rotation_euler=(f-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=20;sc.camera=cam
sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True;sc.render.resolution_x=1200;sc.render.resolution_y=900;sc.render.resolution_percentage=100;sc.view_settings.view_transform='AgX';sc.render.image_settings.file_format='PNG';sc.render.filepath=str((out/'full.png').resolve())
bpy.ops.wm.save_as_mainfile(filepath=str((out/'source.blend').resolve()));bpy.ops.render.render(write_still=True)
