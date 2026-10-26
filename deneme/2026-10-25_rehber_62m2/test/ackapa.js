// Kullanım: node ackapa.js <html> <klasör> "a@kamera@ad;..."  (a: 0 kapalı → 1 açık; kamera: px,py,pz,tx,ty,tz)  — ayrıca 20. adım animasyonunu oynatıp hata arar
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const [html, out, liste] = process.argv.slice(2), NM = path.join(__dirname, 'node_modules/three');
const tmp = path.join(path.dirname(html), '_test.html');
fs.writeFileSync(tmp, `<!doctype html><html><head><meta charset="utf-8"></head><body>${fs.readFileSync(html, 'utf8')}</body></html>`);
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await (await b.newContext({ viewport: { width: 1000, height: 640 } })).newPage(); const e = [];
  p.on('pageerror', x => e.push(x.message));
  await p.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => r.fulfill({ path: path.join(NM, r.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', '')), contentType: 'application/javascript' }));
  await p.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await p.goto('file://' + tmp, { waitUntil: 'domcontentloaded', timeout: 90000 }); await p.waitForTimeout(2500);
  await p.evaluate(() => window.__montaj.goTo(20, true)); await p.waitForTimeout(6000);
  const bilgi = await p.evaluate(() => window.__montaj.parts.filter(q => q.step === 20).map(q => !!(q.anim && q.anim.ackapa)).join(''));
  console.log('20. adımda hareketli parçalar', bilgi);
  await p.screenshot({ path: path.join(out, 'anim_orta.png'), timeout: 180000 });
  for (const it of liste.split(';')) {
    const [a, kam, ad] = it.split('@');
    await p.evaluate(([a, k]) => { const M = window.__montaj; M.goTo(20, false); M.ackapa(+a); const v = k.split(',').map(Number); M.kamera(v.slice(0, 3), v.slice(3, 6)); }, [a, kam]);
    await p.waitForTimeout(900);
    await p.screenshot({ path: path.join(out, ad + '.png'), timeout: 180000 });
  }
  console.log('hata', e); await b.close();
})();
