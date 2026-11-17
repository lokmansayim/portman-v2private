"""İE-41 · rehber.portatifev.com sitesini main'deki koddan kurar: python -m araclar.paket.site <çıktı> --npm <klasör> --esbuild <yol>

Sıra: (1) `rehberler.json`'daki her rehber main'in komutuyla üretilir (D-28); (2) `temizle.sayfa` iç notları çıkarır, kitaplıkları yerele
alır; (3) kapak görseli sayfanın kendisinden (`kapak.js`, genel bakış); (4) açılış sayfası; (5) `ortak.paketle_ve_kur`
belirlenimci tgz ve `rehber_kur.sh`'yi yazar. Çıktı: <çıktı>/site/, <çıktı>/sayfalar/ (main'in ham sayfaları, kıyas için),
<çıktı>/rehber_paket.tgz, <çıktı>/rehber_kur.sh, <çıktı>/ozet.json. Sunucuya koymak Lokman'ın ayrı onayıyla (canlı değişiklik).
'sabit' rehber (rehberler.json) yeniden yazılmaz: klasörü `sabit_paket`'teki canlı paketten bayt bayt gelir (--onceki <rehber_kur.sh>),
açılış kartı canlıdakiyle aynı olmalı. Yeni rehber eklenirken canlıdakiler değişmesin diye (Lokman, 15 Kasım 2026 22:19 UTC).
"""
from __future__ import annotations

import argparse
import html as H
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import ortak, temizle

KAYIT = Path(__file__).with_name('rehberler.json')


def kayit() -> dict:
    return json.loads(KAYIT.read_text(encoding='utf-8'))


def ham_sayfa(r: dict, gec: Path) -> Path:
    """Rehberin main'deki komutla üretilmiş sayfası."""
    gec.mkdir(parents=True, exist_ok=True)
    if r.get('veri'):
        from araclar.paket.rehber import sayfa
        return Path(sayfa.yaz(json.loads((ortak.DEPO / r['veri']).read_text(encoding='utf-8')), gec / f'{r["klasor"]}.html'))
    komut = [sys.executable, '-m', 'araclar.paket', r['kod'], str(gec), '--is-emri', r['is_emri']] + (['--tavan', r['tavan']] if r.get('tavan') else [])
    s = subprocess.run(komut, cwd=ortak.DEPO, capture_output=True, text=True)
    yol = gec / 'prefabrik' / r['kod'] / f'{r["kod"]}_montaj_rehberi.html'
    if s.returncode or not yol.exists():
        raise ortak.SiteHatasi(f'{r["klasor"]}: rehber üretilemedi ({" ".join(komut[2:])}): {(s.stdout + s.stderr)[-800:]}')
    return yol


def kapak_al(site: Path, klasor: str, hedef: Path) -> None:
    """Rehberin genel bakışından 3B sahnenin görüntüsü (`kapak.js`: Node Playwright, yazılım GPU'su), 16:10 orta kesit, 1280 × 800 JPEG."""
    from PIL import Image
    png = hedef.with_suffix('.png')
    s = subprocess.run(['node', str(Path(__file__).with_name('kapak.js')), str(site), klasor, str(png)], capture_output=True, text=True,
                       timeout=600)
    if s.returncode or not png.exists():
        raise ortak.SiteHatasi(f'{klasor}: kapak görseli alınamadı: {(s.stdout + s.stderr)[-800:]}')
    im = Image.open(png).convert('RGB')
    w, h = im.size
    hh = min(h, int(w * 10 / 16))
    im = im.crop((0, (h - hh) // 2, w, (h - hh) // 2 + hh)).resize((1280, 800), Image.LANCZOS)
    im.save(hedef, 'JPEG', quality=85, optimize=True, progressive=True)
    png.unlink()


ACILIS = """<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
__BAS__
<link rel="stylesheet" href="__YAZI__/yazi/yazi.css">
<style>
:root{--bg:#E8ECEF;--surface:#F7F9FA;--ink:#16222D;--muted:#5A6772;--line:#CDD5DB;--accent:#D98E04;--accent-ink:#7A4D00;--on-accent:#1E1400;
  --f-display:"Barlow Condensed","Arial Narrow",Arial,sans-serif;--f-body:"Source Sans 3",system-ui,-apple-system,"Segoe UI",sans-serif;
  --f-mono:"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,monospace}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--bg);color:var(--ink);font-family:var(--f-body);font-size:16px;line-height:1.5}
main{max-width:1040px;margin:0 auto;padding:32px 16px 48px}
.mark{font-family:var(--f-display);font-weight:700;font-size:15px;letter-spacing:.08em;text-transform:uppercase;color:var(--accent-ink)}
h1{font-family:var(--f-display);font-weight:600;font-size:clamp(30px,6vw,44px);line-height:1.05;margin:4px 0 10px}
.lead{color:var(--muted);max-width:60ch;margin:0 0 28px}
.liste{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}
a.kart{display:flex;flex-direction:column;background:var(--surface);border:1px solid var(--line);border-radius:14px;overflow:hidden;
  color:inherit;text-decoration:none;transition:border-color .15s,transform .15s}
a.kart:hover,a.kart:focus-visible{border-color:var(--accent);transform:translateY(-2px)}
a.kart:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.kart img{display:block;width:100%;aspect-ratio:16/10;object-fit:cover;background:#D8DFE4}
.ic{padding:16px 18px 18px;display:flex;flex-direction:column;gap:10px;flex:1}
.ic h2{font-family:var(--f-display);font-weight:600;font-size:26px;line-height:1.1;margin:0}
.alan{font-family:var(--f-mono);font-size:13px;color:var(--muted)}
.spec{display:flex;flex-wrap:wrap;gap:6px}
.spec span{font-family:var(--f-mono);font-size:12px;background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:3px 8px}
.ac{margin-top:auto;align-self:flex-start;font-family:var(--f-display);font-weight:600;font-size:17px;letter-spacing:.02em;
  background:var(--accent);color:var(--on-accent);border-radius:999px;padding:7px 18px}
.not{color:var(--muted);font-size:14px;margin-top:32px;max-width:70ch}
@media (prefers-reduced-motion: reduce){a.kart{transition:none}a.kart:hover{transform:none}}
</style>
</head>
<body>
<main>
  <div class="mark">PortatifEv</div>
  <h1>Montaj Rehberleri</h1>
  <p class="lead">Etkileşimli 3B montaj rehberleri: ev oda oda, adım adım kurulur; bir parçaya dokununca kimlik kartı açılır.</p>
  <div class="liste">
__KARTLAR__
  </div>
  <p class="not">Ölçüler bilgi içindir; uygulamada paftadaki ölçüler esastır.</p>
</main>
</body>
</html>
"""


def kart_ozellikleri(r: dict, oz: dict) -> list[str]:
    """Açılış kartındaki özellikler, sayfanın kendi özelliklerinden (ölçü, çatı, veranda) + adım sayısı + pafta."""
    sp = oz['spec']
    return [sp[0], sp[3], sp[5], f'{oz["adim"]} adım'] + (['ön onay paftası'] if r['pafta'] else [])


def acilis_sayfasi(rehberler: list[dict], ozet: dict) -> str:
    kartlar = [kart_html(r, ozet[r['klasor']]) for r in rehberler]
    s = (ACILIS.replace('__BAS__', ortak.bas_etiketleri('PortatifEv Montaj Rehberleri')).replace('__KARTLAR__', '\n'.join(kartlar))
         .replace('__YAZI__', rehberler[0]['klasor']))
    csp = "default-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self'; font-src 'self'; base-uri 'none'; form-action 'none'"
    s = s.replace('__CSP__', f'<meta http-equiv="Content-Security-Policy" content="{csp}">')
    ortak.denetle(s, 'açılış')
    return s


def kart_html(r: dict, oz: dict) -> str:
    return (f'    <a class="kart" href="{r["klasor"]}/">\n'
            f'      <img src="{r["klasor"]}/gorsel/kapak.jpg" alt="{H.escape(r["ad"])}: bitmiş evin görünümü" loading="lazy">\n'
            f'      <div class="ic"><h2>{H.escape(r["ad"])}</h2>\n'
            f'        <div class="alan">{H.escape(oz["chip"])}</div>\n'
            f'        <div class="spec">{"".join(f"<span>{H.escape(x)}</span>" for x in kart_ozellikleri(r, oz))}</div>\n'
            f'        <span class="ac">Rehberi aç</span></div>\n'
            f'    </a>')


def sabit_dosyalar(k: dict, onceki: Path | None) -> dict[str, bytes]:
    """'sabit' rehberlerin klasörü kayıttaki önceki paketten bayt bayt gelir (`sabit_paket`; canlıdaki sürüm)."""
    if not any(r.get('sabit') for r in k['rehberler']):
        return {}
    if onceki is None:
        raise ortak.SiteHatasi(f'sabit rehber var; --onceki <rehber_kur.sh> gerekir (paket {k["sabit_paket"]["sha256"]})')
    return ortak.onceki_paket(onceki, k['sabit_paket']['sha256'])


def kur(cikti: Path, npm: Path, esbuild: str, kapak: bool = True, onceki: Path | None = None) -> dict:
    k = kayit()
    eski = sabit_dosyalar(k, onceki)
    cikti = Path(cikti).resolve()
    site, sayfalar = cikti / 'site', cikti / 'sayfalar'
    for p in (site, sayfalar):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True)
    ozet = {}
    for r in k['rehberler']:
        print(f'== {r["klasor"]} ({r["ad"]})', flush=True)
        ham = ham_sayfa(r, cikti / 'gecici' / r['klasor'])
        shutil.copyfile(ham, sayfalar / f'{r["klasor"]}.html')
        html, pafta, oz = temizle.sayfa(ham.read_text(encoding='utf-8'), r, esbuild)
        if oz['adim'] != r['adim']:
            raise ortak.SiteHatasi(f'{r["klasor"]}: {r["adim"]} adım beklenirdi, sayfada {oz["adim"]}')
        oz['ham_sha256'] = ortak.sha(ham.read_bytes())
        if r.get('sabit'):
            on = f'{r["klasor"]}/'
            kopya = {p[len(on):]: b for p, b in eski.items() if p.startswith(on)}
            if 'index.html' not in kopya:
                raise ortak.SiteHatasi(f'{r["klasor"]}: önceki pakette bu rehber yok')
            for p, b in kopya.items():
                (site / r['klasor'] / p).parent.mkdir(parents=True, exist_ok=True)
                (site / r['klasor'] / p).write_bytes(b)
            if kart_html(r, oz) not in eski['index.html'].decode('utf-8'):
                raise ortak.SiteHatasi(f'{r["klasor"]}: açılış kartı canlıdakinden farklı; sabit rehberin kartı değişmez')
            oz['sabit'] = k['sabit_paket']['surum']
            ozet[r['klasor']] = oz
            print(f'   sabit: {len(kopya)} dosya önceki paketten ({k["sabit_paket"]["surum"]})', flush=True)
            continue
        oz['addon'] = temizle.klasor_yaz(html, pafta, site / r['klasor'], npm)
        if kapak:
            kapak_al(site, r['klasor'], site / r['klasor'] / 'gorsel' / 'kapak.jpg')
        ozet[r['klasor']] = oz
        print(f'   {oz["adim"]} adım · betik kuralları {oz["betik"]}', flush=True)
    shutil.rmtree(cikti / 'gecici')
    (site / 'index.html').write_text(acilis_sayfasi(k['rehberler'], ozet), encoding='utf-8')
    (site / 'robots.txt').write_text('User-agent: *\nDisallow: /\n')
    paket_sha, kur_yolu = ortak.paketle_ve_kur(site, cikti, mtime=k['mtime'])
    sonuc = {'paket_sha256': paket_sha, 'kurulum': str(kur_yolu), 'rehberler': ozet}
    (cikti / 'ozet.json').write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding='utf-8')
    return sonuc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog='python -m araclar.paket.site', description=__doc__.split('\n')[0])
    ap.add_argument('cikti', type=Path)
    ap.add_argument('--npm', type=Path, required=True, help='npm pack ile açılmış paketler: three-0.160.0, fontsource-*')
    ap.add_argument('--esbuild', required=True, help='esbuild çalıştırılabilir dosyası')
    ap.add_argument('--kapaksiz', action='store_true', help='kapak görseli alınmaz (yalnız deneme; açılış sayfası görselsiz kalır)')
    ap.add_argument('--onceki', type=Path, help="canlıdaki paketin rehber_kur.sh'si (ya da tgz'si); 'sabit' rehberler oradan bayt bayt")
    a = ap.parse_args(argv)
    if not os.access(a.esbuild, os.X_OK):
        ap.error(f'esbuild çalıştırılamıyor: {a.esbuild}')
    try:
        s = kur(a.cikti, a.npm, a.esbuild, kapak=not a.kapaksiz, onceki=a.onceki)
    except ortak.SiteHatasi as e:
        print(f'HATA: {e}', file=sys.stderr)
        return 1
    print(f'site: {a.cikti / "site"} · paket sha256 {s["paket_sha256"]}')
    return 0
