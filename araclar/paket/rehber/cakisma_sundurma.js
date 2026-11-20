// Rehberde sundurmanın parçaları (panel, sac, Z damlalık, mastik, saçak sacı, kapama) başka bir parçanın içine giriyor mu (Lokman,
// 20.11.2026 22:59: "hiç bir zaman kesişme olmasın"). Sundurma adımındaki her parçanın kenarlarından 2 cm arayla noktalar alınır; nokta başka
// bir parçanın içindeyse (altı yönde ışın sayımı, yüzden en az 0,5 mm içeride) çakışmadır. Ters yön de bakılır: öteki parçaların noktaları
// sundurma parçalarının içinde mi. Değen yüzler çakışma sayılmaz.
//   THREE_DIR=<three@0.160.0 klasörü> node cakisma_sundurma.js <rehber.html> <cakisma.json>
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [html, out] = process.argv.slice(2);
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'], env: { ...process.env, TMPDIR: '/tmp' } });
  const p = await b.newPage({ viewport: { width: 800, height: 600 } });
  const T = process.env.THREE_DIR;
  await p.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => r.fulfill({ path: T + '/' + r.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', ''), contentType: 'application/javascript' }));
  await p.route('https://fonts.googleapis.com/**', r => r.fulfill({ body: '', contentType: 'text/css' }));
  const hatalar = [];
  p.on('pageerror', e => hatalar.push(String(e)));
  await p.goto('file://' + html);
  await p.waitForFunction(() => window.__montaj, null, { timeout: 60000 });
  const sonuc = await p.evaluate(() => {
    const M = window.__montaj, T3 = M.THREE; M.goTo(0, false);
    const ad = q => (q.obj.userData.info && q.obj.userData.info.ad) || '?';
    const z = M.parts.find(q => ad(q) === 'Z damlalık');
    if (!z) return { parcalar: [], cakisma: [] };
    const su = z.step, L = [];
    for (const q of M.parts) { q.obj.updateMatrixWorld(true); q.obj.traverse(o => { if (o.isMesh) { o.material.side = T3.DoubleSide; L.push({ o, q, box: new T3.Box3().setFromObject(o) }); } }); }
    const S = L.filter(e => e.q.step === su);
    const ray = new T3.Raycaster(), dirs = [[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]].map(d => new T3.Vector3(...d));
    const icinde = (pt, o) => { let tek = 0, en = 1e9; for (const d of dirs) { ray.set(pt, d); const u = []; ray.intersectObject(o, false).forEach(x => { if (!u.some(y => Math.abs(y - x.distance) < 1e-6)) u.push(x.distance); }); if (u.length % 2) tek++; if (u.length) en = Math.min(en, u[0]); } return tek >= 5 && en > 0.0005; };
    const noktalar = o => { const P = o.geometry.attributes.position, I = o.geometry.index, v = [], out = [];
      for (let i = 0; i < P.count; i++) v.push(new T3.Vector3().fromBufferAttribute(P, i).applyMatrix4(o.matrixWorld));
      const t = I ? I.array : [...Array(P.count).keys()];
      for (let k = 0; k < t.length; k += 3) for (const [i, j] of [[0,1],[1,2],[2,0]]) { const A = v[t[k+i]], B = v[t[k+j]], n = Math.max(1, Math.ceil(A.distanceTo(B) / 0.02)); for (let s = 0; s <= n; s++) out.push(A.clone().lerp(B, s / n)); }
      return out; };
    const cakisma = {}, say = {};
    const bak = (a, c, yon) => { const ib = a.box.clone().intersect(c.box); if (ib.isEmpty()) return; const s = ib.getSize(new T3.Vector3()); if (Math.min(s.x, s.y, s.z) < 0.0005) return;
      let n = 0, ilk = null; for (const pt of noktalar(a.o)) if (ib.containsPoint(pt) && icinde(pt, c.o)) { n++; ilk = ilk || pt; }
      if (n) { const k = `${ad(a.q)} → ${ad(c.q)}${yon}`; cakisma[k] = cakisma[k] || { nokta: 0, yer: [+(ilk.x * 100).toFixed(1), +(ilk.y * 100).toFixed(1), +(ilk.z * 100).toFixed(1)] }; cakisma[k].nokta += n; } };
    for (const a of S) { say[ad(a.q)] = (say[ad(a.q)] || 0) + 1; for (const c of L) { if (c.q === a.q) continue; bak(a, c, ''); if (c.q.step !== su) bak(c, a, ' (ters)'); } }
    return { parcalar: say, cakisma: Object.entries(cakisma).map(([k, v]) => ({ cift: k, ...v })) };
  });
  fs.writeFileSync(out, JSON.stringify({ hatalar, ...sonuc }, null, 1));
  await b.close();
})();
