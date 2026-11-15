"""Disk arşivinin türevleri (İE-43 PR-2): DWG → DXF (sıkıştırılmış), JSON özet ve PNG önizleme.

Mac'te koşar (ezdxf 1.4.5, PyMuPDF, node + @mlightcad/libredwg-web 0.7.14). Ham dosyalara yazmaz; çıktı
`<kök>/_portman_analiz/turev/`. Her türev `turev/manifest.jsonl`'a bir satır yazar: kaynak SHA-256, araç sürümleri,
çıktıların SHA-256'sı, durum, süre. Aynı ham dosyadan aynı araçlarla yeniden üretilebilir.

  python3 turev.py dwg <kök> [--buyuk-mb 15] [--sure 160] [--gecici ~/hdd_gecici] [--node-sure 50]

Süre bitince durur; yeniden koşulunca manifestte olmayan dosyalardan devam eder.
"""

from __future__ import annotations

import argparse
import collections
import contextlib
import csv
import datetime
import gzip
import hashlib
import io
import json
import math
import os
import signal
import subprocess
import sys
import time

BURASI = os.path.dirname(os.path.abspath(__file__))
SEMA = "hdd_dxf_ozet/1"
LIBREDWG = "@mlightcad/libredwg-web 0.7.14 (LibreDWG 0.13.3)"
ONIZLEME_SINIR = 4000
SINIR = {"eklemeler": 20000, "yazilar": 20000, "olculer": 10000, "kapali": 10000}

# LibreDWG çizgi kalınlığı indeksi → DXF (1/100 mm)
LW = {0: 0, 1: 5, 2: 9, 3: 13, 4: 15, 5: 18, 6: 20, 7: 25, 8: 30, 9: 35, 10: 40, 11: 50, 12: 53, 13: 60, 14: 70,
      15: 80, 16: 90, 17: 100, 18: 106, 19: 120, 20: 140, 21: 158, 22: 200, 23: 211, 29: -1, 30: -2, 31: -3}


def _simdi() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_dosya(yol: str) -> str:
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for p in iter(lambda: f.read(1 << 20), b""):
            h.update(p)
    return h.hexdigest()


def r2(x: float) -> float:
    return round(float(x), 2)


# --- LibreDWG DXF çıktısının bilinen iki hatası (17 Ekim 2026 ölçümü) ---------------------------------------------

def katman_duzelt(doc, asil: dict) -> dict:
    """Bütün katmanlar kapalı yazılır (62 eksi) ve 420 renk DWG iç biçimindedir: DWG'deki hâle döndür."""
    renk = 0
    for lay in doc.layers:
        a = asil.get(lay.dxf.name, {})
        c = abs(lay.dxf.get("color", 7)) or 7
        lay.dxf.color = -c if a.get("off") else c
        if a.get("frozen"):
            lay.freeze()
        tc = lay.dxf.get("true_color")
        if tc is not None and not (0 <= tc <= 0xFFFFFF):
            lay.dxf.true_color = tc & 0xFFFFFF
            renk += 1
    for blk in doc.blocks:
        for e in blk:
            if e.dxf.is_supported("true_color"):
                tc = e.dxf.get("true_color")
                if tc is not None and not (0 <= tc <= 0xFFFFFF):
                    e.dxf.true_color = tc & 0xFFFFFF
                    renk += 1
    return {"renk_duzeltme": renk}


def _ortak(doc, x: dict) -> dict:
    a = {}
    lay = x.get("layer") or "0"
    if lay not in doc.layers:
        doc.layers.add(lay)
    a["layer"] = lay
    ci = x.get("colorIndex", 256)
    if isinstance(ci, int) and 0 <= ci <= 256:
        a["color"] = ci
    lt = x.get("lineType") or ""
    if lt and lt in doc.linetypes:
        a["linetype"] = lt
    if x.get("lineTypeScale"):
        a["ltscale"] = x["lineTypeScale"]
    if x.get("lineweight") in LW:
        a["lineweight"] = LW[x["lineweight"]]
    return a


def _v(p: dict) -> tuple:
    return (p.get("x", 0.0), p.get("y", 0.0), p.get("z", 0.0))


def _ekle(doc, msp, x: dict) -> bool:
    t, a = x["type"], _ortak(doc, x)
    if t == "LINE":
        msp.add_line(_v(x["startPoint"]), _v(x["endPoint"]), dxfattribs=a)
    elif t == "POINT":
        msp.add_point(_v(x["position"]), dxfattribs=a)
    elif t == "CIRCLE":
        msp.add_circle(_v(x["center"]), x["radius"], dxfattribs=a)
    elif t == "ARC":
        msp.add_arc(_v(x["center"]), x["radius"], math.degrees(x["startAngle"]), math.degrees(x["endAngle"]),
                    dxfattribs=a)
    elif t == "LWPOLYLINE":
        pts = [(p["x"], p["y"], 0, 0, p.get("bulge", 0)) for p in x["vertices"]]
        a["const_width"] = x.get("constantWidth", 0) or 0
        e = msp.add_lwpolyline(pts, format="xyseb", close=bool(x.get("flag", 0) & 1), dxfattribs=a)
        if x.get("elevation"):
            e.dxf.elevation = x["elevation"]
    elif t == "SOLID":
        msp.add_solid([_v(x["corner1"]), _v(x["corner2"]), _v(x["corner3"]), _v(x["corner4"])], dxfattribs=a)
    elif t == "TEXT":
        a.update(height=x.get("textHeight", 2.5), rotation=math.degrees(x.get("rotation", 0)))
        if x.get("styleName") in doc.styles:
            a["style"] = x["styleName"]
        msp.add_text(x.get("text", ""), dxfattribs=a).set_placement(_v(x["startPoint"]))
    elif t == "MTEXT":
        a.update(char_height=x.get("textHeight", 2.5), insert=_v(x["insertionPoint"]),
                 attachment_point=x.get("attachmentPoint", 1) or 1)
        if x.get("rectWidth"):
            a["width"] = x["rectWidth"]
        if x.get("styleName") in doc.styles:
            a["style"] = x["styleName"]
        msp.add_mtext(x.get("text", ""), dxfattribs=a)
    elif t == "INSERT":
        if x["name"] not in doc.blocks:
            return False
        a.update(xscale=x.get("xScale", 1) or 1, yscale=x.get("yScale", 1) or 1, zscale=x.get("zScale", 1) or 1,
                 rotation=math.degrees(x.get("rotation", 0)))
        msp.add_blockref(x["name"], _v(x["insertionPoint"]), dxfattribs=a)
    else:
        return False
    return True


def tamamla(doc, ogeler: list) -> dict:
    """LibreDWG'nin DXF yazarken düşürdüğü model alanı öğelerini wasm verisinden geri ekler."""
    msp = doc.modelspace()
    var = {e.dxf.handle.upper() for e in msp}
    eklenen, atlanan = collections.Counter(), collections.Counter()
    for x in ogeler:
        if x.get("type") == "ATTRIB":
            atlanan["ATTRIB"] += 1
            continue
        if str(x.get("handle", "")).upper() in var:
            continue
        try:
            ok = _ekle(doc, msp, x)
        except Exception:
            ok = False
        (eklenen if ok else atlanan)[x.get("type", "?")] += 1
    return {"eklenen": dict(eklenen), "atlanan": dict(atlanan)}


# --- JSON özet ------------------------------------------------------------------------------------------------------

def ozet(doc) -> dict:
    from ezdxf import bbox
    from ezdxf.math import area

    msp = doc.modelspace()
    turler = collections.Counter()
    katman_oge = collections.Counter()
    eklemeler, yazilar, olculer, kapali = [], [], [], []
    blok_adet = collections.Counter()
    for e in msp:
        t = e.dxftype()
        turler[t] += 1
        lay = e.dxf.get("layer", "0")
        katman_oge[lay] += 1
        try:
            if t == "INSERT":
                blok_adet[e.dxf.name] += 1
                if len(eklemeler) < SINIR["eklemeler"]:
                    p = e.dxf.insert
                    eklemeler.append({"blok": e.dxf.name, "x": r2(p.x), "y": r2(p.y), "aci": r2(e.dxf.get("rotation", 0)),
                                      "olcek": [r2(e.dxf.get("xscale", 1)), r2(e.dxf.get("yscale", 1))], "katman": lay,
                                      "nitelikler": {a.dxf.tag: a.dxf.text for a in e.attribs} or None})
            elif t in ("TEXT", "MTEXT") and len(yazilar) < SINIR["yazilar"]:
                p = e.dxf.insert
                metin = e.plain_text() if t == "MTEXT" else e.dxf.text
                h = e.dxf.get("char_height" if t == "MTEXT" else "height", 0)
                yazilar.append({"t": metin, "x": r2(p.x), "y": r2(p.y), "h": r2(h), "aci": r2(e.dxf.get("rotation", 0)),
                                "katman": lay})
            elif t == "DIMENSION" and len(olculer) < SINIR["olculer"]:
                try:
                    deger = r2(e.get_measurement())
                except Exception:
                    deger = None
                p1, p2 = e.dxf.get("defpoint2"), e.dxf.get("defpoint3")
                olculer.append({"deger": deger, "yazi": e.dxf.get("text", ""), "katman": lay,
                                "p1": [r2(p1.x), r2(p1.y)] if p1 else None, "p2": [r2(p2.x), r2(p2.y)] if p2 else None})
            elif t == "LWPOLYLINE" and e.closed and len(kapali) < SINIR["kapali"]:
                pts = [(x, y) for x, y in e.get_points("xy")]
                if len(pts) >= 3:
                    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                    kapali.append({"katman": lay, "alan": r2(abs(area(pts))), "kose": len(pts),
                                   "kutu": [r2(min(xs)), r2(min(ys)), r2(max(xs)), r2(max(ys))]})
        except Exception:
            turler["_okunamayan"] += 1
    try:
        b = bbox.extents(msp, fast=True)
        kapsam = [r2(b.extmin.x), r2(b.extmin.y), r2(b.extmax.x), r2(b.extmax.y)] if b.has_data else None
    except Exception:
        kapsam = None
    katmanlar = [{"ad": l.dxf.name, "renk": l.dxf.get("color", 7), "acik": l.is_on(), "oge": katman_oge.get(l.dxf.name, 0)}
                 for l in doc.layers]
    return {
        "dxf": {"surum": doc.dxfversion, "acadver": doc.header.get("$ACADVER"), "birim": doc.header.get("$INSUNITS"),
                "kapsam": kapsam},
        "oge_sayilari": dict(sorted(turler.items())),
        "katmanlar": katmanlar,
        "bloklar": [{"ad": a, "adet": n} for a, n in blok_adet.most_common()],
        "eklemeler": eklemeler,
        "yazilar": yazilar,
        "olculer": olculer,
        "kapali_cizgiler": kapali,
        "kesik": {k: len(v) >= SINIR[k2] for k, v, k2 in (("eklemeler", eklemeler, "eklemeler"),
                                                          ("yazilar", yazilar, "yazilar"),
                                                          ("olculer", olculer, "olculer"),
                                                          ("kapali_cizgiler", kapali, "kapali"))},
    }


# --- PNG önizleme ---------------------------------------------------------------------------------------------------

def _obekler(noktalar, G):
    hucre = collections.defaultdict(list)
    for c in noktalar:
        hucre[(int(c.x // G), int(c.y // G))].append(c)
    gor, sonuc = set(), []
    for h in hucre:
        if h in gor:
            continue
        yig, uye = [h], []
        gor.add(h)
        while yig:
            a = yig.pop()
            uye.extend(hucre[a])
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    n = (a[0] + dx, a[1] + dy)
                    if n in hucre and n not in gor:
                        gor.add(n)
                        yig.append(n)
        sonuc.append(uye)
    return sonuc


def onizleme(doc, png_yolu: str) -> dict:
    """Model alanının genel görünümü: küçük ve uzak artıklar atılır, siyah çizgi, beyaz zemin."""
    from ezdxf import bbox
    from ezdxf.addons.drawing import Frontend, RenderContext, config, layout
    from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend
    from ezdxf.math import BoundingBox2d, Vec2

    msp = doc.modelspace()
    merkez = []
    for e in msp:
        try:
            b = bbox.extents([e], fast=True)
        except Exception:
            continue
        if b.has_data:
            merkez.append(Vec2(b.center))
    if not merkez:
        return {"onizleme": "bos"}
    ilk = BoundingBox2d(merkez)
    olcek = max(5000.0, max(ilk.size.x, ilk.size.y) / 50)
    buyuk = [o for o in _obekler(merkez, olcek) if len(o) >= 30] or [merkez]
    secilen = [p for o in buyuk for p in o]
    kutu = BoundingBox2d(secilen)
    pay = max(kutu.size.x, kutu.size.y) * 0.02 + 1
    kutu = BoundingBox2d([kutu.extmin - Vec2(pay, pay), kutu.extmax + Vec2(pay, pay)])
    cfg = config.Configuration(background_policy=config.BackgroundPolicy.WHITE,
                               color_policy=config.ColorPolicy.BLACK, lineweight_scaling=0.6)
    be = PyMuPdfBackend()
    Frontend(RenderContext(doc), be, config=cfg).draw_layout(msp, finalize=True)
    w, h = kutu.size.x, kutu.size.y
    sayfa = (layout.Page(420, max(420 * h / w, 60), layout.Units.mm, margins=layout.Margins.all(4)) if w >= h
             else layout.Page(max(297 * w / h, 60), 297, layout.Units.mm, margins=layout.Margins.all(4)))
    veri = be.get_pixmap_bytes(sayfa, fmt="png", settings=layout.Settings(fit_page=True), dpi=96, render_box=kutu)
    with open(png_yolu, "wb") as f:
        f.write(veri)
    return {"onizleme_obek": len(buyuk), "onizleme_oge": len(secilen), "onizleme_toplam": len(merkez)}


# --- DWG akışı ------------------------------------------------------------------------------------------------------

def surumler() -> dict:
    import ezdxf
    try:
        import pymupdf
        pm = pymupdf.VersionBind
    except Exception:
        pm = None
    return {"libredwg": LIBREDWG, "ezdxf": ezdxf.__version__, "pymupdf": pm, "sema": SEMA,
            "python": sys.version.split()[0], "betik": sha256_dosya(os.path.abspath(__file__))[:12],
            "cevirici": sha256_dosya(os.path.join(BURASI, "dwg_toplu.mjs"))[:12]}


def oku_esleme(kok: str) -> list[dict]:
    with open(os.path.join(kok, "_portman_analiz", "kod_esleme.csv"), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


DURUM_SIRASI = {"hata": 0, "kismi": 1, "tamam": 2}


def manifest_durumlari(hedef: str) -> dict:
    """Bütün manifest parçaları (manifest*.jsonl): (kod, sıra, tür) başına en iyi durum (tamam > kismi > hata).

    Manifest yalnız eklenir; bir dosya yeniden işlenince yeni satır yazılır, iyi olan geçerlidir."""
    durum = {}
    for ad in sorted(os.listdir(hedef)) if os.path.isdir(hedef) else []:
        if not (ad.startswith("manifest") and ad.endswith(".jsonl")):
            continue
        with open(os.path.join(hedef, ad), encoding="utf-8") as f:
            for s in f:
                try:
                    d = json.loads(s)
                except ValueError:
                    continue
                k = (d["kod"], str(d["sira"]), d["tur"])
                if DURUM_SIRASI.get(d.get("durum"), 0) >= DURUM_SIRASI.get(durum.get(k), -1):
                    durum[k] = d.get("durum")
    return durum


def oku_manifest(hedef: str, yeniden: tuple = ()) -> set:
    """İşlenmiş sayılan (kod, sıra, tür) anahtarları; en iyi durumu `yeniden` içinde olanlar yeniden işlenir."""
    return {k for k, d in manifest_durumlari(hedef).items() if d not in yeniden}


def isle_dwg(anahtar: str, kayit: dict, gecici: str, hedef: str, arac: dict, node_sonuc: dict) -> dict:
    from ezdxf import recover

    kod, sira = kayit["kod"], kayit["sira"]
    satir = {"kod": kod, "sira": int(sira), "tur": "dwg", "kaynak_sha256": kayit["sha256"], "arac": arac,
             "tarih": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "dwg_surum": node_sonuc.get("surum"), "wasm_oge": node_sonuc.get("oge")}
    bas = time.time()
    dxf_g = os.path.join(gecici, anahtar + ".dxf")
    with contextlib.redirect_stdout(io.StringIO()):
        doc, aud = recover.readfile(dxf_g)
    satir["ezdxf_hata"] = len(aud.errors)
    satir.update(katman_duzelt(doc, json.load(open(os.path.join(gecici, anahtar + ".katman.json")))))
    satir["tamamlama"] = tamamla(doc, json.load(open(os.path.join(gecici, anahtar + ".oge.json"))))
    satir["dxf_oge"] = sum(1 for _ in doc.modelspace())
    # wasm listesindeki VIEWPORT'lar kağıt alanına aittir; model alanında olmamaları kayıp değildir
    # wasm listesindeki VIEWPORT'lar kağıt alanına, ATTRIB'ler bloğa bağlıdır; model alanında ayrı öğe değildir
    at = satir["tamamlama"]["atlanan"]
    beklenen = (satir["wasm_oge"] or 0) - at.get("VIEWPORT", 0) - at.get("ATTRIB", 0)
    satir["oge_tutar"] = satir["wasm_oge"] is not None and satir["dxf_oge"] == beklenen
    satir["kayip"] = {t: n for t, n in at.items() if t not in ("VIEWPORT", "ATTRIB")}

    klasor = os.path.join(hedef, "dwg", kod)
    os.makedirs(klasor, exist_ok=True)
    cikti = {}
    akis = io.StringIO()
    doc.write(akis)
    ham = akis.getvalue().encode(doc.output_encoding or "utf-8", errors="replace")
    yol = os.path.join(klasor, f"{sira}.dxf.gz")
    with open(yol, "wb") as f:
        f.write(gzip.compress(ham, 6, mtime=0))
    cikti["dxf_gz"] = {"yol": os.path.relpath(yol, hedef), "sha256": sha256_dosya(yol), "bayt": os.path.getsize(yol),
                       "acik_bayt": len(ham)}
    oz = {"kaynak": {"kod": kod, "sira": int(sira), "sha256": kayit["sha256"]}, "arac": arac, **ozet(doc)}
    yol = os.path.join(klasor, f"{sira}.json.gz")
    with open(yol, "wb") as f:
        f.write(gzip.compress(json.dumps(oz, ensure_ascii=False, separators=(",", ":")).encode("utf-8", "replace"), 6, mtime=0))
    cikti["json_gz"] = {"yol": os.path.relpath(yol, hedef), "sha256": sha256_dosya(yol), "bayt": os.path.getsize(yol)}
    try:
        yol = os.path.join(klasor, f"{sira}.png")
        if satir["dxf_oge"] > ONIZLEME_SINIR:
            # ezdxf çizimi büyük dosyada dakikalar sürüyor (31.547 öğe: 83 sn); önizleme DXF'ten sonra ayrı geçişte
            satir["onizleme"] = "ertelendi"
        else:
            satir.update(onizleme(doc, yol))
        if os.path.exists(yol):
            cikti["png"] = {"yol": os.path.relpath(yol, hedef), "sha256": sha256_dosya(yol), "bayt": os.path.getsize(yol)}
    except Exception as h:
        satir["onizleme_hata"] = str(h)[:200]
    satir["ciktilar"] = cikti
    satir["pano_eklemesi"] = sum(1 for x in oz["eklemeler"] if "PANO" in x["blok"].upper())
    satir["durum"] = "tamam"
    satir["sure"] = round(time.time() - bas + (node_sonuc.get("sure") or 0), 1)
    return satir


def _metin(b: bytes) -> str:
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("cp1254", errors="replace")


SINIR_AKIS = 200000


def _oge_kod(oge: dict, kod: bytes, v: bytes) -> None:
    with contextlib.suppress(ValueError):
        if kod == b"2":
            oge["blok"] = _metin(v)
        elif kod == b"8":
            oge["katman"] = _metin(v)
        elif kod == b"10":
            oge["x"] = r2(float(v))
        elif kod == b"20":
            oge["y"] = r2(float(v))
        elif kod == b"50":
            oge["aci"] = r2(float(v))
        elif kod == b"40":
            oge["h"] = r2(float(v))
        elif kod in (b"1", b"3"):
            oge["parca"].append((kod, _metin(v)))
        elif kod == b"67":
            oge["kagit"] = v == b"1"


def _oge_bitir(oge: dict, eklemeler: list, yazilar: list) -> None:
    ortak = {k: oge[k] for k in ("x", "y", "katman") if k in oge}
    if oge.get("kagit"):
        ortak["kagit"] = True
    if oge["tur"] == b"INSERT":
        if len(eklemeler) < SINIR_AKIS:
            eklemeler.append({"blok": oge.get("blok"), **ortak, "aci": oge.get("aci", 0.0)})
    elif len(yazilar) < SINIR_AKIS:
        # MTEXT: 3'lü parçalar önce, 1 en son; TEXT: yalnız 1
        metin = "".join(m for k, m in oge["parca"] if k == b"3") + "".join(m for k, m in oge["parca"] if k == b"1")
        yazilar.append({"t": metin, **ortak, "h": oge.get("h")})


def dxf_akis(kaynak: str, yol: str | None) -> dict:
    """Büyük DXF'i satır satır bir kez okur: gzip'e yazar ve özetini çıkarır (bellek sabit, ezdxf yok).

    Özet: başlık ($ACADVER, $INSUNITS, $EXTMIN/$EXTMAX), ENTITIES bölümünde öğe türleri, INSERT'ler (blok, konum, açı,
    katman) ve yazılar (TEXT, MTEXT: metin, konum, yükseklik, katman), LAYER tablosunda ad ve renk (62; LibreDWG'nin yazdığı
    eksi işaret ayrıca tutulur). Büyük dosyalar çoğu kez birçok projenin çizimini birlikte taşır (15 Kasım: 49 MB'lık
    DWG'de 434.021 öğe, 2.882 pano bloğu)."""
    turler, bloklar, katmanlar, baslik = collections.Counter(), collections.Counter(), {}, {}
    eklemeler, yazilar = [], []
    oge = None
    bolum = kayit = degisken = katman = None
    bolum_bekle = False
    tampon, kod = [], None
    # yol None: yalnız özet (arşivde zaten DXF olan dosyalar; kopyası yazılmaz)
    with open(kaynak, "rb") as g, (gzip.GzipFile(yol, "wb", compresslevel=6, mtime=0) if yol else
                                   contextlib.nullcontext()) as f:
        for i, satir in enumerate(g):
            if f is not None:
                tampon.append(satir)
                if len(tampon) >= 65536:
                    f.write(b"".join(tampon))
                    tampon.clear()
            if i % 2 == 0:
                kod = satir.strip()
                continue
            v = satir.strip()
            if kod == b"0":
                if oge is not None:
                    _oge_bitir(oge, eklemeler, yazilar)
                    oge = None
                kayit, katman = v, None
                if v == b"SECTION":
                    bolum_bekle = True
                elif v == b"ENDSEC":
                    bolum = None
                elif bolum == b"ENTITIES":
                    turler[_metin(v)] += 1
                    if v in (b"INSERT", b"TEXT", b"MTEXT"):
                        oge = {"tur": v, "parca": []}
            elif oge is not None:
                if kod == b"2" and oge["tur"] == b"INSERT":
                    bloklar[_metin(v)] += 1
                _oge_kod(oge, kod, v)
            elif kod == b"2":
                if bolum_bekle:
                    bolum, bolum_bekle = v, False
                elif bolum == b"TABLES" and kayit == b"LAYER" and katman is None:
                    katman = _metin(v)
                    katmanlar[katman] = {"ad": katman}
            elif bolum == b"HEADER":
                if kod == b"9":
                    degisken = _metin(v)
                elif degisken == "$ACADVER" and kod == b"1":
                    baslik["surum"] = _metin(v)
                elif degisken == "$INSUNITS" and kod == b"70":
                    baslik["birim"] = int(v)
                elif degisken in ("$EXTMIN", "$EXTMAX") and kod in (b"10", b"20", b"30"):
                    with contextlib.suppress(ValueError):
                        baslik.setdefault(degisken, {})[_metin(kod)] = r2(float(v))
            elif katman is not None and kod == b"62":
                with contextlib.suppress(ValueError):
                    katmanlar[katman].update(renk=abs(int(v)), eksi_yazili=int(v) < 0)
            elif katman is not None and kod == b"420":
                with contextlib.suppress(ValueError):
                    katmanlar[katman]["gercek_renk"] = int(v) & 0xFFFFFF
        if f is not None:
            f.write(b"".join(tampon))
    if oge is not None:
        _oge_bitir(oge, eklemeler, yazilar)
    kapsam = None
    if "$EXTMIN" in baslik and "$EXTMAX" in baslik:
        kapsam = [[baslik["$EXTMIN"].get(k) for k in ("10", "20", "30")], [baslik["$EXTMAX"].get(k) for k in ("10", "20", "30")]]
    return {"dxf": {"surum": baslik.get("surum"), "birim": baslik.get("birim"), "kapsam": kapsam},
            "oge_sayilari": dict(sorted(turler.items())), "katmanlar": list(katmanlar.values()),
            "bloklar": [{"ad": a, "adet": n} for a, n in bloklar.most_common()],
            "eklemeler": eklemeler, "yazilar": yazilar,
            "kesik": {k: True for k, L in (("eklemeler", eklemeler), ("yazilar", yazilar)) if len(L) >= SINIR_AKIS}}


def isle_buyuk(anahtar: str, kayit: dict, gecici: str, hedef: str, arac: dict, node_sonuc: dict) -> dict:
    """Büyük 3D model: LibreDWG'nin DXF'i olduğu gibi sıkıştırılır; özet aynı geçişte DXF'ten (ezdxf yok: bellek ve süre)."""
    kod, sira = kayit["kod"], kayit["sira"]
    bas = time.time()
    klasor = os.path.join(hedef, "dwg", kod)
    os.makedirs(klasor, exist_ok=True)
    kaynak = os.path.join(gecici, anahtar + ".dxf")
    yol = os.path.join(klasor, f"{sira}.dxf.gz")
    akis = dxf_akis(kaynak, yol)
    cikti = {"dxf_gz": {"yol": os.path.relpath(yol, hedef), "sha256": sha256_dosya(yol), "bayt": os.path.getsize(yol),
                        "acik_bayt": os.path.getsize(kaynak), "duzeltme": "yok"}}
    oz = {"kaynak": {"kod": kod, "sira": int(sira), "sha256": kayit["sha256"]}, "arac": arac, **akis,
          "not": "büyük dosya: DXF LibreDWG çıktısı olduğu gibi (katmanlar kapalı yazılı, 420 rengi iç biçimde; öğe sayısı "
                 "DWG'yle kıyaslanmadı); özet DXF'ten akışla"}
    yol = os.path.join(klasor, f"{sira}.json.gz")
    with open(yol, "wb") as f:
        f.write(gzip.compress(json.dumps(oz, ensure_ascii=False, separators=(",", ":")).encode("utf-8", "replace"), 6, mtime=0))
    cikti["json_gz"] = {"yol": os.path.relpath(yol, hedef), "sha256": sha256_dosya(yol), "bayt": os.path.getsize(yol)}
    return {"kod": kod, "sira": int(sira), "tur": "dwg", "kaynak_sha256": kayit["sha256"], "arac": arac,
            "tarih": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "dwg_surum": akis["dxf"]["surum"], "dxf_oge": sum(akis["oge_sayilari"].values()), "buyuk": True,
            "ciktilar": cikti, "durum": "tamam", "duzeltme": "yok",
            "pano_eklemesi": sum(b["adet"] for b in akis["bloklar"] if "PANO" in b["ad"].upper()),
            "sure": round(time.time() - bas + (node_sonuc.get("sure") or 0), 1)}


def wasm_ozet(ogeler: list) -> dict:
    """DXF yazılamayan ya da ezdxf'in açamadığı dosyada özet: DWG'den okunan öğe listesinden."""
    def nokta(x, *adlar):
        for a in adlar:
            p = x.get(a)
            if isinstance(p, dict):
                return r2(p.get("x", 0)), r2(p.get("y", 0))
        return None, None
    turler, bloklar = collections.Counter(), collections.Counter()
    eklemeler, yazilar = [], []
    for x in ogeler:
        t = x.get("type", "?")
        turler[t] += 1
        if t == "INSERT":
            bloklar[x.get("name")] += 1
            if len(eklemeler) < SINIR["eklemeler"]:
                px, py = nokta(x, "insertionPoint")
                eklemeler.append({"blok": x.get("name"), "x": px, "y": py,
                                  "aci": r2(math.degrees(x.get("rotation", 0) or 0)), "katman": x.get("layer")})
        elif t in ("TEXT", "MTEXT") and len(yazilar) < SINIR["yazilar"]:
            px, py = nokta(x, "insertionPoint", "startPoint")
            yazilar.append({"t": x.get("text", ""), "x": px, "y": py, "h": r2(x.get("textHeight", 0) or 0),
                            "katman": x.get("layer")})
    return {"oge_sayilari": dict(sorted(turler.items())), "bloklar": [{"ad": a, "adet": n} for a, n in bloklar.most_common()],
            "eklemeler": eklemeler, "yazilar": yazilar, "kaynak_ozet": "wasm"}


def isle_yedek(anahtar: str, kayit: dict, gecici: str, hedef: str, arac: dict, node_sonuc: dict, neden: str) -> dict:
    """ezdxf işleyemedi ya da DXF yazılamadı: ham DXF (varsa) sıkıştırılır, özet öğe listesinden."""
    kod, sira = kayit["kod"], kayit["sira"]
    klasor = os.path.join(hedef, "dwg", kod)
    os.makedirs(klasor, exist_ok=True)
    cikti, akis = {}, None
    kaynak = os.path.join(gecici, anahtar + ".dxf")
    if os.path.exists(kaynak):
        yol = os.path.join(klasor, f"{sira}.dxf.gz")
        try:
            akis = dxf_akis(kaynak, yol)        # ezdxf'in açamadığı DXF'te de satır satır okunur
        except Exception:
            with open(kaynak, "rb") as g, gzip.GzipFile(yol, "wb", compresslevel=6, mtime=0) as f:
                for p in iter(lambda: g.read(1 << 22), b""):
                    f.write(p)
        cikti["dxf_gz"] = {"yol": os.path.relpath(yol, hedef), "sha256": sha256_dosya(yol),
                           "bayt": os.path.getsize(yol), "acik_bayt": os.path.getsize(kaynak), "duzeltme": "yok"}
    oge_yolu = os.path.join(gecici, anahtar + ".oge.json")
    wasm = wasm_ozet(json.load(open(oge_yolu))) if os.path.exists(oge_yolu) else {}
    if akis:
        wasm = {k: v for k, v in wasm.items() if k == "oge_sayilari"}
        if wasm:
            wasm = {"wasm_oge_sayilari": wasm["oge_sayilari"]}
    oz = {"kaynak": {"kod": kod, "sira": int(sira), "sha256": kayit["sha256"]}, "arac": arac, **(akis or {}), **wasm,
          "kaynak_ozet": "dxf_akis" if akis else ("wasm" if wasm else None), "not": neden}
    yol = os.path.join(klasor, f"{sira}.json.gz")
    with open(yol, "wb") as f:
        f.write(gzip.compress(json.dumps(oz, ensure_ascii=False, separators=(",", ":")).encode("utf-8", "replace"), 6, mtime=0))
    cikti["json_gz"] = {"yol": os.path.relpath(yol, hedef), "sha256": sha256_dosya(yol), "bayt": os.path.getsize(yol)}
    return {"kod": kod, "sira": int(sira), "tur": "dwg", "kaynak_sha256": kayit["sha256"], "arac": arac,
            "tarih": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "wasm_oge": node_sonuc.get("oge"), "ciktilar": cikti, "durum": "kismi", "hata": neden,
            "pano_eklemesi": sum(1 for x in oz.get("eklemeler", []) if "PANO" in str(x.get("blok", "")).upper())}


GECICI_EKLER = (".dxf", ".katman.json", ".oge.json", ".bitti")
ISLEME_SINIR = 90  # sn: bir dosyanın ezdxf işlemesi bundan uzunsa akışla özetlenir (kismi)


class SureAsimi(BaseException):
    """SIGALRM; BaseException: ezdxf'in genel `except Exception` blokları yutmasın."""


def _alarm(_isaret, _cerceve):
    raise SureAsimi()


signal.signal(signal.SIGALRM, _alarm)


def dwg(kok: str, buyuk_mb: float, sure: float, gecici: str, node_sure: float, parca: str = "0/1",
        yalniz: str = "hepsi", yeniden: tuple = ()) -> int:
    bas = time.time()
    k_no, n_parca = (int(x) for x in parca.split("/"))
    hedef = os.path.join(kok, "_portman_analiz", "turev")
    os.makedirs(hedef, exist_ok=True)
    gecici = f"{gecici}_{k_no}" if n_parca > 1 else gecici
    os.makedirs(gecici, exist_ok=True)
    manifest = os.path.join(hedef, "manifest.jsonl" if n_parca == 1 else f"manifest_p{k_no}.jsonl")
    bitti = oku_manifest(hedef, yeniden)
    arac = surumler()
    kayitlar, bekleyen = {}, []
    for k in oku_esleme(kok):
        if not k["dosya"].lower().endswith(".dwg") or (k["kod"], k["sira"], "dwg") in bitti:
            continue
        if int(k["sha256"][:8], 16) % n_parca != k_no:
            continue
        girdi = os.path.join(kok, k["proje_klasoru"], k["dosya"])
        bayt = os.path.getsize(girdi)
        hafif = bayt > buyuk_mb * 1e6
        if (yalniz == "kucuk" and hafif) or (yalniz == "buyuk" and not hafif):
            continue
        anahtar = f"{k['kod']}_{k['sira']}"
        kayitlar[anahtar] = dict(k, girdi=girdi, hafif=hafif, bayt=bayt)
        bekleyen.append(anahtar)
    bekleyen.sort(key=lambda a: kayitlar[a]["bayt"])
    deneme_yolu = os.path.join(gecici, "deneme.json")
    deneme = json.load(open(deneme_yolu)) if os.path.exists(deneme_yolu) else {}
    hatali = {}

    def hazirlar():
        return [a for a in bekleyen if os.path.exists(os.path.join(gecici, a + ".bitti"))]

    n = 0
    islenen = set()
    while time.time() - bas < sure - 45:
        hazir = [a for a in hazirlar() if a not in islenen]
        if not hazir:
            # iki denemede çevrilemeyenler önce yazılır; yalnız onlar kaldıysa da manifeste girer
            for a in bekleyen:
                if deneme.get(a, 0) >= 2 and a not in islenen:
                    hatali[a] = "iki denemede çevrilemedi (zaman aşımı ya da çökme)"
            sira = [a for a in bekleyen if deneme.get(a, 0) < 2 and a not in islenen and a not in hatali]
            if not sira and not hatali:
                break
            if sira:
                liste = os.path.join(gecici, "liste.jsonl")
                with open(liste, "w", encoding="utf-8") as f:
                    for a in (sira[:1] if kayitlar[sira[0]]["hafif"] else sira[:300]):
                        f.write(json.dumps({"anahtar": a, "girdi": kayitlar[a]["girdi"], "hafif": kayitlar[a]["hafif"]},
                                           ensure_ascii=False) + "\n")
                ns = max(15.0, min(node_sure, sure - 45 - (time.time() - bas)))
                # büyük modelde tek dosyanın çevrimi sürenin kalanını kullanabilir; işlenmesi sonraki koşuya kalabilir
                zaman = max(ns + 60, sure - (time.time() - bas)) if kayitlar[sira[0]]["hafif"] else ns + 60
                cikis, kod = "", 0
                try:
                    r = subprocess.run(["node", os.path.join(BURASI, "dwg_toplu.mjs"), liste, gecici, str(ns)],
                                       capture_output=True, text=True, timeout=zaman)
                    cikis, kod = r.stdout, r.returncode
                except subprocess.TimeoutExpired as h:
                    cikis = h.stdout.decode() if isinstance(h.stdout, bytes) else (h.stdout or "")
                    kod = -9
                sonuclar = {}
                for s_ in cikis.splitlines():
                    with contextlib.suppress(ValueError, KeyError):
                        d = json.loads(s_)
                        sonuclar[d["anahtar"]] = d
                for a, d in sonuclar.items():
                    if d.get("durum") == "hata":
                        hatali[a] = d.get("hata") or "hata"
                if kod != 0:
                    yarim = next((a for a in sira[:300] if a not in sonuclar), None)
                    if yarim:
                        deneme[yarim] = deneme.get(yarim, 0) + 1
                json.dump(deneme, open(deneme_yolu, "w"))
            hazir = [a for a in hazirlar() if a not in islenen]
            if not hazir and not hatali:
                break
        with open(manifest, "a", encoding="utf-8") as m:
            for a, hata in list(hatali.items()):
                k = kayitlar[a]
                m.write(json.dumps({"kod": k["kod"], "sira": int(k["sira"]), "tur": "dwg", "kaynak_sha256": k["sha256"],
                                    "arac": arac, "tarih": _simdi(), "durum": "hata", "hata": hata}, ensure_ascii=False) + "\n")
                islenen.add(a)
                n += 1
            hatali.clear()
            for a in hazir:
                if time.time() - bas > sure - 40:
                    break
                k = kayitlar[a]
                ns_ = json.load(open(os.path.join(gecici, a + ".bitti")))
                # bir dosyada takılan ezdxf koşuyu kilitlemesin (15 Kasım: bir parça 3 saat aynı dosyada kaldı)
                kalan_sn = int(sure - 15 - (time.time() - bas))
                sinir = min(ISLEME_SINIR, kalan_sn)
                try:
                    signal.alarm(max(1, sinir))
                    if ns_.get("durum") == "dxfsiz":
                        satir = isle_yedek(a, k, gecici, hedef, arac, ns_, f"DXF yazılamadı (kod {ns_.get('dxf_kod')}): {ns_.get('dxf_hata') or ''}")
                    else:
                        satir = (isle_buyuk if ns_.get("hafif") else isle_dwg)(a, k, gecici, hedef, arac, ns_)
                    signal.alarm(0)
                except SureAsimi:
                    signal.alarm(0)
                    if sinir < ISLEME_SINIR:
                        break                      # koşunun süresi bitti; dosya sonraki koşuda yeniden işlenir
                    satir = isle_yedek(a, k, gecici, hedef, arac, ns_, f"isleme {ISLEME_SINIR} sn'de bitmedi")
                except Exception as h:
                    signal.alarm(0)
                    try:
                        satir = isle_yedek(a, k, gecici, hedef, arac, ns_, f"isleme: {str(h)[:200]}")
                    except Exception as h2:
                        satir = {"kod": k["kod"], "sira": int(k["sira"]), "tur": "dwg", "kaynak_sha256": k["sha256"],
                                 "arac": arac, "durum": "hata", "hata": f"isleme: {str(h)[:150]}; yedek: {str(h2)[:100]}"}
                if ns_.get("dxf_kod") is not None:
                    satir["dxf_kod"] = ns_["dxf_kod"]   # LibreDWG'nin DXF yazım kodu (0 temiz; 128'in altı kritik değil)
                m.write(json.dumps(satir, ensure_ascii=False) + "\n")
                m.flush()
                for son in GECICI_EKLER:
                    with contextlib.suppress(FileNotFoundError):
                        os.remove(os.path.join(gecici, a + son))
                islenen.add(a)
                n += 1
    kalan = len(bekleyen) - n
    print(f"bu koşu {n} DWG; kalan {kalan}; süre {time.time() - bas:.0f} sn")
    return 0 if kalan == 0 else 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = ap.add_subparsers(dest="komut", required=True)
    d = alt.add_parser("dwg")
    d.add_argument("kok")
    d.add_argument("--buyuk-mb", type=float, default=15.0, help="bundan büyük DWG hafif yoldan (3D modeller)")
    d.add_argument("--sure", type=float, default=150.0)
    d.add_argument("--node-sure", type=float, default=60.0)
    d.add_argument("--gecici", default=os.path.expanduser("~/hdd_gecici"))
    d.add_argument("--parca", default="0/1", help="k/n: paralel koşu için dosyaların k'ıncı parçası")
    d.add_argument("--yalniz", choices=("hepsi", "kucuk", "buyuk"), default="hepsi")
    d.add_argument("--yeniden", default="", help="virgüllü durumlar (hata,kismi): en iyi durumu bunlar olan dosyalar yeniden")
    a = ap.parse_args(argv)
    if a.komut == "dwg":
        return dwg(a.kok, a.buyuk_mb, a.sure, a.gecici, a.node_sure, a.parca, a.yalniz,
                   tuple(x for x in a.yeniden.split(",") if x))
    return 1


if __name__ == "__main__":
    sys.exit(main())
