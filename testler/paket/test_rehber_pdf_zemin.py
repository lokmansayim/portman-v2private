"""Montaj rehberinin zemininde ön onay PDF'i (Lokman, 4 Kasım 2026 00:36: "rehber aynı şekilde kalsın sadece altına PDF gelsin"; 00:50:
"aynen şu anki halini repoda mühürleyelim"). Hedef örnek TK-01 r07: `rehber_pdf/TK01_r07.json` (planın PDF'teki yeri, sayfanın plandaki
dikdörtgeni, görselin pikselleri) ve görsel kanıtı `rehber_pdf/TK01_r07_adim09.jpg`.

- `test_a4_plan_motordan_okunur`: paket üretecinin çizim adımı (`uret.cizim`, motorun `dxf_out.uret`'i) PDF'teki kat planının yerini ve
  ölçeğini hedefteki gibi okur; okuyucu motorun işlevlerini geri koyar ve PDF'i değiştirmez.
- `test_kagit_dikdortgeni`: sayfanın motor planı çerçevesindeki dikdörtgeni hedefteki gibi; planın köşeleri sayfada planın yerine düşer.
- `test_pdf_zemin_verisi`: sayfanın görseli tek sayfalık PDF'ten, 300 dpi JPEG.
- `test_rehber_ayni_kalir`: PDF zemini rehberin verisine yalnız `pdf_zemin` ekler; sayfanın izi (her parçanın adımı, sırası, kartı, yazısı,
  köşeleri; adımların metni ve kamerası) PDF'siz sayfanınkiyle aynı, sayfa hatasız açılır (iz: Node, Playwright, three.js 0.160.0).
"""
from __future__ import annotations

import base64
import io
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from araclar.paket.rehber import iz  # noqa: E402
from araclar.paket.rehber import pdf_zemin as PZ  # noqa: E402

HEDEF = json.loads((Path(__file__).with_name("rehber_pdf") / "TK01_r07.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cizim(tmp_path_factory):
    from araclar.paket import uret as U
    ie = json.loads((KOK / HEDEF["is_emri"]).read_text(encoding="utf-8"))
    return U.cizim(ie, tmp_path_factory.mktemp("tk01_r07"))


def test_a4_plan_motordan_okunur(cizim, tmp_path):
    from motor import dxf_out
    a4 = cizim["a4_plan"]
    assert a4 is not None and cizim["pdf"] is not None
    assert a4["sayfa_mm"] == HEDEF["a4"]["sayfa_mm"]
    for k in ("plan_mm", "plan_kutu_cm"):
        assert a4[k] == pytest.approx(HEDEF["a4"][k], abs=1e-6), k
    assert a4["olcek_mm_cm"] == pytest.approx(HEDEF["a4"]["olcek_mm_cm"], rel=1e-9)
    # okuyucu motorun işlevlerini geri koyar; okunurken çizilen PDF okuyucusuz çizilenle bayt bayt aynı
    assert dxf_out.a4_yerlesim.__module__ == "motor.dxf_out" and dxf_out._bolge_pdf.__module__ == "motor.dxf_out"
    ie = json.loads((KOK / HEDEF["is_emri"]).read_text(encoding="utf-8"))
    m = dxf_out.uret(ie, tmp_path / "okuyucusuz")
    assert (tmp_path / "okuyucusuz" / m["pdf"]).read_bytes() == Path(cizim["pdf"]).read_bytes()


def test_kagit_dikdortgeni():
    k = PZ.kagit_cm(HEDEF["a4"])
    assert [round(v, 3) for v in k] == HEDEF["kagit_cm"]
    # planın kutusu sayfada planın dikdörtgenine düşer (motorun dönüşümü: x + (X − kx0)·s, y + (ky1 − Y)·s)
    a = HEDEF["a4"]; x, y, w, h = a["plan_mm"]; s = a["olcek_mm_cm"]; kx0, ky0, kx1, ky1 = a["plan_kutu_cm"]
    sw, sh = a["sayfa_mm"]
    sayfa = lambda X, Y: ((X - k[0]) / (k[2] - k[0]) * sw, (k[3] - Y) / (k[3] - k[1]) * sh)
    assert sayfa(kx0, ky1) == pytest.approx((x, y), abs=1e-6)
    assert sayfa(kx1, ky0) == pytest.approx((x + w, y + h), abs=1e-6)


def test_pdf_zemin_verisi(cizim):
    from PIL import Image
    pz = PZ.veri(cizim["pdf"], cizim["a4_plan"])
    assert pz["resim"].startswith("data:image/jpeg;base64,")
    assert pz["piksel"] == HEDEF["piksel"]
    im = Image.open(io.BytesIO(base64.b64decode(pz["resim"].split(",", 1)[1])))
    assert im.format == "JPEG" and list(im.size) == HEDEF["piksel"]
    assert pz["kagit_cm"] == HEDEF["kagit_cm"]
    assert set(pz) == {"resim", "piksel", "kagit_cm"}       # A4 yerleşiminin ham ondalıkları sayfaya yazılmaz (numara taraması)


def _jpeg_1x1() -> str:
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (1, 1), (255, 255, 255)).save(b, "JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode("ascii")


def test_rehber_ayni_kalir(tmp_path):
    from araclar.paket.rehber import sayfa
    d = json.loads((Path(__file__).with_name("rehber62") / "veri.json").read_text(encoding="utf-8"))
    d2 = dict(d, pdf_zemin={"resim": _jpeg_1x1(), "piksel": [1, 1], "kagit_cm": [-500.0, -800.0, 1250.0, 1680.0]})
    a, b = sayfa.yaz(d, tmp_path / "a.html"), sayfa.yaz(d2, tmp_path / "b.html")
    if iz.hazir() is not None:
        pytest.skip(f"rehber izi: {iz.hazir()}")
    za, zb = iz.al(a, tmp_path / "a.json"), iz.al(b, tmp_path / "b.json")
    assert zb["hatalar"] == []
    for k in ("N", "liste", "ilerleme", "parca"):
        assert zb[k] == za[k], k
