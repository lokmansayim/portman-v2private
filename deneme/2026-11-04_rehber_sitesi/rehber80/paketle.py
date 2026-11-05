"""İE-18 şablonlu montaj rehberlerinin herkese açık paketi (kart 104; 4.11.2026, 6.11'den beri birden çok rehber).

Girdi: kaynak/ altında Lokman'ın gönderdiği sayfa (İE-18 şablonu + evin altında ön onay paftası); REHBERLER'de her
rehberin kaynağı, görünen adı, çipi ve alt notu. Kararlar (Lokman, 4.11): başlıkta kod görünmez (alan + oda sayısı);
ön onay paftasının "PORTMAN | Bayi … | İş Emri …" satırı silinir.

Temizlik üç katta:
  1. veri (JSON): iç kaynak alanları atılır; değerlerde iç not taşıyan parantezler, cümleler ve maddeler çıkar;
  2. modül betiği: esbuild ile yorumsuz, sonra kart "Kaynak" satırları ve "(Lokman …)" parantezleri;
  3. son kapı: ortak.YASAK taraması (paket bu taramadan geçmezse üretilmez).
Pafta görseli sayfadan ayrı dosyaya çıkar (gorsel/onay_pafta.jpg), üst satırı beyazla örtülür.

Kullanım: python3 paketle.py --rehber <80m2|80m2-21> --npm <npm pack klasörü> --esbuild <esbuild yolu> --cikti <klasör>
"""
import argparse, base64, io, json, os, re, shutil, subprocess, sys
from PIL import Image, ImageDraw

B = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(B))
import ortak  # noqa: E402

def _not(ad):
    return (f'Bu rehber {ad} montaj paftasından kurulan 3B modeldir. Parça yerleri paftadan, adetler yükleme '
            'listesindendir. Evin altında ön onay paftası gerçek ölçekte serilidir. Ölçüler bilgi içindir; '
            'uygulamada paftadaki ölçüler esastır.')


REHBERLER = {   # klasör → kaynak (kaynak/ altında), iç kod, görünen ad, çip
    '80m2': dict(kaynak='TK-01_montaj_rehberi_pdfli.html', kod='TK-01', ad='80 m² 3+1', chip='78,38 m² brüt · 72,71 m² net'),
    '80m2-21': dict(kaynak='TK-04_montaj_rehberi_r08.html', kod='TK-04', ad='80 m² 2+1', chip='77,95 m² brüt · 65,22 m² net'),
}
PAFTA_ORTU = (600, 98, 1880, 142)       # 2481 × 3508 görselde "PORTMAN | Bayi … | İş Emri …" satırı (ölçüldü: y 106–134)

# İç not işaretleri: bunları taşıyan parantez, sonra cümle/madde çıkar.
IC = re.compile(r"varsayı|motor|lokman|pk-01|62 m²|62 m2|kitab|kitap|montaj rehberi|kural|modelinde|model(?:den|inden)\b|"
                r"teyit|sketchup|alpha mini|`|paftası yok|tk-\d\d|deneme|kart modeli|liste de böyle", re.I)
ON_DEGISIM = [   # cümle düşürmeden önce anlamı koruyan kısa değişimler
    (r'motorun kart modeli:\s*', ''), (r'motorun (?:kimlik kartlı )?planından', 'paftadan'),
    (r'{kod} prefabrik', '{ad} prefabrik konut'), (r'\b{kod}\b', '{ad}'),   # yalnız bu evin kodu; başka evin kodu iç nottur
    (r',\s*kitabın aralığıyla', ''), (r'Veranda çatılarında da sıralar kart modelinden, aynı kuralla\.', 'Veranda çatılarında da sıralar aynı düzende.'),
]
ATILAN_ANAHTAR = {'kaynak', 'makas_kaynak', 'dvr_kaynak'}


AD = KOD = None


def _parantez(m):
    """İç not taşıyan parantez: iç notlu maddeler (;) düşer, kalan varsa parantez kalır."""
    ic = m.group(1)
    if not IC.search(ic):
        return m.group(0)
    kalan = [p for p in re.split(r';\s*', ic) if p and not IC.search(p)]
    return f'{m.group(0)[:len(m.group(0)) - len(m.group(0).lstrip())]}({"; ".join(kalan)})' if kalan else ''


KARAR = re.compile(r'\s?\((?:(?:D|İE|BK)-\d{2}[;,]?\s*)+\)|(?<=\()(?:D|İE|BK)-\d{2}[;,]\s*|[;,]\s*(?:D|İE|BK)-\d{2}(?=\))')


def temiz_deger(s):
    if isinstance(s, str):                               # parantez içi karar kodları: "(D-41)", "(D-39; …)", "(…; D-41)"
        s = KARAR.sub('', s)
    if not isinstance(s, str) or not IC.search(s):
        return s
    for d, y in ON_DEGISIM:
        s = re.sub(d.replace('{kod}', KOD), y.replace('{ad}', AD), s)
    onceki = None
    while onceki != s:                                   # iç not taşıyan en içteki parantezler
        onceki = s
        s = re.sub(r'\s?\(([^()]*)\)', _parantez, s)
    if IC.search(s):                                     # cümle ve madde düzeyi
        cumleler = re.split(r'(?<=[.!?])\s+', s)
        s = ' '.join(c for c in cumleler if not IC.search(c))
        if IC.search(s) or not s:
            s = '; '.join(p for p in re.split(r';\s*', s) if p and not IC.search(p))
    return re.sub(r'\s{2,}', ' ', s).strip()


def temiz_veri(x):
    if isinstance(x, dict):
        return {k: temiz_veri(v) for k, v in x.items() if k not in ATILAN_ANAHTAR}
    if isinstance(x, list):
        return [temiz_veri(v) for v in x]
    return temiz_deger(x)


S = r'''(?:"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`)'''
JS_DEGISIM = [   # esbuild çıktısında (çift tırnak, boşluksuz)
    (r',\s*\[\s*"Kaynak"\s*,\s*' + S + r'\s*\]', '', 'Kaynak satırı (sabit)', 1),
    (r',\s*\[\s*"Kaynak"\s*,\s*[A-Za-z_$][\w$.]*(?:\s*\|\|\s*[A-Za-z_$][\w$.]*)?\s*\]', '', 'Kaynak satırı (veriden)', 1),
    (r',\s*\.\.\.\w+\?\[\[\s*"Kaynak"\s*,\s*\w+(?:\.\w+)*\?' + S + r':' + S + r'\]\]:\[\]', '', 'Kaynak satırı (koşullu)', 0),
    (r'\((?:Lokman|Lokman’ın|Lokman\'ın)[^;()`"]*;\s*', '(', 'Lokman; … parantez başı', 0),
    (r' cm varsayım\)', ' cm, yaklaşık)', 'U dudağı varsayım', 0),
    (r'\s?\([^()`"]*Lokman[^()`"]*\)', '', 'Lokman geçen parantezler', 1),
    (r' \(kart modelinde bu kenarın Z’si .*?; liste de böyle sayar\)', '', 'Z kenarı: kart modeli açıklaması', 1),
    (r'\["Kural",`\$\{[^`]*`\]', '["Tavan",`${a.ad.toLocaleLowerCase("tr")} tavanı ters tavan, yeşil alçıpan`]', 'Kural satırı', 0),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rehber', required=True, choices=sorted(REHBERLER))
    ap.add_argument('--npm', required=True)
    ap.add_argument('--esbuild', required=True)
    ap.add_argument('--cikti', required=True, help='paketin yazılacağı klasör (silinip yeniden kurulur)')
    a = ap.parse_args()
    global AD, KOD
    r = REHBERLER[a.rehber]
    KOD = r['kod']
    AD, KISA, CHIP, NOT_METNI = r['ad'], r['ad'], r['chip'], _not(r['ad'])
    KAYNAK = os.path.join(B, 'kaynak', r['kaynak'])
    paket = os.path.abspath(a.cikti)
    if os.path.exists(paket):
        shutil.rmtree(paket)
    os.makedirs(os.path.join(paket, 'gorsel'))
    html = open(KAYNAK, encoding='utf-8').read()

    # 1 · ön onay paftası: ayrı dosya, üst satır örtülü
    m = re.search(r"data:image/jpeg;base64,([A-Za-z0-9+/=]+)", html)
    im = Image.open(io.BytesIO(base64.b64decode(m.group(1)))).convert('RGB')
    if im.size != (2481, 3508):
        sys.exit(f'HATA: pafta görseli boyutu değişmiş {im.size}; örtü yerini yeniden ölç')
    ImageDraw.Draw(im).rectangle(PAFTA_ORTU, fill=(255, 255, 255))
    im.save(os.path.join(paket, 'gorsel', 'onay_pafta.jpg'), 'JPEG', quality=88, optimize=True, progressive=True)
    html = html[:m.start()] + 'gorsel/onay_pafta.jpg' + html[m.end():]
    print('pafta: ayrı dosya, üst satır örtüldü')

    # 2 · veri
    v = re.search(r'(<script type="application/json" id="pafta">)(.*?)(</script>)', html, flags=re.S)
    d = temiz_veri(json.loads(v.group(2)))
    d['kod'] = AD
    d['kabuk'].update(proje=AD, kisa=KISA, chip=CHIP, note=NOT_METNI)
    veri = json.dumps(d, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    html = html[:v.start(2)] + veri + html[v.end(2):]

    # 3 · kabuk (başlık, çip, not; kabuk.html'e üretimde yazılmış hâlleri)
    kab = [(r'<title>[^<]*</title>', ortak.bas_etiketleri(f'PortatifEv Montaj Rehberi · {KISA}'), 1),
           (r'<h1>[^<]*</h1>', f'<h1>{AD} · Montaj Rehberi</h1>', 1),
           (r'<span class="chip">[^<]*</span>', f'<span class="chip">{CHIP}</span>', 1),
           (r'<p class="note">.*?</p>', f'<p class="note">{NOT_METNI}</p>', 1),
           (r'<meta name="claude:viewport-fit-sides"[^>]*>\n?', '', 1),
           (r'<link rel="preconnect"[^>]*>\n?', '', 2),
           (r'<link rel="stylesheet" href="https://fonts\.googleapis\.com[^>]*>', '<link rel="stylesheet" href="yazi/yazi.css">', 1),
           (r'"three": "https://cdn\.jsdelivr\.net/npm/three@0\.160\.0/build/three\.module\.js"', '"three": "./js/three.module.js"', 1),
           (r'"three/addons/": "https://cdn\.jsdelivr\.net/npm/three@0\.160\.0/examples/jsm/"', '"three/addons/": "./js/addons/"', 1)]
    for desen, yeni, en_az in kab:
        html, n = re.subn(desen, lambda _m: yeni, html, flags=re.S)
        if n < en_az:
            sys.exit(f'HATA: kabuk kuralı eşleşmedi: {desen[:40]}')

    # 4 · modül betikleri yorumsuz (esbuild: yalnız boşluk ve yorum), sonra iç not kuralları
    def kucult(m_):
        kod = subprocess.run([a.esbuild, '--loader=js', '--format=esm', '--target=es2022', '--charset=utf8',
                              '--legal-comments=none', '--minify-whitespace'], input=m_.group(1).encode(),
                             capture_output=True, check=True).stdout.decode()
        return '<script type="module">\n' + kod + '</script>'
    html = re.sub(r'<script type="module">(.*?)</script>', kucult, html, flags=re.S)
    print('maskeleme (betik):')
    for desen, yeni, ad, en_az in JS_DEGISIM:
        html, n = re.subn(desen, yeni, html, flags=re.S)
        if n < en_az:
            sys.exit(f'HATA: kural beklenenden az eşleşti ({n} < {en_az}): {ad}')
        print(f'  {n:3d} × {ad}')
    html = ortak.belge_ve_csp(html, 1 + len(re.findall(r'<script type="module">', html)))
    ortak.denetle(re.sub(r'<script type="application/json" id="pafta">.*?</script>', '', html, flags=re.S), 'index.html (betik)')
    ortak.denetle(veri, 'index.html (veri)')
    open(os.path.join(paket, 'index.html'), 'w', encoding='utf-8').write(html)
    addon = ortak.yerel_kutuphaneler(html, paket, a.npm)
    print(f'{AD} paketi: {paket} (addon: {", ".join(addon)})')


if __name__ == '__main__':
    main()
