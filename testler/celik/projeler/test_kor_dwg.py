"""İE-16 PR-7 · kör paftanın onay sayfası DWG'den (`kor_dwg.py`): uydurma DXF'le kurallar (çerçeve, onay adayı, etiket, yöntem, kat);
LibreDWG'nin çözemediği 1254 baytları. Gerçek DWG'ler depoya girmez; ikinci kümenin sonuçları aracın belgesinde."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(KOK))
from testler.celik.projeler import kor_dwg  # noqa: E402

W, H = 2970.0, 2100.0


def uydurma(yol: Path, cerceveler: list[list[str]], disari: list[str] = ()) -> Path:
    """Yan yana A3 oranlı çerçeveler (kapalı dikdörtgen), her birinin içinde verilen yazılar; `disari` çerçevelerin dışında."""
    import ezdxf

    doc = ezdxf.new("R2018")
    msp = doc.modelspace()
    for i, yazilar in enumerate(cerceveler):
        x0 = i * (W + 300)
        msp.add_lwpolyline([(x0, 0), (x0 + W, 0), (x0 + W, H), (x0, H)], close=True)
        msp.add_lwpolyline([(x0 + 50, 50), (x0 + W - 50, 50), (x0 + W - 50, H - 50), (x0 + 50, H - 50)], close=True)   # iç çerçeve
        for j, t in enumerate(yazilar):
            msp.add_text(t, dxfattribs={"insert": (x0 + 200, H - 300 - 100 * j), "height": 20})
    for j, t in enumerate(disari):
        msp.add_text(t, dxfattribs={"insert": (-2000, 100 * j), "height": 20})
    doc.saveas(yol)
    return yol


def test_coz():
    assert kor_dwg.coz("k\udcf6şebent") == "köşebent" and kor_dwg.coz("DIŞ") == "DIŞ"


def test_uydurma_dwg(tmp_path):
    d = kor_dwg.denetle(uydurma(tmp_path / "a.dxf", [
        ["MÜŞTERİ ONAY PAFTASI", "Dış Duvarlar ( kalınlık )", "140 mm", "İç Duvarlar ( kalınlık )", "80 mm"],
        ["DUVAR PANELLERİ", "D01", "D02", "TAVAN OMEGASI"],
        ["KAT PLANI", "Dış Duvarlar ( kalınlık )", "İç Duvarlar ( kalınlık )", "K1"],
    ]))
    assert d["cerceve_sayisi"] == 3 and d["onay"] == [1]                     # iç çerçeve sayılmaz (iç içe olanlardan dıştaki)
    assert [s["etiketsiz"] for s in d["sayfalar"]] == [True, False, False]   # "K1" de etiket biçimine uyar: plan çerçevesi aday değil
    assert d["sayfalar"][2]["ozellik_tablosu"] and not d["sayfalar"][2]["musteri_onay"]
    assert d["yontem"] == "B" and d["kat"] == "tek" and d["kat_dayanagi"] is None


def test_kat_ve_yontem(tmp_path):
    cift = kor_dwg.denetle(uydurma(tmp_path / "c.dxf", [["TEKNİK ÖZELLİKLER"], ["1. KAT PLANI"]]))
    assert cift["kat"] == "çift" and cift["kat_dayanagi"] == "2. çerçeve: 1. KAT" and cift["yontem"] == "A" and cift["onay"] == [1]
    disari = kor_dwg.denetle(uydurma(tmp_path / "d.dxf", [["TEKNİK ÖZELLİKLER"]], disari=["araziye göre merdiven sayısı"]))
    assert disari["kat"] == "belirsiz" and disari["kat_dayanagi"] == "çerçeve dışı: MERDIVEN"


def test_onay_olmayan_cerceve_gorunture_cevrilmez(tmp_path):
    dxf = uydurma(tmp_path / "e.dxf", [["TEKNİK ÖZELLİKLER"], ["DUVAR PANELLERİ", "D01"]])
    with pytest.raises(SystemExit, match="onay sayfası adayı değil"):
        kor_dwg.onay_png(dxf, 2, tmp_path / "e.png")
    assert not (tmp_path / "e.png").exists()
