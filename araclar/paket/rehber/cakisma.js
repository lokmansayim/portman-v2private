// Rehberde kalkan kenarının parçaları başka bir parçanın içine giriyor mu (Lokman, 9.11.2026: "çakışma olmasın tam değme olsun").
// Baş makas Z'si, alın sacı ve C kapamanın her kutusunun içinden noktalar alınır (yüzlerinden 0,1 mm içeride); nokta başka bir parçanın
// içindeyse çakışmadır. Değen yüzler çakışma sayılmaz. Kutu dışındaki parçalarda içerisi ışın sayımıyla (iki yön) bulunur.
//   THREE_DIR=<three@0.160.0 klasörü> node cakisma.js <rehber.html> <cakisma.json>
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [html, out] = process.argv.slice(2);
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'], env: { ...process.env, TMPDIR: '/tmp' } });
  const p = await b.newPage({ viewport: { width: 1200, height: 800 } });
  const T = process.env.THREE_DIR;
  await p.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => r.fulfill({ path: T + '/' + r.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', ''), contentType: 'application/javascript' }));
  await p.route('https://fonts.googleapis.com/**', r => r.fulfill({ body: '', contentType: 'text/css' }));
  const hatalar = [];
  p.on('pageerror', e => hatalar.push(String(e)));
  await p.goto('file://' + html);
  await p.waitForFunction(() => window.__montaj, null, { timeout: 60000 });
  const sonuc = await p.evaluate(() => {
    const M = window.__montaj, THREE = M.THREE;
    const HEDEF = ["Baş makas Z'si", 'Alın sacı', 'C kapama'];
    const EPS = 1e-4, ADIM = 0.02;   // m: yüzden içeri 0,1 mm; uzun kenarda 2 cm arayla nokta
    const meshler = pt => { const a = []; pt.obj.updateWorldMatrix(true, true); pt.obj.traverse(m => { if (m.isMesh) a.push(m); }); return a; };
    const kutuMu = m => m.geometry.type === 'BoxGeometry', k8Mu = m => !!m.geometry.userData.k8;
    const noktalar = m => {   // kutunun (ya da altı yüzlü parçanın) içinden noktalar (dünya)
      if (k8Mu(m)) {   // köşeler: 0..3 bir uçtaki kesit (sırayla), 4..7 öteki uç; iç noktalar köşelerden doğrusal
        const v = m.geometry.userData.k8.map(a => new THREE.Vector3(...a)), out = [];
        const say = L => Math.min(Math.max(1, Math.ceil(L / ADIM)) + 1, 400), ic = (k, L, i) => (k === 1 ? 0.5 : EPS / L + (1 - 2 * EPS / L) * i / (k - 1));
        const [Lx, La, Lb] = [v[0].distanceTo(v[4]), v[0].distanceTo(v[1]), v[0].distanceTo(v[3])], [nx, na, nb] = [say(Lx), say(La), say(Lb)];
        for (let i = 0; i < nx; i++) for (let j = 0; j < na; j++) for (let k = 0; k < nb; k++) {
          const x = ic(nx, Lx, i), a = ic(na, La, j), b = ic(nb, Lb, k), q = new THREE.Vector3();
          [[0, (1 - a) * (1 - b)], [1, a * (1 - b)], [2, a * b], [3, (1 - a) * b]].forEach(([c, wgt]) => { q.addScaledVector(v[c], (1 - x) * wgt); q.addScaledVector(v[c + 4], x * wgt); });
          out.push(q.applyMatrix4(m.matrixWorld));
        }
        return out;
      }
      const { width: w, height: h, depth: d } = m.geometry.parameters, n = x => Math.max(1, Math.ceil(x / ADIM)), out = [];
      const ek = (L, k, i) => (k === 1 ? 0 : -L / 2 + EPS + (L - 2 * EPS) * i / (k - 1));
      const [nx, ny, nz] = [n(w), n(h), n(d)].map(k => Math.min(k + 1, 400));
      for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) for (let k = 0; k < nz; k++)
        out.push(new THREE.Vector3(ek(w, nx, i), ek(h, ny, j), ek(d, nz, k)).applyMatrix4(m.matrixWorld));
      return out;
    };
    const tum = M.parts.map((pt, i) => ({ i, ad: pt.obj.userData.info.ad, adim: pt.step, bu: ((pt.obj.userData.info.satir || []).find(r => r[0] === 'Bu parça') || [, ''])[1], m: meshler(pt) }));
    tum.forEach(t => { t.kutu = new THREE.Box3(); t.m.forEach(m => t.kutu.expandByObject(m)); });
    const inv = new THREE.Matrix4(), v = new THREE.Vector3(), rc = new THREE.Raycaster();
    const yonler = [new THREE.Vector3(0.123, 0.981, 0.147).normalize(), new THREE.Vector3(-0.71, 0.13, 0.69).normalize()];
    const icinde = (m, q) => {
      if (kutuMu(m)) {
        const { width: w, height: h, depth: d } = m.geometry.parameters;
        inv.copy(m.matrixWorld).invert(); v.copy(q).applyMatrix4(inv);
        return Math.abs(v.x) < w / 2 && Math.abs(v.y) < h / 2 && Math.abs(v.z) < d / 2;
      }
      const yan = m.material.side; m.material.side = THREE.DoubleSide;
      const tek = yonler.every(y => { rc.set(q, y); return rc.intersectObject(m, false).length % 2 === 1; });
      m.material.side = yan; return tek;
    };
    const rapor = [];
    tum.filter(t => HEDEF.includes(t.ad)).forEach(t => {
      const kom = tum.filter(o => o !== t && o.kutu.intersectsBox(t.kutu));
      const say = {};
      let n = 0;
      const yer = {}, gi = new THREE.Matrix4(), lq = new THREE.Vector3();
      t.m.forEach(m => { if (!kutuMu(m) && !k8Mu(m)) return; gi.copy(m.parent.matrixWorld).invert(); noktalar(m).forEach(q => { n++; kom.forEach(o => { if (!o.kutu.containsPoint(q)) return; if (o.m.some(om => icinde(om, q))) {
        const k = `${o.ad} · adım ${o.adim + 1} · ${o.bu}`; say[k] = (say[k] || 0) + 1;
        lq.copy(q).applyMatrix4(gi).multiplyScalar(100); const y = yer[k] || (yer[k] = [[1e9, -1e9], [1e9, -1e9], [1e9, -1e9]]);   // parçanın grubunda (cm): x eğik boyunca, y eğime dik, z dışa
        [lq.x, lq.y, lq.z].forEach((c, j) => { y[j][0] = Math.min(y[j][0], Math.round(c * 100) / 100); y[j][1] = Math.max(y[j][1], Math.round(c * 100) / 100); });
      } }); }); });
      rapor.push({ ad: t.ad, bu: t.bu, adim: t.adim + 1, sira: t.i, nokta: n, cakisan: say, yer });
    });
    return rapor;
  });
  fs.writeFileSync(out, JSON.stringify({ parcalar: sonuc, hatalar }, null, 1));
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
