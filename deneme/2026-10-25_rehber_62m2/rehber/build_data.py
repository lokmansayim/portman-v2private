"""62 m² prefabrik (beşik + cumba) montaj rehberi verisi.
Kaynak: proje DWG (MIMARI PLANSS bloğu: pano, pencere, kapı; H profil paftası: H yerleri ve türleri renkten;
tavan omega, makas ve dere, aşık, çatı kaplama paftaları), proje SKP (MKS01–12 yerleri ve kesitleri),
yükleme listesi (adetler). Koordinat: cm, x sol dış yüzden sağa (0–900), y ön dış yüzden arkaya (0–600); veranda y < 0.
Kullanım: python build_data.py  → data.json"""
import json, math, os, sys
from collections import Counter

REPO = os.environ.get('PORTMAN_REPO', '/home/claude/portman-v2private')
D = os.path.dirname(os.path.abspath(__file__))
CARDS = {c['kod']: c for c in json.load(open(os.path.join(REPO, 'kurallar/urun/kartlar.json')))['kartlar']}

# ---------- Panolar (plan bloğundan; boylar dış duvar görünüşleriyle aynı) ----------
# (anahtar, rect, duvar, kart, ad (kart yoksa), açıklık)
W = lambda size, a0, a1, s, top=200: dict(kind='win', size=size, a0=a0, a1=a1, s=s, top=top)
P = [
    # ön duvar (y 0–10)
    ('F1', [5, 0, 67.75, 10], 'D-01', None, None),
    ('F2', [67.75, 0, 318.75, 10], None, 'Betopan kaplı çelik karkas duvar · DVR01', W('180/180', 103.25, 283.25, 20)),
    ('F3', [318.75, 0, 381.5, 10], 'D-01', None, None),
    ('F4', [381.5, 0, 507, 10], 'D-05', None, dict(kind='door_ext', a0=396.75, a1=491.75, s=0, top=210)),
    ('F5', [507, 0, 569.75, 10], 'D-01', None, None),
    ('F6', [569.75, 0, 820.75, 10], None, 'Betopan kaplı çelik karkas duvar · DVR02', W('180/180', 605.25, 785.25, 20)),
    ('F7', [820.75, 0, 895, 10], 'D-01', None, None),
    # arka duvar (y 590–600)
    ('B1', [5, 590, 130.5, 600], 'D-01', None, None),
    ('B2', [130.5, 590, 256, 600], 'D-01', None, None),
    ('B3', [256, 590, 381.5, 600], None, "100'lük yapıştırma dolu vasistaslı pano (60/60)", W('60/60', 295.96, 355.96, 140)),
    ('B4', [381.5, 590, 507, 600], 'D-01', None, None),
    ('B5', [507, 590, 632.5, 600], 'D-01', None, None),
    ('B6', [632.5, 590, 758, 600], 'D-01', None, None),
    ('B7', [758, 590, 820.75, 600], 'D-01', None, None),
    ('B8', [820.75, 590, 895, 600], 'D-01', None, None),
    # sol duvar (x 0–10)
    ('L1', [0, 10, 10, 88], 'D-01', None, None),
    ('L2', [0, 88, 10, 213.5], None, "100'lük pencereli pano (120/80 sürgülü)", W('120/80', 90.75, 210.75, 120)),
    ('L3', [0, 213.5, 10, 339], 'D-01', None, None),
    ('L4', [0, 339, 10, 464.5], 'D-02', None, W('120/120', 341.75, 461.75, 80)),
    ('L5', [0, 464.5, 10, 590], 'D-01', None, None),
    # sağ duvar (x 890–900)
    ('R1', [890, 10, 900, 88], 'D-01', None, None),
    ('R2', [890, 88, 900, 213.5], 'D-01', None, None),
    ('R3', [890, 213.5, 900, 339], 'D-01', None, None),
    ('R4', [890, 339, 900, 464.5], 'D-02', None, W('120/120', 341.75, 461.75, 80)),
    ('R5', [890, 464.5, 900, 590], 'D-01', None, None),
    # iç duvarlar (6 cm)
    ('I1a', [10, 273.25, 130.5, 279.25], 'I-01', None, None),
    ('I1b', [130.5, 273.25, 256, 279.25], 'I-01', None, None),
    ('I2a', [253, 279.25, 259, 401.75], 'I-02', None, dict(kind='door', a0=296.27, a1=378.27, s=0, top=200)),
    ('I2b', [253, 401.75, 259, 464.5], 'I-01', None, None),
    ('I2c', [253, 464.5, 259, 590], 'I-01', None, None),
    ('I3a', [259, 398.75, 381.5, 404.75], 'I-02', None, dict(kind='door', a0=280.32, a1=362.32, s=0, top=200)),
    ('I3b', [381.5, 398.75, 504, 404.75], 'I-01', None, None),
    ('I4a', [504, 279.25, 510, 401.75], 'I-02', None, dict(kind='door', a0=294.95, a1=376.95, s=0, top=200)),
    ('I4b', [504, 401.75, 510, 464.5], 'I-01', None, None),
    ('I4c', [504, 464.5, 510, 590], 'I-01', None, None),
    ('I5a', [507, 273.25, 632.5, 279.25], 'I-01', None, None),
    ('I5b', [632.5, 273.25, 758, 279.25], 'I-01', None, None),
    ('I5c', [758, 273.25, 820.75, 279.25], 'I-01', None, None),
    ('I5d', [820.75, 273.25, 890, 279.25], 'I-01', None, None),
]
# Köşe direkleri: O dış köşe, db biten duvar boyunca, dt içeri giren duvar boyunca, e içeri giren duvarın kutuda bittiği yer
POSTS = {
    'BL': dict(rect=[0, 590, 10, 600], O=[0, 600], db=[0, -1], dt=[1, 0], e=5, card='B-01'),
    'BR': dict(rect=[890, 590, 900, 600], O=[900, 600], db=[0, -1], dt=[-1, 0], e=5, card='B-01'),
    'FR': dict(rect=[890, 0, 900, 10], O=[900, 0], db=[0, 1], dt=[-1, 0], e=5, card='B-01'),
    'FL': dict(rect=[0, 0, 10, 10], O=[0, 0], db=[0, 1], dt=[1, 0], e=5, card=None, ad='Özel köşe direği · A (veranda köşesi)'),
    'IC1': dict(rect=[253, 273.25, 259, 279.25], O=[259, 273.25], db=[0, 1], dt=[-1, 0], e=3, ic=True, card='B-02'),
    'IC2': dict(rect=[504, 273.25, 510, 279.25], O=[504, 273.25], db=[0, 1], dt=[1, 0], e=3, ic=True, card='B-02'),
}
# Çektirme U'su: iç duvar dış duvarın pano ortasına girer (I1 sol duvara, I5 sağ duvara)
CEKU = {
    'UL': dict(xy=[10, 276.25], yon=[1, 0], t=6),
    'UR': dict(xy=[890, 276.25], yon=[-1, 0], t=6),
}
# Oda oda dizilim (Lokman'ın seçtiği sıra: Yatak 1 → banyo → hol → yatak 2 → salon-mutfak)
ROOMS = [
    ('yatak1', 'Yatak odası 1', 7.55, [[10, 279.25, 253, 590]],
     ['post:BL', 'L5', 'L4', 'L3', 'B1', 'B2', 'I2c', 'I2b', 'I2a', 'post:IC1', 'I1b', 'U:UL', 'I1a']),
    ('banyo', 'Banyo', 4.53, [[259, 404.75, 504, 590]],
     ['B3', 'B4', 'I4c', 'I4b', 'I3b', 'I3a']),
    ('hol', 'Hol', 3.07, [[259, 273.25, 504, 398.75]],
     ['I4a', 'post:IC2']),
    ('yatak2', 'Yatak odası 2', 11.8, [[510, 279.25, 890, 590]],
     ['B5', 'B6', 'B7', 'B8', 'post:BR', 'R5', 'R4', 'R3', 'I5d', 'I5c', 'I5b', 'U:UR', 'I5a']),
    ('salon', 'Yaşam alanı · salon ve mutfak', 22.14, [[10, 10, 890, 273.25]],
     ['L2', 'L1', 'post:FL', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'post:FR', 'R1', 'R2']),
]
# H'lar: H profil paftasındaki 30 çember (tür çember renginden), pano eklerine oturtuldu
HC = {'dubelli_kulakli': 'H-01', 'dubelli': 'H-02', 'standart': 'H-03', 'uclu_dubelli_kulakli': 'H-04', 'uclu_dubelli': 'H-05', 'uclu_standart': 'H-06', 'ozel_c': None}
Hham = json.load(open(os.path.join(D, 'h_ham.json')))  # okuma/hlar.py çıktısı

panels, posts, ceku, rooms, seen = [], [], [], [], set()
pmap = {k: dict(key=k, rect=r, card=c, ad=a, op=o) for k, r, c, a, o in P}
for ri, (rid, ad, m2, rects, seq) in enumerate(ROOMS):
    step = 2 + ri
    rooms.append(dict(id=rid, ad=ad, m2=m2, rects=rects, step=step))
    for o, s in enumerate(seq):
        if s.startswith('post:'):
            n = s.split(':')[1]; d = dict(POSTS[n]); d.update(step=step, order=o, room=rid, id=n); posts.append(d); continue
        if s.startswith('U:'):
            n = s.split(':')[1]; d = dict(CEKU[n]); d.update(step=step, order=o, room=rid, id=n); ceku.append(d); continue
        assert s not in seen, s; seen.add(s)
        p = pmap[s]; x0, y0, x1, y1 = p['rect']
        ori = 'h' if (x1 - x0) > (y1 - y0) else 'v'
        t = round((y1 - y0) if ori == 'h' else (x1 - x0), 2)
        boy = round((x1 - x0) if ori == 'h' else (y1 - y0), 2)
        panels.append(dict(id=s, rect=p['rect'], o=ori, t=t, duvar='dis' if t > 8 else 'ic', tur='STD' if abs(boy - 125.5) < 0.1 else 'OZEL',
                           boy=boy, card=p['card'], ad=p['ad'], op=p['op'], room=rid, step=step, order=o))
assert len(panels) == len(P), (len(panels), len(P))
byid = {p['id']: p for p in panels}

# Duvar hatları ve pano ekleri
lines = {}
for p in panels:
    x0, y0, x1, y1 = p['rect']
    perp = (y0 + y1) / 2 if p['o'] == 'h' else (x0 + x1) / 2
    a0, a1 = (x0, x1) if p['o'] == 'h' else (y0, y1)
    lines.setdefault((p['o'], round(perp, 2), p['t']), []).append((a0, a1, p['id']))
joints = []
for (o, perp, t), ps in lines.items():
    ps.sort()
    for (a0, a1, i), (b0, b1, j) in zip(ps, ps[1:]):
        if abs(a1 - b0) > 1: continue
        joints.append(dict(o=o, perp=perp, t=t, a=a1, i=i, j=j, xy=(perp, a1) if o == 'v' else (a1, perp)))
hs = []
used = set()
for h in Hham:
    d, k = min((math.dist((h['x'], h['y']), J['xy']), k) for k, J in enumerate(joints))
    assert d < 12, (h, d)
    assert k not in used, h; used.add(k)
    J = joints[k]; tur = h['tur']
    if J['o'] == 'h' and abs(J['perp'] - 5) < 0.1 and abs(J['a'] - 318.75) < 0.1 or abs(J['a'] - 569.75) < 0.1 and abs(J['perp'] - 5) < 0.1:
        tur = 'ozel_c'   # paftada C işaretli: veranda kirişinin bağlandığı özel H
    pi, pj = byid[J['i']], byid[J['j']]
    later = max(pi, pj, key=lambda p: (p['step'], p['order']))
    stub = None; st = None
    if tur.startswith('uclu'):
        for q in panels:
            if q['o'] == J['o']: continue
            qx0, qy0, qx1, qy1 = q['rect']; x, y = J['xy']
            if qx0 - 6 <= x <= qx1 + 6 and qy0 - 6 <= y <= qy1 + 6:
                cx, cy = (qx0 + qx1) / 2, (qy0 + qy1) / 2
                v = (cx - x, cy - y); n = math.hypot(*v); stub = [round(v[0] / n), round(v[1] / n)]; st = q['t']; qq = q; break
        assert stub, J
        later = sorted([pi, pj, qq], key=lambda p: (p['step'], p['order']))[1]
    hs.append(dict(xy=[round(J['xy'][0], 2), round(J['xy'][1], 2)], o=J['o'], t=J['t'], tur=tur, card=HC[tur],
                   ad='Özel H (dübelli) · C' if tur == 'ozel_c' else None, stub=stub, stub_t=st,
                   step=later['step'], order=later['order'] + 0.5, room=later['room']))
assert len(hs) == 30, len(hs)
yok = [J for k, J in enumerate(joints) if k not in used]
print('H olmayan ekler (köşe kutusu ya da çektirme U):', [(J['i'], J['j']) for J in yok])

# Alt çerçeve: duvar hatları, kapı boşluklarında kesik
alt = []
for (o, perp, t), ps in lines.items():
    ps.sort(); segs = []
    for a0, a1, i in ps:
        if segs and a0 - segs[-1][1] < 12: segs[-1][1] = max(segs[-1][1], a1)
        else: segs.append([a0, a1])
    cuts = [(byid[i]['op']['a0'], byid[i]['op']['a1']) for a0, a1, i in ps if byid[i]['op'] and byid[i]['op']['kind'].startswith('door')]
    for s0, s1 in segs:
        pts = [s0]
        for c0, c1 in sorted(cuts):
            if s0 < c0 < s1: pts += [c0, c1]
        pts.append(s1)
        for a, b in zip(pts[0::2], pts[1::2]):
            alt.append(dict(o=o, perp=perp, t=t, a0=round(a, 2), a1=round(b, 2), duvar='dis' if t > 8 else 'ic'))
alt_dis = sum(s['a1'] - s['a0'] for s in alt if s['duvar'] == 'dis'); alt_ic = sum(s['a1'] - s['a0'] for s in alt if s['duvar'] == 'ic')

# İç kapılar (K-01 kanadı; bu projede iç kapılar alıcıya ait): menteşe, kapalı ve açık yön planın kanat ve yaylarından
doors = [
    dict(room='yatak1', hinge=[256, 296.27], closed=[0, 1], open=[-1, 0]),
    dict(room='banyo', hinge=[280.32, 401.75], closed=[1, 0], open=[0, 1]),
    dict(room='yatak2', hinge=[507, 294.95], closed=[0, 1], open=[1, 0]),
]

# Veranda (kaynaklı detaylar paftası A, B, C; plan bloğundaki çelik profiller): kolon 3 × 240, ön kiriş B 574,75, yan ve orta kirişler 140
veranda = dict(
    kolon=[[0, -150, 10, -140], [313.75, -150, 323.75, -140], [564.75, -150, 574.75, -140]],
    kiris_on=[0, -150, 574.75, -140],
    kiris=[[0, -140, 10, 0], [313.75, -140, 323.75, 0], [564.75, -140, 574.75, 0]],
)

# Duvar üstü omegaları (yükleme listesinin formülleriyle uyumlu yerler)
#  saçak omegası: makas saçaklarının oturduğu hatlar (arka duvar 900, ön duvar sağ kısmı 325,25, veranda yan kirişleri 2 × 150 = 1525,25 → 7 adet)
#  100'lük duvar omegası: saçak ve baş makas omegası gelmeyen yer (ön duvarın cumba altı, 574,75)
#  baş makas omegası: üç baş makasın altı (sol ve sağ duvar, veranda ön kirişi)
omega_duvar = [
    dict(tur='sacak', o='h', perp=595, a0=0, a1=900, out=1, yer='arka duvar'),
    dict(tur='sacak', o='h', perp=5, a0=574.75, a1=900, out=-1, yer='ön duvar, cumbanın sağı'),
    dict(tur='sacak', o='v', perp=5, a0=-150, a1=0, out=-1, yer='veranda sol yan kirişi'),
    dict(tur='sacak', o='v', perp=569.75, a0=-150, a1=0, out=1, yer='veranda sağ yan kirişi'),
    dict(tur='duvar', o='h', perp=5, a0=0, a1=574.75, out=-1, yer='ön duvar, cumba altı'),
    dict(tur='bas', o='v', perp=5, a0=0, a1=600, out=-1, yer='sol duvar, MKS01 altı'),
    dict(tur='bas', o='v', perp=895, a0=0, a1=600, out=1, yer='sağ duvar, MKS08 altı'),
    dict(tur='bas', o='h', perp=-145, a0=0, a1=574.75, out=-1, yer='veranda ön kirişi, MKS09 altı'),
    # 60'lık duvar omegası: iç duvarların üstü (Lokman 25.10.2026); kapı üstlerinden ve H'lardan kesintisiz geçer.
    # Listede 60'lık duvar omegası toplamı 127,64 m = tavan omegası 111,8 m + iç duvar üstleri ~15 m.
    dict(tur='ic', o='h', perp=276.25, a0=10, a1=259, out=1, yer='salon ile yatak odası 1 arası'),
    dict(tur='ic', o='h', perp=276.25, a0=504, a1=890, out=1, yer='salon ile yatak odası 2 arası'),
    dict(tur='ic', o='v', perp=256, a0=279.25, a1=590, out=1, yer='yatak odası 1 ile banyo ve hol arası'),
    dict(tur='ic', o='v', perp=507, a0=279.25, a1=590, out=1, yer='banyo ve hol ile yatak odası 2 arası'),
    dict(tur='ic', o='h', perp=401.75, a0=259, a1=504, out=1, yer='hol ile banyo arası'),
]

# Makaslar (SketchUp modeli: MKS01–08 ana çatı, y boyunca −30…630; MKS09–10 cumba, x boyunca −30…604,8; MKS11–12 cumba ara makası)
# Baş makaslar (MKS01, MKS08, MKS09): dış yüzü baş makas omegasının dış kanadıyla aynı hizada; betopan makasa dayanır,
# alt ucu omeganın dış kanalına oturur (Lokman çizimi 25.10.2026). Kanat duvar dış yüzünün 1,1 mm dışında → makas ekseni 4 − 0,11.
BAS_DIS = 0.11
makas = [dict(ad=f'MKS{i + 1:02d}', aile='ana', rol='bas' if i in (0, 7) else 'orta', konum=c, bas=-30, son=630)
         for i, c in enumerate([4 - BAS_DIS, 130.5, 256, 381.5, 507, 632.5, 758, 896 + BAS_DIS])]
makas += [dict(ad='MKS09', aile='cumba', rol='bas', konum=-146 - BAS_DIS, bas=-30, son=604.75),
          dict(ad='MKS10', aile='cumba', rol='orta', konum=-34, bas=-30, son=604.75),
          dict(ad='MKS11', aile='ara', rol='ara', konum=91, bas=111.4, son=463.5, yuz=87),
          dict(ad='MKS12', aile='ara', rol='ara', konum=191, bas=207.6, son=367.2, yuz=187)]

# Tavan omegaları (tavan omega yerleşim planı, 45 parça)
omega = []
for x in [10, 70, 130, 190, 250, 310, 370, 430, 490, 550]:
    omega.append(dict(yon='y', konum=x, bas=-140, son=0, oda='veranda'))
for y in [33.3, 93.3, 153.3, 213.3, 273.3]:
    for a, b in [(10, 375), (375, 740), (740, 890)]: omega.append(dict(yon='x', konum=y, bas=a, son=b, oda='salon'))
for y in [278.8, 338.8, 398.8]: omega.append(dict(yon='x', konum=y, bas=259, son=504, oda='hol'))
for y in [410, 470, 530, 590]: omega.append(dict(yon='x', konum=y, bas=259, son=504, oda='banyo'))
for y in [290, 350, 410, 470, 530, 590]: omega.append(dict(yon='x', konum=y, bas=10, son=253, oda='yatak1'))
for y in [290, 350, 410, 470, 530, 590]: omega.append(dict(yon='x', konum=y, bas=510, son=875, oda='yatak2'))
omega.append(dict(yon='x', konum=590, bas=875, son=890, oda='yatak2'))
for o in omega: o['boy'] = round(o['son'] - o['bas'], 2)

# Aşık paftası: sıralar saçaktan eğim boyunca (cm) ve paftadaki boylar
asik = dict(
    ana_sira=[12.4, 47.4, 107.4, 167.4, 227.4, 287.4, 337.0],      # paftada son sıra mahyada; iki yüzün mahya aşıkları arası ~20 cm
    cumba_sira=[10.5, 35.4, 95.4, 155.4, 215.4, 275.4, 325.0],
    pafta=dict(arka=[[410, 410, 140]] * 7,
               on_sag=[[410, 230.022], [410, 175.287], [410, 120.552], [410, 65.816], [410, 11.081], [366.346], [334.391]][::-1],
               on_sol=[[39.096], [93.831], [148.566], [203.302], [258.037], [312.772]],
               cumba=[[157.08], [181.695], [240.807], [299.919], [359.031], [410, 8.143], [410, 67.255]]),
    toplam_cm=15396.9, liste='AŞIK L:4200 · 43 adet (toplam / 410 + 5)',
)
# Çatı kaplama paftası: trapez (80 cm kapatır) — ana çatı 350'lik, cumba 340'lık
kaplama = dict(arka=dict(x0=-30, n=12), on_sag=dict(x1=930, n=7), on_sol=dict(x0=-30, n=2), cumba=dict(y0=-180, n=4),
               liste=[["(ANTRASİT) TRAPEZ SAC (80 CM KAPATIR) 3500", 21], ["(ANTRASİT) TRAPEZ SAC (80 CM KAPATIR) 3400", 8],
                      ["TRAPEZ SAC MAHYASI L:800", 25], ["(ANTRASİT) TERS MAHYA L:2800", 4], ["TERS MAHYA KENAR KUTULARI", 8]])
betopan = dict(adet=6, boyut='125 × 250', yarim=250)
# Dere ve iniş (makas ve dere yerleşim planı)
dere = dict(
    hatlar=[dict(ad='arka', yon='x', a0=-30.2, a1=930.2, kenar=630.2, out=1, pafta=958),
            dict(ad='ön', yon='x', a0=604.95, a1=930.2, kenar=-30.2, out=-1, pafta=324.2),
            dict(ad='cumba sol', yon='y', a0=-180.2, a1=-30.2, kenar=-30.2, out=-1, pafta=180),
            dict(ad='cumba sağ', yon='y', a0=-180.2, a1=-45.4, kenar=604.95, out=1, pafta=180)],
    inisler=[dict(hat='arka', s=-29, yuz=600, duvar='arka duvar'), dict(hat='arka', s=503, yuz=600, duvar='arka duvar'),
             dict(hat='arka', s=929, yuz=600, duvar='arka duvar'), dict(hat='ön', s=929, yuz=0, duvar='ön duvar'),
             dict(hat='ön', s=628.5, yuz=0, duvar='ön duvar'), dict(hat='cumba sol', s=-180, yuz=0, duvar='veranda kolonu'),
             dict(hat='cumba sağ', s=-180, yuz=574.75, duvar='veranda kolonu')],
    toplam_pafta=1642.2, liste='( ANTRASİT ) METAL DERE L:4000 · 5 adet; iniş takımı 7')

def kart(k):
    v = CARDS[k]; return dict(ad=v['ad'], olcu=v.get('olcu'), ifc=v.get('ifc'), birim=v.get('birim'))
kodlar = sorted({p['card'] for p in panels if p['card']} | {h['card'] for h in hs if h['card']} | {p['card'] for p in posts if p['card']} | {'K-01', 'K-02', 'P-01', 'V-01', 'V-02', 'MA-01', 'MA-02'})
data = dict(
    kaynak='Montaj paftası DWG (19 pafta) ve yükleme listesi; makaslar SketchUp modelinden. Kodla okundu.',
    dis=[900, 600], h=250,
    rooms=rooms, panels=panels, posts=posts, ceku=ceku, hs=hs, alt=alt,
    alt_m=dict(dis=round(alt_dis / 100, 2), ic=round(alt_ic / 100, 2)),
    veranda=veranda, omega_duvar=omega_duvar, makas=makas, omega=omega, asik=asik, kaplama=kaplama,
    betopan=betopan, dere=dere, doors=doors,
    cards={k: kart(k) for k in kodlar},
)
json.dump(data, open(os.path.join(D, 'data.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
print('pano', len(panels), Counter(p['card'] or p['ad'] for p in panels))
print('H', Counter(h['card'] or h['ad'] for h in hs))
print('oda/adım', Counter((p['room']) for p in panels), Counter(h['room'] for h in hs))
print('alt çerçeve m', data['alt_m'], 'parça', len(alt))
print('3lü', [(h['xy'], h['stub'], h['room']) for h in hs if h['stub']])
print('tavan omega', len(omega), round(sum(o['boy'] for o in omega) / 100, 2), 'm')
print('boyut', len(json.dumps(data)))
