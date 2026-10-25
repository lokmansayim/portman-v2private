const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'); const SP = process.argv[2];
const body = fs.readFileSync(path.join(SP, 'montaj-rehberi.html'), 'utf8');
fs.writeFileSync(path.join(SP, 't/index.html'), `<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0}[hidden]{display:none!important}</style></head><body>${body}</body></html>`);
(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await (await browser.newContext({ viewport: { width: 1440, height: 860 } })).newPage();
  const errs=[]; page.on('pageerror', e => errs.push(e.message)); page.on('console', m => { if (m.type()==='error' && !/ERR_FAILED/.test(m.text())) errs.push(m.text()); });
  await page.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', route => route.fulfill({ path: path.join(SP, 't/node_modules/three', route.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', '')), contentType: 'application/javascript' }));
  await page.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await page.goto('file://' + path.join(SP, 't/index.html')); await page.waitForTimeout(1200);
  const shot = async (step, tgt, pos, name) => {
    await page.evaluate(s => window.__montaj.goTo(s, true), step); await page.waitForTimeout(800);
    await page.evaluate(([t, p]) => { const M = window.__montaj; M.controls.target.set(...t); M.camera.position.set(...p); M.controls.update(); }, [tgt, pos]);
    await page.waitForTimeout(900); await page.screenshot({ path: path.join(SP, `t/${name}.png`) });
  };
  // ön sol köşe: X=-3, Z=5 ; alın sacı ve iniş
  await shot(16, [-2.6, 2.4, 5.0], [-4.6, 2.2, 7.2], 'v8-alin');
  await shot(16, [-3.0, 1.4, 0.0], [-6.5, 1.8, 1.5], 'v8-inis');
  console.log('errors', errs);
  await browser.close();
})();
