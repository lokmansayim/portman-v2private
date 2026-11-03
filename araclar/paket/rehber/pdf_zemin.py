"""Montaj rehberinin zemininde ön onay PDF'i (Lokman, 4 Kasım 2026 00:36: "rehber aynı şekilde kalsın sadece altına PDF gelsin"; 00:50:
"aynen şu anki halini repoda mühürleyelim").

Rehber aynen kalır (adımlar, parçalar, kartlar, kamera); sahneye yalnız bayiye giden tek sayfalık A4 ön onay PDF'inin sayfası eklenir.
Sayfa gerçek ölçektedir ve kat planı evin tam altına oturur: duvarlar paftadaki duvar çizgilerinin üstünde durur. Temel plak sahnede
gizlenir (planı örtmesin); GLB'ye yine yazılır (`glb.js`, galeri aynı).

Planın sayfadaki yeri ve ölçeği motorun kendi kararıdır (`motor.dxf_out.a4_bayi_sayfasi`: `a4_yerlesim` ve `_bolge_pdf`'e giden plan
kutusu). Bu modül onu yeniden hesaplamaz; PDF çizilirken okur (`A4PlanOkuyucu`; D-28 madde 1: sayıyı motor üretir, rehber okur).
Dönüşüm (mm; X, Y motor planı, cm; s = `olcek_mm_cm`):

    sayfa_x = plan_x + (X − kutu_x0) · s        sayfa_y (üstten) = plan_y + (kutu_y1 − Y) · s

Sahnede (`sahne.js`) sayfa, motor planı çerçevesindeki dikdörtgeni `kagit_cm` ile yerleşir (X(), Z() rehberin dönüşümü).
"""
from __future__ import annotations

import base64
from pathlib import Path

PDF_DPI = 300                 # sayfanın görseli; 2481 × 3508 piksel (A4)
JPEG_KALITE = 88


class A4PlanOkuyucu:
    """`with A4PlanOkuyucu() as o: dxf_out.uret(...)` → `o.sonuc`: {"sayfa_mm", "plan_mm" [x, y, en, boy], "olcek_mm_cm", "plan_kutu_cm"
    [x0, y0, x1, y1]} ya da None (PDF çizilmediyse ya da plan bölgesi tek anlamlı bulunamadıysa: yanlış yere sayfa konmaz).
    Motorun iki işlevini yalnız `with` süresince sarar ve geri koyar; davranışını değiştirmez (dönen değerler aynen). İş parçacığı güvenli
    değildir: paket üreteci sırayla koşar."""

    def __enter__(self):
        from motor import dxf_out
        self._m = dxf_out
        self._asil = (dxf_out.a4_yerlesim, dxf_out._bolge_pdf)
        self._yer, self._bolgeler = None, []
        asil_yer, asil_bolge = self._asil

        def yer(kutular):
            r = asil_yer(kutular)
            self._yer = r
            return r

        def bolge(doc, handles, kutu, w_mm, h_mm, cfg):
            self._bolgeler.append(([kutu.extmin.x, kutu.extmin.y, kutu.extmax.x, kutu.extmax.y], w_mm, h_mm))
            return asil_bolge(doc, handles, kutu, w_mm, h_mm, cfg)

        dxf_out.a4_yerlesim, dxf_out._bolge_pdf = yer, bolge
        return self

    def __exit__(self, *hata):
        self._m.a4_yerlesim, self._m._bolge_pdf = self._asil
        return False

    @property
    def sonuc(self) -> dict | None:
        if not self._yer or "plan" not in self._yer:
            return None
        x, y, w, h = self._yer["plan"]
        s = self._yer["olcek"]["plan"]
        # plan bölgesinin kutusu: sayfadaki dikdörtgeni aynı olan ve ölçeği planınki olan tek kutu
        aday = [k for k, kw, kh in self._bolgeler
                if abs(kw - w) < 1e-9 and abs(kh - h) < 1e-9 and abs((k[2] - k[0]) * s - w) < 1e-6 and abs((k[3] - k[1]) * s - h) < 1e-6]
        if len(aday) != 1:
            return None
        return {"sayfa_mm": list(self._m.A4_DIKEY_MM), "plan_mm": [x, y, w, h], "olcek_mm_cm": s, "plan_kutu_cm": aday[0]}


def kagit_cm(a4: dict) -> list[float]:
    """Sayfanın dört kenarı motor planı çerçevesinde (cm): [x0, y0, x1, y1] (y0 sayfanın altı, y1 üstü)."""
    sw, sh = a4["sayfa_mm"]
    x, y, _w, _h = a4["plan_mm"]
    s = a4["olcek_mm_cm"]
    kx0, _ky0, _kx1, ky1 = a4["plan_kutu_cm"]
    return [kx0 + (0.0 - x) / s, ky1 - (sh - y) / s, kx0 + (sw - x) / s, ky1 - (0.0 - y) / s]


def veri(pdf: Path, a4: dict, dpi: int = PDF_DPI) -> dict:
    """Rehberin verisine giren `pdf_zemin`: sayfanın görseli (JPEG, data URI), pikselleri ve sayfanın plandaki dikdörtgeni (cm, 3 hane).
    Okunan A4 yerleşiminin ham sayıları sayfaya yazılmaz (uzun ondalıklar numara taramasında numara sanılır; sahne yalnız `kagit_cm`'i
    kullanır). PDF tek sayfa olmalı (ön onay PDF'i, M-02)."""
    import pymupdf
    with pymupdf.open(str(pdf)) as doc:
        if doc.page_count != 1:
            raise ValueError(f"ön onay PDF'i tek sayfa değil ({doc.page_count})")
        pix = doc[0].get_pixmap(dpi=dpi)
        jpg = pix.tobytes("jpg", jpg_quality=JPEG_KALITE)
    return {"resim": "data:image/jpeg;base64," + base64.b64encode(jpg).decode("ascii"), "piksel": [pix.width, pix.height],
            "kagit_cm": [round(v, 3) for v in kagit_cm(a4)]}
