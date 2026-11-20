"""Aşık ve tavan omegasının oturuşunu dört kesitte çizer: sol saçak, mahya, arka sol odanın tavanı, veranda çatısı.

Kesit bandındaki iskelet parçaları ve bütün aşık ile omega parçaları (eksenleri boyunca izdüşümle kesit biçimini verir).
Kullanım: python kesit.py celik_iskelet_90m2_asik_omega.glb kesit_asik_omega.png
"""
import sys, os, numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from asik_omega import glb_oku
P = glb_oku(sys.argv[1])
renk = {'Makas': '#7f8c8d', 'Asik': '#e67e22', 'Tavan_omegasi': '#1f6feb', 'Duvar': '#c9d0d6', 'Cati_paneli': '#a04040', 'Lento': '#555'}
pencere = [('sol saçak (y 3,7–3,9 makası)', 'xz', (3.70, 3.90), (-5.0, -3.6), (2.45, 3.35)),
           ('mahya', 'xz', (3.70, 3.90), (-0.7, 0.7), (4.0, 4.5)),
           ('tavan, arka sol oda', 'xz', (3.70, 3.90), (-4.7, -3.0), (2.50, 2.80)),
           ('veranda çatısı (x 0,8–0,9 makası)', 'yz', (0.80, 0.90), (-5.2, -2.6), (2.5, 3.5))]
fig, axs = plt.subplots(1, 4, figsize=(22, 5.5))
for ax, (ad, dz, bant, xl, zl) in zip(axs, pencere):
    a = 0 if dz == 'xz' else 1; b = 1 - a
    for p in P:
        T = p['P'][p['I'].reshape(-1, 3)]
        if p['kat'] in ('Asik', 'Tavan_omegasi'):
            sec = T
        else:
            sec = T[(T[:, :, b].max(1) >= bant[0]) & (T[:, :, b].min(1) <= bant[1])]
        if len(sec):
            ax.add_collection(PolyCollection(sec[:, :, [a, 2]], facecolor=renk.get(p['kat'], '#999'), edgecolor=renk.get(p['kat'], '#999'), linewidths=0.4, alpha=0.6))
    ax.set_xlim(*xl); ax.set_ylim(*zl); ax.set_aspect('equal'); ax.grid(alpha=0.3); ax.set_title(ad, fontsize=10)
plt.tight_layout(); plt.savefig(sys.argv[2], dpi=85)
