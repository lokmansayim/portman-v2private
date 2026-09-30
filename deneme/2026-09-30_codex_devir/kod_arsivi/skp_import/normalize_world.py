from pathlib import Path
import json
for code in ['P9201','P9401','P9501']:
 p=Path('work/skp_import')/code/'scene.json';j=json.loads(p.read_text(encoding='utf-8'));changed=[]
 for n in j['nodes']:
  t=n['world_transform'];assert max(abs(t[i]) for i in [3,7,11])<1e-12
  assert abs(t[15])>1e-12
  if abs(t[15]-1)>1e-12:
   n['source_world_transform_raw']=list(t);n['world_transform']=[x/t[15] for x in t];changed.append(n['id'])
 j['world_transform_normalization']='Homogeneous source matrix divided by m15 before Cartesian conversion; verified using SketchUp C API SUPoint3DTransform.'
 p.write_text(json.dumps(j,ensure_ascii=False,separators=(',',':')),encoding='utf-8');print(code,changed)
p=Path('work/skp_import/read_skp.py');s=p.read_text(encoding='utf-8');s=s.replace("full=mm(transform,list(t.values));idx=len(nodes)","full=mm(transform,list(t.values));full=[x/full[15] for x in full];idx=len(nodes)");p.write_text(s,encoding='utf-8')
