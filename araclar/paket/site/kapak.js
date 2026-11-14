// İE-41 · rehberin genel bakışından 3B sahnenin görüntüsü (açılış sayfasının kartı): node kapak.js <site> <rehber klasörü> <çıktı.png>
// Site yerel bir adresten sunulur (http://site.yerel/, dosyalar diskten); dış istek yoktur. Yazılım GPU'su (SwiftShader).
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const TUR = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.jpg': 'image/jpeg', '.png': 'image/png',
  '.woff2': 'font/woff2', '.txt': 'text/plain' };
(async () => {
  const [site, klasor, cikti] = process.argv.slice(2);
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1400, height: 900 }, deviceScaleFactor: 1 });
  await p.route('**/*', r => {
    const u = new URL(r.request().url());
    if (u.origin !== 'http://site.yerel') return r.abort();
    let f = path.join(site, decodeURIComponent(u.pathname));
    if (f.endsWith('/')) f += 'index.html';
    if (!fs.existsSync(f)) return r.fulfill({ status: 404, body: '' });
    r.fulfill({ path: f, contentType: TUR[path.extname(f)] || 'application/octet-stream' });
  });
  await p.goto(`http://site.yerel/${klasor}/`, { waitUntil: 'networkidle', timeout: 120000 });
  await p.waitForFunction(() => window.__montaj, null, { timeout: 60000 });
  await p.waitForTimeout(4000);
  await p.locator('#viewport canvas').screenshot({ path: cikti });
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
