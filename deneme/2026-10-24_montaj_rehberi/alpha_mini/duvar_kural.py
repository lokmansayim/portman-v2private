"""Duvar paneli: makine işlemlerini YALNIZ geometriden türet, Frame Builder CSV'siyle kıyasla.

Girdi (kör): çubuk eksenleri ve boyları (CSV x1..y2), çubuk türü (SKP `code`), panel ayarından servis deliği
yükseklikleri ve elle eklenmiş servis delikleri. CSV'nin işlem listeleri yalnız kıyasta kullanılır.

Kurallar (DVR1'den çıkarıldı; ikinci bir panelde sınanmadı):
- Her kesişen çubuk çiftinde "alan" çubuk (kanalı açık olan) ve "giren" çubuk var. Alan: önceliği yüksek tür.
- DIMPLE: iki eksenin kesişimi, iki çubukta da.
- LIP_CUT (alan çubukta): giren çubuğun ekseni, alanın giren tarafındaki kenarını kestiği yer; uçtan en az 31.
- SWAGE (giren çubukta): kesişim ucuna W'den yakınsa uçtan 34, değilse kesişimde (ortadan geçen dikme).
- NOTCH: eşik (Ws) ve lentonun (Hb) uçtaki kesişiminde, uçtan 25.
- SERVICE_HOLE: tam boy dikmede döşemeden 610 ve 1830 (panel ayarı); artı elle eklenenler.
- Etiket: alan çubuk girene doğru açılır; bir şey almayan çubuk aşağı (dikeyse +x) açılır.
  Açık yüz çubuk yönünün solundaysa LABEL_NRM, sağındaysa LABEL_INV.

Kullanım: python duvar_kural.py kaynak/DVR1_duvar.csv kaynak/DVR1_fbd.json [--yaz uretilen.csv]
"""
import argparse, collections, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import csv_oku

W = 54.0; H = W / 2                    # düzlem içi genişlik (80S54: flanş 54)
LIP_UC, SWAGE_UC, NOTCH_UC = 31.0, 34.0, 25.0
ONCELIK = {'Bp': 5, 'Tp': 5, 'Ws': 4, 'Hb': 4, 'Ks': 3, 'St': 3, 'Ng': 1, 'Wbh': 1}
ISLEMLER = ('DIMPLE', 'LIP_CUT', 'SWAGE', 'NOTCH', 'SERVICE_HOLE')
PAY = 0.1                              # mm; kabul ölçütü ±1 mm, SKP'nin inç yuvarlaması ~0,05 mm


def eksen(p):
    L = math.hypot(p['x2'] - p['x1'], p['y2'] - p['y1'])
    return (p['x1'], p['y1']), ((p['x2'] - p['x1']) / L, (p['y2'] - p['y1']) / L), L


def kesisim(a, b, pay=0.5):
    (ax, ay), (ux, uy), La = eksen(a); (bx, by), (vx, vy), Lb = eksen(b)
    den = ux * vy - uy * vx
    if abs(den) < 1e-9:
        return None
    t = ((bx - ax) * vy - (by - ay) * vx) / den; s = ((bx - ax) * uy - (by - ay) * ux) / den
    return (t, s) if -pay <= t <= La + pay and -pay <= s <= Lb + pay else None


def turet(P, servis_yuk, elle):
    """P: [{'ad','kod','x1','y1','x2','y2'}]. Dönüş: {ad: {islem: [konum]}}, {ad: etiket}."""
    uret = {p['ad']: collections.defaultdict(list) for p in P}; acik = collections.defaultdict(list)
    for i, a in enumerate(P):
        for b in P[i + 1:]:
            k = kesisim(a, b)
            if not k:
                continue
            R, I, tR, tI = (a, b, k[0], k[1]) if ONCELIK[a['kod']] >= ONCELIK[b['kod']] else (b, a, k[1], k[0])
            (rx, ry), (ux, uy), LR = eksen(R); (ix, iy), (vx, vy), LI = eksen(I)
            uret[R['ad']]['DIMPLE'].append(tR); uret[I['ad']]['DIMPLE'].append(tI)
            uzak = LI if tI < LI / 2 else 0.0                         # giren çubuğun gövdesi hangi tarafta
            nx, ny = -uy, ux
            taraf = 1 if (ix + vx * uzak - rx) * nx + (iy + vy * uzak - ry) * ny > 0 else -1
            vn = vx * nx + vy * ny
            lip = tR + (taraf * H * (vx * ux + vy * uy) / vn if abs(vn) > 1e-9 else 0.0)
            uret[R['ad']]['LIP_CUT'].append(min(max(lip, LIP_UC), LR - LIP_UC)); acik[R['ad']].append(taraf)
            if R['kod'] in ('Ws', 'Hb') and (tR <= W or tR >= LR - W):
                uret[R['ad']]['NOTCH'].append(NOTCH_UC if tR <= W else LR - NOTCH_UC)
            uret[I['ad']]['SWAGE'].append(SWAGE_UC if tI <= W else LI - SWAGE_UC if tI >= LI - W else tI)
    etiket = {}
    for p in P:
        if p['kod'] in ('St', 'Ks') and abs(p['x1'] - p['x2']) < 1e-6:
            y0, L = min(p['y1'], p['y2']), eksen(p)[2]
            uret[p['ad']]['SERVICE_HOLE'] += [h - y0 for h in servis_yuk if y0 < h < y0 + L]
        uret[p['ad']]['SERVICE_HOLE'] += elle.get(p['ad'], [])
        if acik[p['ad']]:
            t = collections.Counter(acik[p['ad']]).most_common(1)[0][0]
        else:
            (_, _), (ux, uy), _ = eksen(p)
            t = 1 if (ux < -1e-9 or (abs(ux) <= 1e-9 and -uy > 0)) else -1   # sol normal (-uy, ux) aşağı ya da +x mi
        etiket[p['ad']] = 'LABEL_NRM' if t == 1 else 'LABEL_INV'
    return uret, etiket


SAPMA = [0.0]


def esles(a, b, pay=PAY):
    kalan = sorted(b); es = 0
    for x in sorted(a):
        m = sorted((y for y in kalan if abs(x - y) <= pay), key=lambda y: abs(x - y))
        if m:
            kalan.remove(m[0]); es += 1; SAPMA[0] = max(SAPMA[0], abs(x - m[0]))
    return es


def sayi(x):                           # CSV'deki gibi: 2 ondalığa kadar, en az bir ondalık (27.0, 1221.99)
    s = f'{x:.2f}'.rstrip('0')
    return s + '0' if s.endswith('.') else s


def yaz(yol, ust, P, uret, etiket):
    with open(yol, 'w', encoding='utf-8') as f:
        for k in ('UNIT', 'VERSION', 'PROFILE', 'FRAMESET'):
            f.write(','.join([k] + ust[k]) + '\n')
        for p in P:
            alan = [p['ad'], etiket[p['ad']], str(p['adet']), sayi(p['boy']), p['tip'], sayi(p['govde']), sayi(p['flans']),
                    sayi(p['kalinlik']), p['sinif']] + [sayi(p[k]) for k in ('x1', 'y1', 'x2', 'y2')]
            for k in ISLEMLER:
                for x in sorted(uret[p['ad']][k]):
                    alan += [k, sayi(x)]
            f.write('COMPONENT,' + ','.join(alan + ['CUT', sayi(p['boy'])]) + '\n')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('csv'); ap.add_argument('fbd'); ap.add_argument('--yaz')
    a = ap.parse_args()
    ust, P = csv_oku.oku(a.csv)
    pn = json.load(open(a.fbd, encoding='utf-8'))['paneller'][0]
    U = {u['csv_ad']: u for u in pn['uyeler']}
    for p in P:
        p['kod'] = U[p['ad']]['kod']
    servis = [float(x) for x in (pn['panel'].get('horz_service_hole_pos') or '').split('|') if x]
    elle = collections.defaultdict(list)
    for kod, x1, y1, x2, y2, kon in pn['panel']['added_service_holes']:
        for p in P:
            if p['kod'] == kod and abs(p['x1'] - x1) < 1 and abs(p['y1'] - y1) < 1:
                elle[p['ad']] += kon
    uret, etiket = turet(P, servis, elle)

    # 1) SKP'nin kendi işlem listesi CSV ile aynı mı (CSV, SKP'nin dışa aktarımı mı)
    skp_es = sum(esles(U[p['ad']]['islem_skp'][k], p['islem'].get(k, []), 0.005) for p in P for k in ISLEMLER)
    skp_flip = sum((U[p['ad']]['flip_x']) == (p['etiket'] == 'LABEL_NRM') for p in P)
    n_csv = sum(len(p['islem'].get(k, [])) for p in P for k in ISLEMLER)
    print(f'SKP = CSV (±0,005 mm): işlem {skp_es}/{n_csv}, flip_x ↔ LABEL_NRM {skp_flip}/{len(P)}')
    # 2) geometriden türetilen işlemler
    SAPMA[0] = 0.0
    print(f'Geometriden türetilen, {len(P)} çubuk (girdi yalnız geometri; kurallar bu panelden çıkarıldı, kör test değil):')
    fark = []; top_es = 0
    for k in ISLEMLER:
        es = sum(esles(uret[p['ad']][k], p['islem'].get(k, [])) for p in P)
        nu = sum(len(uret[p['ad']][k]) for p in P); nc = sum(len(p['islem'].get(k, [])) for p in P)
        top_es += es
        print(f'  {k:12s} CSV {nc:3d} · üretilen {nu:3d} · eşleşen (±0,1 mm) {es:3d}')
        fark += [(p['ad'], k) for p in P if esles(uret[p['ad']][k], p['islem'].get(k, [])) != len(p['islem'].get(k, [])) or len(uret[p['ad']][k]) != len(p['islem'].get(k, []))]
    et = sum(etiket[p['ad']] == p['etiket'] for p in P)
    print(f'  TOPLAM {top_es}/{n_csv} işlem · en büyük sapma {SAPMA[0]:.3f} mm · etiket {et}/{len(P)} · elle eklenen servis deliği (girdi) {sum(len(v) for v in elle.values())}')
    for f in fark:
        print('  FARK', f)
    if a.yaz:
        yaz(a.yaz, ust, P, uret, etiket)
        _, Y = csv_oku.oku(a.yaz)
        ayni = all(esles(y['islem'].get(k, []), p['islem'].get(k, [])) == len(p['islem'].get(k, [])) == len(y['islem'].get(k, []))
                   and y['etiket'] == p['etiket'] and abs(y['boy'] - p['boy']) < 0.01 for y, p in zip(Y, P) for k in ISLEMLER + ('CUT',))
        print(f'  yazıldı: {a.yaz} · geri okununca CSV ile {"aynı (sıra hariç)" if ayni else "FARKLI"}')
