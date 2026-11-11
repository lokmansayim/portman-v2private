// Rehberde bir yerden bakınca hangi parça görünür: dikdörtgen bir pencereden paralel ışınlar atılır, her ışının ilk çarptığı parça sayılır.
// Kampanyalı evin cumba köşesi için yazıldı (Lokman, 11.11.2026 08:52 UTC: "tam arkadan bakınca baş makas omegası ve cumba makası
// görünmeyecek"). Pencere dünya koordinatındadır (m): `bas` köşesi, `u` ve `v` kenarları, `nu` × `nv` ışın, `yon` bakış yönü.
// Parçaların arka yüzleri de sayılır (iki yüzlü). Sonuç: ilk çarpılan parçaya göre ışın sayısı ("ad · bu"), boşa gidenler "", bir parçanın
// içinden başlayanlar "(parçanın içinden)". İstekte `dahil` (düzenli ifade) varsa yalnız adı ("ad · bu") ona uyan parçalar sayılır,
// öteki parçalar yokmuş gibi (saçak sacının kıvrımı ile son aşık, 11.11.2026: kaplama kaldırılmış hâlde hangisi üstte).
//   THREE_DIR=<three@0.160.0 klasörü> node bakis.js <rehber.html> <istek.json> <sonuc.json>
//   istek: {"bas": [x, y, z], "u": [x, y, z], "v": [x, y, z], "nu": 60, "nv": 24, "yon": [x, y, z], "dahil": "Aşık|Saçak sacı"}
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [html, istek, out] = process.argv.slice(2);
  const q = JSON.parse(fs.readFileSync(istek, 'utf8'));
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'], env: { ...process.env, TMPDIR: '/tmp' } });
  const p = await b.newPage({ viewport: { width: 1200, height: 800 } });
  const T = process.env.THREE_DIR;
  await p.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => r.fulfill({ path: T + '/' + r.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', ''), contentType: 'application/javascript' }));
  await p.route('https://fonts.googleapis.com/**', r => r.fulfill({ body: '', contentType: 'text/css' }));
  const hatalar = [];
  p.on('pageerror', e => hatalar.push(String(e)));
  await p.goto('file://' + html);
  await p.waitForFunction(() => window.__montaj, null, { timeout: 60000 });
  const sonuc = await p.evaluate(q => {
    const M = window.__montaj, THREE = M.THREE, V = a => new THREE.Vector3(...a);
    const meshler = [], ad = new Map(), D = q.dahil ? new RegExp(q.dahil) : null;
    M.parts.forEach(pt => {
      pt.obj.updateWorldMatrix(true, true);
      const info = pt.obj.userData.info || {}, bu = ((info.satir || []).find(r => r[0] === 'Bu parça') || [, ''])[1];
      if (D && !D.test(`${info.ad} · ${bu}`)) return;
      pt.obj.traverse(m => { if (m.isMesh) { meshler.push(m); ad.set(m, `${info.ad} · ${bu}`); (Array.isArray(m.material) ? m.material : [m.material]).forEach(x => { x.side = THREE.DoubleSide; }); } });
    });
    const rc = new THREE.Raycaster(), bas = V(q.bas), u = V(q.u), v = V(q.v), yon = V(q.yon).normalize(), ilk = {};
    for (let i = 0; i < q.nu; i++) for (let j = 0; j < q.nv; j++) {
      const o = bas.clone().addScaledVector(u, (i + 0.5) / q.nu).addScaledVector(v, (j + 0.5) / q.nv);
      rc.set(o, yon);
      const hs = rc.intersectObjects(meshler, false), say = new Map();
      hs.forEach(h => say.set(h.object, (say.get(h.object) || 0) + 1));
      // Işın bir parçanın içinden başlıyorsa (o parçayla tek sayıda kesişir) bakış değildir: ayrı sayılır.
      const k = [...say.values()].some(n => n % 2) ? '(parçanın içinden)' : hs.length ? ad.get(hs[0].object) : '';
      ilk[k] = (ilk[k] || 0) + 1;
    }
    return { isin: q.nu * q.nv, ilk };
  }, q);
  fs.writeFileSync(out, JSON.stringify({ ...sonuc, hatalar }, null, 1));
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
