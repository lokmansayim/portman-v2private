""".bde harfleri için rol sınaması (Frame Builder CSV'sinin işlem adlarından türeyen hipotez).

Hipotez: h = DIMPLE (her bağlantıda iki çubukta), f = LIP_CUT (yalnız alan çubukta: başlıklar PU/PD),
w = SWAGE (yalnız giren çubukta: çapraz ve dikmeler, uçtan sabit mesafe). n, s, l makasta boş: NOTCH ve
SERVICE_HOLE makasta kullanılmaz (duvar CSV'sinde var); l bilinmiyor.
CSV'deki duvarda uç değerleri: DIMPLE 27, LIP_CUT 31 (uçtan en az), SWAGE 34.

Kullanım: python bde_rol.py kaynak/BDE-58_cati_makas.bde kaynak/BDE-144_cati_makas.bde
"""
import collections, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bde_oku import oku, ALANLAR

BASLIK = ('PU', 'PD')

for yol in sys.argv[1:]:
    S = oku(yol); c = collections.Counter(); uc = collections.defaultdict(collections.Counter)
    for s in S:
        rol = 'başlık' if s['uye'] in BASLIK else 'giren'
        L = s['boy_mm']
        for k in ALANLAR:
            v = s.get(k, [])
            c[(rol, k)] += len(v)
            if v and k in ('h', 'f', 'w'):
                uc[(rol, k)][round(min(v))] += 1; uc[(rol, k)][round(L - max(v))] += 1
        if rol == 'giren':
            c['giren'] += 1; c['iki_h'] += len(s['h']) == 2
            c['w_25'] += len(s['w']) >= 2 and round(min(s['w'])) in (25, 26) and round(L - max(s['w'])) in (25, 26)
    print(f'{os.path.basename(yol)}: {len(S)} çubuk')
    for rol in ('başlık', 'giren'):
        print(f'  {rol:6s} ' + ' '.join(f'{k}:{c[(rol, k)]}' for k in ALANLAR))
    print(f"  giren çubuk {c['giren']} · tam iki h {c['iki_h']} · iki ucunda 25±1 mm w {c['w_25']}")
    print('  başlık uç mesafesi (en sık)  h:', dict(uc[('başlık', 'h')].most_common(3)), ' f:', dict(uc[('başlık', 'f')].most_common(3)))
    print('  giren uç mesafesi (en sık)   w:', dict(uc[('giren', 'w')].most_common(3)))
