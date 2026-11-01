import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const D = JSON.parse(document.getElementById('pafta').textContent);
const $ = id => document.getElementById(id);
const now = () => performance.now() / 1000;
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const fmt = (n, d = 1) => Number(n).toFixed(d).replace('.', ',');
const fmtc = n => (Math.round(n * 100) / 100).toString().replace('.', ',');

/* İE-18 · Prefabrik montaj rehberinin tek şablonu. Hedef örnek 62 m² rehberi (deneme/2026-10-25_rehber_62m2, Lokman'ın 25–26 Ekim
   düzeltmeleriyle); onun sahnesi aynen, yalnız eve ait sayılar, yerler ve yazılar veriden (`araclar/paket/rehber/veri.py`). 62 m²'nin
   verisiyle bu dosya 62 m² rehberini parça parça aynı verir (`testler/paket/test_rehber.py`).
   Pafta çerçevesi (cm): x sol dış yüzden sağa, y ön dış yüzden arkaya (veranda y < 0 ya da y > derinlik). Sahne (m): X sağa, Y yukarı, Z öne. */
const X = x => x / 100 - D.dis[0] / 200;
const Z = y => D.dis[1] / 200 - y / 100;
const H = D.h;
const HEEL = 10, CH = 4.5, TB = H + 0.25, SAC = 0.1;   // TB: makas tabanı = duvar üstü + omega + saçak sacı tırnağı
const M = D.metin;                                      // eve ait kart ve adım yazıları
const yaz = (s, o) => String(s).replace(/\{(\w+)\}/g, (_, k) => typeof o[k] === 'number' ? fmtc(o[k]) : o[k]);
/* Çatılar (D.R): her beşik kendi s ekseninde (makas boyunca) L…R, mahya M, eğim tan. 62 m²: AN ana beşik (y boyunca), CU cumba (x boyunca). */
const RF = D.R;
Object.values(RF).forEach(R => { R.th = Math.atan(R.tan); R.cos = Math.cos(R.th); R.sin = Math.sin(R.th); R.SL = (R.M - R.L) / R.cos; });
const ysR = (R, s) => TB + HEEL + (s <= R.M ? s - R.L : R.R - s) * R.tan;   // üst başlık dış çizgisi = aşık oturma yüzü (cm)
// Çatı katmanları, aşık oturma yüzünden eğime dik (cm): aşık 3, ters mahya, kaplama doğrudan aşıkta.
// OSB ve nem bariyeri yok (Lokman, 25.10.2026). Kaplamanın kesiti veriden (D.kaplama.profil; 62 m²: trapez 27/200-6, 100 cm kapatır, 0,5 mm).
const KP = D.kaplama.profil;
const RIBH = KP.hadve, RIB_UST = KP.tepe, RIB_TABAN = KP.taban, RIB_KENAR = KP.kenar;   // RIB_KENAR: kalkan kenarındaki hadvenin ekseni, levha kenarından
const AH = 3.0 + SAC, TM0 = AH + 0.02, TM1 = TM0 + 0.1, TR0 = TM1 + 0.02, TR1 = TR0 + 0.05, PTOP = TR1 + RIBH + 0.1;   // kaplama 0,5 mm
// Cephe fugası (62 m² paftası: fugalı duvar detayı): alttan 6 × 38 cm betopan + 2 cm fuga, üstte 10 cm bant; oluk 5 mm derin. Fugasız evde boş.
const FUGA = D.fuga ? D.fuga.bant : [], FUGA_H = 2, FUGA_D = 0.5;
const N = D.N, AD = D.S;   // adım sayısı ve adımların yeri (62 m²: Lokman'ın sırası, 26.10.2026)
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
  pvc:      { color: 0x383e42, roughness: 0.4, metalness: 0.1 },      // antrasit gri PVC (RAL 7016; Lokman 26.10.2026)
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
Object.entries(D.renk || {}).forEach(([k, c]) => { BASE[k] = { ...BASE[k], color: c }; });   // eve ait renk (ör. beyaz PVC)
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
// Kartı modelde olan parçalar (aşık, omega, sac, dere, betopan, kaplama): verideki `kart_bag` (rol → kart kodu); 62 m²'de yok, kod boş kalır
const KB = r => (D.kart_bag && D.kart_bag[r]) || null;
// İç duvar kalınlığının liste adı ("60'lık" / "100'lük"; liste üretecinin kuralıyla, veriden); 62 m²'nin verisinde yok, orada 60'lık
const IC_KAL = M.ic_kal || "60'lık";
const kartSat = kod => kod ? [['Kart ölçüsü', D.cards[kod].olcu], ['IFC', D.cards[kod].ifc ? `${D.cards[kod].ifc.sinif} · ${D.cards[kod].ifc.alt_tur}` : '—']] : [];

// Zemin (veranda dahil)
scene.add(bp(D.zemin[0], D.zemin[1], D.zemin[2], D.zemin[3], -12, 0, mat('concrete', 0)));

/* 1 · Alt çerçeve */
D.alt.forEach((s, i) => {
  const w = s.t + 0.6, a0 = s.a0 + 0.3, a1 = s.a1 - 0.3, m = mat('frame', AD.alt), o = new THREE.Group();
  const seg = (c0, c1, h0, h1) => o.add(s.o === 'h' ? bp(a0, a1, c0, c1, h0, h1, m) : bp(c0, c1, a0, a1, h0, h1, m));
  seg(s.perp - w / 2, s.perp + w / 2, 0, 0.16);
  seg(s.perp - w / 2, s.perp - w / 2 + 0.16, 0, 2.7);
  seg(s.perp + w / 2 - 0.16, s.perp + w / 2, 0, 2.7);
  add(AD.alt, o, i, { kod: KB('alt_' + s.duvar), ad: s.duvar === 'dis' ? "100'lük alt çerçeve" : `${IC_KAL} alt çerçeve`, satir: [['Bu parça', `hat ${fmtc(s.a1 - s.a0)} cm`], ['Duvar', s.duvar === 'dis' ? 'dış' : 'iç'], ['Liste', M.alt_liste[s.duvar]], ...kartSat(KB('alt_' + s.duvar))] });
});

/* Odalar: pano, H, köşe direği, çektirme U'su */
const PW = D.pencere;   // pencere ölçüsü → kart, ad, liste satırı, açılım (acilir | surgulu | vasistas | b180), karkas
const openTxt = op => !op ? null : op.kind === 'win' ? `Pencere ${op.size} · eşik ${op.s} cm` : op.kind === 'door_ext' ? `Dış kapı boşluğu ${Math.round(op.a1 - op.a0)} × ${op.top} · ${M.dis_kapi}` : M.ic_kapi_boslugu;
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
    const jm = (op.kind === 'win' && PW[op.size].karkas && !dvr) ? mat('steel', s) : pm;   // pencere karkası (X, Y); DVR'de pencere yanları da betopan kaplı ve fugalı (Lokman)
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
  const yapi = dvr ? [['Yapı', 'çelik karkas (alt ve üst başlık, dikmeler, pencere üstünde kafes başlık), iki yüzü betopan'], ['Kaynak', M.dvr_kaynak]]
    : op && op.kind === 'win' && PW[op.size].karkas ? [['Yapı', PW[op.size].tip === 'b180' ? '' : `alt pano ${op.s} cm + üst pano ${H - op.top} cm, özel pencere karkası (100'lük çektirme U'su + H)`]] : [];
  add(s, g, p.order, { kod: p.card, ad: kart(p.card, p.ad), satir: [['Bu parça', `boy ${fmtc(p.boy)} cm · ${p.tur === 'STD' ? 'standart' : 'özel boy'}`], ['Oda', roomName(p.room)], ['Duvar', `${p.duvar === 'dis' ? 'dış' : 'iç'} · ${fmtc(p.t)} cm`], ...(op ? [['Açıklık', openTxt(op)]] : []), ...yapi, ...(disYuz >= 0 && D.fuga ? [['Cephe', D.fuga.metin]] : []), ...kartSat(p.card)] });
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
  add(s, g, h.order, { kod: h.card, ad: kart(h.card, h.ad), satir: [['Bu parça', yer], ['Oda', roomName(h.room)], ...(h.card ? kartSat(h.card) : [['Liste', M.ozel_h_liste]])] });
  if (dis) {   // çelik dübel: dübelli H'ların dibinde, dış yüzde
    const f0 = perp + out * h.t / 2, md = mat('dubel', s), d = new THREE.Group();
    const rng = (u0, u1) => [Math.min(perp + out * u0, perp + out * u1), Math.max(perp + out * u0, perp + out * u1)];
    const box = ([c0, c1], h0, h1) => d.add(h.o === 'h' ? bp(a - 2, a + 2, c0, c1, h0, h1, md) : bp(c0, c1, a - 2, a + 2, h0, h1, md));
    box(rng(h.t / 2 + HS + 0.35, h.t / 2 + HS + 0.65), 0, 7.3);
    box(rng(h.t / 2 + HS + 0.35, h.t / 2 + HS + 4.65), 0, 0.3);
    add(s, d, h.order + 0.2, { kod: null, ad: M.dubel_ad, satir: [['Bu parça', 'dübelli H’nın dibinde, dış yüzde'], ['Bağlantı', 'H’ya 1×M6 8.8 cıvata, zemine ankraj'], ['Liste', M.dubel_liste]] });
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
  if (p.baglanti) r(-SAC - 0.6, -SAC, 0, 10, H - 16, H);   // A: veranda yan kirişinin bağlantı levhası (ön yüzde)
  // iç duvarı 100'lük evde iç köşe de 10'luk direktir (`ic_yer`; liste üreteci, PK-07): kesit dış köşeninki
  const kesit = ic ? `iç köşe (6'lık iç duvar): kanatlar 9 × 9 cm (6 + 3), iç kanat 8,5 cm, iç tırnak 3 cm, kutu ${fmtc(w)} × ${fmtc(k.e)} cm, sac 1 mm (Lokman)` : `${k.ic_yer ? "iç köşe (10'luk iç duvar)" : "dış köşe (10'luk dış duvar)"}: kanatlar 13 × 13 cm (10 + 3), iç kanat 12,5 cm, iç tırnak 3 cm, kutu ${fmtc(w)} × ${fmtc(k.e)} cm, sac 1 mm (Lokman çizimi)`;
  add(p.step, obj, p.order - 0.4, { kod: p.card, ad: kart(p.card, p.ad), satir: [['Oda', roomName(p.room)], ['Kesit', kesit], ...(p.baglanti ? [['Görev', p.baglanti.gorev], ['Liste', p.baglanti.liste]] : []), ...kartSat(p.card)] });
});
D.ceku.forEach(u => {   // çektirme U'su (iç duvarın kalınlığında): iç duvar dış duvara pano ortasında girer
  const g = new THREE.Group(), m = mat('steel', u.step), [x, y] = u.xy, [ux, uy] = u.yon, hw = u.t / 2;
  const b = (a0, a1, b0, b1) => g.add(bp(Math.min(x + ux * a0 + uy * b0, x + ux * a1 + uy * b1), Math.max(x + ux * a0 + uy * b0, x + ux * a1 + uy * b1), Math.min(y + uy * a0 + ux * b0, y + uy * a1 + ux * b1), Math.max(y + uy * a0 + ux * b0, y + uy * a1 + ux * b1), 0, 244, m));
  b(0, SAC, -hw - SAC, hw + SAC);             // sırt: dış panonun iç yüzünde
  b(0, 3, -hw - SAC, -hw); b(0, 3, hw, hw + SAC);   // kanatlar: iç duvarın iki yüzünde 3 cm
  add(u.step, g, u.order, { kod: null, ad: `Çektirme U'su (${IC_KAL})`, satir: [['Bu parça', 'iç duvarın dış duvara pano ortasında girdiği yer'], ['Oda', roomName(u.room)], ['Liste', M.ceku_liste]] });
});

/* Veranda kolon ve kirişleri (62 m²: kaynaklı detaylar, A köşe direği, B ön kiriş, C özel H). Kolon ve kirişin yazısı veriden. */
(D.verandalar || []).forEach(v => {
  const m = mat('box', AD.veranda);
  v.kolon.forEach(k => {
    const [x0, y0, x1, y1] = k.rect, g = new THREE.Group(); g.add(bp(x0, x1, y0, y1, 0.6, H - 10, m)); g.add(bp(x0 - 5, x1 + 5, y0 - 5, y1 + 5, 0, 0.6, m));
    add(AD.veranda, g, k.order, { kod: 'V-01', ad: kart('V-01'), satir: [['Bu parça', k.bu], ['Liste', k.liste], ...kartSat('V-01')] });
  });
  v.kiris.forEach(k => { const [x0, y0, x1, y1] = k.rect; add(AD.veranda, bp(x0, x1, y0, y1, H - 10, H, m), k.order, { kod: 'V-02', ad: kart('V-02'), satir: [['Bu parça', k.bu], ['Liste', k.liste], ...kartSat('V-02')] }); });
});

/* Duvar üstü omegaları: saçak omegası, duvar omegası, baş makas omegası, iç duvar omegası */
function serit(o, perp, out) {   // hat çerçevesi: yerel x hattan dışa, yerel z hat boyunca
  const u = o === 'h' ? [0, out] : [out, 0], r = Math.atan2(u[1], u[0]);
  const zOf = a => o === 'h' ? a * u[1] : -a * u[0];
  return { yeni: () => cerceve(r, o === 'h' ? 0 : perp, o === 'h' ? perp : 0), zOf };
}
{
  let oo = 0;
  D.omega_duvar.forEach(sg => {
    const ic = sg.tur === 'ic', PL = ic && !sg.sirt ? 375 : 250;   // 60'lık omega L 3750; 100'lük duvar omegası (iç duvar üstünde de) L 2500
    const bas = sg.tur === 'bas', S = serit(sg.o, sg.perp, sg.out), n = Math.ceil((sg.a1 - sg.a0) / PL - 1e-6);
    const SR = ic ? (sg.sirt || 6.5) : OM100;   // iç duvar omegasının sırtı: 60'lıkta 6,5; 100'lük iç duvarda modelden (100'lük duvar omegası; Lokman 29 ve 30.10.2026: 10,5)
    const [uI, uD] = ic ? [-SR / 2, SR / 2] : [5 + HS - OM100, 5 + HS];   // iç ve dış kanadın iç yüzü (yerel x dışa); 100'lükte dış kanat H kanadının dış yüzünde
    for (let k = 0; k < n; k++) {
      const a0 = sg.a0 + k * PL, a1 = Math.min(sg.a1, a0 + PL), [z0, z1] = [S.zOf(a0 + 0.2), S.zOf(a1 - 0.2)].sort((p, q) => p - q);
      const g = S.yeni(), m = mat('frame', AD.omega), b = (u0, u1, h0, h1) => g.add(lb(u0, u1, h0, h1, z0, z1, m));
      b(uI - SAC, uD + SAC, H, H + SAC);
      if (sg.tur === 'sacak') {
        // Lokman çizimi (25.10.2026): içte 3 cm kanat + içe 3 cm ayak; dışta 3 cm kanat, ucunda yukarı ve dışa eğik dudak (dudak ölçüsü çizimden yaklaşık)
        b(uI - SAC, uI, H - 3, H); b(uI - 3, uI, H - 3 - SAC, H - 3); b(uD, uD + SAC, H - 3, H);
        const sl = lc(uD + SAC / 2, H - 3, uD + 1.3, H - 0.6, m, SAC, Math.abs(z1 - z0)); sl.position.z = (z0 + z1) / 200; g.add(sl);
      } else if (bas) {   // içte 3 cm açık yanak; dışta 1 cm U yanak (baş makas betopanı bu U'ya girer)
        const K = BAS_KANAT, U0 = uD + SAC, U1 = U0 + BAS_U;
        b(uI - SAC, uI, H - K, H); b(uI - 3, uI, H - K - SAC, H - K);
        b(uD, U0, H - K, H); b(uD, U1 + SAC, H - K - SAC, H - K); b(U1, U1 + SAC, H - K, H - K + BAS_DUDAK);
      } else if (ic) {   // 6,5 cm açıklık (100'lük iç duvarda sırt 10,5), 3 cm derinlik, iki yanda 3 cm kulak
        b(uI - SAC, uI, H - 3, H); b(uD, uD + SAC, H - 3, H); b(uI - 3, uI, H - 3 - SAC, H - 3); b(uD, uD + 3, H - 3 - SAC, H - 3);
      }
      else { b(uI - SAC, uI, H - 3, H); b(uD, uD + SAC, H - 3, H); }   // 100'lük duvar omegası: derinlik 3 cm
      const ad = ic && sg.sirt ? '100’lük duvar omegası (iç duvar üstü)'
        : { sacak: '100’lük saçak omegası', duvar: '100’lük duvar omegası', bas: 'Baş makas omegası', ic: '60’lık duvar omegası (iç duvar üstü)' }[sg.tur];
      const ls = sg.liste || M.omega_liste[sg.tur];
      const kesit = { sacak: 'üst 10,5 cm (2 + 100 + 2 mm H kanatları), dış kanat dışarıda tam yaslanır; içte 3 cm kanat + içe 3 cm ayak; dışta 3 cm kanat, ucunda yukarı ve dışa eğik dudak; içteki aralıklara silikonize mastik; sac 1 mm (Lokman çizimi, 25.10.2026; dudak ölçüsü yaklaşık)', duvar: 'üst 10,5 cm (2 + 100 + 2 mm H kanatları), dış kanat dışarıda tam yaslanır; iki yanda 3 cm kanat; içteki aralıklara silikonize mastik; sac 1 mm',
        bas: `üst 10,5 cm (2 + 100 + 2 mm H kanatları), dış kanat dışarıda tam yaslanır; derinlik ${BAS_KANAT} cm; içte 3 cm açık yanak; dışta ${BAS_U} cm U yanak: 8 mm baş makas betopanı bu U’ya girer, betopan makasa dayanır; makas dış kanatla aynı hizada; içteki aralığa silikonize mastik; sac 1 mm (Lokman, 25.10.2026; U dudağı ~${BAS_DUDAK} cm varsayım)`,
        ic: sg.sirt ? `sırt ${fmt(sg.sirt)} cm (2 + 100 + 2 mm H kanatları + 1 mm), derinlik 3 cm, iki yanda 3 cm kulak: öteki ölçüleri 60’lık omeganın; kapı üstlerinden ve H’lardan kesintisiz geçer; sac 1 mm (Lokman, 29.10.2026)`
          : '6,5 cm açıklık (6 cm pano + iki yanda H sacı 2 + 2 mm), derinlik 3 cm, iki yanda 3 cm kulak; kapı üstlerinden ve H’lardan kesintisiz geçer; sac 1 mm (Lokman, 25.10.2026)' }[sg.tur];
      const kod = sg.kart || KB('omega_' + sg.tur);   // iç duvar omegasının kartı modelden (OM-01; 100'lük iç duvarda OM-02, 100'lük duvar omegası)
      add(AD.omega, g, oo++ * 0.6, { kod, ad, satir: [['Bu parça', `${sg.yer} · L ${fmtc(a1 - a0)} cm`], ...(sg.hat ? [['Hat', sg.hat]] : []), ['Kesit', kesit], ['Liste', ls], ...(ic ? [['Kaynak', sg.sirt ? `Lokman, 30.10.2026: iç duvar üstü omegası 100’lük duvar omegasıdır; 29.10.2026: sırtı ${fmt(sg.sirt)} cm, öteki ölçüleri 60’lık omeganın` : 'Lokman, 25.10.2026: iç duvarların üstüne 60’lık omega']] : []), ...kartSat(kod)] });
    }
  });
}

/* Saçak sacı: tırnak 3 → saçak altı 30 → alın 13 → makasa doğru kıvrım 10. Saçaklar veriden (D.sacak; R çatının anahtarı). */
const SACAK = D.sacak.map(e => ({ ...e, R: RF[e.R] }));
{
  let to = 0;
  const hs = TB - 0.05, ht = hs + 13;
  SACAK.forEach(e => {
    const S = serit(e.o, e.face, e.out), n = Math.ceil((e.a1 - e.a0) / 250 - 1e-6);
    for (let k = 0; k < n; k++) {
      const a0 = e.a0 + k * 250, a1 = Math.min(e.a1, a0 + 250), [z0, z1] = [S.zOf(a0), S.zOf(a1)].sort((p, q) => p - q);
      const g = S.yeni(), m = mat('trim', AD.sacak);
      const t0 = Math.max(a0, e.t0), t1 = Math.min(a1, e.t1);         // saçak altı baş makasın betopanına dayanır, orada kesilir (Lokman, 26.10.2026)
      if (t1 > t0) { const [u0, u1] = [S.zOf(t0), S.zOf(t1)].sort((p, q) => p - q); g.add(lb(-2.8, 30.2, hs - SAC, hs, u0, u1, m)); }   // tırnak + saçak altı
      const f0 = Math.max(a0, e.f0), f1 = Math.min(a1, e.f1);
      if (f1 > f0) {
        const [y0, y1] = [S.zOf(f0), S.zOf(f1)].sort((p, q) => p - q);
        g.add(lb(30.2, 30.2 + SAC, hs - SAC, ht, y0, y1, m));           // alın 13 cm
        const fl = lb(-5, 5, -SAC / 2, SAC / 2, y0, y1, m);             // makasa doğru 10 cm kıvrım: aşığın üstünden trapezin altına
        fl.position.x = (30.2 - 5 * e.R.cos) / 100; fl.position.y = (ht + 5 * e.R.sin) / 100; fl.rotation.z = -e.R.th; g.add(fl);
      }
      add(AD.sacak, g, to++ * 0.5, { kod: KB('sacak'), ad: 'Saçak sacı', satir: [['Bu parça', `${e.ad} · L ${fmtc(a1 - a0)} cm`], ['Profil', 'tırnak 3 → saçak altı 30 → alın 13 → makasa doğru kıvrım 10; açınım ≈ 56 cm'], ['Sıra', 'aşıklardan sonra, dereden önce (Lokman, 26.10.2026)'], ['Uçta', 'saçak altı baş makasın (betopanının) hizasında kesilir; alın ve kıvrım köşeye, alın sacına kadar devam eder (Lokman, 26.10.2026)'], ['Liste', M.sacak_liste], ...kartSat(KB('sacak'))] });
    }
  });
}

/* Makaslar (62 m²: yerleri ve kesitleri SketchUp modelinden; iç çubuklar Alpha Mini düzeni: Warren). Her makasın çatısı (R), yönü
   (y: makas y boyunca, x: x boyunca), duvar hizasındaki dikmeleri (wl), göz sayısı (NB) ve ilk düğümü (T0) veriden. */
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
function araMakas(R, s0, s1, zb, nps, m) {   // cumba ara makası: alt başlığı ana makasların üst başlığında, üstü cumba eğiminde
  const sm = R.M, g = new THREE.Group(), off = CH / 2 / R.cos, yt = s => ysR(R, s) - off, yb = zb + CH / 2;
  g.add(lc(s0, yb, s1, yb, m)); g.add(lc(s0, yt(s0), sm, yt(sm), m)); g.add(lc(s1, yt(s1), sm, yt(sm), m));
  [-1, 1].forEach(side => {
    const e = side < 0 ? s0 + 2.25 : s1 - 2.25, pts = Array.from({ length: nps + 1 }, (_, k) => e + (sm - e) * k / nps);
    pts.forEach((s, k) => { if (k < nps || side < 0) g.add(lc(s, zb + CH, s, yt(s) - off, m)); });
    for (let k = 0; k < nps; k++) g.add(lc(pts[k], yb, pts[k + 1], yt(pts[k + 1]) - off, m));
  });
  return g;
}
D.makas.forEach((mk, i) => {
  const ara = mk.aile === 'ara', step = AD.makas, m = mat('truss', step), R = RF[mk.R];
  let g, P = 0;
  if (!ara) { const r = makasKur(R, mk.bas, mk.son, mk.wl, mk.NB, mk.T0, m); g = r.g; P = r.P; }
  else g = araMakas(R, mk.bas, mk.son, ysR(RF[mk.zR], mk.yuz), mk.nps, m);
  const w = mk.yon === 'y' ? cerceve(Math.PI / 2, mk.konum, 0) : cerceve(0, 0, mk.konum); w.add(g);
  const kod = ara ? null : mk.kod !== undefined ? mk.kod : mk.rol === 'bas' ? 'MA-01' : 'MA-02';
  const yer = mk.yon === 'y' ? `x = ${fmtc(mk.konum)} cm (sol dış yüzden)` : mk.konum > D.dis[1] ? `y = ${fmtc(mk.konum)} cm (arka duvarın arkasında)` : `y = ${fmtc(mk.konum)} cm (ön duvarın ${mk.konum < 0 ? 'önünde' : 'arkasında'})`;
  const span = mk.son - mk.bas;
  add(step, w, i, { kod, ad: kart(kod, mk.kart_ad || M.ara_ad), satir: [
    ['Bu parça', `${mk.ad} · ${ara ? `L ${fmtc(span)} cm, ana makasların üst başlıklarına oturur` : `açıklık ${fmtc(span)} cm`}`], ['Yer', yer],
    ['Çatı', mk.cati],
    ...(ara ? [['Görev', M.ara_gorev]] : [['İç çubuklar', `Warren, ${2 * mk.NB} çapraz · göz ${fmt(P)} cm · 10 cm topuk, duvar hizasında dikme`]]),
    ['Profil', M.makas_profil], ['Kaynak', mk.kaynak || M.makas_kaynak], ...kartSat(kod)] });
});

/* Kalkanlar: baş makas betopanı (makas uçlarına artanı), baş makas Z'si (sonra C kapama ve alın sacı) */
// Kalkan çerçevesi: yerel x = s (makas boyunca), z = o (kalkan yüzünden dışa); oT makasın dış yüzü = baş makas omegasının dış kanadı
// (Lokman çizimi 25.10.2026: betopan makasa dayanır, alt ucu omeganın dış kanalına oturur), oTip alın sacının yüzü.
// Kalkanlar veriden (D.kalkan): r dönüş, O plan noktası, R çatı, p (s → plan: p · s), uçlar, duvarlar, betopan parçaları ve uç dolguları.
const KALKAN = D.kalkan.map(G => ({ ...G, R: RF[G.R], plan: s => G.p * s, oT: BAS_DIS }));
KALKAN.forEach(G => { G.h = s => ysR(G.R, G.plan(s)); G.oTip = 30.2; G.ob = G.oT + BET_T; });   // ob: 8 mm betopanın dış yüzü
function rake(G, end, m, uzat = 0) {
  const sE = G.uc[end], dir = Math.sign(G.sm - sE), sT = sE - dir * (0.2 + uzat), sm = (sT + G.sm) / 2, Ls = Math.abs(G.sm - sT) / G.R.cos;
  const w = cerceve(G.r, ...G.O), g = new THREE.Group(); w.add(g);
  g.position.set(sm / 100, G.h(sm) / 100, 0); g.rotation.z = dir * G.R.th;
  // x0, x1: parçanın eğik kenar boyunca yeri (yerel x, ortadan; verilmezse kenarın tamamı)
  const lev = (o0, o1, p0, p1, x0 = -Ls / 2, x1 = Ls / 2) => { const b = mesh(new THREE.BoxGeometry((x1 - x0) / 100, (p1 - p0) / 100, Math.abs(o1 - o0) / 100), m); b.position.set((x0 + x1) / 200, (p0 + p1) / 200, (o0 + o1) / 200); g.add(b); };
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
      const o = mesh(new THREE.ExtrudeGeometry(sh, { depth: BET_T / 100, bevelEnabled: false }), mat('betopan', AD.kalkan));
      o.position.z = G.oT / 100;
      const w = cerceve(G.r, ...G.O); w.add(o);
      add(AD.kalkan, w, bo++ * 0.5, { kod: dolgu ? null : KB('betopan'), ad: dolgu ? 'Baş makas betopanı · makas ucu' : 'Baş makas betopanı', satir: dolgu ? [['Bu parça', `${fmtc(Math.abs(b - a))} cm · ${G.ad}, ${M.betopan.dolgu}`], ['Malzeme', '125 × 250 betopanların eğimle kesilen artanından'], ['Oturma', 'alt ucu baş makas omegasının dış U yanağında; 8 mm'], ['Kaynak', 'Lokman, 25.10.2026: makas uçlarına artan betopan döşenir']] : [['Bu parça', `${M.betopan.levha} · ${G.ad}`], ['Pafta', M.betopan.pafta], ['Oturma', 'makasa dayanır, alt ucu baş makas omegasının dış U yanağına girer; aralığa silikon mastik (Lokman, 25.10.2026)'], ['Not', 'fabrikada hazırlanır; eğimle kesilen artanı makas uçlarına döşenir'], ...kartSat(KB('betopan'))] });
    });
    // Makasın duvar dışında kalan ucu (saçak tarafı, ~30 cm): saçak altından makasın üstüne artan betopan (Lokman, 26.10.2026:
    // "baş makasların uçlarında hâlâ kaplanmamış alan var; saçak sacı ile alın sacının birleştiği yerin boş kalmasının sebebi o")
    ['A', 'B'].forEach(end => {
      if (G.ucKapali && G.ucKapali[end]) return;   // uç veranda çatısının altında kalır (yüz ana çatının devamı)
      // alt ucu duvar üstündeki parçalar gibi baş makas omegasının dış U yanağında: omega saçak ucundan saçak ucuna (D-32); önce saçak sacının
      // saçak altındaydı, omeganın 3 cm üstünde kalıyordu (Lokman, 31.10.2026: "baş makas omegasının tam arasına girmeli, uçlarda yukarıda kalmış")
      const sE = G.uc[end], dir = Math.sign(G.sm - sE), a = G.duvar[end], b = sE + dir * 0.2, yt = s => (G.h(s) - 0.2) / 100, alt = (H - BAS_KANAT) / 100;
      const sh = new THREE.Shape(); sh.moveTo(a / 100, alt); sh.lineTo(b / 100, alt); sh.lineTo(b / 100, yt(b)); sh.lineTo(a / 100, yt(a)); sh.closePath();
      const o = mesh(new THREE.ExtrudeGeometry(sh, { depth: BET_T / 100, bevelEnabled: false }), mat('betopan', AD.kalkan));
      o.position.z = G.oT / 100;
      const w = cerceve(G.r, ...G.O); w.add(o);
      add(AD.kalkan, w, bo++ * 0.5, { kod: null, ad: 'Baş makas betopanı · saçak ucu', satir: [['Bu parça', `${fmtc(Math.abs(b - a))} cm · ${G.ad}, ${end === 'A' ? 'ön/sol' : 'arka/sağ'} uç: makasın duvar dışında kalan ucu`], ['Oturma', 'alt ucu baş makas omegasının dış U yanağında (omega saçak ucuna kadar), üstü makasın üst başlığında; dışında baş makas Z’si ve alın sacı (Lokman, 31.10.2026)'], ['Malzeme', '125 × 250 betopanların artanından; 8 mm'], ['Görev', 'saçak sacı ile alın sacının birleştiği köşeyi kapatır'], ['Kaynak', 'Lokman, 26.10.2026']] });
    });
    ['A', 'B'].forEach(end => {   // Baş makas Z'si: makas ve betopan üstünden geçer, betopanın dış yüzünden 3 cm iner, altta 3 cm dışarı kıvrılır
      const zl = (K, x0, x1) => { K.lev(G.oT - 8, G.ob + 0.1, -SAC, 0, x0, x1); K.lev(G.ob, G.ob + SAC, -3, 0, x0, x1); K.lev(G.ob, G.ob + 3.1, -3, -3 + SAC, x0, x1); };
      const satir = (bu, ek = []) => [['Bu parça', bu], ...ek, ['Kesit', 'üst kanat makas ve betopan üstünde · 3 cm çentik · 3 cm dış kanat; sac 1 mm'], ['Liste', M.z_liste], ['Kaynak', 'Lokman çizimi (24.10.2026, PK-01 kalkan kesiti)'], ...kartSat(KB('z'))];
      const yz = `${G.ad} · ${end === 'A' ? 'ön/sol' : 'arka/sağ'} yüz`;
      if (!G.z_parca) {   // 62 m²: kenar başına tek parça
        const K = rake(G, end, mat('frame', AD.kalkan)); zl(K);
        add(AD.kalkan, K.w, 20 + bo++ * 0.5, { kod: KB('z'), ad: "Baş makas Z'si", satir: satir(`${yz} · L ${Math.round(K.Ls)} cm`) });
        return;
      }
      // kenar başına ⌈eğik ÷ parça boyu⌉ parça (kart modeli ve liste; D-39): saçak ucundan mahyaya, son parça kalan
      const n = Math.ceil(Math.abs(G.sm - G.uc[end]) / G.R.cos / G.z_parca - 1e-6);   // eğik boy saçak ucundan (çizimdeki 0,2 cm uzatma sayılmaz)
      for (let k = 0; k < n; k++) {
        const K = rake(G, end, mat('frame', AD.kalkan)), uc = -K.dir * K.Ls / 2, a = k * G.z_parca, b = Math.min(K.Ls, (k + 1) * G.z_parca);
        const [x0, x1] = [uc + K.dir * (a + (k ? 0.1 : 0)), uc + K.dir * (b - (k < n - 1 ? 0.1 : 0))].sort((p, q) => p - q);
        zl(K, x0, x1);
        add(AD.kalkan, K.w, 20 + bo++ * 0.5, { kod: KB('z'), ad: "Baş makas Z'si", satir: satir(`${yz} · ${k + 1}/${n}. parça · L ${Math.round(b - a)} cm`, [['Kenar', `L ${Math.round(K.Ls)} cm · ${n} parça (parça boyu ${fmtc(G.z_parca)} cm; kenar başına ⌈eğik ÷ ${fmtc(G.z_parca)}⌉, liste ve kart modeli gibi)`]]) });
      }
    });
  });
}

/* Tavan omegaları: ters tavanda makas alt başlıklarının altında (62 m²: odalarda makaslara dik, verandada cumba makaslarına dik);
   asma dizme tavanda odaların içindeki omega hatları (iç duvarların üstündekiler duvar omegası olarak duvar adımında) */
D.omega.forEach((o, i) => {
  const m = mat('tomega', AD.tomega), len = o.son - o.bas, obj = mesh(omegaGeo(len, true), m);
  if (o.yon === 'y') obj.position.set(X(o.konum), TB / 100, Z(o.son));
  else { obj.rotation.y = Math.PI / 2; obj.position.set(X(o.bas), TB / 100, Z(o.konum)); }
  add(AD.tomega, obj, i * 0.5, { kod: KB('tomega'), ad: M.tomega.ad, satir: [['Bu parça', `L ${fmtc(len)} cm · ${o.oda === 'veranda' ? 'veranda' : roomName(o.oda)}`], ['Kesit', '110 × 35 mm, üst 65, sac 1 mm'], ['Pafta', M.tomega.pafta], ['Liste', M.tomega.liste], ...kartSat(KB('tomega'))] });
});

const TAVAN_ALT = TB - 3.5;   // tavan omegası şapkasının altı
if (D.tavan.tip === 'ters') {
/* Ters tavan kaplaması: odalarda 12,5 mm alçıpan (ıslak hacimde yeşil), verandada boardex; tavan omegalarının altına vidalanır (Lokman: omegalardan sonra) */
  let ao = 0;
  const koy = (x0, x1, y0, y1, key, info) => add(AD.alcipan, bp(x0 + 0.15, x1 - 0.15, y0 + 0.15, y1 - 0.15, TAVAN_ALT - 1.25, TAVAN_ALT, mat(key, AD.alcipan)), ao++ * 0.3, info);
  D.rooms.forEach(r => r.rects.forEach(([x0, y0, x1, y1]) => {
    const yesil = !!r.yesil;
    for (let xa = x0; x1 - xa > 2; xa += 120) for (let ya = y0; y1 - ya > 2; ya += 250) {   // 120 × 250, uzun kenarı omegalara dik (y boyunca)
      const xb = Math.min(xa + 120, x1), yb = Math.min(ya + 250, y1), tam = xb - xa > 119.9 && yb - ya > 249.9;
      koy(xa, xb, ya, yb, yesil ? 'alcipan_y' : 'alcipan', { kod: null, ad: yesil ? 'Ters tavan alçıpanı · yeşil' : 'Ters tavan alçıpanı · beyaz', satir: [
        ['Bu parça', `${r.ad} · ${tam ? 'tam levha 120 × 250' : `kesilmiş ${fmtc(xb - xa)} × ${fmtc(yb - ya)} cm`}`],
        ['Malzeme', `12,5 mm ${yesil ? 'yeşil (ıslak hacim) ' : ''}alçıpan; uzun kenarı tavan omegalarına dik, alçıpan vidasıyla (3,5 × 35)`],
        ['Sıra', 'tavan omegalarından sonra (Lokman, 25.10.2026)'],
        ['Liste', yesil ? M.alcipan_liste.yesil : M.alcipan_liste.beyaz]] });
    }
  }));
  // Veranda tavanı: boardex 120 × 240, uzun kenarı veranda omegalarına dik (x boyunca), kirişlerin arasında
  (D.tavan.boardex || []).forEach(([x0, x1, y0, y1]) => {
    for (let xa = x0; x1 - xa > 2; xa += 240) for (let ya = y0; y1 - ya > 2; ya += 120) {
      const xb = Math.min(xa + 240, x1), yb = Math.min(ya + 120, y1);
      koy(xa, xb, ya, yb, 'boardex', { kod: null, ad: 'Veranda tavanı · boardex', satir: [['Bu parça', `${fmtc(xb - xa)} × ${fmtc(yb - ya)} cm · kirişlerin arasında`], ['Malzeme', '12,5 mm boardex (çimento esaslı levha), veranda omegalarının altına'], ['Liste', M.boardex_liste]] });
    }
  });
} else {
/* Asma dizme tavan: omega hatlarının arasına tavan H'ı (kuralın aralığıyla), gözlere 12,5 mm alçıpan (ıslak hacimde yeşil). Hat ve gözler veriden. */
  const T = D.tavan, mh = mat('steel', AD.tomega);
  T.h.forEach((h, i) => add(AD.tomega, h.o === 'h' ? bp(h.a0, h.a1, h.perp - 2.5, h.perp + 2.5, TAVAN_ALT, TAVAN_ALT + 2, mh) : bp(h.perp - 2.5, h.perp + 2.5, h.a0, h.a1, TAVAN_ALT, TAVAN_ALT + 2, mh),
    100 + i * 0.12, { kod: null, ad: "Tavan H'ı (asma dizme tavan)", satir: [['Bu parça', `${fmtc(h.a1 - h.a0)} cm · ${roomName(h.oda)}`], ['Görev', 'iki omega hattı arasında; alçıpan gözlerinin kenarını taşır'], ['Aralık', T.h_aralik], ['Liste', M.tavan_h_liste]] }));
  T.goz.forEach(([x0, y0, x1, y1, yesil, oda], i) => add(AD.alcipan, bp(x0, x1, y0, y1, TAVAN_ALT - 1.25, TAVAN_ALT, mat(yesil ? 'alcipan_y' : 'alcipan', AD.alcipan)), i * 0.3,
    { kod: null, ad: yesil ? 'Asma tavan alçıpanı · yeşil' : 'Asma tavan alçıpanı · beyaz', satir: [['Bu parça', `${roomName(oda)} · göz ${fmtc(x1 - x0)} × ${fmtc(y1 - y0)} cm`],
      ['Malzeme', `12,5 mm ${yesil ? 'yeşil (ıslak hacim) ' : ''}alçıpan, 120 × 250 levhadan kesilir; omega ve tavan H'ı gözüne oturur`], ['Sıra', "tavan omegaları ve tavan H'larından sonra"],
      ['Liste', yesil ? M.alcipan_liste.yesil : M.alcipan_liste.beyaz]] }));
}
/* Açık mahalin tavanı (gömme veranda, balkon, niş): ters tavan, 12,5 mm yeşil alçıpan; tavan omegalarının altına, kolon ve kirişlerin arasında.
   Odaların tavanı asma da olsa burada ters tavan (Lokman, 31.10.2026). Alan ve omega yönü veriden; levha 120 × 250, uzun kenarı omegalara dik. */
let acO = parts.filter(p => p.step === AD.alcipan).reduce((a, p) => Math.max(a, p.order), -0.3);   // odaların levhalarından sonra
(D.tavan.acik || []).forEach(a => a.rects.forEach(([x0, y0, x1, y1]) => {
  const ux = a.yon === 'y', ex = ux ? 250 : 120, ey = ux ? 120 : 250;   // y yönündeki omegalara dik: uzun kenar x boyunca
  for (let xa = x0; x1 - xa > 2; xa += ex) for (let ya = y0; y1 - ya > 2; ya += ey) {
    const xb = Math.min(xa + ex, x1), yb = Math.min(ya + ey, y1), tam = xb - xa > ex - 0.1 && yb - ya > ey - 0.1;
    add(AD.alcipan, bp(xa + 0.15, xb - 0.15, ya + 0.15, yb - 0.15, TAVAN_ALT - 1.25, TAVAN_ALT, mat('alcipan_y', AD.alcipan)), acO += 0.3, {
      kod: null, ad: `${a.ad} tavanı · yeşil alçıpan (ters tavan)`, satir: [
        ['Bu parça', `${a.ad} · ${tam ? `tam levha ${fmtc(ex)} × ${fmtc(ey)}` : `kesilmiş ${fmtc(xb - xa)} × ${fmtc(yb - ya)} cm`}`],
        ['Malzeme', '12,5 mm yeşil alçıpan; tavan omegalarının altına, uzun kenarı omegalara dik, alçıpan vidasıyla (3,5 × 35)'],
        ['Kural', `${a.ad.toLocaleLowerCase('tr')} tavanı ters tavan, yeşil alçıpan (Lokman, 31.10.2026)`],
        ['Liste', M.alcipan_liste.yesil]] });
  }
}));

/* Çatı yüzleri: yerel s (eğim boyunca, makas ucundan), t (saçak boyunca), n (aşık oturma yüzünden dik). Yüzler veriden (D.yuz):
   E saçak noktası, d eğim yönü (plan), R çatı, poly plan çokgeni (62 m²'de dere hattında kırpılmış), dere hattı (varsa). */
const YUZ = Object.fromEntries(Object.entries(D.yuz).map(([k, Y]) => [k, { ...Y, R: RF[Y.R] }]));
Object.values(YUZ).forEach(Y => {
  const [dx, dy] = Y.d, R = Y.R, c = R.cos, s = R.sin;
  const dS = new THREE.Vector3(dx * c, s, -dy * c), nS = new THREE.Vector3(-dx * s, c, dy * s), zS = new THREE.Vector3().crossVectors(dS, nS);
  Y.q = new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(dS, nS, zS));
  Y.yerel = ([x, y]) => { const px = x - Y.E[0], py = y - Y.E[1]; return [(px * dx + py * dy) / c, px * dy - py * dx]; };
  Y.tOf = (x, y) => Y.yerel([x, y])[1];
  Y.P = ccw(Y.poly.map(Y.yerel));
  Y.grup = () => { const g = new THREE.Group(); g.quaternion.copy(Y.q); g.position.set(X(Y.E[0]), (TB + HEEL) / 100, Z(Y.E[1])); return g; };
});

/* Omega aşıklar + C kapama */
{
  const A = D.asik.yuzler;   // her yüzün sıraları (saçaktan eğim boyunca), paftadaki parça boyları ve ilk parçanın başladığı uç
  const rows = Object.fromEntries(Object.entries(A).map(([k, a]) => [k, a.sira])), paf = Object.fromEntries(Object.entries(A).map(([k, a]) => [k, a.pafta]));
  const bas = Object.fromEntries(Object.entries(A).map(([k, a]) => [k, a.bas]));
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
        const g = Y.grup(), o = mesh(omegaGeo(len, false), mat('asik', AD.asik)); o.position.set(sr / 100, 0, t0 / 100); g.add(o);
        add(AD.asik, g, ao++ * 0.18, { kod: KB('asik'), ad: 'Aşık (omega)', satir: [['Bu parça', `${Y.ad}, ${r + 1}. sıra · paftada L ${fmtc(p)} cm`], ['Kesit', '87 × 30 mm, üst 35, sac 1 mm'], ['Sıra yeri', `saçaktan eğim boyunca ${fmtc(sr)} cm`], ['Liste', M.asik_liste], ...kartSat(KB('asik'))] });
      });
    });
  });
  // C kapama: kalkan saçağında aşık uçlarını kapatır
  KALKAN.forEach(G => ['A', 'B'].forEach(end => {
    const K = rake(G, end, mat('asik', AD.asik));
    K.lev(G.oTip - 0.2, G.oTip - 0.2 + SAC, -2.9, AH); K.lev(G.oTip - 2.2, G.oTip - 0.2, AH, AH + SAC); K.lev(G.oTip - 2.2, G.oTip - 0.2, -2.9, -2.9 + SAC);
    add(AD.asik, K.w, 200 + ao++ * 0.18, { kod: KB('ckapama'), ad: 'C kapama', satir: [['Bu parça', `${G.ad} · L ${Math.round(K.Ls)} cm`], ['Görev', 'aşık uçlarını kapatır; alın sacı bunun önüne gelir'], ['Kaynak', 'Lokman çizimi (24.10.2026, PK-01 kalkan kesiti)'], ...kartSat(KB('ckapama'))] });
  }));
}

/* Çatı izolasyonu: 10 cm rulo cam yünü (Izocam), çatı kapanmadan makas aralarına serilir (Lokman, 25.10.2026).
   Her makas aralığına bir şerit; rulo bir duvardan karşı duvara açılır (rehberde serilirken gösterilir). Yön, boy ve ek şeritler veriden (D.izo). */
const ROLL_R0 = 22, ROLL_R1 = 9;   // rulo yarıçapı: başta ve sonda (cm)
if (AD.izo) {
  const T = 10, h0 = TB + 0.1, m = mat('izocam', AD.izo), I = D.izo;
  // şerit: başlangıç noktası (plan), serilme yönü ('y' ön → arka, 'x' sol → sağ), en, boy
  const serit = (px, py, yon, w, L, sira, ad, satir) => {
    const g = new THREE.Group(); g.position.set(X(px), h0 / 100, Z(py)); if (yon === 'x') g.rotation.y = -Math.PI / 2;   // yerel −z serilme yönü
    const sr = mesh(new THREE.BoxGeometry(w / 100, T / 100, L / 100), m); sr.position.set(0, T / 200, -L / 200); g.add(sr);
    const rp = new THREE.Group(); rp.visible = false; rp.userData.gecici = true; g.add(rp);   // rulo (yalnız serilirken)
    const rc = mesh(new THREE.CylinderGeometry(ROLL_R0 / 100, ROLL_R0 / 100, (w - 1) / 100, 28), m); rc.rotation.z = Math.PI / 2; rp.add(rc);
    add(AD.izo, g, sira, { kod: null, ad, satir: [...satir, ['Kaynak', 'Lokman, 25.10.2026'], ['Liste', M.izo_liste]] }, { serme: { sr, rp, rc, L } });
  };
  // ana çatı: her makas aralığına bir şerit, bir duvardan karşı duvara
  const AM = D.makas.filter(m => m.aile === 'ana').sort((a, b) => a.konum - b.konum), ANA = AM.map(m => m.konum);
  for (let i = 0; i < ANA.length - 1; i++) {
    const x0 = ANA[i] + 4.2, x1 = ANA[i + 1] - 4.2, w = x1 - x0;
    serit(I.ana.yon === 'y' ? (x0 + x1) / 2 : I.ana.bas, I.ana.yon === 'y' ? I.ana.bas : (x0 + x1) / 2, I.ana.yon, w, I.ana.L, i, I.ana.ad, [
      ['Bu parça', `makas aralığı ${i + 1} (${AM[i].ad}–${AM[i + 1].ad}) · ${fmtc(w)} × ${fmtc(I.ana.L)} cm`],
      ['Serme', I.ana.serme]]);
  }
  // ek şeritler (62 m²: cumbanın altı, makas yönünde yatay, veranda tavanının üstüne; Lokman)
  (I.ek || []).forEach((e, j) => {
    const w = e.yon === 'y' ? e.x1 - e.x0 : e.y1 - e.y0;   // İE-24: cumbada şerit y yönünde (makas aralığı x0…x1, ön duvardan)
    if (e.yon === 'y') serit((e.x0 + e.x1) / 2, e.y, 'y', w, e.L, ANA.length - 1 + j, e.ad, [['Bu parça', yaz(e.bu, { w, L: e.L })], ['Serme', e.serme]]);
    else serit(e.x, (e.y0 + e.y1) / 2, 'x', w, e.L, ANA.length - 1 + j, e.ad, [['Bu parça', yaz(e.bu, { w, L: e.L })], ['Serme', e.serme]]);
  });
}
function ackapaAyarla(L, a) {   // a: 0 kapalı → 1 açık
  L.forEach(m => {
    if (m.tip === 'don') m.el.rotation.y = (m.taban || 0) + m.max * a;
    else if (m.tip === 'devir') m.el.rotation[m.ax] = m.max * a;
    else m.el.position[m.ax] = m.p0 + m.max * a;
  });
}
function sermeAyarla(S, e) {   // e: 0 → 1 serilen oran
  S.sr.scale.z = Math.max(0.002, e); S.sr.position.z = -S.L * e / 200;
  const R = ROLL_R0 + (ROLL_R1 - ROLL_R0) * e;
  S.rp.visible = e < 0.999; S.rp.position.set(0, R / 100, -S.L * e / 100);
  S.rc.scale.set(R / ROLL_R0, 1, R / ROLL_R0); S.rp.rotation.x = -(S.L * e) / R;
}

/* Ters mahya, kaplama ve mahya (kaplama doğrudan aşıkların üstünde; 62 m²: trapez sac) */
const RIB = (() => { const s = new THREE.Shape(), a = RIB_TABAN / 200, u = RIB_UST / 200; s.moveTo(-a, 0); s.lineTo(a, 0); s.lineTo(u, RIBH / 100); s.lineTo(-u, RIBH / 100); s.closePath(); return s; })();
{
  let ro = 0;
  // Ters mahya (dere hattı sacı): dere (vadi) hatlarında, her iki yüzde 20 cm, aşıkların üstünde, kaplamanın altında
  Object.entries(YUZ).forEach(([k, Y]) => {
    if (!Y.dere) return;
    const p1 = Y.yerel(Y.dere[0]), p2 = Y.yerel(Y.dere[1]), e = [p2[0] - p1[0], p2[1] - p1[1]], el = Math.hypot(...e), u = [e[0] / el, e[1] / el];
    const cen = Y.P.reduce((a, p) => [a[0] + p[0] / Y.P.length, a[1] + p[1] / Y.P.length], [0, 0]);
    let nv = [-u[1], u[0]]; if ((cen[0] - p1[0]) * nv[0] + (cen[1] - p1[1]) * nv[1] < 0) nv = [-nv[0], -nv[1]];
    const L = 60, W = 22, a = [p1[0] - u[0] * L - nv[0] * 2, p1[1] - u[1] * L - nv[1] * 2], b = [p2[0] + u[0] * L - nv[0] * 2, p2[1] + u[1] * L - nv[1] * 2];
    const Q = kirp(Y.P, ccw([a, b, [b[0] + nv[0] * (W + 2), b[1] + nv[1] * (W + 2)], [a[0] + nv[0] * (W + 2), a[1] + nv[1] * (W + 2)]]));
    if (!Q) return;
    const g = Y.grup(); g.add(levha(Q, TM0, TM1, mat('ridge', AD.tersmahya)));
    add(AD.tersmahya, g, ro++ * 0.3, { kod: null, ad: M.tersmahya.ad, satir: [['Bu parça', `${Y.ad}, ${Y.dere_yan} dere hattı · ${Math.round(el)} cm`], ['Görev', M.tersmahya.gorev], ['Liste', M.tersmahya.liste]] });
  });
  // Kaplama (62 m²: trapez sac 27/200-6, 100 cm kapatır, 0,5 mm; Lokman). Levhalar her yüzün verideki başından (D.yuz.*.serit) dizilir;
  // son levha enine kesilir, dere ve mahya hattında açıyla kesilir. Hadveler plan ekseni boyunca verideki yerlerde (D.kaplama.hadve).
  const KM = D.kaplama.metin, KW = KP.kapatir;
  const dizi = (bas, son, yon) => { const out = []; for (let v = bas; yon * (son - v) > 0.5; v += yon * KW) out.push(yon > 0 ? [v, Math.min(son, v + KW)] : [Math.max(son, v - KW), v]); return out; };
  let so = 0;
  Object.entries(YUZ).forEach(([k, Y]) => {
    const S = Y.serit, enine = Y.eksen === 'y';
    const tAt = v => enine ? Y.tOf(Y.E[0], v) : Y.tOf(v, Y.E[1]);
    const ribs = D.kaplama.hadve[Y.hadve].map(tAt);
    dizi(S.bas, S.son, S.yon).forEach(([v0, v1]) => {
      const [t0, t1] = [tAt(v0), tAt(v1)].sort((a, b) => a - b);
      const Q = Y.icbukey ? kirp(Y.P, dikd(-1.35, Y.R.SL + 2, t0, t1)) : kirp(dikd(-1.35, Y.R.SL + 2, t0, t1), Y.P); if (!Q) return;   // içbükey yüz şeritle kırpılır (İE-24)
      const g = Y.grup(), m = mat('roof', AD.kaplama); g.add(levha(Q, TR0, TR1, m));
      ribs.forEach(tc => {
        if (tc < t0 - 0.01 || tc >= t1 - 0.01) return;   // levha sınırındaki hadve tek levhaya
        const iv = aralik(Q, 1, Math.min(Math.max(tc, t0 + 0.05), t1 - 0.05)); if (!iv || iv[1] - iv[0] < 4) return;
        const rb = mesh(new THREE.ExtrudeGeometry(RIB, { depth: (iv[1] - iv[0]) / 100, bevelEnabled: false }), m);
        rb.rotation.y = Math.PI / 2; rb.position.set(iv[0] / 100, TR1 / 100, tc / 100); g.add(rb);
      });
      const en = Math.abs(v1 - v0), kes = kirp(dikd(-1.35, Y.R.SL + 2, t0, t1), [[-1e4, -1e4], [1e4, -1e4], [1e4, 1e4], [-1e4, 1e4]]);
      const acili = Math.abs(Math.abs(alan(Q)) - Math.abs(alan(kes))) > 450, oran = Math.abs(alan(Q)) / (KW * (Y.R.SL + 3.35));
      const durum = !acili && en > KW - 0.5 ? 'tam levha' : [en < KW - 0.5 ? `enine kesilmiş (${fmtc(en)} cm)` : '', acili ? 'dere ya da mahya hattında açıyla kesilir' : ''].filter(Boolean).join(', ');
      add(AD.kaplama, g, so++ * 0.22, { kod: KB('kaplama'), ad: oran < 0.45 ? KM.kesim : yaz(KM.ad, { ad: S.ad }), satir: [
        ['Bu parça', `${Y.ad} · ${durum}`], ['Profil', KM.profil], ['Dizilim', KM.dizilim], ['Renk', KM.renk], ['Liste', KM.liste], ...kartSat(KB('kaplama'))] });
    });
  });
  // Mahya: her beşiğin mahyası, hadve tepelerinin üstünde; yüksekliği verideki çatının (topR) mahyasından
  D.kaplama.mahya.forEach((e, j) => {
    const R = RF[e.R], T = RF[e.topR], top = ysR(T, T.M) + (PTOP + 0.8) / T.cos, [z0, z1] = e.z;
    [1, -1].forEach((side, i) => {
      const w = cerceve(e.r, ...e.O), o = lb(-13, 13, -0.3, 0.3, z0, z1, mat('ridge', AD.kaplama));
      o.position.x = (e.s0 - side * R.cos * 12) / 100; o.position.y = (top - R.sin * 12 + 1) / 100; o.rotation.z = side * R.th; w.add(o);
      add(AD.kaplama, w, 9 + (j * 2 + i) * 0.3, { kod: KB('mahya'), ad: KM.mahya_ad, satir: [['Bu parça', `${e.ad} · ${fmtc(z1 - z0)} cm`], ['Liste', KM.mahya_liste], ...kartSat(KB('mahya'))] });
    });
  });
}

/* Alın sacı (kalkanlar), dere ve iniş */
let to = 0;
const ALIN_ALT = -3 - SAC - 6;   // Lokman, 26.10.2026: ayrı alt uç parçası yok; alın sacı dereyi de içine alacak kadar geniş (saçak altından 6 cm aşağı)
const MA = M.alin, ALIN_H = fmt(PTOP - ALIN_ALT, 0);
KALKAN.forEach(G => ['A', 'B'].forEach(end => {
  const K = rake(G, end, mat('trim', AD.alin)), ot = G.oTip;
  K.lev(G.ob + SAC, ot, -3 - SAC, -3);                       // tırnak (Z'nin alt kanadının altında) + saçak altı
  const uz = G.altUc[end] ? 16.5 : 0, KU = rake(G, end, mat('trim', AD.alin), uz);
  KU.lev(ot, ot + SAC, ALIN_ALT, PTOP);                      // alın: saçak altının 6 cm altından kaplamanın kenar hadvesinin üstüne; köşede dereyi de içine alır
  const k1 = RIB_KENAR + RIB_UST / 2 - 0.2, k2 = RIB_KENAR + RIB_TABAN / 2 - 0.1;   // kenar hadvesinin tepe ve taban iç kenarı (alın yüzünden)
  KU.lev(ot - k1, ot + SAC, PTOP - 0.1, PTOP);             // kıvrım: kenar hadvesinin tepesinin üstünden içeri
  KU.egik(ot - k1, PTOP - 0.1, ot - k2, TR1 + 0.5);        // hadveyi kavrayan kıvrım: hadvenin iç yüzü boyunca aşağı
  const nm = `${G.ad} · ${end === 'A' ? 'ön/sol' : 'arka/sağ'} yüz`;
  add(AD.alin, KU.w, to++ * 0.5, { kod: KB('alin'), ad: MA.ad, satir: [['Bu parça', `${nm} · alın ve üst kıvrımlar${uz ? '; köşede derenin ucunu da içine alacak kadar uzar' : ''}`], ['Alın', yaz(MA.alin, { h: ALIN_H })], ['Kaynak', MA.kaynak], ...kartSat(KB('alin'))] });
  add(AD.alin, K.w, to++ * 0.5, { kod: KB('alin'), ad: MA.ad, satir: [['Bu parça', `${nm} · L ${Math.round(K.Ls)} cm`], ['Profil', MA.profil], ['Uçta', MA.uc], ['Bu proje', yaz(MA.proje, { h: ALIN_H })], ['Liste', MA.liste], ...kartSat(KB('alin'))] });
  // Ayrı alt uç parçası yok (Lokman, 26.10.2026): alın sacının kendisi dereyi de içine alacak kadar geniş
}));
// Dere: galvaniz eksiz oluk, K kesit (38'lik açınım), boyalı; sırtı saçak sacının alnına asılır
const DERE_K = [[0, 11.4], [0, 0], [9, 0], [10, 0.8], [10.6, 2.6], [12, 3.6], [13, 5.6], [13.4, 8.6], [14.6, 10.2], [15, 11.4], [14, 11.4]];
const DERE_ALT = TB - 0.05 + 13 - 0.4 - 11.4;   // üstü alının 4 mm altında
const HAT = Object.fromEntries(D.dere.hatlar.map(h => [h.ad, h]));
const dereSerit = h => serit(h.yon === 'x' ? 'h' : 'v', h.kenar, h.out);   // yerel x dışa: 0 = saçak sacının alnı
const MD = M.dere, MI = M.inis;
D.dere.hatlar.forEach((h, i) => {
  const S = dereSerit(h), g = S.yeni(), m = mat('gutter', AD.dere), [z0, z1] = [S.zOf(h.a0), S.zOf(h.a1)].sort((p, q) => p - q), L = (z1 - z0) / 100;
  const sh = thick(DERE_K.map(([u, v]) => [u + SAC + 0.03, v]), 0.05);
  const k = mesh(new THREE.ExtrudeGeometry(sh, { depth: L, bevelEnabled: false }), m); k.position.set(0, DERE_ALT / 100, z0 / 100); g.add(k);
  const kap = new THREE.Shape(); DERE_K.slice(0, 10).forEach(([u, v], j) => j ? kap.lineTo((u + SAC + 0.03) / 100, v / 100) : kap.moveTo((u + SAC + 0.03) / 100, v / 100)); kap.closePath();
  [z0 / 100 - 0.001, z1 / 100].forEach(zz => { const c = mesh(new THREE.ExtrudeGeometry(kap, { depth: 0.001, bevelEnabled: false }), m); c.position.set(0, DERE_ALT / 100, zz); g.add(c); });
  add(AD.dere, g, i, { kod: KB('dere'), ad: MD.ad, satir: [['Bu parça', `${h.ad} hat · ${fmtc(h.a1 - h.a0)} cm (paftada ${fmtc(h.pafta)}) · iki ucunda kapak`], ['Kesit', MD.kesit], ['Pafta', MD.pafta], ['Liste', MD.liste], ...kartSat(KB('dere'))] });
});
D.dere.inisler.forEach((p, i) => {
  // Lokman'ın fotoğrafları (25–26.10.2026): köşede iniş aparatı derenin uç kısmında, borunun tam hizasında; kaz boynu (2 açık dirsek)
  // duvara (verandada kolona) dik döner; boru köşe direği kaplamasının (13 cm) hemen yanından 2 kelepçeyle iner, altta kapalı dirsek.
  const h = HAT[p.hat], S = dereSerit(h), w = S.yeni(), m = mat('gutter', AD.dere), ust = DERE_ALT;   // cm
  const kolon = p.sw !== undefined;   // verandada boru kolonun yerinde (p.sw)
  const yuzU = (p.yuz - h.kenar) * h.out;   // duvar yüzünün yerel x'i (dışa pozitif)
  const sw = kolon ? p.sw : Math.min(D.dis[p.dis] - 17, Math.max(17, p.s));                 // boru: köşe direği kaplamasının yanında ya da kolonda
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
  add(AD.dere, w, 4 + i * 0.5, { kod: KB('inis'), ad: MI.ad, satir: [['Bu parça', `${h.ad} hattı · ${p.duvar} boyunca`], ['Ağız', kolon ? MI.agiz_kolon : (p.kose !== undefined ? p.kose : p.s < 17 || p.s > D.dis[p.dis] - 17) ? MI.agiz_kose : MI.agiz], ['Kesit', MI.kesit], ['Takım', MI.takim], ['Pafta', MI.pafta], ['Liste', MI.liste], ...kartSat(KB('inis'))] });
});

/* İç kapılar (kanat yeri ve açılışı paftadan) */
D.doors.forEach((d, i) => {
  const g = new THREE.Group();
  g.position.set(X(d.hinge[0]), 0, Z(d.hinge[1]));
  const leaf = mesh(new THREE.BoxGeometry(0.80, 1.96, 0.04), mat('door', AD.dograma));
  leaf.position.set(0.41, 0.98, 0); g.add(leaf);
  const kn = mesh(new THREE.BoxGeometry(0.025, 0.12, 0.08), mat('steel', AD.dograma)); kn.position.set(0.72, 1.02, 0); g.add(kn);
  const a0 = Math.atan2(d.closed[1], d.closed[0]);
  let da = Math.atan2(d.open[1], d.open[0]) - a0; da = Math.atan2(Math.sin(da), Math.cos(da));
  g.rotation.y = a0;
  add(AD.dograma, g, i, { kod: M.ic_kapi.kod, ad: kart(M.ic_kapi.kod), satir: [['Oda', roomName(d.room)], ['Bu proje', M.ic_kapi.not], ...kartSat(M.ic_kapi.kod)] }, { ackapa: [{ el: g, tip: 'don', taban: a0, max: da * 0.9 }] });
});
/* Pencereler ve dış kapı (doğrama adımında kanatlar ve kapılar sırayla açılıp kapanır, Lokman 26.10.2026). Pencere tipleri veriden (D.pencere):
   b180 = Lokman'ın 180/180 çizimi (4 bölme), acilir = ilk kanat içe döner, surgulu = ikinci kanat kayar, vasistas = alttan devrilir. */
{
  const MK = M.dis_kapi_kanat;
  let wo = 3;
  D.panels.filter(p => p.op && (p.op.kind === 'win' || p.op.kind === 'door_ext')).forEach(p => {
    const [x0, y0, x1, y1] = p.rect, op = p.op, g = new THREE.Group(), c = p.o === 'h' ? (y0 + y1) / 2 : (x0 + x1) / 2;
    const out = p.o === 'h' ? (c > D.dis[1] / 2 ? 1 : -1) : (c > D.dis[0] / 2 ? 1 : -1), ic = -out;   // ic: odanın içine doğru (plan)
    const kutu = (hedef, a0, a1, d0, d1, h0, h1, m, sh = true) => {
      const o = p.o === 'h' ? bp(a0, a1, d0, d1, h0, h1, m) : bp(d0, d1, a0, a1, h0, h1, m); o.castShadow = sh;
      if (hedef !== g) o.position.sub(hedef.position);
      hedef.add(o);
    };
    const box = (...a) => kutu(g, ...a);
    const mentese = (al, ac, h) => { const v = new THREE.Group(); const [px, py] = p.o === 'h' ? [al, ac] : [ac, al]; v.position.set(X(px), h / 100, Z(py)); g.add(v); return v; };
    // hareket: don = düşey menteşede içe döner, devir = alttan içe devrilir (vasistas), kay = duvar boyunca kayar
    const don = (v, yon, max = 1.25) => ({ el: v, tip: 'don', max: max * (p.o === 'h' ? yon * ic : -ic * yon) });
    const devir = (v, max = 0.3) => ({ el: v, tip: 'devir', ax: p.o === 'h' ? 'x' : 'z', max: max * -ic });
    const kay = (v, d) => ({ el: v, tip: 'kay', ax: p.o === 'h' ? 'x' : 'z', p0: v.position[p.o === 'h' ? 'x' : 'z'], max: (p.o === 'h' ? 1 : -1) * d / 100 });
    const { a0, a1, s: sill, top } = op, f = 5, dpt = 3.5;
    const fm = mat(op.kind === 'win' ? 'pvc' : 'cdoor', AD.dograma), gm = mat('glass', AD.dograma);
    const kanatKur = (v, b0, b1, d, i0, i1, kf) => {   // kanat çerçevesi (köşelerde üst üste binmeden) + cam
      kutu(v, b0, b0 + kf, d - 3.25, d + 3.25, i0, i1, fm); kutu(v, b1 - kf, b1, d - 3.25, d + 3.25, i0, i1, fm);
      kutu(v, b0 + kf, b1 - kf, d - 3.25, d + 3.25, i1 - kf, i1, fm); kutu(v, b0 + kf, b1 - kf, d - 3.25, d + 3.25, i0, i0 + kf, fm);
      kutu(v, b0 + kf, b1 - kf, d - 0.3, d + 0.3, i0 + kf, i1 - kf, gm, false);
    };
    const W = op.kind === 'win' ? PW[op.size] : null;
    if (W && W.tip === 'b180') {   // Lokman çizimi (26.10.2026): 178 × 178 (iki yanda 1'er cm pervaz payı), 4 bölme: iki yanda sabit, ortada iki açılır kanat
      const dis = c + out * p.t / 2;
      const W0 = a0 + 1, W1 = a1 - 1, H0 = sill + 1, H1 = top - 1, ff = 5, mw = 8, bw = (W1 - W0 - 2 * ff - 2 * mw) / 4, kf = 4.5;
      box(W0, W0 + ff, c - dpt, c + dpt, H0, H1, fm); box(W1 - ff, W1, c - dpt, c + dpt, H0, H1, fm);
      box(W0 + ff, W1 - ff, c - dpt, c + dpt, H1 - ff, H1, fm); box(W0 + ff, W1 - ff, c - dpt, c + dpt, H0, H0 + ff, fm);
      const bay = k => W0 + ff + k * bw + (k >= 1 ? mw : 0) + (k >= 3 ? mw : 0), i0 = H0 + ff, i1 = H1 - ff, d = c + ic * 0.6;
      [1, 3].forEach(k => box(bay(k) - mw, bay(k), c - dpt, c + dpt, i0, i1, fm));   // sabit bölmelerle kanatlar arasındaki kayıtlar; ortada kayıt yok, kanatlar birbirine kapanır
      const hk = [];
      [0, 1, 2, 3].forEach(k => {
        const b0 = bay(k), b1 = b0 + bw;
        if (k === 1 || k === 2) {   // açılır kanatlar: ortada buluşur, menteşeler dış kayıtlarda, içe açılır (Lokman'ın gönderdiği görsel)
          const hinge = k === 1 ? b0 : b1, v = mentese(hinge, d + ic * 3.25, 0);
          kanatKur(v, b0, b1, d, i0, i1, kf); hk.push(don(v, k === 1 ? 1 : -1, 1.2));
        } else box(b0, b1, c - 0.3, c + 0.3, i0, i1, gm, false);   // sabit cam
      });
      const pv = 5, pt = 0.6, e0 = Math.min(dis, dis + out * pt), e1 = Math.max(dis, dis + out * pt);   // dış pervaz: 1 cm payın ve kasanın 1 cm'sinin üstüne biner
      box(a0 - 3, a0 + 2, e0, e1, sill - 3, top + 3, fm); box(a1 - 2, a1 + 3, e0, e1, sill - 3, top + 3, fm);
      box(a0 + 2, a1 - 2, e0, e1, top - 2, top + 3, fm); box(a0 + 2, a1 - 2, e0, e1, sill - 3, sill + 2, fm);
      add(AD.dograma, g, wo++, { kod: W.kod || null, ad: kart(W.kod || null, W.ad), satir: [['Bu parça', `boşluk 180 × 180 · pencere 178 × 178 (iki yanda 1’er cm pervaz payı) · eşik ${op.s} cm`], ['Bölme', '4 bölme: iki yanda sabit cam, ortada iki açılır kanat (çift açılım)'], ['Renk', M.pvc_renk], ['Pervaz', 'orta kayıttan, dıştan biner; içte pervaz matik'], ['Not', 'verilen ölçüler iç ölçüdür'], ['Oda', roomName(p.room)], ['Liste', W.liste], ['Kaynak', 'Lokman çizimi 180/180 (26.10.2026)']] }, { ackapa: hk });
      return;
    }
    box(a0, a0 + f, c - dpt, c + dpt, sill, top, fm); box(a1 - f, a1, c - dpt, c + dpt, sill, top, fm);
    box(a0 + f, a1 - f, c - dpt, c + dpt, top - f, top, fm);
    if (op.kind === 'win') {
      box(a0 + f, a1 - f, c - dpt, c + dpt, sill, sill + f, fm);
      const wide = a1 - a0 > 100, am = (a0 + a1) / 2, i0 = sill + f, i1 = top - f, hk = [];
      if (wide) box(am - 3, am + 3, c - dpt + 0.5, c + dpt - 0.5, i0, i1, fm);
      const panes = wide ? [[a0 + f, am - 3], [am + 3, a1 - f]] : [[a0 + f, a1 - f]];
      panes.forEach(([b0, b1], j) => {
        if (W.tip === 'vasistas') {   // vasistas: alttan içe devrilir
          const v = mentese((b0 + b1) / 2, c + ic * 3.25, i0); kanatKur(v, b0, b1, c + ic * 0.6, i0, i1, 4); hk.push(devir(v, 0.3));
        } else if (W.tip === 'surgulu' && j === 1) {   // sürgülü: ikinci kanat içten öbürünün önüne kayar
          const v = mentese(0, 0, 0); kanatKur(v, b0, b1, c + ic * 4.2, i0, i1, 3.5); hk.push(kay(v, -(b1 - b0) * 0.8));
        } else if (W.tip === 'acilir' && j === 0) {   // çift açılım: dış kayıttaki menteşede içe döner
          const v = mentese(b0, c + ic * 3.85, 0); kanatKur(v, b0, b1, c + ic * 0.6, i0, i1, 4); hk.push(don(v, 1, 1.2));
        } else box(b0, b1, c - 0.3, c + 0.3, i0, i1, gm, false);
      });
      const kod = W.kod || null;
      add(AD.dograma, g, wo++, { kod, ad: kart(kod, W.ad), satir: [['Bu parça', `${op.size} · eşik ${op.s} cm · ${M.pvc_renk_kisa}, pervaz matik`], ['Oda', roomName(p.room)], ['Liste', W.liste], ...kartSat(kod)] }, hk.length ? { ackapa: hk } : undefined);
    } else {   // çelik dış kapı: içe açılır; menteşe verideki yanda (op.mentese; 62 m²: sağ), kol öbür yanda
      const sol = op.mentese === 'sol', v = mentese(sol ? a0 + f : a1 - f, c + ic * 2.25, 0);
      kutu(v, a0 + f, a1 - f, c - 2.25, c + 2.25, 0, top - f, mat('cdoor', AD.dograma));
      const hx = sol ? a1 - f - 8.5 : a0 + f + 6; kutu(v, hx, hx + 2.5, c - 4.5, c + 4.5, 98, 112, mat('steel', AD.dograma));
      add(AD.dograma, g, wo++, { kod: MK.kod, ad: kart(MK.kod), satir: [['Bu parça', `boşluk ${Math.round(a1 - a0)} × ${top} cm · ${MK.kanat}`], ['Oda', roomName(p.room)], ['Liste', MK.liste], ...kartSat(MK.kod)] }, { ackapa: [don(v, sol ? 1 : -1, 1.35)] });
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
  if (list.some(p => p.anim && p.anim.ackapa)) return { stagger: 0.75, dur: 3.2, total: maxO * 0.75 + 3.2 };   // kanatlar ve kapılar: sırayla açılıp kapanır
  const stagger = maxO > 0 ? Math.min(per, (oda ? 4.6 : 2.6) / maxO) : 0;
  return { stagger, dur: 0.6, total: maxO * stagger + 0.6 };
});
const DROP = D.adimlar.map(a => a.drop);   // parçanın düştüğü yükseklik (m); alçıpan gibi alttan gelenlerde eksi

function cardRows(steps) {
  const c = new Map();
  parts.filter(p => steps.includes(p.step)).forEach(p => {
    const i = p.obj.userData.info, k = (i.kod || '') + '|' + i.ad;
    c.set(k, { kod: i.kod, ad: i.ad, n: (c.get(k)?.n || 0) + 1 });
  });
  return [...c.values()].sort((a, b) => (a.kod || 'zz').localeCompare(b.kod || 'zz', 'tr', { numeric: true }) || a.ad.localeCompare(b.ad, 'tr')).map(v => [v.kod, v.ad, v.n + ' adet', v.kod ? null : 'model']);
}
/* Adımlar veriden (D.adimlar): başlık, metin, liste satırları ([kart, ad, değer, kaynak]; '-' kartsız bilgi, 'grp' başlık), kamera, düşme.
   Yazılardaki {ad} yerleri modelden sayılır (SAY); oda adımlarının metni odanın kaydından (D.rooms[].metin). */
const SAY = {
  N, alt_dis: fmt(D.alt_m.dis), alt_ic: fmt(D.alt_m.ic),
  omega_ic_n: parts.filter(q => q.step === AD.omega && q.obj.userData.info.ad.includes('(iç duvar üstü)')).length,
  omega_ic_m: fmt(D.omega_duvar.filter(o => o.tur === 'ic').reduce((a, o) => a + o.a1 - o.a0, 0) / 100),
  izo_n: parts.filter(q => q.step === AD.izo).length,
  izo_m2: fmt(parts.filter(q => q.step === AD.izo).reduce((t, q) => t + q.obj.children[0].geometry.parameters.width * q.obj.children[0].geometry.parameters.depth, 0), 0),
  kaplama_n: parts.filter(q => q.step === AD.kaplama && q.obj.userData.info.ad.startsWith(D.kaplama.metin.say_onek)).length,
};
const satir = r => r.map((c, j) => j === 2 && typeof c === 'string' ? yaz(c, SAY) : c);
const STEPS = D.adimlar.map(a => {
  if (a.oda) { const r = ROOM[a.oda]; return { t: `${r.ad} (${fmt(r.m2, 2)} m²)`, p: r.metin, room: r.id, ad: r.ad, name: r.ad }; }
  return { t: yaz(a.t, SAY), p: yaz(a.p, SAY), head: a.head, ad: a.ad, name: a.ad, kamera: a.kamera, rows: a.rows && a.rows.map(satir), extra: a.extra && a.extra.map(satir) };
});
STEPS.forEach((st, i) => {
  if (i === 0 || st.rows) return;
  st.rows = cardRows([i]).concat(st.extra || []);
});
// Genel bakış: gruplu liste (D.genel: {grp} başlık, {pre, adlar} karttan ve addan seçilen satırlar, ya da hazır satır)
{
  const all = cardRows(Array.from({ length: N }, (_, i) => i + 1));
  const pick = (pre, adlar = []) => all.filter(r => (r[0] && pre.some(p => r[0].startsWith(p))) || (!r[0] && adlar.some(a => r[1].startsWith(a))));
  STEPS[0].rows = D.genel.flatMap(e => Array.isArray(e) ? [satir(e)] : e.grp ? [['grp', e.grp]] : pick(e.pre, e.adlar));
}
const NAMES = STEPS.map(s => s.ad);

/* ---------- Kamera ---------- */
function roomCenter(id) {
  let ax = 0, ay = 0, aw = 0;
  ROOM[id].rects.forEach(([x0, y0, x1, y1]) => { const w = (x1 - x0) * (y1 - y0); ax += (x0 + x1) / 2 * w; ay += (y0 + y1) / 2 * w; aw += w; });
  return [ax / aw, ay / aw];
}
function preset(step, aspZorla) {
  let t, az, el, dist;
  const st = STEPS[step];
  if (st.room) { const [cx, cy] = roomCenter(st.room); t = [X(cx), 0.7, Z(cy)]; az = 0.5; el = 1.0; dist = ROOM[st.room].kamera || 8; }
  else {
    const K = st.kamera;   // hedef: plan (cm, yükseklik m) ya da sahne (m); yön açısı, yükseklik açısı, uzaklık
    t = K.plan ? [X(K.t[0]), K.t[1], Z(K.t[2])] : K.t; az = K.az; el = K.el; dist = K.d;
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
const ROOF_STEPS = D.cati_adim;   // doğrama adımında gizlenen çatı, tavan ve izolasyon adımları
function applyVisibility() {
  const upto = cur === 0 ? N : cur;
  for (let s = 1; s <= N; s++) groups[s].visible = s <= upto && !(cutaway && ROOF_STEPS.includes(s));
  const b = $('roofTog'); b.setAttribute('aria-pressed', String(cutaway)); b.textContent = cutaway ? 'Çatıyı göster' : 'Çatıyı gizle';
  if (selHelper && !isShown(selObj)) clearSel();
}
function goTo(i, animate = true) {
  cur = Math.max(0, Math.min(N, i));
  cutaway = cur === N;
  for (const p of parts) { p.obj.visible = true; p.obj.position.y = p.y; if (p.anim && p.anim.ackapa) ackapaAyarla(p.anim.ackapa, 0); if (p.anim && p.anim.serme) sermeAyarla(p.anim.serme, 1); }
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
  $('badgeNo').textContent = cur === 0 ? D.rozet : isRoom ? `Oda ${roomIdx} · adım ${cur}/${N}` : `Adım ${cur} / ${N}`;
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
  const sec = { 1: 'Zemin', [ODA0]: 'Oda oda dizilim', [ODA1 + 1]: M.bolum_cati, [N]: 'Bitirme' };
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
      if (p.anim && p.anim.ackapa) { const q = Math.min(1, k); ackapaAyarla(p.anim.ackapa, q < 0.25 ? 0 : Math.sin(Math.PI * (q - 0.25) / 0.75)); p.obj.position.y = p.y + (1 - easeOut(Math.min(1, q / 0.25))) * DROP[cur]; }
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
window.__montaj = { goTo, parts, STEPS, camera, THREE, controls, preset, N, serme: e => parts.forEach(p => p.anim && p.anim.serme && sermeAyarla(p.anim.serme, e)), ackapa: a => parts.forEach(p => p.anim && p.anim.ackapa && ackapaAyarla(p.anim.ackapa, a)), kamera: (p, t) => { tween = null; camera.position.set(...p); if (controls) { controls.target.set(...t); controls.update(); } } };
