"""Aşık düzeltmesinin önce/sonra görüntüsü: evin ön bölümü yukarıdan; yeni ve değişen sıralar kırmızı.

Kullanım: python once_sonra.py <önceki GLB> <yeni GLB> once_sonra.png
(önceki GLB: git show 458dc421:deneme/2026-11-20_celik_iskelet/celik_iskelet_90m2_asik_omega.glb)
"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from asik_omega import glb_oku
fig = plt.figure(figsize=(18, 8.5))
for j, (yol, baslik) in enumerate(((sys.argv[1], 'Önce'), (sys.argv[2], 'Sonra: panelin sağ yüzüne 4 sıra, veranda sıraları dereye kadar'))):
    ax = fig.add_subplot(1, 2, j + 1, projection='3d')
    for p in glb_oku(yol):
        T = p['P'][p['I'].reshape(-1, 3)]
        T = T[(T[:, :, 0].max(1) < 5.3) & (T[:, :, 1].max(1) < 0.0) & (T[:, :, 2].min(1) > 1.5)]
        if not len(T): continue
        if p['kat'] == 'Asik':
            yeni = j == 1 and ('panel_sag' in p['ad'] or 'veranda' in p['ad'])
            ax.add_collection3d(Poly3DCollection(T, facecolor='#d62728' if yeni else '#f28c28', edgecolor='none', alpha=1.0))
        elif p['kat'] != 'Tavan_omegasi':
            ax.add_collection3d(Poly3DCollection(T, facecolor='#aab3bb', edgecolor='#7b858e', linewidths=0.1, alpha=0.55))
    ax.set_xlim(-5.2, 5.2); ax.set_ylim(-5.4, 0.0); ax.set_zlim(1.5, 4.6); ax.set_box_aspect((10.4, 5.4, 3.1))
    ax.view_init(elev=38, azim=-112); ax.set_axis_off(); ax.set_title(baslik, fontsize=11)
plt.tight_layout(); plt.savefig(sys.argv[3], dpi=85)
