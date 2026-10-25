// Kullanım: node test.js <html> <çıktı klasörü> [adım,adım,...] [genişlik yükseklik]
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const [html, out, adimlar = '0', W = '1400', Hh = '860'] = process.argv.slice(2);
const NM = path.join(__dirname, 'node_modules/three');
const body = fs.readFileSync(html, 'utf8'); const tmp = path.join(path.dirname(html), '_test.html');
fs.writeFileSync(tmp, `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>${body}</body></html>`);
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await (await b.newContext({ viewport: { width: +W, height: +Hh } })).newPage(); const e = [];
  p.on('pageerror', x => e.push(x.message + ' ' + (x.stack || '').split('\n').slice(0, 4).join(' | ')));
  p.on('console', m => { if (m.type() === 'error') e.push('console: ' + m.text()); });
  await p.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => r.fulfill({ path: path.join(NM, r.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', '')), contentType: 'application/javascript' }));
  await p.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await p.goto('file://' + tmp, { waitUntil: 'domcontentloaded', timeout: 90000 }); await p.waitForTimeout(2500);
  if (e.length) { console.log('HATA', e); }
  const say = await p.evaluate(() => { const M = window.__montaj; if (!M) return null; const c = {}; M.parts.forEach(q => c[q.step] = (c[q.step] || 0) + 1); return c; });
  console.log('adım başına parça', JSON.stringify(say));
  for (const a of adimlar.split(';')) {
    const [st, kam, ad] = a.split('@');
    await p.evaluate(i => window.__montaj.goTo(+i, false), st); await p.waitForTimeout(1400);
    if (kam) { await p.evaluate(k => { const M = window.__montaj, v = k.split(',').map(Number); M.kamera(v.slice(0, 3), v.slice(3, 6)); }, kam); await p.waitForTimeout(700); }
    await p.screenshot({ path: path.join(out, (ad || `s${String(st).padStart(2, '0')}`) + '.png') });
  }
  if (e.length) console.log('HATA', e);
  await b.close();
})();
