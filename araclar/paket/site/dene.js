// İE-41 · kurulan siteyi yerelde dener: node dene.js <site> <rehberler.json> <ekran klasörü>  (çıkış 0 = bulgu yok)
// İlk hâli `claude/montaj-rehberi-devir` dalında `deneme/2026-11-04_rehber_sitesi/dene.py` (kart 104, 4 Kasım 2026).
// Site yerel bir adresten sunulur (http://site.yerel/, dosyalar diskten). Masaüstü (1366 × 860) ve telefon (390 × 844, dokunmatik):
//   açılış: her rehberin kartı, kapak görseli yüklü, bağlantı açılır;
//   her rehber: belge kipi, adım sayısı, kart satırları sağlam, her adım açılır; görünen bütün yazılarda (üst bilgi, her adımın paneli,
//   bütün kimlik kartları) iç not yok; evin altındaki ön onay paftası yüklü (pafta: true); parçaya dokununca kart açılır;
//   her sayfada konsol/sayfa hatası, CSP ihlali, 4xx/5xx ve dış istek yok, yatay taşma yok.
// İE-45: montaj oyunu (kayıttaki 'oyunlar'): açılışta kartı rehberlerin önünde; model yüklenir, 21 adım doğru kartla oynanır (iki
//   yanlış seçimle ipucu da denenir), bitiş kartı, "Evi gez", "Kapıları aç"; görünen yazılarda iç not yok. DENE_OYUN=0: oyun atlanır.
// Ekranlar ve her rehberin görünen metni <ekran klasörü>'ne. DENE_REHBER=<klasör>: yalnız o rehber.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const TUR = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.jpg': 'image/jpeg', '.png': 'image/png',
  '.woff2': 'font/woff2', '.txt': 'text/plain' };
const KOK = 'http://site.yerel/';
const YASAK = ['lokman', 'kaynak:', 'liste de böyle', 'varsay', 'motor', 'teyit', 'sketchup', 'alpha mini', 'pk-0', 'tk-0', 'ap-0', 'ap-1',
  'ap-2', '(d-', 'pm-tk', 'kitap', 'kitab', 'kural', 'modelinde', 'kart modeli', 'portman', 'tatar', 'patron', 'deneme', 'iş emri'];
const KELIME = ['undefined', 'null', 'nan'];
const CIHAZ = { masaustu: { viewport: { width: 1366, height: 860 } },
  telefon: { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true } };
const [site, kayitYolu, ekran] = process.argv.slice(2);
const kayit = JSON.parse(fs.readFileSync(kayitYolu, 'utf8'));
fs.mkdirSync(ekran, { recursive: true });
const bulgu = [];

async function ac(b, ayar, yol) {
  const ctx = await b.newContext(ayar);
  await ctx.route('**/*', r => {
    const u = new URL(r.request().url());
    if (u.origin + '/' !== KOK) return r.abort();
    let f = path.join(site, decodeURIComponent(u.pathname));
    if (f.endsWith('/')) f += 'index.html';
    if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) return r.fulfill({ status: 404, body: '' });
    r.fulfill({ path: f, contentType: TUR[path.extname(f)] || 'application/octet-stream' });
  });
  const p = await ctx.newPage();
  const kay = { hata: [], dis: [], eksik: [] };
  p.on('pageerror', e => kay.hata.push(`pageerror: ${e.message}`));
  p.on('console', m => (m.type() === 'error' || m.type() === 'warning') && kay.hata.push(`console.${m.type()}: ${m.text()}`));
  p.on('request', r => { const u = r.url(); if (!u.startsWith(KOK) && !u.startsWith('data:') && !u.startsWith('blob:')) kay.dis.push(u); });
  p.on('response', r => r.status() >= 400 && kay.eksik.push(`${r.status()} ${r.url()}`));
  await p.goto(KOK + yol, { waitUntil: 'networkidle', timeout: 120000 });
  return { p, kay };
}

async function kapat({ p, kay }, ad) {
  if (await p.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)) bulgu.push(`${ad}: yatay taşma var`);
  for (const h of kay.hata) if (!(h.includes('GPU stall') || (h.includes('WebGL') && h.includes('warning')))) bulgu.push(`${ad}: ${h}`);
  kay.dis.forEach(u => bulgu.push(`${ad}: dış istek ${u}`));
  kay.eksik.forEach(u => bulgu.push(`${ad}: yanıt ${u}`));
  await p.context().close();
}

async function acilis(b, cihaz, ayar) {
  const ad = `açılış/${cihaz}`;
  const s = await ac(b, ayar, '');
  const { p } = s;
  await p.evaluate(() => Promise.all([...document.images].map(i => i.complete ? 1 : new Promise(r => { i.onload = i.onerror = r; }))));
  const o = await p.evaluate(() => ({ kip: document.compatMode, baslik: document.title,
    kart: [...document.querySelectorAll('a.kart')].map(a => ({ href: a.getAttribute('href'), ad: a.querySelector('h2').textContent,
      img: a.querySelector('img').complete && a.querySelector('img').naturalWidth > 0 })) }));
  console.log(`[${ad}] ${JSON.stringify(o)}`);
  const beklenen = [...(kayit.oyunlar || []).filter(x => x.acilis_karti), ...kayit.rehberler];
  if (o.kip !== 'CSS1Compat' || o.kart.length !== beklenen.length) bulgu.push(`${ad}: belge kipi ya da kart sayısı yanlış`);
  o.kart.forEach((k, i) => {
    if (k.href !== beklenen[i].klasor + '/' || k.ad !== beklenen[i].ad) bulgu.push(`${ad}: ${i + 1}. kart yanlış (${k.href} ${k.ad})`);
    if (!k.img) bulgu.push(`${ad}: kapak görseli yüklenmedi (${k.href})`);
  });
  await p.screenshot({ path: path.join(ekran, `acilis_${cihaz}.png`), fullPage: true });
  await kapat(s, ad);
}

async function rehber(b, r, cihaz, ayar) {
  const ad = `${r.klasor}/${cihaz}`;
  const s = await ac(b, ayar, r.klasor + '/');
  const { p } = s;
  await p.waitForFunction(() => window.__montaj && window.__montaj.parts, null, { timeout: 60000 });
  await p.waitForTimeout(1500);
  const o = await p.evaluate(() => { const m = window.__montaj; const kotu = []; let kartli = 0;
    m.parts.forEach(x => { const i = x.obj.userData.info; if (!i) return; kartli++;
      if (!Array.isArray(i.satir) || i.satir.some(q => q && (!Array.isArray(q) || q.length !== 2))) kotu.push(i.ad); });
    return { N: m.N, adim: m.STEPS.length, parca: m.parts.length, kartli, kotu: [...new Set(kotu)], kip: document.compatMode,
      baslik: document.title, h1: document.querySelector('h1').textContent, chip: document.querySelector('.chip').textContent }; });
  console.log(`[${ad}] ${JSON.stringify(o)}`);
  await p.screenshot({ path: path.join(ekran, `${r.klasor}_${cihaz}_acilis.png`) });
  if (o.kip !== 'CSS1Compat') bulgu.push(`${ad}: belge tuhaf kipte`);
  if (o.N !== r.adim || o.adim !== r.adim + 1) bulgu.push(`${ad}: ${r.adim} adım beklenirdi (N=${o.N}, STEPS=${o.adim})`);
  if (o.h1 !== `${r.ad} · Montaj Rehberi`) bulgu.push(`${ad}: başlık ${o.h1}`);
  if (o.kotu.length) bulgu.push(`${ad}: satırı bozuk kart: ${o.kotu}`);
  const yazi = [await p.evaluate(() => document.querySelector('header').innerText),
                await p.evaluate(() => (document.querySelector('.note') || {}).innerText || '')];
  for (let i = 0; i < o.adim; i++) {
    await p.evaluate(i => window.__montaj.goTo(i, false), i);
    yazi.push(await p.evaluate(() => (document.querySelector('main') || document.body).innerText));
  }
  yazi.push(await p.evaluate(() => window.__montaj.parts.map(x => x.obj.userData.info).filter(Boolean)
    .map(i => [i.kod || '', i.ad, ...i.satir.filter(q => q && q[1]).map(q => q[0] + ': ' + q[1])].join(' | ')).join('\n')));
  const metin = yazi.join('\n');
  if (cihaz === 'masaustu') fs.writeFileSync(path.join(ekran, `${r.klasor}_gorunen_metin.txt`), metin);
  const kucuk = metin.toLocaleLowerCase('tr');
  for (const y of YASAK) { const i = kucuk.indexOf(y); if (i >= 0) bulgu.push(`${ad}: görünen metinde "${y}": …${metin.slice(Math.max(0, i - 60), i + 60)}…`); }
  for (const y of KELIME) if (new RegExp('\\b' + y + '\\b').test(kucuk)) bulgu.push(`${ad}: görünen metinde "${y}"`);
  if (r.pafta) {
    const pf = await p.evaluate(() => { let sc = window.__montaj.parts[0].obj; while (sc.parent) sc = sc.parent;
      const k = window.__pdf || sc.getObjectByName('Ön onay sayfası'); const im = k && k.material.map && k.material.map.image;
      return { var: !!k, gorunur: !!(k && k.visible), yuklu: !!(im && im.complete && im.naturalWidth), en: im ? im.naturalWidth : 0 }; });
    console.log(`[${ad}] ön onay paftası: ${JSON.stringify(pf)}`);
    if (!(pf.var && pf.gorunur && pf.yuklu)) bulgu.push(`${ad}: ön onay paftası yüklenmedi (${JSON.stringify(pf)})`);
  }
  await p.evaluate(() => window.__montaj.goTo(window.__montaj.N, false));
  await p.waitForTimeout(1500);
  await p.screenshot({ path: path.join(ekran, `${r.klasor}_${cihaz}_son.png`) });
  const vp = await p.locator('#viewport canvas').boundingBox();
  let acildi = false;
  for (const fx of [0.5, 0.45, 0.55, 0.4, 0.6]) {
    for (const fy of [0.5, 0.45, 0.55, 0.6, 0.4]) {
      const x = vp.x + vp.width * fx, y = vp.y + vp.height * fy;
      if (ayar.hasTouch) await p.touchscreen.tap(x, y); else await p.mouse.click(x, y);
      await p.waitForTimeout(120);
      if (await p.evaluate(() => !document.getElementById('info').hidden)) { acildi = true; break; }
    }
    if (acildi) break;
  }
  if (acildi) {
    console.log(`[${ad}] dokunulan kart: ${await p.textContent('#infoT')}`);
    await p.screenshot({ path: path.join(ekran, `${r.klasor}_${cihaz}_kart.png`) });
  } else bulgu.push(`${ad}: parçaya dokununca kart açılmadı`);
  await kapat(s, ad);
}

async function oyun(b, o, cihaz, ayar) {
  const ad = `${o.klasor}/${cihaz}`;
  const s = await ac(b, ayar, o.klasor + '/');
  const { p } = s;
  await p.waitForFunction(() => !document.getElementById('basla').disabled, null, { timeout: 120000 });
  const metin = [await p.evaluate(() => document.body.innerText)];
  await p.screenshot({ path: path.join(ekran, `${o.klasor}_${cihaz}_acilis.png`) });
  await p.click('#basla');
  const durum = () => p.evaluate(() => ({ cur: +(document.getElementById('soruAlt').textContent.split(' ')[1] || 0),
    acik: [...document.querySelectorAll('#kartlar .kart')].filter(k => !k.disabled).map(k => +k.dataset.i) }));
  const sec = i => p.evaluate(i => [...document.querySelectorAll('#kartlar .kart')].find(k => +k.dataset.i === i && !k.disabled).click(), i);
  const N = (await p.evaluate(() => JSON.parse(document.getElementById('veri').textContent).adimlar.length));
  for (let k = 1; k <= N; k++) {
    await p.waitForFunction(k => document.getElementById('soruAlt').textContent.startsWith('Adım ' + k + ' ')
      && [...document.querySelectorAll('#kartlar .kart')].some(b => !b.disabled), k, { timeout: 90000 });
    const d = await durum();
    if (d.acik.length !== 4 || !d.acik.includes(k)) bulgu.push(`${ad}: ${k}. adımda kartlar yanlış (${d.acik})`);
    if (k === 2) {                                  // iki yanlış: ipucu ve işaretli kart
      for (const y of d.acik.filter(i => i !== k).slice(0, 2)) await sec(y);
      const ip = await p.evaluate(() => ({ m: document.getElementById('mesaj').className, isaret: !!document.querySelector('.kart.isaret') }));
      if (!(ip.m.includes('ipucu') && ip.isaret)) bulgu.push(`${ad}: iki yanlıştan sonra ipucu çıkmadı (${JSON.stringify(ip)})`);
      metin.push(await p.evaluate(() => document.getElementById('tepsi').innerText));
    }
    await sec(k);
    metin.push(await p.evaluate(() => document.getElementById('tepsi').innerText));
  }
  await p.waitForFunction(() => !document.getElementById('bitis').hidden, null, { timeout: 90000 });
  metin.push(await p.evaluate(() => document.getElementById('bitis').innerText));
  await p.screenshot({ path: path.join(ekran, `${o.klasor}_${cihaz}_bitis.png`) });
  await p.click('#gezTus');
  await p.waitForTimeout(1500);
  if (await p.evaluate(() => document.getElementById('kapiTus').hidden)) bulgu.push(`${ad}: "Kapıları aç" düğmesi yok (modelde açılır kapı yok)`);
  else {
    await p.click('#kapiTus'); await p.waitForTimeout(1600);
    if ((await p.textContent('#kapiTus')).trim() !== 'Kapıları kapat') bulgu.push(`${ad}: kapılar açılmadı`);
  }
  await p.screenshot({ path: path.join(ekran, `${o.klasor}_${cihaz}_gez.png`) });
  const tum = metin.join('\n');
  fs.writeFileSync(path.join(ekran, `${o.klasor}_${cihaz}_metin.txt`), tum);
  const k = tum.toLocaleLowerCase('tr');
  YASAK.forEach(y => k.includes(y) && bulgu.push(`${ad}: görünen yazıda "${y}"`));
  KELIME.forEach(y => new RegExp(`\\b${y}\\b`).test(k) && bulgu.push(`${ad}: görünen yazıda "${y}"`));
  console.log(`[${ad}] ${N} adım oynandı`);
  await kapat(s, ad);
}

(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const yalniz = process.env.DENE_REHBER;
  for (const [cihaz, ayar] of Object.entries(CIHAZ)) {
    if (!yalniz) await acilis(b, cihaz, ayar);
    for (const r of kayit.rehberler) if (!yalniz || r.klasor === yalniz) await rehber(b, r, cihaz, ayar);
    if (process.env.DENE_OYUN !== '0') for (const o of kayit.oyunlar || []) if (!yalniz || o.klasor === yalniz) await oyun(b, o, cihaz, ayar);
  }
  await b.close();
  console.log(bulgu.length ? 'BULGU:' : 'SONUÇ: bulgu yok');
  bulgu.forEach(x => console.log('  - ' + x));
  process.exit(bulgu.length ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
