"""Frame Builder CSV'sindeki paneli çizer: çubuklar düzlem içi genişlikleriyle, işlemler eksen üstünde işaretli.

Kullanım: python ciz_duvar.py kaynak/DVR1_duvar.csv gor/DVR1_islemler.png
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import csv_oku

ISARET = {'DIMPLE': ('o', '#1d3a5a', 'vida deliği (DIMPLE)'), 'LIP_CUT': ('x', '#c0392b', 'dudak kesme (LIP_CUT)'),
          'SWAGE': ('s', '#e08e0b', 'ezme (SWAGE)'), 'NOTCH': ('v', '#7d3c98', 'kertme (NOTCH)'),
          'SERVICE_HOLE': ('o', '#27ae60', 'servis deliği (SERVICE_HOLE)')}

ust, P = csv_oku.oku(sys.argv[1])
fig, ax = plt.subplots(figsize=(9, 9))
gorulen = set()
for p in P:
    L = math.hypot(p['x2'] - p['x1'], p['y2'] - p['y1']); ux, uy = (p['x2'] - p['x1']) / L, (p['y2'] - p['y1']) / L
    nx, ny = -uy * p['flans'] / 2, ux * p['flans'] / 2
    kose = [(p['x1'] + nx, p['y1'] + ny), (p['x2'] + nx, p['y2'] + ny), (p['x2'] - nx, p['y2'] - ny), (p['x1'] - nx, p['y1'] - ny)]
    ax.fill(*zip(*kose), facecolor='#f6d8e3' if p['etiket'] == 'LABEL_INV' else '#cfe8f3', edgecolor='#555', lw=0.6)
    ax.text((p['x1'] + p['x2']) / 2 + nx * 1.6, (p['y1'] + p['y2']) / 2 + ny * 1.6, p['ad'].split('-')[-1], fontsize=6, ha='center', va='center')
    for k, (m, renk, ad) in ISARET.items():
        for t in p['islem'].get(k, []):
            ax.plot(p['x1'] + ux * t, p['y1'] + uy * t, m, color=renk, ms={'SERVICE_HOLE': 7, 'LIP_CUT': 6}.get(k, 4),
                    mfc='none' if k in ('SWAGE', 'SERVICE_HOLE') else renk, mew=1.2, label=ad if k not in gorulen else None)
            gorulen.add(k)
ax.set_aspect('equal'); ax.set_xlabel('x (mm)'); ax.set_ylabel('y (mm)')
ax.set_title(f"{ust['FRAMESET'][0]} · {len(P)} çubuk · profil {P[0]['govde']:.0f}×{P[0]['flans']:.0f}×{P[0]['kalinlik']} · mavi LABEL_NRM, pembe LABEL_INV", fontsize=9)
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.07), ncol=3, fontsize=7, frameon=False)
plt.tight_layout(); os.makedirs(os.path.dirname(sys.argv[2]) or '.', exist_ok=True); plt.savefig(sys.argv[2], dpi=130)
print('yazıldı:', sys.argv[2])
