from pathlib import Path
import ctypes as C,json,math
p=Path('work/skp_import/read_skp.py').resolve();ns={'__file__':str(p)};exec(compile(p.read_text().split('\nlib.SUInitialize()')[0],str(p),'exec'),ns);globals().update(ns)
bind('SUPoint3DTransform',[C.POINTER(Transform),C.POINTER(Pt)])
report={}
for code in ['P9201','P9401','P9501']:
 j=json.loads((Path('work/skp_import')/code/'scene.json').read_text());sel=json.loads((Path('work/skp_import')/code/'selected.json').read_text());selected={n['id'] for n in sel['nodes']}
 nonunit=[n for n in j['nodes'] if abs(n.get('source_world_transform_raw',n['world_transform'])[15]-1)>1e-9];stats={'nonunit_nodes':len(nonunit),'nonunit_selected':sum(n['id'] in selected for n in nonunit),'projective_nodes':sum(any(abs(n['world_transform'][i])>1e-9 for i in [3,7,11]) for n in j['nodes']),'cases':[],'max_normalized_vs_api_m':0,'max_previous_vs_api_m':0}
 cases=nonunit+([j['nodes'][340],j['nodes'][359]] if code=='P9501' else [])
 for n in cases:
  t=n.get('source_world_transform_raw',n['world_transform']);vs=j['meshes'][n['geometry']]['vertices'];tr=Transform((C.c_double*16)(*t))
  for i in sorted({0,len(vs)//2,len(vs)-1}):
   v=vs[i];point=Pt(*(x/.0254 for x in v));ok(lib.SUPoint3DTransform(C.byref(tr),C.byref(point)));api=[point.x*.0254,point.y*.0254,point.z*.0254];old=[sum(t[c*4+r]*v[c] for c in range(3))+t[12+r]*.0254 for r in range(3)];norm=[x/t[15] for x in old];d=lambda a,b:math.sqrt(sum((x-y)**2 for x,y in zip(a,b)));error=d(norm,api);old_error=d(old,api)
   stats['max_normalized_vs_api_m']=max(stats['max_normalized_vs_api_m'],error);stats['max_previous_vs_api_m']=max(stats['max_previous_vs_api_m'],old_error)
   stats['cases'].append({'node':n['id'],'source_id':n.get('source_id'),'vertex':i,'w':t[15],'api_world_m':api,'normalized_world_m':norm,'previous_world_m':old,'normalized_error_m':error,'previous_error_m':old_error})
 report[code]=stats
Path('work/roof_qa/homogeneous_api_check.json').write_text(json.dumps(report,indent=2))
for code,s in report.items():print(code,{k:v for k,v in s.items() if k!='cases'})
for c in report['P9501']['cases']:
 if c['node'] in [43,59,106] and c['vertex']==0:print(c)
