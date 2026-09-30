import json,base64,io,hashlib,shutil
from pathlib import Path
from PIL import Image
OUT=Path('outputs/Uc_Model_Sunum');allmeta={}
focus={'P9201':[2.8,4.4,1.8],'P9401':[5.12,4.7,1.8],'P9501':[15.2,14.6,2]}
roofmap={'P9201':{1,67,78,114,121,137,139,145,146,154,162,170,174,203},'P9401':{223},'P9501':{332,112,371,372,373,374,375,376,377,378,328}}
excluded={'P9201':{14,87,287},'P9401':{13,221},'P9501':{9}}
for code in focus:
 raw=Path('work/skp_import')/code;j=json.loads((raw/'scene.json').read_text(encoding='utf-8'));nodes=j['nodes'];meshes=j['meshes']
 def rootid(n):
  while n['parent'] not in [0,None]:n=nodes[n['parent']]
  return n['id']
 data={'code':code,'revision':'SKP-inceleme-01','focus':focus[code],'source_sha256':j['sha256'],'nodes':[],'materials':{},'meshes':{},'notes':[]}
 texcache={}
 for k,m in j['materials'].items():
  q=dict(m)
  if m['texture']:
   p=m['texture']
   if p not in texcache:
    im=Image.open(p);im.thumbnail((1024,1024));buf=io.BytesIO();im.save(buf,format='PNG');texcache[p]='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()
   q['texture']=texcache[p]
  data['materials'][k]=q
 for n in nodes:
  if n['hidden']:continue
  top=rootid(n);r=nodes[top]
  if top in excluded[code]:continue
  # P9401 has two separate building copies; retain the left copy only.
  if code=='P9401' and top and r['bbox_parent_inches'][0][0]*.0254>12:continue
  g=meshes[n['geometry']]
  if not g['triangles']:continue
  isroof=top in roofmap[code]
  bounds=r.get('bbox_parent_inches',[[0,0,0],[0,0,0]])
  minz=bounds[0][2]*.0254; maxz=bounds[1][2]*.0254
  stage=3 if isroof else (0 if maxz<.65 or top==0 else (1 if n['face_count']>70 and maxz-minz>2 else 2))
  item={k:n[k] for k in ['id','name','source_id','world_transform','material','geometry'] if k in n};item.update(root=top,roof=isroof,stage=stage)
  data['nodes'].append(item)
  if n['geometry'] not in data['meshes']:
   data['meshes'][n['geometry']]={k:g[k] for k in ['vertices','triangles','uv','materials']}
   data['meshes'][n['geometry']]['vertices']=[[round(x,7) for x in v] for v in g['vertices']]
 data['nodes'].sort(key=lambda n:(n['stage'],n['root'],n['id']))
 if code=='P9401':data['notes'].append('SKP dosyasındaki soldaki yapı kopyası gösteriliyor; ikinci kopya kaynakta korunuyor.')
 data['notes'].append('Kaynak SKP inceleme modeli. JPG/DWG ile revizyon uyumu ve teknik kabul bekliyor.')
 (OUT/code/'model.js').write_text('window.PORTMAN_MODELS=window.PORTMAN_MODELS||{};window.PORTMAN_MODELS['+json.dumps(code)+']='+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')
 (raw/'selected.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
 plan=next((Path('outputs/Ilk_3_Model_Kaynaklari')/code).glob('PS-*.jpg'));shutil.copy2(plan,OUT/code/'kaynak_plan.jpg')
 allmeta[code]={'source':j['source'],'sha256':j['sha256'],'nodes':len(data['nodes']),'triangles':sum(len(meshes[n['geometry']]['triangles']) for n in data['nodes']),'revision':data['revision'],'excluded_top_nodes':list(excluded[code]),'roof_top_nodes':sorted(roofmap[code]),'notes':data['notes']}
 print(code,allmeta[code]['nodes'],allmeta[code]['triangles'])
(OUT/'kaynak_manifest.json').write_text(json.dumps(allmeta,ensure_ascii=False,indent=2),encoding='utf-8')
