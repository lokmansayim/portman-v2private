"""Montaj rehberi sayfası (62 m², beşik + cumba): kabuk.html + sahne.js + data.json → tek dosya HTML.
Kullanım: python uret.py <çıktı.html> [--proje "<başlık>"] [--kisa "<sekme adı>"] [--gorsel]  (--gorsel: galeri ve adım render'ları açık)"""
import json, os, sys
D = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
cikti = args[0]
proje = args[args.index('--proje') + 1] if '--proje' in args else '62 m² prefabrik'
kisa = args[args.index('--kisa') + 1] if '--kisa' in args else proje   # sekme başlığı
GORSELLER = [
    ['gorsel/ev_on_sol.jpg', 'Ön-soldan: veranda, cumba ve ana çatı; montajı biten ev (ham malzeme; boya ve sıva yok)'],
    ['gorsel/ev_on_sag.jpg', 'Ön-sağdan: cumba ile ana çatının dere hattı, iç köşede dere ve iniş'],
    ['gorsel/ev_arka_sol.jpg', 'Arka-soldan: kalkan, alın sacı ve inişler'],
    ['gorsel/ev_catisiz.jpg', 'Çatısız: oda oda dizilim, iç kapılar, pencereler ve dış kapı'],
    ['gorsel/cati_katman.jpg', 'Çatı katmanları: makas, aşık, trapez sac; tavanda 10 cm cam yünü'],
    ['gorsel/ic_kose.jpg', 'Cumbanın sağı: cumba deresi iç köşede ön dereye bağlanır; inişler duvar ve veranda kolonu boyunca'],
    ['gorsel/bas_detay.jpg', 'Baş makas detayı: betopan makasa dayanır, alt ucu baş makas omegasının dış kanalına oturur'],
    ['gorsel/ev_render_pafta.jpg', 'Hepsi tek paftada'],
] if '--gorsel' in args else []
s = open(os.path.join(D, 'kabuk.html'), encoding='utf-8').read().replace('__SCRIPT__', open(os.path.join(D, 'sahne.js'), encoding='utf-8').read())
d = json.load(open(os.path.join(D, 'data.json'), encoding='utf-8'))
s = s.replace('__DATA__', json.dumps(d, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))
s = s.replace('__GORSELLER__', json.dumps(GORSELLER, ensure_ascii=False)).replace('__KISA__', kisa).replace('__PROJE__', proje)
open(cikti, 'w', encoding='utf-8').write(s)
print(cikti, len(s))
