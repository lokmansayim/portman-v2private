"""Alpha Mini .bde okuyucu (ASCII, satır başına bir çubuk).

Satır: <makas> <üye kodu> <kesim boyu mm> h: … f: … n: … s: … l: … w: … x1: a y1: b x2: c y2: d
Üye kodları (okunan): PU alt başlık, PD üst başlık, PR/PL topuk dikmesi, SL/SR duvar hattı dikmesi, BD/BR/BL çapraz.
h f n s l w: çubuk boyunca işlem konumları (mm, çubuğun başından). Hangi harfin hangi istasyon olduğu
yazılımcıdan bekleniyor (6 istasyon: kesme, kertme, düzleme, vida, servis deliği, 6. bilinmiyor).
x1 y1 x2 y2: çubuğun makas düzlemindeki uçları (mm). Profil dosya adında: 80-45-10-0,8.

Kullanım: python bde_oku.py kaynak/BDE-58_cati_makas.bde [--json cikti.json]
"""
import argparse, collections, json, re

ALANLAR = ('h', 'f', 'n', 's', 'l', 'w')
SAYI = re.compile(r'^-?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?$')


def oku(yol):
    satirlar = []
    for ham in open(yol, encoding='latin-1'):
        t = ham.split()
        if len(t) < 3 or not SAYI.match(t[2]):
            continue
        d = {'makas': t[0], 'uye': t[1], 'boy_mm': float(t[2].replace(',', '.'))}
        alan = None
        for tok in t[3:]:
            if tok.endswith(':'):
                alan = tok[:-1]; d[alan] = []; continue
            if alan and SAYI.match(tok):
                d[alan].append(float(tok.replace(',', '.')))
        for k in ('x1', 'y1', 'x2', 'y2'):
            v = d.get(k) or [None]
            d[k] = round(v[0], 3) if v[0] is not None else None
        satirlar.append(d)
    return satirlar


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('bde'); ap.add_argument('--json')
    a = ap.parse_args()
    S = oku(a.bde)
    makaslar = collections.OrderedDict()
    for s in S:
        makaslar.setdefault(s['makas'], []).append(s)
    print(f'{len(S)} çubuk, {len(makaslar)} makas')
    for m, uyeler in makaslar.items():
        sayac = collections.Counter(u['uye'] for u in uyeler)
        islem = {k: sum(len(u.get(k, [])) for u in uyeler) for k in ALANLAR}
        print(f'  {m}: {len(uyeler)} çubuk · ' + ' '.join(f'{k}×{v}' for k, v in sorted(sayac.items())) + ' · işlem ' + ' '.join(f'{k}:{v}' for k, v in islem.items()))
    if a.json:
        json.dump(S, open(a.json, 'w'), ensure_ascii=False, indent=1)
