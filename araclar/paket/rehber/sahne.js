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
// Sandviç panel (D-40; Lokman, 1.11.2026): alt sac, yalıtım (verideki `yalitim`), üst sac ve hadveler; tek kat panelde (62 m²) yalıtım yok.
const YAL = KP.yalitim || 0;
const AH = 3.0 + SAC, TM0 = AH + 0.02, TM1 = TM0 + 0.1, TR0 = TM1 + 0.02, TR1 = TR0 + 0.05;   // kaplama 0,5 mm
const TU1 = YAL ? TR1 + YAL + 0.05 : TR1, PTOP = TU1 + RIBH + 0.1;   // TU1: hadvelerin tabanı (sandviçte üst sacın üstü)
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
  kopuk:    { color: 0xeccf6e, roughness: 0.95, polygonOffset: true, polygonOffsetFactor: 2, polygonOffsetUnits: 2 },   // poliüretan (sarı); üst sacın altında kalır (derinlik çakışması yok)
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
const plak = bp(D.zemin[0], D.zemin[1], D.zemin[2], D.zemin[3], -12, 0, mat('concrete', 0));
scene.add(plak);
/* İE-15 K6 · Ön onay sayfası evin altında (Lokman, 5 Kasım 2026 00:53, TK-01 rehberi): Motor'un A4 sayfası gerçek ölçekte, kat planı evin
   tam altına oturur; sayfa varken temel plak gizli. Görüntü ve yer `kagit.py`'den (`dxf_out.a4_cercevesi`); sayfasız rehberde null. */
const KAGIT = __KAGIT__;
if (KAGIT) {
  plak.visible = false;
  const img = new Image(), tex = new THREE.Texture(img);
  tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 16;
  img.onload = () => { tex.needsUpdate = true; };
  img.src = KAGIT.src;
  const [x0, x1] = KAGIT.x, [y0, y1] = KAGIT.y;
  const kagit = new THREE.Mesh(new THREE.PlaneGeometry((x1 - x0) / 100, (y1 - y0) / 100), new THREE.MeshStandardMaterial({ map: tex, roughness: 0.92 }));
  kagit.name = 'Ön onay sayfası'; kagit.rotation.x = -Math.PI / 2; kagit.position.set(X((x0 + x1) / 2), -0.002, Z((y0 + y1) / 2)); kagit.receiveShadow = true;
  scene.add(kagit);
}

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
  const [x0, y0, x1, y1] = p.rect, op = p.op, s = p.step, dvr = !!p.karkas || (!p.card && /DVR/.test(p.ad || ''));   // D-46: karkaslı kaplama duvar panosu
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
  else if (p.ops && p.ops.length > 1) {   // D-46: birden çok açıklıklı karkaslı pano; açıklıkların arası tam boy, altı ve üstü dolu
    const fm = mat('steel', s), t = p.t + 1.2, f = 2.2;
    const across = p.o === 'h' ? [(y0 + y1) / 2 - t / 2, (y0 + y1) / 2 + t / 2] : [(x0 + x1) / 2 - t / 2, (x0 + x1) / 2 + t / 2];
    const fr = (b0, b1, h0, h1, m) => g.add(p.o === 'h' ? bp(b0, b1, across[0], across[1], h0, h1, m) : bp(across[0], across[1], b0, b1, h0, h1, m));
    let u = along[0];
    [...p.ops].sort((a, b) => a.a0 - b.a0).forEach(o => {
      if (o.a0 > u) piece(u, o.a0, 0, H, pm);
      if (o.s > 0) piece(o.a0, o.a1, 0, o.s, pm);
      piece(o.a0, o.a1, o.top, H, pm);
      const m = o.kind === 'door' ? mat('kasa', s) : fm;
      fr(o.a0, o.a1, o.top - f, o.top, m); if (o.s > 0) fr(o.a0, o.a1, o.s, o.s + f, m);
      fr(o.a0, o.a0 + f, o.s, o.top, m); fr(o.a1 - f, o.a1, o.s, o.top, m);
      u = o.a1;
    });
    if (along[1] > u) piece(u, along[1], 0, H, pm);
  } else {
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
  const yapi = p.karkas ? [['Yapı', 'karkaslı kaplama duvar panosu: tek parça çelik karkas, iki yüzü betopan; içinde derz ve H yok, pencerenin üst ve alt panosu ve özel pencere karkası yok'], ['Kaynak', 'İş Emri, montaj paftasındaki yerinden (D-46)']]
    : dvr ? [['Yapı', 'çelik karkas (alt ve üst başlık, dikmeler, pencere üstünde kafes başlık), iki yüzü betopan'], ['Kaynak', M.dvr_kaynak]]
    : op && op.kind === 'win' && PW[op.size].karkas ? [['Yapı', PW[op.size].tip === 'b180' ? '' : `alt pano ${op.s} cm + üst pano ${H - op.top} cm, özel pencere karkası (100'lük çektirme U'su + H)`]] : [];
  add(s, g, p.order, { kod: p.card, ad: kart(p.card, p.ad), satir: [['Bu parça', `boy ${fmtc(p.boy)} cm · ${p.tur === 'STD' ? 'standart' : 'özel boy'}`], ['Oda', roomName(p.room)], ['Duvar', `${p.duvar === 'dis' ? 'dış' : 'iç'} · ${fmtc(p.t)} cm`], ...(p.ops && p.ops.length > 1 ? p.ops.map(o => ['Açıklık', openTxt(o)]) : op ? [['Açıklık', openTxt(op)]] : []), ...yapi, ...(disYuz >= 0 && D.fuga ? [['Cephe', D.fuga.metin]] : []), ...kartSat(p.card)] });
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
  add(s, g, h.order, { kod: h.card, ad: kart(h.card, h.ad), satir: [['Bu parça', yer], ['Oda', roomName(h.room)], ...(h.card ? kartSat(h.card) : [['Liste', h.liste || M.ozel_h_liste]])] });
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
      add(AD.sacak, g, to++ * 0.5, { kod: KB('sacak'), ad: 'Saçak sacı', satir: [['Bu parça', `${e.ad} · L ${fmtc(a1 - a0)} cm`], ['Profil', 'tırnak 3 → saçak altı 30 → alın 13 → makasa doğru kıvrım 10; açınım ≈ 56 cm'], ['Sıra', 'aşıklardan sonra, dereden önce (Lokman, 26.10.2026)'], ['Uçta', 'saçak altı baş makasın (betopanının) hizasında kesilir; alın ve kıvrım köşeye, alın sacına kadar devam eder (Lokman, 26.10.2026)'], ...(e.not ? [['Bu çatıda', e.not]] : []), ['Liste', M.sacak_liste], ...kartSat(KB('sacak'))] });
    }
  });
}

/* Makaslar (62 m²: yerleri ve kesitleri SketchUp modelinden; iç çubuklar Alpha Mini düzeni: Warren). Her makasın çatısı (R), yönü
   (y: makas y boyunca, x: x boyunca), duvar hizasındaki dikmeleri (wl), göz sayısı (NB) ve ilk düğümü (T0) veriden. */
// dus: üst başlığın aşık oturma yüzünden aşağısı (cm). Baş makasta 1 mm: Z'nin üst kanadı makasla aşığın arasına girer (Lokman, 9.11.2026).
function makasKur(R, s0, s1, wl, NB, T0, m, dus = 0) {
  const g = new THREE.Group(), sm = R.M, off = CH / 2 / R.cos, yt = s => ysR(R, s) - dus / R.cos - off, yb = TB + CH / 2;
  g.add(lc(s0, yb, s1, yb, m));
  g.add(lc(s0, yt(s0), sm, yt(sm), m)); g.add(lc(s1, yt(s1), sm, yt(sm), m));
  // uç dikmeleri: üstü eğimin alçak kenarında biter, aşık oturma yüzünün üstüne taşmaz (Lokman, 9.11.2026: "çakışma olmasın tam değme olsun")
  [s0 + 2.25, s1 - 2.25].forEach(s => g.add(lc(s, TB, s, Math.min(ysR(R, s - 2.25), ysR(R, s + 2.25)) - dus / R.cos, m)));
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
  if (!ara) { const r = makasKur(R, mk.bas, mk.son, mk.wl, mk.NB, mk.T0, m, mk.rol === 'bas' ? SAC : 0); g = r.g; P = r.P; }
  else g = araMakas(R, mk.bas, mk.son, ysR(RF[mk.zR], mk.yuz), mk.nps, m);
  const w = mk.yon === 'y' ? cerceve(Math.PI / 2, mk.konum, 0) : cerceve(0, 0, mk.konum); w.add(g);
  const kod = mk.kod !== undefined ? mk.kod : ara ? null : mk.rol === 'bas' ? 'MA-01' : 'MA-02';   // İE-15 K6: çapraz cumbanın ara makası MA-05
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
// Baş makas Z'si ve alın sacının tırnağı (Lokman, 9.11.2026; çizim, ölçü ve "çakışma olmasın tam değme olsun"): Z'nin üst kanadı 4 cm (makasın
// ve betopanın üstünde), gövdesi 7 cm (betopanın dış yüzünde), tırnağı 3 cm, gövdeyle 30°, dışa ve yukarı. Alın sacının 3 cm tırnağı Z'nin
// gövdesi boyunca iner; alt ucu Z'nin tırnağının iç yüzüne değer (30°'lik kıvrımda daha aşağı inemez). Saçak altı tırnağın üst ucunda.
const Z_UST = 4, Z_GOVDE = 7, Z_TIRNAK = 3, Z_ACI = Math.PI / 6, ALIN_TIRNAK = 3, ZOB = BAS_DIS + BET_T;
const ZT0 = [ZOB + SAC / 2, -Z_GOVDE + SAC / 2], ZT1 = [ZT0[0] + Z_TIRNAK * Math.sin(Z_ACI), ZT0[1] + Z_TIRNAK * Math.cos(Z_ACI)];   // Z'nin tırnağının orta çizgisi
const TIRNAK_ALT = (ZT0[1] + SAC / 2 * Math.sin(Z_ACI)) + (ZOB + 2 * SAC - (ZT0[0] - SAC / 2 * Math.cos(Z_ACI))) / Math.tan(Z_ACI);   // değme noktası
const SACAK_ALTI = TIRNAK_ALT + ALIN_TIRNAK;   // alın sacının saçak altının üst yüzü (makas üstünden, eğime dik)
function rake(G, end, m, uzat = 0) {
  const sE = G.uc[end], dir = Math.sign(G.sm - sE), sT = sE - dir * (0.2 + uzat), sm = (sT + G.sm) / 2, Ls = Math.abs(G.sm - sT) / G.R.cos;
  const w = cerceve(G.r, ...G.O), g = new THREE.Group(); w.add(g);
  g.position.set(sm / 100, G.h(sm) / 100, 0); g.rotation.z = dir * G.R.th;
  // x0, x1: parçanın eğik kenar boyunca yeri (yerel x, ortadan; verilmezse kenarın tamamı). Mahya ucu düşey kesilir (mahya düzlemi:
  // x = dir · (Ls/2 + p · tan θ)); iki yüzün parçaları mahyada birbirine değer, içine girmez (Lokman, 9.11.2026: "çakışma olmasın tam değme olsun").
  // Dereyle bitmeyen saçak ucunda (altUc yok: yanındaki saçak aynı düzlemde sürer, 62 m²'de cumba) aşık oturma yüzünün üstündeki kısım
  // da düşey kesilir; yandaki saçağın sacına değer, üstüne binmez.
  const tn = Math.tan(G.R.th), dusey = !G.altUc[end];
  const uc = (x, p) => (Math.abs(x - dir * Ls / 2) < 1e-6 ? dir * (Ls / 2 + p * tn) : dusey && p > 0 && Math.abs(x + dir * Ls / 2) < 1e-6 ? dir * (-Ls / 2 + p * tn) : x);
  const parca = (kes, x0, x1) => {   // kes: kesitin dört köşesi [o, p] (sırayla); x0 < x1
    const c = [];
    [x0, x1].forEach(x => kes.forEach(([o, p]) => c.push([uc(x, p), p, o])));
    g.add(mesh(hex(c), m));
  };
  const lev = (o0, o1, p0, p1, x0 = -Ls / 2, x1 = Ls / 2) => parca([[o0, p0], [o1, p0], [o1, p1], [o0, p1]], x0, x1);
  const egik = (o0, p0, o1, p1, x0 = -Ls / 2, x1 = Ls / 2) => {   // orta çizgisi (o0, p0) → (o1, p1), kalınlığı SAC
    const l = Math.hypot(o1 - o0, p1 - p0), n = [-(p1 - p0) / l * SAC / 2, (o1 - o0) / l * SAC / 2];
    parca([[o0 - n[0], p0 - n[1]], [o1 - n[0], p1 - n[1]], [o1 + n[0], p1 + n[1]], [o0 + n[0], p0 + n[1]]], x0, x1);
  };
  // Çatının üstündeki kısım (C kapamanın üst kanadı, alın sacının kıvrımı) yalnız çatı yüzünün üstünde: saçak ucundan başlayarak (x, o)
  // noktası bu çatının bir yüzüne girene kadar kısalır (62 m²: sol kalkanın ön ucunda ana çatı yüzü dere hattıyla sivrilir, altı cumba).
  w.updateMatrixWorld();
  const plan = (x, o) => { const v = new THREE.Vector3((sm + x * G.R.cos) / 100, 0, o / 100).applyMatrix4(w.matrixWorld); return [(v.x + D.dis[0] / 200) * 100, (D.dis[1] / 200 - v.z) * 100]; };
  const yuzde = (x, o) => { const q = plan(x, o); return Object.values(YUZ).some(Y => Y.R === G.R && cokgende(Y.P, Y.yerel(q))); };
  const catida = (o, x0 = -Ls / 2, x1 = Ls / 2) => {
    const e = dir > 0 ? x0 : x1;
    for (let d = 0; d < 80; d += 0.25) if (yuzde(e + dir * d, o)) return d === 0 ? [x0, x1] : dir > 0 ? [e + d, x1] : [x0, e - d];
    return [x0, x1];
  };
  const xOf = (s, p = 0) => (s - sm + p * dir * Math.sin(G.R.th)) / G.R.cos;   // kalkan boyundaki s noktasının yerel x'i (p yüksekliğinde)
  return { w, Ls, lev, egik, dir, catida, xOf };
}
function cokgende(P, [x, y]) {   // nokta çokgenin içinde mi
  let c = false;
  for (let i = 0, j = P.length - 1; i < P.length; j = i++) { const [xi, yi] = P[i], [xj, yj] = P[j]; if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) c = !c; }
  return c;
}
// Altı yüzlü parça (cm): c[0..3] bir uçtaki kesit, c[4..7] öteki uçtaki aynı köşeler. Yüzler dışa bakar; userData.k8 köşeleri (m) tutar.
function hex(c) {
  const v = c.map(([x, y, z]) => new THREE.Vector3(x / 100, y / 100, z / 100)), mrk = v.reduce((a, p) => a.add(p), new THREE.Vector3()).multiplyScalar(1 / 8);
  const yuz = [[0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]], pos = [];
  yuz.forEach(f => {
    const [a, b, cc, d] = f.map(i => v[i]), nrm = new THREE.Vector3().subVectors(cc, a).cross(new THREE.Vector3().subVectors(d, b));
    const ym = new THREE.Vector3().add(a).add(b).add(cc).add(d).multiplyScalar(0.25).sub(mrk);
    const q = nrm.dot(ym) >= 0 ? [a, b, cc, a, cc, d] : [a, d, cc, a, cc, b];
    q.forEach(p => pos.push(p.x, p.y, p.z));
  });
  const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); geo.computeVertexNormals();
  geo.userData.k8 = v.map(p => p.toArray());
  return geo;
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
      if (Math.abs(G.uc[end] - G.duvar[end]) < 0.5) return;   // İE-15 K6: makas duvarın üstünde başlar (cumbanın baş makasının arkasında), dışarıda ucu yok
      // alt ucu duvar üstündeki parçalar gibi baş makas omegasının dış U yanağında: omega saçak ucundan saçak ucuna (D-32); önce saçak sacının
      // saçak altındaydı, omeganın 3 cm üstünde kalıyordu (Lokman, 31.10.2026: "baş makas omegasının tam arasına girmeli, uçlarda yukarıda kalmış")
      const sE = G.uc[end], dir = Math.sign(G.sm - sE), a = G.duvar[end], b = sE + dir * 0.2, yt = s => (G.h(s) - 0.2) / 100, alt = (H - BAS_KANAT) / 100;
      const sh = new THREE.Shape(); sh.moveTo(a / 100, alt); sh.lineTo(b / 100, alt); sh.lineTo(b / 100, yt(b)); sh.lineTo(a / 100, yt(a)); sh.closePath();
      const o = mesh(new THREE.ExtrudeGeometry(sh, { depth: BET_T / 100, bevelEnabled: false }), mat('betopan', AD.kalkan));
      o.position.z = G.oT / 100;
      const w = cerceve(G.r, ...G.O); w.add(o);
      add(AD.kalkan, w, bo++ * 0.5, { kod: null, ad: 'Baş makas betopanı · saçak ucu', satir: [['Bu parça', `${fmtc(Math.abs(b - a))} cm · ${G.ad}, ${end === 'A' ? 'ön/sol' : 'arka/sağ'} uç: makasın duvar dışında kalan ucu`], ['Oturma', 'alt ucu baş makas omegasının dış U yanağında (omega saçak ucuna kadar), üstü makasın üst başlığında; dışında baş makas Z’si ve alın sacı (Lokman, 31.10.2026)'], ['Malzeme', '125 × 250 betopanların artanından; 8 mm'], ['Görev', 'saçak sacı ile alın sacının birleştiği köşeyi kapatır'], ['Kaynak', 'Lokman, 26.10.2026']] });
    });
    ['A', 'B'].forEach(end => {   // Baş makas Z'si: üst kanat makasın ve betopanın üstünde, gövde betopanın dış yüzünde 7 cm iner, tırnak 30° dışa
      const zl = (K, x0, x1) => { K.lev(G.ob + SAC - Z_UST, G.ob + SAC, -SAC, 0, x0, x1); K.lev(G.ob, G.ob + SAC, -Z_GOVDE, 0, x0, x1); K.egik(...ZT0, ...ZT1, x0, x1); };
      const satir = (bu, ek = []) => [['Bu parça', bu], ...ek, ['Kesit', `üst kanat ${Z_UST} cm, makasın ve betopanın üstünde · gövde ${Z_GOVDE} cm · tırnak ${Z_TIRNAK} cm, gövdeyle 30°; sac 1 mm`], ['Alın sacı', `tırnağı (${ALIN_TIRNAK} cm) Z'nin gövdesi boyunca iner, Z'nin tırnağına oturur`], ['Liste', M.z_liste], ['Kaynak', 'Lokman çizimi ve ölçüsü (9.11.2026)'], ...kartSat(KB('z'))];
      const yz = `${G.ad} · ${end === 'A' ? 'ön/sol' : 'arka/sağ'} yüz`;
      const zu = G.altUc[end] ? 0 : -0.2;   // dereyle bitmeyen uçta Z makasın ucunda biter (62 m²: cumbanın makasına değer)
      if (!G.z_parca) {   // 62 m²: kenar başına tek parça
        const K = rake(G, end, mat('frame', AD.kalkan), zu); zl(K);
        add(AD.kalkan, K.w, 20 + bo++ * 0.5, { kod: KB('z'), ad: "Baş makas Z'si", satir: satir(`${yz} · L ${Math.round(K.Ls)} cm`) });
        return;
      }
      // kenarın parça sayısı kart modelinden (o kenardaki Z, ⌈eğik ÷ parça boyu⌉; liste de böyle sayar, D-39): saçak ucundan mahyaya, son parça kalan
      const n = G.z_n[end];
      for (let k = 0; k < n; k++) {
        const K = rake(G, end, mat('frame', AD.kalkan), zu), uc = -K.dir * K.Ls / 2, a = k * G.z_parca, b = k === n - 1 ? K.Ls : (k + 1) * G.z_parca;
        const [x0, x1] = [uc + K.dir * (a + (k ? 0.1 : 0)), uc + K.dir * (b - (k < n - 1 ? 0.1 : 0))].sort((p, q) => p - q);
        zl(K, x0, x1);
        add(AD.kalkan, K.w, 20 + bo++ * 0.5, { kod: KB('z'), ad: "Baş makas Z'si", satir: satir(`${yz} · ${k + 1}/${n}. parça · L ${Math.round(b - a)} cm`, [['Kenar', `L ${Math.round(K.Ls)} cm · ${n} parça (kart modelinde bu kenarın Z’si ${fmtc(G.z_kart[end])} cm: ⌈${fmtc(G.z_kart[end])} ÷ ${fmtc(G.z_parca)}⌉ = ${n}; liste de böyle sayar)`]]) });
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
  // Aşığın kalkan ucu C kapamanın gövdesine değer: alın sacının iç yüzünün 2 mm içinde biter (Lokman, 9.11.2026: "çakışma olmasın tam değme olsun")
  const KC = KALKAN.map(G => { const w = cerceve(G.r, ...G.O); w.updateMatrixWorld(); return { G, w, s0: Math.min(G.uc.A, G.uc.B) - 1, s1: Math.max(G.uc.A, G.uc.B) + 1 }; });
  const kalkanda = (Y, s, t) => {
    const [dx, dy] = Y.d, c = Y.R.cos, q = new THREE.Vector3(X(Y.E[0] + s * c * dx + t * dy), 0, Z(Y.E[1] + s * c * dy - t * dx));
    return KC.some(({ G, w, s0, s1 }) => { const v = w.worldToLocal(q.clone()); return Math.abs(v.z * 100 - G.oTip) < 0.05 && v.x * 100 > s0 && v.x * 100 < s1; });
  };
  Object.entries(YUZ).forEach(([k, Y]) => {
    let pr = 0;
    rows[k].forEach((sr, r) => {
      const iv = aralik(Y.P, 0, sr); if (!iv || iv[1] - iv[0] < 20) return;
      const kp = [kalkanda(Y, sr, iv[0]) ? 0.2 : 0, kalkanda(Y, sr, iv[1]) ? 0.2 : 0];
      iv[0] += kp[0]; iv[1] -= kp[1];
      // Uçlar yüzün kenarına göre kesilir: dere hattında (eğik kenar) aşığın her noktası kendi yerindeki kenarda biter, öbür yüzün altına
      // girmez (Lokman, 9.11.2026: "çakışma olmasın tam değme olsun"). Dik kenarda (kalkan, saçak) kesim aynı kalır.
      const ucKes = (geo, t0, len, ilk, son) => {
        const P = geo.attributes.position;
        for (let i = 0; i < P.count; i++) {
          const z = P.getZ(i) * 100, bas0 = Math.abs(z) < 1e-4, son0 = Math.abs(z - len) < 1e-4;
          if (!(bas0 && ilk) && !(son0 && son)) continue;
          const q = aralik(Y.P, 0, sr + P.getX(i) * 100 - P.getY(i) * 100 * Y.R.tan); if (!q) continue;
          if (bas0) P.setZ(i, (Math.min(q[0] + kp[0], t0 + len - 1) - t0) / 100); else P.setZ(i, (Math.max(q[1] - kp[1], t0 + 1) - t0) / 100);
        }
        P.needsUpdate = true; geo.computeVertexNormals(); return geo;
      };
      const pf = paf[k][pr++] || [iv[1] - iv[0]], L = iv[1] - iv[0];
      const cuts = []; let acc = 0;
      pf.forEach((p, j) => { const l = j === pf.length - 1 ? L - acc : Math.min(p, L - acc); if (l > 1) cuts.push([acc, acc + l, p]); acc += l; });
      cuts.forEach(([u0, u1, p]) => {
        const t0 = bas[k] === 'max' ? iv[1] - u1 : iv[0] + u0, len = u1 - u0;
        const g = Y.grup(), o = mesh(ucKes(omegaGeo(len, false), t0, len, Math.abs(t0 - iv[0]) < 1e-6, Math.abs(t0 + len - iv[1]) < 1e-6), mat('asik', AD.asik)); o.position.set(sr / 100, 0, t0 / 100); g.add(o);
        add(AD.asik, g, ao++ * 0.18, { kod: KB('asik'), ad: 'Aşık (omega)', satir: [['Bu parça', `${Y.ad}, ${r + 1}. sıra · paftada L ${fmtc(p)} cm`], ['Kesit', '87 × 30 mm, üst 35, sac 1 mm'], ['Sıra yeri', `saçaktan eğim boyunca ${fmtc(sr)} cm`], ['Liste', M.asik_liste], ...kartSat(KB('asik'))] });
      });
    });
  });
  // C kapama: kalkan saçağında aşık uçlarını kapatır
  KALKAN.forEach(G => ['A', 'B'].forEach(end => {
    const K = rake(G, end, mat('asik', AD.asik));
    // gövde aşık uçlarının önünde (aşık 2 mm önünde biter), üst kanadı aşıkların üstünde, alt kanadı saçak altının üstünde (Lokman, 9.11.2026)
    K.lev(G.oTip - 0.2, G.oTip - 0.2 + SAC, SACAK_ALTI, AH); K.lev(G.oTip - 2.2, G.oTip - 0.2, AH - SAC, AH, ...K.catida(G.oTip - 2.2)); K.lev(G.oTip - 2.2, G.oTip - 0.2, SACAK_ALTI, SACAK_ALTI + SAC);
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
// Sandviç panelde hadvenin içi poliüretan dolu (Lokman, 1.11.2026 10:46, görsel): üst sac hadvenin üstünde 0,5 mm'lik kabuk (RIB_SAC), içi sarı (RIB_IC)
const [RIB_SAC, RIB_IC] = (() => {
  const a = RIB_TABAN / 200, u = RIB_UST / 200, h = RIBH / 100, k = 0.0005, d = k * Math.hypot(a - u, h) / h;   // d: yan kenarda 0,5 mm'lik yatay pay
  const dis = [[-a, 0], [-u, h], [u, h], [a, 0]], ic = [[a - d, 0], [u - d * u / a, h - k], [-u + d * u / a, h - k], [-a + d, 0]];
  const sekil = P => { const s = new THREE.Shape(); P.forEach(([x, y], i) => i ? s.lineTo(x, y) : s.moveTo(x, y)); s.closePath(); return s; };
  return [sekil([...dis, ...ic]), sekil([...ic].reverse())];
})();
// Düz mahya (trapez sac dışındaki kaplamalar) hadvelerin tepesine oturur: trapez mahya gibi 0,6 mm üstünde, 0,5 mm (DM0 → DM1). Ucu kalkandaysa
// alın sacının iç yüzüne kadar uzanır; alın sacı en son takılır, üst kıvrımı mahyanın ucunu örter (Lokman, 10.11.2026 20:16: "önce trapez sac ve
// mahya gelir sonra alın sacı üzerini örter"; 21:01: "mahya ne olursa olsun alın sacının altına girecek yoksa bina yağmurlarda su alır").
// MAHYA_KALKAN: ucunda düz mahya biten kalkanlar (alın sacı orada mahyanın üstüne yatar).
const DM0 = TU1 + RIBH + 0.06, DM1 = DM0 + 0.05, MAHYA_KALKAN = new Set();
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
      if (YAL) { g.add(levha(Q, TR1, TR1 + YAL, mat('kopuk', AD.kaplama))); g.add(levha(Q, TR1 + YAL, TU1, m)); }   // sandviç: yalıtım ve üst sac
      ribs.forEach(tc => {
        if (tc < t0 - 0.01 || tc >= t1 - 0.01) return;   // levha sınırındaki hadve tek levhaya
        const iv = aralik(Q, 1, Math.min(Math.max(tc, t0 + 0.05), t1 - 0.05)); if (!iv || iv[1] - iv[0] < 4) return;
        const hadveKoy = (sekil, mm) => { const rb = mesh(new THREE.ExtrudeGeometry(sekil, { depth: (iv[1] - iv[0]) / 100, bevelEnabled: false }), mm);
          rb.rotation.y = Math.PI / 2; rb.position.set(iv[0] / 100, TU1 / 100, tc / 100); g.add(rb); };
        if (YAL) { hadveKoy(RIB_SAC, m); hadveKoy(RIB_IC, mat('kopuk', AD.kaplama)); } else hadveKoy(RIB, m);   // sandviç: sac kabuk + sarı dolgu
      });
      const en = Math.abs(v1 - v0), kes = kirp(dikd(-1.35, Y.R.SL + 2, t0, t1), [[-1e4, -1e4], [1e4, -1e4], [1e4, 1e4], [-1e4, 1e4]]);
      const acili = Math.abs(Math.abs(alan(Q)) - Math.abs(alan(kes))) > 450, oran = Math.abs(alan(Q)) / (KW * (Y.R.SL + 3.35));
      const durum = !acili && en > KW - 0.5 ? 'tam levha' : [en < KW - 0.5 ? `enine kesilmiş (${fmtc(en)} cm)` : '', acili ? 'dere ya da mahya hattında açıyla kesilir' : ''].filter(Boolean).join(', ');
      add(AD.kaplama, g, so++ * 0.22, { kod: KB('kaplama'), ad: oran < 0.45 ? KM.kesim : yaz(KM.ad, { ad: S.ad }), satir: [
        ['Bu parça', `${Y.ad} · ${durum}`], ['Profil', KM.profil], ['Dizilim', KM.dizilim], ['Renk', KM.renk], ['Liste', KM.liste], ...kartSat(KB('kaplama'))] });
    });
  });
  // Mahya: her beşiğin mahyası, hadve tepelerinin üstünde; yüksekliği verideki çatının (topR) mahyasından
  // kanat her yanda D.kaplama.mahya_kanat cm (trapez sac mahyası 35, metal kiremit mahyası 26; kart modelinin gösterim kesiti), mahyayı 1 cm aşar
  const KN = D.kaplama.mahya_kanat, KO = KN / 2 - 1;
  // Trapez sac mahyası sacla aynı biçimde (27/200) preslidir: iki kanadı mahyanın iki yanında KN cm, her hadvesi sacın hadvesinin üstüne oturur;
  // boyu levhanın kapattığı kadar, her levhanın üstünde bir mahya, bindirme yok (Lokman, 10.11.2026 04:45: bağlantıdaki "Trapez Mahya",
  // "Trapez mahya L:100 ve 35x35"; 17:01: "mahya düz"). Kanatlar iki yüzün kendi çerçevesinde kurulur, mahyanın üstünde birleşir.
  const planda = (w, sx, hy, z) => { const v = new THREE.Vector3(sx / 100, hy / 100, z / 100).applyMatrix4(w.matrixWorld); return [(v.x + D.dis[0] / 200) * 100, (D.dis[1] / 200 - v.z) * 100]; };
  if (D.kaplama.mahya_hadveli) {
    const MK = 0.06;   // mahya sacın üstünde 0,6 mm
    const n0 = TR1 + MK, n1 = n0 + 0.05, nh = TU1 + MK;
    // Kalkan ucunda mahya alın sacının üst kıvrımlarına değer, girmez: alının yüzünden kenar hadvesinin iç tabanına kadar (RIB_KENAR + RIB_TABAN / 2)
    // mahya yok (Lokman, 9.11.2026: "çakışma olmasın tam değme olsun"; M-17)
    const KK = KALKAN.map(G => { const w = cerceve(G.r, ...G.O); w.updateMatrixWorld(); return { G, w, s0: Math.min(G.uc.A, G.uc.B) - 1, s1: Math.max(G.uc.A, G.uc.B) + 1 }; });
    const kalkanUcu = ([x, y]) => KK.some(({ G, w, s0, s1 }) => { const v = w.worldToLocal(new THREE.Vector3(X(x), 0, Z(y))); return Math.abs(v.z * 100 - G.oTip) < 1.5 && v.x * 100 > s0 && v.x * 100 < s1; });
    const KES = RIB_KENAR + RIB_TABAN / 2 + 0.1;
    let mo = 0;
    D.kaplama.mahya.forEach(e => {
      const R = RF[e.R], w = cerceve(e.r, ...e.O); w.updateMatrixWorld();
      const yuzler = Object.values(YUZ).filter(Y => Y.R === R && Y.serit);
      // her yüzün levhaları (plan ekseni boyunca) ve mahyanın o yüzdeki t aralığı
      const kanat = yuzler.map(Y => {
        const enine = Y.eksen === 'y', tAt = v => enine ? Y.tOf(Y.E[0], v) : Y.tOf(v, Y.E[1]);
        const sM = Math.max(...Y.P.map(p => p[0])), tn = Math.tan(R.th);
        const Pe = ccw(Y.P.map(([s_, t_]) => [s_ >= sM - 0.01 ? sM + 3 : s_, t_]));
        const uc = e.z.map(z => planda(w, e.s0, 0, z)), tu = uc.map(p => Y.tOf(...p));
        const [tm0, tm1] = tu.map((t, k) => kalkanUcu(uc[k]) ? t + Math.sign(tu[1 - k] - t) * KES : t).sort((a, b) => a - b);
        const ribs = D.kaplama.hadve[Y.hadve].map(tAt);
        const levhalar = dizi(Y.serit.bas, Y.serit.son, Y.serit.yon).map(([v0, v1]) => [tAt(v0), tAt(v1)].sort((a, b) => a - b))
          .map(([t0, t1]) => [Math.max(t0, tm0), Math.min(t1, tm1)]).filter(([t0, t1]) => t1 - t0 > 1);
        return { Y, sM, tn, Pe, ribs, levhalar };
      });
      const sayi = Math.max(0, ...kanat.map(k => k.levhalar.length));
      for (let i = 0; i < sayi; i++) {
        const parca = new THREE.Group(); let boy = 0;
        kanat.forEach(({ Y, sM, tn, Pe, ribs, levhalar }) => {
          const lv = levhalar[i]; if (!lv) return;
          const [t0, t1] = lv; boy = Math.max(boy, t1 - t0);
          const g = Y.grup(), m = mat('ridge', AD.kaplama), sA = sM - KN;
          const kes = sB => { const C = dikd(sA, sB, t0, t1); return Y.icbukey ? kirp(Pe, C) : kirp(C, Pe); };
          const Q = kes(sM + n1 * tn); if (!Q) return;
          g.add(levha(Q, n0, n1, m));
          const Qr = kes(sM + (nh + RIBH) * tn);
          ribs.forEach(tc => {
            if (tc < t0 - 0.01 || tc >= t1 - 0.01 || !Qr) return;
            const iv = aralik(Qr, 1, Math.min(Math.max(tc, t0 + 0.05), t1 - 0.05)); if (!iv || iv[1] - iv[0] < 4) return;
            const rb = mesh(new THREE.ExtrudeGeometry(RIB, { depth: (iv[1] - iv[0]) / 100, bevelEnabled: false }), m);
            rb.rotation.y = Math.PI / 2; rb.position.set(iv[0] / 100, nh / 100, tc / 100); g.add(rb);
          });
          parca.add(g);
        });
        if (!parca.children.length) continue;
        add(AD.kaplama, parca, 9 + mo++ * 0.3, { kod: KB('mahya'), ad: KM.mahya_ad, satir: [['Bu parça', `${e.ad} · ${fmtc(boy)} cm`], ['Biçim', KM.mahya_bicim],
          ['Liste', KM.mahya_liste], ...kartSat(KB('mahya'))] });
      }
    });
  } else {
    // Düz mahya: iki kanat, her biri kendi yüzünde hadvelerin tepesinde (DM0 → DM1, eğime dik); kanat iki düzlemin kesiştiği tepeden 1 cm öteden KN − 1 cm'ye.
    // Ucu kalkandaysa (alın sacının yüzünde) o kalkan MAHYA_KALKAN'a girer; mahya alın sacının iç yüzüne kadar, alın sacı üstünden örter.
    const KC = KALKAN.map(G => { const w = cerceve(G.r, ...G.O); w.updateMatrixWorld(); return { G, w, s0: Math.min(G.uc.A, G.uc.B) - 1, s1: Math.max(G.uc.A, G.uc.B) + 1 }; });
    const kalkanBul = ([x, y]) => (KC.find(({ G, w, s0, s1 }) => { const v = w.worldToLocal(new THREE.Vector3(X(x), 0, Z(y))); return Math.abs(v.z * 100 - G.oTip) < 0.05 && v.x * 100 > s0 && v.x * 100 < s1; }) || {}).G;
    D.kaplama.mahya.forEach((e, j) => {
      const R = RF[e.R], T = RF[e.topR], tepe = ysR(T, T.M), [z0, z1] = e.z, p = (DM0 + DM1) / 2;
      const wp = cerceve(e.r, ...e.O); wp.updateMatrixWorld();
      e.z.forEach(z => { const G = kalkanBul(planda(wp, e.s0, 0, z)); if (G) MAHYA_KALKAN.add(G); });
      [1, -1].forEach((side, i) => {
        const w = cerceve(e.r, ...e.O), o = lb(-KN / 2, KN / 2, -(DM1 - DM0) / 2, (DM1 - DM0) / 2, z0, z1, mat('ridge', AD.kaplama));
        // kanat yüzün hadve tepesi düzleminde; iki yüzün düzlemi mahyanın üstünde (aşık oturma çizgisinin tepesinden p / cos yukarıda) kesişir
        o.position.x = (e.s0 - side * R.cos * KO) / 100; o.position.y = (tepe + p / R.cos - R.sin * KO) / 100; o.rotation.z = side * R.th; w.add(o);
        add(AD.kaplama, w, 9 + (j * 2 + i) * 0.3, { kod: KB('mahya'), ad: KM.mahya_ad, satir: [['Bu parça', `${e.ad} · ${fmtc(z1 - z0)} cm`], ['Liste', KM.mahya_liste], ...kartSat(KB('mahya'))] });
      });
    });
  }
}

/* Alın sacı (kalkanlar), dere ve iniş */
let to = 0;
// Alın sacı abkantta tek biçimde bükülür, 250 ve 280 boyda aynı: kenar boyunca saçak altının 6 cm altına iner ve köşede derenin ucunu örter;
// ayrı alt uç parçası yok (Lokman, 26.10.2026; 9.11.2026 19:57: "alın sacı çizdiğin şekilde abkantta bükülüyor yani 280 veya 250 boyunda aynı formda")
const ALIN_ALT = SACAK_ALTI - SAC - 6;
const MA = M.alin, ALIN_H = fmt(PTOP - ALIN_ALT, 0);
// Dere: galvaniz eksiz oluk, K kesit (38'lik açınım), boyalı; sırtı saçak sacının alnına asılır
const DERE_K = [[0, 11.4], [0, 0], [9, 0], [10, 0.8], [10.6, 2.6], [12, 3.6], [13, 5.6], [13.4, 8.6], [14.6, 10.2], [15, 11.4], [14, 11.4]];
const DERE_ALT = TB - 0.05 + 13 - 0.4 - 11.4;   // üstü alının 4 mm altında
const DERE_SIRT = SAC + 0.03;                   // derenin sırtı saçak sacının alnından (dere ve iniş çizimiyle aynı)
// Dereyle biten saçak ucunda alının yüzü kalkan çerçevesinde (s yatay, y yükseklik; cm): kenar boyunca tek biçim, saçak sacının alnında düşey
// biter; alnın dışında levha derenin ucunu örter ve derenin biçiminde kesilir: altı derenin sırtı, tabanı ve K kıvrımı, dışı derenin dış ağzı,
// üstü alının üst çizgisi (Lokman, 9.11.2026 19:57: "alın sacını dereyi kapattığı yeri derenin deseninde kes"; "bir montajcı sanatkar ise
// sahada alın sacının bittiği yeri derenin şekli formunda kesiyor"). 5 cm aşağı bükülen saçak altı (sıradan montajcının yolu) çizilmez.
function alinYuzu(G, end, K, ot) {
  const dir = Math.sign(G.sm - G.uc[end]), sA = G.uc[end] - dir * 0.2, m = mat('trim', AD.alin);
  const ust = s => G.h(s) + PTOP / G.R.cos, alt = s => G.h(s) + ALIN_ALT / G.R.cos, S = u => sA - dir * u;   // u: saçak sacının alnından dışa
  const plaka = q => { const c = []; [ot, ot + SAC].forEach(o => q.forEach(([s, y]) => c.push([s, y, o]))); K.w.add(mesh(hex(c), m)); };
  plaka([[sA, alt(sA)], [G.sm, alt(G.sm)], [G.sm, ust(G.sm)], [sA, ust(sA)]]);   // kenar boyunca: alnın hizasından mahyaya
  // derenin dış çizgisi (u, yükseklik): sırtın altı, taban, K kıvrımı, dış ağız; levha bunun üstünde ve alının iki çizgisinin arasında
  const cz = [[0, DERE_ALT], ...DERE_K.slice(1, 10).map(([u, v]) => [u + DERE_SIRT, DERE_ALT + v])];
  const kes = (f, g, a, b) => { const fa = f(a) - g(a), fb = f(b) - g(b); return fa * fb < 0 ? a + (b - a) * fa / (fa - fb) : null; };
  for (let i = 0; i + 1 < cz.length; i++) {
    const [ua, ya] = cz[i], [ub, yb] = cz[i + 1], c = u => ya + (yb - ya) * (u - ua) / (ub - ua), U = u => ust(S(u)), A = u => alt(S(u));
    const lo = u => Math.max(c(u), A(u));
    const br = [ua, ub, kes(c, A, ua, ub), kes(U, c, ua, ub), kes(U, A, ua, ub)].filter(u => u !== null).sort((p, q) => p - q);
    for (let j = 0; j + 1 < br.length; j++) {
      const [p, q] = [br[j], br[j + 1]]; if (q - p < 1e-6) continue;
      const mid = (p + q) / 2; if (U(mid) - lo(mid) <= 1e-6) continue;
      plaka([[S(p), lo(p)], [S(q), lo(q)], [S(q), Math.max(U(q), lo(q))], [S(p), Math.max(U(p), lo(p))]]);
    }
  }
}
// Cumbanın kısa yan saçağı ana çatının kalkanının devamında sürüyorsa (kampanyalı ev, TK-04 r08 ön/sol) kalkanın alt ucu bir dere hattının
// kenarındadır ve hat kalkanla aynı yöndedir. Bu uçta alın derenin biçiminde kesilmez; derenin ucu açık kalır (Lokman, 10.11.2026 21:26 UTC:
// "montajcılar binanın ana makaslarının alın sacını alttan uzun bırakıyor ki saçak sacını kapatsın derenin o kısmı açıkta kalıyor orayı
// kapatmıyoruz"). Cumbanın öteki ucunda cumbanın alın sacı derenin biçiminde kesilir (alinYuzu, M-17).
function ucPlan(G, end) {   // kalkan ucunun alın noktası, planda (cm)
  const w = cerceve(G.r, ...G.O); w.updateMatrixWorld();
  const v = new THREE.Vector3(G.uc[end] / 100, 0, G.oTip / 100).applyMatrix4(w.matrixWorld);
  return { P: [(v.x + D.dis[0] / 200) * 100, (D.dis[1] / 200 - v.z) * 100], boyY: Math.abs(Math.sin(G.r)) > 0.5 };
}
function hizaliDere(G, end) {
  const { P, boyY } = ucPlan(G, end);
  return D.dere.hatlar.some(h => (h.yon === 'y') === boyY && Math.abs(h.kenar - (boyY ? P[0] : P[1])) < 0.5 && [h.a0, h.a1].some(a => Math.abs(a - (boyY ? P[1] : P[0])) < 0.6));
}
function basOmegaUcu(G, end) {   // kalkanın bu ucuna dik gelen baş makas omegası: kesitinin s aralığı (iç ayaktan dış U'ya) ve altı
  const { P, boyY } = ucPlan(G, end);
  const sg = D.omega_duvar.find(o => o.tur === 'bas' && (o.o === 'h') === boyY && [o.a0, o.a1].some(a => Math.abs(a - (boyY ? P[0] : P[1])) < 0.6));
  if (!sg) return null;
  const uI = 5 + HS - OM100, uD = 5 + HS;   // omega bloğundaki gibi: iç ve dış kanadın iç yüzü; iç ayak 3 cm, dış U BAS_U
  return { s: [uI - 3, uD + 2 * SAC + BAS_U].map(x => (sg.perp + sg.out * x) / G.p).sort((a, b) => a - b), alt: H - BAS_KANAT - SAC };
}
function alinUzun(G, end, K, ot) {   // alın: kalkanın ucunda düz biter; dere biçiminde kesilmez, derenin ucu açık kalır
  const dir = Math.sign(G.sm - G.uc[end]), sA = G.uc[end] - dir * 0.2, m = mat('trim', AD.alin);
  const ust = s => G.h(s) + PTOP / G.R.cos, alt = s => G.h(s) + ALIN_ALT / G.R.cos, c = [];
  [ot, ot + SAC].forEach(o => [[sA, alt(sA)], [G.sm, alt(G.sm)], [G.sm, ust(G.sm)], [sA, ust(sA)]].forEach(([s, y]) => c.push([s, y, o])));
  K.w.add(mesh(hex(c), m));
}
// Aynı uçta arkadan bakınca baş makas omegası ve cumba makası görünmesin diye alın sacının saçak altı (tırnağıyla) omeganın arka yüzünde
// biter ve oradan dik aşağı bükülür: omeganın altına iner, dışı alına değer; Z'nin ve kalkanın duvar omegasının çevresinde kesilir. Ek parça yok.
// Lokman, 11.11.2026 UTC: 06:29 "dik uzanacak yani montajcı alın sacının üst tarafını kesiyor alt tarafını aşağı doğru büküyor"; 08:52 "alın
// sacı tek formda ... alın sacının altındaki parçayı aşağı doğru uzatacaksın yani tam arkadan bakınca baş makas omegası ve cumba makası
// görünmeyecek"; 10:06 eskiz kartı "Doğru, böyle yap".
function alinKapak(G, end) {
  const OM = basOmegaUcu(G, end); if (!OM) return null;
  const dir = Math.sign(G.sm - G.uc[end]), g = 0.025, sF = (dir < 0 ? OM.s[0] : OM.s[1]) + dir * g, sB = sF + dir * SAC;
  const y = (s, p) => G.h(s) + p / G.R.cos, k = 1 / Math.tan(Z_ACI);
  const ustZ = o => ZT0[1] + SAC / 2 * Math.sin(Z_ACI) + (o - (ZT0[0] - SAC / 2 * Math.cos(Z_ACI))) * k;   // Z tırnağının üst yüzü (p)
  const altZ = o => ZT0[1] - SAC / 2 * Math.sin(Z_ACI) + (o - (ZT0[0] + SAC / 2 * Math.cos(Z_ACI))) * k;   // alt yüzü
  const oI = G.ob + SAC, oU = ZT1[0] + SAC, oL = G.oT + BAS_U + SAC;   // saçak altının iç kenarı, Z tırnağının ucunun dışı, duvar omegasının U yanağının dışı
  const ciz = K => {
    const m = mat('trim', AD.alin), plaka = q => { const c = []; [sB, sF].forEach(s => q(s).forEach(([o, yy]) => c.push([s, yy, o]))); K.w.add(mesh(hex(c), m)); };
    const kolon = (o0, o1, alt, ust) => plaka(s => [[o0, alt(s, o0)], [o1, alt(s, o1)], [o1, ust(s, o1)], [o0, ust(s, o0)]]);   // o0..o1 arası, alttan üste
    const sabit = v => () => v, sacak = s => y(s, SACAK_ALTI), zUstu = (s, o) => y(s, ustZ(o)) + g, zAlti = (s, o) => y(s, altZ(o)) - g;
    kolon(oU, G.oTip, sabit(OM.alt), sacak);                                         // dış: omeganın altından saçak altına, dışı alına değer
    kolon(oI, oU, zUstu, sacak);                                                     // Z tırnağının üstü
    kolon(oL, oU, sabit(OM.alt), zAlti);                                             // Z tırnağının altı
    kolon(oL - SAC, oL, sabit(H - BAS_KANAT + BAS_DUDAK), zAlti);                    // duvar omegasının U yanağının üstü
    kolon(G.ob + SAC, oL - SAC, sabit(H - BAS_KANAT), zAlti);                        // U'nun içi, Z tırnağının altı
    kolon(G.ob, G.ob + SAC, sabit(H - BAS_KANAT), s => y(s, -Z_GOVDE) - g);          // U'nun içi, Z gövdesinin altı; betopana değer
  };
  return { sB, sF, ciz, boy: y(sB, SACAK_ALTI) - OM.alt };
}
KALKAN.forEach(G => ['A', 'B'].forEach(end => {
  const K = rake(G, end, mat('trim', AD.alin)), ot = G.oTip, kose = G.altUc[end], hiz = kose && hizaliDere(G, end), kap = hiz ? alinKapak(G, end) : null;
  const xk = !kap ? [] : K.dir < 0 ? [-K.Ls / 2, K.xOf(kap.sB, SACAK_ALTI - SAC / 2)] : [K.xOf(kap.sB, SACAK_ALTI - SAC / 2), K.Ls / 2];   // köşede bükülen yerde biter
  K.lev(G.ob + SAC, G.ob + 2 * SAC, TIRNAK_ALT, SACAK_ALTI, ...xk); // tırnak: Z'nin gövdesi boyunca, alt ucu Z'nin tırnağına değer (Lokman, 9.11.2026)
  K.lev(G.ob + SAC, ot, SACAK_ALTI - SAC, SACAK_ALTI, ...xk);       // saçak altı: tırnağın üst ucundan alına
  if (kap) kap.ciz(K);                                              // köşede saçak altı dik aşağı bükülür
  const KU = rake(G, end, mat('trim', AD.alin));
  if (hiz) alinUzun(G, end, KU, ot);                          // alın: köşede düz biter, derenin ucu açık
  else if (kose) alinYuzu(G, end, KU, ot);                        // alın: tek biçim; köşede derenin ucunu örter, ucu derenin biçiminde
  else KU.lev(ot, ot + SAC, ALIN_ALT, PTOP);                 // alın: tek biçim, saçak altının 6 cm altından kenar hadvesinin üstüne
  // kıvrımlar kenar boyunca; hadveye dışından değer (Lokman, 9.11.2026: "çakışma olmasın tam değme olsun")
  const hu = [ot - RIB_KENAR - RIB_UST / 2, TU1 + RIBH], hd = [ot - RIB_KENAR - RIB_TABAN / 2, TU1];   // kenar hadvesinin iç yanağı: tepe ve taban köşesi
  const [kx0, kx1] = KU.catida(hd[0]);
  const hl = Math.hypot(hu[0] - hd[0], hu[1] - hd[1]), hn = [-(hu[1] - hd[1]) / hl * (SAC / 2 + 0.01), (hu[0] - hd[0]) / hl * (SAC / 2 + 0.01)], hk = 0.5 / RIBH;
  // Düz mahya bu kalkanda bitiyorsa mahyanın kanadı boyunca (tepeden KN − 1 cm) üst kıvrım mahyanın üstüne yatar, alın o kadar uzar;
  // hadveyi kavrayan iç kıvrım orada kesilir (mahya hadvenin üstünden alına kadar geçer). Alın sacının biçimi aynı (Lokman, 10.11.2026 21:01;
  // kesit eskizi, 21:20: "montajcı ... Sandviç panel hadvelerine bindirdiği kıvrımı tam tepede Düz mahyaya bastırarak vidalıyor ... önerin doğru sayılır").
  const zm = MAHYA_KALKAN.has(G) ? Math.min(D.kaplama.mahya_kanat - 1, KU.Ls) : 0, xz = KU.dir * (KU.Ls / 2 - zm);
  const [[a0, a1], [m0, m1]] = KU.dir > 0 ? [[kx0, Math.min(kx1, xz)], [Math.max(kx0, xz), kx1]] : [[Math.max(kx0, xz), kx1], [kx0, Math.min(kx1, xz)]];
  if (a1 - a0 > 0.01) {
    KU.lev(hu[0], ot + SAC, PTOP - 0.1, PTOP, a0, a1);    // kıvrım: kenar hadvesinin tepesinin üstünden içeri
    KU.egik(hu[0] + hn[0], hu[1] + hn[1], hd[0] + (hu[0] - hd[0]) * hk + hn[0], hd[1] + (hu[1] - hd[1]) * hk + hn[1], a0, a1);   // hadveyi kavrayan kıvrım: hadvenin iç yanağı boyunca aşağı
  }
  if (zm && m1 - m0 > 0.01) {
    KU.lev(hu[0], ot + SAC, DM1, DM1 + 0.1, m0, m1);      // kıvrım mahyanın üstünde
    KU.lev(ot, ot + SAC, PTOP, DM1 + 0.1, m0, m1);        // alın mahyanın kalınlığı kadar uzar
  }
  const nm = `${G.ad} · ${end === 'A' ? 'ön/sol' : 'arka/sağ'} yüz`;
  add(AD.alin, KU.w, to++ * 0.5, { kod: KB('alin'), ad: MA.ad, satir: [['Bu parça', `${nm} · alın ve üst kıvrımlar${hiz ? '; köşede düz biter, derenin ucu açık kalır' : kose ? '; köşede derenin ucunu örter, ucu derenin biçiminde kesilir' : ''}`], ['Alın', yaz(MA.alin, { h: ALIN_H })], ['Kaynak', MA.kaynak], ...kartSat(KB('alin'))] });
  add(AD.alin, K.w, to++ * 0.5, { kod: KB('alin'), ad: MA.ad, satir: [['Bu parça', `${nm} · L ${Math.round(K.Ls)} cm`], ['Profil', MA.profil], ['Uçta', MA.uc], ...(kap ? [['Köşede', `saçak altı baş makas omegasının arka yüzünde dik aşağı bükülür, omeganın altına iner (${fmt(kap.boy, 1)} cm); arkadan bakınca omega ve cumba makası görünmez (Lokman, 11.11.2026)`]] : []), ['Bu proje', yaz(MA.proje, { h: ALIN_H })], ['Liste', MA.liste], ...kartSat(KB('alin'))] });
  // Ayrı alt uç parçası yok (Lokman, 26.10.2026): alın sacının kendisi dereyi de örter
}));
const HAT = Object.fromEntries(D.dere.hatlar.map(h => [h.ad, h]));
const dereSerit = h => serit(h.yon === 'x' ? 'h' : 'v', h.kenar, h.out);   // yerel x dışa: 0 = saçak sacının alnı
const MD = M.dere, MI = M.inis;
D.dere.hatlar.forEach((h, i) => {
  const S = dereSerit(h), g = S.yeni(), m = mat('gutter', AD.dere), [z0, z1] = [S.zOf(h.a0), S.zOf(h.a1)].sort((p, q) => p - q), L = (z1 - z0) / 100;
  const sh = thick(DERE_K.map(([u, v]) => [u + SAC + 0.03, v]), 0.05);
  const k = mesh(new THREE.ExtrudeGeometry(sh, { depth: L, bevelEnabled: false }), m); k.position.set(0, DERE_ALT / 100, z0 / 100); g.add(k);
  const kap = new THREE.Shape(); DERE_K.slice(0, 10).forEach(([u, v], j) => j ? kap.lineTo((u + SAC + 0.03) / 100, v / 100) : kap.moveTo((u + SAC + 0.03) / 100, v / 100)); kap.closePath();
  // kapaklar derenin içinde: dışı alın sacına değer (Lokman, 9.11.2026: "çakışma olmasın tam değme olsun")
  [z0 / 100, z1 / 100 - 0.001].forEach(zz => { const c = mesh(new THREE.ExtrudeGeometry(kap, { depth: 0.001, bevelEnabled: false }), m); c.position.set(0, DERE_ALT / 100, zz); g.add(c); });
  add(AD.dere, g, i, { kod: KB('dere'), ad: MD.ad, satir: [['Bu parça', `${h.ad} hat · ${fmtc(h.a1 - h.a0)} cm (paftada ${fmtc(h.pafta)}) · iki ucunda kapak`], ['Kesit', MD.kesit], ['Pafta', MD.pafta], ['Liste', MD.liste], ...kartSat(KB('dere'))] });
});
D.dere.inisler.forEach((p, i) => {
  // Lokman'ın fotoğrafları (25–26.10.2026): köşede iniş aparatı derenin uç kısmında, borunun tam hizasında; kaz boynu (2 açık dirsek)
  // duvara (verandada kolona) dik döner; boru köşe direği kaplamasının (13 cm) hemen yanından 2 kelepçeyle iner, altta kapalı dirsek.
  const h = HAT[p.hat], S = dereSerit(h), w = S.yeni(), m = mat('gutter', AD.dere), ust = DERE_ALT;   // cm
  const kolon = p.sw !== undefined;   // verandada boru kolonun yerinde (p.sw)
  const yuzU = (p.yuz - h.kenar) * h.out;   // duvar yüzünün yerel x'i (dışa pozitif)
  const sw = p.boru !== undefined ? p.boru : kolon ? p.sw : Math.min(D.dis[p.dis] - 17, Math.max(17, p.s));   // boru: köşe direği kaplamasının yanında
  // ya da kolonda; veri yerini verdiyse orada (İE-15 K6: cumbanın kısa yan saçağında evin köşesinde, ağzı tam hizasında; Lokman, 5 Kasım 2026)
  const so = p.agiz !== undefined ? p.agiz : Math.min(Math.max(h.a0, h.a1) - 6, Math.max(Math.min(h.a0, h.a1) + 6, sw));    // ağız: borunun hizasında
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
  D.panels.flatMap(p => (p.ops || (p.op ? [p.op] : [])).map(op => [p, op])).filter(([p, op]) => op.kind === 'win' || op.kind === 'door_ext').forEach(([p, op]) => {   // D-46: karkaslı panoda her açıklık
    const [x0, y0, x1, y1] = p.rect, g = new THREE.Group(), c = p.o === 'h' ? (y0 + y1) / 2 : (x0 + x1) / 2;
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
