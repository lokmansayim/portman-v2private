// Montaj sırası hakemi: sırada sonra gelen ve öncekini örten parça (üst), örttüğü parçaların (alt) üstünde mi
// (Lokman, 10.11.2026 20:16: "önce trapez sac ve mahya gelir sonra alın sacı üzerini örter"). Kurallar `kurallar/rehber/montaj_sirasi.json`'da;
// adımlar ve parçalar `sira.py`'den çözülmüş gelir. Üst parçanın içinden noktalar alınır (yüzlerinden 0,1 mm içeride, 2 cm arayla; `cakisma.js`
// gibi). Her noktadan çatı yüzüne dik doğrultuda (parçanın eğimle dönen grubunun +y'si) yukarı ışın gider; ışın 50 cm içinde bir alt parçaya
// çarparsa o alt parça üstün üstündedir: bulgu. Değen yüz de bulgudur (alt parça üstün üstüne yaslanmış). Geometriyi değiştirmez, yalnız okur.
//   THREE_DIR=<three@0.160.0 klasörü> node sira.js <rehber.html> <kurallar.json> <sonuc.json>
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [html, kuralYolu, out] = process.argv.slice(2);
  const kurallar = JSON.parse(fs.readFileSync(kuralYolu, 'utf8'));
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'], env: { ...process.env, TMPDIR: '/tmp' } });
  const p = await b.newPage({ viewport: { width: 1200, height: 800 } });
  const T = process.env.THREE_DIR;
  await p.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => r.fulfill({ path: T + '/' + r.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', ''), contentType: 'application/javascript' }));
  await p.route('https://fonts.googleapis.com/**', r => r.fulfill({ body: '', contentType: 'text/css' }));
  const hatalar = [];
  p.on('pageerror', e => hatalar.push(String(e)));
  await p.goto('file://' + html);
  await p.waitForFunction(() => window.__montaj, null, { timeout: 60000 });
  const sonuc = await p.evaluate(kurallar => {
    const M = window.__montaj, THREE = M.THREE;
    const EPS = 1e-4, ADIM = 0.02, UZAK = 0.5, ISARET = 40;   // m: yüzden içeri 0,1 mm; 2 cm arayla nokta; ışın 50 cm; bulgu başına en çok 40 işaret noktası
    const ad = pt => pt.obj.userData.info.ad;
    const bu = pt => ((pt.obj.userData.info.satir || []).find(r => r[0] === 'Bu parça') || [, ''])[1];
    const meshler = pt => { const a = []; pt.obj.updateWorldMatrix(true, true); pt.obj.traverse(m => { if (m.isMesh) a.push(m); }); return a; };
    const kutuMu = m => m.geometry.type === 'BoxGeometry', k8Mu = m => !!(m.geometry.userData && m.geometry.userData.k8);
    const noktalar = m => {   // kutunun ya da altı yüzlü parçanın içinden noktalar (dünya); `cakisma.js` ile aynı
      if (k8Mu(m)) {
        const v = m.geometry.userData.k8.map(a => new THREE.Vector3(...a)), o = [];
        const say = L => Math.min(Math.max(1, Math.ceil(L / ADIM)) + 1, 400), ic = (k, L, i) => (k === 1 ? 0.5 : EPS / L + (1 - 2 * EPS / L) * i / (k - 1));
        const [Lx, La, Lb] = [v[0].distanceTo(v[4]), v[0].distanceTo(v[1]), v[0].distanceTo(v[3])], [nx, na, nb] = [say(Lx), say(La), say(Lb)];
        for (let i = 0; i < nx; i++) for (let j = 0; j < na; j++) for (let k = 0; k < nb; k++) {
          const x = ic(nx, Lx, i), a = ic(na, La, j), c = ic(nb, Lb, k), q = new THREE.Vector3();
          [[0, (1 - a) * (1 - c)], [1, a * (1 - c)], [2, a * c], [3, (1 - a) * c]].forEach(([n, w]) => { q.addScaledVector(v[n], (1 - x) * w); q.addScaledVector(v[n + 4], x * w); });
          o.push(q.applyMatrix4(m.matrixWorld));
        }
        return o;
      }
      if (!kutuMu(m)) return [];
      const { width: w, height: h, depth: d } = m.geometry.parameters, n = x => Math.max(1, Math.ceil(x / ADIM)), o = [];
      const ek = (L, k, i) => (k === 1 ? 0 : -L / 2 + EPS + (L - 2 * EPS) * i / (k - 1));
      const [nx, ny, nz] = [n(w), n(h), n(d)].map(k => Math.min(k + 1, 400));
      for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) for (let k = 0; k < nz; k++) o.push(new THREE.Vector3(ek(w, nx, i), ek(h, ny, j), ek(d, nz, k)).applyMatrix4(m.matrixWorld));
      return o;
    };
    // Çatı yüzüne dik doğrultu: parçanın eğimle dönen grubunun (kalkan çerçevesinde z ekseni etrafında) +y'si; dönen grup yoksa düşey
    const normal = pt => {
      let g = null; pt.obj.traverse(o => { if (!g && !o.isMesh && Math.abs(o.rotation.z) > 1e-6) g = o; });
      return g ? new THREE.Vector3(0, 1, 0).transformDirection(g.matrixWorld) : new THREE.Vector3(0, 1, 0);
    };
    const rc = new THREE.Raycaster(); rc.far = UZAK;
    return kurallar.map(K => {
      const ust = M.parts.filter(pt => pt.step === K.ust.adim && ad(pt) === K.ust.ad && (!K.ust.bu_icerir || bu(pt).includes(K.ust.bu_icerir)));
      const alt = M.parts.filter(pt => pt.step === K.alt.adim).map(pt => ({ pt, m: meshler(pt) }));
      const yanlar = new Map();
      alt.forEach(a => { a.kutu = new THREE.Box3(); a.m.forEach(m => { a.kutu.expandByObject(m); const mt = m.material; if (!yanlar.has(mt)) yanlar.set(mt, mt.side); mt.side = THREE.DoubleSide; }); });
      const bulgular = [];
      let nokta = 0;
      ust.forEach(pt => {
        const nrm = normal(pt), kutu = new THREE.Box3(); meshler(pt).forEach(m => kutu.expandByObject(m));
        const aday = alt.filter(a => a.kutu.intersectsBox(kutu.clone().expandByScalar(UZAK)));
        const say = new Map();
        meshler(pt).forEach(m => noktalar(m).forEach(q => {
          nokta++;
          rc.set(q, nrm);
          aday.forEach(a => {
            const h = rc.intersectObjects(a.m, false); if (!h.length) return;
            const k = ad(a.pt) + ' · ' + bu(a.pt), s = say.get(k) || { alt_ad: ad(a.pt), alt_bu: bu(a.pt), alt_adim: a.pt.step + 1, nokta: 0, uzaklik_cm: [1e9, -1e9], isaret: [] };
            s.nokta++; s.uzaklik_cm = [Math.min(s.uzaklik_cm[0], h[0].distance * 100), Math.max(s.uzaklik_cm[1], h[0].distance * 100)];
            if (s.isaret.length < ISARET && s.nokta % 7 === 1) s.isaret.push([q.x, q.y, q.z].map(x => Math.round(x * 1e4) / 1e4));
            say.set(k, s);
          });
        }));
        say.forEach(s => bulgular.push({ ust_bu: bu(pt), ust_adim: pt.step + 1, ...s, uzaklik_cm: s.uzaklik_cm.map(x => Math.round(x * 100) / 100) }));
      });
      yanlar.forEach((s, mt) => { mt.side = s; });
      return { no: K.no, ust_parca: ust.length, alt_parca: alt.length, nokta, bulgular };
    });
  }, kurallar);
  fs.writeFileSync(out, JSON.stringify({ kurallar: sonuc, hatalar }, null, 1));
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
