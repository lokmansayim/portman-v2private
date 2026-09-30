import json,math,collections
from pathlib import Path
j=json.loads(Path('work/skp_import/P9501/scene.json').read_text())
faces=json.loads(Path('work/roof_qa/face_materials.json').read_text())
def sub(a,b):return [a[i]-b[i] for i in range(3)]
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def dot(a,b):return sum(a[i]*b[i] for i in range(3))
def world(n):
 t=n['world_transform'];g=j['meshes'][n['geometry']]
 return [[sum(t[c*4+r]*v[c] for c in range(3))+t[12+r]*.0254 for r in range(3)] for v in g['vertices']]
cyan=j['nodes'][340];g=j['meshes'][cyan['geometry']];vs=world(cyan)
for pid in [46689,46690]:
 ix=next(i for i,p in enumerate(g['source_faces']) if p==pid);a,b,c=[vs[v] for v in g['triangles'][ix]];n=cross(sub(b,a),sub(c,a));s=math.sqrt(dot(n,n));n=[v/s for v in n]
 print('cyan plane',pid,'normal',n,'point',a)
 for node in [342,359]:
  v=world(j['nodes'][node]);ds=[dot(sub(x,a),n)*1000 for x in v]
  print('red node',node,'above/below counts',sum(d>0 for d in ds),sum(d<0 for d in ds),'range mm',min(ds),max(ds),'median',sorted(ds)[len(ds)//2])
print('parallel face areas against matching cyan plane')
for cyanpid,node in [(46690,342),(46689,359)]:
 ix=next(i for i,p in enumerate(g['source_faces']) if p==cyanpid);a,b,c=[vs[v] for v in g['triangles'][ix]];normal=cross(sub(b,a),sub(c,a));length=math.sqrt(dot(normal,normal));normal=[v/length for v in normal]
 red=j['nodes'][node];rg=j['meshes'][red['geometry']];rv=world(red);summ=collections.defaultdict(lambda:[0,0,[],set()])
 for i,tri in enumerate(rg['triangles']):
  ps=[rv[v] for v in tri];cr=cross(sub(ps[1],ps[0]),sub(ps[2],ps[0]));area=math.sqrt(dot(cr,cr))/2;ds=[dot(sub(p,a),normal)*1000 for p in ps]
  key='coplanar' if max(abs(v) for v in ds)<.001 else 'raised'
  summ[key][0]+=area;summ[key][1]+=1;summ[key][2].extend(ds);summ[key][3].add(rg['source_faces'][i])
 print(node,{key:{'area_m2':v[0],'triangles':v[1],'distance_mm':[min(v[2]),max(v[2])],'face_ids':list(v[3])} for key,v in summ.items()})
 for pid in summ['coplanar'][3]:print('face',pid,faces[str(pid)])
