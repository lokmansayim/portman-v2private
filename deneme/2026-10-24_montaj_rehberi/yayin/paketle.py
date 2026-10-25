"""Montaj rehberinin herkese açık yayın paketi (kart 104, 25.10.2026).

Kullanım: python3 paketle.py [--npm <npm pack klasörü>]
Çıktı (cikti/, depoya girmez):
  paket/          index.html (PK-01, iç notlar temiz, noindex, CSP) + gorsel/ + js/ + yazi/ + robots.txt + SHA256SUMS
  rehber_paket.tgz  aynı içerik, belirlenimci tar (sabit zaman, sıralı)
  rehber_kur.sh     vps/rehber_yayin.sh + gömülü paket (tek dosya; Lokman koşar)

Maskeleme kuralları aşağıdaki DEGISIM listesindedir; her biri en az bir kez eşleşmeli.
Son kapı YASAK listesidir: çıktıda (HTML ve görsel adlarında) bunlardan biri kalırsa paket üretilmez.
--npm klasöründe şunlar açılmış olmalı (npm pack + tar): three-0.160.0, fontsource-barlow-condensed-*,
fontsource-ibm-plex-mono-*, fontsource-source-sans-3-*.
"""
import argparse, base64, glob, hashlib, io, json, os, re, shutil, sys, tarfile
from PIL import Image, ImageDraw

B = os.path.dirname(os.path.abspath(__file__))
REHBER = os.path.join(B, '..', 'rehber')
DEPO = os.path.abspath(os.path.join(B, '..', '..', '..'))
CIKTI = os.path.join(B, 'cikti')
PAKET = os.path.join(CIKTI, 'paket')
PROJE = 'PK-01'

# (desen, yerine, açıklama). Desenler düzenli ifade; sıra önemli.
DEGISIM = [
    (r'<p class="note">Kaynak:.*?</p>',
     '<p class="note">Bu rehber PK-01 60 m² montaj paftasından kurulan 3B modeldir. Parça yerleri ve adetleri '
     'paftadandır; ölçüler bilgi içindir, uygulamada paftadaki ölçüler esastır.</p>', 'kaynak notu'),
    (r", \['Kaynak', '[^']*'\]", '', 'kartlardaki Kaynak satırları'),
    (r", \['Durum', 'paftada yok; kesimden varsayıldı, teyit bekliyor'\]", '', 'teyit bekleyen Durum satırı'),
    (r' \(Lokman notu, ölçüler yaklaşık\)', ' (ölçüler yaklaşık)', 'saçak omegası notu'),
    (r' \(PK-01 \.bde ile teyit\)', '', 'makas .bde notu'),
    (r"Ölçüler Lokman'ın el çizimi, ", 'Ölçüler: ', 'kesit yorumu'),
    (r" Lokman'ın kalkan kesiti çizimi, 24\.10\.2026\.", '', 'kalkan yorumu'),
    (r' ?\([^()]*Lokman[^()]*\)', '', 'Lokman geçen parantezler'),
    (r'Alpha Mini / LyteCad düzeni', 'makas düzeni', 'makas yorumu'),
    (r'Alpha Mini düzeni', 'makas düzeni', 'makas metni'),
    (r'Makas düzeni: |makas düzeni: ', 'Makas düzeni: ', None),  # yalnız biçim; eşleşmesi şart değil
    (r'<meta name="claude:viewport-fit-sides"[^>]*>\n?', '', 'artefakt meta'),
    (r'<link rel="preconnect"[^>]*>\n?', '', 'Google Fonts preconnect'),
    (r'<link rel="stylesheet" href="https://fonts\.googleapis\.com[^>]*>',
     '<link rel="stylesheet" href="yazi/yazi.css">', 'Google Fonts → yerel'),
    (r'"three": "https://cdn\.jsdelivr\.net/npm/three@0\.160\.0/build/three\.module\.js"',
     '"three": "./js/three.module.js"', 'importmap three'),
    (r'"three/addons/": "https://cdn\.jsdelivr\.net/npm/three@0\.160\.0/examples/jsm/"',
     '"three/addons/": "./js/addons/"', 'importmap addons'),
    (r'<title>PortatifEv Montaj Rehberi</title>',
     '<title>PortatifEv Montaj Rehberi · PK-01</title>\n<meta name="robots" content="noindex, nofollow">'
     '\n<meta name="referrer" content="no-referrer">\n__CSP__', 'başlık + noindex'),
]
YASAK = ['lokman', 'teyit', 'paftada yok', '.bde', 'alpha mini', 'lytecad', 'sketchup', 'dwg', 'tedarik',
         'portman', 'astra', 'ubeyd', 'varsayıldı', '__proje__', '__data__', 'jsdelivr', 'googleapis', 'gstatic',
         'http://', 'https://']
TELEFON = re.compile(r'(?<![\d.,])(?:\+?90[ -]?)?0?5\d{2}[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}(?![\d.,])')

# Pafta görselindeki iç ibareler: zemin rengiyle örtülür (2000 × 2808 piksel; konumlar ölçülerek bulundu).
PAFTA_ORTU = [(1148, 2668, 1990, 2702),   # "(Lokman'ın çizimiyle)" → "Kalkan kesiti" kalır
              (340, 2756, 1990, 2790)]    # "· ölçüler pafta ve Lokman'ın çizimlerinden" → tarih kalır
ZEMIN = (246, 245, 241)

FONTLAR = [('barlow-condensed', ['500', '600', '700']), ('ibm-plex-mono', ['400', '500']),
           ('source-sans-3', ['400', '600'])]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def maskele(html):
    for desen, yeni, ad in DEGISIM:
        html, n = re.subn(desen, yeni, html, flags=re.S)
        if ad and n == 0:
            sys.exit(f'HATA: maskeleme kuralı eşleşmedi: {ad}')
        if ad:
            print(f'  maske {n:2d} × {ad}')
    return html


def csp_ekle(html):
    # Satır içi iki çalışan betik (importmap + modül) için SHA-256 özetli CSP; veri betiği (application/json) çalışmaz.
    betikler = re.findall(r'<script type="(importmap|module)">(.*?)</script>', html, flags=re.S)
    if len(betikler) != 2:
        sys.exit(f'HATA: 2 satır içi betik bekleniyordu, {len(betikler)} bulundu')
    ozet = ' '.join("'sha256-%s'" % base64.b64encode(hashlib.sha256(g.encode()).digest()).decode() for _, g in betikler)
    csp = ("default-src 'none'; script-src 'self' %s; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
           "font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'" % ozet)
    return html.replace('__CSP__', f'<meta http-equiv="Content-Security-Policy" content="{csp}">')


def denetle(metin, ad):
    k = metin.lower()
    kalan = [y for y in YASAK if y in k]
    if kalan:
        for y in kalan:
            i = k.index(y)
            print(f'  YASAK "{y}" {ad}: …{metin[max(0, i - 60):i + 60]!r}…')
        sys.exit('HATA: herkese açık pakette iç not ya da dış bağlantı kaldı')
    if TELEFON.search(metin):
        sys.exit(f'HATA: {ad} içinde telefona benzeyen dizi var')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--npm', required=True, help='npm pack ile açılmış paketlerin klasörü')
    a = ap.parse_args()
    npm = os.path.abspath(a.npm)
    if os.path.exists(PAKET):
        shutil.rmtree(PAKET)
    os.makedirs(PAKET)

    # 1 · HTML (uret.py ile aynı birleştirme; data.json'daki kaynak alanı kısaltılır)
    d = json.load(open(os.path.join(REHBER, 'data.json'), encoding='utf-8'))
    d['kaynak'] = f'{PROJE} 60 m² montaj paftası'

    def ic_alan_at(x):   # sayfanın kullanmadığı iç alanlar (ör. teyitli_olculer) pakete girmez
        if isinstance(x, dict):
            return {k: ic_alan_at(v) for k, v in x.items() if k not in ('teyitli_olculer',)}
        if isinstance(x, list):
            return [ic_alan_at(v) for v in x]
        return x
    d = ic_alan_at(d)
    veri = json.dumps(d, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    html = open(os.path.join(REHBER, 'template.html'), encoding='utf-8').read()
    html = html.replace('__DATA__', veri).replace('__PROJE__', PROJE)
    print('index.html maskeleme:')
    html = csp_ekle(maskele(html))
    # Şablon artefakt parçasıdır (doctype/head yok): tam belgeye sarılır, yoksa tarayıcı tuhaf kipte (quirks) açar.
    bas = html.index('</style>') + len('</style>')
    html = ('<!doctype html>\n<html lang="tr">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + html[:bas] + '\n</head>\n<body>\n' + html[bas:].lstrip('\n') + '</body>\n</html>\n')
    denetle(html, 'index.html')
    open(os.path.join(PAKET, 'index.html'), 'w', encoding='utf-8').write(html)

    # 2 · görseller (pafta görseli örtülerek, ötekiler bayt bayt)
    for kay in sorted(glob.glob(os.path.join(REHBER, 'gorsel', '**', '*.jpg'), recursive=True)):
        rel = os.path.relpath(kay, REHBER)
        denetle(rel, 'görsel adı')
        hedef = os.path.join(PAKET, rel)
        os.makedirs(os.path.dirname(hedef), exist_ok=True)
        if os.path.basename(kay) == 'ev_render_pafta.jpg':
            im = Image.open(kay).convert('RGB')
            if im.size != (2000, 2808):
                sys.exit(f'HATA: pafta görseli boyutu değişmiş {im.size}; örtü konumlarını yeniden ölç')
            dr = ImageDraw.Draw(im)
            for kutu in PAFTA_ORTU:
                dr.rectangle(kutu, fill=ZEMIN)
            im.save(hedef, 'JPEG', quality=88, optimize=True, progressive=True)
            print('  pafta görseli: 2 ibare örtüldü')
        else:
            shutil.copyfile(kay, hedef)
    for rel in re.findall(r"'(gorsel/[^']+\.jpg)'", html):
        if not os.path.exists(os.path.join(PAKET, rel)):
            sys.exit(f'HATA: sayfanın istediği görsel pakette yok: {rel}')

    # 3 · Three.js 0.160.0 (yerel) ve yazı tipleri (latin + latin-ext; Türkçe harfler latin-ext'te)
    three = os.path.join(npm, 'three-0.160.0', 'package')
    os.makedirs(os.path.join(PAKET, 'js', 'addons', 'controls'))
    shutil.copyfile(os.path.join(three, 'build', 'three.module.js'), os.path.join(PAKET, 'js', 'three.module.js'))
    shutil.copyfile(os.path.join(three, 'examples', 'jsm', 'controls', 'OrbitControls.js'),
                    os.path.join(PAKET, 'js', 'addons', 'controls', 'OrbitControls.js'))
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
            kaynak_css = open(os.path.join(kok, f'{w}.css'), encoding='utf-8').read()
            for blok in re.findall(r'/\* [^*]+ \*/\s*@font-face \{.*?\}', kaynak_css, flags=re.S):
                alt = re.search(r'/\* (\S+) \*/', blok).group(1)
                if not (alt.endswith(f'-latin-{w}-normal') or alt.endswith(f'-latin-ext-{w}-normal')):
                    continue
                dosya = f'{alt}.woff2'
                shutil.copyfile(os.path.join(kok, 'files', dosya), os.path.join(PAKET, 'yazi', dosya))
                blok = re.sub(r'src: [^;]+;', f"src: url(./{dosya}) format('woff2');", blok)
                css.append(blok)
    open(os.path.join(PAKET, 'yazi', 'yazi.css'), 'w', encoding='utf-8').write('\n\n'.join(css) + '\n')
    print(f'  yazı tipi yüzü: {len(css)}')
    open(os.path.join(PAKET, 'robots.txt'), 'w').write('User-agent: *\nDisallow: /\n')

    # 4 · SHA256SUMS ve belirlenimci tar
    dosyalar = sorted(os.path.relpath(p, PAKET) for p in glob.glob(os.path.join(PAKET, '**', '*'), recursive=True)
                      if os.path.isfile(p))
    satirlar = [f'{sha(open(os.path.join(PAKET, r), "rb").read())}  {r}' for r in dosyalar]
    open(os.path.join(PAKET, 'SHA256SUMS'), 'w').write('\n'.join(satirlar) + '\n')
    tgz = os.path.join(CIKTI, 'rehber_paket.tgz')
    tampon = io.BytesIO()
    with tarfile.open(fileobj=tampon, mode='w', format=tarfile.PAX_FORMAT) as t:
        for r in dosyalar + ['SHA256SUMS']:
            ti = t.gettarinfo(os.path.join(PAKET, r), arcname=r)
            ti.mtime, ti.uid, ti.gid, ti.uname, ti.gname, ti.mode = 1761350400, 0, 0, 'root', 'root', 0o644
            t.addfile(ti, open(os.path.join(PAKET, r), 'rb'))
    import gzip
    with open(tgz, 'wb') as f:
        f.write(gzip.compress(tampon.getvalue(), mtime=0))
    boyut = sum(os.path.getsize(os.path.join(PAKET, r)) for r in dosyalar)
    paket_ozet = sha(open(tgz, 'rb').read())
    print(f'paket: {len(dosyalar)} dosya, {boyut / 1e6:.2f} MB; tgz {os.path.getsize(tgz) / 1e6:.2f} MB; sha256 {paket_ozet}')

    # 5 · tek dosya kurulum betiği: vps/rehber_yayin.sh + gömülü paket
    betik = open(os.path.join(DEPO, 'vps', 'rehber_yayin.sh'), encoding='utf-8').read()
    if '# __PAKET_YERI__' not in betik:
        sys.exit('HATA: vps/rehber_yayin.sh içinde "# __PAKET_YERI__" işareti yok')
    b64 = base64.encodebytes(open(tgz, 'rb').read()).decode()
    gomulu = ("PAKET_SHA256='%s'\npaket_yaz() {\n  base64 -d > \"$1\" <<'__PAKET_SONU__'\n%s__PAKET_SONU__\n}"
              % (paket_ozet, b64))
    kur = os.path.join(CIKTI, 'rehber_kur.sh')
    open(kur, 'w', encoding='utf-8').write(betik.replace('# __PAKET_YERI__', gomulu, 1))
    print(f'kurulum betiği: {kur} ({os.path.getsize(kur) / 1e6:.2f} MB)')


if __name__ == '__main__':
    main()
