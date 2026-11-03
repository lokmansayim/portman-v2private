"""Herkese açık rehber sitesinin ortak parçaları (kart 104, 4.11.2026).

Yerel Three.js 0.160.0 ve yazı tipleri, satır içi betiklerin CSP özetleri, son kapı taraması (YASAK, telefon),
belirlenimci tgz ve vps/rehber_yayin.sh'ye gömülü tek dosya kurulum betiği. Gereken npm paketleri `npm pack` ile
açılmış olarak --npm klasöründe: three-0.160.0, fontsource-barlow-condensed-*, fontsource-ibm-plex-mono-*,
fontsource-source-sans-3-*.
"""
import base64, glob, gzip, hashlib, io, os, re, shutil, sys, tarfile

DEPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
FONTLAR = [('barlow-condensed', ['500', '600', '700']), ('ibm-plex-mono', ['400', '500']), ('source-sans-3', ['400', '600'])]
YASAK = ['lokman', 'teyit', 'paftada yok', '.bde', 'alpha mini', 'lytecad', 'sketchup', 'dwg', 'ums metal', 'assan',
         'varsayım', 'varsayıl', 'tedarik', 'portman', 'astra', 'ubeyd', 'tatar', 'patron', '["kaynak"', "['kaynak'",
         'kaynak:', 'motor', 'kart modeli', 'modelinde', 'liste de böyle', 'kitap', 'pk-01', 'tk-01', 'tk01', 'pm-tk', 'iş emri', '__proje__', '__kisa__', '__data__',
         '__script__', '__gorseller__', '__chip__', '__spec__', '__note__', 'jsdelivr', 'googleapis', 'gstatic',
         'http://', 'https://']
TELEFON = re.compile(r'(?<![\d.,])(?:\+?90[ -]?)?0?5\d{2}[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}(?![\d.,])')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def denetle(metin, ad, yasak=YASAK):
    k = metin.lower()
    kalan = [y for y in yasak if y in k]
    for y in kalan:
        for m in list(re.finditer(re.escape(y), k))[:3]:
            print(f'  YASAK "{y}" {ad}: …{metin[max(0, m.start() - 80):m.start() + 80]!r}…')
    if kalan:
        sys.exit(f'HATA: {ad}: herkese açık pakette iç not ya da dış bağlantı kaldı')
    if TELEFON.search(metin):
        sys.exit(f'HATA: {ad} içinde telefona benzeyen dizi var')


def belge_ve_csp(html, betik_sayisi):
    """Artefakt parçasını tam belgeye sarar, satır içi çalışan betiklerin SHA-256 özetleriyle CSP yazar (__CSP__ yerine)."""
    if not html.lstrip().lower().startswith('<!doctype'):
        bas = html.index('</style>') + len('</style>')
        html = ('<!doctype html>\n<html lang="tr">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                + html[:bas] + '\n</head>\n<body>\n' + html[bas:].lstrip('\n') + '</body>\n</html>\n')
    betikler = re.findall(r'<script type="(importmap|module)">(.*?)</script>', html, flags=re.S)
    if len(betikler) != betik_sayisi:
        sys.exit(f'HATA: {betik_sayisi} satır içi betik bekleniyordu, {len(betikler)} bulundu')
    ozet = ' '.join("'sha256-%s'" % base64.b64encode(hashlib.sha256(g.encode()).digest()).decode() for _, g in betikler)
    csp = ("default-src 'none'; script-src 'self' %s; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
           "font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'" % ozet)
    return html.replace('__CSP__', f'<meta http-equiv="Content-Security-Policy" content="{csp}">')


def bas_etiketleri(baslik):
    return (f'<title>{baslik}</title>\n<meta name="robots" content="noindex, nofollow">\n'
            '<meta name="referrer" content="no-referrer">\n__CSP__')


def yerel_kutuphaneler(html, paket, npm):
    """three.module.js + sayfanın içe aktardığı addon'lar (js/) ve yazı tipleri (yazi/) pakete."""
    three = os.path.join(npm, 'three-0.160.0', 'package')
    os.makedirs(os.path.join(paket, 'js'), exist_ok=True)
    shutil.copyfile(os.path.join(three, 'build', 'three.module.js'), os.path.join(paket, 'js', 'three.module.js'))
    addon = sorted(set(re.findall(r"from\s*['\"]three/addons/([^'\"]+)['\"]", html)))
    if not addon:
        sys.exit('HATA: sayfa hiçbir three/addons modülü içe aktarmıyor (desen?)')
    for imp in addon:
        hedef = os.path.join(paket, 'js', 'addons', imp)
        os.makedirs(os.path.dirname(hedef), exist_ok=True)
        shutil.copyfile(os.path.join(three, 'examples', 'jsm', imp), hedef)
    shutil.copyfile(os.path.join(three, 'LICENSE'), os.path.join(paket, 'js', 'LICENSE-three.txt'))
    os.makedirs(os.path.join(paket, 'yazi'), exist_ok=True)
    css = []
    for ad, agirliklar in FONTLAR:
        kok = glob.glob(os.path.join(npm, f'fontsource-{ad}-*', 'package'))
        if len(kok) != 1:
            sys.exit(f'HATA: {ad} yazı tipi paketi bulunamadı')
        kok = kok[0]
        shutil.copyfile(os.path.join(kok, 'LICENSE'), os.path.join(paket, 'yazi', f'OFL-{ad}.txt'))
        for w in agirliklar:
            for blok in re.findall(r'/\* [^*]+ \*/\s*@font-face \{.*?\}', open(os.path.join(kok, f'{w}.css'), encoding='utf-8').read(), flags=re.S):
                alt = re.search(r'/\* (\S+) \*/', blok).group(1)
                if alt.endswith(f'-latin-{w}-normal') or alt.endswith(f'-latin-ext-{w}-normal'):
                    shutil.copyfile(os.path.join(kok, 'files', f'{alt}.woff2'), os.path.join(paket, 'yazi', f'{alt}.woff2'))
                    css.append(re.sub(r'src: [^;]+;', f"src: url(./{alt}.woff2) format('woff2');", blok))
    open(os.path.join(paket, 'yazi', 'yazi.css'), 'w', encoding='utf-8').write('\n\n'.join(css) + '\n')
    return addon


def paketle_ve_kur(kok, cikti, mtime):
    """kok/ altındaki her dosya → SHA256SUMS, belirlenimci tgz, rehber_kur.sh. (özet, kurulum yolu) döner."""
    dosyalar = sorted(os.path.relpath(p, kok) for p in glob.glob(os.path.join(kok, '**', '*'), recursive=True)
                      if os.path.isfile(p) and os.path.basename(p) != 'SHA256SUMS')
    open(os.path.join(kok, 'SHA256SUMS'), 'w').write(''.join(f'{sha(open(os.path.join(kok, r), "rb").read())}  {r}\n' for r in dosyalar))
    tampon = io.BytesIO()
    with tarfile.open(fileobj=tampon, mode='w', format=tarfile.PAX_FORMAT) as t:
        for r in dosyalar + ['SHA256SUMS']:
            ti = t.gettarinfo(os.path.join(kok, r), arcname=r)
            ti.mtime, ti.uid, ti.gid, ti.uname, ti.gname, ti.mode = mtime, 0, 0, 'root', 'root', 0o644
            t.addfile(ti, open(os.path.join(kok, r), 'rb'))
    tgz = os.path.join(cikti, 'rehber_paket.tgz')
    open(tgz, 'wb').write(gzip.compress(tampon.getvalue(), mtime=0))
    ozet = sha(open(tgz, 'rb').read())
    boyut = sum(os.path.getsize(os.path.join(kok, r)) for r in dosyalar)
    print(f'paket: {len(dosyalar)} dosya, {boyut / 1e6:.2f} MB; tgz {os.path.getsize(tgz) / 1e6:.2f} MB; sha256 {ozet}')
    betik = open(os.path.join(DEPO, 'vps', 'rehber_yayin.sh'), encoding='utf-8').read()
    if '# __PAKET_YERI__' not in betik:
        sys.exit('HATA: vps/rehber_yayin.sh içinde "# __PAKET_YERI__" yok')
    gomulu = ("PAKET_SHA256='%s'\npaket_yaz() {\n  base64 -d > \"$1\" <<'__PAKET_SONU__'\n%s__PAKET_SONU__\n}"
              % (ozet, base64.encodebytes(open(tgz, 'rb').read()).decode()))
    kur = os.path.join(cikti, 'rehber_kur.sh')
    open(kur, 'w', encoding='utf-8').write(betik.replace('# __PAKET_YERI__', gomulu, 1))
    print(f'kurulum betiği: {kur} ({os.path.getsize(kur) / 1e6:.2f} MB)')
    return ozet, kur
