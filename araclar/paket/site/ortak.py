"""Herkese açık rehber sitesinin ortak parçaları (kart 104, 4.11.2026; İE-41'de main'e taşındı).

Yerel three.js 0.160.0 ve yazı tipleri, satır içi betiklerin CSP özetleri, son kapı taraması (YASAK, telefon),
belirlenimci tgz ve `vps/rehber_yayin.sh`'ye gömülü tek dosya kurulum betiği. Gereken npm paketleri `npm pack` ile
açılmış olarak --npm klasöründe: three-0.160.0, fontsource-barlow-condensed-*, fontsource-ibm-plex-mono-*,
fontsource-source-sans-3-*. Canlıdaki sitenin yazı tipleri fontsource 5.1.0'dandır (üç paket de; 17 Kasım 2026'da bayt bayt
denetlendi); başka sürüm yazi.css'i ve OFL metnini değiştirir.
"""
from __future__ import annotations

import base64
import glob
import gzip
import hashlib
import io
import os
import posixpath
import re
import shutil
import tarfile
from pathlib import Path

DEPO = Path(__file__).resolve().parents[3]
FONTLAR = [('barlow-condensed', ['500', '600', '700']), ('ibm-plex-mono', ['400', '500']), ('source-sans-3', ['400', '600'])]
YASAK = ['lokman', 'teyit', 'paftada yok', '.bde', 'alpha mini', 'lytecad', 'sketchup', 'dwg', 'ums metal', 'assan',
         'varsayım', 'varsayıl', 'tedarik', 'portman', 'astra', 'ubeyd', 'tatar', 'patron', '["kaynak"', "['kaynak'",
         'kaynak:', 'motor', 'kart modeli', 'modelinde', 'liste de böyle', 'kitap', 'pk-0', 'tk-0', 'tk-1', '(d-3', '(d-2',
         '(d-4', '(d-5', '(d-6', '(d-7', '(d-8', '(d-9', 'ie-1', 'İe-1', 'ie-2', 'ie-3', 'ie-4', 'tk0', 'pm-tk', 'iş emri',
         'köşebent', '__proje__', '__kisa__', '__data__', '__script__', '__gorseller__', '__kagit__', '__chip__', '__spec__',
         '__note__', 'jsdelivr', 'googleapis', 'gstatic', 'http://', 'https://']
TELEFON = re.compile(r'(?<![\d.,])(?:\+?90[ -]?)?0?5\d{2}[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}(?![\d.,])')


class SiteHatasi(RuntimeError):
    """Paket üretilmez: iç not, dış bağlantı, eşleşmeyen kural ya da eksik girdi."""


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def bulgular(metin: str, yasak: list[str] = YASAK) -> list[str]:
    """Herkese açık metinde kalan yasak dizgeler (bağlamıyla) ve telefona benzeyen diziler."""
    k = metin.lower()
    out = []
    for y in yasak:
        for m in list(re.finditer(re.escape(y), k))[:3]:
            out.append(f'"{y}": …{metin[max(0, m.start() - 80):m.start() + 80]!r}…')
    for m in list(TELEFON.finditer(metin))[:3]:
        out.append(f'telefona benzeyen dizi: {m.group(0)!r}')
    return out


def denetle(metin: str, ad: str, yasak: list[str] = YASAK) -> None:
    b = bulgular(metin, yasak)
    if b:
        raise SiteHatasi(f'{ad}: herkese açık pakette iç not ya da dış bağlantı kaldı:\n  ' + '\n  '.join(b[:12]))


def belge_ve_csp(html: str, betik_sayisi: int) -> str:
    """Artefakt parçasını tam belgeye sarar, satır içi çalışan betiklerin SHA-256 özetleriyle CSP yazar (__CSP__ yerine)."""
    if not html.lstrip().lower().startswith('<!doctype'):
        bas = html.index('</style>') + len('</style>')
        html = ('<!doctype html>\n<html lang="tr">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                + html[:bas] + '\n</head>\n<body>\n' + html[bas:].lstrip('\n') + '</body>\n</html>\n')
    betikler = re.findall(r'<script type="(importmap|module)">(.*?)</script>', html, flags=re.S)
    if len(betikler) != betik_sayisi:
        raise SiteHatasi(f'{betik_sayisi} satır içi betik bekleniyordu, {len(betikler)} bulundu')
    ozet = ' '.join("'sha256-%s'" % base64.b64encode(hashlib.sha256(g.encode()).digest()).decode() for _, g in betikler)
    csp = ("default-src 'none'; script-src 'self' %s; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
           "font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'" % ozet)
    return html.replace('__CSP__', f'<meta http-equiv="Content-Security-Policy" content="{csp}">')


def bas_etiketleri(baslik: str) -> str:
    return (f'<title>{baslik}</title>\n<meta name="robots" content="noindex, nofollow">\n'
            '<meta name="referrer" content="no-referrer">\n__CSP__')


def npm_klasoru(npm: Path, ad: str) -> Path:
    kok = glob.glob(os.path.join(npm, f'{ad}-*', 'package')) or glob.glob(os.path.join(npm, ad, 'package'))
    if len(kok) != 1:
        raise SiteHatasi(f'{ad} paketi --npm klasöründe bulunamadı ({npm})')
    return Path(kok[0])


def yerel_kutuphaneler(html: str, paket: Path, npm: Path) -> list[str]:
    """three.module.js + sayfanın içe aktardığı addon'lar (js/) ve yazı tipleri (yazi/) pakete."""
    three = npm_klasoru(npm, 'three-0.160.0') if glob.glob(os.path.join(npm, 'three-0.160.0*')) else npm_klasoru(npm, 'three')
    (paket / 'js').mkdir(parents=True, exist_ok=True)
    shutil.copyfile(three / 'build' / 'three.module.js', paket / 'js' / 'three.module.js')
    addon = sorted(set(re.findall(r"from\s*['\"]three/addons/([^'\"]+)['\"]", html)))
    if not addon:
        raise SiteHatasi('sayfa hiçbir three/addons modülü içe aktarmıyor (desen?)')
    kuyruk, kopya = list(addon), set()
    while kuyruk:   # addon'un göreli içe aktardığı dosyalar da (İE-45: GLTFLoader → ../utils/BufferGeometryUtils.js)
        imp = kuyruk.pop(0)
        if imp in kopya:
            continue
        kopya.add(imp)
        hedef = paket / 'js' / 'addons' / imp
        hedef.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(three / 'examples' / 'jsm' / imp, hedef)
        for g in re.findall(r"(?:from|import)\s*['\"](\.{1,2}/[^'\"]+)['\"]", hedef.read_text(encoding='utf-8')):
            kuyruk.append(posixpath.normpath(posixpath.join(posixpath.dirname(imp), g)))
    shutil.copyfile(three / 'LICENSE', paket / 'js' / 'LICENSE-three.txt')
    (paket / 'yazi').mkdir(parents=True, exist_ok=True)
    css = []
    for ad, agirliklar in FONTLAR:
        kok = npm_klasoru(npm, f'fontsource-{ad}')
        shutil.copyfile(kok / 'LICENSE', paket / 'yazi' / f'OFL-{ad}.txt')
        for w in agirliklar:
            for blok in re.findall(r'/\* [^*]+ \*/\s*@font-face \{.*?\}', (kok / f'{w}.css').read_text(encoding='utf-8'), flags=re.S):
                alt = re.search(r'/\* (\S+) \*/', blok).group(1)
                if alt.endswith(f'-latin-{w}-normal') or alt.endswith(f'-latin-ext-{w}-normal'):
                    shutil.copyfile(kok / 'files' / f'{alt}.woff2', paket / 'yazi' / f'{alt}.woff2')
                    css.append(re.sub(r'src: [^;]+;', f"src: url(./{alt}.woff2) format('woff2');", blok))
    (paket / 'yazi' / 'yazi.css').write_text('\n\n'.join(css) + '\n', encoding='utf-8')
    return sorted(kopya)


def paketle_ve_kur(kok: Path, cikti: Path, mtime: int) -> tuple[str, Path]:
    """kok/ altındaki her dosya → SHA256SUMS, belirlenimci tgz, rehber_kur.sh. (özet, kurulum yolu) döner."""
    dosyalar = sorted(os.path.relpath(p, kok) for p in glob.glob(os.path.join(kok, '**', '*'), recursive=True)
                      if os.path.isfile(p) and os.path.basename(p) != 'SHA256SUMS')
    (kok / 'SHA256SUMS').write_text(''.join(f'{sha((kok / r).read_bytes())}  {r}\n' for r in dosyalar))
    tampon = io.BytesIO()
    with tarfile.open(fileobj=tampon, mode='w', format=tarfile.PAX_FORMAT) as t:
        for r in dosyalar + ['SHA256SUMS']:
            ti = t.gettarinfo(str(kok / r), arcname=r)
            ti.mtime, ti.uid, ti.gid, ti.uname, ti.gname, ti.mode = mtime, 0, 0, 'root', 'root', 0o644
            with open(kok / r, 'rb') as f:
                t.addfile(ti, f)
    tgz = cikti / 'rehber_paket.tgz'
    tgz.write_bytes(gzip.compress(tampon.getvalue(), mtime=0))
    ozet = sha(tgz.read_bytes())
    boyut = sum(os.path.getsize(kok / r) for r in dosyalar)
    print(f'paket: {len(dosyalar)} dosya, {boyut / 1e6:.2f} MB; tgz {tgz.stat().st_size / 1e6:.2f} MB; sha256 {ozet}')
    betik = (DEPO / 'vps' / 'rehber_yayin.sh').read_text(encoding='utf-8')
    if '# __PAKET_YERI__' not in betik:
        raise SiteHatasi('vps/rehber_yayin.sh içinde "# __PAKET_YERI__" yok')
    gomulu = ("PAKET_SHA256='%s'\npaket_yaz() {\n  base64 -d > \"$1\" <<'__PAKET_SONU__'\n%s__PAKET_SONU__\n}"
              % (ozet, base64.encodebytes(tgz.read_bytes()).decode()))
    kur = cikti / 'rehber_kur.sh'
    kur.write_text(betik.replace('# __PAKET_YERI__', gomulu, 1), encoding='utf-8')
    print(f'kurulum betiği: {kur} ({kur.stat().st_size / 1e6:.2f} MB)')
    return ozet, kur


def onceki_paket(yol: Path, beklenen_sha: str) -> dict[str, bytes]:
    """Daha önce kurulmuş paketin dosyaları {yol: bayt}. `yol` ya `rehber_kur.sh` (gömülü paket) ya da `rehber_paket.tgz`.
    Paketin sha256'sı `beklenen_sha` değilse durur: sabit rehber yalnız kayıttaki pakettan alınır."""
    ham = Path(yol).read_bytes()
    if b"<<'__PAKET_SONU__'" in ham:
        m = re.search(rb"<<'__PAKET_SONU__'\n(.*?)^__PAKET_SONU__$", ham, flags=re.S | re.M)
        if not m:
            raise SiteHatasi(f'{yol}: gömülü paket okunamadı')
        ham = base64.b64decode(m.group(1))
    if sha(ham) != beklenen_sha:
        raise SiteHatasi(f'{yol}: paket sha256 {sha(ham)}; kayıttaki {beklenen_sha} değil')
    dosyalar = {}
    with tarfile.open(fileobj=io.BytesIO(ham), mode='r:gz') as t:
        for ti in t.getmembers():
            if ti.isfile():
                dosyalar[ti.name] = t.extractfile(ti).read()
    return dosyalar
