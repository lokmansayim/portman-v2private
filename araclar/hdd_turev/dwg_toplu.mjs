// DWG → DXF toplu çevirici (İE-43 PR-2). Tek süreçte birçok dosya; wasm bir kez yüklenir.
// Kullanım: node dwg_toplu.mjs <iş listesi.jsonl> <geçici klasör> <süre sn>
// İş satırı: {"anahtar": "HD-001_19", "girdi": "<DWG yolu>", "hafif": false}. Her dosya için geçici klasöre
// <anahtar>.dxf, <anahtar>.katman.json, <anahtar>.oge.json ve en son <anahtar>.bitti (sonuç) yazar; sonucu stdout'a da
// JSON satırı basar. Hafif (büyük 3D modeller): yalnız <anahtar>.dxf ve .bitti; sürücü her hafif dosyaya ayrı süreç açar.
// Kütüphane: @mlightcad/libredwg-web 0.7.14 (LibreDWG 0.13.3 wasm). Yalnız okur; girdiye yazmaz.
import { Dwg_File_Type, LibreDwg } from '@mlightcad/libredwg-web';
import fs from 'node:fs';
import path from 'node:path';

const [liste, gecici, sureSn] = process.argv.slice(2);
const sinir = Date.now() + 1000 * Number(sureSn || 60);
const wasm = path.join(path.dirname(new URL(import.meta.url).pathname), 'node_modules/@mlightcad/libredwg-web/wasm/');
const wasmYolu = fs.existsSync(wasm) ? wasm : process.env.LIBREDWG_WASM;
// BigInt (bazı DWG'lerde tutamak ve 64 bit alanlar) JSON'a metin olarak yazılır
const json = (x) => JSON.stringify(x, (_, v) => (typeof v === 'bigint' ? v.toString() : v));

// Kütüphanenin dwg_write_dxf'i sıfırdan farklı her kodda DXF'i atar; LibreDWG'de 128'in altı kritik değildir
// (DWG_ERR_CRITICAL = 128). Burada wasm işlevi doğrudan çağrılır: kod 128'in altındaysa ve dosya yazıldıysa DXF alınır.
function dxfYaz(lib, ab) {
  const M = lib.wasmInstance;
  const g = 'girdi.dwg', c = 'cikti.dxf';
  try {
    M.FS.writeFile(g, new Uint8Array(ab));
    const kod = M.dwg_write_dxf(g, c);
    const var_ = M.FS.analyzePath(c, false).exists;
    return { kod, dxf: kod < 128 && var_ ? M.FS.readFile(c) : null };
  } finally {
    for (const ad of [g, c]) if (M.FS.analyzePath(ad, false).exists) M.FS.unlink(ad);
  }
}

const isler = fs.readFileSync(liste, 'utf8').split('\n').filter(Boolean).map((s) => JSON.parse(s));
for (const is of isler) {
  if (Date.now() > sinir) break;
  const bas = Date.now();
  const sonuc = { anahtar: is.anahtar };
  try {
    // Her dosyaya yeni örnek: bir DXF yazımından sonra aynı örnek sonraki dosyayı okuyamıyor (15 Kasım denemesi).
    const lib = await LibreDwg.create(wasmYolu);
    const buf = fs.readFileSync(is.girdi);
    const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
    if (is.hafif) {
      // Büyük 3D model: yalnız DXF yazılır. convert() bütün öğeleri JS nesnesine çevirir; 15 MB'lık DWG'de 2,3 GB
      // bellek tuttu (15 Kasım ölçümü). Öğe sayıları, bloklar ve katmanlar Python'da DXF'ten akışla okunur.
      sonuc.hafif = true;
      let dxf = null;
      try { const y = dxfYaz(lib, ab); dxf = y.dxf; sonuc.dxf_kod = y.kod; } catch (h) { sonuc.dxf_hata = String(h?.message || h).slice(0, 200); }
      if (dxf) {
        fs.writeFileSync(path.join(gecici, `${is.anahtar}.dxf`), dxf);
        sonuc.durum = 'cevrildi';
      } else {
        sonuc.durum = 'hata';
        sonuc.hata = `DXF yazılamadı (kod ${sonuc.dxf_kod ?? '-'}) ${sonuc.dxf_hata || ''}`.trim();
      }
      sonuc.sure = (Date.now() - bas) / 1000;
      if (sonuc.durum !== 'hata') fs.writeFileSync(path.join(gecici, `${is.anahtar}.bitti`), json(sonuc));
      console.log(json(sonuc));
      continue;
    }
    const ptr = lib.dwg_read_data(ab, Dwg_File_Type.DWG);
    const db = lib.convert(ptr);
    const L = {};
    for (const l of db.tables?.LAYER?.entries || []) L[l.name] = { off: !!l.off, frozen: !!l.frozen, locked: !!l.locked, c: l.colorIndex };
    const ham = db.entities || [];
    sonuc.surum = db.header?.ACADVER ?? null;
    sonuc.oge = ham.length;
    const E = ham.map((e) => { const c = { ...e }; delete c.xdata; return c; });
    // dwg_free çağrılmaz: sonraki dosyada "null function" hatası veriyor (15 Kasım denemesi)
    fs.writeFileSync(path.join(gecici, `${is.anahtar}.katman.json`), json(L));
    fs.writeFileSync(path.join(gecici, `${is.anahtar}.oge.json`), json(E));
    sonuc.hafif = false;
    let dxf = null;
    try { const y = dxfYaz(lib, ab); dxf = y.dxf; sonuc.dxf_kod = y.kod; } catch (h) { sonuc.dxf_hata = String(h?.message || h).slice(0, 200); }
    if (dxf) {
      fs.writeFileSync(path.join(gecici, `${is.anahtar}.dxf`), dxf);
      sonuc.durum = 'cevrildi';
    } else {
      // DWG okundu ama DXF yazılamadı: öğe listesinden özet yine çıkar
      sonuc.durum = 'dxfsiz';
    }
  } catch (h) {
    sonuc.durum = 'hata';
    sonuc.hata = String(h?.message || h).slice(0, 200);
  }
  sonuc.sure = (Date.now() - bas) / 1000;
  if (sonuc.durum !== 'hata') fs.writeFileSync(path.join(gecici, `${is.anahtar}.bitti`), json(sonuc));
  console.log(json(sonuc));
}
