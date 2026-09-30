import bpy,json,sys
from pathlib import Path
from mathutils import Matrix,Vector
args=sys.argv[sys.argv.index('--')+1:];code=args[0]
j=json.loads((Path('work/skp_import')/code/'scene.json').read_text())
p=Path(args[1]) if len(args)>1 else Path('outputs/Uc_Model_Sunum')/code/(code+'_inceleme.blend')
bpy.ops.wm.open_mainfile(filepath=str(p.resolve()))
report={'code':code,'blend':str(p),'node_count':0,'vertex_count':0,'max_displacement_m':0,'differing_nodes':[],'count_errors':[]}
for ob in bpy.data.objects:
 node=ob.get('skp_node')
 if node is None:continue
 n=j['nodes'][node];g=j['meshes'][n['geometry']];t=n['world_transform']
 m=Matrix([[t[c*4+r] for c in range(4)] for r in range(4)])
 for r in range(3):m[r][3]*=.0254
 report['node_count']+=1
 if len(g['vertices'])!=len(ob.data.vertices):report['count_errors'].append({'node':node,'source':len(g['vertices']),'blend':len(ob.data.vertices)});continue
 errors=[((m@Vector(raw))-(ob.matrix_world@ob.data.vertices[i].co)).length for i,raw in enumerate(g['vertices'])]
 report['vertex_count']+=len(errors);err=max(errors,default=0);report['max_displacement_m']=max(err,report['max_displacement_m'])
 if err>1e-5:report['differing_nodes'].append({'node':node,'max_displacement_m':err})
report['passed']=not report['differing_nodes'] and not report['count_errors']
output=Path('work/roof_qa')/(code+'_world_check.json');output.write_text(json.dumps(report))
print(json.dumps(report))
