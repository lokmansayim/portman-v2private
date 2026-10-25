const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'); const SP = process.argv[2];
const body = fs.readFileSync(path.join(SP, 'montaj-rehberi.html'), 'utf8');
fs.writeFileSync(path.join(SP, 't/index.html'), `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0}[hidden]{display:none!important}</style></head><body>${body}</body></html>`);
(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await (await browser.newContext({ viewport: { width: 1440, height: 860 } })).newPage();
  const errs=[]; page.on('pageerror', e => errs.push(e.message)); page.on('console', m => { if (m.type()==='error' && !/ERR_FAILED/.test(m.text())) errs.push(m.text()); });
  await page.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', route => route.fulfill({ path: path.join(SP, 't/node_modules/three', route.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', '')), contentType: 'application/javascript' }));
  await page.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await page.goto('file://' + path.join(SP, 't/index.html'));
  await page.waitForTimeout(1200);
  const shot = async (step, tgt, pos, name) => {
    await page.evaluate(s => window.__montaj.goTo(s, false), step); await page.waitForTimeout(1800);
    await page.evaluate(([t, p]) => { const M = window.__montaj; M.controls.target.set(...t); M.camera.position.set(...p); M.controls.update(); }, [tgt, pos]);
    await page.waitForTimeout(1200); await page.screenshot({ path: path.join(SP, `t/${name}.png`) });
  };
  // B-02: X = -1.048, Z = -2.411 ; yukarıdan, yatak 1 tarafından
  await shot(2, [-1.0, 2.5, -2.38], [-1.0, 2.95, -2.37], 'v7-b02');
  // HFL: X = -0.44, Z = 2.90
  await shot(6, [-0.39, 2.5, 2.95], [-0.39, 3.0, 2.96], 'v7-hfl');
  // B-02 kartı: tıkla
  const info = await page.evaluate(() => { const p = window.__montaj.parts.find(q => q.info && q.info.kod === 'B-02'); return p ? p.info.satir : null; });
  console.log('B-02', JSON.stringify(info));
  console.log('errors', errs);
  await browser.close();
})();
