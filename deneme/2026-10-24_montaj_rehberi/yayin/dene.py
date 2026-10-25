"""Yayın paketini yerelde dener (kart 104): python3 dene.py [paket klasörü]
Paket yerel bir HTTP sunucusundan açılır; masaüstü ve telefon genişliğinde:
konsol/sayfa hatası ve CSP ihlali yok, dış istek yok, adımlar, her adımın render görseli, galeri, parça kartları,
bir parçaya dokununca kart. Ekran görüntüleri cikti/ekran/ altına. Çıkış kodu 0 = geçti.
"""
import functools, http.server, json, os, sys, threading
from playwright.sync_api import sync_playwright

B = os.path.dirname(os.path.abspath(__file__))
PAKET = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(B, 'cikti', 'paket'))
EKRAN = os.path.join(B, 'cikti', 'ekran')
os.makedirs(EKRAN, exist_ok=True)


class Sessiz(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Sessiz, directory=PAKET))
threading.Thread(target=srv.serve_forever, daemon=True).start()
KOK = f'http://127.0.0.1:{srv.server_port}/'
bulgu = []


def kos(pw, ad, ayar):
    b = pw.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    ctx = b.new_context(**ayar)
    p = ctx.new_page()
    hatalar, dis, eksik = [], [], []
    p.on('pageerror', lambda e: hatalar.append(f'pageerror: {e}'))
    p.on('console', lambda m: m.type in ('error', 'warning') and hatalar.append(f'console.{m.type}: {m.text}'))
    p.on('request', lambda r: (not r.url.startswith(KOK) and not r.url.startswith(('data:', 'blob:'))) and dis.append(r.url))
    p.on('response', lambda r: r.status >= 400 and eksik.append(f'{r.status} {r.url}'))
    p.goto(KOK, wait_until='networkidle')
    p.wait_for_function('() => window.__montaj && window.__montaj.parts', timeout=20000)
    p.wait_for_timeout(800)
    p.screenshot(path=os.path.join(EKRAN, f'{ad}_acilis.png'))
    o = p.evaluate('''() => { const m = window.__montaj; const kotu = [];
        let kartli = 0; const kartlar = new Set();
        m.parts.forEach(x => { const i = x.obj.userData.info; if (!i) return;
          kartli++; kartlar.add(i.ad);
          if (!Array.isArray(i.satir) || i.satir.some(r => !Array.isArray(r) || r.length !== 2)) kotu.push(i.ad); });
        return { adim: m.STEPS.length, kartli, cesit: kartlar.size, kotu: [...new Set(kotu)], baslik: document.title,
                 quirks: document.compatMode, h1: document.querySelector('h1').textContent }; }''')
    print(f'[{ad}] {json.dumps(o, ensure_ascii=False)}')
    if o['quirks'] != 'CSS1Compat':
        bulgu.append(f'{ad}: belge tuhaf kipte ({o["quirks"]})')
    if o['kotu']:
        bulgu.append(f'{ad}: satırı bozuk kart: {o["kotu"]}')
    # adımlar + adımın render görseli
    p.click('#rndTog')
    for i in range(o['adim']):
        p.evaluate(f'() => window.__montaj.goTo({i}, false)')
        p.wait_for_function(f'() => {{ const im = document.getElementById("rndImg"); return im.complete && im.src.endsWith("adim_{i:02d}.jpg") && im.naturalWidth > 0; }}', timeout=10000)
        if i in (0, 9, o['adim'] - 1):
            p.screenshot(path=os.path.join(EKRAN, f'{ad}_adim{i:02d}_render.png'))
    p.click('#rndTog')
    durum = p.evaluate('() => document.getElementById("rndImg").hidden')
    if not durum:
        bulgu.append(f'{ad}: "3B görünüme dön" render görselini kapatmadı')
    # galeri
    p.click('#galTog')
    n = p.evaluate('() => document.querySelectorAll("#galThumbs button").length')
    for k in range(n):
        p.click(f'#galThumbs button:nth-child({k + 1})')
        p.wait_for_function('() => { const i = document.getElementById("galImg"); return i.complete && i.naturalWidth > 0; }', timeout=10000)
    p.screenshot(path=os.path.join(EKRAN, f'{ad}_galeri.png'))
    p.click('#galX')
    # parçaya dokun: ekranın ortasından ızgara üzerinde ilk isabet
    p.evaluate('() => window.__montaj.goTo(window.__montaj.STEPS.length - 1, false)')
    p.wait_for_timeout(1500)
    vp = p.locator('#viewport canvas').bounding_box()
    acildi = False
    for fx in (0.5, 0.45, 0.55, 0.4, 0.6):
        for fy in (0.5, 0.45, 0.55, 0.6, 0.4):
            x, y = vp['x'] + vp['width'] * fx, vp['y'] + vp['height'] * fy
            if ayar.get('has_touch'):
                p.touchscreen.tap(x, y)
            else:
                p.mouse.click(x, y)
            p.wait_for_timeout(120)
            if p.evaluate('() => !document.getElementById("info").hidden'):
                acildi = True
                break
        if acildi:
            break
    if acildi:
        print(f'[{ad}] dokunulan kart: {p.text_content("#infoT")}')
        p.screenshot(path=os.path.join(EKRAN, f'{ad}_kart.png'))
    else:
        bulgu.append(f'{ad}: parçaya dokununca kart açılmadı')
    tasma = p.evaluate('() => document.documentElement.scrollWidth > window.innerWidth + 1')
    if tasma:
        bulgu.append(f'{ad}: yatay taşma var')
    p.wait_for_timeout(300)
    for h in hatalar:
        if 'GPU stall' in h or 'WebGL' in h and 'warning' in h:   # yazılım GPU'sunun uyarıları; gerçek cihazda yok
            continue
        bulgu.append(f'{ad}: {h}')
    bulgu.extend(f'{ad}: dış istek {u}' for u in dis)
    bulgu.extend(f'{ad}: yanıt {u}' for u in eksik)
    b.close()


with sync_playwright() as pw:
    kos(pw, 'masaustu', dict(viewport={'width': 1366, 'height': 860}))
    kos(pw, 'telefon', dict(viewport={'width': 390, 'height': 844}, device_scale_factor=3, is_mobile=True, has_touch=True))
srv.shutdown()
print('BULGU:' if bulgu else 'SONUÇ: geçti (bulgu yok)')
for x in bulgu:
    print('  -', x)
sys.exit(1 if bulgu else 0)
