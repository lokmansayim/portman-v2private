"""İE-16 PR-4 · kör paftanın sayfa denetimi (`kor_sayfa.py`): uydurma paftayla kurallar; tam koşuda (`PORTMAN_CELIK_KAYNAK`) açık beşin
paftasında 1. sayfa etiketsiz, kat tek ve yöntem listelerimizin yöntemiyle aynı (ÇP-03 A, öteki dördü B); pafta mühürdeki montaj
paftasıdır (`kiyas.muhur_denetle`)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(KOK))
from testler.celik import kiyas  # noqa: E402
from testler.celik.projeler import kor_sayfa  # noqa: E402

BURADA = Path(__file__).resolve().parent
KAYNAK = os.environ.get("PORTMAN_CELIK_KAYNAK")
MUHUR = json.loads(kiyas.MUHUR.read_text(encoding="utf-8"))
ACIK = sorted(k for k, p in MUHUR["projeler"].items() if p["durum"] in ("acik", "hedef"))


def uydurma(yol: Path, sayfalar: list[str]) -> Path:
    import pymupdf

    doc = pymupdf.open()
    for metin in sayfalar:
        doc.new_page().insert_text((72, 72), metin, fontname="helv")
    doc.save(str(yol))
    return yol


def test_duz():
    assert kor_sayfa.duz("Aşık") == "ASIK" and kor_sayfa.duz("BİRİNCİ kat") == "BIRINCI KAT" and kor_sayfa.duz("ıi") == "II"


def test_uydurma_pafta(tmp_path):
    tek = kor_sayfa.denetle(uydurma(tmp_path / "a.pdf", ["ZEMIN KAT PLANI 900 M2", "D01 D02 MK03", "CATI PANEL C01"]))
    assert tek["onay_sayfasi_etiketsiz"] and tek["yontem"] == "A" and tek["kat"] == "tek" and tek["kat_dayanagi"] is None
    b = kor_sayfa.denetle(uydurma(tmp_path / "b.pdf", ["PLAN", "TAVAN OMEGA YERLESIMI"]))
    assert b["yontem"] == "B"
    b2 = kor_sayfa.denetle(uydurma(tmp_path / "b2.pdf", ["PLAN", "asik plani"]))
    assert b2["yontem"] == "B"
    cift = kor_sayfa.denetle(uydurma(tmp_path / "c.pdf", ["PLAN", "1.KAT TAVAN OMEGA", "1. KAT DUVAR PANELLERI"]))
    assert cift["kat"] == "çift" and cift["kat_dayanagi"] == "2. sayfa: 1.KAT"
    assert kor_sayfa.denetle(uydurma(tmp_path / "d.pdf", ["11. KAT", "ZEMIN KAT", "TEK KATLI"]))["kat"] == "tek"


@pytest.mark.parametrize("metin", ["ZEMIN + 1 KAT", "1 KAT PLANI", "I. KAT PLANI", "UST KAT", "MERDIVEN DETAYI", "DUBLEKS", "2 KATLI"])
def test_kat_ipucu_belirsiz(tmp_path, metin):
    """Mühürün kat ayrımına uymayan kat ya da merdiven sözcüğü sessizce tek sayılmaz (kod incelemesi)."""
    s = kor_sayfa.denetle(uydurma(tmp_path / "k.pdf", ["PLAN", metin]))
    assert s["kat"] == "belirsiz" and s["kat_dayanagi"].startswith("2. sayfa: ")


def test_etiketli_onay_sayfasi_acilmaz(tmp_path):
    p = uydurma(tmp_path / "e.pdf", ["PLAN D01 (D02)", "x"])
    assert kor_sayfa.denetle(p)["onay_sayfasi_etiketsiz"] is False
    with pytest.raises(SystemExit):
        kor_sayfa.onay_png(p, tmp_path / "e.png")
    assert not (tmp_path / "e.png").exists()
    p2 = uydurma(tmp_path / "f.pdf", ["PLAN 81 M2 DK1 KP1 120/180", "D01"])     # kapı ve pencere kodları etiket değil (ÇP-14'ün 1. sayfası)
    assert kor_sayfa.onay_png(p2, tmp_path / "f.png").is_file()


@pytest.mark.parametrize("metin", ["PLAN D04A", "PLAN D 06", "PLAN MK 3", "PLAN KRS-12B"])
def test_ekli_ve_bolunmus_etiket(tmp_path, metin):
    assert kor_sayfa.denetle(uydurma(tmp_path / "g.pdf", [metin]))["onay_sayfasi_etiketsiz"] is False


@pytest.mark.skipif(not KAYNAK, reason="tam koşu: PORTMAN_CELIK_KAYNAK=<klasör> (dosyalar Drive kimliğiyle adlı)")
@pytest.mark.parametrize("kod", ACIK)
def test_acik_besin_paftasi(kod):
    paftalar = [d for d in MUHUR["dosyalar"] if d["kod"] == kod and d["tur"] == kiyas.PAFTA]
    assert len(paftalar) == 1, kod
    yol = Path(KAYNAK) / f"{paftalar[0]['drive_id']}.pdf"
    kiyas.muhur_denetle(yol, MUHUR, kod, turler=(kiyas.PAFTA,))
    s = kor_sayfa.denetle(yol)
    yontem = json.loads((BURADA / kiyas.kod_klasoru(kod) / "bizim_liste.json").read_text(encoding="utf-8"))["yontem"]["kod"]
    assert s["onay_sayfasi_etiketsiz"] and s["kat"] == "tek"
    assert s["yontem"] == {"panel": "A", "omega_asik": "B"}[yontem]
