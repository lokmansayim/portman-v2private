// Rehberin sahnesini GLB'ye yazar: her parça bir düğüm, extras'ta kart kodu, ad ve adım
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [html, out] = process.argv.slice(2);
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1200, height: 800 } });
  const T = process.env.THREE_DIR;
  await p.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => r.fulfill({ path: T + '/' + r.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', ''), contentType: 'application/javascript' }));
  await p.route('https://fonts.googleapis.com/**', r => r.fulfill({ body: '', contentType: 'text/css' }));
  await p.goto('file://' + html);
  await p.waitForFunction(() => window.__montaj, null, { timeout: 60000 });
  const b64 = await p.evaluate(async () => {
    const M = window.__montaj, THREE = M.THREE;
    M.goTo(0, false);
    const { GLTFExporter } = await import('https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/exporters/GLTFExporter.js');
    const root = new THREE.Group(); root.name = JSON.parse(document.getElementById('pafta').textContent).kod;
    const adimlar = M.STEPS.map(s => s.name);
    const grup = adimlar.map((ad, i) => { const g = new THREE.Group(); g.name = String(i).padStart(2, '0') + ' ' + ad; root.add(g); return g; });
    M.parts.forEach(pt => {
      // parçanın yerindeki yüksekliği (`pt.y`; sahnede düşme animasyonu bunun üstünden oynar). Eskiden 0'a çekiliyordu: kökü yüksekte
      // duran parçalar (TK-01'de veranda kirişleri, tavan omegaları ve H'lar, alçıpan, cam yünü, aşıklar, çatı kaplaması) GLB'de yere düşüyordu.
      const o = pt.obj.clone(true); o.visible = true; o.position.y = pt.y;
      const gecici = []; o.traverse(c => { if (c.userData && c.userData.gecici) gecici.push(c); });   // serilirken görünen rulo
      gecici.forEach(c => c.parent && c.parent.remove(c));
      const i = pt.obj.userData.info || {};
      o.name = (i.kod ? i.kod + ' ' : '') + (i.ad || '');
      o.userData = { kod: i.kod || null, ad: i.ad || null, adim: pt.step, adim_adi: adimlar[pt.step] };
      o.traverse(m => { if (m.isMesh) { m.material = m.material.clone(); m.material.emissiveIntensity = 0; } });
      grup[pt.step].add(o);
    });
    // temel plak (sahnenin `concrete` kutusu, adım değil): render onu GLB'den alır, ölçüsü ikinci kez yazılmaz
    let sahne = M.parts[0].obj; while (sahne.parent) sahne = sahne.parent;
    sahne.children.filter(c => c.isMesh && c.material && c.material.name === 'concrete').forEach(c => { const z = c.clone(); z.name = 'Temel plak'; root.add(z); });
    const ab = await new GLTFExporter().parseAsync(root, { binary: true, onlyVisible: false });
    let s = ''; const u = new Uint8Array(ab); for (let k = 0; k < u.length; k += 0x8000) s += String.fromCharCode.apply(null, u.subarray(k, k + 0x8000));
    return btoa(s);
  });
  fs.writeFileSync(out, Buffer.from(b64, 'base64'));
  console.log(out, fs.statSync(out).size);
  await b.close();
})();
