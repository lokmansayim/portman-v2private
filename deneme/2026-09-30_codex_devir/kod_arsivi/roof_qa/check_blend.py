import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
j=json.loads(Path('work/skp_import/P9501/scene.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(Path('outputs/Uc_Model_Sunum/P9501/P9501_inceleme.blend').resolve()))
report=[]
for ob in bpy.data.objects:
 node=ob.get('skp_node')
 if node is None:continue
 n=j['nodes'][node];t=n['world_transform'];wanted=Matrix([[t[c*4+r] for c in range(4)] for r in range(4)])
 for r in range(3):wanted[r][3]*=.0254
 delta=max(abs(wanted[r][c]-ob.matrix_world[r][c]) for r in range(4) for c in range(4))
 if delta>1e-5:
  g=j['meshes'][n['geometry']];distances=[((wanted@Vector(v))-(ob.matrix_world@Vector(v))).length for v in g['vertices']]
  report.append({'node':node,'delta_max':delta,'vertex_displacement_m':max(distances),'wanted':list(map(list,wanted)),'actual':list(map(list,ob.matrix_world))})
Path('work/roof_qa/blend_matrix_differences.json').write_text(json.dumps(report))
print('differing nodes',len(report))
for r in report:
 if r['node'] in [340,342,359,368,335,353]:print(r)
