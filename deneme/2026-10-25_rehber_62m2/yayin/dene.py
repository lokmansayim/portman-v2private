"""62 m² yayın paketini yerelde dener (kart 116): python3 dene.py [paket klasörü]
Yerel HTTP sunucusundan, masaüstü ve telefon genişliğinde: sayfa/konsol hatası ve CSP ihlali yok, dış istek yok,
20 adım (+ genel bakış), parçaya dokununca kart, galeride 8 görsel, 13. adımda izocam rulo serimi oynuyor,
20. adımda pencere kanatları ve kapılar sırayla açılıp kapanıyor. Ekranlar cikti/ekran/. Çıkış 0 = geçti.
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

# Hareketli parçaların anlık durumu: rulo serimi oranı (sr.scale.z) ve aç-kapa açıklığı (0 kapalı)
DURUM_JS = '''(adim) => { const M = window.__montaj; const ps = M.parts.filter(p => p.step === adim && p.anim);
  const serme = ps.filter(p => p.anim.serme).map(p => +p.anim.serme.sr.scale.z.toFixed(3));
  const ackapa = ps.filter(p => p.anim.ackapa).map(p => Math.max(...p.anim.ackapa.map(m =>
      Math.abs(m.tip === 'don' ? m.el.rotation.y - (m.taban || 0) : m.tip === 'devir' ? m.el.rotation[m.ax] : m.el.position[m.ax] - m.p0))));
  return { serme, ackapa: ackapa.map(v => +v.toFixed(3)) }; }'''


def kos(pw, ad, ayar):
    b = pw.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    p = b.new_context(**ayar).new_page()
    hatalar, dis, eksik = [], [], []
    p.on('pageerror', lambda e: hatalar.append(f'pageerror: {e}'))
    p.on('console', lambda m: m.type in ('error', 'warning') and hatalar.append(f'console.{m.type}: {m.text}'))
    p.on('request', lambda r: (not r.url.startswith(KOK) and not r.url.startswith(('data:', 'blob:'))) and dis.append(r.url))
    p.on('response', lambda r: r.status >= 400 and eksik.append(f'{r.status} {r.url}'))
    p.goto(KOK, wait_until='networkidle', timeout=120000)
    p.wait_for_function('() => window.__montaj && window.__montaj.parts', timeout=60000)
    p.wait_for_timeout(1000)
    p.screenshot(path=os.path.join(EKRAN, f'{ad}_acilis.png'))
    o = p.evaluate('''() => { const m = window.__montaj; const kotu = []; let kartli = 0; const ad = new Set();
        m.parts.forEach(x => { const i = x.obj.userData.info; if (!i) return; kartli++; ad.add(i.ad);
          if (!Array.isArray(i.satir) || i.satir.some(r => !Array.isArray(r) || r.length !== 2)) kotu.push(i.ad); });
        return { adim: m.STEPS.length, N: m.N, kartli, cesit: ad.size, kotu: [...new Set(kotu)], baslik: document.title,
                 kip: document.compatMode, h1: document.querySelector('h1').textContent,
                 galeri: document.querySelectorAll('#galThumbs button').length }; }''')
    print(f'[{ad}] {json.dumps(o, ensure_ascii=False)}')
    if o['kip'] != 'CSS1Compat':
        bulgu.append(f'{ad}: belge tuhaf kipte')
    if o['N'] != 20 or o['adim'] != 21:
        bulgu.append(f'{ad}: 20 adım (+ genel bakış) beklenirdi: N={o["N"]}, STEPS={o["adim"]}')
    if o['kotu']:
        bulgu.append(f'{ad}: satırı bozuk kart: {o["kotu"]}')
    # her adım + adımın render görseli (varsa)
    rnd = p.evaluate('() => !!document.getElementById("rndTog")')
    if rnd:
        p.click('#rndTog')
    for i in range(o['adim']):
        p.evaluate(f'() => window.__montaj.goTo({i}, false)')
        if rnd:
            p.wait_for_function(f'() => {{ const im = document.getElementById("rndImg"); return im.hidden || (im.complete && im.naturalWidth > 0); }}', timeout=15000)
    if rnd:
        p.click('#rndTog')
    # 13 · izocam rulo serimi: her şerit bir ara değerden geçip 1'e (tam serili) ulaşmalı; şeritler sırayla
    # (Animasyon sırasında ekran görüntüsü alınmaz: yazılım GPU'sunda uzun sürer ve animasyon saatini atlatır.)
    p.evaluate('() => window.__montaj.goTo(12, false)'); p.wait_for_timeout(500)
    p.evaluate('() => window.__montaj.goTo(13, true)')
    ara, ilk_ara, son = None, None, None
    for k in range(40):
        p.wait_for_timeout(500)
        d = p.evaluate(DURUM_JS, 13)['serme']
        if ara is None:
            ara, ilk_ara = [False] * len(d), [None] * len(d)
        for j, v in enumerate(d):
            if 0.05 < v < 0.95 and not ara[j]:
                ara[j], ilk_ara[j] = True, k
        son = d
    p.screenshot(path=os.path.join(EKRAN, f'{ad}_adim13_serme_son.png'))
    print(f'[{ad}] 13. adım: {len(son or [])} şerit, ara değerden geçen {sum(ara or [])}, ilk geçiş anı (×0,5 sn) {ilk_ara}, sonda {son}')
    if not son:
        bulgu.append(f'{ad}: 13. adımda rulo serimi parçası yok')
    elif sum(ara) < len(ara) / 2 or min(son) < 0.99:   # yazılım GPU'sunda kare atlar; ara hâl her şeritte yakalanmayabilir
        bulgu.append(f'{ad}: 13. adımda rulo serimi tam oynamadı (geçen {sum(ara)}/{len(ara)}, sonda {son})')
    elif len({x for x in ilk_ara if x is not None}) < 2:
        bulgu.append(f'{ad}: 13. adımda şeritler sırayla serilmedi')
    # 20 · kanat ve kapılar: her biri açılmalı, sırayla, sonunda hepsi kapalı
    p.evaluate('() => window.__montaj.goTo(19, false)'); p.wait_for_timeout(500)
    p.evaluate('() => window.__montaj.goTo(20, true)')
    tepe, ilk, son = None, None, None
    for k in range(40):
        p.wait_for_timeout(500)
        d = p.evaluate(DURUM_JS, 20)['ackapa']
        if tepe is None:
            tepe, ilk = [0.0] * len(d), [None] * len(d)
        for j, v in enumerate(d):
            tepe[j] = max(tepe[j], v)
            if v > 0.05 and ilk[j] is None:
                ilk[j] = k
        son = d
    p.evaluate('() => { const M = window.__montaj; M.goTo(20, false); M.ackapa(1); }'); p.wait_for_timeout(600)
    p.screenshot(path=os.path.join(EKRAN, f'{ad}_adim20_acik.png'))
    p.evaluate('() => window.__montaj.ackapa(0)')
    print(f'[{ad}] 20. adım: {len(tepe or [])} kanat/kapı, açılan {sum(1 for v in (tepe or []) if v > 0.05)}, '
          f'açılma anı (×0,5 sn) {ilk}, sonda en büyük açıklık {max(son) if son else None}')
    if not tepe or any(v <= 0.05 for v in tepe):
        bulgu.append(f'{ad}: 20. adımda açılmayan kanat/kapı var ({tepe})')
    elif max(son) > 0.02:
        bulgu.append(f'{ad}: 20. adım sonunda kanat/kapı kapanmadı ({son})')
    elif len(set(ilk)) < 3:
        bulgu.append(f'{ad}: 20. adımda kanat/kapılar sırayla açılmadı ({ilk})')
    # galeri: 8 görselin hepsi yükleniyor
    p.click('#galTog')
    for k in range(o['galeri']):
        p.click(f'#galThumbs button:nth-child({k + 1})')
        p.wait_for_function('() => { const i = document.getElementById("galImg"); return i.complete && i.naturalWidth > 0; }', timeout=15000)
    p.screenshot(path=os.path.join(EKRAN, f'{ad}_galeri.png'))
    p.click('#galX')
    if o['galeri'] != 8:
        bulgu.append(f'{ad}: galeride {o["galeri"]} görsel (8 beklenirdi)')
    # parçaya dokun → kart
    p.evaluate('() => window.__montaj.goTo(window.__montaj.N, false)')
    p.wait_for_timeout(1500)
    vp = p.locator('#viewport canvas').bounding_box()
    acildi = False
    for fx in (0.5, 0.45, 0.55, 0.4, 0.6):
        for fy in (0.5, 0.45, 0.55, 0.6, 0.4):
            x, y = vp['x'] + vp['width'] * fx, vp['y'] + vp['height'] * fy
            p.touchscreen.tap(x, y) if ayar.get('has_touch') else p.mouse.click(x, y)
            p.wait_for_timeout(120)
            if p.evaluate('() => !document.getElementById("info").hidden'):
                acildi = True
                break
        if acildi:
            break
    if acildi:
        print(f'[{ad}] dokunulan kart: {p.text_content("#infoT")} · satırlar: {p.text_content("#infoD")[:160]}')
        p.screenshot(path=os.path.join(EKRAN, f'{ad}_kart.png'))
    else:
        bulgu.append(f'{ad}: parçaya dokununca kart açılmadı')
    if p.evaluate('() => document.documentElement.scrollWidth > window.innerWidth + 1'):
        bulgu.append(f'{ad}: yatay taşma var')
    metin = p.evaluate('() => document.body.innerText').lower()
    for y in ('lokman', 'kaynak:', 'sketchup', 'teyit', 'varsayım'):
        if y in metin:
            bulgu.append(f'{ad}: görünen metinde "{y}"')
    for h in hatalar:
        if 'GPU stall' in h or ('WebGL' in h and 'warning' in h):   # yazılım GPU uyarısı
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
