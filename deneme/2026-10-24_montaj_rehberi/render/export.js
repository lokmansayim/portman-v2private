const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'); const SP = process.argv[2];
const body = fs.readFileSync(path.join(SP, 'montaj-rehberi.html'), 'utf8');
fs.writeFileSync(path.join(SP, 't/index.html'), `<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0}</style></head><body>${body}</body></html>`);
(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await (await browser.newContext({ viewport: { width: 1000, height: 700 } })).newPage();
  const errs = []; page.on('pageerror', e => errs.push(e.message));
  await page.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', route => route.fulfill({ path: path.join(SP, 't/node_modules/three', route.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', '')), contentType: 'application/javascript' }));
  await page.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await page.goto('file://' + path.join(SP, 't/index.html')); await page.waitForTimeout(1500);
  const b64 = await page.evaluate(async () => {
    const M = window.__montaj, T = M.THREE;
    M.goTo(17, true);
    const BASE = { concrete: 0xb7babc, frame: 0x98a2aa, pdis: 0xeceae3, pic: 0xe2ded6, eps: 0xf6f4ef, dubel: 0x7d878f, steel: 0xa9b3bb, post: 0x87929b, box: 0x6f7a83, kasa: 0xf4f3ef, door: 0xd6c6aa, pvc: 0xf7f7f5, glass: 0x9cc3dc, cdoor: 0x3e464e, truss: 0xb3bcc3, betopan: 0xc6c9c8, tomega: 0x9fb0bc, asik: 0xbac3ca, roof: 0x4b535b, ridge: 0x3f464d, trim: 0x474f57, gutter: 0xb4bcc2 };
    const byHex = {}; for (const [k, v] of Object.entries(BASE)) byHex[new T.Color(v).getHex()] = k;
    const root = new T.Group(); const bilinmeyen = new Set();
    M.parts.forEach((p, i) => {
      p.obj.visible = true; p.obj.position.y = p.y;
      if (p.anim && p.anim.swing) p.obj.rotation.y = p.anim.swing[1];
      const c = p.obj.clone(true); c.name = `s${p.step}_${i}`;
      c.traverse(o => { o.visible = true; if (o.isMesh) { const m = o.material.clone(); m.emissiveIntensity = 0; m.emissive.set(0); const k = byHex[m.color.getHex()]; if (!k) bilinmeyen.add(m.color.getHexString()); m.name = k || ('x' + m.color.getHexString()); o.material = m; } });
      c.updateMatrix(); root.add(c);
    });
    const { GLTFExporter } = await import('three/addons/exporters/GLTFExporter.js');
    const buf = await new GLTFExporter().parseAsync(root, { binary: true });
    const u = new Uint8Array(buf); let s = ''; for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000));
    return JSON.stringify({ n: M.parts.length, bilinmeyen: [...bilinmeyen], data: btoa(s) });
  });
  const r = JSON.parse(b64);
  fs.writeFileSync(path.join(SP, 'render/huma.glb'), Buffer.from(r.data, 'base64'));
  console.log('parca', r.n, 'bilinmeyen renk', r.bilinmeyen, 'hata', errs);
  await browser.close();
})();
