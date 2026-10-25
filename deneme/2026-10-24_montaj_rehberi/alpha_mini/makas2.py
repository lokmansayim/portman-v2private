import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, collections, skp_oku
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
ad=sys.argv[1]; r=skp_oku.oku('kaynak/%s.skp'%ad)
T=[f for f in r['yuzler'] if f['katman']=='LCAD_Truss']
C=np.array([np.vstack(f['halkalar']).mean(0) for f in T])
E=[np.ptp(np.vstack(f['halkalar']),axis=0) for f in T]
def clusters(vals,gap=12):
    o=np.sort(vals); g=[[o[0]]]
    for v in o[1:]:
        (g[-1].append(v) if v-g[-1][-1]<gap else g.append([v]))
    return g
for ax_i,name in ((0,'x'),(1,'y')):
    g=clusters(C[:,ax_i]); big=[x for x in g if len(x)>20]
    print(name,'kümeler',len(g),'büyük',len(big),[ (round(np.mean(x),1),len(x)) for x in big][:20])
g=[x for x in clusters(C[:,1]) if len(x)>20]; cents=[np.mean(x) for x in g]
fig,axs=plt.subplots(len(cents),1,figsize=(13,1.9*len(cents)))
for a,c in zip(axs,cents):
    for f,cc in zip(T,C):
        if abs(cc[1]-c)<12:
            H=f['halkalar'][0]; a.fill(H[:,0],H[:,2],facecolor='#4a78a8',edgecolor='#1d3a5a',lw=0.3,alpha=0.55)
    a.set_aspect('equal'); a.set_xlim(630,1545); a.set_title('y≈%.1f'%c,fontsize=8); a.tick_params(labelsize=6)
plt.tight_layout(); plt.savefig('gor/%s_makaslar.png'%ad,dpi=100)
W=[f for f in r['yuzler'] if f['katman']=='LCAD_Wall']; P=np.vstack([np.vstack(f['halkalar']) for f in W])
print('duvar kutusu', np.round(P.min(0),1), np.round(P.max(0),1))
