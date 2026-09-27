"""İçerik parmak izi: DXF ve PDF çıktılarının dosya özeti her koşuda değişir, içeriği değişmemelidir.

Motor'un DXF'i her koşuda farklı bayt üretir: oluşturma ve güncelleme zamanı ($TDCREATE, $TDUPDATE), rastgele
kimlikler ($FINGERPRINTGUID, $VERSIONGUID), ezdxf'in üst veri zamanları ve OBJECTS bölümündeki nesne sırası
(Python karma tohumuna bağlı; PYTHONHASHSEED=0 ile sabitlenir). Motor ayrıca her çizime üretim zamanını yazar
(PORTMAN_INFO katmanı: "Üretim: 2026-09-27 22:11:55 UTC"). Bu betik bunları dışarıda bırakıp içerikten özet çıkarır:

  DXF: model alanı, kâğıt alanları ve blok tanımlarındaki her varlık. Varlığın tüm DXF öznitelikleri (tutamaç ve
       sahip hariç) yuvarlanarak yazılır; ayrıca türüne göre köşe noktaları ve eğimler (LWPOLYLINE, POLYLINE),
       metin içeriği (MTEXT), tarama sınırları (HATCH), blok eki öznitelikleri (INSERT) eklenir. Metinlerdeki
       tarih-saat "<zaman>" ile değiştirilir. Satırlar sıralanır; varlık sırası özeti değiştirmez.
  PDF: sayfa sayısı ve sayfa ölçüleri. PDF, DXF'ten basılır ve üretim zamanını çizgi olarak taşır; piksel özeti
       her koşuda değişir. İçerik referansı DXF parmak izidir.

Kullanım:  python3 testler/referans/parmak_izi.py <dosya.dxf|dosya.pdf> [...]
Çıktı: her dosya için "<özet>  <yol>" (özet = sha256, içerikten).
"""
from __future__ import annotations
import hashlib, json, re, sys
from pathlib import Path

YUVARLA = 3  # mm altı gürültüyü kes (DXF birimi cm)
ZAMAN = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}( UTC)?")
ATLA = {"handle", "owner"}


def _d(v):
    """Değeri yuvarlanmış, karşılaştırılabilir biçime çevirir."""
    if isinstance(v, float):
        return round(v, YUVARLA)
    if isinstance(v, (int, bool)) or v is None:
        return v
    if isinstance(v, str):
        return ZAMAN.sub("<zaman>", v)
    if isinstance(v, (tuple, list)):
        return [_d(x) for x in v]
    try:  # ezdxf Vec2/Vec3
        return [_d(float(x)) for x in v]
    except TypeError:
        return str(v)


def _varlik(e) -> list:
    t = e.dxftype()
    oz = sorted((k, _d(v)) for k, v in e.dxfattribs().items() if k not in ATLA)
    ek = []
    if t == "LWPOLYLINE":
        ek = [_d(p) for p in e.get_points("xyseb")]
    elif t == "POLYLINE":
        ek = [_d(v.dxf.location) for v in e.vertices]
    elif t == "MTEXT":
        ek = [_d(e.text)]
    elif t == "HATCH":
        for yol in e.paths:
            if hasattr(yol, "vertices"):
                ek.append(["poly", _d([tuple(v) for v in yol.vertices]), bool(getattr(yol, "is_closed", True))])
            else:
                ek.append(["kenar", [[type(k).__name__, _d(getattr(k, "start", None)), _d(getattr(k, "end", None)),
                                      _d(getattr(k, "center", None)), _d(getattr(k, "radius", None))]
                                     for k in getattr(yol, "edges", [])]])
    elif t == "INSERT":
        ek = sorted([a.dxf.tag, _d(a.dxf.text), _d(a.dxf.insert)] for a in e.attribs)
    elif t == "SPLINE":
        ek = [_d(list(e.control_points)), _d(list(e.fit_points))]
    return [t, oz, ek]


def dxf_ozet(yol: Path) -> str:
    import ezdxf
    doc = ezdxf.readfile(yol)
    satirlar = []
    alanlar = [("model", doc.modelspace())] + [(f"kagit:{l.name}", l) for l in doc.layouts if l.name != "Model"]
    for ad, alan in alanlar:
        for e in alan:
            satirlar.append(json.dumps([ad] + _varlik(e), ensure_ascii=False, default=str))
    for blok in doc.blocks:
        if blok.name.lower().startswith(("*model_space", "*paper_space")):
            continue
        for e in blok:
            satirlar.append(json.dumps([f"blok:{blok.name}"] + _varlik(e), ensure_ascii=False, default=str))
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
