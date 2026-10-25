import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
RED, WALL, EDGE = '#c0392b', '#e6e1d6', '#9a958c'
fig, axs = plt.subplots(1, 2, figsize=(13.5, 7.2))
for ax, (baslik, w, e, L) in zip(axs, [("Dış köşe · B-01 10'luk\n(10 cm dış duvar, dış köşeler ve veranda iç köşesi)", 10, 4.8, 13),
                                      ("İç köşe · B-02 6'lık\n(6 cm iç duvar, oda içindeki köşeler)", 6, 3.0, 9)]):
    # plan: O = (0,0) dış köşe; biten duvar sola, içeri giren duvar aşağı
    ax.add_patch(Rectangle((-40, -w), 40 - w, w, fc=WALL, ec=EDGE, lw=1))          # biten duvar
    ax.add_patch(Rectangle((-w, -32), w, 32 - e, fc=WALL, ec=EDGE, lw=1))           # içeri giren duvar
    ax.text(-30, -w / 2, 'biten duvar', va='center', fontsize=10, color='#555')
    ax.text(-w / 2, -24, 'içeri\ngiren\nduvar', ha='center', va='center', fontsize=10, color='#555')
    ax.text(-w / 2, -e / 2, f'kutu\n{w} × {e:g}'.replace('.', ','), ha='center', va='center', fontsize=8.5)
    k = dict(color=RED, lw=3.2, solid_capstyle='butt')
    ax.plot([0, -L], [0, 0], **k); ax.plot([0, 0], [0, -L], **k)                    # iki dış kanat
    ax.plot([-w, -w], [0, -(L - 0.5)], **k)                                         # iç kanat
    ax.plot([0, -w], [-e, -e], **k)                                                 # kutu tabanı
    ax.plot([-w, -w - 3], [-w, -w], **k)                                            # iç tırnak 3 cm
    ax.text(-L / 2, 1.2, f'{L} cm  ({w} + 3)', ha='center', color=RED, fontsize=11)
    ax.text(1.0, -L / 2, f'{L} cm\n({w} + 3)', va='center', color=RED, fontsize=11)
    ax.text(-w - 0.4, -w + 0.5, 'tırnak 3 cm', ha='right', va='bottom', color=RED, fontsize=9.5)
    ax.text(-w - 0.5, -(L - 0.5) - 0.3, f'iç kanat {L - 0.5:g} cm'.replace('.', ','), ha='right', va='top', color=RED, fontsize=9.5)
    ax.set_title(baslik, fontsize=12)
    ax.set_xlim(-41, 9); ax.set_ylim(-33, 4); ax.set_aspect('equal'); ax.axis('off')
fig.text(0.5, 0.02, 'Biçim aynı; yalnız duvar kalınlığı değişir. Kanat = duvar kalınlığı + 3 cm. Sac 1 mm. Aynı ölçekte çizildi.', ha='center', fontsize=10.5, color='#333')
plt.tight_layout(rect=(0, 0.05, 1, 1)); plt.savefig('cizim/kose_okuma_v2.png', dpi=110)
