import bpy,json
from pathlib import Path
from mathutils import Vector
j=json.loads(Path('work/skp_import/P9401/scene.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(Path('outputs/Uc_Model_Sunum/P9401/P9401_inceleme.blend').resolve()));out=[]
for ob in bpy.data.objects:
 node=ob.get('skp_node')
 if node not in [1,2,3,4,5,223]:continue
 n=j['nodes'][node];g=j['meshes'][n['geometry']];t=n['world_transform'];vs=[ob.matrix_world@v.co for v in ob.data.vertices];err=[]
 for i,v in enumerate(g['vertices']):
  expected=Vector([(sum(t[c*4+r]*v[c] for c in range(3))+t[12+r]*.0254)/t[15] for r in range(3)]);err.append((expected-vs[i]).length)
 out.append({'node':node,'object':ob.name,'matrix_world':[list(r) for r in ob.matrix_world],'bounds':[[min(v[k] for v in vs) for k in range(3)],[max(v[k] for v in vs) for k in range(3)]],'source_max_displacement_m':max(err,default=0)})
Path('work/p9401_cati_qa/blend_source_check.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
