from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,hashlib,zipfile,shutil
out=Path('outputs');p=out/'Uc_Model_Sunum'
font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',28);small=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',19)
im=Image.new('RGB',(1800,1000),'#edf0ed');d=ImageDraw.Draw(im);d.text((26,18),'PORTMAN · Üç model · SKP-inceleme-01',fill='#173a32',font=font);d.text((26,61),'Mevcut kaynak geometrisi · Katalog uyumu ve Lokman kabulü bekliyor',fill='#5b6d64',font=small)
for col,code in enumerate(['P9201','P9401','P9501']):
 x=col*600;d.text((x+22,110),code+' · dış / çatı açık',fill='#173a32',font=font)
 for row,name in enumerate(['dis_gorunus.png','cati_acik.png']):
  panel=Image.open(p/code/name).convert('RGB');panel.thumbnail((586,410));im.paste(panel,(x+(600-panel.width)//2,155+row*416))
 report=json.loads((p/code/'ifc_kontrol.json').read_text(encoding='utf-8'));assert not report['schema_issues'] and not report['geometry_errors'] and not report['saved_topology_mismatch_nodes']
 assert json.loads((p/code/'blender_son_dosya_kontrol.json').read_text())['passed']
im.save(p/'Uc_Model_Onizleme.jpg',quality=92)
for name in ['P9201_Ilk_Is_Emri.md','37_Model_Takip.md']:shutil.copyfile(out/name,p/name)
manifest=[]
for f in sorted(p.rglob('*')):
 if f.is_file() and f.name!='teslim_sha256.json' and not f.name.startswith('.') and f.suffix!='.blend1':manifest.append({'file':str(f.relative_to(p)),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(p/'teslim_sha256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
zpath=out/'Portman_Uc_Model_Inceleme_01.zip'
with zipfile.ZipFile(zpath,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for row in manifest:z.write(p/row['file'],arcname='Uc_Model_Sunum/'+row['file'])
 z.write(p/'teslim_sha256.json',arcname='Uc_Model_Sunum/teslim_sha256.json')
with zipfile.ZipFile(zpath) as z:assert z.testzip() is None
print(json.dumps({'files':len(manifest)+1,'zip':str(zpath),'bytes':zpath.stat().st_size,'verified':True}))
