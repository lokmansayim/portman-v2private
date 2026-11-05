"""İE-15 K6 · Rehberin altındaki ön onay sayfası.

Lokman (5 Kasım 2026 00:53), evin altına kat planı serilmiş TK-01 rehberini göndererek: "biz dün en son bunda kalmıştık … altta diğer
sohbette oluşturduğumuz kat planı var"; 00:55: "bu kat planını montaj 'kampanyalı binanın montaj rehberi' başlığına vermen lazım".

Sayfa Motor'un ön onay PDF'idir (`motor/dxf_out.uret`; bayiye giden sayfanın kendisi, D-28 madde 1). Burada yalnız JPEG'e çevrilir; sayfanın
kat planı çerçevesindeki yeri manifestin `a4_sayfa_cm`'sinden (`dxf_out.a4_cercevesi`). Sahne (`sahne.js` › `KAGIT`) sayfayı temel plağın
yerine gerçek ölçekte serer: kat planı evin tam altına oturur. TK-01 r07'de çerçeve, Lokman'ın gönderdiği sayfanınkiyle aynıdır
(`testler/paket/test_k6_rehber.py`).
"""
from __future__ import annotations

import base64
from pathlib import Path

DPI = 300               # Lokman'ın gönderdiği TK-01 sayfasındaki görüntü gibi (2481 × 3508)
JPEG_KALITE = 85


def kur(pdf: Path, cerceve: dict | None) -> dict | None:
    """Sahnenin `KAGIT`'ı: {"src": JPEG data URI, "x": [sol, sağ], "y": [ön, arka]} (cm). PDF ya da çerçeve yoksa None (sayfasız rehber)."""
    if not pdf or not cerceve:
        return None
    import pymupdf
    with pymupdf.open(Path(pdf)) as d:
        if len(d) != 1:
            raise ValueError(f"ön onay PDF'i tek sayfa değil ({len(d)})")
        jpg = d[0].get_pixmap(dpi=DPI, alpha=False).tobytes("jpeg", jpg_quality=JPEG_KALITE)
    return {"src": "data:image/jpeg;base64," + base64.b64encode(jpg).decode("ascii"),
            "x": [float(v) for v in cerceve["x"]], "y": [float(v) for v in cerceve["y"]]}
