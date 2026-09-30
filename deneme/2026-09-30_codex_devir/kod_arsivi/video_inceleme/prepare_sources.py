from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import hashlib, json, shutil, unicodedata
root=Path('/Users/lokmansayim/Desktop/Portatifev Toptan')
out=Path('outputs/Ilk_3_Model_Kaynaklari');out.mkdir(parents=True,exist_ok=True)
manifest=[]
for p in root.rglob('*'):
 if not p.is_file():continue
 rel=unicodedata.normalize('NFC',str(p.relative_to(root)))
 parts=rel.split('/')
 model=next((c for c in ['P9201','P9401','P9501'] if f'PORT - {c}/' in rel),None)
 dest=None
 if model and rel.startswith('İçerik Son Hali/TEK KAT PREFABRİK/') and p.suffix.lower() in ['.jpg','.jpeg','.png']:
  dest=out/model/unicodedata.normalize('NFC',p.name)
 elif model and rel.startswith('Arşiv/TEK KAT PREFABRİK/') and p.suffix.lower()=='.skp':
  dest=out/model/unicodedata.normalize('NFC',p.name)
 elif rel=='Arşiv/TEK KAT PREFABRİK/PORTATİF EV - TEK KAT PREFABRİK PLANLARI.dwg':
  dest=out/'Ortak'/'TEK_KAT_PREFABRIK_PLANLARI.dwg'
 if dest:
  dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
  digest=hashlib.sha256(p.read_bytes()).hexdigest()
  assert hashlib.sha256(dest.read_bytes()).hexdigest()==digest
  manifest.append({'source':str(p),'copy':str(dest.resolve()),'sha256':digest,'status':'Kaynak kopyası; DWG/SKP içeriği henüz açılıp doğrulanmadı' if p.suffix.lower() in ['.dwg','.skp'] else 'Kaynak görsel'})
(out/'Kaynak_Kaydi.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',32)
small=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',22)
sheet=Image.new('RGB',(1800,1350),'#f4f2ed');draw=ImageDraw.Draw(sheet)
for i,model in enumerate(['P9201','P9401','P9501']):
 x=i*600
 draw.text((x+25,22),model,fill='#192e30',font=font)
 ps=sorted((out/model).glob('PS-*.jpg'))[0]
 photo=sorted(p for p in (out/model).glob('*.jpg') if not p.name.startswith('PS-'))[0]
 for path, y, maxsize in [(ps,85,(550,750)),(photo,850,(550,400))]:
  im=Image.open(path).convert('RGB');im.thumbnail(maxsize);sheet.paste(im,(x+25+(550-im.width)//2,y))
 draw.text((x+25,1275),'Mevcut katalog kaynakları',fill='#566568',font=small)
sheet.save('outputs/Uc_Model_Kaynak_Onizleme.jpg',quality=90)
readme=['# İlk üç adayın kaynakları','', '30.09.2026 — İlk aşama üç model. IFC teslimata dahil; ayrıntılı BIM/BOM sonra. Modelleme sunumu Lokman ile seçiliyor. P9201/P9401/P9501 önceki aday sırasıdır; kesin model kabulü değildir.','', 'DWG, SKP ve görseller kaynak dosyaların aynı içerikte kopyalarıdır. Orijinaller korunmuştur. Bu üç modelin plan görselleri JPG biçimindedir. DWG/SKP iç geometri ve IFC uygunluğu henüz doğrulanmadı.','', '| Model | SketchUp | Plan |','|---|---|---|']
for m in ['P9201','P9401','P9501']:
 sk=next((out/m).glob('*.skp'));pl=next((out/m).glob('PS-*.jpg'))
 readme.append(f'| {m} | [{sk.name}](<{sk.resolve()}>) | [{pl.name}](<{pl.resolve()}>) |')
readme+=['',f'Ortak DWG: [Tek kat prefabrik planları](<{(out/"Ortak/TEK_KAT_PREFABRIK_PLANLARI.dwg").resolve()}>)','', 'Her model klasöründe mevcut dış görünüş görselleri de var. Tam kaynak yolu ve SHA-256 kimliği Kaynak_Kaydi.json içinde.','', 'Önerilen ilk sunum: malzemeli dış görünüş + çatısı gizlenmiş iç plan + ölçülü 2D + aynı revizyondan IFC. Bunlar hedef teslimlerdir; bu klasör henüz üretilmiş yeni model içermez.']
(out/'Kaynaklari_Ac.md').write_text('\n'.join(readme)+'\n')
print(f'{len(manifest)} kaynak dosyası kopyalandı ve içerik eşitliği doğrulandı.')
