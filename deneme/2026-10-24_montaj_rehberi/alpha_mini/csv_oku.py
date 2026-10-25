"""Frame Builder üretim CSV'si okuyucu (Howick biçimi; SketchUp eklentisi MRD Frame Builder çıkarır).

Başlık satırları: UNIT, VERSION, PROFILE, FRAMESET <panel>,<proje>.
Parça satırı: COMPONENT, ad, LABEL_NRM|LABEL_INV, adet, boy, tip (C), gövde, flanş, kalınlık, çelik sınıfı,
x1, y1, x2, y2 (panel düzleminde çubuk ekseni, mm), sonra (İŞLEM, konum) çiftleri. Konum (x1,y1) ucundan mm.
İşlemler: DIMPLE (vida deliği), LIP_CUT (dudak kesme), SWAGE (ezme), NOTCH (kertme), SERVICE_HOLE (servis deliği),
CUT (boy kesimi; konumu = boy).

Kullanım: python csv_oku.py kaynak/DVR1_duvar.csv [--maskele cikti.csv]
  --maskele: FRAMESET'teki proje adını (bayi adı içerebilir) PROJE ile değiştirip kopya yazar.
"""
import argparse, collections, re


def oku(yol):
    ust = {}; parcalar = []
    for satir in open(yol, encoding='utf-8-sig'):
        t = [x.strip() for x in satir.strip().split(',')]
        if not t or not t[0]:
            continue
        if t[0] != 'COMPONENT':
            ust[t[0]] = t[1:]; continue
        d = {'ad': t[1], 'etiket': t[2], 'adet': int(t[3]), 'boy': float(t[4]), 'tip': t[5],
             'govde': float(t[6]), 'flans': float(t[7]), 'kalinlik': float(t[8]), 'sinif': t[9],
             'x1': float(t[10]), 'y1': float(t[11]), 'x2': float(t[12]), 'y2': float(t[13]),
             'islem': collections.defaultdict(list), 'sira': []}
        r = t[14:]
        for i in range(0, len(r) - 1, 2):
            d['islem'][r[i]].append(float(r[i + 1])); d['sira'].append((r[i], float(r[i + 1])))
        parcalar.append(d)
    return ust, parcalar


def maskele(yol, cikti, ad='PROJE'):
    with open(yol, encoding='utf-8-sig') as f, open(cikti, 'w', encoding='utf-8') as g:
        for satir in f:
            t = satir.rstrip('\r\n').split(',')
            if t[0] == 'FRAMESET' and len(t) > 2:
                alan = re.search(r'(\d+M2)$', t[2], flags=re.I)   # yalnız alan kalır (ör. 62M2)
                t[2] = ad + ('_' + alan.group(1).upper() if alan else '')
            g.write(','.join(t) + '\n')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('csv'); ap.add_argument('--maskele')
    a = ap.parse_args()
    if a.maskele:
        maskele(a.csv, a.maskele)
    ust, P = oku(a.maskele or a.csv)
    c = collections.Counter()
    for p in P:
        for k, v in p['islem'].items():
            c[k] += len(v)
    print('başlık:', {k: v for k, v in ust.items()})
    print(f'{len(P)} parça · toplam boy {sum(p["boy"] * p["adet"] for p in P):.1f} mm · işlem ' + ' '.join(f'{k}:{v}' for k, v in c.items()))
