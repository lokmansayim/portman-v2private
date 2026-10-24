import json, math
import os
REPO=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../..'))
K=json.load(open(REPO+'/testler/kimlik/veri/PK01_pafta_katmani.json'))
A=K['ayrinti']
P=A['montaj']['panolar']
Hs=A['h_plani']['konumlar']
CARDS={c['kod']:c for c in json.load(open(REPO+'/kurallar/urun/kartlar.json'))['kartlar']}

def key(r): return (round(r[0],1), round(r[1],1))
pan={key(p['rect']):dict(i=i,**p) for i,p in enumerate(P)}

# Açıklıklar (pafta: pencere uç işaretleri + kapı kanat/yayları; ölçü ve eşik kart P-01..P-03'ten)
OPEN={
 (198.2,990.2):dict(kind='win',size='60/40',w=60,s=160,top=200,card='D-04'),
 (590.2,744.2):dict(kind='win',size='120/120',w=120,s=80,top=200,card='D-02'),
 (590.2,367.7):dict(kind='win',size='120/120',w=120,s=80,top=200,card='D-02'),
 (0.0,744.2):dict(kind='win',size='120/120',w=120,s=80,top=200,card='D-02'),
 (427.0,200.0):dict(kind='win',size='120/180',w=120,s=20,top=200,card='D-03'),
 (70.3,0.0):dict(kind='win',size='120/180',w=120,s=20,top=200,card='D-03'),
 (261.0,200.0):dict(kind='door_ext',a0=283.5,a1=365.5,s=0,top=200,card='D-05'),
 (257.9,493.1):dict(kind='door',a0=521.25,a1=603.25,s=0,top=200,card='I-02'),
 (257.9,618.5):dict(kind='door',a0=634.2,a1=716.2,s=0,top=200,card='I-02'),
 (383.6,493.1):dict(kind='door',a0=521.25,a1=603.25,s=0,top=200,card='I-02'),
 (383.6,618.5):dict(kind='door',a0=634.2,a1=716.2,s=0,top=200,card='I-02'),
 (261.0,741.1):dict(kind='door',a0=284.1,a1=366.1,s=0,top=200,card='I-02'),
}
# Oda oda dizilim (arka-sol köşeden başlar; sıra Lokman'ın teyidine açık)
ROOMS=[
 ('yatak1','Yatak odası 1',7.5,[[10,621,258,741],[10,747,195,990]],
  ['post:BL','P:9.8,990.2','P:135.5,990.2','P:195.2,869.5','P:195.2,744.2','post:B02','P:201.3,741.1','P:257.9,618.5','P:135.5,615.5','P:9.8,615.5','P:0.0,618.5','P:0.0,744.2','P:0.0,869.5']),
 ('banyo','Banyo',4.4,[[201,747,384,990]],
  ['P:198.2,990.2','P:323.7,990.2','P:383.6,869.5','P:383.6,744.2','P:261.0,741.1']),
 ('yatak2','Yatak odası 2',7.3,[[389,621,590,990]],
  ['P:386.4,990.2','P:512.1,990.2','post:BR','P:590.2,869.5','P:590.2,744.2','P:590.2,618.5','P:512.1,615.5','P:389.4,615.5','P:383.6,618.5']),
 ('salon','Salon',8.1,[[389,210,590,615]],
  ['P:590.2,493.1','P:590.2,367.7','P:590.2,242.0','P:590.2,205.0','post:SFR','P:552.6,200.0','P:427.0,200.0','P:386.4,200.0','P:383.6,210.0','P:383.6,242.0','P:383.6,367.7','P:383.6,493.1']),
 ('hol','Hol',6.3,[[264,210,384,741]],
  ['post:HFL','P:261.0,200.0','P:257.9,210.0','P:257.9,242.0','P:257.9,367.7','P:257.9,493.1']),
 ('mutfak','Mutfak',14.9,[[10,10,256,615]],
  ['P:255.9,116.6','P:255.9,5.0','post:KFR','P:195.7,0.0','P:70.3,0.0','P:9.8,0.0','post:FL','P:0.0,5.0','P:0.0,116.6','P:0.0,242.0','P:0.0,367.7','P:0.0,493.1']),
]
POSTS={
 'BL':dict(rect=[0,990.18,9.82,1000],card='B-01'),
 'BR':dict(rect=[590.18,990.18,600,1000],card='B-01'),
 'FL':dict(rect=[0,0,9.82,10.07],card='B-01'),
 'KFR':dict(rect=[255.92,0,265.99,10.07],card='B-01'),
 'HFL':dict(rect=[255.92,199.95,265.99,210.02],card='B-01'),
 'SFR':dict(rect=[590.18,199.95,600,210.02],card='B-01'),
 'B02':dict(rect=[195.21,741.12,201.26,747.17],card='B-02'),
}
def pk(s):
    x,y=s.split(':')[1].split(','); x=float(x); y=float(y)
    for k in pan:
        if abs(k[0]-x)<0.15 and abs(k[1]-y)<0.15: return k
    raise KeyError(s)

panels=[]; posts=[]; seen=set(); rooms=[]
for ri,(rid,ad,m2,rects,seq) in enumerate(ROOMS):
    step=2+ri; rooms.append(dict(id=rid,ad=ad,m2=m2,rects=rects,step=step))
    for o,s in enumerate(seq):
        if s.startswith('post:'):
            n=s.split(':')[1]; d=dict(POSTS[n]); d.update(step=step,order=o,room=rid,id=n); posts.append(d); continue
        k=pk(s); assert k not in seen, s; seen.add(k)
        p=pan[k]; x0,y0,x1,y1=p['rect']
        ori='h' if (x1-x0)>(y1-y0) else 'v'
        t=round((y1-y0) if ori=='h' else (x1-x0),2)
        op=next((v for kk,v in OPEN.items() if abs(kk[0]-p['rect'][0])<0.2 and abs(kk[1]-p['rect'][1])<0.2),None)
        if op and op['kind']=='win':
            a0,a1=(x0,x1) if ori=='h' else (y0,y1); c=(a0+a1)/2
            op=dict(op,a0=c-op['w']/2,a1=c+op['w']/2)
        card = op['card'] if op else ('D-01' if p['duvar']=='dis' else 'I-01')
        panels.append(dict(id=p['i'],rect=[round(v,2) for v in p['rect']],o=ori,t=t,duvar=p['duvar'],tur=p['tur'],boy=p['boy'],card=card,op=op,room=rid,step=step,order=o))
assert len(panels)==50, len(panels)
byid={p['id']:p for p in panels}

# H'lar: pano eklerinden; tür H planındaki en yakın daireden (38/38 eşleşti)
lines={}
for p in panels:
    x0,y0,x1,y1=p['rect']
    perp=(y0+y1)/2 if p['o']=='h' else (x0+x1)/2
    a0,a1=(x0,x1) if p['o']=='h' else (y0,y1)
    lines.setdefault((p['o'],round(perp,1),p['t']),[]).append((a0,a1,p['id']))
HC={'dubelli_kulakli':'H-01','dubelli':'H-02','standart':'H-03','uclu_dubelli_kulakli':'H-04','uclu_dubelli':'H-05','uclu_standart':'H-06'}
hs=[]
for (o,perp,t),ps in lines.items():
    ps.sort()
    for (a0,a1,i),(b0,b1,j) in zip(ps,ps[1:]):
        if abs(a1-b0)>1: continue
        xy=(perp,a1) if o=='v' else (a1,perp)
        d,hk=min((math.dist(xy,h['xy']),k) for k,h in enumerate(Hs))
        assert d<14
        tur=Hs[hk]['tur']
        pi,pj=byid[i],byid[j]
        later=max(pi,pj,key=lambda p:(p['step'],p['order']))
        stub=None
        if tur.startswith('uclu'):
            # T'nin iç duvar kolu: eke dokunan dik pano
            for q in panels:
                if q['o']==o: continue
                qx0,qy0,qx1,qy1=q['rect']
                if qx0-6<=xy[0]<=qx1+6 and qy0-6<=xy[1]<=qy1+6:
                    cx,cy=(qx0+qx1)/2,(qy0+qy1)/2
                    v=(cx-xy[0],cy-xy[1]); n=math.hypot(*v); stub=[round(v[0]/n),round(v[1]/n)]; st=q['t']; qq=q; break
            assert stub, xy
        if stub:  # 3'lü H, üç panodan ikincisi yerleşince konur
            later=sorted([pi,pj,qq],key=lambda p:(p['step'],p['order']))[1]
        hs.append(dict(xy=[round(xy[0],2),round(xy[1],2)],o=o,t=t,tur=tur,card=HC[tur],stub=stub,stub_t=(st if stub else None),step=later['step'],order=later['order']+0.5,room=later['room']))
assert len(hs)==38

# Alt çerçeve: duvar hatları, kapı boşluklarında kesik
alt=[]
for (o,perp,t),ps in lines.items():
    ps.sort(); segs=[]
    for a0,a1,i in ps:
        if segs and a0-segs[-1][1]<12: segs[-1][1]=max(segs[-1][1],a1)
        else: segs.append([a0,a1])
    cuts=[(byid[i]['op']['a0'],byid[i]['op']['a1']) for a0,a1,i in ps if byid[i]['op'] and byid[i]['op']['kind'].startswith('door')]
    for s0,s1 in segs:
        pts=[s0]; 
        for c0,c1 in sorted(cuts):
            if s0<c0<s1: pts+= [c0,c1]
        pts.append(s1)
        for a,b in zip(pts[0::2],pts[1::2]):
            alt.append(dict(o=o,perp=perp,t=t,a0=round(a,2),a1=round(b,2),duvar='dis' if t>8 else 'ic'))
alt_dis=sum(s['a1']-s['a0'] for s in alt if s['duvar']=='dis'); alt_ic=sum(s['a1']-s['a0'] for s in alt if s['duvar']=='ic')

# Kapılar (K-01): menteşe, kapalı ve açık yön planın kanat/yaylarından
doors=[
 dict(room='mutfak',hinge=[260.95,603.25],closed=[0,-1],open=[-1,0]),
 dict(room='yatak1',hinge=[260.95,634.2],closed=[0,1],open=[-1,0]),
 dict(room='salon',hinge=[386.5,603.25],closed=[0,-1],open=[1,0]),
 dict(room='yatak2',hinge=[386.5,634.2],closed=[0,1],open=[1,0]),
 dict(room='banyo',hinge=[366.1,744.15],closed=[-1,0],open=[0,1]),
]
data=dict(
 kaynak='PK-01 60 m² montaj paftası (10 sayfa), Portman pafta okuyucusu sürüm 2 (kodla okundu)',
 dis=[600,1000], h=250,
 rooms=rooms, panels=panels, posts=posts, hs=hs, alt=alt,
 alt_m=dict(dis=round(alt_dis/100,1),ic=round(alt_ic/100,1)),
 veranda=dict(kolon=[590.18,0,600,10.07],kiris=[[266,0,590.18,10.07],[590.18,10.07,600,199.95]]),
 makas=A['makas']['makaslar'], omega=A['omega']['parcalar'], asik=A['asik'],
 kaplama=A['kaplama'], betopan=A['betopan'], dere=A['dere'], doors=doors,
 cards={k:dict(ad=v['ad'],olcu=v.get('olcu'),ifc=v.get('ifc'),birim=v.get('birim')) for k,v in CARDS.items()},
)
json.dump(data,open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'data.json'),'w'),ensure_ascii=False,separators=(',',':'))
from collections import Counter
print('panels by room', Counter(p['room'] for p in panels))
print('cards', Counter(p['card'] for p in panels), Counter(h['card'] for h in hs))
print('alt m', data['alt_m'], 'segs', len(alt))
print('uclu stubs', [(h['xy'],h['stub']) for h in hs if h['stub']])
print(len(json.dumps(data)))
