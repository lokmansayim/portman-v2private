const { chromium } = require('playwright');
const path = require('path'); const SP = process.argv[2];
(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await (await browser.newContext({ viewport: { width: 1000, height: 700 } })).newPage();
  await page.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', route => route.fulfill({ path: path.join(SP, 't/node_modules/three', route.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', '')), contentType: 'application/javascript' }));
  await page.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await page.goto('file://' + path.join(SP, 't/index.html')); await page.waitForTimeout(1200);
  const out = await page.evaluate(() => {
    const M = window.__montaj, T = M.THREE; M.goTo(17, true);
    const res = {};
    for (const [n, X, Z] of [['B02', 198.2, 744.1], ['HFL', 261, 205], ['BL', 5, 995]]) {
      const p = M.parts.find(q => q.obj.type === 'Group' && q.obj.children.length === 5 && Math.abs(new T.Box3().setFromObject(q.obj).getCenter(new T.Vector3()).x - (X/100-3)) < 0.08 && Math.abs(new T.Box3().setFromObject(q.obj).getCenter(new T.Vector3()).z - (5-Z/100)) < 0.08);
      if (!p) { res[n] = 'yok'; continue; }
      res[n] = p.obj.children.map(c => { const b = new T.Box3().setFromObject(c); const f = v => Math.round(v*1000)/10; return `x ${f(b.min.x+3)}–${f(b.max.x+3)}  y ${f(5-b.max.z)}–${f(5-b.min.z)}`; });
    }
    return res;
  });
  console.log(JSON.stringify(out, null, 1));
  await browser.close();
})();
