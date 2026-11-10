// İE-34 · Montaj rehberi telefonda, nginx'in verdiği baytlar ve başlıklarla (testler/test_rehber_yayin.py).
//   THREE_DIR=<three@0.160.0> node testler/rehber_telefon.js <adres> <gövde.html> <başlıklar.json> <ekran.png> <sonuç.json>
// iPhone 13 öykünmesi. Test sayfayı yerel nginx'ten HTTPS ile alır (gerçek yapılandırma); tarayıcıdaki adres isteği o gövde ve o başlıklarla
// (CSP dahil) karşılanır. Tarayıcı CSP'yi bu başlıktan uygular. Ortamda WebGL olup olmadığı ayrıca yazılır (`webgl`). three.js 0.160.0 isteği jsDelivr adresiyle yapılır ve THREE_DIR'den karşılanır
// (CSP adrese bakar: izin yalnız cdn.jsdelivr.net'e), Google Fonts boş CSS döner; başka her istek kesilir ve yazılır. CSP ihlali, sayfa hatası,
// sahne (canvas), adım sayısı ve son adımın başlığı yazılır. Ağ yok, LLM yok.
const { chromium, devices } = require('playwright');
const fs = require('fs');
(async () => {
  const [adres, govde, basliklar, ekran, out] = process.argv.slice(2);
  const alan = new URL(adres).hostname;
  const b = await chromium.launch({
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
    env: { ...process.env, TMPDIR: '/tmp' },
  });
  const c = await b.newContext({ ...devices['iPhone 13'] });
  const p = await c.newPage();
  // Ortamda WebGL var mı: CSP'siz boş sayfada sına. Yoksa (CI koşucusu GPU sürecini açamıyor) three.js'in WebGL bağlam iletileri
  // beklenir ve sahne çizilmez; testin öteki denetimleri (CSP, sayfa hatası, adımlar, telefon düzeni) aynı kalır.
  const sina = await c.newPage();
  const webgl = await sina.evaluate(() => { const t = document.createElement('canvas'); return !!(t.getContext('webgl2') || t.getContext('webgl')); });
  await sina.close();
  const T = process.env.THREE_DIR;
  const disari = [];
  await p.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => r.fulfill({ path: T + '/' + r.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', ''), contentType: 'application/javascript' }));
  await p.route('https://fonts.googleapis.com/**', r => r.fulfill({ body: '', contentType: 'text/css' }));
  await p.route(u => u.hostname === alan && u.href !== adres, r => r.fulfill({ status: 404, body: '' }));      // ör. favicon
  await p.route(adres, r => r.fulfill({ status: 200, headers: JSON.parse(fs.readFileSync(basliklar, 'utf8')), body: fs.readFileSync(govde) }));
  await p.route(u => u.hostname !== alan && !['cdn.jsdelivr.net', 'fonts.googleapis.com'].includes(u.hostname), r => { disari.push(r.request().url()); r.abort(); });
  await p.addInitScript(() => { window.__csp = []; document.addEventListener('securitypolicyviolation', e => window.__csp.push(`${e.violatedDirective} ${e.blockedURI}`)); });
  const hatalar = [];
  p.on('pageerror', e => hatalar.push(String(e)));
  p.on('console', m => { if (m.type() === 'error') hatalar.push(`konsol: ${m.text()}`); });
  const r = await p.goto(adres);
  const sonuc = { http: r.status(), csp_basligi: (await r.allHeaders())['content-security-policy'] || null, webgl };
  try {
    await p.waitForFunction(() => window.__montaj, null, { timeout: 60000 });
    const ilk = await p.evaluate(() => ({ baslik: document.title, N: window.__montaj.N, adim: document.getElementById('stepTitle').textContent,
      genislik: window.innerWidth }));      // telefon ayarı (viewport) yoksa 980: masaüstü düzeni
    await p.waitForTimeout(500);
    await p.screenshot({ path: ekran });
    const son = await p.evaluate(() => { const M = window.__montaj; M.goTo(M.N - 1, false); return document.getElementById('stepTitle').textContent; });
    const tuval = await p.evaluate(() => { const t = document.querySelector('canvas'); return t ? [t.width, t.height] : null; });
    Object.assign(sonuc, ilk, { son_adim: son, tuval });
  } catch (e) {
    sonuc.bekleme_hatasi = String(e).slice(0, 300);
  }
  sonuc.csp = await p.evaluate(() => window.__csp || []);
  sonuc.hatalar = hatalar;
  sonuc.disari = disari;
  fs.writeFileSync(out, JSON.stringify(sonuc, null, 1));
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
