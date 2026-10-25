// Serme ara durumu: node serme2.js <html> <png> <oran> <kamera px,py,pz,tx,ty,tz>
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const [html, out, oran, kam] = process.argv.slice(2), NM = path.join(__dirname, 'node_modules/three');
const tmp = path.join(path.dirname(html), '_test.html');
fs.writeFileSync(tmp, `<!doctype html><html><head><meta charset="utf-8"></head><body>${fs.readFileSync(html, 'utf8')}</body></html>`);
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await (await b.newContext({ viewport: { width: 1000, height: 640 } })).newPage(); const e = [];
  p.on('pageerror', x => e.push(x.message));
  await p.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => r.fulfill({ path: path.join(NM, r.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', '')), contentType: 'application/javascript' }));
  await p.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await p.goto('file://' + tmp, { waitUntil: 'domcontentloaded', timeout: 90000 }); await p.waitForTimeout(2500);
  await p.evaluate(([o, k]) => { const M = window.__montaj; M.goTo(16, false); M.serme(+o); const v = k.split(',').map(Number); M.kamera(v.slice(0, 3), v.slice(3, 6)); }, [oran, kam]);
  await p.waitForTimeout(1200); await p.screenshot({ path: out });
  console.log('hata', e); await b.close();
})();
