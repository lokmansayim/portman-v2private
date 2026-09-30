from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
p=Path('outputs/P9401_Cati_Alternatifleri');im=Image.new('RGB',(1800,1480),'#eff0ea');d=ImageDraw.Draw(im);ft=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',30);small=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',21)
d.text((30,20),'P9401 · Çatı seçenekleri',font=ft,fill='#173d31');d.text((30,67),'Aynı gövde · Nötr karşılaştırma renkleri · Tasarım seçimi bekliyor',font=small,fill='#71816f')
names={'A':'Kaynak: veranda kollu beşik','B':'Öneri: sade kırma','C':'Öneri: tek eğimli','D':'Öneri: parapetli düz görünüş'}
for i,(k,name) in enumerate(names.items()):
 x=(i%2)*900;y=115+(i//2)*677;d.text((x+26,y),k+' · '+name,font=ft,fill='#173d31');panel=Image.open(p/k/'dis_gorunus.png').convert('RGB');panel.thumbnail((875,610));im.paste(panel,(x+(900-panel.width)//2,y+46))
im.save(p/'P9401_Dort_Cati.jpg',quality=94)
