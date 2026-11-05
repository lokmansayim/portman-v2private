"""rehber.portatifev.com sitesi: açılış sayfası + her rehber kendi klasöründe (kart 104, 4.11.2026).

Lokman'ın kararı (4.11): iki rehber birlikte yayında, açılış sayfası ikisini listeler.
  /        açılış (PortatifEv montaj rehberleri)
  /62m2/   62 m² Beşik + Cumba (deneme/2026-10-25_rehber_62m2/yayin/paketle.py)
  /80m2/   80 m² 3+1, evin altında ön onay paftası (rehber80/paketle.py --rehber 80m2)
  /80m2-21/ 80 m² 2+1, aynı şablon (rehber80/paketle.py --rehber 80m2-21; Lokman 6.11)

Kullanım: python3 site.py --npm <npm pack klasörü> --esbuild <esbuild yolu>
Çıktı (cikti/, depoya girmez): site/, rehber_paket.tgz, rehber_kur.sh (vps/rehber_yayin.sh + gömülü site).
80 m²'nin kapak görseli sayfanın kendisinden alınır (Playwright, genel bakış): 80m2/gorsel/kapak.jpg.
"""
import argparse, functools, html, http.server, os, re, shutil, subprocess, sys, threading

B = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, B)
import ortak  # noqa: E402

CIKTI = os.path.join(B, 'cikti')
SITE = os.path.join(CIKTI, 'site')
R62 = os.path.join(ortak.DEPO, 'deneme', '2026-10-25_rehber_62m2', 'yayin')

REHBERLER = [   # klasör, başlık, özellikler, kapak
    ('62m2', '62 m² Beşik + Cumba', ['900 × 600 cm', 'beşik + cumba çatı', 'veranda', '20 adım'], 'gorsel/ev_on_sol.jpg'),
    ('80m2', '80 m² 3+1', ['898,5 × 888,5 cm', '3 yatak odası', '2 veranda', '22 adım', 'ön onay paftası'], 'gorsel/kapak.jpg'),
    ('80m2-21', '80 m² 2+1', ['888,5 × 898,5 cm', '2 yatak odası', 'çapraz cumba', 'gömme veranda', '21 adım', 'ön onay paftası'],
     'gorsel/kapak.jpg'),
]


def kapak_al(klasor, hedef):
    """Rehberin genel bakışından 3B sahnenin görüntüsü (yerel sunucu, yazılım GPU'su)."""
    from playwright.sync_api import sync_playwright

    class Sessiz(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Sessiz, directory=klasor))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        p = b.new_page(viewport={'width': 1400, 'height': 900}, device_scale_factor=1)
        p.goto(f'http://127.0.0.1:{srv.server_port}/', wait_until='networkidle', timeout=120000)
        p.wait_for_function('() => window.__montaj', timeout=60000)
        p.wait_for_timeout(4000)
        p.locator('#viewport canvas').screenshot(path=hedef + '.png')
        b.close()
    srv.shutdown()
    from PIL import Image
    im = Image.open(hedef + '.png').convert('RGB')
    w, h = im.size                                   # 16:10 orta kesit
    hh = min(h, int(w * 10 / 16))
    im = im.crop((0, (h - hh) // 2, w, (h - hh) // 2 + hh)).resize((1280, 800), Image.LANCZOS)
    im.save(hedef, 'JPEG', quality=85, optimize=True, progressive=True)
    os.remove(hedef + '.png')


ACILIS = """<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
__BAS__
<link rel="stylesheet" href="62m2/yazi/yazi.css">
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
.spec{display:flex;flex-wrap:wrap;gap:6px}
.spec span{font-family:var(--f-mono);font-size:12px;background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:3px 8px;white-space:nowrap}
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


def acilis_sayfasi():
    kartlar = []
    for kl, ad, spec, kapak in REHBERLER:
        kartlar.append(
            f'    <a class="kart" href="{kl}/">\n'
            f'      <img src="{kl}/{kapak}" alt="{html.escape(ad)}: bitmiş evin görünümü" loading="lazy">\n'
            f'      <div class="ic"><h2>{html.escape(ad)}</h2>\n'
            f'        <div class="spec">{"".join(f"<span>{html.escape(x)}</span>" for x in spec)}</div>\n'
            f'        <span class="ac">Rehberi aç</span></div>\n'
            f'    </a>')
    s = ACILIS.replace('__BAS__', ortak.bas_etiketleri('PortatifEv Montaj Rehberleri')).replace('__KARTLAR__', '\n'.join(kartlar))
    csp = ("default-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self'; font-src 'self'; "
           "base-uri 'none'; form-action 'none'")
    s = s.replace('__CSP__', f'<meta http-equiv="Content-Security-Policy" content="{csp}">')
    ortak.denetle(s, 'açılış')
    return s


def main():
    import argparse as _a
    ap = _a.ArgumentParser()
    ap.add_argument('--npm', required=True)
    ap.add_argument('--esbuild', required=True)
    a = ap.parse_args()
    if os.path.exists(SITE):
        shutil.rmtree(SITE)
    os.makedirs(SITE)
    print('== 62 m² paketi')
    subprocess.run([sys.executable, os.path.join(R62, 'paketle.py'), '--npm', a.npm, '--esbuild', a.esbuild], check=True)
    shutil.copytree(os.path.join(R62, 'cikti', 'paket'), os.path.join(SITE, '62m2'),
                    ignore=shutil.ignore_patterns('SHA256SUMS', 'robots.txt'))
    s62 = open(os.path.join(SITE, '62m2', 'index.html'), encoding='utf-8').read()
    ortak.denetle(re.sub(r'<script type="application/json" id="pafta">.*?</script>', '', s62, flags=re.S), '62m2 (betik)')
    ortak.denetle(re.search(r'id="pafta">(.*?)</script>', s62, flags=re.S).group(1), '62m2 (veri)')
    for kl in ('80m2', '80m2-21'):
        print(f'== {kl} paketi ve kapak görseli')
        subprocess.run([sys.executable, os.path.join(B, 'rehber80', 'paketle.py'), '--rehber', kl, '--npm', a.npm,
                        '--esbuild', a.esbuild, '--cikti', os.path.join(SITE, kl)], check=True)
        kapak_al(os.path.join(SITE, kl), os.path.join(SITE, kl, 'gorsel', 'kapak.jpg'))
    for kl, _, _, kapak in REHBERLER:
        if not os.path.exists(os.path.join(SITE, kl, kapak)):
            sys.exit(f'HATA: kapak yok: {kl}/{kapak}')
    print('== açılış sayfası')
    open(os.path.join(SITE, 'index.html'), 'w', encoding='utf-8').write(acilis_sayfasi())
    open(os.path.join(SITE, 'robots.txt'), 'w').write('User-agent: *\nDisallow: /\n')
    ortak.paketle_ve_kur(SITE, CIKTI, mtime=1793750400)


if __name__ == '__main__':
    main()
