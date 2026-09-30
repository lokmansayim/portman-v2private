import sys,json,uuid,collections
from pathlib import Path
sys.path.insert(0,str(Path('work/ifc_runtime').resolve()))
import ifcopenshell,ifcopenshell.guid
from mathutils import Matrix,Vector
for code in ['P9201','P9401','P9501']:
 folder=Path('outputs/Uc_Model_Sunum')/code;reportpath=folder/'ifc_kontrol.json'
 if not reportpath.exists():continue
 d=json.loads((Path('work/skp_import')/code/'selected.json').read_text(encoding='utf-8'));f=ifcopenshell.open(str(folder/f'{code}_referans.ifc'));maxdelta=0;mis=[];written=0
 for n in d['nodes']:
  guid=ifcopenshell.guid.compress(uuid.uuid5(uuid.NAMESPACE_URL,d['source_sha256']+'/'+code+'/'+str(n['id'])).hex);ob=f.by_guid(guid);items=ob.Representation.Representations[0].Items;mesh=d['meshes'][n['geometry']];t=n['world_transform'];mat=Matrix([[t[c*4+r] for c in range(4)] for r in range(4)])
  for r in range(3):mat[r][3]*=.0254
  verts=[tuple(mat@Vector(v)) for v in mesh['vertices']];stored=items[0].Coordinates.CoordList
  if len(verts)!=len(stored):mis.append(n['id']);continue
  maxdelta=max(maxdelta,max(abs(a-b) for va,vb in zip(verts,stored) for a,b in zip(va,vb)))
  want=collections.Counter(tuple(i+1 for i in tri) for tri in mesh['triangles']);got=collections.Counter(tuple(tri) for item in items for tri in item.CoordIndex);written+=sum(got.values())
  if want!=got:mis.append(n['id'])
 report=json.loads(reportpath.read_text(encoding='utf-8'));report.update(saved_triangles=written,saved_coordinate_max_delta_m=maxdelta,saved_topology_mismatch_nodes=mis,geometry_engine_note='Geometri motorunun yeniden üçgenleme sayısı kaynak/saklanan yüz sayısından farklı olabilir; saklanan koordinat ve üçgen bağlantıları ayrıca karşılaştırıldı.')
 reportpath.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(code,written,maxdelta,mis)
