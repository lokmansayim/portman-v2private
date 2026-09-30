import json,math,collections
from pathlib import Path
j=json.loads(Path('work/skp_import/P9401/scene.json').read_text());sel=json.loads(Path('work/skp_import/P9401/selected.json').read_text());out={}
def world(n):
 t=n['world_transform'];g=j['meshes'][n['geometry']]
 return [[(sum(t[c*4+r]*v[c] for c in range(3))+t[12+r]*.0254)/t[15] for r in range(3)] for v in g['vertices']]
def box(vs):return [[min(v[k] for v in vs) for k in range(3)],[max(v[k] for v in vs) for k in range(3)]]
for node in [1,2,3,4,5,223]:
 n=j['nodes'][node];g=j['meshes'][n['geometry']];vs=world(n);fs=collections.defaultdict(lambda:{'vertices':set(),'materials':set(),'triangles':0})
 for i,tri in enumerate(g['triangles']):
  pid=g['source_faces'][i];fs[pid]['vertices'].update(tuple(round(x,6) for x in vs[v]) for v in tri);fs[pid]['materials'].add(j['materials'].get(g['materials'][i] or n['material'],{}).get('name','default'));fs[pid]['triangles']+=1
 row={'node':node,'name':n['name'],'source_id':n['source_id'],'bounds':box(vs),'vertices':sorted(set(tuple(round(x,6) for x in v) for v in vs)),'faces':[{**f,'vertices':sorted(f['vertices']),'materials':sorted(f['materials']),'source_face':pid} for pid,f in fs.items()]};out[node]=row
 print('NODE',node,'bbox',row['bounds'])
 if node==223:
  for f in row['faces']:print(f)
 elif node==1:
  print('top vertices',sorted(set(tuple(round(x,6) for x in v) for v in vs if v[2]>3.1016)))
Path('work/p9401_cati_qa/source_geometry.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
