// İE-21 · telefon öykünmesi (iPhone 13, dokunma olayları): aç, tek parmakla çevir, iki parmakla yaklaştır, çatıyı aç, üstten, odaya dokun.
// node telefon.js <url> <ad> [dizin]   (PM_YEREL=1: yerel nginx'in kendi imzalı sertifikası kabul edilir, ör. https://127.0.0.1/3d/<anahtar>/)
const { chromium, devices } = require('playwright');
(async () => {
  const [url, ad, dizin] = [process.argv[2], process.argv[3], process.argv[4] || '.'];
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const ctx = await b.newContext({ ...devices['iPhone 13'], ignoreHTTPSErrors: !!process.env.PM_YEREL });   // yerel sınamada kendi imzalı sertifika
  const p = await ctx.newPage(); const hatalar = [];
  p.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') hatalar.push(m.type() + ': ' + m.text()); });
  p.on('pageerror', e => hatalar.push('pageerror: ' + e.message));
  const yanit = await p.goto(url); await p.waitForTimeout(1500);
  const kare = async (n) => { const x = await p.screenshot({ path: `${dizin}/${ad}_${n}.png` }); return x.toString('base64'); };
  const k0 = await kare('1_acilis');
  const cdp = await ctx.newCDPSession(p);
  const T = (type, pts) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: pts });
  await T('touchStart', [{ x: 120, y: 450 }]); for (let i = 1; i <= 12; i++) await T('touchMove', [{ x: 120 + i * 14, y: 450 }]); await T('touchEnd', []);
  await p.waitForTimeout(900); const k1 = await kare('2_cevrildi');
  await T('touchStart', [{ x: 175, y: 450, id: 0 }, { x: 215, y: 450, id: 1 }]);
  for (let i = 1; i <= 8; i++) await T('touchMove', [{ x: 175 - i * 6, y: 450, id: 0 }, { x: 215 + i * 6, y: 450, id: 1 }]); await T('touchEnd', []);
  await p.waitForTimeout(900); const k2 = await kare('3_yaklasti');
  await p.tap('#dis'); await p.tap('#cati'); await p.waitForTimeout(600); await kare('4_cati_acik');
  await p.tap('#ust'); await p.waitForTimeout(600); await kare('5_ustten');
  // üstten görünümde ortadaki odaya dokun
  await p.touchscreen.tap(195, 430); await p.waitForTimeout(300); const secim = await p.textContent('#s');
  await kare('6_oda');
  const ust = await p.evaluate(() => { const u = document.getElementById('u').getBoundingClientRect(), b = document.getElementById('b').getBoundingClientRect(); return { bilgi_alt: Math.round(u.bottom), dugme_ust: Math.round(b.top), dugmeler: [...document.querySelectorAll('#b button')].map(x => [x.textContent, Math.round(x.getBoundingClientRect().height)]) }; });
  console.log(JSON.stringify({ ad, http: yanit.status(), csp: !!yanit.headers()['content-security-policy'], cevrildi: k0 !== k1, yaklasti: k1 !== k2, secim, ...ust, hatalar }));
  await b.close();
})();
