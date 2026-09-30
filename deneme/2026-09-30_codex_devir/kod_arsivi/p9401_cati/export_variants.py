import sys
from pathlib import Path
script=Path('work/skp_import/export_ifc.py').read_text(encoding='utf-8')
old="code=sys.argv[sys.argv.index('--')+1];d=json.loads((Path('work/skp_import')/code/'selected.json').read_text(encoding='utf-8'));out=Path('outputs/Uc_Model_Sunum')/code"
for key in (sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['A','B','C','D']):
 new="code='P9401';d=json.loads(Path('work/p9401_cati/"+key+"_selected.json').read_text(encoding='utf-8'));out=Path('outputs/P9401_Cati_Alternatifleri/"+key+"')"
 s=script.replace(old,new).replace("path=out/f'{code}_referans.ifc'","path=out/'P9401_Cati_"+key+".ifc'")
 s=s.replace("d['source_sha256']+'/'+code+'/'+str(key)","d['source_sha256']+'/'+d['revision']+'/'+str(key)")
 s=s.replace("'Kabul':'Bekliyor'","'Kabul':'Bekliyor','Secenek':'"+key+"','ParcaDurumu':'Yeni tasarım önerisi' if n.get('proposal') else 'Kaynak SKP geometrisi'")
 s=s.replace("'scope':'SKP geometrik referans; üretim veya semantik BIM kabulü değildir'","'scope':'P9401 çatı karşılaştırması; kaynak gövde + işaretli tasarım önerisi; üretim kabulü değil'")
 s=s.replace("Name=code+' kaynak inceleme'","Name=d['revision']")
 exec(compile(s,'export_ifc_variant_'+key,'exec'),{})
