"""İE-32 · M-13 · Montaj rehberinin altında ön onay sayfası: kilit testi (hedef örnek `rehber_kagit/TK01_r07.json`).

Lokman, 4 Kasım 2026 00:36: "rehber aynı şekilde kalsın sadece altına PDF gelsin"; 00:50: "aynen şu anki halini repoda mühürleyelim".
Özellik `main`'e İE-15 K6 ile girdi (D-53 madde 6, PR #124: `motor/dxf_out.a4_cercevesi`, `araclar/paket/rehber/kagit.py`, `sahne.js` ›
`KAGIT`); bu test onu TK-01 r07 hedef örneğiyle sabitler, mühür M-13'ün kilididir (`KARARLAR/muhurlu.json`).

- `test_tk01_r07_cercevesi_hedefle_ayni`: Motor'un ön onay sayfasının kat planı çerçevesindeki yeri hedefteki gibi (Lokman'ın gördüğü
  sayfanınki); çerçeve tam bir A4 (210 × 297 mm).
- `test_tk01_r07_kat_plani_evin_altinda`: plandaki duvar, veranda ve dikme bloklarının köşeleri çerçeveyle sayfaya taşınınca PDF'teki
  çizgilerin köşesine düşer (kâğıtta 0,12 mm'den yakın).
- `test_tk01_r07_sayfa_rehberde`: rehberin altındaki sayfa bayiye giden ön onay PDF'inin kendisi (paketin çizim adımı, 300 dpi, A4
  pikselleri) ve hedefteki yerde; rehber sayfasında `KAGIT` olarak durur.
- `test_rehber_aynen_kalir`: sayfa rehbere yalnız zemini ekler: adımlar, parçalar, kartlar, yazılar, kamera sayfasız rehberinkiyle aynı,
  sayfa hatasız açılır (iz: Node, Playwright, three.js 0.160.0; yoksa atlanır, CI'da "kalan" işinde koşar).
"""
from __future__ import annotations

import base64
import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from araclar.paket.rehber import iz  # noqa: E402

HEDEF = json.loads((Path(__file__).with_name("rehber_kagit") / "TK01_r07.json").read_text(encoding="utf-8"))
PT = 72 / 25.4


def _ie() -> dict:
    return json.loads((KOK / HEDEF["is_emri"]).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def motor_cikti(tmp_path_factory):
    from motor import dxf_out
    k = tmp_path_factory.mktemp("m13_motor")
    m = dxf_out.uret(_ie(), k)
    return m, k / m["pdf"]


def test_tk01_r07_cercevesi_hedefle_ayni(motor_cikti):
    m, _ = motor_cikti
    a = m["a4_sayfa_cm"]
    assert a == HEDEF["a4_sayfa_cm"]
    sw, sh = HEDEF["sayfa_mm"]
    assert (a["x"][1] - a["x"][0]) * a["olcek_mm_cm"] == pytest.approx(sw, abs=1e-3)
    assert (a["y"][1] - a["y"][0]) * a["olcek_mm_cm"] == pytest.approx(sh, abs=1e-3)


def test_tk01_r07_kat_plani_evin_altinda(motor_cikti):
    """Köşelerin en az %80'i PDF'teki bir çizgi köşesine 1 cm'den yakın, ortanca 0,6 cm'nin altında (kâğıtta 0,07 mm). Çerçeve birkaç cm
    kaysa köşelerin çoğu tutmaz."""
    import ezdxf
    import pymupdf
    from ezdxf import bbox
    m, pdf = motor_cikti
    a = m["a4_sayfa_cm"]
    k = a["olcek_mm_cm"]
    with pymupdf.open(pdf) as d:
        assert len(d) == 1
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
    assert len(kose) > 200
    assert sum(u < 1 for u in uzak) >= 0.8 * len(kose) and uzak[len(uzak) // 2] < 0.6


def test_tk01_r07_sayfa_rehberde(motor_cikti, tmp_path):
    import pymupdf
    from araclar.paket import uret as U
    from araclar.paket.rehber import kagit, sayfa
    cz = U.cizim(copy.deepcopy(_ie()), tmp_path)                 # paketin çizim adımı: ön onay PDF'i ve sayfanın yeri
    assert cz["a4"] == HEDEF["a4_sayfa_cm"]
    _, pdf = motor_cikti
    assert Path(cz["pdf"]).read_bytes() == pdf.read_bytes()      # rehberin altındaki sayfa bayiye giden PDF'in kendisi
    kg = kagit.kur(cz["pdf"], cz["a4"])
    assert kagit.DPI == HEDEF["dpi"]
    assert (kg["x"], kg["y"]) == (HEDEF["a4_sayfa_cm"]["x"], HEDEF["a4_sayfa_cm"]["y"])
    pix = pymupdf.Pixmap(base64.b64decode(kg["src"].split(",", 1)[1]))
    assert [pix.width, pix.height] == HEDEF["piksel"]
    d = json.loads((KOK / "testler" / "paket" / "rehber62" / "veri.json").read_text(encoding="utf-8"))
    assert 'const KAGIT = {"src":"data:image/jpeg;base64,' in sayfa.metin(d, kagit=kg)
    assert "const KAGIT = null;" in sayfa.metin(d)


def _jpeg_1x1() -> str:
    import io
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (1, 1), (255, 255, 255)).save(b, "JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode("ascii")


@pytest.mark.skipif(iz.hazir() is not None, reason=f"rehber izi: {iz.hazir()}")
def test_rehber_aynen_kalir(tmp_path):
    from araclar.paket.rehber import sayfa
    d = json.loads((KOK / "testler" / "paket" / "rehber62" / "veri.json").read_text(encoding="utf-8"))
    kg = {"src": _jpeg_1x1(), "x": HEDEF["a4_sayfa_cm"]["x"], "y": HEDEF["a4_sayfa_cm"]["y"]}
    a = iz.al(sayfa.yaz(d, tmp_path / "sayfasiz.html"), tmp_path / "a.json")
    b = iz.al(sayfa.yaz(d, tmp_path / "sayfali.html", kagit=kg), tmp_path / "b.json")
    assert b["hatalar"] == [] and a["hatalar"] == []
    for k in ("N", "liste", "ilerleme", "parca", "parts", "adimlar"):
        assert b[k] == a[k], k
