"""Disk arşivinin türevleri (İE-43 PR-2): PDF, Excel ve görseller.

  python3 turev_belge.py pdf    <kök> [--sure 150] [--parca k/n] [--sayfa-onizleme 10]
  python3 turev_belge.py excel  <kök> [--sure 150] [--parca k/n]
  python3 turev_belge.py gorsel <kök> [--sure 150] [--parca k/n]
  python3 turev_belge.py dxf    <kök> [--sure 150] [--parca k/n]

Mac'te koşar; ham dosyaya yazmaz. Çıktı `<kök>/_portman_analiz/turev/<tür>/<kod>/<sıra>.*`, manifest
`turev/manifest_<tür>[_p<k>].jsonl` (DWG'nin manifestiyle aynı biçim). Kişisel veri (Excel'deki TC kimlik no, telefon,
adres; fotoğraflardaki konum) bu çıktılarda olduğu gibi durur: çıktılar yalnız Mac'te ve Drive'da kalır, depoya girmez.
"""

from __future__ import annotations

import argparse
import datetime
import gzip
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from turev import dxf_akis, oku_esleme, oku_manifest, r2, sha256_dosya  # noqa: E402

SINIR_SEGMENT = 100000
SINIR_BLOK = 5000
SON_DOSYA_PAYI = 20  # sn: süre bitmeden bu kadar önce yeni dosyaya başlanmaz


def _simdi() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _yaz_json_gz(yol: str, veri: dict) -> dict:
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "wb") as f:
        f.write(gzip.compress(json.dumps(veri, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 6, mtime=0))
    return {"sha256": sha256_dosya(yol), "bayt": os.path.getsize(yol)}


def surumler() -> dict:
    s = {"python": sys.version.split()[0], "betik": sha256_dosya(os.path.abspath(__file__))[:12]}
    for ad, modul in (("pymupdf", "pymupdf"), ("openpyxl", "openpyxl"), ("pillow", "PIL")):
        try:
            m = __import__(modul)
            s[ad] = getattr(m, "VersionBind", None) or getattr(m, "__version__", None)
        except Exception:
            s[ad] = None
    return s


# --- PDF ------------------------------------------------------------------------------------------------------------

def isle_pdf(girdi: str, klasor: str, sira: str, hedef: str, sayfa_onizleme: int) -> dict:
    import pymupdf

    doc = pymupdf.open(girdi)
    sayfalar, ciktilar = [], {}
    toplam_metin = 0
    for i, pg in enumerate(doc):
        d = {"no": i + 1, "boyut": [r2(pg.rect.width), r2(pg.rect.height)], "donus": pg.rotation}
        metin = pg.get_text("text")
        toplam_metin += len(metin.strip())
        d["metin"] = metin
        d["bloklar"] = [[r2(b[0]), r2(b[1]), r2(b[2]), r2(b[3]), b[4]] for b in pg.get_text("blocks") if b[6] == 0][:SINIR_BLOK]
        d["resim_sayisi"] = len(pg.get_images())
        cizgi, dikdortgen = [], []
        try:
            for yol in pg.get_drawings():
                for it in yol.get("items", []):
                    if len(cizgi) + len(dikdortgen) >= SINIR_SEGMENT:
                        d["cizgi_kesik"] = True
                        break
                    if it[0] == "l":
                        cizgi.append([r2(it[1].x), r2(it[1].y), r2(it[2].x), r2(it[2].y)])
                    elif it[0] == "re":
                        r = it[1]
                        dikdortgen.append([r2(r.x0), r2(r.y0), r2(r.x1), r2(r.y1)])
                    elif it[0] == "c":
                        cizgi.append([r2(it[1].x), r2(it[1].y), r2(it[4].x), r2(it[4].y), "c"])
                    elif it[0] == "qu":
                        q = it[1]
                        dikdortgen.append([r2(q.ul.x), r2(q.ul.y), r2(q.lr.x), r2(q.lr.y), "q"])
        except Exception as h:
            d["cizgi_hata"] = str(h)[:100]
        d["cizgiler"], d["dikdortgenler"] = cizgi, dikdortgen
        if i < sayfa_onizleme:
            yol = os.path.join(klasor, f"{sira}_s{i + 1}.png")
            pix = pg.get_pixmap(dpi=72, colorspace=pymupdf.csGRAY)
            pix.save(yol)
            ciktilar[f"png_s{i + 1}"] = {"yol": os.path.relpath(yol, hedef), "sha256": sha256_dosya(yol),
                                         "bayt": os.path.getsize(yol)}
        sayfalar.append(d)
    oz = {"sayfa_sayisi": doc.page_count, "meta": {k: v for k, v in (doc.metadata or {}).items() if v},
          "taranmis_olabilir": toplam_metin < 20 and any(s["resim_sayisi"] for s in sayfalar), "sayfalar": sayfalar}
    return oz, ciktilar


# --- Excel ----------------------------------------------------------------------------------------------------------

def _hucre(v):
    if isinstance(v, (datetime.datetime, datetime.date, datetime.time)):
        return v.isoformat()
    if isinstance(v, float):
        return round(v, 6)
    return v if isinstance(v, (int, str, bool)) or v is None else str(v)


def isle_excel(girdi: str, klasor: str, sira: str, hedef: str, _sayfa_onizleme: int) -> dict:
    import openpyxl

    if girdi.lower().endswith(".xls"):
        raise ValueError("eski .xls biçimi: bu araçla okunmaz")
    wb_f = openpyxl.load_workbook(girdi, data_only=False)
    wb_v = openpyxl.load_workbook(girdi, data_only=True)
    sayfalar = []
    for ws in wb_f.worksheets:
        wv = wb_v[ws.title]
        hucreler = []
        for satir in ws.iter_rows():
            for c in satir:
                if c.value is None:
                    continue
                kayit = [c.coordinate, _hucre(wv[c.coordinate].value)]
                if isinstance(c.value, str) and c.value.startswith("="):
                    kayit.append(c.value)
                hucreler.append(kayit)
        sayfalar.append({"ad": ws.title, "durum": ws.sheet_state, "boyut": [ws.max_row, ws.max_column],
                         "birlesik": [str(r) for r in ws.merged_cells.ranges][:2000], "hucreler": hucreler})
    return {"sayfa_sayisi": len(sayfalar), "sayfalar": sayfalar}, {}


# --- Görsel ---------------------------------------------------------------------------------------------------------

def isle_gorsel(girdi: str, klasor: str, sira: str, hedef: str, _sayfa_onizleme: int) -> dict:
    from PIL import ExifTags, Image

    oz = {}
    with Image.open(girdi) as im:
        oz["boyut"] = list(im.size)
        oz["kip"] = im.mode
        oz["bicim"] = im.format
        exif = im.getexif()
        e = {ExifTags.TAGS.get(k, str(k)): str(v)[:200] for k, v in exif.items()
             if not isinstance(v, bytes)}
        try:
            alt = exif.get_ifd(0x8769)
            e.update({ExifTags.TAGS.get(k, str(k)): str(v)[:200] for k, v in alt.items() if not isinstance(v, bytes)})
        except Exception:
            pass
        try:
            gps = exif.get_ifd(0x8825)
            if gps:
                oz["konum"] = {ExifTags.GPSTAGS.get(k, str(k)): str(v)[:100] for k, v in gps.items()
                               if not isinstance(v, bytes)}
        except Exception:
            pass
        oz["exif"] = e
        oz["cekim_tarihi"] = e.get("DateTimeOriginal") or e.get("DateTime")
        im2 = im.convert("RGB")
        im2.thumbnail((640, 640))
        yol = os.path.join(klasor, f"{sira}_onizleme.jpg")
        im2.save(yol, "JPEG", quality=80)
    return oz, {"jpg": {"yol": os.path.relpath(yol, hedef), "sha256": sha256_dosya(yol), "bayt": os.path.getsize(yol)}}


# --- Arşivde hazır DXF -------------------------------------------------------------------------------------------

def isle_dxf(girdi: str, klasor: str, sira: str, hedef: str, _sayfa_onizleme: int) -> dict:
    """Arşivde zaten DXF olan dosya: kopyası yazılmaz, özet akışla (başlık, öğe türleri, eklemeler, yazılar, katmanlar)."""
    return dxf_akis(girdi, None), {}


TURLER = {
    "pdf": (("pdf",), isle_pdf),
    "excel": (("xlsx", "xls"), isle_excel),
    "gorsel": (("jpg", "jpeg", "png", "bmp", "webp"), isle_gorsel),
    "dxf": (("dxf",), isle_dxf),
}


def calistir(tur: str, kok: str, sure: float, parca: str, sayfa_onizleme: int) -> int:
    bas = time.time()
    uzantilar, isleyici = TURLER[tur]
    k_no, n_parca = (int(x) for x in parca.split("/"))
    hedef = os.path.join(kok, "_portman_analiz", "turev")
    os.makedirs(hedef, exist_ok=True)
    manifest = os.path.join(hedef, f"manifest_{tur}" + (f"_p{k_no}" if n_parca > 1 else "") + ".jsonl")
    bitti = oku_manifest(hedef)
    arac = surumler()
    bekleyen = []
    for k in oku_esleme(kok):
        uz = k["dosya"].rsplit(".", 1)[-1].lower() if "." in k["dosya"] else ""
        if uz not in uzantilar or (k["kod"], k["sira"], tur) in bitti:
            continue
        if int(k["sha256"][:8], 16) % n_parca != k_no:
            continue
        bekleyen.append(k)
    # bir dosya süre ya da bellek yüzünden iki koşuda bitmezse "hata" yazılır, sıra öteki dosyalara geçer
    deneme_yol = os.path.join(hedef, f"deneme_{tur}" + (f"_p{k_no}" if n_parca > 1 else "") + ".json")
    deneme = json.load(open(deneme_yol, encoding="utf-8")) if os.path.exists(deneme_yol) else {}

    def _deneme_yaz():
        with open(deneme_yol + ".tmp", "w", encoding="utf-8") as f:
            json.dump(deneme, f)
        os.replace(deneme_yol + ".tmp", deneme_yol)

    n = 0
    with open(manifest, "a", encoding="utf-8") as m:
        for k in bekleyen:
            if time.time() - bas > sure - SON_DOSYA_PAYI:
                break
            t0 = time.time()
            girdi = os.path.join(kok, k["proje_klasoru"], k["dosya"])
            klasor = os.path.join(hedef, tur, k["kod"])
            os.makedirs(klasor, exist_ok=True)
            satir = {"kod": k["kod"], "sira": int(k["sira"]), "tur": tur, "kaynak_sha256": k["sha256"], "arac": arac,
                     "tarih": _simdi()}
            anahtar = f"{k['kod']}_{k['sira']}"
            if deneme.get(anahtar, 0) >= 2:
                satir.update(durum="hata", hata="iki koşuda bitmedi (süre ya da bellek)", sure=0)
                m.write(json.dumps(satir, ensure_ascii=False) + "\n")
                m.flush()
                deneme.pop(anahtar)
                _deneme_yaz()
                n += 1
                continue
            deneme[anahtar] = deneme.get(anahtar, 0) + 1
            _deneme_yaz()
            try:
                oz, ciktilar = isleyici(girdi, klasor, k["sira"], hedef, sayfa_onizleme)
                oz = {"kaynak": {"kod": k["kod"], "sira": int(k["sira"]), "sha256": k["sha256"]}, "arac": arac, **oz}
                yol = os.path.join(klasor, f"{k['sira']}.json.gz")
                ciktilar["json_gz"] = {"yol": os.path.relpath(yol, hedef), **_yaz_json_gz(yol, oz)}
                satir.update(durum="tamam", ciktilar=ciktilar)
                if tur == "pdf":
                    satir.update(sayfa=oz["sayfa_sayisi"], taranmis_olabilir=oz["taranmis_olabilir"])
                elif tur == "gorsel":
                    satir.update(konum_var="konum" in oz, cekim_tarihi=oz.get("cekim_tarihi"))
                elif tur == "excel":
                    satir.update(sayfa=oz["sayfa_sayisi"])
                elif tur == "dxf":
                    satir.update(dxf_oge=sum(oz["oge_sayilari"].values()), dwg_surum=oz["dxf"]["surum"],
                                 pano_eklemesi=sum(b["adet"] for b in oz["bloklar"] if "PANO" in b["ad"].upper()))
            except Exception as h:
                satir.update(durum="hata", hata=str(h)[:200])
            satir["sure"] = round(time.time() - t0, 1)
            m.write(json.dumps(satir, ensure_ascii=False) + "\n")
            m.flush()
            deneme.pop(anahtar, None)
            _deneme_yaz()
            n += 1
    kalan = len(bekleyen) - n
    print(f"{tur}: bu koşu {n}; kalan {kalan}; süre {time.time() - bas:.0f} sn")
    return 0 if kalan == 0 else 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tur", choices=sorted(TURLER))
    ap.add_argument("kok")
    ap.add_argument("--sure", type=float, default=150.0)
    ap.add_argument("--parca", default="0/1")
    ap.add_argument("--sayfa-onizleme", type=int, default=10)
    a = ap.parse_args(argv)
    return calistir(a.tur, a.kok, a.sure, a.parca, a.sayfa_onizleme)


if __name__ == "__main__":
    sys.exit(main())
