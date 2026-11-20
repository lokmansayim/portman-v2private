"""İE-41 · main'in montaj rehberi sayfası → sitenin rehber klasörü (index.html, gorsel/, js/, yazi/).

İlk hâli `claude/montaj-rehberi-devir` dalında `deneme/2026-11-04_rehber_sitesi/rehber80/paketle.py` (kart 104, 4 Kasım 2026; Lokman'ın
kararları: başlıkta kod görünmez, alan ve oda sayısı görünür; ön onay paftasının "PORTMAN | Bayi … | İş Emri …" satırı örtülür).
Sahne aynı kalır: üç boyutlu model, adımlar, kartların satırları ve sayılar main'in sayfasındaki gibidir; yalnız iç notlar çıkar.

Temizlik üç katta:
  1. veri (JSON): iç kaynak alanları atılır; değerlerde iç not taşıyan parantezler, cümleler ve maddeler çıkar; karar kodları silinir;
  2. modül betiği: esbuild ile yorumsuz (yalnız boşluk ve yorum gider), sonra kartların "Kaynak" satırları ve "(Lokman …)" parantezleri;
  3. son kapı: `ortak.YASAK` taraması. Bu taramadan geçmeyen sayfa pakete girmez (`ortak.SiteHatasi`).
"""
from __future__ import annotations

import base64
import io
import json
import re
import subprocess
from pathlib import Path

from . import ortak

PAFTA_BOYU = (2481, 3508)                 # ön onay sayfasının görseli (A4, 300 dpi; `rehber/kagit.py`)
PAFTA_ORTU = (600, 98, 1880, 142)         # bu görselde "PORTMAN | Bayi … | İş Emri …" satırı (ölçüldü: y 106–134); beyazla örtülür
IC_TABAN = (r"varsayı|motor|lokman|patron|portman|pk-\d\d|ap-\d\d|tk-\d\d|kitab|kitap|montaj rehberi|kural|modelinde|"
            r"model(?:den|inden)\b|teyit|sketchup|alpha mini|`|paftası yok|deneme|kart modeli|liste de böyle|iş emri")
ON_DEGISIM = [   # cümle düşürmeden önce anlamı koruyan kısa değişimler ({kod}: bu evin kodu; başka evin kodu iç nottur)
    (r'motorun kart modeli:\s*', ''), (r'motorun (?:kimlik kartlı )?planından', 'paftadan'),
    (r'{kod} prefabrik', '{ad} prefabrik konut'), (r'\b{kod}\b', '{ad}'),
    (r',\s*kitabın aralığıyla', ''),
    (r'Veranda çatılarında da sıralar kart modelinden, aynı kuralla\.', 'Veranda çatılarında da sıralar aynı düzende.'),
]
ATILAN_ANAHTAR = {'kaynak', 'makas_kaynak', 'dvr_kaynak'}
TEKRAR = re.compile(r'\bprefabrik prefabrik\b')   # 62 m² verisi: "__PROJE__ prefabrik konut", proje adı "62 m² prefabrik" (hedef örnek)
KARAR = re.compile(r'\s?\((?:(?:D|İE|BK|PC|M)-\d{2}[;,]?\s*)+\)|(?<=\()(?:D|İE|BK|PC|M)-\d{2}[;,]\s*|[;,]\s*(?:D|İE|BK|PC|M)-\d{2}(?=\))')
S = r'''(?:"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`)'''
JS_DEGISIM = [   # esbuild çıktısında (çift tırnak, boşluksuz): (desen, yerine, ad)
    (r',\s*\[\s*"Kaynak"\s*,\s*' + S + r'\s*\]', '', 'Kaynak satırı (sabit)'),
    (r',\s*\[\s*"Kaynak"\s*,\s*[A-Za-z_$][\w$.]*(?:\s*\|\|\s*[A-Za-z_$][\w$.]*)?\s*\]', '', 'Kaynak satırı (veriden)'),
    (r',\s*\.\.\.\w+\?\[\[\s*"Kaynak"\s*,\s*\w+(?:\.\w+)*\?' + S + r':' + S + r'\]\]:\[\]', '', 'Kaynak satırı (koşullu)'),
    (r'\((?:Lokman|Lokman’ın|Lokman\'ın)[^;()`"]*;\s*', '(', 'Lokman; … parantez başı'),
    (r' cm varsayım\)', ' cm, yaklaşık)', 'U dudağı varsayım'),
    (r'\s?\([^()`"]*Lokman[^()`"]*\)', '', 'Lokman geçen parantezler'),
    (r' \(kart modelinde bu kenarın Z’si .*?; liste de böyle sayar\)', '', 'Z kenarı: kart modeli açıklaması'),
    (r'\["Kural",`\$\{[^`]*`\]', '["Tavan",`${a.ad.toLocaleLowerCase("tr")} tavanı ters tavan, yeşil alçıpan`]', 'Kural satırı'),
]


def not_metni(r: dict) -> str:
    """Sayfanın alt notu (Lokman'ın 4 Kasım sayfalarındaki metin)."""
    return ' '.join(x for x in (
        f'Bu rehber {r["ad"]} montaj paftasından kurulan 3B modeldir.',
        'Parça yerleri paftadan, adetler yükleme listesindendir.',
        r.get('not_ek'),
        'Evin altında ön onay paftası gerçek ölçekte serilidir.' if r['pafta'] else None,
        'Ölçüler bilgi içindir; uygulamada paftadaki ölçüler esastır.') if x)


class Temizleyici:
    """Bir rehberin veri temizliği: iç not işaretleri ve evin kodu → görünen ad."""

    def __init__(self, kod: str | None, ad: str, altmis_iki: bool):
        self.kod, self.ad = kod, ad
        self.ic = re.compile(IC_TABAN + ('' if altmis_iki else r'|62 m²|62 m2'), re.I)

    def _parantez(self, m: re.Match) -> str:
        """İç not taşıyan parantez: iç notlu maddeler (;) düşer, kalan varsa parantez kalır."""
        ic = m.group(1)
        if not self.ic.search(ic):
            return m.group(0)
        kalan = [p for p in re.split(r';\s*', ic) if p and not self.ic.search(p)]
        bas = m.group(0)[:len(m.group(0)) - len(m.group(0).lstrip())]
        return f'{bas}({"; ".join(kalan)})' if kalan else ''

    def deger(self, s):
        if isinstance(s, str):
            s = TEKRAR.sub('prefabrik', KARAR.sub('', s))
        if not isinstance(s, str) or not self.ic.search(s):
            return s
        for d, y in ON_DEGISIM:
            if '{kod}' in d and not self.kod:
                continue
            s = re.sub(d.replace('{kod}', re.escape(self.kod or '')), y.replace('{ad}', self.ad), s)
        onceki = None
        while onceki != s:                                   # iç not taşıyan en içteki parantezler
            onceki = s
            s = re.sub(r'\s?\(([^()]*)\)', self._parantez, s)
        if self.ic.search(s):                                # cümle ve madde düzeyi
            s = ' '.join(c for c in re.split(r'(?<=[.!?])\s+', s) if not self.ic.search(c))
            if self.ic.search(s) or not s:
                s = '; '.join(p for p in re.split(r';\s*', s) if p and not self.ic.search(p))
        return re.sub(r'\s{2,}', ' ', s).strip()

    def veri(self, x):
        if isinstance(x, dict):
            return {k: self.veri(v) for k, v in x.items() if k not in ATILAN_ANAHTAR}
        if isinstance(x, list):
            return [self.veri(v) for v in x]
        return self.deger(x)


def pafta_ayir(html: str, beklenen: bool) -> tuple[str, bytes | None]:
    """Ön onay paftasının gömülü görseli → ayrı JPEG (üst satırı örtülü); sayfada yerine `gorsel/onay_pafta.jpg`."""
    from PIL import Image, ImageDraw
    m = list(re.finditer(r"data:image/jpeg;base64,([A-Za-z0-9+/=]+)", html))
    if len(m) != (1 if beklenen else 0):
        raise ortak.SiteHatasi(f'sayfada {len(m)} gömülü JPEG var, {1 if beklenen else 0} beklenirdi (ön onay paftası)')
    if not m:
        return html, None
    im = Image.open(io.BytesIO(base64.b64decode(m[0].group(1)))).convert('RGB')
    if im.size != PAFTA_BOYU:
        raise ortak.SiteHatasi(f'pafta görselinin boyu değişmiş {im.size}; örtünün yerini yeniden ölç')
    ImageDraw.Draw(im).rectangle(PAFTA_ORTU, fill=(255, 255, 255))
    b = io.BytesIO()
    im.save(b, 'JPEG', quality=88, optimize=True, progressive=True)
    return html[:m[0].start()] + 'gorsel/onay_pafta.jpg' + ortak.surum_eki(b.getvalue()) + html[m[0].end():], b.getvalue()


def _kucult(kod: str, esbuild: str) -> str:
    return subprocess.run([esbuild, '--loader=js', '--format=esm', '--target=es2022', '--charset=utf8', '--legal-comments=none',
                           '--minify-whitespace'], input=kod.encode(), capture_output=True, check=True).stdout.decode()


def sayfa(html: str, r: dict, esbuild: str | None) -> tuple[str, bytes | None, dict]:
    """main'in sayfası → (sitenin index.html'i, pafta JPEG'i ya da None, özet). `esbuild` yoksa (CI) betik katı atlanır ve
    yalnız veri ve kabuk denetlenir; site o hâliyle paketlenmez."""
    ozet: dict = {}
    html, pafta = pafta_ayir(html, r['pafta'])
    # 1 · veri
    v = re.search(r'(<script type="application/json" id="pafta">)(.*?)(</script>)', html, flags=re.S)
    ham = json.loads(v.group(2).replace('<\\/', '</'))
    t = Temizleyici(r.get('kod') or ham.get('kod'), r['ad'], altmis_iki=r['ad'].startswith('62 m²'))
    d = t.veri(ham)
    d['kod'] = r['ad']
    not_ = not_metni(r)
    d['kabuk'].update(proje=r['ad'], kisa=r['ad'], note=not_)
    veri = json.dumps(d, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    html = html[:v.start(2)] + veri + html[v.end(2):]
    ozet.update(adim=d['N'], spec=d['kabuk']['spec'], chip=d['kabuk']['chip'])
    # 2 · kabuk
    spec = ''.join(f'<span>{x}</span>' for x in d['kabuk']['spec'])
    kab = [(r'<title>[^<]*</title>', ortak.bas_etiketleri(f'PortatifEv Montaj Rehberi · {r["ad"]}'), 1),
           (r'<h1>[^<]*</h1>', f'<h1>{r["ad"]} · Montaj Rehberi</h1>', 1),
           (r'<span class="chip">[^<]*</span>', f'<span class="chip">{d["kabuk"]["chip"]}</span>', 1),
           (r'(<div class="spec">\s*).*?(\s*</div>)', lambda m_: m_.group(1) + spec + m_.group(2), 1),
           (r'<p class="note">.*?</p>', f'<p class="note">{not_}</p>', 1),
           (r'<meta name="claude:viewport-fit-sides"[^>]*>\n?', '', 1),
           (r'<link rel="preconnect"[^>]*>\n?', '', 2),
           (r'<link rel="stylesheet" href="https://fonts\.googleapis\.com[^>]*>', '<link rel="stylesheet" href="yazi/yazi.css">', 1),
           (r'"three": "https://cdn\.jsdelivr\.net/npm/three@0\.160\.0/build/three\.module\.js"', '"three": "./js/three.module.js"', 1),
           (r'"three/addons/": "https://cdn\.jsdelivr\.net/npm/three@0\.160\.0/examples/jsm/"', '"three/addons/": "./js/addons/"', 1)]
    for desen, yeni, en_az in kab:
        html, n = re.subn(desen, yeni if callable(yeni) else (lambda _m, y=yeni: y), html, count=0, flags=re.S)
        if n < en_az:
            raise ortak.SiteHatasi(f'{r["klasor"]}: kabuk kuralı eşleşmedi: {desen[:50]}')
    ortak.denetle(veri, f'{r["klasor"]} (veri)')
    if not esbuild:
        return html, pafta, ozet
    # 3 · modül betikleri yorumsuz, sonra iç not kuralları
    html = re.sub(r'<script type="module">(.*?)</script>', lambda m_: '<script type="module">\n' + _kucult(m_.group(1), esbuild) + '</script>',
                  html, flags=re.S)
    ozet['betik'] = {}
    for desen, yeni, ad in JS_DEGISIM:
        html, n = re.subn(desen, yeni, html, flags=re.S)
        ozet['betik'][ad] = n
    html = ortak.belge_ve_csp(html, 1 + len(re.findall(r'<script type="module">', html)))
    ortak.denetle(re.sub(r'<script type="application/json" id="pafta">.*?</script>', '', html, flags=re.S), f'{r["klasor"]} (sayfa)')
    return html, pafta, ozet


def klasor_yaz(html: str, pafta: bytes | None, hedef: Path, npm: Path) -> list[str]:
    (hedef / 'gorsel').mkdir(parents=True, exist_ok=True)
    if pafta:
        (hedef / 'gorsel' / 'onay_pafta.jpg').write_bytes(pafta)
    (hedef / 'index.html').write_text(html, encoding='utf-8')
    return ortak.yerel_kutuphaneler(html, hedef, npm)
