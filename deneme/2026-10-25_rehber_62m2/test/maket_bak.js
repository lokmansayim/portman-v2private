const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
const [klasor, out] = process.argv.slice(2), NM = path.join(__dirname, 'node_modules/three');
const g = fs.readFileSync(path.join(klasor, (process.argv[4] || 'maket62') + '_maket_1-50_govde.stl')).toString('base64'), c = fs.readFileSync(path.join(klasor, (process.argv[4] || 'maket62') + '_maket_1-50_cati.stl')).toString('base64');
const html = `<!doctype html><html><body style="margin:0;background:#e8ecef"><script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
<script type="module">
import * as THREE from 'three'; import { STLLoader } from 'three/addons/loaders/STLLoader.js';
const r = new THREE.WebGLRenderer({ antialias: true }); r.setSize(1400, 700); document.body.appendChild(r.domElement);
const sc = new THREE.Scene(); sc.background = new THREE.Color(0xe8ecef);
sc.add(new THREE.HemisphereLight(0xffffff, 0x8090a0, 1.1)); const d = new THREE.DirectionalLight(0xffffff, 1.6); d.position.set(-120, -200, 260); sc.add(d);
const L = new STLLoader(), b = s => Uint8Array.from(atob(s), ch => ch.charCodeAt(0)).buffer;
const G = L.parse(b('${g}')), C = L.parse(b('${c}'));
[[0, 0], [215, 0]].forEach(([ox, lift], i) => {
  const g1 = new THREE.Mesh(G, new THREE.MeshStandardMaterial({ color: 0xd9d6cf, roughness: 0.8 })); g1.position.set(ox - 92, -75, 0); sc.add(g1);
  const c1 = new THREE.Mesh(C, new THREE.MeshStandardMaterial({ color: 0x4b535b, roughness: 0.6, metalness: 0.2 })); c1.position.set(ox - 92, -75, i ? 45 : 0); sc.add(c1);
});
const cam = new THREE.PerspectiveCamera(30, 2, 1, 5000); cam.up.set(0, 0, 1); cam.position.set(-150, -520, 330); cam.lookAt(105, 0, 30);
r.render(sc, cam); window.bitti = true;
</script></body></html>`;
fs.writeFileSync(path.join(__dirname, '_maket.html'), html);
(async () => {
  const br = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await (await br.newContext({ viewport: { width: 1400, height: 700 } })).newPage(); const e = []; p.on('pageerror', x => e.push(x.message));
  await p.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => r.fulfill({ path: path.join(NM, r.request().url().replace('https://cdn.jsdelivr.net/npm/three@0.160.0/', '')), contentType: 'application/javascript' }));
  await p.goto('file://' + path.join(__dirname, '_maket.html')); await p.waitForFunction(() => window.bitti, null, { timeout: 60000 });
  await p.screenshot({ path: out }); console.log(e); await br.close();
})();
