import bpy,json,sys
from pathlib import Path
from mathutils import Matrix,Vector
code=sys.argv[sys.argv.index('--')+1];root=Path.cwd();raw=root/'work/skp_import'/code
j=json.loads((raw/'scene.json').read_text(encoding='utf-8'));nodes={n['id']:n for n in j['nodes']}
bpy.ops.wm.open_mainfile(filepath=str(raw/'source.blend'))
bpy.context.preferences.filepaths.save_version=0
count=0
for ob in bpy.data.objects:
 if 'skp_node' not in ob:continue
 n=nodes[ob['skp_node']];g=j['meshes'][n['geometry']];assert len(ob.data.vertices)==len(g['vertices'])
 for v,p in zip(ob.data.vertices,g['vertices']):v.co=p
 t=n['world_transform'];m=Matrix([[t[c*4+r] for c in range(4)] for r in range(4)])
 for r in range(3):m[r][3]*=.0254
 ob.data.transform(m);ob.matrix_world=Matrix.Identity(4);ob.data.update();ob['source_world_transform']=list(t);ob['transform_storage']='World coordinates baked; source shear preserved';count+=1
bpy.ops.wm.save_as_mainfile(filepath=str(raw/'source.blend'))
bpy.ops.wm.open_mainfile(filepath=str(raw/'source.blend'))
max_delta=0.;mismatch=[]
for ob in bpy.data.objects:
 if 'skp_node' not in ob:continue
 n=nodes[ob['skp_node']];g=j['meshes'][n['geometry']];t=n['world_transform']
 for v,p in zip(ob.data.vertices,g['vertices']):
  expected=[sum(t[c*4+r]*p[c] for c in range(3))+t[12+r]*.0254 for r in range(3)];actual=ob.matrix_world@v.co;err=max(abs(expected[k]-actual[k]) for k in range(3));max_delta=max(max_delta,err)
  if err>1e-4:mismatch.append(n['id']);break
report={'model':code,'revision':'SKP-inceleme-01','baked_objects':count,'max_coordinate_delta_m':max_delta,'tolerance_m':1e-4,'mismatch_nodes':mismatch,'note':'Blender shear ayrıştırması düzeltilerek tam dünya dönüşümü vertex koordinatlarına uygulandı; geometri değiştirilmedi.'}
(root/'outputs/Uc_Model_Sunum'/code/'blender_kontrol.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(report);assert not mismatch
# Finish from corrected source using the existing finalizer.
exec(compile((root/'work/skp_import/finalize_blend.py').read_text(encoding='utf-8'),'finalize_blend.py','exec'))
