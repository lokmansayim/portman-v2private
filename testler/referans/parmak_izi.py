"""İçerik parmak izi: DXF ve PDF çıktılarının dosya özeti her koşuda değişir, içeriği değişmemelidir.

Motor'un DXF'i oluşturma zamanı ($TDCREATE, $TDUPDATE) ve rastgele kimlikler ($FINGERPRINTGUID, $VERSIONGUID)
taşır; PDF de oluşturma tarihi ve kimlik taşır. Bu yüzden aynı girdiden iki koşu farklı sha256 verir
(28.09 ölçümü, testler/referans/README.md). Bu betik içerikten özet çıkarır:

  DXF: model ve kâğıt alanındaki her varlık (tür, katman, blok adı, yuvarlanmış geometri, metin) sıralı listeye
       yazılır; tutamaç (handle), zaman ve kimlik alanları dışarıda kalır.
  PDF: yalnız sayfa sayısı ve sayfa ölçüleri. PDF, DXF'ten basılır ve üretim zamanını çizgi olarak taşır;
       piksel özeti her koşuda değişir. İçerik referansı DXF parmak izidir.

Kullanım:  python3 testler/referans/parmak_izi.py <dosya.dxf|dosya.pdf> [...]
Çıktı: her dosya için "<özet>  <yol>" (özet = sha256, içerikten).
"""
from __future__ import annotations
import hashlib, json, re, sys
from pathlib import Path

YUVARLA = 3  # mm altı gürültüyü kes (DXF birimi cm)
# Motor her çizime üretim zamanını yazar (PORTMAN_INFO katmanı): "Üretim: 2026-09-27 22:11:55 UTC"
ZAMAN = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}( UTC)?")


def _r(x):
    try:
        return round(float(x), YUVARLA)
    except (TypeError, ValueError):
        return str(x)


def _nokta(p):
    return tuple(_r(c) for c in p)


def dxf_ozet(yol: Path) -> str:
    import ezdxf
    doc = ezdxf.readfile(yol)
    satirlar = []
    for alan_adi, alan in [("model", doc.modelspace())] + [(f"kagit:{l.name}", l) for l in doc.layouts if l.name != "Model"]:
        for e in alan:
            t = e.dxftype()
            kayit = [alan_adi, t, e.dxf.get("layer", ""), ]
            if t == "INSERT":
                kayit += [e.dxf.name, _nokta(e.dxf.insert), _r(e.dxf.get("rotation", 0)),
                          _r(e.dxf.get("xscale", 1)), _r(e.dxf.get("yscale", 1))]
                kayit += sorted((a.dxf.tag, a.dxf.text) for a in e.attribs)
            elif t == "LINE":
                kayit += sorted([_nokta(e.dxf.start), _nokta(e.dxf.end)])
            elif t in ("LWPOLYLINE",):
                kayit += [tuple(_nokta(p[:2]) for p in e.get_points("xy")), bool(e.closed)]
            elif t in ("CIRCLE", "ARC"):
                kayit += [_nokta(e.dxf.center), _r(e.dxf.radius), _r(e.dxf.get("start_angle", 0)), _r(e.dxf.get("end_angle", 0))]
            elif t in ("TEXT", "MTEXT"):
                metin = e.dxf.text if t == "TEXT" else e.text
                boy = e.dxf.get("height", 0) if t == "TEXT" else e.dxf.get("char_height", 0)
                kayit += [ZAMAN.sub("<zaman>", metin), _nokta(e.dxf.insert), _r(boy)]
            elif t == "HATCH":
                kayit += [e.dxf.pattern_name, len(e.paths)]
            elif t == "DIMENSION":
                kayit += [_nokta(e.dxf.get("defpoint", (0, 0, 0))), e.dxf.get("text", "")]
            else:
                try:
                    kayit += [str(sorted((k, str(v)) for k, v in e.dxfattribs().items() if k not in ("handle", "owner")))]
                except Exception:
                    pass
            satirlar.append(json.dumps(kayit, ensure_ascii=False, default=str))
    # blok tanımları (pano, doğrama blokları) içerikleriyle
    for blok in doc.blocks:
        if blok.name.startswith("*"):
            continue
        icerik = sorted(json.dumps([e.dxftype(), e.dxf.get("layer", "")], ensure_ascii=False) for e in blok)
        satirlar.append(json.dumps(["blok", blok.name, icerik], ensure_ascii=False))
    satirlar.sort()
    return hashlib.sha256("\n".join(satirlar).encode("utf-8")).hexdigest()


def pdf_ozet(yol: Path) -> str:
    import fitz
    with fitz.open(yol) as d:
        olculer = [(round(s.rect.width / 72 * 25.4), round(s.rect.height / 72 * 25.4)) for s in d]
    return hashlib.sha256(json.dumps(olculer).encode()).hexdigest()


def ozet(yol: Path) -> str:
    s = yol.suffix.lower()
    if s == ".dxf":
        return dxf_ozet(yol)
    if s == ".pdf":
        return pdf_ozet(yol)
    raise SystemExit(f"desteklenmeyen dosya: {yol}")


if __name__ == "__main__":
    for a in sys.argv[1:]:
        print(f"{ozet(Path(a))}  {a}")
