import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const D = JSON.parse(document.getElementById('pafta').textContent);
const $ = id => document.getElementById(id);
const now = () => performance.now() / 1000;
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const fmt = (n, d = 1) => Number(n).toFixed(d).replace('.', ',');
const fmtc = n => (Math.round(n * 100) / 100).toString().replace('.', ',');

/* Pafta çerçevesi (cm): x sol dış yüzden sağa (0–900), y ön dış yüzden arkaya (0–600; veranda y < 0). Sahne (m): X sağa, Y yukarı, Z öne. */
const X = x => x / 100 - D.dis[0] / 200;
const Z = y => D.dis[1] / 200 - y / 100;
const H = D.h;
const HEEL = 10, CH = 4.5, TB = H + 0.25, SAC = 0.1;   // TB: makas tabanı = duvar üstü + omega + saçak sacı tırnağı
/* Çatı: ana beşik (MKS01–08) y boyunca −30…630, mahya y = 300; cumba (MKS09–10) x boyunca −30…604,75, mahya x = 287,375.
   İki mahya aynı yükseklikte (pafta: kalkanlarda 118,5 cm): ana 108,5 / 330 → 18,2°; cumba 108,5 / 317,375 → 18,9°. */
const AN = { L: -30, R: 630, M: 300, tan: 108.5 / 330 };
const CU = { L: -30, R: 604.75, M: 287.375, tan: 108.5 / 317.375 };
[AN, CU].forEach(R => { R.th = Math.atan(R.tan); R.cos = Math.cos(R.th); R.sin = Math.sin(R.th); R.SL = (R.M - R.L) / R.cos; });
const ysR = (R, s) => TB + HEEL + (s <= R.M ? s - R.L : R.R - s) * R.tan;   // üst başlık dış çizgisi = aşık oturma yüzü (cm)
// Çatı katmanları, aşık oturma yüzünden eğime dik (cm): aşık 3, ters mahya, trapez doğrudan aşıkta (hadve 3,5).
// Bu projede OSB ve nem bariyeri yok (Lokman, 25.10.2026; paftadaki "OSB + nem bariyeri" notu geçersiz).
// Trapez 27/200-6 (Lokman: 100 cm kapatır, 0,5 mm; ölçüler UMS Metal ve Assan Panel 27/200): hadve 27 mm, adım 200 mm, tepe 42 mm, taban 74 mm, 6 hadve
const RIBH = 2.7, RIB_UST = 4.2, RIB_TABAN = 7.4, RIB_KENAR = 4.5;   // RIB_KENAR: kalkan kenarındaki hadvenin ekseni, levha kenarından
const AH = 3.0 + SAC, TM0 = AH + 0.02, TM1 = TM0 + 0.1, TR0 = TM1 + 0.02, TR1 = TR0 + 0.05, PTOP = TR1 + RIBH + 0.1;   // trapez 0,5 mm
// Cephe fugası (pafta: fugalı duvar detayı): alttan 6 × 38 cm betopan + 2 cm fuga, üstte 10 cm bant; oluk 5 mm derin
const FUGA = [38, 78, 118, 158, 198, 238], FUGA_H = 2, FUGA_D = 0.5;
const N = 19;
// 100'lük omegalar (Lokman 25.10.2026): üst 10,5 cm; dış kanat dış duvarın (verandada kirişin) dış yüzüne tam yaslanır,
// içte kalan 5 mm aralığa silikonize mastik (modelde boşluk). Baş makas omegası: derinlik 3 cm, içte 3 cm açık yanak,
// dışta 1 cm U yanak; 8 mm baş makas betopanı U'ya girer ve makasa dayanır.
// Pano: 8 mm betopan + 84 mm strafor (EPS) + 8 mm betopan = 100 mm. H sacı 1,2 mm; kanat uçlarında kıvrım ezildiği için kanat 2 mm (Lokman).
// 100'lük omega 10,5 cm = 2 + 100 + 2 mm H kanadı + 1 mm; dış kanadı H kanadına yaslanır, panonun yüzüyle arasında 2 mm kalır.
const HS = 0.2, OM100 = 10.5, BAS_KANAT = 3, BAS_U = 1, BAS_DUDAK = 2, BET_T = 0.8;
const BAS_DIS = HS + SAC;   // makasın dış yüzü = omeganın dış kanadının dış yüzü (duvar dış yüzünün 3 mm dışında)

/* ---------- Sahne ---------- */
const vp = $('viewport');
let renderer = null;
try { renderer = new THREE.WebGLRenderer({ antialias: true }); }
catch (e) { vp.innerHTML = '<div class="nogl">Bu cihazda 3D görünüm açılamadı (WebGL kapalı). Adımlar ve adetler solda.</div>'; }
const scene = new THREE.Scene();
scene.fog = new THREE.Fog(0xd8dfe4, 34, 85);
const camera = new THREE.PerspectiveCamera(38, 1, 0.05, 200);
let controls = null;
if (renderer) {
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  vp.appendChild(renderer.domElement);
  controls = new OrbitControls(camera, renderer.domElement);
  Object.assign(controls, { enableDamping: true, dampingFactor: 0.08, maxPolarAngle: Math.PI * 0.495, minDistance: 2.5, maxDistance: 45, autoRotateSpeed: 0.7 });
}
scene.add(new THREE.HemisphereLight(0xffffff, 0x7f8a94, 1.05));
const sun = new THREE.DirectionalLight(0xffffff, 1.85);
sun.position.set(6, 13, 9);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -9, right: 9, top: 9, bottom: -9, near: 1, far: 40 });
sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.02;
scene.add(sun);
const groundMat = new THREE.MeshStandardMaterial({ color: 0xc4ccc6, roughness: 1 });
const ground = new THREE.Mesh(new THREE.PlaneGeometry(160, 160), groundMat);
ground.rotation.x = -Math.PI / 2; ground.position.y = -0.1; ground.receiveShadow = true;
scene.add(ground);
function applyTheme() {
  const cs = getComputedStyle(document.documentElement);
  const sc = cs.getPropertyValue('--scene').trim() || '#D8DFE4';
  scene.background = new THREE.Color(sc); scene.fog.color.set(sc);
  groundMat.color.set(cs.getPropertyValue('--ground').trim() || '#C4CCC6');
}
applyTheme();
matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change', applyTheme);
new MutationObserver(applyTheme).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

/* ---------- Malzemeler (render betikleri malzemeyi bu renklerden tanır) ---------- */
const BASE = {
  concrete: { color: 0xb7babc, roughness: 0.95 },
  frame:    { color: 0x98a2aa, roughness: 0.45, metalness: 0.55 },
  pdis:     { color: 0xeceae3, roughness: 0.85 },
  pic:      { color: 0xe2ded6, roughness: 0.9 },
  eps:      { color: 0xf6f4ef, roughness: 0.95 },
  dubel:    { color: 0x7d878f, roughness: 0.45, metalness: 0.6 },
  steel:    { color: 0xa9b3bb, roughness: 0.42, metalness: 0.6 },
  post:     { color: 0x87929b, roughness: 0.45, metalness: 0.6 },
  box:      { color: 0x6f7a83, roughness: 0.45, metalness: 0.55 },
  kasa:     { color: 0xf4f3ef, roughness: 0.6 },
  door:     { color: 0xd6c6aa, roughness: 0.65 },
  pvc:      { color: 0x40474e, roughness: 0.4, metalness: 0.1 },      // antrasit PVC (yükleme listesi)
  glass:    { color: 0x9cc3dc, roughness: 0.05, metalness: 0.1, transparent: true, opacity: 0.38 },
  cdoor:    { color: 0x3e464e, roughness: 0.45, metalness: 0.35 },
  truss:    { color: 0xb3bcc3, roughness: 0.4, metalness: 0.6 },
  betopan:  { color: 0xc6c9c8, roughness: 0.9 },
  tomega:   { color: 0x9fb0bc, roughness: 0.4, metalness: 0.6 },
  asik:     { color: 0xbac3ca, roughness: 0.38, metalness: 0.65 },
  fuga:     { color: 0x7f8486, roughness: 0.95 },
  alcipan:  { color: 0xf2f1ec, roughness: 0.9 },
  alcipan_y:{ color: 0xc3d7bc, roughness: 0.9 },
  boardex:  { color: 0xd7d4cb, roughness: 0.92 },
  izocam:   { color: 0xe3c158, roughness: 1.0 },
  roof:    { color: 0x4b535b, roughness: 0.5, metalness: 0.4 },
  ridge:    { color: 0x3f464d, roughness: 0.5, metalness: 0.45 },
  trim:     { color: 0x474f57, roughness: 0.55, metalness: 0.4 },
  gutter:   { color: 0x3f464e, roughness: 0.45, metalness: 0.4 },
};
const HL = new THREE.Color(0xf0a020);
const matCache = new Map();
const stepMats = Array.from({ length: N + 1 }, () => []);
function mat(key, step) {
  const id = key + '|' + step;
  if (!matCache.has(id)) {
    const m = new THREE.MeshStandardMaterial(BASE[key]); m.name = key;
    m.emissive = HL.clone(); m.emissiveIntensity = 0;
    matCache.set(id, m); stepMats[step].push(m);
  }
  return matCache.get(id);
}

/* ---------- Yardımcılar ---------- */
function mesh(geo, m, shadow = true) { const o = new THREE.Mesh(geo, m); o.castShadow = shadow; o.receiveShadow = true; return o; }
// Paftadaki dikdörtgen (cm) + yükseklik aralığı → kutu
function bp(x0, x1, y0, y1, h0, h1, m) {
  const o = mesh(new THREE.BoxGeometry((x1 - x0) / 100, (h1 - h0) / 100, (y1 - y0) / 100), m);
  o.position.set(X((x0 + x1) / 2), (h0 + h1) / 200, Z((y0 + y1) / 2));
  return o;
}
// Yerel çerçeve: yerel x = u yönü (plan), yerel z = (u.y, −u.x) yönü, y yukarı; O plan noktası (cm)
function cerceve(r, ox, oy) { const g = new THREE.Group(); g.rotation.y = r; g.position.set(X(ox), 0, Z(oy)); return g; }
function lb(s0, s1, h0, h1, z0, z1, m) {   // yerel kutu (cm)
  const o = mesh(new THREE.BoxGeometry(Math.abs(s1 - s0) / 100, Math.abs(h1 - h0) / 100, Math.abs(z1 - z0) / 100), m);
  o.position.set((s0 + s1) / 200, (h0 + h1) / 200, (z0 + z1) / 200); return o;
}
function lc(s1, h1, s2, h2, m, d = CH, w = 8) {   // yerel çubuk, s–h düzleminde (makas)
  const len = Math.hypot(s2 - s1, h2 - h1);
  const o = mesh(new THREE.BoxGeometry(len / 100, d / 100, w / 100), m);
  o.position.set((s1 + s2) / 200, (h1 + h2) / 200, 0); o.rotation.z = Math.atan2(h2 - h1, s2 - s1); return o;
}
// Sac profil kesiti: orta çizgiden kalınlık verilir (cm). Ölçüler Lokman'ın el çizimi, sac 1 mm.
function thick(pts, t) {
  const n = pts.length, A = [], B = [];
  const nrm = (a, b) => { const dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy); return [-dy / l, dx / l]; };
  for (let i = 0; i < n; i++) {
    let v;
    if (i === 0) v = nrm(pts[0], pts[1]); else if (i === n - 1) v = nrm(pts[n - 2], pts[n - 1]);
    else { const a = nrm(pts[i - 1], pts[i]), b = nrm(pts[i], pts[i + 1]); let mx = a[0] + b[0], my = a[1] + b[1]; const ml = Math.hypot(mx, my); mx /= ml; my /= ml; const k = 1 / (mx * a[0] + my * a[1]); v = [mx * k, my * k]; }
    A.push([pts[i][0] + v[0] * t / 2, pts[i][1] + v[1] * t / 2]); B.push([pts[i][0] - v[0] * t / 2, pts[i][1] - v[1] * t / 2]);
  }
  const sh = new THREE.Shape();
  A.concat(B.reverse()).forEach(([u, v], i) => i ? sh.lineTo(u / 100, v / 100) : sh.moveTo(u / 100, v / 100));
  sh.closePath(); return sh;
}
// Aşık: taban 87, gövde dibi 50, üst 35, yükseklik 30 mm; kanatlar makasa oturur
const OMEGA_UP = thick([[-4.35, 0.05], [-2.5, 0.05], [-1.75, 2.95], [1.75, 2.95], [2.5, 0.05], [4.35, 0.05]], SAC);
// Tavan omegası: genişlik 110, üst 65, yükseklik 35 mm; kanatlar makas alt başlığına, şapka aşağı
const OMEGA_DN = thick([[-5.5, -0.05], [-3.25, -0.05], [-3.25, -3.45], [3.25, -3.45], [3.25, -0.05], [5.5, -0.05]], SAC);
function omegaGeo(len, down) { return new THREE.ExtrudeGeometry(down ? OMEGA_DN : OMEGA_UP, { depth: len / 100, bevelEnabled: false }); }
// Çokgen yardımcıları (çatı yüzü yerel s–t düzleminde)
const alan = P => P.reduce((a, p, i) => { const q = P[(i + 1) % P.length]; return a + p[0] * q[1] - q[0] * p[1]; }, 0) / 2;
function kirp(P, C) {   // P'yi dışbükey C ile kırp (C saat yönünün tersine)
  let out = P;
  for (let i = 0; i < C.length && out.length; i++) {
    const a = C[i], b = C[(i + 1) % C.length], inp = out; out = [];
    const f = p => (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]);
    for (let j = 0; j < inp.length; j++) {
      const p = inp[j], q = inp[(j + 1) % inp.length], fp = f(p), fq = f(q);
      if (fp >= -1e-7) out.push(p);
      if ((fp >= -1e-7) !== (fq >= -1e-7)) { const k = fp / (fp - fq); out.push([p[0] + (q[0] - p[0]) * k, p[1] + (q[1] - p[1]) * k]); }
    }
  }
  return out.length >= 3 && Math.abs(alan(out)) > 1 ? out : null;
}
function aralik(P, i, v) {   // çokgenin i. koordinatı = v doğrusundaki öbür koordinat aralığı
  const o = 1 - i, xs = [];
  for (let j = 0; j < P.length; j++) {
    const p = P[j], q = P[(j + 1) % P.length];
    if (p[i] !== q[i] && (p[i] - v) * (q[i] - v) <= 0) xs.push(p[o] + (q[o] - p[o]) * (v - p[i]) / (q[i] - p[i]));
  }
  return xs.length >= 2 ? [Math.min(...xs), Math.max(...xs)] : null;
}
const dikd = (s0, s1, t0, t1) => [[s0, t0], [s1, t0], [s1, t1], [s0, t1]];
const ccw = P => alan(P) < 0 ? P.slice().reverse() : P;
function levha(P, n0, n1, m) {   // s–t çokgeni, eğime dik n0…n1 kalınlığında
  const sh = new THREE.Shape(); P.forEach(([s, t], i) => i ? sh.lineTo(s / 100, t / 100) : sh.moveTo(s / 100, t / 100)); sh.closePath();
  const o = mesh(new THREE.ExtrudeGeometry(sh, { depth: (n1 - n0) / 100, bevelEnabled: false }), m);
  o.rotation.x = Math.PI / 2; o.position.y = n1 / 100; return o;
}

/* ---------- Parçalar ---------- */
const groups = [null];
for (let s = 1; s <= N; s++) { const g = new THREE.Group(); scene.add(g); groups.push(g); }
const parts = [];
function add(step, obj, order, info, anim) {
  obj.userData.info = info;
  groups[step].add(obj);
  parts.push({ obj, step, order, y: obj.position.y, anim });
}
const ROOM = Object.fromEntries(D.rooms.map(r => [r.id, r]));
const roomName = id => ROOM[id] ? ROOM[id].ad : '';
const kart = (kod, ad) => kod ? D.cards[kod].ad : ad;
const kartSat = kod => kod ? [['Kart ölçüsü', D.cards[kod].olcu], ['IFC', D.cards[kod].ifc ? `${D.cards[kod].ifc.sinif} · ${D.cards[kod].ifc.alt_tur}` : '—']] : [];

// Zemin (veranda dahil)
scene.add(bp(-12, D.dis[0] + 12, -162, D.dis[1] + 12, -12, 0, mat('concrete', 0)));

/* 1 · Alt çerçeve */
D.alt.forEach((s, i) => {
  const w = s.t + 0.6, a0 = s.a0 + 0.3, a1 = s.a1 - 0.3, m = mat('frame', 1), o = new THREE.Group();
  const seg = (c0, c1, h0, h1) => o.add(s.o === 'h' ? bp(a0, a1, c0, c1, h0, h1, m) : bp(c0, c1, a0, a1, h0, h1, m));
  seg(s.perp - w / 2, s.perp + w / 2, 0, 0.16);
  seg(s.perp - w / 2, s.perp - w / 2 + 0.16, 0, 2.7);
  seg(s.perp + w / 2 - 0.16, s.perp + w / 2, 0, 2.7);
  add(1, o, i, { kod: null, ad: s.duvar === 'dis' ? "100'lük alt çerçeve" : "60'lık alt çerçeve", satir: [['Bu parça', `hat ${fmtc(s.a1 - s.a0)} cm`], ['Duvar', s.duvar === 'dis' ? 'dış' : 'iç'], ['Liste', s.duvar === 'dis' ? '100 × 3750 · 8 adet' : '60 × 2500 · 7 adet']] });
});

/* 2–6 · Odalar: pano, H, köşe direği, çektirme U'su */
const openTxt = op => !op ? null : op.kind === 'win' ? `Pencere ${op.size} · eşik ${op.s} cm` : op.kind === 'door_ext' ? `Dış kapı boşluğu ${Math.round(op.a1 - op.a0)} × ${op.top} · çelik kapı 90 × 200 (sağ)` : 'Kapı boşluğu 82 × 200 (kasalı) · iç kapı alıcıya ait';
D.panels.forEach(p => {
  const [x0, y0, x1, y1] = p.rect, op = p.op, s = p.step, dvr = !p.card && /DVR/.test(p.ad || '');
  const pm = mat(p.duvar === 'dis' ? 'pdis' : 'pic', s);
  const g = new THREE.Group();
  const along = p.o === 'h' ? [x0, x1] : [y0, y1];
  const em = mat(dvr ? 'frame' : 'eps', s), [c0, c1] = p.o === 'h' ? [y0, y1] : [x0, x1];
  // dış yüz: 0 → c0 tarafı, 1 → c1 tarafı (binanın ortasından uzak olan), -1 → iç duvar
  const disYuz = p.duvar !== 'dis' ? -1 : (p.o === 'h' ? (y0 + y1) / 2 < D.dis[1] / 2 : (x0 + x1) / 2 < D.dis[0] / 2) ? 0 : 1;
  const fgm = mat('fuga', s);
  const kat = (a0, a1, d0, d1, h0, h1, mm) => g.add(p.o === 'h' ? bp(a0, a1, d0, d1, h0, h1, mm) : bp(d0, d1, a0, a1, h0, h1, mm));
  const piece = (a0, a1, h0, h1, m) => {   // pres panel: 8 mm betopan + EPS + 8 mm betopan (DVR: betopan + çelik karkas + betopan)
    const L = m !== pm ? [[c0, c1, m]] : [[c0, c0 + 0.8, pm, disYuz === 0], [c0 + 0.8, c1 - 0.8, em], [c1 - 0.8, c1, pm, disYuz === 1]];
    L.forEach(([d0, d1, mm, fugali]) => {
      if (!fugali) { kat(a0, a1, d0, d1, h0, h1, mm); return; }
      let h = h0;   // dış betopan: fuga bantlarında 5 mm derin oluk, dibi koyu
      FUGA.forEach(f => {
        const f0 = Math.max(f, h0), f1 = Math.min(f + FUGA_H, h1); if (f1 <= f0) return;
        if (f0 > h) kat(a0, a1, d0, d1, h, f0, mm);
        const [g0, g1] = disYuz === 0 ? [d0 + FUGA_D, d1] : [d0, d1 - FUGA_D];
        kat(a0, a1, g0, g1, f0, f1, fgm); h = f1;
      });
      if (h1 > h) kat(a0, a1, d0, d1, h, h1, mm);
    });
  };
  if (!op) piece(along[0], along[1], 0, H, pm);
  else {
    const { a0, a1, s: sill, top } = op;
    const jm = (op.kind === 'win' && op.size !== '60/60' && !dvr) ? mat('steel', s) : pm;   // pencere karkası (X, Y); DVR'de pencere yanları da betopan kaplı ve fugalı (Lokman)
    if (sill > 0) piece(along[0], along[1], 0, sill, pm);
    piece(along[0], along[1], top, H, pm);
    piece(along[0], a0, sill, top, jm);
    piece(a1, along[1], sill, top, jm);
    const fm = op.kind === 'door' ? mat('kasa', s) : mat('steel', s);
    const t = p.t + 1.2, f = 2.2;
    const across = p.o === 'h' ? [(y0 + y1) / 2 - t / 2, (y0 + y1) / 2 + t / 2] : [(x0 + x1) / 2 - t / 2, (x0 + x1) / 2 + t / 2];
    const fr = (b0, b1, h0, h1) => g.add(p.o === 'h' ? bp(b0, b1, across[0], across[1], h0, h1, fm) : bp(across[0], across[1], b0, b1, h0, h1, fm));
    fr(a0, a1, top - f, top);
    if (sill > 0) fr(a0, a1, sill, sill + f);
    fr(a0, a0 + f, sill, top); fr(a1 - f, a1, sill, top);
  }
  const yapi = dvr ? [['Yapı', 'çelik karkas (alt ve üst başlık, dikmeler, pencere üstünde kafes başlık), iki yüzü betopan'], ['Kaynak', 'dış duvar görünüşü ve SketchUp modeli (DVR1/DVR2)']]
    : op && op.kind === 'win' && op.size !== '60/60' ? [['Yapı', op.size === '180/180' ? '' : `alt pano ${op.s} cm + üst pano 50 cm, özel pencere karkası (100'lük çektirme U'su + H)`]] : [];
  add(s, g, p.order, { kod: p.card, ad: kart(p.card, p.ad), satir: [['Bu parça', `boy ${fmtc(p.boy)} cm · ${p.tur === 'STD' ? 'standart' : 'özel boy'}`], ['Oda', roomName(p.room)], ['Duvar', `${p.duvar === 'dis' ? 'dış' : 'iç'} · ${fmtc(p.t)} cm`], ...(op ? [['Açıklık', openTxt(op)]] : []), ...yapi, ...(disYuz >= 0 ? [['Cephe', 'fugalı: alttan 6 × 38 cm + 2 cm fuga, üstte 10 cm bant (pafta: fugalı duvar detayı)']] : []), ...kartSat(p.card)] });
});
D.hs.forEach(h => {
  const s = h.step, g = new THREE.Group(), dis = h.t > 8;
  const m = mat('steel', s), a = h.o === 'h' ? h.xy[0] : h.xy[1], perp = h.o === 'h' ? h.xy[1] : h.xy[0];
  const fl = 2.5;                               // sırt genişliği toplam 5 cm (gövdenin iki yanına 2,5), 100'lük ve 60'lık H'da aynı (Lokman, 26.10.2026; çizimde 43,92 mm); kanat 2 mm (1,2 mm sac, uçta ezilmiş kıvrım)
  const plate = (a0, a1, c0, c1) => g.add(h.o === 'h' ? bp(a0, a1, c0, c1, 0, H, m) : bp(c0, c1, a0, a1, 0, H, m));
  const sgn = h.stub ? (h.o === 'h' ? h.stub[1] : h.stub[0]) : 0;
  [[perp - h.t / 2, -1], [perp + h.t / 2, 1]].forEach(([f, side]) => {
    const c = side < 0 ? [f - HS, f] : [f, f + HS];
    if (h.stub && side === sgn) {              // 3'lü H: iç duvarın girdiği yüzde boşluk + iç duvarın iki yüzünde sırt kadar kol
      const gap = h.stub_t / 2, s0 = f, s1 = f + side * fl;
      plate(a - fl, a - gap, ...c); plate(a + gap, a + fl, ...c);
      [a - gap - HS, a + gap].forEach(x0 => g.add(h.o === 'h' ? bp(x0, x0 + HS, Math.min(s0, s1), Math.max(s0, s1), 0, H, m) : bp(Math.min(s0, s1), Math.max(s0, s1), x0, x0 + HS, 0, H, m)));
    } else plate(a - fl, a + fl, ...c);
  });
  if (h.card === 'H-01' || h.card === 'H-04') {  // kulak: makas bağlantısı
    g.add(h.o === 'h' ? bp(a - 2, a + 2, perp - 0.8, perp + 0.8, H, H + 12, m) : bp(perp - 0.8, perp + 0.8, a - 2, a + 2, H, H + 12, m));
  }
  const out = h.o === 'v' ? (perp < D.dis[0] / 2 ? -1 : 1) : (perp > D.dis[1] / 2 ? 1 : -1);
  if (h.tur === 'ozel_c') {                     // C: veranda kirişinin bağlandığı bağlantı levhası, dış yüzde
    const c0 = perp + out * (h.t / 2 + HS), c1 = c0 + out * 0.6;
    g.add(bp(a - 7, a + 7, Math.min(c0, c1), Math.max(c0, c1), H - 16, H, m));
  }
  const yer = { dubelli_kulakli: 'dış duvar, makasa denk gelen ek', dubelli: 'dış duvar, makasa denk gelmeyen ek', standart: 'iç duvar eki', uclu_dubelli_kulakli: 'dış duvar T’si, makasa denk', uclu_dubelli: 'dış duvar T’si', uclu_standart: 'iç duvar T’si', ozel_c: 'ön duvar eki; veranda kirişi buna bağlanır (paftada C)' }[h.tur];
  add(s, g, h.order, { kod: h.card, ad: kart(h.card, h.ad), satir: [['Bu parça', yer], ['Oda', roomName(h.room)], ...(h.card ? kartSat(h.card) : [['Liste', 'ÖZEL H (DÜBELLİ) - C · 100 × 100 × 2500 · 2 adet']])] });
  if (dis) {   // çelik dübel: dübelli H'ların dibinde, dış yüzde
    const f0 = perp + out * h.t / 2, md = mat('dubel', s), d = new THREE.Group();
    const rng = (u0, u1) => [Math.min(perp + out * u0, perp + out * u1), Math.max(perp + out * u0, perp + out * u1)];
    const box = ([c0, c1], h0, h1) => d.add(h.o === 'h' ? bp(a - 2, a + 2, c0, c1, h0, h1, md) : bp(c0, c1, a - 2, a + 2, h0, h1, md));
    box(rng(h.t / 2 + HS + 0.35, h.t / 2 + HS + 0.65), 0, 7.3);
    box(rng(h.t / 2 + HS + 0.35, h.t / 2 + HS + 4.65), 0, 0.3);
    add(s, d, h.order + 0.2, { kod: null, ad: 'Çelik dübel (köşebent)', satir: [['Bu parça', 'dübelli H’nın dibinde, dış yüzde'], ['Bağlantı', 'H’ya 1×M6 8.8 cıvata, zemine ankraj'], ['Liste', 'ÇELİK DÜBEL · 21 adet (dübelli H adedi kadar) + şase pul 21']] });
  }
});
/* Köşe profili (Lokman'ın çizimi, sac 1 mm). Yerel eksen: a = biten duvar boyunca, b = içeri giren duvar boyunca; O dış köşe.
   İçeri giren duvar köşe kutusuna kadar uzanır (bu projenin paftasında 5 cm; 6'lıkta 3 cm), biten duvar onun iç yüzünde biter. */
D.posts.forEach(p => {
  const [x0, y0, x1, y1] = p.rect, k = p, m = mat('post', p.step);
  const obj = new THREE.Group();
  const w = Math.abs(k.db[0]) ? x1 - x0 : y1 - y0, dep = Math.abs(k.dt[0]) ? x1 - x0 : y1 - y0;
  const P = (a, b) => [k.O[0] + a * k.db[0] + b * k.dt[0], k.O[1] + a * k.db[1] + b * k.dt[1]];
  const r = (a0, a1, b0, b1, h0 = 0, h1 = H) => { const p1 = P(a0, b0), p2 = P(a1, b1); obj.add(bp(Math.min(p1[0], p2[0]), Math.max(p1[0], p2[0]), Math.min(p1[1], p2[1]), Math.max(p1[1], p2[1]), h0, h1, m)); };
  const ic = !!k.ic, L = ic ? 9 : 13;
  r(-SAC, L, -SAC, 0); r(-SAC, 0, 0, L); r(w, w + SAC, 0, L - 0.5); r(0, w, k.e, k.e + SAC); r(w, w + 3, dep, dep + SAC);
  if (p.id === 'FL') r(-SAC - 0.6, -SAC, 0, 10, H - 16, H);   // A: veranda yan kirişinin bağlantı levhası (ön yüzde)
  const kesit = ic ? `iç köşe (6'lık iç duvar): kanatlar 9 × 9 cm (6 + 3), iç kanat 8,5 cm, iç tırnak 3 cm, kutu ${fmtc(w)} × ${fmtc(k.e)} cm, sac 1 mm (Lokman)` : `dış köşe (10'luk dış duvar): kanatlar 13 × 13 cm (10 + 3), iç kanat 12,5 cm, iç tırnak 3 cm, kutu ${fmtc(w)} × ${fmtc(k.e)} cm, sac 1 mm (Lokman çizimi)`;
  add(p.step, obj, p.order - 0.4, { kod: p.card, ad: kart(p.card, p.ad), satir: [['Oda', roomName(p.room)], ['Kesit', kesit], ...(p.id === 'FL' ? [['Görev', 'veranda sol kirişi buna bağlanır (kaynaklı detaylar paftasında A)'], ['Liste', 'ÖZEL KÖŞE DİREĞİ - A · 100 × 100 × 2500']] : []), ...kartSat(p.card)] });
});
D.ceku.forEach(u => {   // 60'lık çektirme U'su: iç duvar dış duvara pano ortasında girer
  const g = new THREE.Group(), m = mat('steel', u.step), [x, y] = u.xy, [ux, uy] = u.yon, hw = u.t / 2;
  const b = (a0, a1, b0, b1) => g.add(bp(Math.min(x + ux * a0 + uy * b0, x + ux * a1 + uy * b1), Math.max(x + ux * a0 + uy * b0, x + ux * a1 + uy * b1), Math.min(y + uy * a0 + ux * b0, y + uy * a1 + ux * b1), Math.max(y + uy * a0 + ux * b0, y + uy * a1 + ux * b1), 0, 244, m));
  b(0, SAC, -hw - SAC, hw + SAC);             // sırt: dış panonun iç yüzünde
  b(0, 3, -hw - SAC, -hw); b(0, 3, hw, hw + SAC);   // kanatlar: iç duvarın iki yüzünde 3 cm
  add(u.step, g, u.order, { kod: null, ad: "Çektirme U'su (60'lık)", satir: [['Bu parça', 'iç duvarın dış duvara pano ortasında girdiği yer'], ['Oda', roomName(u.room)], ['Liste', "ÇEKTİRME U'SU (60 LIK) 60 × 2440 · 4 adet (2 yer + 2 yedek)"]] });
});

/* 7 · Veranda kolon ve kirişleri (kaynaklı detaylar: A köşe direği, B ön kiriş, C özel H) */
{
  const v = D.veranda, m = mat('box', 7);
  v.kolon.forEach(([x0, y0, x1, y1], i) => {
    const g = new THREE.Group(); g.add(bp(x0, x1, y0, y1, 0.6, 240, m)); g.add(bp(x0 - 5, x1 + 5, y0 - 5, y1 + 5, 0, 0.6, m));
    add(7, g, i, { kod: 'V-01', ad: kart('V-01'), satir: [['Bu parça', `veranda kolonu ${i === 0 ? 'sol' : i === 1 ? 'orta' : 'sağ'} · 100 × 100 × 2400, 3 mm, flanşlı`], ['Liste', 'KUTU PROFİL (KOLON) (FLANŞLI) (3 MM) · 3 adet'], ...kartSat('V-01')] });
  });
  const [a, b, c, d] = v.kiris_on;
  add(7, bp(a, c, b, d, 240, 250, m), 3, { kod: 'V-02', ad: kart('V-02'), satir: [['Bu parça', 'ön kiriş · L 574,75 · 4 mm (paftada B)'], ['Liste', 'ÖZEL KUTU PROFİL (KİRİŞ) (4 MM) - B · 1 adet'], ...kartSat('V-02')] });
  v.kiris.forEach(([x0, y0, x1, y1], i) => add(7, bp(x0, x1, y0, y1, 240, 250, m), 4 + i, { kod: 'V-02', ad: kart('V-02'), satir: [['Bu parça', `kiriş L 140 · ${['sol: köşe direği A’ya', 'orta: özel H (C)’ya', 'sağ: özel H (C)’ya'][i]} bağlanır`], ['Liste', 'KUTU PROFİL (KİRİŞ) (4 MM) 100 × 100 × 1400 · 3 adet'], ...kartSat('V-02')] }));
}

/* 8 · Duvar üstü omegaları: saçak omegası, duvar omegası, baş makas omegası */
function serit(o, perp, out) {   // hat çerçevesi: yerel x hattan dışa, yerel z hat boyunca
  const u = o === 'h' ? [0, out] : [out, 0], r = Math.atan2(u[1], u[0]);
  const zOf = a => o === 'h' ? a * u[1] : -a * u[0];
  return { yeni: () => cerceve(r, o === 'h' ? 0 : perp, o === 'h' ? perp : 0), zOf };
}
{
  let oo = 0;
  D.omega_duvar.forEach(sg => {
    const ic = sg.tur === 'ic', PL = ic ? 375 : 250;
    const bas = sg.tur === 'bas', S = serit(sg.o, sg.perp, sg.out), n = Math.ceil((sg.a1 - sg.a0) / PL - 1e-6);
    const [uI, uD] = ic ? [-3.25, 3.25] : [5 + HS - OM100, 5 + HS];   // iç ve dış kanadın iç yüzü (yerel x dışa); 100'lükte dış kanat H kanadının dış yüzünde
    for (let k = 0; k < n; k++) {
      const a0 = sg.a0 + k * PL, a1 = Math.min(sg.a1, a0 + PL), [z0, z1] = [S.zOf(a0 + 0.2), S.zOf(a1 - 0.2)].sort((p, q) => p - q);
      const g = S.yeni(), m = mat('frame', 8), b = (u0, u1, h0, h1) => g.add(lb(u0, u1, h0, h1, z0, z1, m));
      b(uI - SAC, uD + SAC, H, H + SAC);
      if (sg.tur === 'sacak') {
        // Lokman çizimi (25.10.2026): içte 3 cm kanat + içe 3 cm ayak; dışta 3 cm kanat, ucunda yukarı ve dışa eğik dudak (dudak ölçüsü çizimden yaklaşık)
        b(uI - SAC, uI, H - 3, H); b(uI - 3, uI, H - 3 - SAC, H - 3); b(uD, uD + SAC, H - 3, H);
        const sl = lc(uD + SAC / 2, H - 3, uD + 1.3, H - 0.6, m, SAC, Math.abs(z1 - z0)); sl.position.z = (z0 + z1) / 200; g.add(sl);
      } else if (bas) {   // içte 3 cm açık yanak; dışta 1 cm U yanak (baş makas betopanı bu U'ya girer)
        const K = BAS_KANAT, U0 = uD + SAC, U1 = U0 + BAS_U;
        b(uI - SAC, uI, H - K, H); b(uI - 3, uI, H - K - SAC, H - K);
        b(uD, U0, H - K, H); b(uD, U1 + SAC, H - K - SAC, H - K); b(U1, U1 + SAC, H - K, H - K + BAS_DUDAK);
      } else if (ic) {   // 6,5 cm açıklık, 3 cm derinlik, iki yanda 3 cm kulak
        b(uI - SAC, uI, H - 3, H); b(uD, uD + SAC, H - 3, H); b(uI - 3, uI, H - 3 - SAC, H - 3); b(uD, uD + 3, H - 3 - SAC, H - 3);
      }
      else { b(uI - SAC, uI, H - 3, H); b(uD, uD + SAC, H - 3, H); }   // 100'lük duvar omegası: derinlik 3 cm
      const ad = { sacak: '100’lük saçak omegası', duvar: '100’lük duvar omegası', bas: 'Baş makas omegası', ic: '60’lık duvar omegası (iç duvar üstü)' }[sg.tur];
      const ls = { sacak: '100 × 2500 · 7 adet (makas saçaklarının altı: 1525 cm)', duvar: '100 × 2500 · 4 adet (saçak ve baş makas omegası gelmeyen yerler)', bas: 'L 2500 · 8 adet · fabrikada hazırlanır', ic: "60'LIK DUVAR OMEGASI 60 × 3750 · 36 adet (iç duvar üstleri ve ters tavan; listede toplam 127,64 m)" }[sg.tur];
      const kesit = { sacak: 'üst 10,5 cm (2 + 100 + 2 mm H kanatları), dış kanat dışarıda tam yaslanır; içte 3 cm kanat + içe 3 cm ayak; dışta 3 cm kanat, ucunda yukarı ve dışa eğik dudak; içteki aralıklara silikonize mastik; sac 1 mm (Lokman çizimi, 25.10.2026; dudak ölçüsü yaklaşık)', duvar: 'üst 10,5 cm (2 + 100 + 2 mm H kanatları), dış kanat dışarıda tam yaslanır; iki yanda 3 cm kanat; içteki aralıklara silikonize mastik; sac 1 mm',
        bas: `üst 10,5 cm (2 + 100 + 2 mm H kanatları), dış kanat dışarıda tam yaslanır; derinlik ${BAS_KANAT} cm; içte 3 cm açık yanak; dışta ${BAS_U} cm U yanak: 8 mm baş makas betopanı bu U’ya girer, betopan makasa dayanır; makas dış kanatla aynı hizada; içteki aralığa silikonize mastik; sac 1 mm (Lokman, 25.10.2026; U dudağı ~${BAS_DUDAK} cm varsayım)`,
        ic: '6,5 cm açıklık (6 cm pano + iki yanda H sacı 2 + 2 mm), derinlik 3 cm, iki yanda 3 cm kulak; kapı üstlerinden ve H’lardan kesintisiz geçer; sac 1 mm (Lokman, 25.10.2026)' }[sg.tur];
      add(8, g, oo++ * 0.6, { kod: null, ad, satir: [['Bu parça', `${sg.yer} · L ${fmtc(a1 - a0)} cm`], ['Kesit', kesit], ['Liste', ls], ...(ic ? [['Kaynak', 'Lokman, 25.10.2026: iç duvarların üstüne 60’lık omega']] : [])] });
    }
  });
}

/* 9 · Saçak sacı: tırnak 3 → saçak altı 30 → alın 13 → makasa doğru kıvrım 10 */
const SACAK = [
  { ad: 'arka saçak', o: 'h', face: 600, out: 1, a0: -30.2, a1: 930.2, f0: -30.2, f1: 930.2, t0: -1.1, t1: 901.1, R: AN },
  { ad: 'ön saçak (cumbanın sağı)', o: 'h', face: 0, out: -1, a0: 604.95, a1: 930.2, f0: 604.95, f1: 930.2, t0: 604.95, t1: 901.1, R: AN },
  { ad: 'cumba sol saçağı', o: 'v', face: 0, out: -1, a0: -180.2, a1: -30.2, f0: -180.2, f1: -30.2, t0: -151.1, t1: -30.2, R: CU },
  { ad: 'cumba sağ saçağı', o: 'v', face: 574.75, out: 1, a0: -180.2, a1: 0, f0: -180.2, f1: -30.2, t0: -151.1, t1: 0, R: CU },
];
{
  let to = 0;
  const hs = TB - 0.05, ht = hs + 13;
  SACAK.forEach(e => {
    const S = serit(e.o, e.face, e.out), n = Math.ceil((e.a1 - e.a0) / 250 - 1e-6);
    for (let k = 0; k < n; k++) {
      const a0 = e.a0 + k * 250, a1 = Math.min(e.a1, a0 + 250), [z0, z1] = [S.zOf(a0), S.zOf(a1)].sort((p, q) => p - q);
      const g = S.yeni(), m = mat('trim', 9);
      const t0 = Math.max(a0, e.t0), t1 = Math.min(a1, e.t1);         // saçak altı baş makasın betopanına dayanır, orada kesilir (Lokman, 26.10.2026)
      if (t1 > t0) { const [u0, u1] = [S.zOf(t0), S.zOf(t1)].sort((p, q) => p - q); g.add(lb(-2.8, 30.2, hs - SAC, hs, u0, u1, m)); }   // tırnak + saçak altı
      const f0 = Math.max(a0, e.f0), f1 = Math.min(a1, e.f1);
      if (f1 > f0) {
        const [y0, y1] = [S.zOf(f0), S.zOf(f1)].sort((p, q) => p - q);
        g.add(lb(30.2, 30.2 + SAC, hs - SAC, ht, y0, y1, m));           // alın 13 cm
        const fl = lb(-5, 5, -SAC / 2, SAC / 2, y0, y1, m);             // makasa doğru 10 cm kıvrım: aşığın üstünden trapezin altına
        fl.position.x = (30.2 - 5 * e.R.cos) / 100; fl.position.y = (ht + 5 * e.R.sin) / 100; fl.rotation.z = -e.R.th; g.add(fl);
      }
      add(9, g, to++ * 0.5, { kod: null, ad: 'Saçak sacı', satir: [['Bu parça', `${e.ad} · L ${fmtc(a1 - a0)} cm`], ['Profil', 'tırnak 3 → saçak altı 30 → alın 13 → makasa doğru kıvrım 10; açınım ≈ 56 cm'], ['Sıra', 'saçak omegasından sonra, makaslardan önce'], ['Uçta', 'saçak altı baş makasın (betopanının) hizasında kesilir; alın ve kıvrım köşeye, alın sacına kadar devam eder (Lokman, 26.10.2026)'], ['Liste', '(ANTRASİT) SAÇAK SACI (30\'LUK) 300 × 2500 · 8 adet (3 adedi menfezli)']] });
    }
  });
}

/* 10–11 · Makaslar (yerleri ve kesitleri SketchUp modelinden; iç çubuklar Alpha Mini düzeni: Warren, 9 göz) */
function makasKur(R, s0, s1, wl, NB, T0, m) {
  const g = new THREE.Group(), sm = R.M, off = CH / 2 / R.cos, yt = s => ysR(R, s) - off, yb = TB + CH / 2;
  g.add(lc(s0, yb, s1, yb, m));
  g.add(lc(s0, yt(s0), sm, yt(sm), m)); g.add(lc(s1, yt(s1), sm, yt(sm), m));
  [s0 + 2.25, s1 - 2.25].forEach(s => g.add(lc(s, TB, s, ysR(R, s), m)));
  wl.forEach(s => g.add(lc(s, TB + CH, s, yt(s) - off, m)));
  const P = (s1 - s0 - 2 * T0) / NB, T = k => s0 + T0 + k * P, B = k => s0 + T0 + P / 2 + k * P;
  for (let k = 0; k < NB; k++) { g.add(lc(T(k) + 4, yt(T(k) + 4), B(k), yb, m)); g.add(lc(B(k), yb, T(k + 1) - 4, yt(T(k + 1) - 4), m)); }
  return { g, P };
}
function araMakas(s0, s1, zb, nps, m) {   // cumba ara makası: alt başlığı ana makasların üst başlığında, üstü cumba eğiminde
  const R = CU, sm = R.M, g = new THREE.Group(), off = CH / 2 / R.cos, yt = s => ysR(R, s) - off, yb = zb + CH / 2;
  g.add(lc(s0, yb, s1, yb, m)); g.add(lc(s0, yt(s0), sm, yt(sm), m)); g.add(lc(s1, yt(s1), sm, yt(sm), m));
  [-1, 1].forEach(side => {
    const e = side < 0 ? s0 + 2.25 : s1 - 2.25, pts = Array.from({ length: nps + 1 }, (_, k) => e + (sm - e) * k / nps);
    pts.forEach((s, k) => { if (k < nps || side < 0) g.add(lc(s, zb + CH, s, yt(s) - off, m)); });
    for (let k = 0; k < nps; k++) g.add(lc(pts[k], yb, pts[k + 1], yt(pts[k + 1]) - off, m));
  });
  return g;
}
D.makas.forEach((mk, i) => {
  const ana = mk.aile === 'ana', ara = mk.aile === 'ara', step = ana ? 10 : 11, m = mat('truss', step);
  let g, P = 0;
  if (ana) { const r = makasKur(AN, mk.bas, mk.son, [2.7, 597.3], 9, 38.9, m); g = r.g; P = r.P; }
  else if (!ara) { const r = makasKur(CU, mk.bas, mk.son, [2.7, 572.05], 9, 38.86, m); g = r.g; P = r.P; }
  else g = araMakas(mk.bas, mk.son, ysR(AN, mk.yuz), mk.ad === 'MKS11' ? 2 : 1, m);
  const w = ana ? cerceve(Math.PI / 2, mk.konum, 0) : cerceve(0, 0, mk.konum); w.add(g);
  const kod = ara ? null : mk.rol === 'bas' ? 'MA-01' : 'MA-02';
  const yer = ana ? `x = ${fmtc(mk.konum)} cm (sol dış yüzden)` : `y = ${fmtc(mk.konum)} cm (ön duvarın ${mk.konum < 0 ? 'önünde' : 'arkasında'})`;
  const span = mk.son - mk.bas;
  add(step, w, ana ? i : i - 8, { kod, ad: kart(kod, 'Cumba ara makası'), satir: [
    ['Bu parça', `${mk.ad} · ${ara ? `L ${fmtc(span)} cm, ana makasların üst başlıklarına oturur` : `açıklık ${fmtc(span)} cm`}`], ['Yer', yer],
    ['Çatı', ana ? 'ana beşik · eğim 18,2° · tepe 118,5 cm' : 'cumba · eğim 18,9° · mahya ana mahyayla aynı yükseklikte'],
    ...(ara ? [['Görev', 'cumba yüzlerinin dere (vadi) hattına kadar uzanan kısmını taşır']] : [['İç çubuklar', `Warren, 18 çapraz · göz ${fmt(P)} cm · 10 cm topuk, duvar hizasında dikme`]]),
    ['Profil', 'C80 (listede "80X0.8") · 12 makas 314,9 kg'], ['Kaynak', 'SketchUp modeli (yer, boy, yükseklik)'], ...kartSat(kod)] });
});

/* 12 · Kalkanlar: baş makas betopanı (makas uçlarına artanı), baş makas Z'si (ve 15'te C kapama, 18'de alın sacı) */
// Kalkan çerçevesi: yerel x = s (makas boyunca), z = o (kalkan yüzünden dışa); oT makasın dış yüzü = baş makas omegasının dış kanadı
// (Lokman çizimi 25.10.2026: betopan makasa dayanır, alt ucu omeganın dış kanalına oturur), oTip alın sacının yüzü
const KALKAN = [
  { ad: 'sol kalkan (MKS01)', r: -Math.PI / 2, O: [0, 0], R: AN, plan: s => -s, uc: { A: 30, B: -630 }, sm: -300, oT: BAS_DIS, duvar: { A: 0, B: -600 }, altUc: { A: false, B: true }, parca: [[-50, -300], [-300, -550]], dolgu: [[0, -50], [-550, -600]] },
  { ad: 'sağ kalkan (MKS08)', r: Math.PI / 2, O: [900, 0], R: AN, plan: s => s, uc: { A: -30, B: 630 }, sm: 300, oT: BAS_DIS, duvar: { A: 0, B: 600 }, altUc: { A: true, B: true }, parca: [[50, 300], [300, 550]], dolgu: [[0, 50], [550, 600]] },
  { ad: 'cumba kalkanı (MKS09)', r: 0, O: [0, -150], R: CU, plan: s => s, uc: { A: -30, B: 604.75 }, sm: 287.375, oT: BAS_DIS, duvar: { A: 0, B: 574.75 }, altUc: { A: true, B: true }, parca: [[37.375, 287.375], [287.375, 537.375]], dolgu: [[0, 37.375], [537.375, 574.75]] },
];
KALKAN.forEach(G => { G.h = s => ysR(G.R, G.plan(s)); G.oTip = 30.2; G.ob = G.oT + BET_T; });   // ob: 8 mm betopanın dış yüzü
function rake(G, end, m, uzat = 0) {
  const sE = G.uc[end], dir = Math.sign(G.sm - sE), sT = sE - dir * (0.2 + uzat), sm = (sT + G.sm) / 2, Ls = Math.abs(G.sm - sT) / G.R.cos;
  const w = cerceve(G.r, ...G.O), g = new THREE.Group(); w.add(g);
  g.position.set(sm / 100, G.h(sm) / 100, 0); g.rotation.z = dir * G.R.th;
  const lev = (o0, o1, p0, p1) => { const b = mesh(new THREE.BoxGeometry(Ls / 100, (p1 - p0) / 100, Math.abs(o1 - o0) / 100), m); b.position.set(0, (p0 + p1) / 200, (o0 + o1) / 200); g.add(b); };
  const egik = (o0, p0, o1, p1) => { const dz = (o1 - o0) / 100, dy = (p1 - p0) / 100, b = mesh(new THREE.BoxGeometry(Ls / 100, SAC / 100, Math.hypot(dz, dy)), m); b.position.set(0, (p0 + p1) / 200, (o0 + o1) / 200); b.rotation.x = Math.atan2(-dy, dz); g.add(b); };
  return { w, Ls, lev, egik, dir };
}
{
  let bo = 0;
  KALKAN.forEach((G, gi) => {
    [...G.parca.map(p => [p, false]), ...G.dolgu.map(p => [p, true])].forEach(([[a, b], dolgu]) => {
      const sh = new THREE.Shape(), yt = s => (G.h(s) - 0.2) / 100;
      const alt = (H - BAS_KANAT) / 100;   // alt ucu baş makas omegasının dış kanalında
      sh.moveTo(a / 100, alt); sh.lineTo(b / 100, alt); sh.lineTo(b / 100, yt(b)); sh.lineTo(a / 100, yt(a)); sh.closePath();
      const o = mesh(new THREE.ExtrudeGeometry(sh, { depth: BET_T / 100, bevelEnabled: false }), mat('betopan', 12));
      o.position.z = G.oT / 100;
      const w = cerceve(G.r, ...G.O); w.add(o);
      add(12, w, bo++ * 0.5, { kod: null, ad: dolgu ? 'Baş makas betopanı · makas ucu' : 'Baş makas betopanı', satir: dolgu ? [['Bu parça', `${fmtc(Math.abs(b - a))} cm · ${G.ad}, makas ucu (iki betopanın dışında kalan üçgen)`], ['Malzeme', '125 × 250 betopanların eğimle kesilen artanından'], ['Oturma', 'alt ucu baş makas omegasının dış U yanağında; 8 mm'], ['Kaynak', 'Lokman, 25.10.2026: makas uçlarına artan betopan döşenir']] : [['Bu parça', `125 × 250 × 8 mm · ${G.ad}`], ['Pafta', 'Baş makas betopan yerleşimi: 3 kalkan × 2 = 6 adet'], ['Oturma', 'makasa dayanır, alt ucu baş makas omegasının dış U yanağına girer; aralığa silikon mastik (Lokman, 25.10.2026)'], ['Not', 'fabrikada hazırlanır; eğimle kesilen artanı makas uçlarına döşenir']] });
    });
    // Makasın duvar dışında kalan ucu (saçak tarafı, ~30 cm): saçak altından makasın üstüne artan betopan (Lokman, 26.10.2026:
    // "baş makasların uçlarında hâlâ kaplanmamış alan var; saçak sacı ile alın sacının birleştiği yerin boş kalmasının sebebi o")
    ['A', 'B'].forEach(end => {
      const sE = G.uc[end], dir = Math.sign(G.sm - sE), a = G.duvar[end], b = sE + dir * 0.2, yt = s => (G.h(s) - 0.2) / 100, alt = (TB - 0.05 - SAC) / 100;
      const sh = new THREE.Shape(); sh.moveTo(a / 100, alt); sh.lineTo(b / 100, alt); sh.lineTo(b / 100, yt(b)); sh.lineTo(a / 100, yt(a)); sh.closePath();
      const o = mesh(new THREE.ExtrudeGeometry(sh, { depth: BET_T / 100, bevelEnabled: false }), mat('betopan', 12));
      o.position.z = G.oT / 100;
      const w = cerceve(G.r, ...G.O); w.add(o);
      add(12, w, bo++ * 0.5, { kod: null, ad: 'Baş makas betopanı · saçak ucu', satir: [['Bu parça', `${fmtc(Math.abs(b - a))} cm · ${G.ad}, ${end === 'A' ? 'ön/sol' : 'arka/sağ'} uç: makasın duvar dışında kalan ucu`], ['Oturma', 'altı saçak sacının saçak altında, üstü makasın üst başlığında; dışında baş makas Z’si ve alın sacı'], ['Malzeme', '125 × 250 betopanların artanından; 8 mm'], ['Görev', 'saçak sacı ile alın sacının birleştiği köşeyi kapatır'], ['Kaynak', 'Lokman, 26.10.2026']] });
    });
    ['A', 'B'].forEach(end => {   // Baş makas Z'si: makas ve betopan üstünden geçer, betopanın dış yüzünden 3 cm iner, altta 3 cm dışarı kıvrılır
      const K = rake(G, end, mat('frame', 12));
      K.lev(G.oT - 8, G.ob + 0.1, -SAC, 0); K.lev(G.ob, G.ob + SAC, -3, 0); K.lev(G.ob, G.ob + 3.1, -3, -3 + SAC);
      add(12, K.w, 20 + bo++ * 0.5, { kod: null, ad: "Baş makas Z'si", satir: [['Bu parça', `${G.ad} · ${end === 'A' ? 'ön/sol' : 'arka/sağ'} yüz · L ${Math.round(K.Ls)} cm`], ['Kesit', 'üst kanat makas ve betopan üstünde · 3 cm çentik · 3 cm dış kanat; sac 1 mm'], ['Liste', "BAŞ MAKAS Z'Sİ L 2800 · 8 adet · fabrikada hazırlanır"], ['Kaynak', 'Lokman çizimi (24.10.2026, PK-01 kalkan kesiti)']] });
    });
  });
}

/* 13 · Tavan omegaları (ters tavan): odalarda makaslara dik, verandada cumba makaslarına dik */
D.omega.forEach((o, i) => {
  const m = mat('tomega', 13), len = o.son - o.bas, obj = mesh(omegaGeo(len, true), m);
  if (o.yon === 'y') obj.position.set(X(o.konum), TB / 100, Z(o.son));
  else { obj.rotation.y = Math.PI / 2; obj.position.set(X(o.bas), TB / 100, Z(o.konum)); }
  add(13, obj, i * 0.5, { kod: null, ad: "60'lık duvar omegası (ters tavan)", satir: [['Bu parça', `L ${fmtc(len)} cm · ${o.oda === 'veranda' ? 'veranda' : roomName(o.oda)}`], ['Kesit', '110 × 35 mm, üst 65, sac 1 mm'], ['Pafta', 'Tavan omega yerleşim planı: 45 parça, 111,8 m'], ['Liste', "60'LIK DUVAR OMEGASI 60 × 3750 · 36 adet (iç duvar üstleriyle birlikte)"]] });
});

/* 14 · Ters tavan kaplaması: odalarda 12,5 mm alçıpan (banyoda yeşil), verandada boardex; tavan omegalarının altına vidalanır (Lokman: omegalardan sonra) */
const TAVAN_ALT = TB - 3.5;   // tavan omegası şapkasının altı
{
  let ao = 0;
  const koy = (x0, x1, y0, y1, key, info) => add(14, bp(x0 + 0.15, x1 - 0.15, y0 + 0.15, y1 - 0.15, TAVAN_ALT - 1.25, TAVAN_ALT, mat(key, 14)), ao++ * 0.3, info);
  D.rooms.forEach(r => r.rects.forEach(([x0, y0, x1, y1]) => {
    const yesil = r.id === 'banyo';
    for (let xa = x0; x1 - xa > 2; xa += 120) for (let ya = y0; y1 - ya > 2; ya += 250) {   // 120 × 250, uzun kenarı omegalara dik (y boyunca)
      const xb = Math.min(xa + 120, x1), yb = Math.min(ya + 250, y1), tam = xb - xa > 119.9 && yb - ya > 249.9;
      koy(xa, xb, ya, yb, yesil ? 'alcipan_y' : 'alcipan', { kod: null, ad: yesil ? 'Ters tavan alçıpanı · yeşil' : 'Ters tavan alçıpanı · beyaz', satir: [
        ['Bu parça', `${r.ad} · ${tam ? 'tam levha 120 × 250' : `kesilmiş ${fmtc(xb - xa)} × ${fmtc(yb - ya)} cm`}`],
        ['Malzeme', `12,5 mm ${yesil ? 'yeşil (ıslak hacim) ' : ''}alçıpan; uzun kenarı tavan omegalarına dik, alçıpan vidasıyla (3,5 × 35)`],
        ['Sıra', 'tavan omegalarından sonra (Lokman, 25.10.2026)'],
        ['Liste', yesil ? '( ASMA / TERS ) TAVAN YEŞİL ALÇIPAN 12,5 × 1200 × 2500 · 2 adet' : '( ASMA / TERS ) TAVAN BEYAZ ALÇIPAN 12,5 × 1200 × 2500 · 17 adet']] });
    }
  }));
  // Veranda tavanı: boardex 120 × 240, uzun kenarı veranda omegalarına dik (x boyunca), kirişlerin arasında
  [[10, 313.75], [323.75, 564.75]].forEach(([x0, x1]) => {
    for (let xa = x0; x1 - xa > 2; xa += 240) for (let ya = -140; -ya > 2; ya += 120) {
      const xb = Math.min(xa + 240, x1), yb = Math.min(ya + 120, 0);
      koy(xa, xb, ya, yb, 'boardex', { kod: null, ad: 'Veranda tavanı · boardex', satir: [['Bu parça', `${fmtc(xb - xa)} × ${fmtc(yb - ya)} cm · kirişlerin arasında`], ['Malzeme', '12,5 mm boardex (çimento esaslı levha), veranda omegalarının altına'], ['Liste', 'VERANDA-SUNDURMA-BALKON TAVAN BOARDEX 12,5 × 1200 × 2400 · 4 adet']] });
    }
  });
}

/* 15–18 · Çatı yüzleri: yerel s (eğim boyunca, makas ucundan), t (saçak boyunca), n (aşık oturma yüzünden dik) */
const VSL = (x) => -30 + (x + 30) * (330 / 317.375);        // sol dere (vadi) hattı: (−30, −30) → (287,375; 300)
const VSR = (x) => -30 + (604.75 - x) * (330 / 317.375);    // sağ dere hattı: (604,75; −30) → (287,375; 300)
const YUZ = {
  MB:  { ad: 'ana çatı arka yüz', E: [0, 630], d: [0, -1], R: AN, poly: [[-30.2, 300], [930.2, 300], [930.2, 631.3], [-30.2, 631.3]] },
  MFR: { ad: 'ana çatı ön yüz (cumbanın sağı)', E: [0, -30], d: [0, 1], R: AN, poly: [[604.75 + 1.3 * 317.375 / 330, -31.3], [930.2, -31.3], [930.2, 300], [287.375, 300]], dere: [[604.75, -30], [287.375, 300]] },
  MFL: { ad: 'ana çatı ön yüz (cumbanın solu)', E: [0, -30], d: [0, 1], R: AN, poly: [[-30.2, VSL(-30.2)], [-30.2, 300], [287.375, 300]], dere: [[-30, -30], [287.375, 300]] },
  CL:  { ad: 'cumba sol yüz', E: [-30, 0], d: [1, 0], R: CU, poly: [[-31.3, -180.2], [287.375, -180.2], [287.375, 300], [-31.3, VSL(-31.3)]], dere: [[-30, -30], [287.375, 300]] },
  CR:  { ad: 'cumba sağ yüz', E: [604.75, 0], d: [-1, 0], R: CU, poly: [[287.375, -180.2], [606.05, -180.2], [606.05, VSR(606.05)], [287.375, 300]], dere: [[604.75, -30], [287.375, 300]] },
};
Object.values(YUZ).forEach(Y => {
  const [dx, dy] = Y.d, R = Y.R, c = R.cos, s = R.sin;
  const dS = new THREE.Vector3(dx * c, s, -dy * c), nS = new THREE.Vector3(-dx * s, c, dy * s), zS = new THREE.Vector3().crossVectors(dS, nS);
  Y.q = new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(dS, nS, zS));
  Y.yerel = ([x, y]) => { const px = x - Y.E[0], py = y - Y.E[1]; return [(px * dx + py * dy) / c, px * dy - py * dx]; };
  Y.tOf = (x, y) => Y.yerel([x, y])[1];
  Y.P = ccw(Y.poly.map(Y.yerel));
  Y.grup = () => { const g = new THREE.Group(); g.quaternion.copy(Y.q); g.position.set(X(Y.E[0]), (TB + HEEL) / 100, Z(Y.E[1])); return g; };
});

/* 15 · Omega aşıklar + C kapama */
{
  const A = D.asik, rows = { MB: A.ana_sira, MFR: A.ana_sira, MFL: A.ana_sira, CL: A.cumba_sira, CR: A.cumba_sira };
  const paf = { MB: A.pafta.arka, MFR: A.pafta.on_sag, MFL: A.pafta.on_sol, CL: A.pafta.cumba, CR: A.pafta.cumba };
  const bas = { MB: 'max', MFR: 'max', MFL: 'min', CL: 'max', CR: 'min' };   // paftadaki ilk parçanın başladığı uç (sol kalkan, sağ kalkan ya da cumbanın önü)
  let ao = 0;
  Object.entries(YUZ).forEach(([k, Y]) => {
    let pr = 0;
    rows[k].forEach((sr, r) => {
      const iv = aralik(Y.P, 0, sr); if (!iv || iv[1] - iv[0] < 20) return;
      const pf = paf[k][pr++] || [iv[1] - iv[0]], L = iv[1] - iv[0];
      const cuts = []; let acc = 0;
      pf.forEach((p, j) => { const l = j === pf.length - 1 ? L - acc : Math.min(p, L - acc); if (l > 1) cuts.push([acc, acc + l, p]); acc += l; });
      cuts.forEach(([u0, u1, p]) => {
        const t0 = bas[k] === 'max' ? iv[1] - u1 : iv[0] + u0, len = u1 - u0;
        const g = Y.grup(), o = mesh(omegaGeo(len, false), mat('asik', 15)); o.position.set(sr / 100, 0, t0 / 100); g.add(o);
        add(15, g, ao++ * 0.18, { kod: null, ad: 'Aşık (omega)', satir: [['Bu parça', `${Y.ad}, ${r + 1}. sıra · paftada L ${fmtc(p)} cm`], ['Kesit', '87 × 30 mm, üst 35, sac 1 mm'], ['Sıra yeri', `saçaktan eğim boyunca ${fmtc(sr)} cm`], ['Liste', 'AŞIK L 4200 · 43 adet (10 cm bindirme)']] });
      });
    });
  });
  // C kapama: kalkan saçağında aşık uçlarını kapatır
  KALKAN.forEach(G => ['A', 'B'].forEach(end => {
    const K = rake(G, end, mat('asik', 15));
    K.lev(G.oTip - 0.2, G.oTip - 0.2 + SAC, -2.9, AH); K.lev(G.oTip - 2.2, G.oTip - 0.2, AH, AH + SAC); K.lev(G.oTip - 2.2, G.oTip - 0.2, -2.9, -2.9 + SAC);
    add(15, K.w, 200 + ao++ * 0.18, { kod: null, ad: 'C kapama', satir: [['Bu parça', `${G.ad} · L ${Math.round(K.Ls)} cm`], ['Görev', 'aşık uçlarını kapatır; alın sacı bunun önüne gelir'], ['Kaynak', 'Lokman çizimi (24.10.2026, PK-01 kalkan kesiti)']] });
  }));
}

/* 16 · Çatı izolasyonu: 10 cm rulo cam yünü (Izocam), çatı kapanmadan makas aralarına serilir (Lokman, 25.10.2026).
   Her makas aralığına bir şerit; rulo ön duvardan arka duvara açılır (rehberde serilirken gösterilir). */
const ROLL_R0 = 22, ROLL_R1 = 9;   // rulo yarıçapı: başta ve sonda (cm)
{
  const T = 10, h0 = TB + 0.1, m = mat('izocam', 16);
  // şerit: başlangıç noktası (plan), serilme yönü ('y' ön → arka, 'x' sol → sağ), en, boy
  const serit = (px, py, yon, w, L, sira, ad, satir) => {
    const g = new THREE.Group(); g.position.set(X(px), h0 / 100, Z(py)); if (yon === 'x') g.rotation.y = -Math.PI / 2;   // yerel −z serilme yönü
    const sr = mesh(new THREE.BoxGeometry(w / 100, T / 100, L / 100), m); sr.position.set(0, T / 200, -L / 200); g.add(sr);
    const rp = new THREE.Group(); rp.visible = false; rp.userData.gecici = true; g.add(rp);   // rulo (yalnız serilirken)
    const rc = mesh(new THREE.CylinderGeometry(ROLL_R0 / 100, ROLL_R0 / 100, (w - 1) / 100, 28), m); rc.rotation.z = Math.PI / 2; rp.add(rc);
    add(16, g, sira, { kod: null, ad, satir: [...satir, ['Kaynak', 'Lokman, 25.10.2026'], ['Liste', 'ÇATI İZOLASYONU (IZOCAM-KNAUF) 100 mm · 9,6 m² / paket · 7 paket']] }, { serme: { sr, rp, rc, L } });
  };
  // ana çatı: her makas aralığına bir şerit, ön duvardan arka duvara
  const ANA = D.makas.filter(m => m.aile === 'ana').map(m => m.konum).sort((a, b) => a - b);
  for (let i = 0; i < ANA.length - 1; i++) {
    const x0 = ANA[i] + 4.2, x1 = ANA[i + 1] - 4.2, w = x1 - x0;
    serit((x0 + x1) / 2, 10, 'y', w, 580, i, 'Çatı izolasyonu · 10 cm rulo cam yünü', [
      ['Bu parça', `makas aralığı ${i + 1} (MKS${String(i + 1).padStart(2, '0')}–MKS${String(i + 2).padStart(2, '0')}) · ${fmtc(w)} × 580 cm`],
      ['Serme', 'çatı kapanmadan önce, aşıkların arasından; rulo ön duvardan arka duvara açılır, tavanın (alçıpanın) üstüne serilir']]);
  }
  // cumba (veranda): makas yönünde yatay, veranda tavanının üstüne; MKS09–MKS10 arası ve MKS10 ile ön duvar arası (Lokman)
  const CB = D.makas.filter(m => m.aile === 'cumba').map(m => m.konum).sort((a, b) => a - b);   // [MKS09, MKS10]
  [[-140, CB[1] - 4.2, 'MKS09–MKS10 arası'], [CB[1] + 4.2, 0, 'MKS10 ile ön duvar arası']].forEach(([y0, y1, yer], j) => {
    const w = y1 - y0, L = 564.75 - 10;
    serit(10, (y0 + y1) / 2, 'x', w, L, ANA.length - 1 + j, 'Çatı izolasyonu · 10 cm rulo cam yünü (cumba)', [
      ['Bu parça', `cumba (veranda) · ${yer} · ${fmtc(w)} × ${fmtc(L)} cm`],
      ['Serme', 'makas yönünde (yatay); rulo sol yan kirişten sağa açılır, veranda tavanının (boardex) üstüne serilir']]);
  });
}
function sermeAyarla(S, e) {   // e: 0 → 1 serilen oran
  S.sr.scale.z = Math.max(0.002, e); S.sr.position.z = -S.L * e / 200;
  const R = ROLL_R0 + (ROLL_R1 - ROLL_R0) * e;
  S.rp.visible = e < 0.999; S.rp.position.set(0, R / 100, -S.L * e / 100);
  S.rc.scale.set(R / ROLL_R0, 1, R / ROLL_R0); S.rp.rotation.x = -(S.L * e) / R;
}

/* 17 · Ters mahya, trapez sac, mahya (trapez doğrudan aşıkların üstünde) */
const RIB = (() => { const s = new THREE.Shape(), a = RIB_TABAN / 200, u = RIB_UST / 200; s.moveTo(-a, 0); s.lineTo(a, 0); s.lineTo(u, RIBH / 100); s.lineTo(-u, RIBH / 100); s.closePath(); return s; })();
{
  let ro = 0;
  // Ters mahya (dere hattı sacı): iki dere hattında, her iki yüzde 20 cm, aşıkların üstünde, trapezin altında
  Object.entries(YUZ).forEach(([k, Y]) => {
    if (!Y.dere) return;
    const p1 = Y.yerel(Y.dere[0]), p2 = Y.yerel(Y.dere[1]), e = [p2[0] - p1[0], p2[1] - p1[1]], el = Math.hypot(...e), u = [e[0] / el, e[1] / el];
    const cen = Y.P.reduce((a, p) => [a[0] + p[0] / Y.P.length, a[1] + p[1] / Y.P.length], [0, 0]);
    let nv = [-u[1], u[0]]; if ((cen[0] - p1[0]) * nv[0] + (cen[1] - p1[1]) * nv[1] < 0) nv = [-nv[0], -nv[1]];
    const L = 60, W = 22, a = [p1[0] - u[0] * L - nv[0] * 2, p1[1] - u[1] * L - nv[1] * 2], b = [p2[0] + u[0] * L - nv[0] * 2, p2[1] + u[1] * L - nv[1] * 2];
    const Q = kirp(Y.P, ccw([a, b, [b[0] + nv[0] * (W + 2), b[1] + nv[1] * (W + 2)], [a[0] + nv[0] * (W + 2), a[1] + nv[1] * (W + 2)]]));
    if (!Q) return;
    const g = Y.grup(); g.add(levha(Q, TM0, TM1, mat('ridge', 17)));
    add(17, g, ro++ * 0.3, { kod: null, ad: 'Ters mahya (dere hattı)', satir: [['Bu parça', `${Y.ad}, ${k === 'MFR' || k === 'CR' ? 'sağ' : 'sol'} dere hattı · ${Math.round(el)} cm`], ['Görev', 'iki yüzün kesiştiği iç köşede suyu saçağa indirir; trapez sac bunun üstünde kesilir'], ['Liste', '(ANTRASİT) TERS MAHYA L 2800 · 4 adet + kenar kutusu 8']] });
  });
  // Trapez sac 27/200-6: 100 cm kapatır, 0,5 mm (Lokman). Paftadaki dizilim 80'lik levhaya göre; model 100'lük levhayla yeniden dizildi.
  // Levhalar kalkan kenarından (cumbada ön saçaktan) başlar; son levha enine kesilir, dere ve mahya hattında açıyla kesilir.
  const dizi = (bas, son, yon) => { const out = []; for (let v = bas; yon * (son - v) > 0.5; v += yon * 100) out.push(yon > 0 ? [v, Math.min(son, v + 100)] : [Math.max(son, v - 100), v]); return out; };
  const SERIT = {
    MB: { ad: 350, iv: dizi(-30.2, 930.2, 1) }, MFR: { ad: 350, iv: dizi(930.2, 287.375, -1) }, MFL: { ad: 350, iv: dizi(-30.2, 287.375, 1) },
    CL: { ad: 340, iv: dizi(-180.2, 300, 1) }, CR: { ad: 340, iv: dizi(-180.2, 300, 1) },
  };
  const RX = Array.from({ length: 49 }, (_, k) => -30.2 + 4.5 + k * (960.4 - 9) / 48);     // ana çatı hadveleri (plan x), ~20 cm adım; iki kalkan kenarında birer hadve
  const RY = Array.from({ length: 25 }, (_, k) => -180.2 + 4.5 + k * 20).filter(y => y < 300);   // cumba hadveleri (plan y)
  let so = 0;
  Object.entries(YUZ).forEach(([k, Y]) => {
    const S = SERIT[k], cumba = k[0] === 'C';
    const tAt = v => cumba ? Y.tOf(Y.E[0], v) : Y.tOf(v, Y.E[1]);
    const ribs = (cumba ? RY : RX).map(tAt);
    S.iv.forEach(([v0, v1]) => {
      const [t0, t1] = [tAt(v0), tAt(v1)].sort((a, b) => a - b);
      const Q = kirp(dikd(-1.35, Y.R.SL + 2, t0, t1), Y.P); if (!Q) return;
      const g = Y.grup(), m = mat('roof', 17); g.add(levha(Q, TR0, TR1, m));
      ribs.forEach(tc => {
        if (tc < t0 - 0.01 || tc >= t1 - 0.01) return;   // levha sınırındaki hadve tek levhaya
        const iv = aralik(Q, 1, Math.min(Math.max(tc, t0 + 0.05), t1 - 0.05)); if (!iv || iv[1] - iv[0] < 4) return;
        const rb = mesh(new THREE.ExtrudeGeometry(RIB, { depth: (iv[1] - iv[0]) / 100, bevelEnabled: false }), m);
        rb.rotation.y = Math.PI / 2; rb.position.set(iv[0] / 100, TR1 / 100, tc / 100); g.add(rb);
      });
      const en = Math.abs(v1 - v0), kes = kirp(dikd(-1.35, Y.R.SL + 2, t0, t1), [[-1e4, -1e4], [1e4, -1e4], [1e4, 1e4], [-1e4, 1e4]]);
      const acili = Math.abs(Math.abs(alan(Q)) - Math.abs(alan(kes))) > 450, oran = Math.abs(alan(Q)) / (100 * (Y.R.SL + 3.35));
      const durum = !acili && en > 99.5 ? 'tam levha' : [en < 99.5 ? `enine kesilmiş (${fmtc(en)} cm)` : '', acili ? 'dere ya da mahya hattında açıyla kesilir' : ''].filter(Boolean).join(', ');
      add(17, g, 10 + so++ * 0.22, { kod: null, ad: oran < 0.45 ? 'Trapez sac · kesim parçası' : `Trapez sac ${S.ad} × 100`, satir: [
        ['Bu parça', `${Y.ad} · ${durum}`],
        ['Profil', '27/200-6: hadve 27 mm, adım 200 mm, tepe 42 / taban 74 mm; 6 hadve, 100 cm kapatır; 0,5 mm (Lokman)'],
        ['Dizilim', 'modelde 100’lük levhayla; paftadaki dizilim 80’lik levhaya göre çizilmiş'], ['Renk', 'antrasit'], ['Liste', 'TRAPEZ SAC 3500 · 21 adet, 3400 · 8 adet']] });
    });
  });
  // Mahya: ana mahya (x boyunca) ve cumba mahyası (y boyunca), hadve tepelerinin üstünde
  const top = ysR(AN, AN.M) + (PTOP + 0.8) / AN.cos;
  [[AN, Math.PI / 2, [0, 0], AN.M, [-30.2, 930.2], 'ana mahya'], [CU, Math.PI, [CU.M, 0], 0, [-180.2, 300], 'cumba mahyası']].forEach(([R, r, O, s0, [z0, z1], ad], j) => {
    [1, -1].forEach((side, i) => {
      const w = cerceve(r, ...O), zz = j ? [z0, z1] : [z0, z1], o = lb(-13, 13, -0.3, 0.3, zz[0], zz[1], mat('ridge', 17));
      o.position.x = (s0 - side * R.cos * 12) / 100; o.position.y = (top - R.sin * 12 + 1) / 100; o.rotation.z = side * R.th; w.add(o);
      add(17, w, 80 + j * 2 + i, { kod: null, ad: 'Trapez sac mahyası', satir: [['Bu parça', `${ad} · ${fmtc(z1 - z0)} cm`], ['Liste', 'TRAPEZ SAC MAHYASI L 800 · 25 adet; mahya bandı 4 rulo']] });
    });
  });
}

/* 18 · Alın sacı (3 kalkan), dere ve iniş */
let to = 0;
const ALIN_ALT = -3 - SAC - 6;   // Lokman, 26.10.2026: ayrı alt uç parçası yok; alın sacı dereyi de içine alacak kadar geniş (saçak altından 6 cm aşağı)
KALKAN.forEach(G => ['A', 'B'].forEach(end => {
  const K = rake(G, end, mat('trim', 18)), ot = G.oTip;
  K.lev(G.ob + SAC, ot, -3 - SAC, -3);                       // tırnak (Z'nin alt kanadının altında) + saçak altı
  const uz = G.altUc[end] ? 16.5 : 0, KU = rake(G, end, mat('trim', 18), uz);
  KU.lev(ot, ot + SAC, ALIN_ALT, PTOP);                      // alın: saçak altının 6 cm altından trapezin kenar hadvesinin üstüne; köşede dereyi de içine alır
  const k1 = RIB_KENAR + RIB_UST / 2 - 0.2, k2 = RIB_KENAR + RIB_TABAN / 2 - 0.1;   // kenar hadvesinin tepe ve taban iç kenarı (alın yüzünden)
  KU.lev(ot - k1, ot + SAC, PTOP - 0.1, PTOP);             // kıvrım: kenar hadvesinin tepesinin üstünden içeri
  KU.egik(ot - k1, PTOP - 0.1, ot - k2, TR1 + 0.5);        // hadveyi kavrayan kıvrım: hadvenin iç yüzü boyunca aşağı
  const nm = `${G.ad} · ${end === 'A' ? 'ön/sol' : 'arka/sağ'} yüz`;
  add(18, KU.w, to++ * 0.5, { kod: null, ad: 'Alın sacı', satir: [['Bu parça', `${nm} · alın ve üst kıvrımlar${uz ? '; köşede derenin ucunu da içine alacak kadar uzar' : ''}`], ['Alın', `~${fmt(PTOP - ALIN_ALT, 0)} cm: trapezin kenar hadvesinden saçak altının 6 cm altına; dereyi de içine alır, ayrı alt uç parçası yok (Lokman, 26.10.2026)`], ['Kaynak', 'Lokman çizimleri (24.10.2026)']] });
  add(18, K.w, to++ * 0.5, { kod: null, ad: 'Alın sacı', satir: [['Bu parça', `${nm} · L ${Math.round(K.Ls)} cm`], ['Profil', "tırnak 3 (baş makas Z'sine) → saçak altı 30 → alın → hadve üstünden kıvrım → hadveyi kavrayan kıvrım"], ['Uçta', 'saçak altı kolu makasın topuğuna dayanır, orada kesilir; alın yüzü ve üst kıvrım derenin ucunu kapatmak için devam eder (Lokman, 26.10.2026)'], ['Bu proje', `alın ~${fmt(PTOP - ALIN_ALT, 0)} cm: kenar hadvesinden dereyi de içine alacak kadar aşağı (Lokman, 26.10.2026; PK-01’de sandviç panelle 13 cm); kesin ölçü teyit bekler`], ['Liste', '( ANTRASİT) ALIN SACI (30\'LUK) 300 × 2500 · 10 adet']] });
  // Ayrı alt uç parçası yok (Lokman, 26.10.2026): alın sacının kendisi dereyi de içine alacak kadar geniş
}));
// Dere: galvaniz eksiz oluk, K kesit (38'lik açınım), boyalı antrasit; sırtı saçak sacının alnına asılır
const DERE_K = [[0, 11.4], [0, 0], [9, 0], [10, 0.8], [10.6, 2.6], [12, 3.6], [13, 5.6], [13.4, 8.6], [14.6, 10.2], [15, 11.4], [14, 11.4]];
const DERE_ALT = TB - 0.05 + 13 - 0.4 - 11.4;   // üstü alının 4 mm altında
const HAT = Object.fromEntries(D.dere.hatlar.map(h => [h.ad, h]));
const dereSerit = h => serit(h.yon === 'x' ? 'h' : 'v', h.kenar, h.out);   // yerel x dışa: 0 = saçak sacının alnı
D.dere.hatlar.forEach((h, i) => {
  const S = dereSerit(h), g = S.yeni(), m = mat('gutter', 18), [z0, z1] = [S.zOf(h.a0), S.zOf(h.a1)].sort((p, q) => p - q), L = (z1 - z0) / 100;
  const sh = thick(DERE_K.map(([u, v]) => [u + SAC + 0.03, v]), 0.05);
  const k = mesh(new THREE.ExtrudeGeometry(sh, { depth: L, bevelEnabled: false }), m); k.position.set(0, DERE_ALT / 100, z0 / 100); g.add(k);
  const kap = new THREE.Shape(); DERE_K.slice(0, 10).forEach(([u, v], j) => j ? kap.lineTo((u + SAC + 0.03) / 100, v / 100) : kap.moveTo((u + SAC + 0.03) / 100, v / 100)); kap.closePath();
  [z0 / 100 - 0.001, z1 / 100].forEach(zz => { const c = mesh(new THREE.ExtrudeGeometry(kap, { depth: 0.001, bevelEnabled: false }), m); c.position.set(0, DERE_ALT / 100, zz); g.add(c); });
  add(18, g, 30 + i, { kod: null, ad: 'Galvaniz eksiz oluk (dere)', satir: [['Bu parça', `${h.ad} hat · ${fmtc(h.a1 - h.a0)} cm (paftada ${fmtc(h.pafta)}) · iki ucunda kapak`], ['Kesit', 'K profil, 15 × 11,4 cm (38’lik açınım), boyalı antrasit'], ['Pafta', 'Makas ve dere planı: 4 hat, 16,4 m'], ['Liste', '( ANTRASİT ) METAL DERE L 4000 · 5 adet; dere kapağı 8, dere kelepçesi 40']] });
});
D.dere.inisler.forEach((p, i) => {
  // Lokman'ın fotoğrafları (25–26.10.2026): köşede iniş aparatı derenin uç kısmında, borunun tam hizasında; kaz boynu (2 açık dirsek)
  // duvara (verandada kolona) dik döner; boru köşe direği kaplamasının (13 cm) hemen yanından 2 kelepçeyle iner, altta kapalı dirsek.
  const h = HAT[p.hat], S = dereSerit(h), w = S.yeni(), m = mat('gutter', 18), ust = DERE_ALT;   // cm
  const kolon = p.duvar === 'veranda kolonu';
  const yuzU = (p.yuz - h.kenar) * h.out;   // duvar yüzünün yerel x'i (dışa pozitif)
  const sw = kolon ? -145 : Math.min(D.dis[0] - 17, Math.max(17, p.s));                 // boru: köşe direği kaplamasının yanında ya da kolonda
  const so = Math.min(Math.max(h.a0, h.a1) - 6, Math.max(Math.min(h.a0, h.a1) + 6, sw));    // ağız: borunun hizasında
  const zo = S.zOf(so), zw = S.zOf(sw), gx = SAC + 0.03 + 7.5, wx = yuzU + 4;
  const V = (x, y, z) => new THREE.Vector3(x / 100, y / 100, z / 100);
  const boru = (a, b) => { const d = new THREE.Vector3().subVectors(b, a), c = mesh(new THREE.BoxGeometry(0.06, d.length(), 0.08), m);
    c.position.copy(a).add(b).multiplyScalar(0.5); c.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.clone().normalize()); w.add(c); };
  const dirsek = v => { const d = mesh(new THREE.BoxGeometry(0.064, 0.064, 0.084), m); d.position.copy(v); w.add(d); };
  const ap = mesh(new THREE.BoxGeometry(0.07, 0.05, 0.09), m); ap.position.copy(V(gx, ust - 2.5, zo)); w.add(ap);
  const yatay = Math.hypot(gx - wx, zo - zw), dus = Math.max(26, yatay);   // kaz boynu ~45°
  const A = V(gx, ust - 5, zo), B = V(gx, ust - 14, zo), C = V(wx, ust - 14 - dus, zw), Dd = V(wx, 16, zw);
  boru(A, B); dirsek(B); boru(B, C); dirsek(C); boru(C, Dd); dirsek(Dd); boru(Dd, V(wx + 12, 6, zw));
  [80, 180].forEach(hh => {
    const k = mesh(new THREE.BoxGeometry(0.066, 0.02, 0.088), m); k.position.copy(V(wx, hh, zw)); w.add(k);
    w.add(lb(yuzU, wx - 3, hh - 1, hh + 1, zw - 1, zw + 1, m));
  });
  add(18, w, 40 + i * 0.4, { kod: null, ad: 'İniş borusu (dikdörtgen, oluklu)', satir: [['Bu parça', `${h.ad} hattı · ${p.duvar} boyunca`], ['Ağız', kolon ? 'kolonun hizasında; kaz boynu kolona dik döner' : (p.s < 17 || p.s > D.dis[0] - 17) ? 'derenin köşe ucunda, borunun hizasında; kaz boynu duvara dik döner, boru köşe direğinin yanından iner (Lokman’ın fotoğrafları)' : 'borunun hizasında; kaz boynu duvara dik döner'], ['Kesit', 'yaklaşık 8 × 6 cm, boyalı antrasit; bina ile birlikte iner'], ['Takım', 'iniş aparatı · 2 açık dirsek (kaz boynu) · boru L 3000 · 2 kelepçe · kapalı dirsek'], ['Pafta', '7 iniş'], ['Liste', 'iniş borusu 7, açık dirsek 14, kapalı dirsek 7, kelepçe 14']] });
});

/* 19 · İç kapılar (K-01 kanadı; bu projede iç kapılar alıcıya ait) */
D.doors.forEach((d, i) => {
  const g = new THREE.Group();
  g.position.set(X(d.hinge[0]), 0, Z(d.hinge[1]));
  const leaf = mesh(new THREE.BoxGeometry(0.80, 1.96, 0.04), mat('door', 19));
  leaf.position.set(0.41, 0.98, 0); g.add(leaf);
  const kn = mesh(new THREE.BoxGeometry(0.025, 0.12, 0.08), mat('steel', 19)); kn.position.set(0.72, 1.02, 0); g.add(kn);
  const a0 = Math.atan2(d.closed[1], d.closed[0]);
  let da = Math.atan2(d.open[1], d.open[0]) - a0; da = Math.atan2(Math.sin(da), Math.cos(da));
  g.rotation.y = a0;
  add(19, g, i, { kod: 'K-01', ad: kart('K-01'), satir: [['Oda', roomName(d.room)], ['Bu proje', 'iç kapılar alıcıya ait; yer ve açılış yönü paftadan'], ...kartSat('K-01')] }, { swing: [a0, a0 + da * 0.62] });
});
/* 19 · Pencereler ve dış kapı */
{
  const WC = { '120/120': 'P-01' }, WAD = { '120/80': 'PVC pencere 120/80 (sürgülü)', '180/180': 'PVC pencere 180/180 (çift açılım)', '60/60': 'PVC vasistas 60/60' };
  const WL = { '120/120': 'PVC DOĞRAMA … ÇİFT AÇILIM 120 × 120 · 2 adet', '120/80': 'PVC DOĞRAMA … SÜRGÜLÜ 120 × 80 · 1 adet', '180/180': 'PVC DOĞRAMA … ÇİFT AÇILIM 180 × 180 · 2 adet', '60/60': 'PVC DOĞRAMA … VASİSTAS 60 × 60 · 1 adet' };
  let wo = 5;
  D.panels.filter(p => p.op && (p.op.kind === 'win' || p.op.kind === 'door_ext')).forEach(p => {
    const [x0, y0, x1, y1] = p.rect, op = p.op, g = new THREE.Group(), c = p.o === 'h' ? (y0 + y1) / 2 : (x0 + x1) / 2;
    const box = (a0, a1, d0, d1, h0, h1, m, sh = true) => { const o = p.o === 'h' ? bp(a0, a1, d0, d1, h0, h1, m) : bp(d0, d1, a0, a1, h0, h1, m); o.castShadow = sh; g.add(o); };
    const { a0, a1, s: sill, top } = op, f = 5, dpt = 3.5;
    const fm = mat(op.kind === 'win' ? 'pvc' : 'cdoor', 19);
    box(a0, a0 + f, c - dpt, c + dpt, sill, top, fm); box(a1 - f, a1, c - dpt, c + dpt, sill, top, fm);
    box(a0, a1, c - dpt, c + dpt, top - f, top, fm);
    if (op.kind === 'win') {
      box(a0, a1, c - dpt, c + dpt, sill, sill + f, fm);
      const wide = a1 - a0 > 100, am = (a0 + a1) / 2;
      if (wide) box(am - 3, am + 3, c - dpt + 0.5, c + dpt - 0.5, sill + f, top - f, fm);
      const panes = wide ? [[a0 + f, am - 3], [am + 3, a1 - f]] : [[a0 + f, a1 - f]];
      panes.forEach(([b0, b1]) => box(b0, b1, c - 0.3, c + 0.3, sill + f, top - f, mat('glass', 19), false));
      const kod = WC[op.size] || null;
      add(19, g, wo++, { kod, ad: kart(kod, WAD[op.size]), satir: [['Bu parça', `${op.size} · eşik ${op.s} cm · antrasit, pervaz matik`], ['Oda', roomName(p.room)], ['Liste', WL[op.size]], ...kartSat(kod)] });
    } else {
      box(a0 + f, a1 - f, c - 2.25, c + 2.25, 0, top - f, mat('cdoor', 19));
      const hx = a0 + f + 6; box(hx, hx + 2.5, c - 4.5, c + 4.5, 98, 112, mat('steel', 19));
      add(19, g, wo++, { kod: 'K-02', ad: kart('K-02'), satir: [['Bu parça', `boşluk ${Math.round(a1 - a0)} × ${top} cm · kanat 90 × 200, sağ`], ['Oda', roomName(p.room)], ['Liste', 'PREFABRİK ÇELİK KAPI ( SAĞ ) 90 × 200 · 1 adet'], ...kartSat('K-02')] });
    }
  });
}

/* Oda zemin vurgusu */
const roomPatch = {};
const patchMat = new THREE.MeshBasicMaterial({ color: 0xf0a020, transparent: true, opacity: 0.26, depthWrite: false });
D.rooms.forEach(r => {
  const g = new THREE.Group();
  r.rects.forEach(([x0, y0, x1, y1]) => { const o = new THREE.Mesh(new THREE.BoxGeometry((x1 - x0) / 100, 0.004, (y1 - y0) / 100), patchMat); o.position.set(X((x0 + x1) / 2), 0.003, Z((y0 + y1) / 2)); g.add(o); });
  g.visible = false; scene.add(g); roomPatch[r.step] = g;
});

/* ---------- Adım verisi ---------- */
const ODA0 = 2, ODA1 = 1 + D.rooms.length;   // oda adımları 2–6
const byStep = Array.from({ length: N + 1 }, () => []);
parts.forEach(p => byStep[p.step].push(p));
const timing = byStep.map((list, s) => {
  const maxO = list.reduce((a, p) => Math.max(a, p.order), 0), oda = s >= ODA0 && s <= ODA1;
  const per = oda ? 0.34 : 0.14;
  if (list.some(p => p.anim && p.anim.serme)) return { stagger: 1.1, dur: 2.6, total: maxO * 1.1 + 2.6 };   // rulo serme: yavaş, sırayla
  const stagger = maxO > 0 ? Math.min(per, (oda ? 4.6 : 2.6) / maxO) : 0;
  return { stagger, dur: 0.6, total: maxO * stagger + 0.6 };
});
const DROP = [0, 0.3, 1.4, 1.4, 1.4, 1.4, 1.4, 1.2, 0.6, 0.6, 1.4, 1.2, 0.8, 0.5, -0.5, 0.7, 0, 0.9, 0.6, 0];   // 14: alçıpan aşağıdan yukarı

function cardRows(steps) {
  const c = new Map();
  parts.filter(p => steps.includes(p.step)).forEach(p => {
    const i = p.obj.userData.info, k = (i.kod || '') + '|' + i.ad;
    c.set(k, { kod: i.kod, ad: i.ad, n: (c.get(k)?.n || 0) + 1 });
  });
  return [...c.values()].sort((a, b) => (a.kod || 'zz').localeCompare(b.kod || 'zz', 'tr', { numeric: true }) || a.ad.localeCompare(b.ad, 'tr')).map(v => [v.kod, v.ad, v.n + ' adet', v.kod ? null : 'model']);
}
const R = (k, ad, v, src) => [k, ad, v, src];
const I = (ad, v) => ['-', ad, v];
const roomText = {
  yatak1: 'Dizilim arka sol köşe direğinden başlar. Sol dış duvar (120/120 pencereli pano), arka duvarın sol kısmı, banyo ve holle ortak iç duvar (kapılı pano) ve salon tarafındaki iç duvar bu odayla kurulur. Arka duvardaki T birleşimine 3’lü H girer; salon tarafındaki iç duvar sol dış duvara pano ortasında çektirme U’suyla bağlanır.',
  banyo: 'Arka duvarda 60/60 vasistaslı pano. Yatak odası 2 ile ortak iç duvar ve hol tarafında kapılı pano (banyo kapısı). İç duvar T’lerine 3’lü standart H girer.',
  hol: 'Yatak odası 2’nin kapılı panosu ve holün salon köşesindeki 6’lık köşe direği. Holün salona bakan tarafı açıktır.',
  yatak2: 'Arka duvarın sağ kısmı, arka sağ köşe direği, sağ dış duvar (120/120 pencereli pano) ve salon tarafındaki iç duvar. İç duvar sağ dış duvara çektirme U’suyla bağlanır.',
  salon: 'Sol dış duvar (120/80 sürgülü pencereli pano), veranda köşesindeki özel köşe direği A, ön duvar ve sağ dış duvarın ön kısmı. Ön duvarda iki betopan kaplı çelik karkas duvar (DVR01, DVR02; 180/180 pencereli) ve karkaslı çelik kapı panosu var; veranda kirişleri iki özel H’ya (C) bağlanacak. Dizilim bu odada kapanır.',
};
const STEPS = [
  { t: 'Bitmiş bina ve malzeme listesi', head: 'Kimlik kartına göre adetler',
    p: `__PROJE__ prefabrik konut: 900 × 600 cm, beşik çatı ve verandanın üstünde cumba. Dış cephe fugalı (38 cm’de bir 2 cm fuga), çatıda trapez sac doğrudan aşıkların üstünde. Montaj paftasından kurulan 3D model; her parça kimlik kartına bağlı (kartı olmayanlarda yükleme listesindeki adı yazar). Bir parçaya dokunun, kartı açılır. Oynat’a basınca montaj oda oda, ${N} adımda gösterilir.` },
  { t: 'Alt çerçeve', p: 'Zemin hazır olduktan sonra 100’lük alt çerçeve dış duvar hattına, 60’lık alt çerçeve iç duvar hattına serilip sabitlenir. Kapı boşluklarında çerçeve kesilir. Panolar bu çerçeveye oturur.',
    rows: [R(null, '100’lük alt çerçeve 100 × 3750', '8 adet', 'liste'), R(null, '60’lık alt çerçeve 60 × 2500', '7 adet', 'liste'), I('Dış duvar hattı', `${fmt(D.alt_m.dis)} m`), I('İç duvar hattı', `${fmt(D.alt_m.ic)} m`)] },
  ...D.rooms.map(r => ({ t: `${r.ad} (${fmt(r.m2, 2)} m²)`, p: roomText[r.id], room: r.id })),
  { t: 'Veranda kolon ve kirişleri', p: 'Verandanın iki ön köşesine ve ortasına flanşlı kutu profil kolon (100 × 100 × 2400, 3 mm) dikilir; üstlerine 574,75 cm’lik ön kiriş (B) bağlanır. Üç kısa kiriş (140 cm, 4 mm) ön kirişi binaya bağlar: soldaki özel köşe direği A’ya, öbür ikisi ön duvardaki özel H’lara (C). Cumba makasları bu kirişlere oturur.' },
  { t: 'Saçak, duvar ve baş makas omegası', p: 'Makasların oturacağı hatlara omega geçirilir. 100’lük omegalar 10,5 cm’dir (100 mm pano + iki yanda 2 mm H kanadı): dış kanat dışarıda tam yaslanır, içte kalan aralıklara silikonize mastik sıkılır. Arka duvar, ön duvarın sağ kısmı ve veranda yan kirişleri üstüne 100’lük saçak omegası (içte 3 cm kanat ve ayak, dışta 3 cm kanat ve eğik dudak); ön duvarın cumba altında kalan kısmına 100’lük duvar omegası; üç baş makasın altına baş makas omegası (fabrikada hazırlanır): 10,5 cm, dış kanadı duvara tam yaslı, 3 cm derinlik, içte 3 cm açık yanak, dışta baş makas betopanının gireceği 1 cm U yanak. İç duvarların üstüne 60’lık duvar omegası geçirilir (6,5 cm açıklık, 3 cm derinlik, 3 cm kulaklar); kapı üstlerinden kesintisiz geçer.',
    rows: [R(null, '100’lük saçak omegası 100 × 2500', '7 adet', 'liste'), R(null, '100’lük duvar omegası 100 × 2500', '4 adet', 'liste'), R(null, 'Baş makas omegası L 2500', '8 adet', 'liste'), R(null, '60’lık duvar omegası (iç duvar üstü)', `${parts.filter(q => q.step === 8 && q.obj.userData.info.ad.startsWith('60’lık')).length} parça · ${fmt(D.omega_duvar.filter(o => o.tur === 'ic').reduce((a, o) => a + o.a1 - o.a0, 0) / 100)} m`, 'model'), I('Sac', '1 mm')] },
  { t: 'Saçak sacı', p: 'Makaslardan önce takılır. 3 cm tırnağı saçak omegasının üstüne girer, makas oturunca altında sıkışır; 30 cm saçak altı, 13 cm alın ve makasa doğru 10 cm kıvrım. Dört saçak var: arka, ön (cumbanın sağı) ve cumbanın iki yanı; cumbanın sağında ön saçakla iç köşe yapar.',
    rows: [R(null, 'Saçak sacı (antrasit, 30’luk) 300 × 2500', '8 adet', 'liste'), I('Menfezli', '3 adet'), I('Profil', '3 + 30 + 13 + 10 cm'), I('Sac', '1 mm')] },
  { t: 'Ana çatı makasları', p: '8 makas (MKS01–08) 125,5 cm aralıkla, her biri bir kulaklı H ya da DVR karkası hizasında: iki uçta baş makas (MKS01, MKS08), arada 6 orta makas. Açıklık 660 cm (2 × 30 saçak), eğim 18,2°, tepe 118,5 cm. Alpha Mini düzeni: 10 cm topuk, duvar hizasında dikme, Warren zikzak. Ön uçları cumbanın altında kalır.',
    extra: [I('Açıklık', '660 cm'), I('Eğim', '18,2° · tepe 118,5 cm'), I('Makas aralığı', '125,5 cm (son göz 137)'), I('İç çubuk', 'Warren · 9 göz')] },
  { t: 'Cumba makasları', p: 'Cumba, verandanın üstünden ana çatıya dik uzanan ikinci beşiktir; mahyası ana mahyayla aynı yükseklikte. MKS09 veranda ön kirişine (cumbanın baş makası), MKS10 yan kirişlere oturur. MKS11 ve MKS12 ara makaslardır: ana makasların üst başlıklarına oturur ve iki yüzün kesiştiği dere (vadi) hattına doğru kısalır. Açıklık 634,75 cm, eğim 18,9°.',
    extra: [I('Açıklık', '634,75 cm'), I('Eğim', '18,9° · tepe 118,5 cm'), I('Aralık', '104 · 117 · 92 cm (pafta)')] },
  { t: 'Baş makas betopanı ve Z', p: 'Üç kalkan var: ana çatının iki ucu (MKS01, MKS08) ve cumbanın önü (MKS09). Her kalkanın dış yüzü iki 125 × 250 betopanla kapatılır: betopan (8 mm) makasa dayanır, alt ucu baş makas omegasının dış U yanağına girer; aralıklara silikon mastik sıkılır. Betopanların eğimle kesilen artanı iki uçtaki makas uçlarına döşenir. Üstüne baş makas Z’si gelir: makasın ve betopanın üstünden geçer, betopanın dış yüzünden 3 cm iner ve dışarı kıvrılır; alın sacının tırnağı buna girer.',
    rows: [R(null, 'Baş makas betopanı 125 × 250 × 8 mm', '6 adet', 'pafta'), R(null, 'Baş makas Z’si L 2800', '8 adet', 'liste'), I('Makas uçları', 'artan betopandan (6 parça)')] },
  { t: 'Tavan omegaları', p: 'Ters tavan için omegalar makas alt başlıklarının altına, şapkası aşağı bağlanır: odalarda 60 cm aralıkla makaslara dik, verandada 60 cm aralıkla cumba makaslarına dik. Kesit 110 × 35 mm, sac 1 mm.',
    rows: [R(null, 'Tavan omegası', '45 parça · 111,8 m', 'pafta'), R(null, '60’lık duvar omegası 60 × 3750', '36 adet (iç duvar üstleriyle)', 'liste'), I('Veranda', '10 × 140 cm')] },
  { t: 'Ters tavan alçıpanı', p: 'Tavan omegalarından sonra ters tavan kaplanır: 12,5 mm alçıpan levhalar (120 × 250) uzun kenarı omegalara dik olacak biçimde alttan vidalanır. Banyoda yeşil (ıslak hacim) alçıpan kullanılır. Verandanın tavanı boardex (120 × 240), kirişlerin arasında.',
    extra: [R(null, 'Tavan alçıpanı beyaz 12,5 × 1200 × 2500', '17 adet', 'liste'), R(null, 'Tavan alçıpanı yeşil (ıslak hacim)', '2 adet', 'liste'), R(null, 'Veranda tavanı boardex 12,5 × 1200 × 2400', '4 adet', 'liste'), R(null, 'Alçıpan vidası 3,5 × 35', '1250 adet', 'liste')] },
  { t: 'Omega aşıklar', p: 'Aşıklar 60 cm aralıkla makasların üst başlıklarına vidalanır; iki yüzün mahya aşıkları arasında 20 cm. Ana çatının arka yüzünde 7 sıra (410 + 410 + 140), ön yüzde cumbanın iki yanında; cumbanın her yüzünde 7 sıra, dere hattında kesilir. Kalkan saçaklarında aşık uçları C kapamayla kapatılır.',
    rows: [R(null, 'Aşık (omega) L 4200', '43 adet', 'liste'), I('Paftada', '57 parça · 154 m'), I('Kesit', '87 × 30 mm, sac 1 mm'), R(null, 'C kapama', '6 kalkan kenarı', 'model')] },
  { t: 'Çatı izolasyonu (10 cm rulo cam yünü)', p: 'Çatı kapanmadan önce 10 cm rulo cam yünü (Izocam) aşıkların arasından indirilip tavanın üstüne serilir. Her makas aralığına bir şerit gelir: rulo ön duvarın üstünden başlar, açılarak arka duvara kadar serilir. Rulo eni 120 cm, makas aralığı 125,5 cm. Cumbanın (verandanın) üstü de boş kalmaz: orada makas yönünde, yatay serilir.',
    extra: [R(null, 'Çatı izolasyonu (Izocam-Knauf) 100 mm · 9,6 m² / paket', '7 paket', 'liste'), I('Modelde', `${parts.filter(q => q.step === 16).length} şerit · ≈ ${fmt(parts.filter(q => q.step === 16).reduce((t, q) => t + q.obj.children[0].geometry.parameters.width * q.obj.children[0].geometry.parameters.depth, 0), 0)} m²`)] },
  { t: 'Trapez sac, mahya ve ters mahya', p: 'İki dere (vadi) hattına önce ters mahya döşenir. Ana çatıya 350’lik, cumbaya 340’lık antrasit 27/200 trapez sac (0,5 mm; hadve 27 mm, adım 200 mm; 100 cm kapatır) doğrudan aşıkların üstüne serilip vidalanır (bu projede OSB ve nem bariyeri yok); dere hattında açıyla kesilir. Levhalar kalkan kenarından başlayarak dizilir; paftadaki dizilim 80’lik levhaya göre çizildiği için model 100’lük levhayla yeniden dizildi. Mahyalar trapez sac mahyasıyla kapatılır.',
    rows: [R(null, 'Trapez sac L 3500 (ana çatı)', '21 adet', 'liste'), R(null, 'Trapez sac L 3400 (cumba)', '8 adet', 'liste'), I('Modelde', `${parts.filter(q => q.step === 17 && /^Trapez sac/.test(q.obj.userData.info.ad)).length} levha · 100 cm kapatır, 0,5 mm`), R(null, 'Trapez sac mahyası L 800', '25 adet', 'liste'), R(null, 'Ters mahya L 2800', '4 adet', 'liste'), R(null, 'Ters mahya kenar kutusu', '8 adet', 'liste')] },
  { t: 'Alın sacı, dere ve iniş', p: 'Alın sacı (antrasit) üç kalkanın eğik kenarlarına takılır: tırnağı baş makas Z’sine girer, saçak altı aşıkların altını kapatır, üstte trapezin kenar hadvesini kavrar; alın yüzü dereyi de içine alacak kadar geniştir, köşede derenin ucunu kapatır (ayrı parça yok). Dört saçağa K kesitli dere asılır; cumbanın sağında ön dereyle iç köşe yapar. 7 iniş borusu kaz boynuyla duvara ya da veranda kolonuna döner ve kelepçeyle iner.',
    rows: [R(null, 'Alın sacı 300 × 2500', '10 adet', 'liste'), R(null, 'Metal dere L 4000', '5 adet', 'liste'), I('Dere (pafta)', '4 hat · 16,4 m'), R(null, 'İniş takımı', '7 adet', 'pafta'), R(null, 'Dere kapağı', '8 adet', 'liste')] },
  { t: 'Kapı ve pencereler', p: 'Antrasit PVC pencereler (2 × 120/120 çift açılım, 1 × 120/80 sürgülü, 2 × 180/180 çift açılım, 1 × 60/60 vasistas) ve prefabrik çelik dış kapı (90 × 200, sağ) yerine konur. İç kapılar alıcıya ait; modelde yerlerini ve açılış yönlerini göstermek için çizildi. Bu adımda çatı, tavan ve izolasyon gizlenir; düğmeyle geri açılır.',
    extra: [I('İç kapılar', 'alıcıya ait')] },
];
STEPS.forEach((st, i) => {
  if (i === 0 || st.rows) return;
  st.rows = cardRows([i]).concat(st.extra || []);
});
// Genel bakış: gruplu liste
{
  const all = cardRows(Array.from({ length: N }, (_, i) => i + 1));
  const pick = (pre, adlar = []) => all.filter(r => (r[0] && pre.some(p => r[0].startsWith(p))) || (!r[0] && adlar.some(a => r[1].startsWith(a))));
  STEPS[0].rows = [
    ['grp', 'Duvar panoları'], ...pick(['D-', 'I-'], ['100\'lük yapıştırma', '100\'lük pencereli', 'Betopan kaplı']),
    ['grp', 'Ekler, köşeler ve veranda'], ...pick(['H-', 'B-', 'V-'], ['Özel H', 'Özel köşe', 'Çektirme']),
    ['grp', 'Çatı'], ...pick(['MA-'], ['Cumba ara']),
    R(null, 'Saçak omegası · duvar omegası · baş makas omegası', '7 · 4 · 8', 'liste'), R(null, 'Saçak sacı', '8 adet', 'liste'),
    R(null, 'Baş makas betopanı', '6 adet', 'pafta'), R(null, 'Tavan omegası', '45 · 111,8 m', 'pafta'), R(null, '60’lık duvar omegası (tavan + iç duvar)', '36 adet', 'liste'),
    R(null, 'Tavan alçıpanı beyaz · yeşil · veranda boardex', '17 · 2 · 4', 'liste'), R(null, 'Aşık L 4200', '43 adet', 'liste'), R(null, 'Çatı izolasyonu 100 mm (rulo)', '7 paket', 'liste'),
    R(null, 'Trapez sac 3500 / 3400 (100 cm kapatır, 0,5 mm)', '21 / 8 adet', 'liste'), R(null, 'Mahya · ters mahya', '25 · 4', 'liste'),
    R(null, 'Alın sacı', '10 adet', 'liste'), R(null, 'Dere ve iniş', '4 hat · 7 iniş', 'pafta'), R(null, 'Çelik dübel', '21 adet', 'liste'),
    ['grp', 'Kapı ve pencere'], ...pick(['K-', 'P-'], ['PVC']),
  ];
}
const NAMES = ['Genel bakış', 'Alt çerçeve', ...D.rooms.map(r => r.ad), 'Veranda', 'Duvar üstü omegaları', 'Saçak sacı', 'Ana çatı makasları', 'Cumba makasları', 'Baş makas betopanı ve Z', 'Tavan omegaları', 'Ters tavan alçıpanı', 'Omega aşıklar', 'Çatı izolasyonu', 'Trapez sac ve mahya', 'Alın sacı ve dere', 'Kapı ve pencereler'];

/* ---------- Kamera ---------- */
function roomCenter(id) {
  let ax = 0, ay = 0, aw = 0;
  ROOM[id].rects.forEach(([x0, y0, x1, y1]) => { const w = (x1 - x0) * (y1 - y0); ax += (x0 + x1) / 2 * w; ay += (y0 + y1) / 2 * w; aw += w; });
  return [ax / aw, ay / aw];
}
function preset(step, aspZorla) {
  let t, az, el, dist;
  const st = STEPS[step];
  if (st.room) { const [cx, cy] = roomCenter(st.room); t = [X(cx), 0.7, Z(cy)]; az = 0.5; el = 1.0; dist = { salon: 12.5, yatak2: 9, hol: 8, banyo: 8, yatak1: 8.5 }[st.room] || 8; }
  else {
    const P = {
      0: [[0, 1.4, 0.7], 0.62, 0.34, 16.5], 1: [[0, 0, 0.6], 0.45, 1.05, 13.5], 7: [[X(300), 1.2, Z(-60)], 0.55, 0.42, 8.5],
      8: [[0, 2.3, 0.6], 0.62, 0.55, 13.5],
      9: [[X(740), 2.45, Z(-20)], 0.7, 0.16, 5.2],
      10: [[0, 2.4, 0.2], 0.95, 0.55, 14.5], 11: [[X(287), 2.8, Z(-20)], 0.55, 0.45, 9.5], 12: [[X(250), 2.9, Z(150)], -0.55, 0.24, 11.5],
      13: [[0, 2.3, 0.6], 0.55, 1.28, 12.5], 14: [[0, 2.3, 0.6], 0.55, 1.28, 12.5], 15: [[0, 3.0, 0.6], 0.95, 0.6, 14],
      16: [[X(450), 2.5, Z(300)], 2.5, 0.95, 12.5], 17: [[0, 2.6, 0.6], 0.62, 0.5, 15.5], 18: [[0, 2.0, 0.6], -0.62, 0.28, 14.5], 19: [[0, 0.8, 0.6], 0.5, 1.0, 13],
    }[step];
    [t, az, el, dist] = P;
  }
  const asp = aspZorla || vp.clientWidth / Math.max(1, vp.clientHeight);
  dist *= Math.max(1, 1.35 / asp);
  const target = new THREE.Vector3(...t);
  const pos = target.clone().add(new THREE.Vector3(Math.cos(el) * Math.sin(az), Math.sin(el), Math.cos(el) * Math.cos(az)).multiplyScalar(dist));
  return { pos, target };
}
let tween = null;
function flyTo(step, instant = false) {
  if (!controls) return;
  const p = preset(step);
  if (instant || reduced) { camera.position.copy(p.pos); controls.target.copy(p.target); tween = null; return; }
  tween = { t0: now(), from: camera.position.clone(), fromT: controls.target.clone(), to: p.pos, toT: p.target, dur: 1.1 };
}

/* ---------- Akış ---------- */
let cur = 0, stepT0 = 0, stepEnd = 0, animating = false, playing = false, cutaway = false;
const ROOF_STEPS = [9, 10, 11, 12, 13, 14, 15, 16, 17, 18];
function applyVisibility() {
  const upto = cur === 0 ? N : cur;
  for (let s = 1; s <= N; s++) groups[s].visible = s <= upto && !(cutaway && ROOF_STEPS.includes(s));
  const b = $('roofTog'); b.setAttribute('aria-pressed', String(cutaway)); b.textContent = cutaway ? 'Çatıyı göster' : 'Çatıyı gizle';
  if (selHelper && !isShown(selObj)) clearSel();
}
function goTo(i, animate = true) {
  cur = Math.max(0, Math.min(N, i));
  cutaway = cur === N;
  for (const p of parts) { p.obj.visible = true; p.obj.position.y = p.y; if (p.anim && p.anim.swing) p.obj.rotation.y = p.anim.swing[1]; if (p.anim && p.anim.serme) sermeAyarla(p.anim.serme, 1); }
  Object.entries(roomPatch).forEach(([s, g]) => g.visible = +s === cur);
  applyVisibility();
  animating = cur > 0 && animate && !reduced;
  if (animating) { stepT0 = now(); byStep[cur].forEach(p => { p.obj.visible = false; }); }
  stepEnd = now() + (animating ? timing[cur].total : 0);
  if (controls) controls.autoRotate = false;
  renderUI(); flyTo(cur);
}
function rowsHtml(rows) {
  return rows.map(r => {
    if (r[0] === 'grp') return `<li class="grp">${r[1]}</li>`;
    const [k, ad, v, src] = r;
    return `<li>${k === '-' ? '<span></span>' : `<span class="k${k ? '' : ' none'}">${k || 'kart yok'}</span>`}<span>${ad}${src ? `<em class="src">${src}</em>` : ''}</span><span class="v">${v}</span></li>`;
  }).join('');
}
function renderUI() {
  const st = STEPS[cur];
  const isRoom = !!st.room, roomIdx = isRoom ? D.rooms.findIndex(r => r.id === st.room) + 1 : 0;
  $('eyebrow').textContent = cur === 0 ? `Genel bakış · ${N} adım` : isRoom ? `Adım ${cur} / ${N} · Oda ${roomIdx} / ${D.rooms.length}` : `Adım ${cur} / ${N}`;
  $('stepTitle').textContent = st.t;
  $('stepText').textContent = st.p;
  $('partsHead').textContent = st.head || 'Bu adımda';
  $('stepParts').innerHTML = rowsHtml(st.rows);
  $('badgeNo').textContent = cur === 0 ? '900 × 600 · 62,62 m²' : isRoom ? `Oda ${roomIdx} · adım ${cur}/${N}` : `Adım ${cur} / ${N}`;
  $('badgeTitle').textContent = cur === 0 ? 'Bitmiş bina' : NAMES[cur];
  $('stepList').querySelectorAll('button').forEach(b => {
    const idx = +b.dataset.i, done = cur > 0 && idx > 0 && idx < cur;
    b.classList.toggle('done', done);
    b.querySelector('.n').textContent = idx === 0 ? '—' : done ? '✓' : String(idx).padStart(2, '0');
    if (idx === cur) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current');
  });
  $('progress').querySelectorAll('button').forEach(b => {
    const s = +b.dataset.i;
    b.classList.toggle('on', cur > 0 && s < cur);
    b.classList.toggle('cur', s === cur);
  });
  $('prev').disabled = cur === 0;
  $('next').disabled = cur === N;
  updatePlay();
}
function updatePlay() {
  const b = $('play');
  const icon = playing ? '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 2h3v12h-3zM9.5 2h3v12h-3z"/></svg>' : '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2l10 6-10 6V2z"/></svg>';
  const label = playing ? 'Duraklat' : (cur === 0 || cur === N) ? 'Baştan oynat' : 'Oynat';
  b.innerHTML = icon + '<span>' + label + '</span>';
  b.setAttribute('aria-label', label);
}
function setupLists() {
  const sec = { 1: 'Zemin', [ODA0]: 'Oda oda dizilim', [ODA1 + 1]: 'Veranda ve çatı', [N]: 'Bitirme' };
  $('stepList').innerHTML = NAMES.map((n, i) => (sec[i] ? `<li class="sec">${sec[i]}</li>` : '') + `<li><button type="button" data-i="${i}"><span class="n"></span><span>${n}</span></button></li>`).join('');
  $('stepList').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; playing = false; goTo(+b.dataset.i); });
  $('progress').innerHTML = NAMES.slice(1).map((n, i) => `<button type="button" class="${i + 1 >= ODA0 && i + 1 <= ODA1 ? 'room' : ''}" data-i="${i + 1}" aria-label="Adım ${i + 1}: ${n}"></button>`).join('');
  $('progress').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; playing = false; goTo(+b.dataset.i); });
}
setupLists();
$('prev').addEventListener('click', () => { playing = false; goTo(cur - 1); });
$('next').addEventListener('click', () => { playing = false; goTo(cur + 1); });
$('play').addEventListener('click', () => {
  if (playing) { playing = false; updatePlay(); return; }
  playing = true;
  if (cur === 0 || cur === N) goTo(1); else if (!animating) goTo(cur + 1); else updatePlay();
});
$('roofTog').addEventListener('click', () => { cutaway = !cutaway; applyVisibility(); });
/* Render görselleri (Blender Cycles; montaj hâli, ham malzeme) */
const GORSELLER = __GORSELLER__;
{
  const gal = $('gal'), img = $('galImg'), cap = $('galCap'), th = $('galThumbs'); let gi = 0;
  const goster = i => { gi = (i + GORSELLER.length) % GORSELLER.length; img.src = GORSELLER[gi][0]; img.alt = GORSELLER[gi][1]; cap.textContent = GORSELLER[gi][1];
    [...th.children].forEach((b, k) => b.setAttribute('aria-current', String(k === gi))); };
  GORSELLER.forEach(([src, ad], i) => { const b = document.createElement('button'); b.type = 'button'; b.setAttribute('aria-label', ad);
    const t = document.createElement('img'); t.src = src; t.alt = ''; t.loading = 'lazy'; b.appendChild(t); b.addEventListener('click', () => goster(i)); th.appendChild(b); });
  const ac = () => { gal.hidden = false; goster(gi); $('galX').focus(); }, kapa = () => { gal.hidden = true; $('galTog').focus(); };
  $('galTog').addEventListener('click', ac); $('galX').addEventListener('click', kapa);
  if (!GORSELLER.length) $('galTog').hidden = true;
  document.addEventListener('keydown', e => { if (gal.hidden) return; e.stopPropagation(); if (e.key === 'Escape') kapa(); else if (e.key === 'ArrowRight') goster(gi + 1); else if (e.key === 'ArrowLeft') goster(gi - 1); });
}
window.addEventListener('keydown', e => {
  if (e.key === 'ArrowRight') { playing = false; goTo(cur + 1); }
  if (e.key === 'ArrowLeft') { playing = false; goTo(cur - 1); }
  if (e.key === 'Escape') clearSel();
});
if (controls) controls.addEventListener('start', () => { tween = null; controls.autoRotate = false; });

/* ---------- Kimlik kartı: parçaya dokun ---------- */
const ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
let down = null, selObj = null, selHelper = null;
function isShown(o) { for (let p = o; p; p = p.parent) if (!p.visible) return false; return true; }
function clearSel() { if (selHelper) { scene.remove(selHelper); selHelper.geometry.dispose(); } selHelper = null; selObj = null; $('info').hidden = true; }
function showInfo(obj) {
  clearSel();
  selObj = obj; selHelper = new THREE.BoxHelper(obj, 0xf0a020); scene.add(selHelper);
  const inf = obj.userData.info;
  $('infoK').textContent = inf.kod ? `Kimlik kartı ${inf.kod}` : 'Kimlik kartı henüz yok';
  $('infoK').className = 'ik' + (inf.kod ? '' : ' none');
  $('infoT').textContent = inf.ad;
  $('infoD').innerHTML = inf.satir.filter(r => r && r[1]).map(([a, b]) => `<dt>${a}</dt><dd>${b}</dd>`).join('');
  $('info').hidden = false;
}
$('infoX').addEventListener('click', clearSel);
if (renderer) {
  const el = renderer.domElement;
  el.addEventListener('pointerdown', e => { down = { x: e.clientX, y: e.clientY, t: now() }; });
  el.addEventListener('pointerup', e => {
    if (!down || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 6 || now() - down.t > 0.5) { down = null; return; }
    down = null;
    const r = el.getBoundingClientRect();
    ptr.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ptr, camera);
    const hits = ray.intersectObjects(groups.slice(1).filter(g => g.visible), true);
    for (const h of hits) {
      if (!isShown(h.object)) continue;
      let o = h.object; while (o && !o.userData.info) o = o.parent;
      if (o) { showInfo(o); return; }
    }
    clearSel();
  });
}

/* ---------- Döngü ---------- */
const easeOut = k => 1 - Math.pow(1 - k, 3);
const easeInOut = k => k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
function resize() {
  if (!renderer) return;
  const w = vp.clientWidth, h = Math.max(1, vp.clientHeight);
  renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(vp);
function tick() {
  const t = now();
  if (animating) {
    const { stagger, dur } = timing[cur];
    let all = true;
    for (const p of byStep[cur]) {
      const k = (t - stepT0 - p.order * stagger) / dur;
      if (k <= 0) { p.obj.visible = false; all = false; continue; }
      p.obj.visible = true;
      if (k < 1) all = false;
      const e = easeOut(Math.min(1, k));
      if (p.anim && p.anim.swing) p.obj.rotation.y = p.anim.swing[0] + (p.anim.swing[1] - p.anim.swing[0]) * e;
      else if (p.anim && p.anim.serme) sermeAyarla(p.anim.serme, easeInOut(Math.min(1, k)));
      else p.obj.position.y = p.y + (1 - e) * DROP[cur];
    }
    if (all) animating = false;
  }
  const glow = animating ? 1 : Math.max(0, 1 - (t - stepEnd) / 0.9);
  for (let s = 1; s <= N; s++) { const v = s === cur ? 0.08 + 0.34 * glow : 0; for (const m of stepMats[s]) m.emissiveIntensity = v; }
  if (playing && !animating && t > stepEnd + 1.3) {
    if (cur < N) goTo(cur + 1); else { playing = false; if (controls) controls.autoRotate = true; updatePlay(); }
  }
  if (tween) {
    const k = Math.min(1, (t - tween.t0) / tween.dur), e = easeInOut(k);
    camera.position.lerpVectors(tween.from, tween.to, e); controls.target.lerpVectors(tween.fromT, tween.toT, e);
    if (k >= 1) tween = null;
  }
  if (selHelper) selHelper.update();
  if (controls) controls.update();
  if (renderer) renderer.render(scene, camera);
  requestAnimationFrame(tick);
}
resize();
goTo(0, false);
flyTo(0, true);
tick();
window.__montaj = { goTo, parts, STEPS, camera, THREE, controls, preset, N, serme: e => parts.forEach(p => p.anim && p.anim.serme && sermeAyarla(p.anim.serme, e)), kamera: (p, t) => { tween = null; camera.position.set(...p); if (controls) { controls.target.set(...t); controls.update(); } } };
