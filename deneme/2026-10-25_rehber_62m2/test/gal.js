const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const [html, out] = process.argv.slice(2), NM = path.join(__dirname, 'node_modules/three');
const tmp = path.join(path.dirname(html), '_test.html');
fs.writeFileSync(tmp, `<!doctype html><html><head><meta charset="utf-8"></head><body>${fs.readFileSync(html, 'utf8')}</body></html>`);
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await (await b.newContext({ viewport: { width: 1300, height: 820 } })).newPage(); const e = [], bad = [];
  p.on('pageerror', x => e.push(x.message)); p.on('requestfailed', r => { if (!/fonts\./.test(r.url())) bad.push(r.url()); });
  await p.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => r.fulfill({ path: path.join(NM, r.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', '')), contentType: 'application/javascript' }));
  await p.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await p.goto('file://' + tmp, { waitUntil: 'domcontentloaded', timeout: 90000 }); await p.waitForTimeout(2500);
  // "Adımı render göster" kaldırıldı (Lokman, 25.10.2026): düğme yok olmalı, galeri açılmalı
  await p.evaluate(() => window.__montaj.goTo(16, false));
  const ok = await p.evaluate(() => ['rndTog', 'rndImg'].map(k => !!document.getElementById(k)));
  await p.click('#galTog'); await p.waitForTimeout(1500);
  const g = await p.evaluate(() => { const i = document.getElementById('galImg'); return [i.complete, i.naturalWidth, [...document.querySelectorAll('#galThumbs img')].filter(t => t.naturalWidth > 0).length]; });
  await p.screenshot({ path: out + '_gal.png', timeout: 180000 });
  console.log('adım render düğmesi var mı', ok, 'galeri', g, 'hata', e, 'yüklenemeyen', bad); await b.close();
})();
