import json, math, sys
import os
REPO=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../..'))
K=json.load(open(REPO+'/testler/kimlik/veri/PK01_pafta_katmani.json'))
P=K['ayrinti']['montaj']['panolar']
Hs=K['ayrinti']['h_plani']['konumlar']
lines={}
for i,p in enumerate(P):
    x0,y0,x1,y1=p['rect']
    if (x1-x0)>(y1-y0): o='h'; perp=(y0+y1)/2; t=y1-y0; a0,a1=x0,x1
    else: o='v'; perp=(x0+x1)/2; t=x1-x0; a0,a1=y0,y1
    key=(o,round(perp,1),round(t,1))
    lines.setdefault(key,[]).append((a0,a1,i))
joints=[]
for key,ps in lines.items():
    ps.sort()
    for (a0,a1,i),(b0,b1,j) in zip(ps,ps[1:]):
        if abs(a1-b0)<1.0:
            o,perp,t=key
            xy=(perp,a1) if o=='v' else (a1,perp)
            joints.append(dict(o=o,perp=perp,t=t,a=a1,xy=xy,pi=i,pj=j))
print('lines',len(lines),'joints',len(joints))
used=set()
for jt in joints:
    best=None
    for k,h in enumerate(Hs):
        d=math.dist(jt['xy'],h['xy'])
        if best is None or d<best[0]: best=(d,k)
    jt['h']=Hs[best[1]]['tur'] if best[0]<14 else None
    jt['hd']=round(best[0],1)
    if best[0]<14:
        if best[1] in used: print('DUP',jt,best)
        used.add(best[1])
for jt in joints: print(jt['o'],jt['perp'],jt['t'],round(jt['a'],1),jt['h'],jt['hd'])
print('unmatched circles:',[ (Hs[k]['tur'],Hs[k]['xy']) for k in range(len(Hs)) if k not in used])
from collections import Counter
print(Counter(j['h'] for j in joints))
