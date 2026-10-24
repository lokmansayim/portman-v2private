const { chromium } = require('playwright'); const fs = require('fs'), path = require('path'); const SP = process.argv[2];
const body = fs.readFileSync(path.join(SP, 'montaj-rehberi.html'), 'utf8');
fs.writeFileSync(path.join(SP, 't/index.html'), `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0}[hidden]{display:none!important}</style></head><body>${body}</body></html>`);
(async () => { const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  for (const [w, h, ad] of [[390, 844, 'tel']]) {
    const p = await (await b.newContext({ viewport: { width: w, height: h } })).newPage(); const e = []; p.on('pageerror', x => e.push(x.message));
    await p.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => r.fulfill({ path: path.join(SP, 't/node_modules/three', r.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', '')), contentType: 'application/javascript' }));
    await p.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
    await p.goto('file://' + path.join(SP, 't/index.html'), { waitUntil: 'domcontentloaded', timeout: 90000 }); await p.waitForTimeout(1500);
    await p.click('#galTog'); await p.waitForTimeout(600); await p.keyboard.press('ArrowRight'); await p.waitForTimeout(500);
    await p.screenshot({ path: path.join(SP, `t/gal-${ad}.png`) });
    const ok = await p.evaluate(() => [...document.querySelectorAll('#galThumbs img')].map(i => i.complete && i.naturalWidth > 0));
    await p.keyboard.press('Escape'); const kapali = await p.evaluate(() => document.getElementById('gal').hidden);
    console.log(ad, 'hata', e, 'resimler', ok.join(','), 'esc kapatti', kapali);
  }
  await b.close(); })();
