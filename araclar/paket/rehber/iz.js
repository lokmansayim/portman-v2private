// Rehber sayfasının izi: her parçanın adımı, sırası, kimlik kartı ve geometrisi (dünya koordinatında köşeler, 0,1 mm'ye yuvarlak,
// malzemeyle birlikte FNV-1a), adımların metni ve satırları, kamera ve rozetler. Şablonun 62 m² rehberini aynen verdiğini sınar.
//   THREE_DIR=<three@0.160.0 klasörü> node iz.js <rehber.html> <iz.json>
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [html, out] = process.argv.slice(2);
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1200, height: 800 } });
  const T = process.env.THREE_DIR;
  await p.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => r.fulfill({ path: T + '/' + r.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', ''), contentType: 'application/javascript' }));
  await p.route('https://fonts.googleapis.com/**', r => r.fulfill({ body: '', contentType: 'text/css' }));
  const hatalar = [], kayit = [];
  p.on('pageerror', e => hatalar.push(String(e)));
  // Sayfa açılamazsa nedeni görünsün (CI'da "Page crashed"): çökme ve konsoldaki hata ve uyarılar stderr'e, iz.py hatayla birlikte gösterir
  p.on('crash', () => kayit.push('sayfa çöktü'));
  p.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') kayit.push(`konsol ${m.type()}: ${m.text()}`); });
  try {
    await p.goto('file://' + html);
    await p.waitForFunction(() => window.__montaj, null, { timeout: 60000 });
  } catch (e) {
    console.error(kayit.concat(hatalar).join('\n'));
    throw e;
  }
  const iz = await p.evaluate(() => {
    const M = window.__montaj, THREE = M.THREE, $ = id => document.getElementById(id);
    M.goTo(0, false);
    const fnv = (h, n) => { h ^= n & 0xffff; h = Math.imul(h, 16777619) >>> 0; h ^= (n >>> 16) & 0xffff; return Math.imul(h, 16777619) >>> 0; };
    const fnvS = (h, s) => { for (let i = 0; i < s.length; i++) h = fnv(h, s.charCodeAt(i)); return h; };
    const v = new THREE.Vector3();
    const geo = o => {
      o.updateWorldMatrix(true, true);
      let h = 2166136261, n = 0;
      o.traverse(m => {
        if (!m.isMesh) return;
        h = fnvS(h, (m.material && m.material.name) || '');
        h = fnv(h, m.visible ? 1 : 0);
        const a = m.geometry.attributes.position;
        for (let i = 0; i < a.count; i++) { v.fromBufferAttribute(a, i).applyMatrix4(m.matrixWorld); h = fnv(h, Math.round(v.x * 1e4)); h = fnv(h, Math.round(v.y * 1e4)); h = fnv(h, Math.round(v.z * 1e4)); n++; }
      });
      return [h.toString(16), n];
    };
    const parts = M.parts.map(pt => {
      const i = pt.obj.userData.info, [h, n] = geo(pt.obj);
      return { s: pt.step, o: Math.round(pt.order * 1e6) / 1e6, kod: i.kod || null, ad: i.ad, satir: i.satir.filter(r => r && r[1]), anim: pt.anim ? Object.keys(pt.anim).sort() : [], geo: h, n };
    });
    const adimlar = M.STEPS.map((st, i) => {
      M.goTo(i, false);
      const pr = M.preset(i, 1.6), r = x => Math.round(x * 1e4) / 1e4;
      return { i, eyebrow: $('eyebrow').textContent, t: $('stepTitle').textContent, p: $('stepText').textContent, head: $('partsHead').textContent,
        satirlar: $('stepParts').innerHTML, rozet: [$('badgeNo').textContent, $('badgeTitle').textContent],
        kamera: [pr.pos.toArray().map(r), pr.target.toArray().map(r)], gorunen: M.parts.filter(q => q.obj.parent.visible).length };
    });
    return { N: M.N, liste: $('stepList').innerHTML, ilerleme: $('progress').innerHTML, parca: parts.length, parts, adimlar };
  });
  iz.hatalar = hatalar;
  fs.writeFileSync(out, JSON.stringify(iz, null, 0));
  console.log(out, 'parça', iz.parca, 'adım', iz.adimlar.length, 'hata', hatalar.length);
  await b.close();
})();
