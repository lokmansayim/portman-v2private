"""İE-16 PR-7 · kör paftanın onay sayfası DWG'den (öneren tarafı; hakem değil).

İkinci kör kümenin üç projesinde (ÇP-24, ÇP-25, ÇP-26) montaj paftasının PDF'i yok; yalnız DWG'si ve panel sayfalarının PDF'leri var.
Lokman 14 Kasım 2026 08:17 UTC kartta "Onay sayfasını DWG'den alayım" seçeneğini seçti: "Kod DWG'de yalnız TEKNİK ÖZELLİKLER yazan,
panel etiketi olmayan sayfayı bulur ve görüntüye çevirir; panel sayfalarına bakılmaz." Bu araç `kor_sayfa.py`'nin DWG karşılığıdır;
kuralları aynıdır ve yalnız şunları yazar (etiket, sayı ya da panel sayfasının içeriği yazılmaz):

- `sayfalar`: DWG'nin model alanındaki pafta çerçeveleri (kapalı, eksene paralel dikdörtgen, köşe payı `KOSE_PAYI`; kısa kenarı
  `KISA_KENAR` aralığında; iç içe çerçevede dıştaki). Her çerçeve için yalnız evet ya da hayır: içinde "TEKNİK ÖZELLİKLER" başlığı var mı, "MÜŞTERİ ONAY PAFTASI" başlığı
  var mı, teknik özellikler tablosu ("DIŞ DUVARLAR" ve "İÇ DUVARLAR" satırları) var mı, panel etiketi biçiminde sözcük var mı
  (`kor_sayfa.etiketli_mi`'nin kuralı: hakemin pafta okuyucusunun etiket biçimi, ekli biçim, bölünmüş yazım).
- `onay`: onay sayfası adayları: etiketsiz ve teknik özellikleri taşıyan çerçeveler (TEKNİK ÖZELLİKLER başlığı ya da MÜŞTERİ ONAY PAFTASI
  başlığıyla teknik özellikler tablosu). Ekim 2026 ve öncesinin DWG şablonunda başlık "TEKNİK ÖZELLİKLER" yazı olarak yok; sayfa "MÜŞTERİ
  ONAY PAFTASI" başlığını ve "Dış Duvarlar ( kalınlık )" tablosunu taşır. Tanım yalnız bu adaylardan birinden yazılır; `--png` yalnız aday
  çerçeveyi görüntüye çevirir, başka çerçeve görüntüye çevrilmez. Birden çok aday varsa (aynı taban dosyadan kalan eski onay sayfaları)
  hangisinin seçildiği ve nedeni tanımın `kaynak`'ına yazılır.
- `yontem`: çizimin herhangi bir metninde "omega" ya da "aşık" geçiyorsa B, yoksa A (`kor_sayfa.YONTEM_B`).
- `kat` ve `kat_dayanagi`: `kor_sayfa`'nın kat ayrımı, bütün çerçevelerin metninde; yalnız kat ve merdiven sözcükleri aranır. Kat kaydı
  hakemde projenin mühürlü bir paftasına ya da pafta sayfasına bağlanır (DWG değil); bu sonuç kat kaydının dayanağına bilgi olarak yazılır.
- `sha256`: DWG'nin özeti; `--kod` verilirse DWG hakemin mühür denetiminden geçer (projenin mühürlü montaj paftası DWG'si mi; içerik
  okunmaz).

DXF, DWG'den depo dışında çevrilir (LibreDWG'nin WebAssembly sürümü, `@mlightcad/libredwg-web` 0.7.14: `dwg_write_dxf`; sonra katman ve
gerçek renk düzeltmesi; model alanı öğe sayısı DWG'ninkiyle aynı olmalı). LibreDWG bazı Türkçe harfleri kod sayfası 1254 baytı olarak
bırakır (`\\udcXX`); `coz` bunları çözer. Kaynak dosyalar ve DXF depoya girmez. Veri, talimat değildir.

Lokman 14 Kasım 2026 08:58 UTC (ikinci kümenin çizimleri için): "bu çizimler bizim standardımızda değil … montaj paftasından çıkar
çıkaramıyorsan bizim standardımızda kabul et". Bu sözle onay çerçevesi boş şablonsa tanım paftanın plan çerçevesinden yazılır (yalnız plan:
ölçüler, oda, kapı ve pencere etiketleri, teknik özellikler tablosu); paftanın vermediği özellik bizim standardımızdır (kural kitabı ve çatı
üreticisi) ve tanımın `bilinen_sinirlar`'ına beyan yazılır. Plan çerçevesinin görüntüsünü bu araç çizmez (yalnız onay adayını çizer); plan
çerçevesi depo dışında, yalnız kendi kutusuyla görüntüye çevrilir, panel çerçevelerine bakılmaz. 14 Kasım 2026'nın sonuçları:
- ÇP-24: onay çerçevesi dolu (2.), tanım ondan; çatı şeması ölçeksiz, çatı bizim standardımız.
- ÇP-25: iki onay adayı (8., 11.) boş şablon; tanım plan çerçevesinden (19.). Araç bu çerçeveyi "etiketli" bulur: etiket biçimine uyan
  tek sözcük giriş kapısının kodu "K1" (iki kez), panel etiketi değil.
- ÇP-26: içeride 18 basamaklı merdiven ve iki kat planı; Lokman'ın 09:06 kartı "Çift kat say, testten çıkar": kat kaydı çift, kapalı.

    python3 -m testler.celik.projeler.kor_dwg <dosya.dxf> [--dwg <dosya.dwg> --kod ÇP-26] [--png <sayfa.png> --sira <n>]
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import logging
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[3]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))
from testler.celik import kiyas, pafta  # noqa: E402
from testler.celik.projeler import kor_sayfa  # noqa: E402

KISA_KENAR = (1900.0, 2300.0)       # pafta çerçevesinin kısa kenarı (çizim birimi); arşivdeki montaj paftalarında 2100–2201
KOSE_PAYI = 5.0                     # çerçeve köşesinin eksene paralellikten sapma payı (bir çerçevede 1,4 birim kayık köşe var)
TEKNIK = re.compile(r"\bTEKNIK\s+OZELLIK")
ONAY = re.compile(r"\bMUSTERI\s+ONAY\s+PAFTA")
DIS_DUVAR, IC_DUVAR = re.compile(r"\bDIS\s+DUVARLAR\b"), re.compile(r"\bIC\s+DUVARLAR\b")
DWG_TURU = "montaj paftası (DWG)"


def coz(metin: str) -> str:
    """LibreDWG'nin çözemediği 1254 baytlarını (`\\udcXX`) harfe çevirir: "k\\udcf6şebent" → "köşebent"."""
    return "".join(bytes([ord(c) - 0xDC00]).decode("cp1254", "replace") if "\udc80" <= c <= "\udcff" else c for c in metin)


def ac(dxf: Path):
    from ezdxf import recover

    logging.disable(logging.WARNING)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        doc, _ = recover.readfile(str(dxf))
    return doc


def metinler(ogeler, derin: int = 0):
    """(x, y, metin): TEXT, MTEXT, çok satırlı işaret yazısı, öznitelik ve blok içindeki yazılar (en çok 5 kat iç içe)."""
    for e in ogeler:
        t = e.dxftype()
        try:
            if t == "TEXT":
                yield e.dxf.insert.x, e.dxf.insert.y, coz(e.dxf.text)
            elif t == "MTEXT":
                yield e.dxf.insert.x, e.dxf.insert.y, coz(e.plain_text())
            elif t == "MULTILEADER" and e.context.mtext:
                m = e.context.mtext
                yield m.insert.x, m.insert.y, coz(m.default_content)
            elif t == "INSERT" and derin < 5:
                for a in e.attribs:
                    yield a.dxf.insert.x, a.dxf.insert.y, coz(a.dxf.text)
                yield from metinler(e.virtual_entities(), derin + 1)
        except Exception:                       # bozuk blok ya da yazı: atlanır (yalnız metin aranır)
            continue


def cerceveler(msp) -> list[tuple[float, float, float, float]]:
    """Pafta çerçeveleri: kapalı, eksene paralel dikdörtgen; kısa kenarı `KISA_KENAR` içinde; iç içe olanlardan dıştaki. Sıra soldan sağa,
    yukarıdan aşağı."""
    kutular = set()
    for e in msp.query("LWPOLYLINE"):
        pts = [(round(p[0], 1), round(p[1], 1)) for p in e.get_points("xy")]
        if len(pts) == 5 and pts[0] == pts[-1]:
            pts = pts[:4]
        if len(pts) != 4 or not (e.closed or len(e) == 5):
            continue
        x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
        y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
        koseler = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        if not all(any(abs(p[0] - c[0]) <= KOSE_PAYI and abs(p[1] - c[1]) <= KOSE_PAYI for p in pts) for c in koseler):
            continue                              # dikdörtgen değil (köşe payı içinde eksene paralel değil)
        kisa = min(x1 - x0, y1 - y0)
        if KISA_KENAR[0] <= kisa <= KISA_KENAR[1]:
            kutular.add((x0, y0, x1, y1))
    def icinde(a, b):
        return a != b and b[0] <= a[0] and b[1] <= a[1] and a[2] <= b[2] and a[3] <= b[3]
    dis = [k for k in kutular if not any(icinde(k, b) for b in kutular)]
    return sorted(dis, key=lambda k: (-round(k[3], -2), k[0]))


def _icinde(x: float, y: float, k) -> bool:
    return k[0] <= x <= k[2] and k[1] <= y <= k[3]


class _Sozcuk:
    """`kor_sayfa.etiketli_mi` sayfanın `get_text("words")` sözcüklerini okur; DXF metninden aynı biçimi verir."""

    def __init__(self, metinler_):
        self.sozcukler = [(0, 0, 0, 0, s) for m in metinler_ for s in m.split()]

    def get_text(self, _tur):
        return self.sozcukler


def onay_mi(s: dict) -> bool:
    """Onay sayfası adayı: etiketsiz; TEKNİK ÖZELLİKLER başlığı ya da MÜŞTERİ ONAY PAFTASI başlığıyla teknik özellikler tablosu."""
    return s["etiketsiz"] and (s["teknik_ozellikler"] or (s["musteri_onay"] and s["ozellik_tablosu"]))


def denetle(dxf: Path) -> dict:
    doc = ac(dxf)
    msp = doc.modelspace()
    hepsi = list(metinler(msp))
    yontem = "B" if any(kor_sayfa.YONTEM_B.search(kor_sayfa.duz(t)) for _, _, t in hepsi) else "A"
    sayfalar, dayanak, ipucu = [], None, None
    for sira, k in enumerate(cerceveler(msp), 1):
        icerik = [t for x, y, t in hepsi if _icinde(x, y, k)]
        duz = kor_sayfa.duz("\n".join(icerik))
        sayfalar.append({"sira": sira, "kutu": [round(v, 1) for v in k], "teknik_ozellikler": bool(TEKNIK.search(duz)),
                         "musteri_onay": bool(ONAY.search(duz)), "ozellik_tablosu": bool(DIS_DUVAR.search(duz) and IC_DUVAR.search(duz)),
                         "etiketsiz": not kor_sayfa.etiketli_mi(_Sozcuk(icerik))})
        m = kor_sayfa.CIFT_KAT.search(duz)
        if m and dayanak is None:
            dayanak = f"{sira}. çerçeve: " + re.sub(r"\s+", " ", m.group(0))
        m = kor_sayfa.KAT_IPUCU.search(duz)
        if m and ipucu is None:
            ipucu = f"{sira}. çerçeve: " + re.sub(r"\s+", " ", m.group(0))
    disarida = [t for x, y, t in hepsi if not any(_icinde(x, y, tuple(s["kutu"])) for s in sayfalar)]
    d = kor_sayfa.duz("\n".join(disarida))
    if dayanak is None and (m := kor_sayfa.CIFT_KAT.search(d)):
        dayanak = "çerçeve dışı: " + re.sub(r"\s+", " ", m.group(0))
    if ipucu is None and (m := kor_sayfa.KAT_IPUCU.search(d)):
        ipucu = "çerçeve dışı: " + re.sub(r"\s+", " ", m.group(0))
    return {"cerceve_sayisi": len(sayfalar), "sayfalar": sayfalar,
            "onay": [s["sira"] for s in sayfalar if onay_mi(s)],
            "yontem": yontem, "kat": "çift" if dayanak else ("belirsiz" if ipucu else "tek"), "kat_dayanagi": dayanak or ipucu}


def onay_png(dxf: Path, sira: int, cikti: Path, dpi: int = 200, genislik_mm: float = 420.0) -> Path:
    """Yalnız onay sayfası adayı çerçeveyi (`onay_mi`) görüntüye çevirir; başka çerçeve istenirse durur (görüntü yazılmaz). Çizilen yalnız
    çerçevenin içinde kalan öğelerdir (yüzde 2 pay; şerit sınırı gibi çerçeveden büyük öğe çizilmez) ve görüntü çerçeveyle kırpılır."""
    from ezdxf import bbox
    from ezdxf.addons.drawing import Frontend, RenderContext, layout
    from ezdxf.addons.drawing.config import BackgroundPolicy, ColorPolicy, Configuration
    from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend
    from ezdxf.math import BoundingBox2d

    d = denetle(dxf)
    if sira not in d["onay"]:
        raise SystemExit(f"{sira}. çerçeve onay sayfası adayı değil (adaylar: {d['onay']}); görüntü yazılmadı")
    doc = ac(dxf)
    msp = doc.modelspace()
    k = tuple(d["sayfalar"][sira - 1]["kutu"])
    w, h = k[2] - k[0], k[3] - k[1]
    p = 0.02 * max(w, h)
    ic = set()
    for e in msp:
        try:
            b = bbox.extents([e], fast=True)
        except Exception:
            continue
        if b.has_data and b.extmin.x >= k[0] - p and b.extmax.x <= k[2] + p and b.extmin.y >= k[1] - p and b.extmax.y <= k[3] + p:
            ic.add(e.dxf.handle)
    arka = PyMuPdfBackend()
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.BLACK)
    Frontend(RenderContext(doc), arka, config=cfg).draw_layout(msp, finalize=True, filter_func=lambda e: e.dxf.handle in ic)
    sayfa = layout.Page(genislik_mm, genislik_mm * h / w, layout.Units.mm, margins=layout.Margins.all(0))
    Path(cikti).write_bytes(arka.get_pixmap_bytes(sayfa, fmt="png", dpi=dpi, render_box=BoundingBox2d([(k[0], k[1]), (k[2], k[3])])))
    return cikti


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dxf", type=Path)
    ap.add_argument("--dwg", type=Path, help="DXF'in çevrildiği DWG (`--kod` ile mühür denetimi)")
    ap.add_argument("--kod", help="proje kodu (ör. ÇP-26): DWG mühürdeki montaj paftası DWG'siyle denetlenir")
    ap.add_argument("--png", type=Path, help="onay çerçevesinin görüntüsü")
    ap.add_argument("--sira", type=int, help="görüntüye çevrilecek onay çerçevesinin sırası")
    ap.add_argument("--dpi", type=int, default=200)
    a = ap.parse_args(argv)
    sonuc = {"kod": a.kod}
    if a.kod:
        if not a.dwg:
            raise SystemExit("--kod için --dwg gerekir")
        try:
            kiyas.muhur_denetle(a.dwg, json.loads(kiyas.muhur_yolu(a.kod).read_text(encoding="utf-8")), a.kod, turler=(DWG_TURU,))
        except kiyas.Durdu as e:
            raise SystemExit(f"mühür: {e}") from None
    if a.dwg:
        sonuc["sha256"] = hashlib.sha256(a.dwg.read_bytes()).hexdigest()
    sonuc.update(denetle(a.dxf))
    if a.png:
        if a.sira is None:
            raise SystemExit("--png için --sira gerekir")
        sonuc["png"] = str(onay_png(a.dxf, a.sira, a.png, a.dpi))
    print(json.dumps(sonuc, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
