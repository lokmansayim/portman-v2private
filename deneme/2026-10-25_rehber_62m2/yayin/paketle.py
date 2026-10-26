"""62 m² Beşik + Cumba montaj rehberinin herkese açık yayın paketi (kart 104/116, 26.10.2026).

PK-01 paketleyicisinin (deneme/2026-10-24_montaj_rehberi/yayin/paketle.py) bu rehbere uyarlanmışı:
sayfa rehber/uret.py ile üretilir (kabuk.html + sahne.js + data.json), modül betiği esbuild ile yorumsuz yazılır
(kod aynı; yalnız boşluk ve yorumlar gider), iç notlar kurallarla temizlenir, sonra YASAK taraması.

Kullanım: python3 paketle.py --npm <npm pack klasörü> --esbuild <esbuild yolu> [--marka cikar]
  --marka kalsin (varsayılan) | cikar : "Izocam" / "Izocam-Knauf" malzeme adı sayfada kalsın mı (Lokman karar verir)
Çıktı (cikti/, depoya girmez): paket/, rehber_paket.tgz, rehber_kur.sh (vps/rehber_yayin.sh + gömülü paket)
"""
import argparse, base64, glob, gzip, hashlib, io, json, os, re, shutil, subprocess, sys, tarfile

B = os.path.dirname(os.path.abspath(__file__))
REHBER = os.path.join(B, '..', 'rehber')
DEPO = os.path.abspath(os.path.join(B, '..', '..', '..'))
CIKTI = os.path.join(B, 'cikti')
PAKET = os.path.join(CIKTI, 'paket')
PROJE, KISA = '62 m² Beşik + Cumba', '62 m²'

NOT_METNI = ('Bu rehber 62 m² Beşik + Cumba montaj paftasından kurulan 3B modeldir. Parça yerleri paftadan, adetler '
             'yükleme listesindendir. Çatıda OSB ve nem bariyeri yoktur; trapez sac doğrudan aşıkların üstüne gelir. '
             'Ölçüler bilgi içindir; uygulamada paftadaki ölçüler esastır.')

S = r'''(?:"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`)'''   # JS dize sabiti
# (desen, yerine, açıklama, en az eşleşme). Sıra önemli: özel kurallar genelden önce.
DEGISIM = [
    (r'<p class="note">Kaynak:.*?</p>', f'<p class="note">{NOT_METNI}</p>', 'kaynak notu', 1),
    (r',\s*\[\s*"Kaynak"\s*,\s*' + S + r'\s*\]', '', 'kart Kaynak satırları (ortada/sonda)', 1),
    (r'\[\s*"Kaynak"\s*,\s*' + S + r'\s*\]\s*,?', '', 'kart Kaynak satırları (tek/başta)', 1),
    (r' \(Lokman, 26\.10\.2026; PK-01’de sandviç panelle 13 cm\); kesin ölçü teyit bekler', '', 'alın sacı teyit notu', 1),
    (r'\((?:Lokman|Lokman’ın|Lokman\'ın)[^;()]*;\s*', '(', 'Lokman; ... parantez başları', 2),
    (r' cm varsayım\)', ' cm, yaklaşık)', 'U dudağı varsayım', 1),
    (r'\s?\([^()]*Lokman[^()]*\)', '', 'Lokman geçen parantezler', 1),
    (r'Alpha Mini düzeni', 'Makas düzeni', 'makas metni', 1),
    (r'<meta name="claude:viewport-fit-sides"[^>]*>\n?', '', 'artefakt meta', 1),
    (r'<link rel="preconnect"[^>]*>\n?', '', 'Google Fonts preconnect', 2),
    (r'<link rel="stylesheet" href="https://fonts\.googleapis\.com[^>]*>', '<link rel="stylesheet" href="yazi/yazi.css">',
     'Google Fonts → yerel', 1),
    (r'"three": "https://cdn\.jsdelivr\.net/npm/three@0\.160\.0/build/three\.module\.js"', '"three": "./js/three.module.js"',
     'importmap three', 1),
    (r'"three/addons/": "https://cdn\.jsdelivr\.net/npm/three@0\.160\.0/examples/jsm/"', '"three/addons/": "./js/addons/"',
     'importmap addons', 1),
    (r'<title>[^<]*</title>', f'<title>PortatifEv Montaj Rehberi · {KISA}</title>\n<meta name="robots" content="noindex, nofollow">'
     '\n<meta name="referrer" content="no-referrer">\n__CSP__', 'başlık + noindex', 1),
]
MARKA = [(r' \(Izocam\)', '', 'Izocam (adım metni)', 1),
         (r' \(Izocam-Knauf\)', '', 'Izocam-Knauf (malzeme satırı)', 1),
         (r' \(IZOCAM-KNAUF\)', '', 'IZOCAM-KNAUF (liste satırı)', 1)]
YASAK = ['lokman', 'teyit', 'paftada yok', '.bde', 'alpha mini', 'lytecad', 'sketchup', 'dwg', 'ums metal', 'assan',
         'varsayım', 'varsayıl', 'tedarik', 'portman', 'astra', 'ubeyd', 'tatar', 'patron', '["kaynak"', "['kaynak'",
         'kaynak:', '__proje__', '__kisa__', '__data__', '__script__', '__gorseller__', 'jsdelivr', 'googleapis',
         'gstatic', 'http://', 'https://']
TELEFON = re.compile(r'(?<![\d.,])(?:\+?90[ -]?)?0?5\d{2}[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}(?![\d.,])')
FONTLAR = [('barlow-condensed', ['500', '600', '700']), ('ibm-plex-mono', ['400', '500']), ('source-sans-3', ['400', '600'])]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def uygula(html, kurallar):
    for desen, yeni, ad, en_az in kurallar:
        html, n = re.subn(desen, yeni, html, flags=re.S)
        if n < en_az:
            sys.exit(f'HATA: maskeleme kuralı beklenenden az eşleşti ({n} < {en_az}): {ad}')
        print(f'  maske {n:2d} × {ad}')
    return html


def denetle(metin, ad):
    k = metin.lower()
    kalan = [y for y in YASAK if y in k]
    if kalan:
        for y in kalan:
            for m in list(re.finditer(re.escape(y), k))[:3]:
                print(f'  YASAK "{y}" {ad}: …{metin[max(0, m.start() - 70):m.start() + 70]!r}…')
        sys.exit('HATA: herkese açık pakette iç not ya da dış bağlantı kaldı')
    if TELEFON.search(metin):
        sys.exit(f'HATA: {ad} içinde telefona benzeyen dizi var')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--npm', required=True)
    ap.add_argument('--esbuild', required=True)
    ap.add_argument('--marka', choices=['kalsin', 'cikar'], default='kalsin')
    a = ap.parse_args()
    npm = os.path.abspath(a.npm)
    if os.path.exists(PAKET):
        shutil.rmtree(PAKET)
    os.makedirs(PAKET)

    # 1 · ham sayfa: rehber/uret.py ile (galeri açık)
    ham = os.path.join(CIKTI, 'ham.html')
    subprocess.run([sys.executable, os.path.join(REHBER, 'uret.py'), ham, '--proje', PROJE, '--kisa', KISA, '--gorsel'],
                   check=True, stdout=subprocess.DEVNULL)
    html = open(ham, encoding='utf-8').read()
    # data.json'daki iç kaynak alanı
    html, n = re.subn(r'("kaynak":)"[^"]*"', r'\1"62 m² Beşik + Cumba montaj paftası ve yükleme listesi"', html, count=1)
    if n != 1:
        sys.exit('HATA: data kaynak alanı bulunamadı')
    # 2 · modül betiği yorumsuz (esbuild yalnız boşluk/yorum küçültür; adlar ve sözdizimi aynı)
    m = re.search(r'<script type="module">(.*?)</script>', html, flags=re.S)
    kucuk = subprocess.run([a.esbuild, '--loader=js', '--format=esm', '--target=es2022', '--charset=utf8',
                            '--legal-comments=none', '--minify-whitespace'], input=m.group(1).encode(),
                           capture_output=True, check=True).stdout.decode()
    html = html[:m.start(1)] + '\n' + kucuk + html[m.end(1):]
    print(f'modül betiği: {len(m.group(1))} → {len(kucuk)} karakter (yorumsuz)')
    print('maskeleme:')
    html = uygula(html, DEGISIM + (MARKA if a.marka == 'cikar' else []))
    # 3 · tam belge + CSP
    bas = html.index('</style>') + len('</style>')
    html = ('<!doctype html>\n<html lang="tr">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + html[:bas] + '\n</head>\n<body>\n' + html[bas:].lstrip('\n') + '</body>\n</html>\n')
    betikler = re.findall(r'<script type="(importmap|module)">(.*?)</script>', html, flags=re.S)
    if len(betikler) != 2:
        sys.exit(f'HATA: 2 satır içi betik bekleniyordu, {len(betikler)} bulundu')
    ozet = ' '.join("'sha256-%s'" % base64.b64encode(hashlib.sha256(g.encode()).digest()).decode() for _, g in betikler)
    csp = ("default-src 'none'; script-src 'self' %s; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
           "font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'" % ozet)
    html = html.replace('__CSP__', f'<meta http-equiv="Content-Security-Policy" content="{csp}">')
    denetle(html, 'index.html')
    open(os.path.join(PAKET, 'index.html'), 'w', encoding='utf-8').write(html)
    print(f'  marka: {a.marka} · Izocam geçişi: {html.lower().count("izocam")}')

    # 4 · görseller (bayt bayt; bayi adı yok, iç ibare yok — 26.10 gözle bakıldı)
    for kay in sorted(glob.glob(os.path.join(REHBER, 'gorsel', '*.jpg'))):
        rel = os.path.relpath(kay, REHBER)
        denetle(rel, 'görsel adı')
        os.makedirs(os.path.join(PAKET, 'gorsel'), exist_ok=True)
        shutil.copyfile(kay, os.path.join(PAKET, rel))
    for rel in set(re.findall(r'"(gorsel/[^"]+\.(?:jpg|png))"', html)):
        if not os.path.exists(os.path.join(PAKET, rel)):
            sys.exit(f'HATA: sayfanın istediği görsel pakette yok: {rel}')

    # 5 · Three.js 0.160.0 ve yazı tipleri (latin + latin-ext)
    three = os.path.join(npm, 'three-0.160.0', 'package')
    os.makedirs(os.path.join(PAKET, 'js', 'addons', 'controls'))
    shutil.copyfile(os.path.join(three, 'build', 'three.module.js'), os.path.join(PAKET, 'js', 'three.module.js'))
    for imp in sorted(set(re.findall(r"from\s*['\"]three/addons/([^'\"]+)['\"]", html))):
        hedef = os.path.join(PAKET, 'js', 'addons', imp)
        os.makedirs(os.path.dirname(hedef), exist_ok=True)
        shutil.copyfile(os.path.join(three, 'examples', 'jsm', imp), hedef)
        print(f'  addon: {imp}')
    if not os.path.exists(os.path.join(PAKET, 'js', 'addons', 'controls', 'OrbitControls.js')):
        sys.exit('HATA: OrbitControls.js pakete girmedi (import deseni)')
    shutil.copyfile(os.path.join(three, 'LICENSE'), os.path.join(PAKET, 'js', 'LICENSE-three.txt'))
    os.makedirs(os.path.join(PAKET, 'yazi'))
    css = []
    for ad, agirliklar in FONTLAR:
        kok = glob.glob(os.path.join(npm, f'fontsource-{ad}-*', 'package'))
        if len(kok) != 1:
            sys.exit(f'HATA: {ad} yazı tipi paketi bulunamadı')
        kok = kok[0]
        shutil.copyfile(os.path.join(kok, 'LICENSE'), os.path.join(PAKET, 'yazi', f'OFL-{ad}.txt'))
        for w in agirliklar:
            for blok in re.findall(r'/\* [^*]+ \*/\s*@font-face \{.*?\}', open(os.path.join(kok, f'{w}.css'), encoding='utf-8').read(), flags=re.S):
                alt = re.search(r'/\* (\S+) \*/', blok).group(1)
                if not (alt.endswith(f'-latin-{w}-normal') or alt.endswith(f'-latin-ext-{w}-normal')):
                    continue
                shutil.copyfile(os.path.join(kok, 'files', f'{alt}.woff2'), os.path.join(PAKET, 'yazi', f'{alt}.woff2'))
                css.append(re.sub(r'src: [^;]+;', f"src: url(./{alt}.woff2) format('woff2');", blok))
    open(os.path.join(PAKET, 'yazi', 'yazi.css'), 'w', encoding='utf-8').write('\n\n'.join(css) + '\n')
    open(os.path.join(PAKET, 'robots.txt'), 'w').write('User-agent: *\nDisallow: /\n')

    # 6 · SHA256SUMS, belirlenimci tgz, tek dosya kurulum betiği
    dosyalar = sorted(os.path.relpath(p, PAKET) for p in glob.glob(os.path.join(PAKET, '**', '*'), recursive=True) if os.path.isfile(p))
    open(os.path.join(PAKET, 'SHA256SUMS'), 'w').write(
        ''.join(f'{sha(open(os.path.join(PAKET, r), "rb").read())}  {r}\n' for r in dosyalar))
    tampon = io.BytesIO()
    with tarfile.open(fileobj=tampon, mode='w', format=tarfile.PAX_FORMAT) as t:
        for r in dosyalar + ['SHA256SUMS']:
            ti = t.gettarinfo(os.path.join(PAKET, r), arcname=r)
            ti.mtime, ti.uid, ti.gid, ti.uname, ti.gname, ti.mode = 1761436800, 0, 0, 'root', 'root', 0o644
            t.addfile(ti, open(os.path.join(PAKET, r), 'rb'))
    tgz = os.path.join(CIKTI, 'rehber_paket.tgz')
    open(tgz, 'wb').write(gzip.compress(tampon.getvalue(), mtime=0))
    ozet_tgz = sha(open(tgz, 'rb').read())
    boyut = sum(os.path.getsize(os.path.join(PAKET, r)) for r in dosyalar)
    print(f'paket: {len(dosyalar)} dosya, {boyut / 1e6:.2f} MB; tgz {os.path.getsize(tgz) / 1e6:.2f} MB; sha256 {ozet_tgz}')
    betik = open(os.path.join(DEPO, 'vps', 'rehber_yayin.sh'), encoding='utf-8').read()
    if '# __PAKET_YERI__' not in betik:
        sys.exit('HATA: vps/rehber_yayin.sh içinde "# __PAKET_YERI__" yok')
    gomulu = ("PAKET_SHA256='%s'\npaket_yaz() {\n  base64 -d > \"$1\" <<'__PAKET_SONU__'\n%s__PAKET_SONU__\n}"
              % (ozet_tgz, base64.encodebytes(open(tgz, 'rb').read()).decode()))
    kur = os.path.join(CIKTI, 'rehber_kur.sh')
    open(kur, 'w', encoding='utf-8').write(betik.replace('# __PAKET_YERI__', gomulu, 1))
    print(f'kurulum betiği: {kur} ({os.path.getsize(kur) / 1e6:.2f} MB)')


if __name__ == '__main__':
    main()
