// Rehberin seçilen adımlarının ekran görüntüsü (görsel kontrol): THREE_DIR=<three@0.160.0> node shot.js <rehber.html> <klasör> "0;2;10" [en] [boy]
const { chromium } = require('playwright');
(async () => {
  const [html, dir, steps, w, h] = process.argv.slice(2);
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: +(w || 1440), height: +(h || 900) } });
  const errs = [];
  const T = process.env.THREE_DIR;
  await p.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => {
    const u = r.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', '');
    r.fulfill({ path: T + '/' + u, contentType: 'application/javascript' });
  });
  await p.route('https://fonts.googleapis.com/**', r => r.fulfill({ body: '', contentType: 'text/css' }));
  p.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errs.push(m.type() + ': ' + m.text()); });
  p.on('pageerror', e => errs.push('pageerror: ' + e.message));
  await p.goto('file://' + html);
  await p.waitForFunction(() => window.__montaj, null, { timeout: 60000 });
  for (const s of steps.split(';')) {
    await p.evaluate(s => window.__montaj.goTo(+s, false), s);
    await p.waitForTimeout(1800);
    await p.screenshot({ path: `${dir}/adim_${String(s).padStart(2, '0')}.png` });
  }
  console.log(JSON.stringify(errs.slice(0, 20)));
  await b.close();
})();
