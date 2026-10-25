const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const html = process.argv[2], NM = path.join(__dirname, 'node_modules/three');
const tmp = path.join(path.dirname(html), '_test.html');
fs.writeFileSync(tmp, `<!doctype html><html><head><meta charset="utf-8"></head><body>${fs.readFileSync(html, 'utf8')}</body></html>`);
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await (await b.newContext({ viewport: { width: 1200, height: 800 } })).newPage(); const e = [];
  p.on('pageerror', x => e.push(x.message));
  await p.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => r.fulfill({ path: path.join(NM, r.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', '')), contentType: 'application/javascript' }));
  await p.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await p.goto('file://' + tmp, { waitUntil: 'domcontentloaded', timeout: 90000 }); await p.waitForTimeout(2500);
  const r = await p.evaluate(() => {
    const M = window.__montaj, bad = [], ornek = {};
    M.parts.forEach((q, i) => { const inf = q.obj.userData.info;
      if (!inf || !inf.ad) bad.push([i, 'ad yok']);
      (inf.satir || []).forEach(s => { if (!Array.isArray(s) || s.length !== 2 || s.some(v => v === undefined || v === null || /undefined|NaN/.test(String(v)))) bad.push([i, inf.ad, JSON.stringify(s)]); });
      const k = (inf.kod || '-') + ' ' + inf.ad; if (!ornek[k]) ornek[k] = inf.satir.filter(s => s && s[1]).map(s => s.join(': ')).join(' | ');
    });
    // rastgele 3 parçaya tıklama benzetimi: kartı aç
    return { bad: bad.slice(0, 20), n: bad.length, ornek };
  });
  console.log('sorunlu satır', r.n, JSON.stringify(r.bad, null, 0));
  Object.entries(r.ornek).forEach(([k, v]) => console.log('•', k, '→', v.slice(0, 260)));
  console.log('hata', e); await b.close();
})();
