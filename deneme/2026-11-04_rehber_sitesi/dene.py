"""Site paketini yerelde dener (kart 104, 4.11.2026): python3 dene.py [site klasörü]

Yerel HTTP sunucusundan, masaüstü ve telefon genişliğinde:
  açılış: iki kart, görseller yüklenir, bağlantılar açılır;
  her rehber: belge kipi, adım sayısı, kart satırları, her adım açılır, görünen bütün yazılarda (adım metni, liste,
  bütün kimlik kartları) iç not yok, rulo serimi ve kanat/kapı aç-kapa oynar, parçaya dokununca kart açılır,
  galeri (varsa) yüklenir; 80 m²'de evin altındaki ön onay paftası yüklenir;
  her sayfada konsol/sayfa hatası, CSP ihlali, 4xx/5xx ve dış istek yok, yatay taşma yok.
Ekranlar cikti/ekran/. Çıkış 0 = geçti.
"""
import functools, http.server, json, os, sys, threading
from playwright.sync_api import sync_playwright

B = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(B, 'cikti', 'site'))
EKRAN = os.path.join(B, 'cikti', 'ekran')
os.makedirs(EKRAN, exist_ok=True)
REHBER = {'62m2': dict(N=20, galeri=8, pafta=False, yasak_ek=[]),
          '80m2': dict(N=22, galeri=0, pafta=True, yasak_ek=['62 m²']),
          '80m2-21': dict(N=21, galeri=0, pafta=True, yasak_ek=['62 m²', '3+1'])}
YASAK = ['lokman', 'kaynak:', 'liste de böyle', 'varsay', 'motor', 'teyit', 'sketchup', 'alpha mini', 'tk-01', 'pk-0', 'tk-0', '(d-', 'pm-tk', 'kitap',
         'kitab', 'kural', 'modelinde', 'kart modeli', 'portman', 'tatar', 'patron', 'deneme', 'undefined', 'null', 'nan']


class Sessiz(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Sessiz, directory=SITE))
threading.Thread(target=srv.serve_forever, daemon=True).start()
KOK = f'http://127.0.0.1:{srv.server_port}/'
bulgu = []

DURUM_JS = '''(adim) => { const ps = window.__montaj.parts.filter(p => p.step === adim && p.anim);
  const serme = ps.filter(p => p.anim.serme).map(p => +p.anim.serme.sr.scale.z.toFixed(3));
  const ackapa = ps.filter(p => p.anim.ackapa).map(p => +Math.max(...p.anim.ackapa.map(m =>
      Math.abs(m.tip === 'don' ? m.el.rotation.y - (m.taban || 0) : m.tip === 'devir' ? m.el.rotation[m.ax] : m.el.position[m.ax] - m.p0))).toFixed(3));
  return { serme, ackapa }; }'''


def sayfa_ac(b, ayar, yol):
    p = b.new_context(**ayar).new_page()
    kay = dict(hata=[], dis=[], eksik=[])
    p.on('pageerror', lambda e: kay['hata'].append(f'pageerror: {e}'))
    p.on('console', lambda m: m.type in ('error', 'warning') and kay['hata'].append(f'console.{m.type}: {m.text}'))
    p.on('request', lambda r: (not r.url.startswith(KOK) and not r.url.startswith(('data:', 'blob:'))) and kay['dis'].append(r.url))
    p.on('response', lambda r: r.status >= 400 and kay['eksik'].append(f'{r.status} {r.url}'))
    p.goto(KOK + yol, wait_until='networkidle', timeout=120000)
    return p, kay


def sayfa_kapat(p, kay, ad):
    if p.evaluate('() => document.documentElement.scrollWidth > window.innerWidth + 1'):
        bulgu.append(f'{ad}: yatay taşma var')
    for h in kay['hata']:
        if 'GPU stall' in h or ('WebGL' in h and 'warning' in h):
            continue
        bulgu.append(f'{ad}: {h}')
    bulgu.extend(f'{ad}: dış istek {u}' for u in kay['dis'])
    bulgu.extend(f'{ad}: yanıt {u}' for u in kay['eksik'])
    p.context.close()


def acilis(b, cihaz, ayar):
    ad = f'açılış/{cihaz}'
    p, kay = sayfa_ac(b, ayar, '')
    o = p.evaluate('''() => ({ kip: document.compatMode, baslik: document.title,
        kart: [...document.querySelectorAll('a.kart')].map(a => ({ href: a.getAttribute('href'), ad: a.querySelector('h2').textContent,
              img: a.querySelector('img').complete && a.querySelector('img').naturalWidth > 0 })) })''')
    print(f'[{ad}] {json.dumps(o, ensure_ascii=False)}')
    p.evaluate('() => Promise.all([...document.images].map(i => i.complete ? 1 : new Promise(r => { i.onload = i.onerror = r; })))')
    if o['kip'] != 'CSS1Compat' or len(o['kart']) != len(REHBER):
        bulgu.append(f'{ad}: belge kipi ya da kart sayısı yanlış')
    p.screenshot(path=os.path.join(EKRAN, f'acilis_{cihaz}.png'), full_page=True)
    for k in o['kart']:
        if p.request.get(KOK + k['href']).status != 200:
            bulgu.append(f'{ad}: bağlantı açılmıyor {k["href"]}')
    if p.evaluate('() => [...document.images].some(i => !i.naturalWidth)'):
        bulgu.append(f'{ad}: yüklenmeyen kapak görseli')
    sayfa_kapat(p, kay, ad)


def rehber(b, kl, cihaz, ayar):
    ad, bek = f'{kl}/{cihaz}', REHBER[kl]
    p, kay = sayfa_ac(b, ayar, kl + '/')
    p.wait_for_function('() => window.__montaj && window.__montaj.parts', timeout=60000)
    p.wait_for_timeout(1500)
    o = p.evaluate('''() => { const m = window.__montaj; const kotu = []; let kartli = 0;
        m.parts.forEach(x => { const i = x.obj.userData.info; if (!i) return; kartli++;
          if (!Array.isArray(i.satir) || i.satir.some(r => r && (!Array.isArray(r) || r.length !== 2))) kotu.push(i.ad); });
        return { N: m.N, adim: m.STEPS.length, parca: m.parts.length, kartli, kotu: [...new Set(kotu)], kip: document.compatMode,
                 baslik: document.title, h1: document.querySelector('h1').textContent,
                 galeri: document.querySelectorAll('#galThumbs button').length }; }''')
    print(f'[{ad}] {json.dumps(o, ensure_ascii=False)}')
    p.screenshot(path=os.path.join(EKRAN, f'{kl}_{cihaz}_acilis.png'))
    if o['kip'] != 'CSS1Compat':
        bulgu.append(f'{ad}: belge tuhaf kipte')
    if o['N'] != bek['N'] or o['adim'] != bek['N'] + 1:
        bulgu.append(f'{ad}: {bek["N"]} adım beklenirdi (N={o["N"]}, STEPS={o["adim"]})')
    if o['kotu']:
        bulgu.append(f'{ad}: satırı bozuk kart: {o["kotu"]}')
    # görünen bütün yazılar: her adımın paneli + bütün kimlik kartları + üst bilgi
    yazi = [p.evaluate('() => document.querySelector("header") ? document.querySelector("header").innerText : ""'),
            p.evaluate('() => document.querySelector(".note") ? document.querySelector(".note").innerText : ""')]
    for i in range(o['adim']):
        p.evaluate(f'() => window.__montaj.goTo({i}, false)')
        yazi.append(p.evaluate('() => document.querySelector("main") ? document.querySelector("main").innerText : document.body.innerText'))
    yazi.append(p.evaluate('''() => window.__montaj.parts.map(x => x.obj.userData.info).filter(Boolean)
        .map(i => [i.kod || '', i.ad, ...i.satir.filter(r => r && r[1]).map(r => r[0] + ': ' + r[1])].join(' | ')).join('\\n')'''))
    metin = '\n'.join(yazi)
    open(os.path.join(EKRAN, f'{kl}_gorunen_metin.txt'), 'w', encoding='utf-8').write(metin)
    kucuk = metin.lower()
    for y in YASAK + bek['yasak_ek']:
        if y in ('null', 'nan', 'undefined'):
            import re
            if re.search(r'\b' + y + r'\b', kucuk):
                bulgu.append(f'{ad}: görünen metinde "{y}"')
        elif y in kucuk:
            i = kucuk.index(y)
            bulgu.append(f'{ad}: görünen metinde "{y}": …{metin[max(0, i - 60):i + 60]}…')
    # hareketli adımlar
    adimlar = p.evaluate('''() => { const s = new Set(), a = new Set(); window.__montaj.parts.forEach(q => {
        if (q.anim && q.anim.serme) s.add(q.step); if (q.anim && q.anim.ackapa) a.add(q.step); }); return { serme: [...s], ackapa: [...a] }; }''')
    for st in adimlar['serme']:
        p.evaluate(f'() => window.__montaj.goTo({st - 1}, false)'); p.wait_for_timeout(400)
        p.evaluate(f'() => window.__montaj.goTo({st}, true)')
        ara, son = None, None
        for _ in range(40):
            p.wait_for_timeout(500)
            d = p.evaluate(DURUM_JS, st)['serme']
            ara = ara or [False] * len(d)
            ara = [x or 0.05 < v < 0.95 for x, v in zip(ara, d)]
            son = d
        print(f'[{ad}] {st}. adım rulo: {len(son)} şerit, ara hâli görülen {sum(ara)}, sonda en az {min(son)}')
        if sum(ara) < len(ara) / 2 or min(son) < 0.99:
            bulgu.append(f'{ad}: {st}. adımda rulo serimi tam oynamadı')
    for st in adimlar['ackapa']:   # önce adımı bir kez göster (yazılım GPU'sunda ilk kare uzun sürer), sonra oynat
        p.evaluate(f'() => window.__montaj.goTo({st}, false)'); p.wait_for_timeout(2500)
        p.evaluate(f'() => window.__montaj.goTo({st - 1}, false)'); p.wait_for_timeout(400)
        p.evaluate(f'() => window.__montaj.goTo({st}, true)')
        tepe, ilk, son = None, None, None
        for k in range(120):                  # 0,2 sn arayla: yazılım GPU'sunda ilk kanat kısa sürede açılıp kapanabilir
            p.wait_for_timeout(200)
            d = p.evaluate(DURUM_JS, st)['ackapa']
            tepe = tepe or [0.0] * len(d); ilk = ilk or [None] * len(d)
            tepe = [max(t, v) for t, v in zip(tepe, d)]
            ilk = [k if (x is None and v > 0.05) else x for x, v in zip(ilk, d)]
            son = d
        print(f'[{ad}] {st}. adım aç-kapa: {len(tepe)} kanat/kapı, açılan {sum(v > 0.05 for v in tepe)}, açılma anları {ilk}, sonda {max(son)}')
        if any(v <= 0.05 for v in tepe) or max(son) > 0.02 or len(set(ilk)) < 3:
            bulgu.append(f'{ad}: {st}. adımda kanat/kapılar sırayla açılıp kapanmadı')
        p.evaluate(f'() => {{ const M = window.__montaj; M.goTo({st}, false); M.ackapa(1); }}'); p.wait_for_timeout(600)
        p.screenshot(path=os.path.join(EKRAN, f'{kl}_{cihaz}_adim{st}_acik.png'))
        p.evaluate('() => window.__montaj.ackapa(0)')
    # ön onay paftası
    if bek['pafta']:
        pf = p.evaluate('() => { let sc = window.__montaj.parts[0].obj; while (sc.parent) sc = sc.parent; const k = window.__pdf || sc.getObjectByName("Ön onay sayfası"); const im = k && k.material.map && k.material.map.image; return { var: !!k, gorunur: !!(k && k.visible), yuklu: !!(im && im.complete && im.naturalWidth), en: im ? im.naturalWidth : 0 }; }')
        print(f'[{ad}] ön onay paftası: {pf}')
        if not (pf['var'] and pf['gorunur'] and pf['yuklu']):
            bulgu.append(f'{ad}: ön onay paftası yüklenmedi ({pf})')
    # galeri
    if o['galeri'] != bek['galeri']:
        bulgu.append(f'{ad}: galeride {o["galeri"]} görsel ({bek["galeri"]} beklenirdi)')
    if o['galeri']:
        p.click('#galTog')
        for k in range(o['galeri']):
            p.click(f'#galThumbs button:nth-child({k + 1})')
            p.wait_for_function('() => { const i = document.getElementById("galImg"); return i.complete && i.naturalWidth > 0; }', timeout=15000)
        p.click('#galX')
    # parçaya dokun
    p.evaluate('() => window.__montaj.goTo(window.__montaj.N, false)'); p.wait_for_timeout(1500)
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
        print(f'[{ad}] dokunulan kart: {p.text_content("#infoT")}')
        p.screenshot(path=os.path.join(EKRAN, f'{kl}_{cihaz}_kart.png'))
    else:
        bulgu.append(f'{ad}: parçaya dokununca kart açılmadı')
    sayfa_kapat(p, kay, ad)


CIHAZ = {'masaustu': dict(viewport={'width': 1366, 'height': 860}),
         'telefon': dict(viewport={'width': 390, 'height': 844}, device_scale_factor=3, is_mobile=True, has_touch=True)}
with sync_playwright() as pw:
    b = pw.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    SADECE = os.environ.get('DENE_REHBER')        # ör. DENE_REHBER=80m2-21: yalnız o rehber (açılış dahil değil)
    for cihaz, ayar in CIHAZ.items():
        if not SADECE:
            acilis(b, cihaz, ayar)
        for kl in REHBER:
            if not SADECE or kl == SADECE:
                rehber(b, kl, cihaz, ayar)
    b.close()
srv.shutdown()
print('BULGU:' if bulgu else 'SONUÇ: geçti (bulgu yok)')
for x in bulgu:
    print('  -', x)
sys.exit(1 if bulgu else 0)
