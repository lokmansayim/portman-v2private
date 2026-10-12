"""İçerik parmak izi: DXF ve PDF çıktılarının dosya özeti her koşuda değişir, içeriği değişmemelidir.

Motor'un DXF'i her koşuda farklı bayt üretir: oluşturma ve güncelleme zamanı ($TDCREATE, $TDUPDATE), rastgele
kimlikler ($FINGERPRINTGUID, $VERSIONGUID), ezdxf'in üst veri zamanları ve OBJECTS bölümündeki nesne sırası
(Python karma tohumuna bağlı; PYTHONHASHSEED=0 ile sabitlenir). Motor ayrıca her çizime üretim zamanını yazar
(PORTMAN_INFO katmanı: "Üretim: 2026-09-27 22:11:55 UTC"). Bu betik bunları dışarıda bırakıp içerikten özet çıkarır:

  DXF: model alanı, kâğıt alanları ve blok tanımlarındaki her varlık. Varlığın tüm DXF öznitelikleri (tutamaç ve
       sahip hariç) yuvarlanarak yazılır; ayrıca türüne göre köşe noktaları ve eğimler (LWPOLYLINE, POLYLINE),
       metin içeriği (MTEXT), tarama sınırları (HATCH), blok eki öznitelikleri (INSERT) eklenir. Metinlerdeki
       tarih-saat "<zaman>" ile değiştirilir. Satırlar sıralanır; varlık sırası özeti değiştirmez.
  PDF: sayfa sayısı ve ölçüleri + her sayfadaki bütün çizimler (yazılar da çizgi olarak basılır). Üretim zamanı da
       çizim olduğundan özet, zamanı sabitlenmiş koşularda karşılaştırılır (dogrula.py, sabit_zaman/sitecustomize.py).

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


def _pdf_ogesi(n):
    """PyMuPDF yol parçası ögesi (Point, Rect, Quad ya da sayı) → yuvarlanmış liste."""
    if hasattr(n, "x0"):
        return [round(n.x0, 2), round(n.y0, 2), round(n.x1, 2), round(n.y1, 2)]
    if hasattr(n, "ul"):
        return [[round(q.x, 2), round(q.y, 2)] for q in (n.ul, n.ur, n.ll, n.lr)]
    if hasattr(n, "x"):
        return [round(n.x, 2), round(n.y, 2)]
    if isinstance(n, (int, float)):
        return round(n, 2)
    return str(n)


def _cizim(x) -> str:
    """PDF'teki bir çizim (yol): sınır kutusu, renkler, kalınlık ve her parçanın türüyle noktaları (0,01 pt)."""
    parcalar = [[it[0]] + [_pdf_ogesi(n) for n in it[1:]] for it in x.get("items") or []]
    return json.dumps([_pdf_ogesi(x.get("rect")), _d(list(x.get("color") or [])), _d(list(x.get("fill") or [])),
                       _d(x.get("width")), x.get("closePath"), parcalar], default=str)


def pdf_ozet(yol: Path) -> str:
    """Sayfa sayısı ve ölçüleri + her sayfadaki bütün çizimler (Motor PDF'inde yazılar da çizgi olarak basılır; metin
    katmanı yoktur). Eksik plan, yanlış revizyon yazısı ya da kaymış bir çizgi özeti değiştirir. Üretim zamanı da çizim
    olduğundan karşılaştırma zamanı sabitlenmiş koşularda anlamlıdır (dogrula.py bunu yapar; sabit_zaman/)."""
    import fitz
    sayfalar = []
    with fitz.open(yol) as d:
        for s in d:
            cizimler = sorted(_cizim(x) for x in s.get_drawings())
            sayfalar.append([round(s.rect.width / 72 * 25.4), round(s.rect.height / 72 * 25.4), len(cizimler),
                             hashlib.sha256("\n".join(cizimler).encode("utf-8")).hexdigest()])
    return hashlib.sha256(json.dumps(sayfalar).encode()).hexdigest()


def ozet(yol: Path) -> str:
    s = yol.suffix.lower()
    if s == ".dxf":
        return dxf_ozet(yol)
    if s == ".pdf":
        return pdf_ozet(yol)
    raise SystemExit(f"desteklenmeyen dosya: {yol}")


def genel_pdf_ozet(yol: Path) -> str:
    """Genel motorun şablon paftası PDF'i: sayfa ölçüleri, bütün çizimler (pdf_ozet gibi) ve metin (sözcük + yeri, 0,1 pt). Bayt özeti değil:
    matplotlib gömülü yazı tiplerini dosya adına göre sıralı yazar ve bu sıra depo yoluna bağlıdır (kod incelemesi, 12.10.2026); içerik ise yol
    bağımsızdır. Yazılar Type 3 yazı tipiyle gömülür, PyMuPDF sözcükleri okur; bir etiket ya da değer değişince iz değişir."""
    import fitz
    sayfalar = []
    with fitz.open(yol) as d:
        for s in d:
            cizimler = sorted(_cizim(x) for x in s.get_drawings())
            sozcukler = sorted([round(w[0], 1), round(w[1], 1), round(w[2], 1), round(w[3], 1), w[4]] for w in s.get_text("words"))
            sayfalar.append([round(s.rect.width, 1), round(s.rect.height, 1), len(cizimler), hashlib.sha256("\n".join(cizimler).encode()).hexdigest(), sozcukler])
    return hashlib.sha256(json.dumps(sayfalar, ensure_ascii=False).encode("utf-8")).hexdigest()


def genel_ozet(yol: Path) -> str:
    """Genel motor çıktılarının izi (İE-08, `cikti/denetim/genel*/`): PNG bayt bayt (sha256; matplotlib Agg deterministik), PDF içerikçe
    (`genel_pdf_ozet`), JSON kanonik, IFC içerikçe (`motor/genel/iz.py`: başlık zamanı, GlobalId, kayıt numarası ve küme sırası maskeli)."""
    if yol.suffix.lower() == ".pdf":
        return genel_pdf_ozet(yol)
    kok = Path(__file__).resolve().parents[2]          # depo kökü (motor/genel/iz.py için)
    if str(kok) not in sys.path:
        sys.path.insert(0, str(kok))
    from motor.genel import iz
    return iz.dosya_izi(yol)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        print(f"{ozet(Path(a))}  {a}")
