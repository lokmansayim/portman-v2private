"""İE-15 K6 · Montaj rehberinde evin altına serilen ön onay sayfası (`araclar/paket/rehber/kagit.py`).

Lokman (5 Kasım 2026 00:53) evin altına kat planı serilmiş TK-01 rehberini gönderdi: "biz dün en son bunda kalmıştık … altta diğer sohbette
oluşturduğumuz kat planı var"; 00:55: "bu kat planını montaj 'kampanyalı binanın montaj rehberi' başlığına vermen lazım". Sayfa Motor'un ön
onay PDF'idir (`motor/dxf_out.uret`), yeri manifestin `a4_sayfa_cm`'si (`dxf_out.a4_cercevesi`).

- TK-01 r07'de sayfanın çerçevesi Lokman'ın gönderdiği sayfadakiyle aynı (x −495,515 … 1249,017; y −787,038 … 1680,229 cm).
- TK-04 r05'te çerçeve PDF'in kendisiyle tutar: evin dış köşeleri sayfada duvar çizgisinin köşesine düşer.
- Sayfa rehberin `KAGIT`'ında; sayfasız rehberde `null` (62 m² hedef örneği değişmez, `test_rehber.py`).
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
VERI = KOK / "testler" / "motor" / "veri"
PT = 72 / 25.4


def _uret(ad: str, klasor: Path) -> tuple[dict, Path]:
    from motor import dxf_out
    m = dxf_out.uret(copy.deepcopy(json.loads((VERI / f"{ad}.json").read_text(encoding="utf-8"))), klasor)
    return m, klasor / m["pdf"]


@pytest.fixture(scope="module")
def tk04(tmp_path_factory):
    return _uret("TK04_r05", tmp_path_factory.mktemp("tk04_kagit"))


def test_tk01_lokmanin_sayfasiyla_ayni(tmp_path):
    m, _ = _uret("TK01_r07", tmp_path)
    a = m["a4_sayfa_cm"]
    assert a["x"] == [-495.515, 1249.017] and a["y"] == [-787.038, 1680.229]
    assert (a["x"][1] - a["x"][0]) * a["olcek_mm_cm"] == pytest.approx(210, abs=1e-3)
    assert (a["y"][1] - a["y"][0]) * a["olcek_mm_cm"] == pytest.approx(297, abs=1e-3)


def test_tk04_kat_plani_evin_altinda(tk04):
    """Plandaki duvar, veranda kirişi ve dikme bloklarının köşeleri (DXF, cm) çerçeveyle sayfaya taşınınca PDF'teki çizgilerin köşesine düşer:
    çoğu 1 cm'den yakın (kâğıtta 0,12 mm; 300 dpi'de bir pikselin altında). Çerçeve 3 cm kaysa köşelerin yalnız yedide biri tutar."""
    import ezdxf
    import pymupdf
    from ezdxf import bbox
    m, pdf = tk04
    a = m["a4_sayfa_cm"]
    k = a["olcek_mm_cm"]
    with pymupdf.open(pdf) as d:
        P = []
        for yol in d[0].get_drawings():
            for it in yol["items"]:
                ps = ([it[1].tl, it[1].tr, it[1].bl, it[1].br] if it[0] == "re" else [it[1].ul, it[1].ur, it[1].ll, it[1].lr] if it[0] == "qu"
                      else [p for p in it[1:] if isinstance(p, pymupdf.Point)])
                P += [(p.x / PT / k + a["x"][0], a["y"][1] - p.y / PT / k) for p in ps]     # sayfa (pt) → kat planı çerçevesi (cm)
    kose = []
    for e in ezdxf.readfile(pdf.with_suffix(".dxf")).modelspace().query("INSERT"):
        b = bbox.extents([e])
        if e.dxf.layer.startswith(("DIS_DUVAR", "IC_DUVAR", "VERANDA")) and b.extmin.x > -60 and b.extmax.x < 950 and b.extmax.y < 960:
            kose += [(b.extmin.x, b.extmin.y), (b.extmax.x, b.extmax.y), (b.extmin.x, b.extmax.y), (b.extmax.x, b.extmin.y)]
    uzak = sorted(min(abs(px - x) + abs(py - y) for px, py in P) for x, y in kose)
    assert len(kose) > 150
    assert sum(u < 1 for u in uzak) >= 0.8 * len(kose) and uzak[len(uzak) // 2] < 0.6


def test_kagit_rehberde(tk04):
    import pymupdf
    from araclar.paket.rehber import kagit, sayfa
    m, pdf = tk04
    kg = kagit.kur(pdf, m["a4_sayfa_cm"])
    assert kg["x"] == m["a4_sayfa_cm"]["x"] and kg["y"] == m["a4_sayfa_cm"]["y"]
    assert kg["src"].startswith("data:image/jpeg;base64,")
    import base64
    pix = pymupdf.Pixmap(base64.b64decode(kg["src"].split(",", 1)[1]))
    assert (pix.width, pix.height) == (2481, 3508)
    d = json.loads((KOK / "testler" / "paket" / "rehber62" / "veri.json").read_text(encoding="utf-8"))
    assert 'const KAGIT = {"src":"data:image/jpeg;base64,' in sayfa.metin(d, kagit=kg)
    assert "const KAGIT = null;" in sayfa.metin(d)
    assert kagit.kur(None, m["a4_sayfa_cm"]) is None and kagit.kur(pdf, None) is None
