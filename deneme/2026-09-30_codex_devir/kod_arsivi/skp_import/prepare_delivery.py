from pathlib import Path
import json,hashlib,shutil
from PIL import Image,ImageOps,ImageDraw,ImageFont
base=Path.cwd();out=base/'outputs';p=out/'Uc_Model_Sunum'
# Add the static cutaway link alongside the interactive control.
f=p/'Incele.html';s=f.read_text(encoding='utf-8');s=s.replace('<details><summary>Kaynak ve sınırlar</summary>','<a class="action" id="cut" href="P9201/cati_acik.png" target="_blank">Çatı açık görsel</a><details><summary>Kaynak ve sınırlar</summary>');s=s.replace("$('still').href=c+'/dis_gorunus.png';","$('still').href=c+'/dis_gorunus.png';$('cut').href=c+'/cati_acik.png';")
s=s.replace('Kaynak renkleri korunmuştur; katalogdaki nihai ürün renkleriyle aynı olmayabilir.','Kaynak ön yüz malzemeleri aktarılmıştır; katalogdaki nihai ürün renkleriyle aynı olmayabilir. Yüz yönü ve malzeme görünümü ayrıca gözden geçirilecek.')
s=s.replace("function clear(){for(const o of objects){o.geometry.dispose();}group.clear();objects=[];}","function clear(){const ms=new Set(),ts=new Set();for(const o of objects){o.geometry.dispose();for(const m of (Array.isArray(o.material)?o.material:[o.material])){ms.add(m);if(m.map)ts.add(m.map)}}ts.forEach(t=>t.dispose());ms.forEach(m=>m.dispose());group.clear();objects=[];}")
f.write_text(s,encoding='utf-8')
# Source and acceptance tracking update, without changing the historic r01 package.
f=out/'P9201_Ilk_Is_Emri.md';s=f.read_text(encoding='utf-8').replace('Uygulama başlamadı; çizim kabulü ve canlı entegrasyon yok.','SKP-inceleme-01 sunumları ve geometrik IFC hazır; r01 düzeltmesi, çizim kabulü ve canlı entegrasyon yapılmadı.').replace("Bu belgenin sürümü 01'dir; çizim revizyonu değildir.","Bu belgenin sürümü 02'dir; çizim revizyonu değildir.")
s=s.replace('Arşivde `92 M2 PEYZAJLI.skp` mevcut; içeriği doğrulanmadı, üretim referansı sayılmaz.','Arşivdeki `92 M2 PEYZAJLI.skp` geometri olarak açıldı. SHA-256: `31fc08e97bbeee8483cbca308e0648bb10e87d96b187d3bd9ff9e07b214777fc`. SKP-inceleme-01 sunumunun kaynağıdır; JPG/DWG revizyon uyumu ve üretim kabulü bekliyor.')
s=s.replace('Mevcut sonuç: kaynak incelemesi tamamlandı; uygulama ve yeni çizim üretimi başlamadı; r01 kaynak uyumu kabul edilmedi; Lokman kabulü bekliyor; canlı entegrasyon yok.','Mevcut sonuç: ilk kaynak incelemesi ve mevcut SKP üzerinden üç sunum biçimi + geometrik IFC4 hazır. Bu çıktı SKP-inceleme-01 adını taşır; düzeltilmiş motor r02 çıktısı değildir. r01 kaynak uyumu kabul edilmedi; ölçülü 2D düzeltmesi, Lokman kabulü ve Claude entegrasyonu bekliyor. Ayrıntılar: `Uc_Model_Sunum/OKU.md`.')
f.write_text(s,encoding='utf-8')
f=out/'37_Model_Takip.md';s=f.read_text(encoding='utf-8').replace('P9201 dışında kaynak çizimleri bu tur incelenmedi.','İlk üç modelin JPG planları, eski r01 kayıtları ve SKP geometrileri incelendi; kaynaklar arası ölçü/revizyon eşleştirmesi tamamlanmadı.')
rows={
'| 1 | P9201 |':'| 1 | P9201 | 92 / 3+1 | PS-1092.jpg; 92 M2 PEYZAJLI.skp; r01 DXF çıkarımı | SKP-inceleme-01; motor r01 ayrı | Üç sunum + geometrik IFC4 hazır | F01–F08; JPG/SKP uyumu açık | Bekliyor | IFC aktarımı geçti; kaynak/üretim kabulü yok | Yapılmadı |',
'| 2 | P9401 |':'| 2 | P9401 | 94 / 3+1 | PS-1094.jpg; 9401.skp; r01 DXF çıkarımı | SKP-inceleme-01; motor r01 ayrı | Üç sunum + geometrik IFC4 hazır; soldaki SKP kopyası | Veranda kesimi; açıklık kaymaları; iki SKP kopyası | Bekliyor | IFC aktarımı geçti; kaynak/üretim kabulü yok | Yapılmadı |',
'| 3 | P9501 |':'| 3 | P9501 | 95 / 3+1 | PS-1095.jpg; AMASRA SKP.skp; r01 DXF çıkarımı | SKP-inceleme-01; motor r01 ayrı | Üç sunum + geometrik IFC4 hazır | r01 açıklık kaybı; kaynak/çatı/veranda farkı; malzeme görünümü | Bekliyor | IFC aktarımı geçti; kaynak/üretim kabulü yok | Yapılmadı |'}
s='\n'.join(next((v for k,v in rows.items() if line.startswith(k)),line) for line in s.splitlines())+'\n';f.write_text(s,encoding='utf-8')
# One honest overview made from delivered source renders.
font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',28);small=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',19)
im=Image.new('RGB',(1800,1000),'#edf0ed');d=ImageDraw.Draw(im);d.text((26,18),'PORTMAN · Üç model · SKP-inceleme-01',fill='#173a32',font=font);d.text((26,61),'Mevcut kaynak geometrisi · Katalog uyumu ve Lokman kabulü bekliyor',fill='#5b6d64',font=small)
for col,code in enumerate(['P9201','P9401','P9501']):
 x=col*600;d.text((x+22,110),code+' · dış görünüş',fill='#173a32',font=font)
 for row,name in enumerate(['dis_gorunus.png','cati_acik.png']):
  panel=Image.open(p/code/name).convert('RGB');panel.thumbnail((586,410));im.paste(panel,(x+(600-panel.width)//2,155+row*416))
im.save(p/'Uc_Model_Onizleme.jpg',quality=92)
# Include the source registry (no need to duplicate the 100+ MB originals).
shutil.copyfile(out/'Ilk_3_Model_Kaynaklari/Kaynak_Kaydi.json',p/'orijinal_kaynak_kaydi.json')
