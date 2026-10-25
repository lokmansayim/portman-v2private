// Rehberin 3B modelini GLB'ye aktarır: düğüm adları s{adım}_{sıra}, malzeme adları rehberdeki anahtar (render betikleri bunlardan tanır)
// Kullanım: node export.js <rehber.html> <çıktı.glb>
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const [html, out] = process.argv.slice(2), NM = path.join(__dirname, 'node_modules/three');
const tmp = path.join(path.dirname(html), '_export.html');
fs.writeFileSync(tmp, `<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0}</style></head><body>${fs.readFileSync(html, 'utf8')}</body></html>`);
(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await (await browser.newContext({ viewport: { width: 1000, height: 700 } })).newPage();
  const errs = []; page.on('pageerror', e => errs.push(e.message));
  await page.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => r.fulfill({ path: path.join(NM, r.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', '')), contentType: 'application/javascript' }));
  await page.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await page.goto('file://' + tmp, { waitUntil: 'domcontentloaded', timeout: 90000 }); await page.waitForTimeout(2500);
  const r = JSON.parse(await page.evaluate(async () => {
    const M = window.__montaj, T = M.THREE; M.goTo(M.N, false);
    const root = new T.Group(); const adlar = new Set();
    M.parts.forEach((p, i) => {
      p.obj.visible = true; p.obj.position.y = p.y;
      if (p.anim && p.anim.swing) p.obj.rotation.y = p.anim.swing[1];
      const c = p.obj.clone(true); c.name = `s${p.step}_${i}`;
      const gec = []; c.traverse(o => { if (o.userData && o.userData.gecici) gec.push(o); }); gec.forEach(o => o.parent && o.parent.remove(o));   // serme rulosu gibi geçici parçalar modele girmez
      c.traverse(o => { o.visible = true; if (o.isMesh) { const m = o.material.clone(); m.emissiveIntensity = 0; m.emissive.set(0); m.name = o.material.name; adlar.add(m.name); o.material = m; } });
      c.updateMatrix(); root.add(c);
    });
    const { GLTFExporter } = await import('three/addons/exporters/GLTFExporter.js');
    const buf = await new GLTFExporter().parseAsync(root, { binary: true });
    const u = new Uint8Array(buf); let s = ''; for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000));
    const kam = Array.from({ length: M.N + 1 }, (_, i) => { const p = M.preset(i, 1.6); return { pos: p.pos.toArray(), hedef: p.target.toArray() }; });
    return JSON.stringify({ n: M.parts.length, adlar: [...adlar], kam, data: btoa(s) });
  }));
  fs.writeFileSync(out, Buffer.from(r.data, 'base64')); fs.writeFileSync(out.replace(/\.glb$/, '_kamera.json'), JSON.stringify(r.kam));
  console.log('parça', r.n, 'malzemeler', r.adlar.join(','), 'hata', errs, (fs.statSync(out).size / 1e6).toFixed(1) + ' MB');
  await browser.close();
})();
