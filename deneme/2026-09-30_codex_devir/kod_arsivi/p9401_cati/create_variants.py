import json,math
from pathlib import Path
out=Path('outputs/P9401_Cati_Alternatifleri');work=Path('work/p9401_cati');source=json.loads(Path('work/skp_import/P9401/selected.json').read_text(encoding='utf-8'))
x0,x1,y0,y1,z=-.25,10.49,.3675,9.7525,3.1017
porch=(3.715,10.49,-1.515,y0);th=.10
mats={'roof':{'name':'Öneri antrasit çatı','color':[.22,.25,.27,1],'texture':None},'wall':{'name':'Öneri üst kapama yüzeyi','color':[.82,.82,.77,1],'texture':None},'edge':{'name':'Öneri parapet kapak','color':[.30,.33,.33,1],'texture':None}}
variants={}
I=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
def variant(key,title,desc,params,source_roof=False):
 v={'id':key,'title':title,'description':desc,'revision':f'P9401-CATI-{key}-01','source_roof':source_roof,'parameters':params,'nodes':[],'meshes':{},'materials':mats,'status':'Lokman seçimi ve teknik değerlendirme bekliyor','scope':'P9401 modele özgü çatı seçeneği; genel katalog kuralı değil'};variants[key]=v;return v
def solid(v,name,verts,faces,material):
 gid=f"{v['id']}_{len(v['nodes'])+1:02}";tris=[]
 for face in faces:
  for k in range(1,len(face)-1):tris.append([face[0],face[k],face[k+1]])
 v['meshes'][gid]={'vertices':verts,'triangles':tris,'uv':[[0,0]]*len(verts),'materials':[material]*len(tris)}
 v['nodes'].append({'id':1000+len(v['nodes']),'name':name,'source_id':None,'world_transform':I,'material':material,'geometry':gid,'root':gid,'roof':True,'stage':3,'proposal':True})
def slab(v,name,top,material='roof',thickness=th):
 n=len(top);bot=[[p[0],p[1],p[2]-thickness] for p in top];faces=[list(range(n)),list(reversed(range(n,2*n)))]+[[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)];solid(v,name,top+bot,faces,material)
def box(v,name,a,b,material):
 xa,ya,za=a;xb,yb,zb=b;slab(v,name,[[xa,ya,zb],[xb,ya,zb],[xb,yb,zb],[xa,yb,zb]],material,zb-za)
A=variant('A','Kaynak çatı','Veranda koluyla birleşen beşik çatı. Mevcut SKP geometrisi.',{'Saçak altı (kaynak)':'3,102 m','Ana mahya (kaynak)':'4,640 m','Veranda mahyası (kaynak)':'4,202 m'},True)
B=variant('B','Sade kırma','Dört yöne eğimli ana çatı ve alçak veranda örtüsü.',{'Ana üst kot':'4,640 m · kaynakla aynı tutulan öneri','Ana eğim':f"%{100*(4.640014-(z+th))/((y1-y0)/2):.1f} · öneri",'Veranda örtüsü':'3,202 m üst kot · yatay görsel taslak'})
half=(y1-y0)/2;ya=(y0+y1)/2;left=x0+half;right=x1-half;zz=4.640014;e=z+th
verts=[[x0,y0,e],[x1,y0,e],[x1,y1,e],[x0,y1,e],[left,ya,zz],[right,ya,zz]]
# One continuous roof shell with closed eave perimeter.
faces=[[0,1,5,4],[1,2,5],[2,3,4,5],[3,0,4]];bottom=[[p[0],p[1],p[2]-th] for p in verts];faces2=faces+[[i+6 for i in reversed(f)] for f in faces]+[[i,(i+1)%4,(i+1)%4+6,i+6] for i in range(4)];solid(B,'Kırma çatı önerisi',verts+bottom,faces2,'roof')
pa,pb,pc,pd=porch;slab(B,'Veranda örtüsü önerisi',[[pa,pc,e],[pb,pc,e],[pb,pd,e],[pa,pd,e]])
C=variant('C','Tek eğimli','Önden arkaya yükselen tek yüzey; veranda alçak örtüyle ayrılıyor.',{'Yükselme':'1,00 m · tasarım önerisi','Ana eğim':f"%{100/(y1-y0):.1f} · öneri",'Arka üst kot':f'{e+1:.3f} m · öneri'})
slab(C,'Tek eğimli çatı önerisi',[[x0,y0,e],[x1,y0,e],[x1,y1,e+1],[x0,y1,e+1]])
slab(C,'Veranda örtüsü önerisi',[[pa,pc,e],[pb,pc,e],[pb,pd,e],[pa,pd,e]])
# New above-wall enclosure; no source wall geometry is edited.
outline=[(0,.6175),(3.965,.6175),(3.965,2.5),(10.24,2.5),(10.24,9.5025),(0,9.5025)]
for i,(a,b) in enumerate(zip(outline,outline[1:]+outline[:1])):
 dx,dy=b[0]-a[0],b[1]-a[1];l=math.hypot(dx,dy);nx,ny=-dy/l*.05,dx/l*.05;pts=[a,b,(b[0]+nx,b[1]+ny),(a[0]+nx,a[1]+ny)];top=[[px,py,z+(py-y0)/(y1-y0)] for px,py in pts];bot=[[px,py,z] for px,py in pts];solid(C,f'Üst kapama önerisi {i+1}',top+bot,[[0,1,2,3],[7,6,5,4],[0,4,5,1],[1,5,6,2],[2,6,7,3],[3,7,4,0]],'wall')
D=variant('D','Parapetli düz görünüş','Çatı kenarı parapetin arkasında kalır; yatay bir siluet oluşturur.',{'Parapet yüksekliği':'0,45 m · tasarım önerisi','Parapet kalınlığı':'0,15 m · görsel taslak','Drenaj / çatı eğimi':'Bu aşamada çözülmedi'})
slab(D,'Ana çatı yüzeyi taslağı',[[x0,y0,e],[x1,y0,e],[x1,y1,e],[x0,y1,e]])
slab(D,'Veranda çatı yüzeyi taslağı',[[pa,pc,e],[pb,pc,e],[pb,pd,e],[pa,pd,e]])
outer=[(x0,y0),(pa,y0),(pa,pc),(x1,pc),(x1,y1),(x0,y1)]
# Continuous inset ring avoids overlapping parapet corners.
def ring(v,name,outer,width,bottom,top,material):
 lines=[]
 for a,b in zip(outer,outer[1:]+outer[:1]):
  dx,dy=b[0]-a[0],b[1]-a[1];l=math.hypot(dx,dy);lines.append(((a[0]-dy/l*width,a[1]+dx/l*width),(dx,dy)))
 inner=[]
 for i in range(len(outer)):
  (p,u),(q,w)=lines[i-1],lines[i];cross=u[0]*w[1]-u[1]*w[0];dt=((q[0]-p[0])*w[1]-(q[1]-p[1])*w[0])/cross;inner.append((p[0]+dt*u[0],p[1]+dt*u[1]))
 n=len(outer);verts=[[x,y,bottom] for x,y in outer]+[[x,y,bottom] for x,y in inner]+[[x,y,top] for x,y in outer]+[[x,y,top] for x,y in inner];faces=[]
 for i in range(n):
  j=(i+1)%n;faces.extend([[i+2*n,j+2*n,j+3*n,i+3*n],[j,i,i+n,j+n],[i,j,j+2*n,i+2*n],[j+n,i+n,i+3*n,j+3*n]])
 solid(v,name,verts,faces,material)
ring(D,'Kesintisiz parapet önerisi',outer,.15,e,e+.45,'wall')
ring(D,'Parapet üst kapak önerisi',outer,.15,e+.45,e+.485,'edge')
for v in variants.values():
 (out/v['id']).mkdir(exist_ok=True)
 full={**source,'revision':v['revision'],'materials':{**source['materials'],**mats},'nodes':list(source['nodes'] if v['source_roof'] else [n for n in source['nodes'] if not n['roof']])+v['nodes'],'meshes':{**source['meshes'],**v['meshes']},'notes':[v['description'],v['status']]}
 (work/(v['id']+'_selected.json')).write_text(json.dumps(full,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
(out/'secenekler.js').write_text('window.P9401_ROOFS='+json.dumps(variants,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')
manifest={'model':'P9401','source_revision':'SKP-inceleme-01','source_sha256':source['source_sha256'],'request':'Lokman: videolardaki gibi birkaç çatı modeli','classification':'Modele özgü tasarım seçenekleri','reference_video':'WhatsApp Video 2026-09-29 at 14.07.27.mp4 · seçenek galerisi sunum yaklaşımı; ölçü kaynağı değil','source_roof_footprint_m':{'main':[x0,x1,y0,y1],'porch':list(porch),'wall_top':z},'assumptions':{'roof_skin_thickness_m':.10,'single_slope_infill_thickness_m':.05,'parapet_cap_thickness_m':.035,'note':'Yeni seçeneklerde 0,10 m kabuk görsel kalınlıktır; gerçek çatı katman sistemi değildir. Kaynak çatı geometrisi A içinde korunur. B-C yatay veranda örtüsü ve D yüzeyi drenaj tasarımı içermez. C üst kapama yüzeyleri yeni tasarım parçalarıdır.'},'variants':[{k:val for k,val in v.items() if k not in ['nodes','meshes','materials']} for v in variants.values()]}
manifest['acceptance']={'Lokman_secimi':'bekliyor','teknik_kabul':'bekliyor','Claude_entegrasyonu':'yapılmadı'}
manifest['display_palette']='Nötr karşılaştırma renkleri; ürün rengi onayı değil'
(out/'Tasarim_Kaydi.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print([(k,len(v['nodes'])) for k,v in variants.items()])
