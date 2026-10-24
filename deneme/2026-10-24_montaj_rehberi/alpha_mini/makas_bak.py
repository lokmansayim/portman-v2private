import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sys, pickle, collections, numpy as np, skp_oku
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
ad=sys.argv[1]; r=skp_oku.oku('kaynak/%s.skp'%ad)
T=[f for f in r['yuzler'] if f['katman']=='LCAD_Truss']
R=[f for f in r['yuzler'] if f['katman']=='LCAD_Roof']
print(ad,'truss faces',len(T),'roof',len(R),'materials',collections.Counter(f['malzeme'] for f in T).most_common(4))
# makasları y'ye göre kümele
ys=np.array([np.vstack(f['halkalar']).mean(0)[1] for f in T])
order=np.sort(ys); groups=[]; 
for y in order:
    if groups and y-groups[-1][-1]<15: groups[-1].append(y)
    else: groups.append([y])
cents=[np.mean(g) for g in groups]; print('makas y merkezleri', [round(c,1) for c in cents], 'aralık', np.round(np.diff(cents),1))
fig,axs=plt.subplots(len(cents),1,figsize=(14,2.2*len(cents)))
axs=np.atleast_1d(axs)
for ax,c in zip(axs,cents):
    for f in T:
        H=f['halkalar'][0]
        if abs(H.mean(0)[1]-c)<15: ax.fill(H[:,0],H[:,2],facecolor='#4a78a8',edgecolor='#1d3a5a',lw=0.3,alpha=0.6)
    ax.set_aspect('equal'); ax.set_title('y≈%.1f'%c,fontsize=8); ax.tick_params(labelsize=6)
plt.tight_layout(); plt.savefig('gor/%s_makaslar.png'%ad,dpi=110)
# ilk makasın yüz kutuları
c=cents[0]; F=[f for f in T if abs(np.vstack(f['halkalar']).mean(0)[1]-c)<15]
P=np.vstack([np.vstack(f['halkalar']) for f in F]); print('makas0 kutu', np.round(P.min(0),1), np.round(P.max(0),1), 'y kalınlık', round(P[:,1].max()-P[:,1].min(),1))
pickle.dump(dict(F=F,R=R,cents=cents),open('ara/%s_makas.pkl'%ad,'wb'))
