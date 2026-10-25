const { chromium } = require('playwright'); const fs = require('fs'), path = require('path'); const SP = process.argv[2];
const body = fs.readFileSync(path.join(SP, 'montaj-rehberi.html'), 'utf8');
fs.writeFileSync(path.join(SP, 't/index.html'), `<!doctype html><html><head><meta charset="utf-8"></head><body>${body}</body></html>`);
(async () => { const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await (await b.newContext()).newPage(); const e = []; p.on('pageerror', x => e.push(x.message + ' ' + (x.stack||'').split('\n').slice(0,3).join(' | ')));
  await p.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => r.fulfill({ path: path.join(SP, 't/node_modules/three', r.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', '')), contentType: 'application/javascript' }));
  await p.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await p.goto('file://' + path.join(SP, 't/index.html')); await p.waitForTimeout(1500); console.log(e); await b.close(); })();
